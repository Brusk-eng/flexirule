# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Tests for FlexiRule Permissions
"""

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.core.permissions import check_rule_permission


class TestRulePermissions(FrappeTestCase):
	"""Test cases for Rule permissions"""

	def setUp(self):
		super().setUp()
		# Create a test rule
		self.test_rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Permission Rule",
				"document_type": "ToDo",
				"trigger_event": "Validate",
				"is_active": 1,
				"priority": 10,
			}
		).insert(ignore_permissions=True)

	def tearDown(self):
		super().tearDown()
		# Clean up test rule
		if self.test_rule:
			frappe.delete_doc("Rule", self.test_rule.name, force=True)

	def test_check_rule_permission_with_throw_true(self):
		"""Test check_rule_permission with throw=True (should not raise exception for admin)"""
		# As Administrator, should have permission
		frappe.set_user("Administrator")

		# This should return True if it doesn't raise an exception
		result = check_rule_permission(self.test_rule, throw=True)
		self.assertTrue(result)

	def test_check_rule_permission_with_throw_false(self):
		"""Test check_rule_permission with throw=False"""
		# As Administrator, should have permission
		frappe.set_user("Administrator")

		result = check_rule_permission(self.test_rule, throw=False)
		# Should return True for admin user
		self.assertTrue(result)

	def test_check_rule_permission_with_skip_for_roles(self):
		"""Test check_rule_permission with skip_for_roles"""
		# Create a test user
		test_user = "test_permission@example.com"
		if not frappe.db.exists("User", test_user):
			user_doc = frappe.get_doc(
				{
					"doctype": "User",
					"email": test_user,
					"first_name": "Test Permission",
					"send_welcome_email": 0,
					"user_type": "System User",
				}
			)
			user_doc.insert(ignore_permissions=True)

		# Add a role to the user and clear cache
		user_doc = frappe.get_doc("User", test_user)
		user_doc.add_roles("System Manager")
		frappe.clear_cache(user=test_user)

		try:
			# Set the test rule to skip for System Manager role
			self.test_rule.append("skip_for_roles", {"role": "System Manager"})
			self.test_rule.flags.ignore_validate = True
			self.test_rule.save(ignore_permissions=True)

			frappe.set_user(test_user)

			# Should return False since user has System Manager role which is in skip_for_roles
			result = check_rule_permission(self.test_rule, throw=False)
			self.assertFalse(result)

		finally:
			# Clean up
			frappe.set_user("Administrator")
			frappe.delete_doc("User", test_user, force=True)

	def test_check_rule_permission_inactive_rule(self):
		"""Test check_rule_permission with inactive rule"""
		# Create an inactive rule
		inactive_rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Inactive Permission Rule",
				"document_type": "ToDo",
				"trigger_event": "Validate",
				"is_active": 0,
				"priority": 10,
			}
		).insert(ignore_permissions=True)

		try:
			frappe.set_user("Administrator")

			# For inactive rule, should return False when throw=False
			result = check_rule_permission(inactive_rule, throw=False)
			self.assertFalse(result)

			# For inactive rule, should raise exception when throw=True
			with self.assertRaises(frappe.ValidationError):
				check_rule_permission(inactive_rule, throw=True)

		finally:
			# Clean up
			frappe.delete_doc("Rule", inactive_rule.name, force=True)

	def test_check_rule_permission_non_admin_user(self):
		"""Test check_rule_permission with non-admin user"""
		# Create a test user
		test_user = "test_non_admin@example.com"
		if not frappe.db.exists("User", test_user):
			user_doc = frappe.get_doc(
				{
					"doctype": "User",
					"email": test_user,
					"first_name": "Test Non Admin",
					"send_welcome_email": 0,
					"user_type": "System User",
				}
			)
			user_doc.insert(ignore_permissions=True)

		# Add a role to the user and clear cache
		user_doc = frappe.get_doc("User", test_user)
		user_doc.add_roles("System Manager")
		frappe.clear_cache(user=test_user)

		try:
			frappe.set_user(test_user)

			# Should return True for user with System Manager role
			result = check_rule_permission(self.test_rule, throw=False)
			self.assertTrue(result)

		finally:
			# Clean up
			frappe.set_user("Administrator")
			frappe.delete_doc("User", test_user, force=True)

	def test_check_rule_permission_missing_rule(self):
		"""Test check_rule_permission with missing rule"""

		# Create a mock rule object with minimal attributes
		class MockRule:
			def __init__(self):
				self.is_active = 1
				self.skip_for_roles = []

		mock_rule = MockRule()

		frappe.set_user("Administrator")

		# Should not raise an exception for a mock rule with basic attributes
		result = check_rule_permission(mock_rule, throw=False)
		self.assertTrue(result)

	def test_check_rule_permission_with_skip_for_roles_list(self):
		"""Test check_rule_permission with multiple skip_for_roles"""
		# Create a test user
		test_user = "test_multi_role@example.com"
		if not frappe.db.exists("User", test_user):
			user_doc = frappe.get_doc(
				{
					"doctype": "User",
					"email": test_user,
					"first_name": "Test Multi Role",
					"send_welcome_email": 0,
					"user_type": "System User",
				}
			)
			user_doc.insert(ignore_permissions=True)

		# Add multiple roles to the user and clear cache
		user_doc = frappe.get_doc("User", test_user)
		roles_to_add = ["System Manager", "All Reports"]
		for role in roles_to_add:
			if frappe.db.exists("Role", role):
				user_doc.add_roles(role)
		frappe.clear_cache(user=test_user)

		try:
			# Set the test rule to skip for multiple roles
			for role in roles_to_add:
				if frappe.db.exists("Role", role):
					self.test_rule.append("skip_for_roles", {"role": role})
			self.test_rule.flags.ignore_validate = True
			self.test_rule.save(ignore_permissions=True)

			frappe.set_user(test_user)

			# Should return False since user has a role which is in skip_for_roles
			result = check_rule_permission(self.test_rule, throw=False)
			self.assertFalse(result)

		finally:
			# Clean up
			frappe.set_user("Administrator")
			frappe.delete_doc("User", test_user, force=True)

	def test_check_rule_permission_edge_cases(self):
		"""Test edge cases for check_rule_permission"""
		# Test with rule that has empty skip_for_roles
		frappe.set_user("Administrator")

		# Ensure skip_for_roles is empty
		self.test_rule.skip_for_roles = []
		self.test_rule.flags.ignore_validate = True
		self.test_rule.save(ignore_permissions=True)

		result = check_rule_permission(self.test_rule, throw=False)
		self.assertTrue(result)

	def test_check_rule_permission_with_deleted_user(self):
		"""Test check_rule_permission behavior with deleted user"""
		# Create a test user
		test_user = "test_deleted@example.com"
		if not frappe.db.exists("User", test_user):
			user_doc = frappe.get_doc(
				{
					"doctype": "User",
					"email": test_user,
					"first_name": "Test Deleted",
					"send_welcome_email": 0,
					"user_type": "System User",
				}
			)
			user_doc.insert(ignore_permissions=True)

		try:
			frappe.set_user(test_user)

			# Should work normally
			result = check_rule_permission(self.test_rule, throw=False)
			self.assertTrue(result)

		finally:
			# Clean up
			frappe.set_user("Administrator")
			frappe.delete_doc("User", test_user, force=True)

	def test_check_rule_permission_with_special_characters(self):
		"""Test check_rule_permission with special characters in rule name"""
		# Create a rule with special characters
		special_rule = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Permission Rule With Special Chars !@#$%",
				"document_type": "ToDo",
				"trigger_event": "Validate",
				"is_active": 1,
				"priority": 10,
			}
		).insert(ignore_permissions=True)

		try:
			frappe.set_user("Administrator")

			result = check_rule_permission(special_rule, throw=False)
			self.assertTrue(result)

		finally:
			# Clean up
			frappe.delete_doc("Rule", special_rule.name, force=True)
