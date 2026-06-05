# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Tests for FlexiRule Rule Engine
"""

import json
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.engine import RuleEngine


class TestRuleEngine(FrappeTestCase):
	"""Test cases for Rule Engine"""

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		# Create test rule if not exists
		if not frappe.db.exists("Rule", "Test Validation Rule"):
			frappe.get_doc(
				{
					"doctype": "Rule",
					"rule_name": "Test Validation Rule",
					"document_type": "ToDo",
					"trigger_type": "DocType Event",
					"trigger_event": "Validate",
					"is_active": 1,
					"priority": 10,
				}
			).insert(ignore_permissions=True)

	def _create_stop_rule(self, debug_mode=0):
		return frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": f"Test Log Policy {frappe.generate_hash(length=8)}",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"debug_mode": debug_mode,
				"actions": [
					{
						"action_id": "root",
						"action_type": "Entry Action",
						"action_label": "Start",
						"is_enabled": 1,
						"next_step_if_true": "node_end",
					},
					{
						"action_id": "node_end",
						"action_type": "Stop",
						"operation": "Success",
						"action_label": "End",
						"is_enabled": 1,
					},
				],
			}
		).insert(ignore_permissions=True)

	def test_rule_creation(self):
		"""Test rule is created correctly"""
		rule = frappe.get_doc("Rule", "Test Validation Rule")
		self.assertEqual(rule.document_type, "ToDo")
		self.assertEqual(rule.is_active, 1)

	def test_process_loading(self):
		"""Test processes can be loaded"""
		validation = frappe.get_doc("Process", "Validation")
		enrichment = frappe.get_doc("Process", "Enrichment")

		self.assertEqual(validation.name, "Validation")
		self.assertEqual(enrichment.name, "Enrichment")

	def test_engine_process_execution(self):
		"""
		Test that RuleEngine correctly executes a Process action.
		"""
		# Mock Rule with Process action
		rule_doc = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Engine Process",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"actions": [
					{
						"action_id": "ACT-PROCESS",
						"action_type": "Process",
						"action_label": "Validation Process",
						"is_enabled": 1,
						"process_name": "Validation",
						"operation": "conditional_required",
						"config": '{"condition_field": "status", "condition_value": "Open", "required_fields": ["description"]}',
						"on_error": "Stop",
					}
				],
			}
		)

		engine = RuleEngine(rule_doc)

		# 1. Test success
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test", "status": "Open"})
		engine.execute(doc)

		# Verify execution trace
		trace = [t for t in engine.path_trace if t["type"] == "Process"]
		self.assertTrue(len(trace) > 0)
		self.assertEqual(trace[0]["action"], "Validation Process")

		# 2. Test failure - Now returns a result dict rather than throwing
		doc_fail = frappe.get_doc({"doctype": "ToDo", "description": "", "status": "Open"})
		engine.execute(doc_fail)

		# Trace should show process executed
		trace_fail = [t for t in engine.path_trace if t["type"] == "Process"]
		self.assertTrue(len(trace_fail) > 0)

		# For validation processes, we now expect an 'is_valid' flag in result
		last_action_result = engine.path_trace[-1].get("result")
		self.assertFalse(last_action_result.get("is_valid"))

	def test_execution_log_defaults_to_vars_only_snapshot(self):
		rule = self._create_stop_rule()
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Sensitive task"})
		engine = RuleEngine(
			rule,
			execution_context={
				"skip_log_enqueue": True,
				"vars": {"safe_value": "kept"},
			},
		)

		engine.execute(doc)

		snapshot = json.loads(engine.last_execution_log_payload["context_snapshot"])
		self.assertEqual(snapshot.get("safe_value"), "kept")
		self.assertNotIn("doc", snapshot)

	def test_execution_log_includes_doc_snapshot_in_debug_mode(self):
		rule = self._create_stop_rule(debug_mode=1)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Debug task"})
		engine = RuleEngine(
			rule,
			execution_context={
				"skip_log_enqueue": True,
				"vars": {"safe_value": "kept"},
			},
		)

		engine.execute(doc)

		snapshot = json.loads(engine.last_execution_log_payload["context_snapshot"])
		self.assertEqual(snapshot.get("safe_value"), "kept")
		self.assertEqual(snapshot.get("doc", {}).get("description"), "Debug task")
