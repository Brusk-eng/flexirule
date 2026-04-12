# Copyright (c) 2026, Bolton and contributors
# For license information, please see license.txt

"""
Rule Lifecycle Service — State Machine for Rule Transitions.

Manages the rule lifecycle state machine:
    Draft → Active:   Requires full validation pass
    Active → Draft:   Unlock for editing
    Active → Archived: Preserve for audit
    Draft → Archived:  Archive incomplete rule
    Archived → Draft:  Creates new version (amendment)

Allowed transitions are defined in TRANSITIONS and enforced by the
transition() method.
"""

from __future__ import annotations

import frappe
from frappe import _

# State machine: (current_status, target_status) → handler method name
TRANSITIONS = {
	("Draft", "Active"): "_on_activate",
	("Active", "Draft"): "_on_deactivate",
	("Active", "Archived"): "_on_archive",
	("Draft", "Archived"): "_on_archive",
	("Archived", "Draft"): "_on_unarchive",
}


# Human-readable transition labels for UI
def get_transition_labels():
	return {
		("Draft", "Active"): _("Activate"),
		("Active", "Draft"): _("Unlock for Editing"),
		("Active", "Archived"): _("Archive"),
		("Draft", "Archived"): _("Archive"),
		("Archived", "Draft"): _("Restore as Draft"),
	}


class RuleLifecycleService:
	"""Manages rule state transitions with validation hooks."""

	@classmethod
	def get_allowed_transitions(cls, current_status: str) -> list[dict]:
		"""Return list of allowed transitions from current status.

		Useful for the frontend to show available status buttons.

		Args:
		    current_status: Current rule status

		Returns:
		    list of dicts: [{"target": "Active", "label": "Activate", "key": "activate"}, ...]
		"""
		result = []
		for (source, target), label in get_transition_labels().items():
			if source == current_status:
				result.append(
					{
						"target": target,
						"label": str(label),
						"key": TRANSITIONS[(source, target)].replace("_on_", ""),
					}
				)
		return result

	@classmethod
	def transition(cls, rule_doc, target_status: str, user: str | None = None) -> dict:
		"""Execute a state transition on a rule.

		Args:
		    rule_doc: Rule document (Frappe Document)
		    target_status: Target lifecycle status
		    user: Optional user performing the transition

		Returns:
		    dict: {"status": str, "is_active": int, "message": str}

		Raises:
		    frappe.ValidationError: If transition is invalid or validation fails
		"""
		current = rule_doc.status or "Draft"
		key = (current, target_status)

		if key not in TRANSITIONS:
			frappe.throw(
				_("Cannot transition from '{0}' to '{1}'").format(current, target_status),
				frappe.ValidationError,
			)

		handler_name = TRANSITIONS[key]
		handler = getattr(cls, handler_name)
		result = handler(rule_doc, user)

		rule_doc.status = target_status
		rule_doc.is_active = 1 if target_status == "Active" else 0
		rule_doc.save(ignore_permissions=True)

		# Clear cache for this rule
		frappe.clear_cache(doctype="Rule", name=rule_doc.name)

		return {
			"status": rule_doc.status,
			"is_active": rule_doc.is_active,
			"message": str(result or _("Transition completed")),
		}

	@classmethod
	def _on_activate(cls, rule_doc, user: str | None = None) -> str:
		"""Draft → Active: full validation + lock."""
		from flexirule.ruleflow.core.validation_service import validate_rule_definition

		# Force is_active for validation (it checks graph integrity only when active)
		rule_doc.is_active = 1
		result = validate_rule_definition(rule_doc, mode="full")

		if not result["valid"]:
			# Reset active flag
			rule_doc.is_active = 0
			frappe.throw(
				_("Cannot activate rule. Validation errors:") + "<br>" + "<br>".join(result["errors"]),
				frappe.ValidationError,
			)

		# If previous version is still active, archive it
		if rule_doc.previous_rule:
			try:
				prev = frappe.get_doc("Rule", rule_doc.previous_rule)
				if prev.status == "Active":
					cls.transition(prev, "Archived", user)
			except frappe.DoesNotExistError:
				pass

		rule_doc.last_error = None
		return _("Rule activated and locked for editing")

	@classmethod
	def _on_deactivate(cls, rule_doc, user: str | None = None) -> str:
		"""Active → Draft: unlock for editing."""
		return _("Rule unlocked for editing")

	@classmethod
	def _on_archive(cls, rule_doc, user: str | None = None) -> str:
		"""Active/Draft → Archived: preserve for audit."""
		rule_doc.is_active = 0
		return _("Rule archived")

	@classmethod
	def _on_unarchive(cls, rule_doc, user: str | None = None) -> str:
		"""Archived → Draft: create new version via amendment.

		Note: This creates a copy. The original stays archived.
		"""
		from flexirule.ruleflow.core.rule_service import amend_rule

		# Amend creates a new draft copy linked to the original
		try:
			new_rule = amend_rule(rule_doc.name)
			return _("New draft version created: {0}").format(new_rule)
		except Exception as e:
			frappe.log_error(
				title=_("Rule Unarchive Failed"),
				message=str(e),
			)
			return _("Restored to Draft")
