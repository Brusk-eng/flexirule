# Copyright (c) 2026, FlexiRule Contributors and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RuleFlowSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from flexirule.ruleflow.doctype.ruleflow_excluded_doctype.ruleflow_excluded_doctype import (
			RuleFlowExcludedDocType,
		)

		action_config_mode: DF.Literal["Sidebar", "Dialog"]
		allow_async_actions: DF.Check
		allow_editing_active: DF.Check
		enable_debug_logging: DF.Check
		enable_edge_insertion: DF.Check
		excluded_doctypes: DF.Table[RuleFlowExcludedDocType]
		layout_direction: DF.Literal["Left to Right"]
		log_retention_days: DF.Int
		max_execution_time_default: DF.Int
		require_approval_for_active: DF.Check
		sidebar_position: DF.Literal["Left", "Right"]
		theme: DF.Literal["System", "Light", "Dark"]

	# end: auto-generated types
	def validate(self):
		if (
			frappe.flags.in_install
			or frappe.flags.in_migrate
			or frappe.flags.in_patch
			or frappe.flags.in_import
		):
			return

		excluded = [row.document_type for row in self.get("excluded_doctypes", []) if row.document_type]
		if not excluded:
			return

		# Check if any active Rule exists for the excluded doctypes
		active_rules = frappe.get_all(
			"Rule",
			filters={
				"document_type": ["in", excluded],
				"is_active": 1,
			},
			fields=["name", "document_type"],
		)

		if active_rules:
			conflicts: dict[str, list[str]] = {}
			for rule in active_rules:
				conflicts.setdefault(rule.document_type, []).append(rule.name)

			msg = (
				frappe._("Cannot exclude the following DocTypes because they have active Rules:") + "<br><ul>"
			)
			for dt, rules in conflicts.items():
				msg += f"<li><b>{dt}</b>: {', '.join(rules)}</li>"
			msg += "</ul><br>" + frappe._(
				"Please disable or delete these rules before excluding the DocTypes."
			)
			frappe.throw(msg, title=frappe._("Active Rules Found"))


def get_settings():
	"""Get cached RuleFlow Settings."""
	return frappe.get_cached_doc("RuleFlow Settings")
