# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import cstr


class TestRuleReorder(FrappeTestCase):
	def _insert_with_retry(self, doc, retries=3):
		last_error = None
		for _ in range(retries):
			try:
				return doc.insert()
			except frappe.QueryDeadlockError as e:
				last_error = e
				frappe.db.rollback()
		if last_error:
			raise last_error
		return doc

	def tearDown(self):
		frappe.db.rollback()

	def test_reorder_actions(self):
		# Create a rule where Entry Action is NOT first in the list provided
		rule = frappe.new_doc("Rule")
		rule.rule_name = f"Reorder Test Rule {frappe.generate_hash(length=6)}"
		rule.document_type = "ToDo"
		rule.trigger_event = "Before Save"

		# Add actions in wrong order
		rule.append(
			"actions",
			{
				"action_type": "Set Value",
				"action_label": "Action 1",  # Should be 2nd
				"action_id": "act1",
				"target_field": "description",
				"value_template": "test",
			},
		)

		rule.append(
			"actions",
			{
				"action_type": "Entry Action",
				"action_label": "Start",  # Should be 1st
				"action_id": "root",
				"next_step_if_true": "act1",
			},
		)

		self._insert_with_retry(rule)

		# Check order
		self.assertEqual(len(rule.actions), 2)
		self.assertEqual(rule.actions[0].action_type, "Entry Action")
		self.assertEqual(rule.actions[0].idx, 1)
		self.assertEqual(rule.actions[1].action_type, "Set Value")
		self.assertEqual(rule.actions[1].idx, 2)

	def test_ensure_start_node_reorder(self):
		# Test ensure_start_node adds it and then reorder puts it at top
		rule = frappe.new_doc("Rule")
		rule.rule_name = f"Reorder Test Ensure {frappe.generate_hash(length=6)}"
		rule.document_type = "ToDo"
		rule.trigger_event = "Before Save"

		# Add one action, no entry action
		rule.append(
			"actions",
			{
				"action_type": "Set Value",
				"action_label": "First Added",
				"action_id": "act1",
				"target_field": "description",
				"value_template": "test",
			},
		)

		self._insert_with_retry(rule)

		# Ensure start node adds Entry Action. Reorder should move it to top.
		self.assertEqual(len(rule.actions), 2)
		self.assertEqual(rule.actions[0].action_type, "Entry Action")
		self.assertEqual(rule.actions[1].action_type, "Set Value")
