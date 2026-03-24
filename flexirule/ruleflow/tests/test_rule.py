# Copyright (c) 2025, Bolton and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

# On IntegrationTestCase, the doctype test records and all
# link-field test record depdendencies are recursively loaded
# Use these module variables to add/remove to/from that list
# EXTRA_TEST_RECORD_DEPENDENCIES = ["...]  # eg. ["User"]
# IGNORE_TEST_RECORD_DEPENDENCIES = ["..."]  # eg. ["User"]


class TestRule(FrappeTestCase):
	def tearDown(self):
		super().tearDown()
		frappe.db.delete("Rule", {"rule_name": ["like", "Test Rule Validation%"]})

	def test_active_rule_requires_next_step(self):
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Rule Validation Missing False Path",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"actions": [
					{
						"action_id": "root",
						"action_type": "Entry Action",
						"action_label": "Start",
						"next_step_if_true": "condition_1",
					},
					{
						"action_id": "condition_1",
						"action_type": "Condition",
						"action_label": "Check",
						"condition_json": '[{"left":{"ref":"doc.description"},"op":"!=","right":{"value":""}}]',
						"next_step_if_true": "stop_1",
					},
					{
						"action_id": "stop_1",
						"action_type": "Stop",
						"action_label": "Stop",
					},
				],
			}
		)

		with self.assertRaises(frappe.ValidationError):
			rule.insert(ignore_permissions=True)

	def test_scheduler_rule_clears_doc_event_fields(self):
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Rule Validation Scheduler Leakage",
				"document_type": "ToDo",
				"trigger_type": "Scheduler Event",
				"trigger_event": "Validate",
				"is_active": 0,
				"actions": [],
			}
		)

		rule.insert(ignore_permissions=True)
		self.assertFalse(rule.trigger_event)
