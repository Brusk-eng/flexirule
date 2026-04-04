# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Deduplication Process

Result-oriented dedupe operations that:
- fetch candidates using blocking filters
- score candidates against the current document
- return structured match payloads for downstream actions
"""

from __future__ import annotations

import frappe
from frappe import _

from flexirule.ruleflow.process.deduplication.scoring import (
	DedupeScoringEngine,
	fetch_candidate_rows,
	normalize_fields_config,
)


def find_matching_records(context, config=None):
	"""Find matching records for the current document and return a structured payload."""
	doc = context.get("doc")
	config = config or {}
	if not doc:
		return _empty_result(config)

	fields_config = normalize_fields_config(config)
	if not fields_config:
		return _empty_result(config)

	candidates = fetch_candidate_rows(doc, fields_config, config)
	engine = DedupeScoringEngine(doc, fields_config, config)
	return engine.find_matches(candidates)


def find_duplicates_in_child_table(context, config=None):
	"""Find parent documents whose child-table values overlap with the current document."""
	doc = context.get("doc")
	config = config or {}
	if not doc:
		return _empty_child_result(config)

	child_field = config.get("child_table_field")
	search_field = config.get("child_search_field")
	if not child_field or not search_field:
		return _empty_child_result(config)

	values = [row.get(search_field) for row in (doc.get(child_field) or []) if row.get(search_field)]
	if not values:
		return _empty_child_result(config)

	if config.get("normalize_values", True):
		values = [DedupeScoringEngine.normalize_value(value) for value in values]

	child_doctype = _get_child_doctype(doc.doctype, child_field)
	if not child_doctype:
		return _empty_child_result(config)

	filters = {
		search_field: ["in", values],
		"parenttype": doc.doctype,
	}
	if config.get("ignore_cancelled", True):
		filters["docstatus"] = ["!=", 2]
	if doc.name and not doc.is_new():
		filters["parent"] = ["!=", doc.name]

	rows = frappe.get_all(
		child_doctype,
		filters=filters,
		fields=["parent", search_field],
		limit=int(config.get("result_limit", 1000) or 1000),
		order_by="modified desc",
	)

	match_map: dict[str, set] = {}
	for row in rows:
		parent = row.get("parent")
		if not parent:
			continue
		value = row.get(search_field)
		if config.get("normalize_values", True):
			value = DedupeScoringEngine.normalize_value(value)
		match_map.setdefault(parent, set()).add(value)

	matches = [
		{
			"name": parent,
			"doctype": doc.doctype,
			"matched_values": sorted(matched_values),
			"score": 100.0,
		}
		for parent, matched_values in match_map.items()
	]
	matches.sort(key=lambda row: (-len(row["matched_values"]), row["name"]))

	return {
		"has_match": bool(matches),
		"match_count": len(matches),
		"matches": matches,
		"best_match": matches[0] if matches else None,
		"values_checked": values,
		"child_table_field": child_field,
		"child_search_field": search_field,
	}


def execute(context, func=None, config=None):
	"""Dispatcher for the deduplication process."""
	if not func:
		frappe.throw(_("Operation function name is required"))

	func = _LEGACY_ALIASES.get(func, func)
	if func not in _OPERATIONS:
		frappe.throw(_("Unknown operation: {0}").format(func))
	return _OPERATIONS[func](context, config or {})


def _empty_result(config=None):
	config = config or {}
	return {
		"has_match": False,
		"match_count": 0,
		"candidate_count": 0,
		"best_match": None,
		"matches": [],
		"criteria": {
			"overall_threshold": float(config.get("overall_threshold", 0.8) or 0.8),
			"minimum_fields_matched": int(config.get("minimum_fields_matched", 1) or 1),
			"fields_config": normalize_fields_config(config),
		},
	}


def _empty_child_result(config=None):
	config = config or {}
	return {
		"has_match": False,
		"match_count": 0,
		"matches": [],
		"best_match": None,
		"values_checked": [],
		"child_table_field": config.get("child_table_field"),
		"child_search_field": config.get("child_search_field"),
	}


def _get_child_doctype(parent_doctype: str, child_field: str) -> str | None:
	for df in frappe.get_meta(parent_doctype).fields:
		if df.fieldname == child_field and df.fieldtype == "Table":
			return df.options
	return None


_OPERATIONS = {
	"find_matching_records": find_matching_records,
	"find_duplicates_in_child_table": find_duplicates_in_child_table,
}

_LEGACY_ALIASES = {
	"find_duplicates": "find_matching_records",
	"find_similar_records": "find_matching_records",
	"find_duplicates_by_fields": "find_matching_records",
	"check_duplicate_and_prevent_save": "find_matching_records",
	"check_similar_and_prevent_save": "find_matching_records",
}
