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

	# v15 applies filter rows independently; v16 parses nested logical groups
	# directly inside apply_filters. Recognize both documented source shapes, and
	# fall back to our compatibility compiler when neither can be verified.
	supports_nested_filters = ("_parse_nested_filters" in source and "_condition_to_criterion" in source) or (
		"is_nested_structure" in source and "potential_nested_list" in source
	)

	return FrappeQueryCapabilities(
		supports_ignore_permissions="ignore_permissions" in parameters,
		supports_logical_filter_groups=supports_nested_filters,
	)


QUERY_CAPABILITIES = detect_query_capabilities()


def _is_legacy_filter_leaf(value) -> bool:
	"""Distinguish a filter tuple from a logical filter group by its operator slot."""
	if not isinstance(value, list | tuple):
		return False
	if len(value) == 2:
		return isinstance(value[0], str)
	if len(value) == 3:
		return isinstance(value[0], str) and isinstance(value[1], str) and value[1].casefold() in OPERATOR_MAP
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
		if isinstance(item, str) and item.casefold() in {"and", "or"} and 0 < index < len(value) - 1:
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
	"""Execute with native Query Builder permissions or Frappe's permission-aware list API.

	Frappe v15's Query Builder does not expose permission application. In that
	case, route ordinary filter queries through frappe.get_list/DatabaseQuery,
	which applies doctype, row/user, share, query-hook, and field-level permissions.
	Do not emulate those semantics with hand-built SQL predicates. Filters with
	logical groups cannot be faithfully expressed by the v15 list API and fail
	closed unless an explicitly authorized ignore_permissions override is active.
	"""
	query_kwargs = dict(kwargs)
	filters = query_kwargs.get("filters")

	if not QUERY_CAPABILITIES.supports_ignore_permissions and not ignore_permissions:
		if isinstance(filters, Criterion) or _contains_logical_filter_groups(filters):
			raise frappe.ValidationError(
				"Fetch Records with nested AND/OR filter groups requires a Frappe version "
				"whose Query Builder supports permission-aware logical filters. "
			"Flatten the filters to AND-only conditions or upgrade Frappe."
			)

		# The DatabaseQuery-backed list API is Frappe's permission-aware query
		# implementation on versions without Query Builder permission flags.
		# It applies row/user permissions, shares, permission query hooks, and
		# field-level read restrictions centrally.
		list_kwargs = {
			"fields": query_kwargs.get("fields") or ["name"],
			"filters": filters,
			"order_by": query_kwargs.get("order_by"),
			"group_by": query_kwargs.get("group_by"),
			"start": query_kwargs.get("offset", 0),
			"page_length": query_kwargs.get("limit", 1000),
			"distinct": query_kwargs.get("distinct", False),
			"ignore_permissions": False,
		}
		# Legacy filters are expected as a list of rows; a flat 3/4-part
		# leaf tuple is ambiguous to DatabaseQuery and must be wrapped.
		if (
			_is_legacy_filter_leaf(filters)
			and len(filters) in (3, 4)
			and isinstance(filters[1 if len(filters) == 3 else 2], str)
			and filters[1 if len(filters) == 3 else 2].casefold() in OPERATOR_MAP
		):
			list_kwargs["filters"] = [filters]
		return frappe.get_list(doctype, **list_kwargs)

	if not QUERY_CAPABILITIES.supports_logical_filter_groups and _contains_logical_filter_groups(filters):
		query_kwargs["filters"] = _compile_logical_filters(doctype, filters)

	if QUERY_CAPABILITIES.supports_ignore_permissions:
		query_kwargs["ignore_permissions"] = ignore_permissions

	query = frappe.qb.get_query(doctype, **query_kwargs)
	return query.run(as_dict=True)
