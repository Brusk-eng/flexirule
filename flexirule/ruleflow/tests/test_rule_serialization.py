import unittest
import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.api import validate_rule_document
from flexirule.ruleflow.tests.builder import RuleBuilder
from flexirule.ruleflow.utils.import_export import export_rule


class TestRuleSerialization(FrappeTestCase):
	def setUp(self):
		super().setUp()
		self._test_prefix = f"FRX_SER_{uuid.uuid4().hex[:8]}"

	def tearDown(self):
		if hasattr(self, "_test_prefix"):
			rules = frappe.get_all(
				"Rule", filters={"rule_name": ["like", f"{self._test_prefix}%"]}, fields=["name", "is_active"]
			)
			for r in rules:
				if r.is_active:
					frappe.db.set_value("Rule", r.name, "is_active", 0, update_modified=False)
			for r in rules:
				frappe.delete_doc("Rule", r.name, force=True, ignore_permissions=True)
		super().tearDown()

	def test_serialized_export_payload_keys_and_schema(self):
		"""
		Verify that export_rule() serializes a real Rule document with full
		canonical structure, actions, and without deprecated fields like 'is_sub_rule'.
		"""
		rule_name = f"{self._test_prefix}_Export_Test"
		rule = (
			RuleBuilder(rule_name)
			.document_type("ToDo")
			.active(0)
			.entry_action(next_step="stop_1")
			.stop("Success Stop", action_id="stop_1")
			.build()
		)

		exported = export_rule(rule.name)

		# Top-level envelope assertion
		self.assertEqual(exported.get("flexirule_version"), "1.0")
		self.assertIn("export_date", exported)
		self.assertIn("rule", exported)

		rule_payload = exported["rule"]
		expected_rule_keys = {
			"rule_name",
			"document_type",
			"trigger_event",
			"priority",
			"is_active",
			"actions",
		}
		self.assertTrue(expected_rule_keys.issubset(set(rule_payload.keys())))
		self.assertEqual(rule_payload["rule_name"], rule_name)
		self.assertEqual(len(rule_payload["actions"]), 2)

		# Verify action structure
		action_payload = rule_payload["actions"][0]
		self.assertIn("action_id", action_payload)
		self.assertIn("action_type", action_payload)
		self.assertIn("is_enabled", action_payload)

		# Ensure deprecated field 'is_sub_rule' is not in rule payload
		self.assertNotIn("is_sub_rule", rule_payload)

	def test_payload_structure_and_validation_service(self):
		"""
		Verify that validate_rule_document() validates serialized payload structure against
		the rule definition validation service.
		"""
		rule_name = f"{self._test_prefix}_Validate_Test"
		rule = (
			RuleBuilder(rule_name)
			.document_type("ToDo")
			.active(0)
			.entry_action(next_step="stop_1")
			.stop("Success Stop", action_id="stop_1")
			.build()
		)

		exported = export_rule(rule.name)
		validation = validate_rule_document(exported["rule"], mode="draft")

		self.assertTrue(validation.get("valid"))
		self.assertIsInstance(validation.get("errors"), list)
