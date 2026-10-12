# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Frappe Query Builder API adapter.

Select the installed API contract once, when this module is imported. Fetch Records
always executes through frappe.qb.get_query; this module only adapts the small
syntax difference in legacy filter parsing and the permission keyword signature.
"""

from dataclasses import dataclass
from inspect import signature

import frappe
from frappe.database.operator_map import OPERATOR_MAP
from frappe.database.query import Engine
from frappe.query_builder import Criterion


@dataclass(frozen=True)
class FrappeQueryCapabilities:
	"""Capabilities of the installed Engine.get_query API."""

	supports_ignore_permissions: bool


def detect_query_capabilities() -> FrappeQueryCapabilities:
	"""Feature-detect the permission keyword from the installed public method signature."""
	try:
		get_query = getattr(Engine, "get_query", None)
		parameters = signature(get_query).parameters if callable(get_query) else {}
	except (TypeError, ValueError, RuntimeError):
		parameters = {}

	return FrappeQueryCapabilities(
		supports_ignore_permissions="ignore_permissions" in parameters,
	)


# API contract is detected once during app/module initialization, not per query.
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
	"""Look for AND/OR connector tokens only outside a filter leaf's value."""
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
	"""Compile a simple root-DocType filter leaf into a native Pypika Criterion."""
	if not isinstance(leaf, list | tuple) or len(leaf) not in (2, 3, 4):
		raise ValueError("Legacy Query Builder logical groups require simple filter leaves")

	if len(leaf) == 4:
		leaf_doctype, field, operator, value = leaf
	elif len(leaf) == 3:
		leaf_doctype, field, operator, value = doctype, leaf[0], leaf[1], leaf[2]
	else:
		leaf_doctype, field, operator, value = doctype, leaf[0], "=", leaf[1]

	if not isinstance(field, str) or "." in field or (leaf_doctype and leaf_doctype != doctype):
		raise ValueError(
			"Nested logical groups on this Frappe Query Builder version support root DocType fields only; "
			"linked and child-table filter groups require a newer native filter API"
		)
	if not isinstance(operator, str):
		raise ValueError("Filter operator must be a string")

	operator = operator.casefold()
	if operator not in OPERATOR_MAP:
		raise ValueError(f"Unsupported filter operator for Query Builder logical groups: {operator}")

	column = frappe.qb.DocType(doctype)[field]
	if isinstance(value, bool):
		value = int(value)
	return OPERATOR_MAP[operator](column, value)


def _compile_logical_filters(doctype: str, filters):
	"""Compile nested AND/OR lists into Pypika criteria for legacy filter parsing."""
	if not isinstance(filters, list | tuple):
		return filters
	if not _contains_logical_filter_groups(filters):
		return _criterion_for_leaf(doctype, filters) if _is_legacy_filter_leaf(filters) else filters
	if not filters:
		return None

	connector_indexes = [
		index
		for index, item in enumerate(filters)
		if 0 < index < len(filters) - 1 and isinstance(item, str) and item.casefold() in {"and", "or"}
	]
	connectors = {filters[index].casefold() for index in connector_indexes}
	if len(connectors) > 1:
		raise ValueError("Mixed AND/OR operators at the same level require an explicit nested filter group")

	criteria = []
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
	"""Execute a Fetch Records query through frappe.qb.get_query on every supported version.

	Frappe v15's Query Builder does not expose native query permission enforcement.
	In that case the caller must explicitly opt into FlexiRule's audited permission
	bypass; this adapter will never substitute frappe.get_list, since its filter,
	join, aggregation, and boolean-group contracts differ from Query Builder.
	"""
	query_kwargs = dict(kwargs)
	filters = query_kwargs.get("filters")
	native_permissions = QUERY_CAPABILITIES.supports_ignore_permissions

	if not native_permissions and not ignore_permissions:
		raise frappe.ValidationError(
			"Fetch Records cannot enforce record-level read permissions through the installed "
			"Frappe Query Builder API. On this Frappe version, enable Skip Permissions and provide "
			"a permission audit reason, or use a query mode based on frappe.get_list."
		)

	if native_permissions:
		query_kwargs["ignore_permissions"] = ignore_permissions
	elif _contains_logical_filter_groups(filters):
		try:
			query_kwargs["filters"] = _compile_logical_filters(doctype, filters)
		except ValueError as exc:
			raise frappe.ValidationError(str(exc)) from exc
	elif isinstance(filters, list | tuple) and _is_legacy_filter_leaf(filters):
		# Frappe v15 treats a bare filter tuple as an iterable of individual values.
		query_kwargs["filters"] = [list(filters)]

	query = frappe.qb.get_query(doctype, **query_kwargs)
	return query.run(as_dict=True)
