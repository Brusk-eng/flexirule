# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Unit tests for FlexiRule Process Methods
"""

import unittest

import frappe

from flexirule.ruleflow.core.action_handlers import HandlerRegistry


class TestValidationMethods(unittest.TestCase):
	"""Test validation process methods using the new Process architecture"""

	def setUp(self):
		"""Setup test document and context"""
		self.doc = frappe.get_doc({"doctype": "ToDo", "description": "Test ToDo"})
		self.context = {"doc": self.doc, "vars": {}}
		self.process = frappe.get_doc("Process", "Validation")

	def test_validate_required_fields_success(self):
		"""Test numeric range validation passes for docstatus"""

		result = self.process.execute(
			self.context,
			func="value_in_range",
			config={"field": "docstatus", "min_value": 0, "max_value": 0},
		)

		self.assertTrue(result)

	def test_validate_required_fields_failure(self):
		"""Test numeric range validation fails for non-numeric source field"""

		with self.assertRaises(frappe.ValidationError):
			self.process.execute(
				self.context,
				func="value_in_range",
				config={"field": "description", "min_value": 1},
			)


class TestEnrichmentMethods(unittest.TestCase):
	"""Test enrichment process methods using the new Process architecture"""

	def setUp(self):
		"""Setup test data"""
		self.doc = frappe.get_doc({"doctype": "ToDo", "description": "Test"})
		self.context = {"doc": self.doc, "vars": {}}
		self.process = frappe.get_doc("Process", "Enrichment")

	def test_calculate_value(self):
		"""Test field calculation using Safe Eval"""
		self.doc.description = "Test"

		result = self.process.execute(
			self.context,
			func="calculate_value",
			config={"target_field": "priority", "formula": '"High"'},
		)

		self.assertEqual(result, "High")
		self.assertEqual(self.doc.priority, "High")


class TestNotificationMethods(unittest.TestCase):
	"""Test native replacements for the removed Notification process."""

	def setUp(self):
		"""Setup test data"""
		frappe.set_user("Administrator")
		self.doc = frappe.get_doc({"doctype": "ToDo", "description": "Test Notification"})
		self.doc.insert(ignore_permissions=True)
		self.context = {"doc": self.doc, "vars": {}}
		self.handler = HandlerRegistry.get("Document Action")
		self.engine = frappe._dict()

	def tearDown(self):
		"""Cleanup"""
		frappe.db.rollback()

	def test_add_comment(self):
		"""Test comment creation through Document Action."""
		action = frappe._dict(
			{
				"operation": "Add Comment",
				"reference_doctype": "Comment",
				"config": '{"comment_text":"Test comment from rule"}',
				"skip_permissions": 1,
				"permission_audit_reason": "Automated Test",
				"next_step_if_true": None,
			}
		)
		assert self.handler is not None
		result, _ = self.handler.execute(action, self.context, self.engine)

		self.assertIsNotNone(result.get("name"))

		# Verify comment was created
		comment = frappe.get_doc("Comment", result["name"])
		self.assertEqual(comment.content, "Test comment from rule")

	def test_create_todo(self):
		"""Test linked ToDo creation through Document Action."""
		action = frappe._dict(
			{
				"operation": "Create ToDo",
				"reference_doctype": "ToDo",
				"config": '{"assigned_to":"Administrator","description":"Follow up {{ doc.name }}","priority":"High"}',
				"skip_permissions": 1,
				"permission_audit_reason": "Automated Test",
				"next_step_if_true": None,
			}
		)
		assert self.handler is not None
		result, _ = self.handler.execute(action, self.context, self.engine)

		todo = frappe.get_doc("ToDo", result["name"])
		self.assertEqual(todo.allocated_to, "Administrator")
		self.assertEqual(todo.priority, "High")
		self.assertEqual(todo.reference_name, self.doc.name)


def run_tests():
	"""Helper function to run all method tests"""
	suite = unittest.TestSuite()
	suite.addTest(unittest.makeSuite(TestValidationMethods))
	suite.addTest(unittest.makeSuite(TestEnrichmentMethods))
	suite.addTest(unittest.makeSuite(TestNotificationMethods))

	runner = unittest.TextTestRunner()
	runner.run(suite)


if __name__ == "__main__":
	unittest.main()
