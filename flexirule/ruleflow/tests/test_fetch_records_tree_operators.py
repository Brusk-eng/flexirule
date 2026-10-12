# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.database.utils import NestedSetHierarchy
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.action_handlers.query_records import QueryRecordsHandler
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

	def test_fetch_records_operator_contract_matches_portable_frappe_query_builder_operators(self):
		handler = QueryRecordsHandler()
		allowed = handler._FETCH_RECORDS_OPERATORS
		shared_operators = {
			"=",
			"!=",
			">",
			">=",
			"<",
			"<=",
			"like",
			"not like",
			"in",
			"not in",
			"between",
			"is",
			"timespan",
			"starts with",
			"ends with",
		}

		self.assertTrue(shared_operators.issubset(allowed))
		self.assertTrue({op.casefold() for op in NestedSetHierarchy}.issubset(allowed))
		# These entries are either invalid or version/dialect-specific in the upstream
		# Query Builder, so they are deliberately not part of Fetch Records' portable contract.
		for invalid_operator in ("<>", "regex", "ilike", "previous", "next"):
			with self.subTest(operator=invalid_operator):
				self.assertNotIn(invalid_operator, allowed)
				errors = handler._validate_canonical_fetch_filter_tree(
					{
						"type": "leaf",
						"field": "tree_label",
						"operator": invalid_operator,
						"value": {"mode": "static", "value": "Root"},
					}
				)
				self.assertTrue(any("operator is not supported" in error for error in errors))

	def test_is_operator_requires_native_set_value(self):
		handler = QueryRecordsHandler()
		for value in ("set", "not set", "SET", "Not Set"):
			with self.subTest(value=value):
				errors = handler._validate_canonical_fetch_filter_tree(
					{
						"type": "leaf",
						"field": "tree_label",
						"operator": "is",
						"value": {"mode": "static", "value": value},
					}
				)
				self.assertEqual(errors, [])

		errors = handler._validate_canonical_fetch_filter_tree(
			{
				"type": "leaf",
				"field": "tree_label",
				"operator": "is",
				"value": {"mode": "static", "value": "empty"},
			}
		)
		self.assertTrue(any("must be 'set' or 'not set'" in error for error in errors))

	def test_nested_set_operators_require_tree_doctype_context(self):
		handler = QueryRecordsHandler()
		invalid = handler._validate_canonical_fetch_filter_tree(
			{
				"type": "leaf",
				"field": "name",
				"operator": "descendants of",
				"value": {"mode": "static", "value": "some-name"},
			},
			reference_doctype="ToDo",
		)
		self.assertTrue(any("requires a Tree DocType" in error for error in invalid))

		valid_tree_name = handler._validate_canonical_fetch_filter_tree(
			{
				"type": "leaf",
				"field": "name",
				"operator": "descendants of",
				"value": {"mode": "static", "value": self.root.name},
			},
			reference_doctype=TREE_DOCTYPE,
		)
		self.assertEqual(valid_tree_name, [])

		valid_tree_link = handler._validate_canonical_fetch_filter_tree(
			{
				"type": "leaf",
				"field": "parent_fetch_records_tree_test_node",
				"operator": "ancestors of",
				"value": {"mode": "static", "value": self.child_a.name},
			},
			reference_doctype=TREE_DOCTYPE,
		)
		self.assertEqual(valid_tree_link, [])

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
