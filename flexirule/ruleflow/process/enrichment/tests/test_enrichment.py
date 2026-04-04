# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestEnrichmentProcess(FrappeTestCase):
	"""Test enrichment process methods"""

	def setUp(self):
		self.process = frappe.get_doc("Process", "Enrichment")

	def test_calculate_value(self):
		"""Test formula calculation"""
		doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		context = {"doc": doc, "vars": {}}
		result = self.process.execute(
			context,
			func="calculate_value",
			config={"target_field": "priority", "formula": '"High"'},
		)

		self.assertEqual(result, {"priority": "High"})
		# Document remains unchanged as it's a pure function now
		self.assertNotEqual(doc.priority, "High")
