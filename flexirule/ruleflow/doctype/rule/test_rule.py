# Copyright (c) 2026, Abdo Ruzaqi and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.api import validate_rule_document


class TestRule(FrappeTestCase):
	def setUp(self):
		self.rule_name = "Test Validation Rule"
		if frappe.db.exists("Rule", self.rule_name):
			frappe.delete_doc("Rule", self.rule_name)

	def test_set_value_validation_gap(self):
		"""Verify that non-existent fields in Set Value action are blocked"""
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": self.rule_name,
				"document_type": "User",
				"trigger_type": "DocType Event",
				"trigger_event": "Before Save",
				"actions": [
					{
						"action_label": "Invalid Field Update",
						"action_type": "Set Value",
						"target_field": "this_field_definitely_does_not_exist",
						"value_template": "test",
					}
				],
			}
		)

		with self.assertRaisesRegex(frappe.ValidationError, "does not exist on DocType"):
			rule.validate()

	def test_consolidated_terminal_stop_success(self):
		"""Verify Stop Success action saves correctly without template"""
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": self.rule_name,
				"document_type": "User",
				"trigger_type": "DocType Event",
				"trigger_event": "Before Save",
				"actions": [{"action_label": "Stop Success", "action_type": "Stop", "operation": "Success"}],
			}
		)
		# Should not throw
		rule.validate()

	def test_consolidated_terminal_stop_error(self):
		"""Verify Stop Error action requires value_template"""
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": self.rule_name,
				"document_type": "User",
				"trigger_type": "DocType Event",
				"trigger_event": "Before Save",
				"actions": [
					{
						"action_label": "Stop Error",
						"action_type": "Stop",
						"operation": "Error",
						"value_template": "",  # Empty
					}
				],
			}
		)

		with self.assertRaisesRegex(frappe.ValidationError, "requires field 'value_template'"):
			rule.validate()

		# Build a fresh doc with template and it should pass
		valid_rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": f"{self.rule_name} With Template",
				"document_type": "User",
				"trigger_type": "DocType Event",
				"trigger_event": "Before Save",
				"actions": [
					{
						"action_label": "Stop Error",
						"action_type": "Stop",
						"operation": "Error",
						"value_template": "Critical Error!",
					}
				],
			}
		)
		valid_rule.validate()

	def test_service_matches_form_validation_for_missing_condition(self):
		"""API precheck and form validation should reject the same invalid rule definition."""
		payload = {
			"doctype": "Rule",
			"rule_name": "Rule Missing Condition",
			"document_type": "User",
			"trigger_type": "DocType Event",
			"trigger_event": "Before Save",
			"actions": [
				{
					"action_label": "Missing Condition",
					"action_type": "Condition",
					"action_id": "condition_1",
				}
			],
		}

		api_result = validate_rule_document(payload)
		self.assertFalse(api_result["valid"])
		self.assertTrue(
			any("is a Condition but no condition is defined" in error for error in api_result["errors"])
		)

		rule = frappe.get_doc(payload)
		with self.assertRaisesRegex(frappe.ValidationError, "is a Condition but no condition is defined"):
			rule.validate()

	def test_service_matches_form_validation_for_async_output_mapping(self):
		"""Async output mapping should fail consistently through API and form validation."""
		payload = {
			"doctype": "Rule",
			"rule_name": "Rule Async Output Mapping",
			"document_type": "User",
			"trigger_type": "DocType Event",
			"trigger_event": "Before Save",
			"actions": [
				{
					"action_label": "Async Query",
					"action_type": "Query Records",
					"action_id": "query_1",
					"reference_doctype": "User",
					"operation": "Query List",
					"is_async": 1,
					"config": '{"output_mapping":{"rows":"vars.rows"}}',
				}
			],
		}

		api_result = validate_rule_document(payload)
		self.assertFalse(api_result["valid"])
		self.assertTrue(
			any("cannot use Output Mapping with Async enabled" in error for error in api_result["errors"])
		)

		rule = frappe.get_doc(payload)
		with self.assertRaisesRegex(frappe.ValidationError, "cannot use Output Mapping with Async enabled"):
			rule.validate()
