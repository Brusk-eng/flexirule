# Copyright (c) 2026, Bolton and contributors
# For license information, please see license.txt

"""
Runtime-safe evaluators used by the rule engine.

Splits boolean condition evaluation from value evaluation so callers can
explicitly choose semantics.
"""

from __future__ import annotations

import frappe


def eval_condition_bool(expression: str, safe_locals: dict, default: bool = False) -> bool:
	"""Evaluate expression and coerce to bool."""
	if not expression:
		return True

	try:
		return bool(frappe.safe_eval(expression, None, safe_locals))
	except Exception:
		return default


def eval_value(expression: str, safe_locals: dict, default=None):
	"""Evaluate expression and return raw value."""
	if not expression:
		return default

	try:
		return frappe.safe_eval(expression, None, safe_locals)
	except Exception:
		return default
