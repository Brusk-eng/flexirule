# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Tests for FlexiRule Rule Engine
"""

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
						"operation": "required_fields",
						"config": '{"fields": ["description"]}',
						"on_error": "Stop",
					}
				],
			}
		)

		engine = RuleEngine(rule_doc)

		# 1. Test success (description present)
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		engine.execute(doc)

		# Verify execution trace
		trace = [t for t in engine.path_trace if t["type"] == "Process"]
		self.assertTrue(len(trace) > 0)
		self.assertEqual(trace[0]["action"], "Validation Process")

		# 2. Test failure (description missing)
		doc_fail = frappe.get_doc({"doctype": "ToDo", "description": ""})
		with self.assertRaises(frappe.ValidationError):
			engine.execute(doc_fail)


class TestValidationMethods(FrappeTestCase):
	"""Test validation process methods using the Engine logic"""

	def test_validate_required_fields_pass(self):
		"""Test required fields validation passes"""
		process = frappe.get_doc("Process", "Validation")
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		context = {"doc": doc, "vars": {}}
		result = process.execute(context, func="required_fields", config={"fields": ["description"]})
		self.assertTrue(result)

	def test_validate_required_fields_fail(self):
		"""Test required fields validation fails"""
		process = frappe.get_doc("Process", "Validation")
		doc = frappe.get_doc({"doctype": "ToDo", "description": ""})
		context = {"doc": doc, "vars": {}}

		with self.assertRaises(frappe.ValidationError):
			process.execute(context, func="required_fields", config={"fields": ["description"]})


class TestEnrichmentMethods(FrappeTestCase):
	"""Test enrichment process methods using the Engine logic"""

	def test_set_value(self):
		"""Test field value setting"""
		process = frappe.get_doc("Process", "Enrichment")
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		context = {"doc": doc, "vars": {}}
		result = process.execute(context, func="set_value", config={"field": "priority", "value": "Medium"})

		self.assertEqual(doc.priority, "Medium")
		self.assertEqual(result, "Medium")

	def test_calculate_value(self):
		"""Test formula calculation"""
		process = frappe.get_doc("Process", "Enrichment")
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		context = {"doc": doc, "vars": {}}
		process.execute(
			context,
			func="calculate_value",
			config={"target_field": "priority", "formula": '"High"'},
		)

		self.assertEqual(doc.priority, "High")
