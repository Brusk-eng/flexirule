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
	def test_capabilities_are_detected_from_installed_engine(self):
		from inspect import signature

		expected = "ignore_permissions" in signature(frappe.database.query.Engine.get_query).parameters
		self.assertEqual(QUERY_CAPABILITIES.supports_ignore_permissions, expected)

	def test_capability_detection_tolerates_uninspectable_engine(self):
		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.signature",
			side_effect=ValueError("signature unavailable"),
		):
			with patch(
				"flexirule.ruleflow.utils.frappe_query_compat.getsource",
				side_effect=OSError("source unavailable"),
			):
				capabilities = detect_query_capabilities()

		self.assertFalse(capabilities.supports_ignore_permissions)
		self.assertFalse(capabilities.supports_logical_filter_groups)

	def test_capability_detection_is_not_used_on_hot_path(self):
		query = MagicMock()
		query.run.return_value = [{"name": "Administrator"}]

		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.signature",
			side_effect=AssertionError("signature inspection must not run during execution"),
		):
			with patch("frappe.qb.get_query", return_value=query):
				result = execute_query("User", {"fields": ["name"]}, ignore_permissions=True)

		self.assertEqual(result, [{"name": "Administrator"}])

	def test_native_permission_capability_is_passed_through(self):
		query = MagicMock()
		query.run.return_value = [{"name": "Administrator"}]

		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(
				supports_ignore_permissions=True,
				supports_logical_filter_groups=True,
			),
		):
			with patch("frappe.qb.get_query", return_value=query) as get_query:
				result = execute_query("User", {"fields": ["name"], "limit": 10, "offset": 2}, False)

		self.assertEqual(result, [{"name": "Administrator"}])
		self.assertIs(get_query.call_args.kwargs["ignore_permissions"], False)
		self.assertEqual(get_query.call_args.kwargs["limit"], 10)
		self.assertEqual(get_query.call_args.kwargs["offset"], 2)

	def test_legacy_permission_path_uses_native_permission_aware_get_list(self):
		rows = [{"name": "visible-user"}]
		filters = [["email", "=", "visible@example.com"]]

		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(
				supports_ignore_permissions=False,
				supports_logical_filter_groups=True,
			),
		):
			with patch("frappe.get_list", return_value=rows) as get_list:
				with patch("frappe.qb.get_query") as get_query:
					result = execute_query(
						"User",
						{"fields": ["name"], "filters": filters, "limit": 10, "offset": 2},
						ignore_permissions=False,
					)

		self.assertEqual(result, rows)
		get_list.assert_called_once_with(
			"User",
			fields=["name"],
			filters=filters,
			or_filters=[],
			order_by=None,
			group_by=None,
			start=2,
			page_length=10,
			distinct=False,
			ignore_permissions=False,
		)
		get_query.assert_not_called()

	def test_legacy_permission_fallback_maps_supported_nested_or_group(self):
		rows = [{"name": "visible-user"}]
		filters = [
			["User", "email", "like", "%@example.com"],
			"and",
			[["User", "enabled", "=", 1], "or", ["User", "user_type", "=", "System User"]],
		]
		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(
				supports_ignore_permissions=False,
				supports_logical_filter_groups=False,
			),
		):
			with patch("frappe.get_list", return_value=rows) as get_list:
				result = execute_query(
					"User", {"fields": ["name"], "filters": filters}, ignore_permissions=False
				)

		self.assertEqual(result, rows)
		self.assertEqual(
			get_list.call_args.kwargs["filters"],
			[["User", "email", "like", "%@example.com"]],
		)
		self.assertEqual(
			get_list.call_args.kwargs["or_filters"],
			[["User", "enabled", "=", 1], ["User", "user_type", "=", "System User"]],
		)

	def test_legacy_permission_fallback_rejects_or_over_nested_conjunction(self):
		filters = [
			["enabled", "=", 1],
			"and",
			[["email", "=", "visible@example.com"], "or", [["user_type", "=", "System User"], "and", ["enabled", "=", 1]]],
		]
		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(
				supports_ignore_permissions=False,
				supports_logical_filter_groups=False,
			),
		):
			with patch("frappe.get_list") as get_list:
				with self.assertRaises(frappe.ValidationError):
					execute_query("User", {"fields": ["name"], "filters": filters}, ignore_permissions=False)
		get_list.assert_not_called()

	def test_explicit_ignore_permissions_is_supported_on_legacy_query_api(self):
		query = MagicMock()
		query.run.return_value = [{"name": "Administrator"}]

		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(
				supports_ignore_permissions=False,
				supports_logical_filter_groups=True,
			),
		):
			with patch("frappe.qb.get_query", return_value=query) as get_query:
				result = execute_query("User", {"fields": ["name"]}, ignore_permissions=True)

		self.assertEqual(result, [{"name": "Administrator"}])
		self.assertNotIn("ignore_permissions", get_query.call_args.kwargs)

	def test_legacy_logical_filters_are_compiled_to_native_criterion(self):
		query = MagicMock()
		query.run.return_value = [{"name": "Administrator"}]
		filters = [
			["enabled", "=", 1],
			"or",
			["email", "like", "%@example.com"],
		]

		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(
				supports_ignore_permissions=False,
				supports_logical_filter_groups=False,
			),
		):
			with patch("frappe.qb.get_query", return_value=query) as get_query:
				execute_query("User", {"filters": filters}, ignore_permissions=True)

		compiled = get_query.call_args.kwargs["filters"]
		self.assertNotIsInstance(compiled, list)
		self.assertIn(" OR ", compiled.get_sql().upper())

	def test_limit_and_offset_are_not_rewritten_on_legacy_path(self):
		query = MagicMock()
		query.run.return_value = []

		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(
				supports_ignore_permissions=False,
				supports_logical_filter_groups=True,
			),
		):
			with patch("frappe.qb.get_query", return_value=query) as get_query:
				execute_query(
					"User",
					{"fields": ["name"], "limit": 50, "offset": 100},
					ignore_permissions=True,
				)

		self.assertEqual(get_query.call_args.kwargs["limit"], 50)
		self.assertEqual(get_query.call_args.kwargs["offset"], 100)

	def test_literal_and_or_filter_value_is_not_treated_as_group_operator(self):
		query = MagicMock()
		query.run.return_value = []
		filters = [
			["enabled", "=", 1],
			"and",
			["email", "=", "or"],
		]

		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(
				supports_ignore_permissions=False,
				supports_logical_filter_groups=False,
			),
		):
			with patch("frappe.qb.get_query", return_value=query) as get_query:
				execute_query("User", {"filters": filters}, ignore_permissions=True)

		compiled = get_query.call_args.kwargs["filters"]
		sql = compiled.get_sql().upper()
		self.assertIn(" AND ", sql)
		self.assertNotIn(" OR ", sql)
		self.assertIn("'OR'", sql)

	def test_capability_detection_recognizes_v16_nested_filter_parser(self):
		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.getsource",
			return_value="def apply_filters(): is_nested_structure = True; potential_nested_list = []",
		):
			capabilities = detect_query_capabilities()

		self.assertTrue(capabilities.supports_logical_filter_groups)

	def test_legacy_flat_single_leaf_is_wrapped_as_filter_row(self):
		query = MagicMock()
		query.run.return_value = []
		filters = ["User", "email", "=", "test@example.com"]

		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(
				supports_ignore_permissions=False,
				supports_logical_filter_groups=False,
			),
		):
			with patch("frappe.qb.get_query", return_value=query) as get_query:
				execute_query("User", {"filters": filters}, ignore_permissions=True)

		self.assertEqual(get_query.call_args.kwargs["filters"], [filters])

	def test_legacy_permission_fallback_flattens_and_only_groups(self):
		rows = [{"name": "visible-user"}]
		filters = [
			["User", "enabled", "=", 1],
			"and",
			[["User", "email", "=", "visible@example.com"], "and", ["User", "user_type", "=", "System User"]],
		]

		with patch(
			"flexirule.ruleflow.utils.frappe_query_compat.QUERY_CAPABILITIES",
			FrappeQueryCapabilities(
				supports_ignore_permissions=False,
				supports_logical_filter_groups=False,
			),
		):
			with patch("frappe.get_list", return_value=rows) as get_list:
				result = execute_query(
					"User", {"fields": ["name"], "filters": filters}, ignore_permissions=False
				)

		self.assertEqual(result, rows)
		self.assertEqual(
			get_list.call_args.kwargs["filters"],
			[
				["User", "enabled", "=", 1],
				["User", "email", "=", "visible@example.com"],
				["User", "user_type", "=", "System User"],
			],
		)
