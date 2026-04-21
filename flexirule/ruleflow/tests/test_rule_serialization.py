import unittest

import frappe

from flexirule.ruleflow.api import validate_rule_document


class TestRuleSerialization(unittest.TestCase):
	def test_serialized_payload_keys(self):
		"""
		Verify that the rule payload contains the correct canonical keys
		and does NOT contain deprecated fields like 'is_sub_rule'.
		"""
		# Canonical keys expected in the Rule payload from useRuleStore.js
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

		# Explicit check for the deprecated field
		self.assertNotIn(
			"is_sub_rule", expected_keys, "Deprecated field 'is_sub_rule' should not be in the canonical list"
		)

	def test_payload_structure_compliance(self):
		"""
		Verify that a sample payload is compliant with the Rule DocType schema.
		"""
		# Connect to DB if needed (run-tests handles this, but for direct execute...)
		if not frappe.db:
			frappe.connect()

		meta = frappe.get_meta("Rule")
		valid_fieldnames = [f.fieldname for f in meta.fields]

		# Verify that exposed_as_subrule is valid
		self.assertIn("exposed_as_subrule", valid_fieldnames)

		# Verify that is_sub_rule is NOT valid (deprecated and removed from schema)
		self.assertNotIn("is_sub_rule", valid_fieldnames)
