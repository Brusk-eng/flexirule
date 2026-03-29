# Copyright (c) 2026, FlexiRule and contributors
# See license.txt

"""
Comprehensive test suite for FlexiRule RC-ready validation.
Tests all action types and trigger types with real-world scenarios.
"""

import json
import time
import unittest
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.coordinator import RuleCoordinator
from flexirule.ruleflow.core.engine import RuleEngine
from flexirule.ruleflow.core.exceptions import (
	CycleDetectedError,
	EmptyRuleError,
	RuleDisabledError,
)
from flexirule.ruleflow.core.exceptions import TimeoutError as FlexiRuleTimeoutError


class TestRuleEngineCore(FrappeTestCase):
	"""Core engine tests for RC validation."""

	def setUp(self):
		super().setUp()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC Test%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC Test%"]})

	def tearDown(self):
		super().tearDown()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC Test%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC Test%"]})
		RuleCoordinator.clear_cache()

	def create_rule(
		self,
		name,
		actions=None,
		doctype="ToDo",
		event="Validate",
		trigger_type="DocType Event",
		is_active=1,
		**kwargs,
	):
		"""Helper to create test rules."""
		rule_doc = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": name,
				"document_type": doctype,
				"trigger_type": trigger_type,
				"trigger_event": event if trigger_type == "DocType Event" else None,
				"is_active": is_active,
				"priority": 10,
				"actions": actions
				or [
					{
						"action_id": "root",
						"action_type": "Entry Action",
						"action_label": "Start",
						"is_enabled": 1,
						"next_step_if_true": "ACT-END",
					},
					{
						"action_id": "ACT-END",
						"action_type": "Stop",
						"operation": "Success",
						"action_label": "End",
						"is_enabled": 1,
					},
				],
				**kwargs,
			}
		)
		rule_doc.insert(ignore_permissions=True)
		return rule_doc

	def test_engine_initialization_with_rule_doc(self):
		"""Engine should initialize with Rule doc object."""
		rule = self.create_rule("RC Test Init Doc")
		engine = RuleEngine(rule)
		self.assertEqual(engine.rule.name, rule.name)
		self.assertEqual(len(engine.actions), 2)

	def test_engine_initialization_with_rule_name(self):
		"""Engine should initialize with rule name string."""
		rule = self.create_rule("RC Test Init String")
		engine = RuleEngine(rule.name)
		self.assertEqual(engine.rule.name, rule.name)

	def test_engine_test_mode_bypasses_timeout(self):
		"""In test_mode, timeout should be bypassed."""
		rule = self.create_rule("RC Test No Timeout")
		rule.max_execution_time = 0.001  # Very short
		rule.flags.ignore_validate = True
		rule.save(ignore_permissions=True)

		engine = RuleEngine(rule, {"test_mode": True})
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		# Should not raise timeout error
		result = engine.execute(doc)
		self.assertIsInstance(result, dict)

	def test_engine_disabled_rule_raises_error(self):
		"""Disabled rule should raise RuleDisabledError."""
		rule = self.create_rule("RC Test Disabled", is_active=0)
		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		with self.assertRaises(RuleDisabledError):
			engine.execute(doc)

	def test_engine_empty_actions_raises_error(self):
		"""Rule with no enabled actions should raise EmptyRuleError."""
		rule = self.create_rule("RC Test Empty", actions=[])
		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		with self.assertRaises(EmptyRuleError):
			engine.execute(doc)

	def test_engine_path_trace_populated(self):
		"""Engine should populate path_trace during execution."""
		rule = self.create_rule("RC Test Path Trace")
		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		engine.execute(doc)

		self.assertTrue(len(engine.path_trace) > 0)
		self.assertTrue(any(p.get("action") for p in engine.path_trace))

	def test_engine_execution_log_populated(self):
		"""Engine should populate execution_log during execution."""
		rule = self.create_rule("RC Test Log")
		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		engine.execute(doc)

		self.assertTrue(len(engine.execution_log) > 0)
		self.assertTrue(all("message" in e for e in engine.execution_log))


