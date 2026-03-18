# Copyright (c) 2026, FlexiRule Contributors and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RuleFlowSettings(Document):
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
