# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestValidationProcess(FrappeTestCase):
	"""Test validation process methods"""

	def setUp(self):
		self.process = frappe.get_doc("Process", "Validation")

	def test_value_in_range_success(self):
		"""Test numeric range validation passes"""
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		context = {"doc": doc, "vars": {}}
		result = self.process.execute(
			context, func="value_in_range", config={"field": "docstatus", "min_value": 0, "max_value": 0}
		)
		self.assertTrue(result.get("is_valid"))

	def test_value_in_range_failure(self):
		"""Test numeric range validation fails"""
		doc = frappe.get_doc({"doctype": "ToDo", "description": "10"})
		context = {"doc": doc, "vars": {}}
		result = self.process.execute(
			context, func="value_in_range", config={"field": "description", "min_value": 11}
		)
		self.assertFalse(result.get("is_valid"))
		self.assertIn("must be at least 11", result.get("errors")[0])