class TestConditionAction(FrappeTestCase):
	"""Test Condition action type."""

	def setUp(self):
		super().setUp()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC Cond%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC Cond%"]})

	def tearDown(self):
		super().tearDown()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC Cond%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC Cond%"]})

	def create_condition_rule(self, name, condition_json, true_action="END", false_action=None):
		"""Helper to create rule with condition."""
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "COND-1",
			},
			{
				"action_id": "COND-1",
				"action_type": "Condition",
				"action_label": "Check Status",
				"is_enabled": 1,
				"condition_json": condition_json,
				"next_step_if_true": true_action,
				"next_step_if_false": false_action or "END",
			},
			{
				"action_id": "END",
				"action_type": "Stop",
				"operation": "Success",
				"action_label": "End",
				"is_enabled": 1,
			},
		]

		rule_doc = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": name,
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"priority": 10,
				"actions": actions,
			}
		)
		rule_doc.insert(ignore_permissions=True)
		return rule_doc

	def test_condition_true_path(self):
		"""Condition evaluating to true should follow true path."""
		condition = '[{"left": {"ref": "doc.description"}, "op": "!=", "right": {"value": ""}}]'
		rule = self.create_condition_rule("RC Cond True", condition)

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Has value"})

		engine.execute(doc)

		self.assertTrue(any(p.get("action") == "Check Status" for p in engine.path_trace))

	def test_condition_false_path(self):
		"""Condition evaluating to false should follow false path."""
		condition = '[{"left": {"ref": "doc.description"}, "op": "==", "right": {"value": "wrong"}}]'
		rule = self.create_condition_rule("RC Cond False", condition)

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		engine.execute(doc)

		self.assertTrue(any(p.get("action") == "Check Status" for p in engine.path_trace))

	def test_condition_compilation_error(self):
		"""Invalid condition JSON should fail validation."""
		condition = '[{"left": {"ref": "doc.status"}, "op": "invalid_op", "right": {"value": "Open"}}]'

		with self.assertRaises(frappe.ValidationError):
			self.create_condition_rule("RC Cond Error", condition)


class TestProcessAction(FrappeTestCase):
	"""Test Process action type."""

	def setUp(self):
		super().setUp()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC Proc%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC Proc%"]})

	def tearDown(self):
		super().tearDown()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC Proc%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC Proc%"]})

	def test_process_action_execution(self):
		"""Process action should execute and store result."""
		# Use existing Validation process
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "PROC-1",
			},
			{
				"action_id": "PROC-1",
				"action_type": "Process",
				"action_label": "Validate Value",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "validation_result",
				"on_error": "Stop",
				"next_step_if_true": "END",
			},
			{
				"action_id": "END",
				"action_type": "Stop",
				"operation": "Success",
				"action_label": "End",
				"is_enabled": 1,
			},
		]

		rule_doc = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "RC Proc Test",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"priority": 10,
				"actions": actions,
			}
		)
		rule_doc.insert(ignore_permissions=True)

		engine = RuleEngine(rule_doc)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		result = engine.execute(doc)

		self.assertIn("validation_result", result.get("vars", {}))


