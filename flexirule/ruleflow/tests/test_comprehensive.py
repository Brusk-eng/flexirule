# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Comprehensive Unit Test Suite for FlexiRule Rule Engine
"""

import json
import unittest
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.doctype.process.process import Process


def create_test_rule(name, doctype="ToDo", event="Validate", actions=None):
	"""Helper to create test rules"""
	if frappe.db.exists("Rule", name):
		return frappe.get_doc("Rule", name)

	rule = frappe.get_doc(
		{
			"doctype": "Rule",
			"rule_name": name,
			"document_type": doctype,
			"trigger_type": "DocType Event",
			"trigger_event": event,
			"is_active": 1,
			"priority": "0" if event == "Manual" else "10",
			"max_execution_time": 30,
		}
	)

	if actions:
		for action in actions:
			rule.append("actions", action)

	rule.insert(ignore_permissions=True)
	return rule


class TestRuleEngine(FrappeTestCase):
	"""Test RuleEngine class"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

	def test_engine_initialization(self):
		"""Test engine initializes correctly"""
		from flexirule.ruleflow.core.engine import RuleEngine

		rule = create_test_rule("Test Engine Init")
		engine = RuleEngine(rule)

		self.assertEqual(engine.rule.name, "Test Engine Init")
		self.assertIsInstance(engine.execution_log, list)

	def test_engine_validates_disabled_rule(self):
		"""Test engine rejects disabled rules"""
		from flexirule.ruleflow.core.engine import RuleEngine
		from flexirule.ruleflow.core.exceptions import RuleDisabledError

		rule = create_test_rule("Test Disabled Rule")
		rule.is_active = 0
		rule.save()

		engine = RuleEngine(rule)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})

		with self.assertRaises(RuleDisabledError):
			engine.execute(doc)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()


class TestNormalizationMethods(FrappeTestCase):
	"""Test normalization process methods"""

	def setUp(self):
		self.process = frappe.get_doc("Process", "Normalization")

	def test_normalize_field_lowercase(self):
		"""Test lowercase transformation"""
		doc = frappe.get_doc({"doctype": "ToDo", "description": "HELLO WORLD"})
		context = {"doc": doc, "vars": {}}
		result = self.process.execute(
			context,
			func="normalize_field",
			config={"source_field": "description", "transformations": ["lowercase"]},
		)

		self.assertEqual(result, "hello world")
		self.assertEqual(doc.description, "hello world")

	def test_normalize_field_multiple(self):
		"""Test multiple transformations"""
		doc = frappe.get_doc({"doctype": "ToDo", "description": "  HELLO   WORLD  "})
		context = {"doc": doc, "vars": {}}
		result = self.process.execute(
			context,
			func="normalize_field",
			config={
				"source_field": "description",
				"transformations": ["trim", "lowercase", "remove_extra_spaces"],
			},
		)

		self.assertEqual(result, "hello world")

	def test_normalize_field_to_context(self):
		"""Test normalizing to context"""
		doc = frappe.get_doc({"doctype": "ToDo", "description": "HELLO"})
		context = {"doc": doc, "vars": {}}

		self.process.execute(
			context,
			func="normalize_field_to_context",
			config={"source_field": "description", "transformations": ["lowercase"]},
		)

		self.assertEqual(doc.description, "HELLO")  # Not modified
		self.assertEqual(context["vars"]["normalized_description"], "hello")


class TestValidationMethods(FrappeTestCase):
	"""Test validation process methods"""

	def setUp(self):
		self.process = frappe.get_doc("Process", "Validation")

	def test_validate_required_fields_success(self):
		"""Test numeric range validation passes"""
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		context = {"doc": doc, "vars": {}}
		result = self.process.execute(
			context, func="value_in_range", config={"field": "docstatus", "min_value": 0, "max_value": 0}
		)
		self.assertTrue(result)

	def test_validate_required_fields_failure(self):
		"""Test numeric range validation fails"""
		doc = frappe.get_doc({"doctype": "ToDo", "description": ""})
		context = {"doc": doc, "vars": {}}

		with self.assertRaises(frappe.ValidationError):
			self.process.execute(
				context, func="value_in_range", config={"field": "description", "min_value": 1}
			)


class TestEnrichmentMethods(FrappeTestCase):
	"""Test enrichment process methods"""

	def setUp(self):
		self.process = frappe.get_doc("Process", "Enrichment")

	def test_calculate_value(self):
		"""Test formula calculation"""
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		context = {"doc": doc, "vars": {}}
		self.process.execute(
			context,
			func="calculate_value",
			config={"target_field": "priority", "formula": '"High"'},
		)

		self.assertEqual(doc.priority, "High")


class TestDeduplicationMethods(FrappeTestCase):
	"""Test deduplication process methods"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

	def test_find_matching_records_with_exact_fields(self):
		"""Test exact duplicate detection through the unified matcher."""
		process = frappe.get_doc("Process", "Deduplication")

		existing = frappe.get_doc({"doctype": "ToDo", "description": "Duplicate Test Item"}).insert(
			ignore_permissions=True
		)

		new_doc = frappe.get_doc({"doctype": "ToDo", "description": "Duplicate Test Item"})
		new_doc.name = "temp-new-doc"
		context = {"doc": new_doc, "vars": {}}

		result = process.execute(
			context,
			func="find_matching_records",
			config={"fields": ["description"]},
		)
		self.assertTrue(result["has_match"])
		self.assertEqual(result["match_count"], 1)
		self.assertEqual(result["best_match"]["name"], existing.name)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()


class TestNewTriggerEvents(FrappeTestCase):
	"""Test the newly added trigger events"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")

	def test_before_naming_trigger(self):
		"""Test 'Before Naming' trigger event"""
		from flexirule.ruleflow.core.coordinator import RuleCoordinator

		RuleCoordinator.clear_cache()

		# Create a rule that sets description 'Set by Naming' on Before Naming
		rule_name = "Test Before Naming"
		create_test_rule(
			rule_name,
			doctype="ToDo",
			event="Before Naming",
			actions=[
				{
					"action_id": "set_desc_naming",
					"action_type": "Set Value",
					"action_label": "Set Description",
					"target_field": "description",
					"value_template": "Set by Naming",
					"is_enabled": 1,
				}
			],
		)

		# Creating a doc triggers before_naming
		todo = frappe.get_doc({"doctype": "ToDo", "description": "Original"})
		todo.insert()

		self.assertEqual(todo.description, "Set by Naming")

	def test_on_change_trigger(self):
		"""Test 'On Change' trigger event"""
		from flexirule.ruleflow.core.coordinator import RuleCoordinator

		RuleCoordinator.clear_cache()

		todo = frappe.get_doc({"doctype": "ToDo", "description": "Original"}).insert()

		# On Change runs after the document is saved, so it should use
		# non-mutating actions such as notifications rather than Set Value.
		rule_name = "Test On Change"
		create_test_rule(
			rule_name,
			doctype="ToDo",
			event="On Change",
			actions=[
				{
					"action_id": "notify_change",
					"action_type": "Notify",
					"action_label": "Notify Change",
					"operation": "System Notification",
					"value_template": "Changed {{ doc.name }}",
					"config": '{"subject":"On Change {{ doc.name }}","for_user":"Administrator"}',
					"is_enabled": 1,
				}
			],
		)

		todo.description = "Something Else"
		todo.save()

		notification_name = frappe.db.get_value(
			"Notification Log",
			{
				"for_user": "Administrator",
				"subject": f"On Change {todo.name}",
			},
			"name",
			order_by="creation desc",
		)
		self.assertTrue(notification_name)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()


if __name__ == "__main__":
	unittest.main()
