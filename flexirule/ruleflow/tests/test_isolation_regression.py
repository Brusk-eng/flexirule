# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import json
import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.tests.builder import RuleBuilder


class TestIsolationRegression(FrappeTestCase):
	"""
	Regression coverage for Workspace integrity, test DocType lifecycle,
	partial setup failure recovery, and state isolation.
	"""

	def setUp(self):
		super().setUp()
		self._test_prefix = f"FRX_REG_{uuid.uuid4().hex[:8]}"

	def _cleanup_rules_for_prefix(self, prefix: str):
		rules = frappe.get_all(
			"Rule", filters={"rule_name": ["like", f"{prefix}%"]}, fields=["name", "is_active"]
		)
		for r in rules:
			if r.is_active:
				frappe.db.set_value("Rule", r.name, "is_active", 0, update_modified=False)
		for r in rules:
			frappe.delete_doc("Rule", r.name, force=True, ignore_permissions=True)
		logs = frappe.get_all("Rule Execution Log", filters={"rule": ["like", f"{prefix}%"]}, pluck="name")
		for l in logs:
			frappe.delete_doc("Rule Execution Log", l, force=True, ignore_permissions=True)

	def tearDown(self):
		if hasattr(self, "_test_prefix"):
			self._cleanup_rules_for_prefix(self._test_prefix)
		super().tearDown()

	def test_workspace_configuration_contains_no_test_doctype_references(self):
		"""Verify committed RuleFlow Workspace metadata contains zero references to test-created DocTypes."""
		ws_path = frappe.get_app_path("flexirule", "ruleflow", "workspace", "ruleflow", "ruleflow.json")
		with open(ws_path) as f:
			ws_json = json.load(f)

		forbidden_doctypes = {"Test Contact", "Test Customer", "Test Lead", "QB Test Parent", "QB Test Child"}

		# Check links
		linked_doctypes = {
			link.get("link_to") for link in ws_json.get("links", []) if link.get("link_type") == "DocType"
		}
		for forbidden in forbidden_doctypes:
			self.assertNotIn(forbidden, linked_doctypes)

		# Check shortcuts
		shortcut_targets = {
			s.get("link_to") for s in ws_json.get("shortcuts", []) if s.get("type") == "DocType"
		}
		for forbidden in forbidden_doctypes:
			self.assertNotIn(forbidden, shortcut_targets)

		# Check content string
		content_str = str(ws_json.get("content", ""))
		for forbidden in forbidden_doctypes:
			self.assertNotIn(forbidden, content_str)

	def test_workspace_links_and_shortcuts_reference_valid_app_doctypes(self):
		"""Verify all Workspace links and shortcuts point to existing application DocTypes."""
		ws_path = frappe.get_app_path("flexirule", "ruleflow", "workspace", "ruleflow", "ruleflow.json")
		with open(ws_path) as f:
			ws_json = json.load(f)

		for link in ws_json.get("links", []):
			if link.get("link_type") == "DocType" and link.get("link_to"):
				dt = link["link_to"]
				self.assertTrue(
					frappe.db.exists("DocType", dt), f"Workspace link targets missing DocType: {dt}"
				)

		for shortcut in ws_json.get("shortcuts", []):
			if shortcut.get("type") == "DocType" and shortcut.get("link_to"):
				dt = shortcut["link_to"]
				self.assertTrue(
					frappe.db.exists("DocType", dt), f"Workspace shortcut targets missing DocType: {dt}"
				)

	def test_cleanup_deactivates_and_removes_active_rules_safely_on_failure(self):
		"""Verify cleanup helper safely deactivates and removes active sub-rules."""
		custom_prefix = f"FRX_HELPER_{uuid.uuid4().hex[:8]}"
		sub_name = f"{custom_prefix}_Sub"
		parent_name = f"{custom_prefix}_Parent"

		sub_rule = (
			RuleBuilder(sub_name)
			.document_type("ToDo")
			.subrule(exposed=1)
			.active(1)
			.entry_action(next_step="stop_1")
			.stop("Stop", action_id="stop_1")
			.build()
		)

		parent_rule = (
			RuleBuilder(parent_name)
			.document_type("ToDo")
			.active(1)
			.entry_action(next_step="call_sub")
			.sub_rule_call("Call Sub", sub_rule.name, action_id="call_sub")
			.build()
		)

		self.assertTrue(frappe.db.exists("Rule", sub_rule.name))
		self.assertTrue(frappe.db.exists("Rule", parent_rule.name))

		# Run cleanup helper directly
		self._cleanup_rules_for_prefix(custom_prefix)

		# Verify rules were deactivated and deleted without throwing ValidationError
		self.assertFalse(frappe.db.exists("Rule", sub_rule.name))
		self.assertFalse(frappe.db.exists("Rule", parent_rule.name))

	def test_partial_setup_failure_recovery(self):
		"""Verify cleanup helper recovers and removes created resources if setup fails midway through."""
		custom_prefix = f"FRX_HELPER_PARTIAL_{uuid.uuid4().hex[:8]}"
		r1_name = f"{custom_prefix}_R1"
		r1 = RuleBuilder(r1_name).document_type("ToDo").active(0).entry_action().build()
		self.assertTrue(frappe.db.exists("Rule", r1.name))

		# Simulate exception before second rule creation
		try:
			raise RuntimeError("Simulated failure mid-setup")
		except RuntimeError:
			self._cleanup_rules_for_prefix(custom_prefix)

		self.assertFalse(frappe.db.exists("Rule", r1.name))
