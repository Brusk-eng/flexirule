import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.api import validate_rule_document


class TestRuleSerialization(FrappeTestCase):
	def test_serialized_payload_keys(self):
		"""
		Verify that the rule payload contains the correct canonical keys
		and does NOT contain deprecated fields like 'is_sub_rule'.
		"""
		# Canonical keys expected in the Rule payload from useRuleStore.js
		payload = {
			"rule_name": "SERIALIZATION_TEST",
			"is_active": 0,
			"trigger_type": "DocType Event",
			"document_type": "ToDo",
			"trigger_event": "Validate",
			"trigger_condition": None,
			"exposed_as_subrule": 0,
			"execution_mode": "Synchronous",
			"max_execution_time": 30,
			"debug_mode": 0,
			"description": "",
			"priority": "10",
			"skip_for_roles": [],
			"permissions": [],
			"actions": [],
			"visual_data": "{}",
		}
		expected_keys = [
			"rule_name",
			"is_active",
			"trigger_type",
			"document_type",
			"trigger_event",
			"trigger_condition",
			"exposed_as_subrule",
			"execution_mode",
			"max_execution_time",
			"debug_mode",
			"description",
			"priority",
			"skip_for_roles",
			"permissions",
			"actions",
			"visual_data",
		]

		self.assertEqual(set(payload), set(expected_keys))
		self.assertNotIn("is_sub_rule", payload)

	def test_payload_structure_compliance(self):
		"""
		Verify that a sample payload is compliant with the Rule DocType schema.
		"""
		meta = frappe.get_meta("Rule")
		valid_fieldnames = [f.fieldname for f in meta.fields]

		# Verify that exposed_as_subrule is valid
		self.assertIn("exposed_as_subrule", valid_fieldnames)

		# Verify that is_sub_rule is NOT valid (deprecated and removed from schema)
		self.assertNotIn("is_sub_rule", valid_fieldnames)
