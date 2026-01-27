# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime

# Import the class under test
from flexirule.ruleflow.doctype.rule_scheduler.rule_scheduler import RuleScheduler


class TestRuleScheduler(FrappeTestCase):
	def setUp(self):
		# Create a dummy rule for testing
		if not frappe.db.exists("Rule", "Test Scheduler Rule"):
			self.rule = frappe.get_doc(
				{
					"doctype": "Rule",
					"rule_name": "Test Scheduler Rule",
					"document_type": "ToDo",
					"trigger_event": "Before Save",
					"is_active": 1,
					"actions": [
						{
							"action_type": "Set Value",
							"action_label": "Make High Priority",
							"action_id": "act_high_prio",
							"is_entry_action": 1,
							"next_step_if_true": None,
							"target_field": "priority",
							"value_template": "High",
						}
					],
				}
			).insert(ignore_permissions=True)
		else:
			self.rule = frappe.get_doc("Rule", "Test Scheduler Rule")

	def tearDown(self):
		frappe.db.rollback()

	def test_frequency_calculation(self):
		scheduler = frappe.get_doc(
			{
				"doctype": "Rule Scheduler",
				"rule": self.rule.name,
				"frequency": "Daily",
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

		next_run = scheduler.get_next_execution()
		self.assertTrue(next_run > now_datetime())
		# Roughly 1 day from now/creation
		diff = next_run - now_datetime()
		# Should be within 24 hours from now (Daily = next midnight)
		self.assertTrue(diff.total_seconds() <= 86400 + 3600)
		self.assertTrue(diff.total_seconds() > 0)

	def test_cron_validation(self):
		scheduler = frappe.new_doc("Rule Scheduler")
		scheduler.rule = self.rule.name
		scheduler.frequency = "Cron"
		scheduler.cron_format = "invalid-cron"

		with self.assertRaises(frappe.ValidationError):
			scheduler.save()

		scheduler.cron_format = "0 0 * * *"  # Valid
		scheduler.save()
		self.assertTrue(scheduler.name)

	def test_is_event_due(self):
		scheduler = frappe.get_doc(
			{
				"doctype": "Rule Scheduler",
				"rule": self.rule.name,
				"frequency": "Hourly",
			}
		).insert()

		# Should NOT be due immediately (next run is 1 hour later)
		self.assertFalse(scheduler.is_event_due())

		# Mock last_execution to be old
		scheduler.db_set("last_execution", add_days(now_datetime(), -1))
		# Now it should be due (re-fetch to clear cached properties)
		scheduler.reload()

		# We need to manually trigger calculation or rely on property
		# The property `.next_execution` uses `get_next_execution()` which uses `last_execution`
		# So it should return a time in the past if last_execution is old + Hourly frequency?
		# Wait, croniter(cron, last_execution).get_next() will return next occurrence AFTER last_execution.
		# If last_execution was yesterday, next would be yesterday + 1 hour.
		# So next_execution < now.

		self.assertTrue(scheduler.is_event_due())

	def test_batch_execution_flow(self):
		# Create unique ToDos to avoid data pollution from previous runs (due to commit)
		unique_id = frappe.generate_hash(length=8)

		todo1 = frappe.get_doc({"doctype": "ToDo", "description": f"Batch Test {unique_id} 1"}).insert()
		todo2 = frappe.get_doc({"doctype": "ToDo", "description": f"Batch Test {unique_id} 2"}).insert()

		scheduler = frappe.get_doc(
			{
				"doctype": "Rule Scheduler",
				"rule": self.rule.name,
				"frequency": "Daily",
				"filter_doctype": "ToDo",
				"filter_json": json.dumps({"description": ["like", f"Batch Test {unique_id}%"]}),
				"batch_size": 2,
			}
		).insert()

		# Mock enqueue to run synchronously or just call execute directly
		scheduler.execute()

		# Check logs
		logs = frappe.get_all(
			"Rule Execution Log",
			filters={"scheduler": scheduler.name},
			fields=["reference_docname", "batch_id", "batch_index", "batch_total"],
		)

		self.assertEqual(len(logs), 2)
		docnames = [l.reference_docname for l in logs]
		self.assertIn(todo1.name, docnames)
		self.assertIn(todo2.name, docnames)

		# Check batch fields
		self.assertEqual(logs[0].batch_total, 2)
		self.assertTrue(logs[0].batch_id.startswith("BATCH-"))
