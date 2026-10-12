# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.utils.frappe_query_compat import (
	QUERY_CAPABILITIES,
	FrappeQueryCapabilities,
	detect_query_capabilities,
	execute_query,
)


class TestFrappeQueryCompat(FrappeTestCase):
	def test_capabilities_are_detected_from_installed_engine_signature(self):
		from inspect import signature

		expected = "ignore_permissions" in signature(frappe.database.query.Engine.get_query).parameters
		self.assertEqual(QUERY_CAPABILITIES.supports_ignore_permissions, expected)

	def test_capability_detection_fails_closed_when_signature_is_unavailable(self):
		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.signature",
			side_effect=RuntimeError("signature unavailable"),
		):
			capabilities = detect_query_capabilities()

		self.assertFalse(capabilities.supports_ignore_permissions)

	def test_capability_detection_is_not_used_on_query_execution_hot_path(self):
		query = MagicMock()
		query.run.return_value = [{"name": "Administrator"}]

		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.signature",
			side_effect=AssertionError("signature inspection must not run during execution"),
		):
			with patch(
				"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
				FrappeQueryCapabilities(supports_ignore_permissions=True),
			):
				with patch("frappe.qb.get_query", return_value=query) as get_query:
					result = execute_query("User", {"fields": ["name"]}, ignore_permissions=False)

		self.assertEqual(result, [{"name": "Administrator"}])
		self.assertIs(get_query.call_args.kwargs["ignore_permissions"], False)

	def test_native_permission_flag_is_passed_through_when_supported(self):
		query = MagicMock()
		query.run.return_value = [{"name": "Administrator"}]

		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(supports_ignore_permissions=True),
		):
			with patch("frappe.qb.get_query", return_value=query) as get_query:
				result = execute_query(
					"User", {"fields": ["name"], "limit": 10, "offset": 2}, ignore_permissions=False
				)

		self.assertEqual(result, [{"name": "Administrator"}])
		self.assertIs(get_query.call_args.kwargs["ignore_permissions"], False)
		self.assertEqual(get_query.call_args.kwargs["limit"], 10)
		self.assertEqual(get_query.call_args.kwargs["offset"], 2)

	def test_legacy_api_never_falls_back_to_get_list(self):
		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(supports_ignore_permissions=False),
		):
			with patch("frappe.get_list") as get_list:
				with patch("frappe.qb.get_query") as get_query:
					with self.assertRaises(frappe.ValidationError):
						execute_query("User", {"fields": ["name"], "limit": 10}, ignore_permissions=False)

		get_list.assert_not_called()
		get_query.assert_not_called()

	def test_legacy_api_uses_get_query_without_unsupported_permission_keyword(self):
		query = MagicMock()
		query.run.return_value = [{"name": "Administrator"}]
		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(supports_ignore_permissions=False),
		):
			with patch("frappe.get_list") as get_list:
				with patch("frappe.qb.get_query", return_value=query) as get_query:
					result = execute_query("User", {"fields": ["name"]}, ignore_permissions=True)

		self.assertEqual(result, [{"name": "Administrator"}])
		self.assertNotIn("ignore_permissions", get_query.call_args.kwargs)
		get_list.assert_not_called()

	def test_legacy_nested_filter_groups_compile_to_native_criterion(self):
		query = MagicMock()
		query.run.return_value = [{"name": "Administrator"}]
		filters = [
			["User", "email", "like", "%@example.com"],
			"and",
			[
				["User", "enabled", "=", 1],
				"or",
				["User", "user_type", "=", "System User"],
			],
		]
		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(supports_ignore_permissions=False),
		):
			with patch("frappe.qb.get_query", return_value=query) as get_query:
				execute_query("User", {"fields": ["name"], "filters": filters}, ignore_permissions=True)

		compiled = get_query.call_args.kwargs["filters"]
		self.assertIn(" AND ", compiled.get_sql().upper())
		self.assertIn(" OR ", compiled.get_sql().upper())

	def test_legacy_filter_compiler_rejects_mixed_connectors_at_same_level(self):
		filters = [
			["enabled", "=", 1],
			"or",
			["user_type", "=", "System User"],
			"and",
			["email", "like", "%@example.com"],
		]
		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(supports_ignore_permissions=False),
		):
			with patch("frappe.qb.get_query") as get_query:
				with self.assertRaises(frappe.ValidationError):
					execute_query("User", {"filters": filters}, ignore_permissions=True)
		get_query.assert_not_called()

	def test_legacy_logical_groups_reject_linked_and_child_field_leaves(self):
		filters = [
			["User", "enabled", "=", 1],
			"or",
			["User", "roles.role", "=", "System Manager"],
		]
		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(supports_ignore_permissions=False),
		):
			with patch("frappe.qb.get_query") as get_query:
				with self.assertRaises(frappe.ValidationError):
					execute_query("User", {"filters": filters}, ignore_permissions=True)
		get_query.assert_not_called()

	def test_literal_or_as_filter_value_is_not_a_connector(self):
		query = MagicMock()
		query.run.return_value = []
		filters = [["email", "=", "or"]]
		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(supports_ignore_permissions=False),
		):
			with patch("frappe.qb.get_query", return_value=query) as get_query:
				execute_query("User", {"filters": filters}, ignore_permissions=True)

		self.assertEqual(get_query.call_args.kwargs["filters"], filters)

	def test_bare_legacy_filter_leaf_is_wrapped_as_a_filter_row(self):
		query = MagicMock()
		query.run.return_value = []
		filters = ["User", "email", "=", "person@example.com"]
		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(supports_ignore_permissions=False),
		):
			with patch("frappe.qb.get_query", return_value=query) as get_query:
				execute_query("User", {"filters": filters}, ignore_permissions=True)

		self.assertEqual(get_query.call_args.kwargs["filters"], [filters])

	def test_explicit_limit_and_offset_are_forwarded_without_rewriting(self):
		query = MagicMock()
		query.run.return_value = []
		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(supports_ignore_permissions=False),
		):
			with patch("frappe.qb.get_query", return_value=query) as get_query:
				execute_query(
					"User", {"fields": ["name"], "limit": 250000, "offset": 500000}, ignore_permissions=True
				)

		self.assertEqual(get_query.call_args.kwargs["limit"], 250000)
		self.assertEqual(get_query.call_args.kwargs["offset"], 500000)
