# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.utils.frappe_query_compat import execute_query

TREE_DOCTYPE = "Fetch Records Tree Test Node"


class TestFetchRecordsTreeOperators(FrappeTestCase):
	"""Database integration coverage for Fetch Records nested-set filters on Frappe 15 and 16."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._setup_tree_doctype()
		cls._setup_tree_records()

	@classmethod
	def tearDownClass(cls):
		frappe.db.delete(TREE_DOCTYPE)
		if frappe.db.exists("DocType", TREE_DOCTYPE):
			frappe.delete_doc("DocType", TREE_DOCTYPE, force=True, ignore_permissions=True)
		frappe.db.commit()
		super().tearDownClass()

	@classmethod
	def _setup_tree_doctype(cls):
		if not frappe.db.exists("DocType", TREE_DOCTYPE):
			frappe.get_doc(
				{
					"doctype": "DocType",
					"name": TREE_DOCTYPE,
					"module": "RuleFlow",
					"custom": 1,
					"is_tree": 1,
					"nsm_parent_field": "parent_fetch_records_tree_test_node",
					"fields": [
						{"fieldname": "tree_label", "fieldtype": "Data", "label": "Tree Label", "reqd": 1},
						{
							"fieldname": "parent_fetch_records_tree_test_node",
							"fieldtype": "Link",
							"options": TREE_DOCTYPE,
							"label": "Parent Tree Node",
						},
						{"fieldname": "old_parent", "fieldtype": "Data", "label": "Old Parent"},
						{"fieldname": "is_group", "fieldtype": "Check", "label": "Is Group"},
						{"fieldname": "lft", "fieldtype": "Int", "label": "Left", "hidden": 1},
						{"fieldname": "rgt", "fieldtype": "Int", "label": "Right", "hidden": 1},
					],
				}
			).insert(ignore_permissions=True)
		frappe.db.commit()

	@classmethod
	def _setup_tree_records(cls):
		frappe.db.delete(TREE_DOCTYPE)
		cls.root = frappe.get_doc({"doctype": TREE_DOCTYPE, "tree_label": "Root", "is_group": 1}).insert(
			ignore_permissions=True
		)
		cls.child_a = frappe.get_doc(
			{
				"doctype": TREE_DOCTYPE,
				"tree_label": "Child A",
				"parent_fetch_records_tree_test_node": cls.root.name,
				"is_group": 1,
			}
		).insert(ignore_permissions=True)
		cls.grandchild_a = frappe.get_doc(
			{
				"doctype": TREE_DOCTYPE,
				"tree_label": "Grandchild A",
				"parent_fetch_records_tree_test_node": cls.child_a.name,
				"is_group": 0,
			}
		).insert(ignore_permissions=True)
		cls.child_b = frappe.get_doc(
			{
				"doctype": TREE_DOCTYPE,
				"tree_label": "Child B",
				"parent_fetch_records_tree_test_node": cls.root.name,
				"is_group": 0,
			}
		).insert(ignore_permissions=True)
		cls.other_root = frappe.get_doc(
			{"doctype": TREE_DOCTYPE, "tree_label": "Other Root", "is_group": 1}
		).insert(ignore_permissions=True)
		frappe.db.commit()

	def _run_filter(self, filters):
		rows = execute_query(
			TREE_DOCTYPE,
			{"fields": ["name"], "filters": filters},
			ignore_permissions=True,
		)
		return {row["name"] for row in rows}

	def test_all_five_nested_set_operators_as_single_filters(self):
		cases = {
			"descendants of": (
				self.root.name,
				{self.child_a.name, self.grandchild_a.name, self.child_b.name},
			),
			"descendants of (inclusive)": (
				self.root.name,
				{self.root.name, self.child_a.name, self.grandchild_a.name, self.child_b.name},
			),
			"not descendants of": (
				self.root.name,
				{self.root.name, self.other_root.name},
			),
			"ancestors of": (
				self.grandchild_a.name,
				{self.root.name, self.child_a.name},
			),
			"not ancestors of": (
				self.grandchild_a.name,
				{self.grandchild_a.name, self.child_b.name, self.other_root.name},
			),
		}

		for operator, (target, expected_names) in cases.items():
			with self.subTest(operator=operator):
				# A one-leaf canonical tree can collapse to this bare leaf shape.
				actual_names = self._run_filter(["name", operator, target])
				self.assertEqual(actual_names, expected_names)

	def test_all_five_nested_set_operators_compose_with_and_and_or(self):
		cases = {
			"descendants of": (
				self.root.name,
				{self.child_a.name, self.grandchild_a.name, self.child_b.name},
				self.child_a.name,
				self.root.name,
			),
			"descendants of (inclusive)": (
				self.root.name,
				{self.root.name, self.child_a.name, self.grandchild_a.name, self.child_b.name},
				self.root.name,
				self.other_root.name,
			),
			"not descendants of": (
				self.root.name,
				{self.root.name, self.other_root.name},
				self.other_root.name,
				self.child_a.name,
			),
			"ancestors of": (
				self.grandchild_a.name,
				{self.root.name, self.child_a.name},
				self.root.name,
				self.child_b.name,
			),
			"not ancestors of": (
				self.grandchild_a.name,
				{self.grandchild_a.name, self.child_b.name, self.other_root.name},
				self.grandchild_a.name,
				self.root.name,
			),
		}

		for operator, (target, hierarchy_names, and_name, or_name) in cases.items():
			for connector in ("and", "or"):
				with self.subTest(operator=operator, connector=connector):
					other_name = and_name if connector == "and" else or_name
					filters = [
						["name", operator, target],
						connector,
						["name", "=", other_name],
					]
					actual_names = self._run_filter(filters)
					if connector == "and":
						self.assertEqual(actual_names, hierarchy_names & {and_name})
						self.assertTrue(actual_names, "AND case should retain a matching hierarchy node")
					else:
						self.assertEqual(actual_names, hierarchy_names | {or_name})
