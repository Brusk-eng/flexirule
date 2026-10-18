import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.api import validate_rule_document


class TestRuleSerialization(FrappeTestCase):
	def test_serialized_payload_keys(self):
		"""
		Verify that a serialized Rule document contains expected canonical fields
		and does NOT contain deprecated fields like 'is_sub_rule'.
		"""
		rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "TEST_SERIALIZATION_RULE",
				"document_type": "ToDo",
				"trigger_type": "DocType Event",
				"trigger_event": "Validate",
				"actions": [],
			}
		)
		doc_dict = rule.as_dict()

		self.assertIn("rule_name", doc_dict)
		self.assertIn("is_active", doc_dict)
		self.assertIn("exposed_as_subrule", doc_dict)
		self.assertNotIn("is_sub_rule", doc_dict)

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
