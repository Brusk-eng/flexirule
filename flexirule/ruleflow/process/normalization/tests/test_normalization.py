# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestNormalizationProcess(FrappeTestCase):
	"""Test normalization process methods"""

	def setUp(self):
		self.process = frappe.get_doc("Process", "Normalization")

	def test_transform_value_lowercase(self):
		"""Test lowercase transformation"""
		doc = frappe.get_doc({"doctype": "ToDo", "description": "HELLO WORLD"})
		context = {"doc": doc, "vars": {}}
		result = self.process.execute(
			context,
			func="transform_value",
			config={"source_field": "description", "transformations": ["lowercase"]},
		)

		self.assertEqual(result, "hello world")
		# Document remains unchanged as it's a pure function now
		self.assertEqual(doc.description, "HELLO WORLD")

	def test_transform_value_multiple(self):
		"""Test multiple transformations"""
		doc = frappe.get_doc({"doctype": "ToDo", "description": "  HELLO   WORLD  "})
		context = {"doc": doc, "vars": {}}
		result = self.process.execute(
			context,
			func="transform_value",
			config={
				"source_field": "description",
				"transformations": ["trim", "lowercase", "remove_extra_spaces"],
			},
		)

		self.assertEqual(result, "hello world")