class TestSubRuleAction(FrappeTestCase):
	"""Test Sub-Rule action type."""

	def setUp(self):
		super().setUp()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC Sub%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC Sub%"]})

	def tearDown(self):
		super().tearDown()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC Sub%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC Sub%"]})

	def test_sub_rule_execution(self):
		"""Sub-Rule should execute callable rule."""
		# Create sub-rule (Callable Event)
		sub_actions = [
			{
				"action_id": "SUB-START",
				"action_type": "Entry Action",
				"action_label": "Sub Start",
				"is_enabled": 1,
				"next_step_if_true": "SUB-PROC",
			},
			{
				"action_id": "SUB-PROC",
				"action_type": "Process",
				"action_label": "Sub Process",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"return_variable": "sub_result",
				"on_error": "Stop",
			},
		]

		sub_rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "RC Sub Rule",
				"document_type": "ToDo",
				"trigger_type": "Callable Event",
				"is_active": 1,
				"exposed_as_subrule": 1,
				"priority": 0,
				"actions": sub_actions,
			}
		)
		sub_rule.insert(ignore_permissions=True)

		# Create main rule calling sub-rule
		main_actions = [
			{
				"action_id": "MAIN-START",
				"action_type": "Entry Action",
				"action_label": "Main Start",
				"is_enabled": 1,
				"next_step_if_true": "CALL-SUB",
			},
			{
				"action_id": "CALL-SUB",
				"action_type": "Sub-Rule",
				"action_label": "Call Validation",
				"is_enabled": 1,
				"rule": sub_rule.name,
				"skip_conditions": 1,
				"next_step_if_true": "MAIN-END",
			},
			{
				"action_id": "MAIN-END",
				"action_type": "Stop",
				"operation": "Success",
				"action_label": "Main End",
				"is_enabled": 1,
			},
		]

		main_rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "RC Sub Main",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"priority": 10,
				"actions": main_actions,
			}
		)
		main_rule.insert(ignore_permissions=True)

		engine = RuleEngine(main_rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		engine.execute(doc)

		# Sub-rule should have executed
		sub_executed = any("Call Validation" in p.get("action", "") for p in engine.path_trace)
		self.assertTrue(sub_executed)

	def test_sub_rule_doc_type_flexibility(self):
		"""Sub-rule should work when parent doc_type differs but sub-rule has no doc_type."""
		# Create sub-rule without document_type
		sub_actions = [
			{
				"action_id": "SUB-START",
				"action_type": "Entry Action",
				"action_label": "Sub Start",
				"is_enabled": 1,
				"next_step_if_true": "SUB-END",
			},
			{
				"action_id": "SUB-END",
				"action_type": "Stop",
				"operation": "Success",
				"action_label": "Sub End",
				"is_enabled": 1,
			},
		]

		sub_rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "RC Sub No DocType",
				"document_type": None,
				"trigger_type": "Callable Event",
				"is_active": 1,
				"exposed_as_subrule": 1,
				"priority": 0,
				"actions": sub_actions,
			}
		)
		sub_rule.insert(ignore_permissions=True)

		# Main rule with different doc_type
		main_actions = [
			{
				"action_id": "MAIN-START",
				"action_type": "Entry Action",
				"action_label": "Main Start",
				"is_enabled": 1,
				"next_step_if_true": "CALL-SUB",
			},
			{
				"action_id": "CALL-SUB",
				"action_type": "Sub-Rule",
				"action_label": "Call Generic",
				"is_enabled": 1,
				"rule": sub_rule.name,
				"skip_conditions": 1,
				"next_step_if_true": "MAIN-END",
			},
			{
				"action_id": "MAIN-END",
				"action_type": "Stop",
				"operation": "Success",
				"action_label": "Main End",
				"is_enabled": 1,
			},
		]

		main_rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "RC Sub Main Diff",
				"document_type": "User",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"priority": 10,
				"actions": main_actions,
			}
		)
		main_rule.insert(ignore_permissions=True)

		engine = RuleEngine(main_rule)
		doc = frappe.get_doc({"doctype": "User", "email": "test@example.com"})

		# Should execute without doc_type mismatch error
		result = engine.execute(doc)
		self.assertIsInstance(result, dict)


