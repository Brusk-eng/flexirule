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
	except Exception:
		parameters = {}

	try:
		apply_filters = getattr(Engine, "apply_filters", None)
		source = getsource(apply_filters) if callable(apply_filters) else ""
	except Exception:
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


def _permission_filter_clauses(filters):
	"""Convert logical filters into DatabaseQuery AND filters and one OR group.

	Frappe v15 combines filters with AND and or_filters as one parenthesized
	OR group. Reject shapes requiring multiple OR groups or OR over nested
	conjunctions rather than weakening the query.
	"""
	if isinstance(filters, Criterion):
		raise ValueError("Native Criterion filters cannot use the permission-aware Frappe v15 fallback")
	if filters is None or filters == "" or filters == []:
		return [], [], False
	if _is_legacy_filter_leaf(filters):
		return [list(filters)], [], False
	if not isinstance(filters, list | tuple):
		return [filters], [], False

	connector_indexes = [
		index
		for index, item in enumerate(filters)
		if 0 < index < len(filters) - 1 and isinstance(item, str) and item.casefold() in {"and", "or"}
	]
	if not connector_indexes:
		and_filters = []
		or_filters = []
		has_or_group = False
		for child in filters:
			child_and, child_or, child_has_or = _permission_filter_clauses(child)
			if child_has_or and has_or_group:
				raise ValueError(
					"Only one OR filter group can be used with permission-aware queries on Frappe v15"
				)
			and_filters.extend(child_and)
			if child_has_or:
				or_filters = child_or
				has_or_group = True
		return and_filters, or_filters, has_or_group

	operators = {filters[index].casefold() for index in connector_indexes}
	if len(operators) != 1:
		raise ValueError("Mixed AND/OR operators at the same filter level require a nested filter group")
	operator = next(iter(operators))
	children = [item for index, item in enumerate(filters) if index not in connector_indexes]

	if operator == "or":
		if not children or not all(_is_legacy_filter_leaf(child) for child in children):
			raise ValueError(
				"OR filters around nested conjunctions are not supported by the permission-aware "
				"Frappe v15 query API"
			)
		return [], [list(child) for child in children], True

	and_filters = []
	or_filters = []
	has_or_group = False
	for child in children:
		child_and, child_or, child_has_or = _permission_filter_clauses(child)
		if child_has_or and has_or_group:
			raise ValueError(
				"Only one OR filter group can be used with permission-aware queries on Frappe v15"
			)
		and_filters.extend(child_and)
		if child_has_or:
			or_filters = child_or
			has_or_group = True
	return and_filters, or_filters, has_or_group


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
	case, route supported filter queries through frappe.get_list/DatabaseQuery,
	which applies doctype, row/user, share, query-hook, and field-level permissions.
	Do not emulate those semantics with hand-built SQL predicates. The fallback
	preserves AND-only groups and one OR group; unsupported boolean shapes fail
	closed unless an explicitly authorized ignore_permissions override is active.
	"""
	query_kwargs = dict(kwargs)
	filters = query_kwargs.get("filters")

	if not QUERY_CAPABILITIES.supports_ignore_permissions and not ignore_permissions:
		try:
			and_filters, or_filters, _ = _permission_filter_clauses(filters)
		except ValueError as exc:
			raise frappe.ValidationError(str(exc)) from exc

		# DatabaseQuery is the supported v15 permission-aware query path. It
		# applies doctype and row/user permissions, shares, permission query
		# hooks, and field-level read restrictions without hand-built SQL.
		list_kwargs = {
			"fields": query_kwargs.get("fields") or ["name"],
			"filters": and_filters,
			"or_filters": or_filters,
			"order_by": query_kwargs.get("order_by"),
			"group_by": query_kwargs.get("group_by"),
			"start": query_kwargs.get("offset", 0),
			"page_length": query_kwargs.get("limit", 1000),
			"distinct": query_kwargs.get("distinct", False),
			"ignore_permissions": False,
		}
		return frappe.get_list(doctype, **list_kwargs)

	if not QUERY_CAPABILITIES.supports_logical_filter_groups:
		if isinstance(filters, list | tuple) and _is_legacy_filter_leaf(filters):
			operator_index = 1 if len(filters) == 3 else 2
			if (
				len(filters) in (3, 4)
				and isinstance(filters[operator_index], str)
				and filters[operator_index].casefold() in OPERATOR_MAP
			):
				query_kwargs["filters"] = [list(filters)]
		elif _contains_logical_filter_groups(filters):
			query_kwargs["filters"] = _compile_logical_filters(doctype, filters)

	if QUERY_CAPABILITIES.supports_ignore_permissions:
		query_kwargs["ignore_permissions"] = ignore_permissions

	query = frappe.qb.get_query(doctype, **query_kwargs)
	return query.run(as_dict=True)
