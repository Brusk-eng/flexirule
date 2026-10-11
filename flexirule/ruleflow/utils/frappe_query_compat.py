# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Compatibility helpers for Frappe Query Builder capabilities."""

from dataclasses import dataclass
from inspect import getsource, signature

import frappe
from frappe.database.operator_map import OPERATOR_MAP
from frappe.database.query import Engine
from frappe.query_builder import Criterion


@dataclass(frozen=True)
class FrappeQueryCapabilities:
	"""Static capabilities of the installed Frappe Query Builder API."""

	supports_ignore_permissions: bool
	supports_logical_filter_groups: bool


def detect_query_capabilities() -> FrappeQueryCapabilities:
	"""Detect optional Engine capabilities without making imports depend on source inspection."""
	try:
		get_query = getattr(Engine, "get_query", None)
		parameters = signature(get_query).parameters if callable(get_query) else {}
	except (AttributeError, TypeError, ValueError):
		parameters = {}

	try:
		apply_filters = getattr(Engine, "apply_filters", None)
		source = getsource(apply_filters) if callable(apply_filters) else ""
	except (OSError, TypeError, ValueError):
		source = ""

	return FrappeQueryCapabilities(
		supports_ignore_permissions="ignore_permissions" in parameters,
		supports_logical_filter_groups=(
			"_parse_nested_filters" in source and "_condition_to_criterion" in source
		),
	)


QUERY_CAPABILITIES = detect_query_capabilities()


def _is_legacy_filter_leaf(value) -> bool:
	"""Distinguish a filter tuple from a logical filter group by its operator slot."""
	if not isinstance(value, list | tuple):
		return False
	if len(value) == 2:
		return isinstance(value[0], str)
	if len(value) == 3:
		return (
			isinstance(value[0], str)
			and isinstance(value[1], str)
			and value[1].casefold() in OPERATOR_MAP
		)
	if len(value) == 4:
		return (
			isinstance(value[0], str)
			and isinstance(value[1], str)
			and isinstance(value[2], str)
			and value[2].casefold() in OPERATOR_MAP
		)
	return False


def _contains_logical_filter_groups(value) -> bool:
	"""Check for connector tokens only in a group, never inside a leaf's value."""
	if _is_legacy_filter_leaf(value):
		return False
	if not isinstance(value, list | tuple):
		return False
	for index, item in enumerate(value):
		if (
			isinstance(item, str)
			and item.casefold() in {"and", "or"}
			and 0 < index < len(value) - 1
		):
			return True
		if _contains_logical_filter_groups(item):
			return True
	return False


def _criterion_for_leaf(doctype: str, leaf):
	"""Compile one simple filter using Frappe/Pypika operators."""
	if not isinstance(leaf, list | tuple) or len(leaf) not in (2, 3, 4):
		raise ValueError("Legacy Query Builder compatibility supports simple filter leaves only")

	if len(leaf) == 4:
		leaf_dt, field, operator, value = leaf[0], leaf[1], leaf[2], leaf[3]
	elif len(leaf) == 3:
		leaf_dt, field, operator, value = doctype, leaf[0], leaf[1], leaf[2]
	else:
		leaf_dt, field, operator, value = doctype, leaf[0], "=", leaf[1]

	if not isinstance(field, str) or "." in field:
		raise ValueError("Legacy Query Builder OR compatibility requires root DocType fields")
	if not isinstance(operator, str):
		raise ValueError("Filter operator must be a string")

	operator = operator.casefold()
	if operator not in OPERATOR_MAP:
		raise ValueError(f"Unsupported filter operator for legacy OR compatibility: {operator}")

	column = frappe.qb.DocType(leaf_dt or doctype)[field]
	if isinstance(value, bool):
		value = int(value)
	return OPERATOR_MAP[operator](column, value)


def _compile_logical_filters(doctype: str, filters):
	"""Compile legacy-incompatible AND/OR filter lists into a native Criterion."""
	if not isinstance(filters, list | tuple):
		return filters
	if not _contains_logical_filter_groups(filters):
		return filters
	if not filters:
		return None

	criteria: list[Criterion] = []
	pending_operator = "and"
	for item in filters:
		if isinstance(item, str) and item.casefold() in {"and", "or"}:
			pending_operator = item.casefold()
			continue

		criterion = (
			_compile_logical_filters(doctype, item)
			if isinstance(item, list | tuple) and _contains_logical_filter_groups(item)
			else _criterion_for_leaf(doctype, item)
		)
		if not criteria:
			criteria.append(criterion)
		elif pending_operator == "or":
			criteria[-1] = criteria[-1] | criterion
		else:
			criteria[-1] = criteria[-1] & criterion

	return criteria[0]


def execute_query(doctype: str, kwargs: dict, ignore_permissions: bool):
	"""Execute via native Query Builder; never emulate missing permission semantics."""
	query_kwargs = dict(kwargs)

	if not QUERY_CAPABILITIES.supports_logical_filter_groups:
		filters = query_kwargs.get("filters")
		if _contains_logical_filter_groups(filters):
			query_kwargs["filters"] = _compile_logical_filters(doctype, filters)

	if not QUERY_CAPABILITIES.supports_ignore_permissions and not ignore_permissions:
		# A DocType-level check or a manually attached row predicate cannot establish
		# parity with Frappe's permission semantics (User Permissions, shares, ownership,
		# permission query hooks, and field-level restrictions). Do not return data.
		raise frappe.PermissionError(
			"Fetch Records cannot safely enforce query permissions on this Frappe version. "
			"Upgrade to a version with native Query Builder permission support."
		)

	if QUERY_CAPABILITIES.supports_ignore_permissions:
		query_kwargs["ignore_permissions"] = ignore_permissions

	query = frappe.qb.get_query(doctype, **query_kwargs)
	return query.run(as_dict=True)