class TestSetValueAction(FrappeTestCase):
	"""Test Set Value action type."""

	def setUp(self):
		super().setUp()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC SetVal%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC SetVal%"]})

	def tearDown(self):
		super().tearDown()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC SetVal%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC SetVal%"]})

	def test_set_value_updates_field(self):
		"""Set Value should update document field."""
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "SET-1",
			},
			{
				"action_id": "SET-1",
				"action_type": "Set Value",
				"action_label": "Set Priority",
				"is_enabled": 1,
				"target_field": "priority",
				"value_template": "High",
				"next_step_if_true": "END",
			},
			{
				"action_id": "END",
				"action_type": "Stop",
				"operation": "Success",
				"action_label": "End",
				"is_enabled": 1,
			},
		]

		rule_doc = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "RC SetVal Test",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Before Save",
				"is_active": 1,
				"priority": 10,
				"actions": actions,
			}
		)
		rule_doc.insert(ignore_permissions=True)

		engine = RuleEngine(rule_doc)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test", "priority": "Medium"})

		engine.execute(doc)

		self.assertEqual(doc.priority, "High")

	def test_set_value_with_jinja_template(self):
		"""Set Value should support Jinja templates."""
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "SET-1",
			},
			{
				"action_id": "SET-1",
				"action_type": "Set Value",
				"action_label": "Set Description",
				"is_enabled": 1,
				"target_field": "description",
				"value_template": "{{ doc.description }} - Processed",
				"next_step_if_true": "END",
			},
			{
				"action_id": "END",
				"action_type": "Stop",
				"operation": "Success",
				"action_label": "End",
				"is_enabled": 1,
			},
		]

		rule_doc = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "RC SetVal Jinja",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Before Save",
				"is_active": 1,
				"priority": 10,
				"actions": actions,
			}
		)
		rule_doc.insert(ignore_permissions=True)

		engine = RuleEngine(rule_doc)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Original"})

		engine.execute(doc)

		self.assertEqual(doc.description, "Original - Processed")


class TestStopAction(FrappeTestCase):
	"""Test Stop action type."""

	def setUp(self):
		super().setUp()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC Stop%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC Stop%"]})

	def tearDown(self):
		super().tearDown()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC Stop%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC Stop%"]})

	def test_stop_success(self):
		"""Stop Success should end execution cleanly."""
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "STOP-1",
			},
			{
				"action_id": "STOP-1",
				"action_type": "Stop",
				"operation": "Success",
				"action_label": "Success Stop",
				"is_enabled": 1,
			},
		]

		rule_doc = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "RC Stop Success",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"priority": 10,
				"actions": actions,
			}
		)
		rule_doc.insert(ignore_permissions=True)

		engine = RuleEngine(rule_doc)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		result = engine.execute(doc)
		self.assertIsInstance(result, dict)

	def test_stop_error_raises(self):
		"""Stop Error should raise ValidationError."""
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "STOP-1",
			},
			{
				"action_id": "STOP-1",
				"action_type": "Stop",
				"operation": "Error",
				"action_label": "Error Stop",
				"is_enabled": 1,
				"value_template": "Custom error message",
			},
		]

		rule_doc = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "RC Stop Error",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"priority": 10,
				"actions": actions,
			}
		)
		rule_doc.insert(ignore_permissions=True)

		engine = RuleEngine(rule_doc)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		with self.assertRaises(frappe.ValidationError):
			engine.execute(doc)


