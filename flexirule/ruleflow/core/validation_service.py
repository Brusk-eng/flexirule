# Copyright (c) 2026, Bolton and contributors
# For license information, please see license.txt

"""
Central rule validation service.

Provides structured validation results that can be reused from
backend form save and frontend builder prechecks.
"""

from __future__ import annotations

from collections.abc import Mapping

from frappe import _

from flexirule.ruleflow.core.action_handlers import HandlerRegistry
from flexirule.ruleflow.core.contracts import (
	get_contract,
	get_required_fields,
	get_trigger_type_contract,
	is_release_disabled_action,
	normalize_action_type,
)


def validate_rule_definition(rule_doc) -> dict:
	"""Validate rule payload/doc and return structured errors/warnings."""
	errors: list[str] = []
	warnings: list[str] = []

	trigger_type = _safe_get(rule_doc, "trigger_type")
	trigger_contract = get_trigger_type_contract(trigger_type)

	for fieldname in trigger_contract.get("required_fields", []):
		if _is_empty(_safe_get(rule_doc, fieldname)):
			errors.append(_("Missing required trigger field: {0}").format(fieldname))

	for action in _safe_get(rule_doc, "actions", []) or []:
		action_label = _safe_get(action, "action_label") or _safe_get(action, "action_id") or _("(unnamed)")
		action_type_raw = _safe_get(action, "action_type")
		action_type = normalize_action_type(action_type_raw)

		if _is_empty(action_type):
			errors.append(_("Action '{0}' has no action_type").format(action_label))
			continue

		if is_release_disabled_action(action_type):
			errors.append(_("Action '{0}' uses disabled type '{1}'").format(action_label, action_type))

		contract = get_contract(action_type)

		for fieldname in get_required_fields(action_type):
			if _is_empty(_safe_get(action, fieldname)):
				errors.append(
					_("Action '{0}' ({1}) requires field '{2}'").format(action_label, action_type, fieldname)
				)

		operation = _safe_get(action, "operation")
		if operation:
			for fieldname in contract.get("mandatory_fields", {}).get(operation, []):
				if _is_empty(_safe_get(action, fieldname)):
					errors.append(
						_("Action '{0}' ({1}) mode '{2}' requires field '{3}'").format(
							action_label, action_type, operation, fieldname
						)
					)

		if contract.get("terminal") and (
			_safe_get(action, "next_step_if_true") or _safe_get(action, "next_step_if_false")
		):
			errors.append(
				_("Action '{0}' ({1}) is terminal and should not have next steps").format(
					action_label, action_type
				)
			)

		if not contract.get("has_next_false") and _safe_get(action, "next_step_if_false"):
			errors.append(
				_("Action '{0}' ({1}) does not support 'next step if false'").format(
					action_label, action_type
				)
			)

		if action_type == "Query Records" and operation == "Query API":
			errors.append(_("Action '{0}' uses removed mode Query API").format(action_label))

		handler = HandlerRegistry.get(action_type)
		if handler:
			handler_errors = handler.validate(action, {"doc": None, "vars": {}}) or []
			for err in handler_errors:
				errors.append(
					_("Action '{0}' ({1}) validation failed: {2}").format(action_label, action_type, err)
				)

	return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def _safe_get(obj, key, default=None):
	if obj is None:
		return default
	if isinstance(obj, Mapping):
		return obj.get(key, default)
	if hasattr(obj, "get"):
		return obj.get(key, default)
	return getattr(obj, key, default)


def _is_empty(value) -> bool:
	return value in (None, "", [])