class TestQueryRecordsAction(FrappeTestCase):
	"""Test Query Records action type."""

	def setUp(self):
		super().setUp()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC Query%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC Query%"]})
		frappe.db.delete("ToDo", {"description": ["like", "RC Query Test%"]})

	def tearDown(self):
		super().tearDown()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC Query%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC Query%"]})
		frappe.db.delete("ToDo", {"description": ["like", "RC Query Test%"]})

	def test_query_list(self):
		"""Query List should return matching records."""
		# Create test data
		for i in range(3):
			frappe.get_doc(
				{
					"doctype": "ToDo",
					"description": f"RC Query Test {i}",
					"status": "Open",
				}
			).insert(ignore_permissions=True)

		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "QUERY-1",
			},
			{
				"action_id": "QUERY-1",
				"action_type": "Query Records",
				"action_label": "Find Todos",
				"is_enabled": 1,
				"reference_doctype": "ToDo",
				"operation": "Query List",
				"config": json.dumps({"filters": {"description": ["like", "RC Query Test%"]}, "limit": 10}),
				"return_variable": "todos",
				"return_type": "List of Dict",
				"next_step_if_true": "END",
			},
			{
				"action_id": "END",
				"action_type": "Stop",
				"operation": "Success",
				"action_label": "End",
				"is_enabled": 1,
			},
		]

		rule_doc = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "RC Query List",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"priority": 10,
				"actions": actions,
			}
		)
		rule_doc.insert(ignore_permissions=True)

		engine = RuleEngine(rule_doc)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		result = engine.execute(doc)

		todos = result.get("vars", {}).get("todos", [])
		self.assertIsInstance(todos, list)
		self.assertEqual(len(todos), 3)

	def test_count_records(self):
		"""Count should return number of matching records."""
		for i in range(5):
			frappe.get_doc(
				{
					"doctype": "ToDo",
					"description": f"RC Query Count {i}",
					"status": "Open",
				}
			).insert(ignore_permissions=True)

		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "QUERY-1",
			},
			{
				"action_id": "QUERY-1",
				"action_type": "Query Records",
				"action_label": "Count Todos",
				"is_enabled": 1,
				"reference_doctype": "ToDo",
				"operation": "Count",
				"config": json.dumps({"filters": {"description": ["like", "RC Query Count%"]}}),
				"return_variable": "count",
				"return_type": "Integer",
				"next_step_if_true": "END",
			},
			{
				"action_id": "END",
				"action_type": "Stop",
				"operation": "Success",
				"action_label": "End",
				"is_enabled": 1,
			},
		]

		rule_doc = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "RC Query Count",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"priority": 10,
				"actions": actions,
			}
		)
		rule_doc.insert(ignore_permissions=True)

		engine = RuleEngine(rule_doc)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		result = engine.execute(doc)

		count = result.get("vars", {}).get("count", 0)
		self.assertEqual(count, 5)


class TestWaitAction(FrappeTestCase):
	"""Test Wait action type."""

	def setUp(self):
		super().setUp()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC Wait%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC Wait%"]})

	def tearDown(self):
		super().tearDown()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC Wait%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC Wait%"]})

	def test_wait_action_execution(self):
		"""Wait should introduce delay during execution."""
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "WAIT-1",
			},
			{
				"action_id": "WAIT-1",
				"action_type": "Wait",
				"action_label": "Wait Short",
				"is_enabled": 1,
				"config": json.dumps({"wait_type": "Duration", "value": 0.01, "unit": "Seconds"}),
				"next_step_if_true": "END",
			},
			{
				"action_id": "END",
				"action_type": "Stop",
				"operation": "Success",
				"action_label": "End",
				"is_enabled": 1,
			},
		]

		rule_doc = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "RC Wait Test",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"priority": 10,
				"actions": actions,
			}
		)
		rule_doc.insert(ignore_permissions=True)

		engine = RuleEngine(rule_doc)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		start = time.time()
		engine.execute(doc)
		elapsed = time.time() - start

		# Should have waited at least 10ms
		self.assertGreaterEqual(elapsed, 0.01)


class TestSchedulerRule(FrappeTestCase):
	"""Test Scheduler Event trigger type."""

	def setUp(self):
		super().setUp()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC Sched%"]})
		frappe.db.delete("Rule", {"rule_name": ["like", "RC SchedSub%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC Sched%"]})

	def tearDown(self):
		super().tearDown()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC Sched%"]})
		frappe.db.delete("Rule", {"rule_name": ["like", "RC SchedSub%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC Sched%"]})

	def test_scheduler_rule_no_document_type_required(self):
		"""Scheduler rules should not require document_type."""
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "PROC-1",
			},
			{
				"action_id": "PROC-1",
				"action_type": "Process",
				"action_label": "Process",
				"is_enabled": 1,
				"process_name": "Validation",
				"operation": "value_in_range",
				"config": '{"field": "docstatus", "min_value": 0, "max_value": 0}',
				"on_error": "Stop",
				"next_step_if_true": "END",
			},
			{
				"action_id": "END",
				"action_type": "Stop",
				"operation": "Success",
				"action_label": "End",
				"is_enabled": 1,
			},
		]

		rule_doc = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "RC Sched Test",
				"document_type": None,
				"trigger_type": "Scheduler Event",
				"is_active": 1,
				"priority": 10,
				"actions": actions,
			}
		)

		# Should not raise validation error for missing document_type
		rule_doc.insert(ignore_permissions=True)
		self.assertTrue(rule_doc.name)


class TestAPIEndpoints(FrappeTestCase):
	"""Test API endpoints for RC compatibility."""

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		frappe.db.delete("Rule", {"rule_name": ["like", "RC API%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC API%"]})

	def tearDown(self):
		super().tearDown()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC API%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC API%"]})
		RuleCoordinator.clear_cache()

	def create_simple_rule(self, name):
		"""Create simple rule for API testing."""
		rule_doc = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": name,
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"priority": 10,
				"actions": [
					{
						"action_id": "root",
						"action_type": "Entry Action",
						"action_label": "Start",
						"is_enabled": 1,
						"next_step_if_true": "END",
					},
					{
						"action_id": "END",
						"action_type": "Stop",
						"operation": "Success",
						"action_label": "End",
						"is_enabled": 1,
					},
				],
			}
		)
		rule_doc.insert(ignore_permissions=True)
		return rule_doc

	def test_test_rule_returns_directly_from_engine(self):
		"""test_rule API should return directly from engine, not from DB log."""
		from flexirule.ruleflow.api import test_rule

		rule = self.create_simple_rule("RC API Test Direct")

		result = test_rule(rule.name, "ToDo", None, '{"doctype": "ToDo", "description": "API Test"}')

		self.assertTrue(result.get("success"))
		self.assertIn("execution_path", result)
		self.assertIsInstance(result.get("execution_path"), list)

	def test_validate_rule_document(self):
		"""validate_rule_document API should return validation result."""
		from flexirule.ruleflow.api import validate_rule_document

		payload = {
			"doctype": "Rule",
			"rule_name": "RC API Validation",
			"document_type": "ToDo",
			"trigger_type": "DocType Event",
			"trigger_event": "Validate",
			"actions": [
				{
					"action_id": "root",
					"action_type": "Entry Action",
					"action_label": "Start",
					"is_enabled": 1,
				},
			],
		}

		result = validate_rule_document(payload)

		self.assertIn("valid", result)
		self.assertIn("errors", result)

	def test_get_contract_dto(self):
		"""get_contract_dto API should return contract info."""
		from flexirule.ruleflow.api import get_contract_dto

		result = get_contract_dto()

		self.assertIn("action_type_contract", result)
		self.assertIn("trigger_type_contract", result)
		self.assertIn("release_disabled_action_types", result)


class TestRoleBasedSkip(FrappeTestCase):
	"""Test role-based skip functionality."""

	def setUp(self):
		super().setUp()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC Role%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC Role%"]})

	def tearDown(self):
		super().tearDown()
		frappe.db.delete("Rule", {"rule_name": ["like", "RC Role%"]})
		frappe.db.delete("Rule Execution Log", {"rule": ["like", "RC Role%"]})
		frappe.set_user("Administrator")

	def test_skip_for_roles(self):
		"""Rule should skip execution for users with specific roles."""
		actions = [
			{
				"action_id": "root",
				"action_type": "Entry Action",
				"action_label": "Start",
				"is_enabled": 1,
				"next_step_if_true": "END",
			},
			{
				"action_id": "END",
				"action_type": "Stop",
				"operation": "Success",
				"action_label": "End",
				"is_enabled": 1,
			},
		]

		rule_doc = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "RC Role Skip",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"is_active": 1,
				"priority": 10,
				"skip_for_roles": [{"role": "System Manager"}],
				"actions": actions,
			}
		)
		rule_doc.insert(ignore_permissions=True)

		engine = RuleEngine(rule_doc)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		engine.execute(doc)

		# Should have skipped due to System Manager role
		skip_logged = any("Skipping rule execution" in e.get("message", "") for e in engine.execution_log)
		self.assertTrue(skip_logged)


if __name__ == "__main__":
	unittest.main()
