# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Deduplication Process

File-backed execution for deduplication operations.
Migrated from flexirule.ruleflow.methods.deduplication.
"""

import json
from typing import Any, Dict, List, Optional

import frappe
from frappe import _
from flexirule.ruleflow.utils.field_resolver import parse_field_list
from rapidfuzz import fuzz, process

# ============================================================
# MATCHER ENGINE
# ============================================================


class DedupeMatcher:
    """
    Consolidated matching engine for deduplication.
    Handles various comparison algorithms and scoring logic.
    """

    def __init__(self, doc):
        self.doc = doc
        self._phonetic_scorer = None

    def get_phonetic_scorer(self):
        """Lazy-load phonetic matcher"""
        if self._phonetic_scorer:
            return self._phonetic_scorer

        try:
            import jellyfish

            def phonetic_score(a, b):
                code_a = jellyfish.metaphone(str(a))
                code_b = jellyfish.metaphone(str(b))
                return 1.0 if code_a == code_b else 0.0

            self._phonetic_scorer = phonetic_score
        except ImportError:
            self._phonetic_scorer = lambda a, b: (
                1.0 if str(a).lower() == str(b).lower() else 0.0
            )
        return self._phonetic_scorer

    def normalize(self, value):
        """Basic text normalization"""
        if not isinstance(value, str):
            return str(value) if value is not None else ""
        import re

        value = value.lower().strip()
        value = re.sub(r"\s+", " ", value)
        return value

    def get_score(self, algorithm, val1, val2, config=None):
        """Calculate similarity score (0.0 - 1.0) based on algorithm"""
        if val1 is None or val2 is None:
            return 0.0

        config = config or {}
        normalize = config.get("normalize", True)

        # Prepare values
        s1 = self.normalize(val1) if normalize else str(val1).lower()
        s2 = self.normalize(val2) if normalize else str(val2).lower()

        if algorithm == "Exact":
            return 1.0 if s1 == s2 else 0.0

        elif algorithm == "Fuzzy":
            return fuzz.ratio(s1, s2) / 100.0

        elif algorithm == "Contains":
            return 1.0 if (s1 in s2 or s2 in s1) else 0.0

        elif algorithm == "Phonetic":
            return self.get_phonetic_scorer()(val1, val2)

        elif algorithm == "Numeric Range":
            try:
                n1, n2 = float(val1), float(val2)
                max_val = max(abs(n1), abs(n2))
                if max_val == 0:
                    return 1.0
                return max(0, 1 - (abs(n1 - n2) / max_val))
            except (ValueError, TypeError):
                return 0.0

        elif algorithm == "Date Distance":
            from frappe.utils import date_diff, getdate

            try:
                d1, d2 = getdate(val1), getdate(val2)
                tolerance = float(config.get("tolerance", 30))
                if tolerance <= 0:
                    tolerance = 1
                diff = abs(date_diff(d1, d2))
                return max(0, 1.0 - (diff / tolerance))
            except Exception:
                return 0.0

        return 0.0


# ============================================================
# HELPERS
# ============================================================


def parse_field_list(fields) -> list[str]:
    """Parse fields from multiple formats (list, newline, comma, JSON)"""
    if not fields:
        return []
    if isinstance(fields, list):
        return [f.strip() if isinstance(f, str) else f for f in fields]
    if isinstance(fields, str):
        fields = fields.strip()
        if fields.startswith("["):
            try:
                return json.loads(fields)
            except json.JSONDecodeError:
                pass
        if "\n" in fields:
            return [f.strip() for f in fields.split("\n") if f.strip()]
        if "," in fields:
            return [f.strip() for f in fields.split(",") if f.strip()]
        return [fields]
    return []


def _build_blocking_filters(doc, fields_config):
    """Build optimized filters for initial candidate lookup"""
    filters = {}
    for f in fields_config:
        if not f.get("included_in_filters", True):
            continue
        val = doc.get(f["fieldname"])
        if not val:
            continue

        algo = f.get("algorithm", "Exact")
        if algo == "Exact":
            filters[f["fieldname"]] = val
        elif algo in ("Fuzzy", "Contains", "Phonetic"):
            if isinstance(val, str) and len(val) >= 3:
                filters[f["fieldname"]] = ["like", f"%{val[:3]}%"]
    return filters


# ============================================================
# OPERATIONS
# = : find_similar_records
# = : find_duplicates_by_fields
# ============================================================


def find_similar_records(context, config):
    """Find similar records using configurable algorithms."""
    doc = context.get("doc")
    if not doc:
        return []

    overall_threshold = float(config.get("overall_threshold", 0.8))
    min_fields = int(config.get("minimum_fields_matched", 1))
    fields_config = config.get("fields_config")

    if not fields_config:
        return []

    # 1. Candidate Filtering
    filters = _build_blocking_filters(doc, fields_config)
    if doc.name:
        filters["name"] = ["!=", doc.name]
    filters["docstatus"] = ["!=", 2]

    fieldnames = list(set(["name"] + [f["fieldname"] for f in fields_config]))
    try:
        candidates = frappe.get_all(
            doc.doctype, filters=filters, fields=fieldnames, limit=1000
        )
    except Exception as e:
        frappe.log_error(f"Dedupe candidate fetch failed: {e}")
        return []

    if not candidates:
        return []

    # 2. Detailed Scoring
    matcher = DedupeMatcher(doc)
    results = []
    total_weight = sum(float(f.get("weight", 1.0)) for f in fields_config)

    for cand in candidates:
        cand_scores = {}
        weighted_sum = 0.0
        fields_met = 0

        for f in fields_config:
            fname = f["fieldname"]
            weight = float(f.get("weight", 1.0))
            threshold = float(f.get("threshold", 0.8))

            score = matcher.get_score(
                f.get("algorithm", "Fuzzy"), doc.get(fname), cand.get(fname), f
            )
            cand_scores[fname] = round(score * 100, 1)
            weighted_sum += score * weight

            if score >= threshold:
                fields_met += 1

        final_score = (weighted_sum / total_weight) if total_weight > 0 else 0.0

        if final_score >= overall_threshold and fields_met >= min_fields:
            results.append(
                {
                    "name": cand.name,
                    "doctype": doc.doctype,
                    "score": round(final_score * 100, 1),
                    "fields": cand_scores,
                }
            )

    return sorted(results, key=lambda x: x["score"], reverse=True)


def find_duplicates_by_fields(context, config):
    """Find exact duplicate records based on field values."""
    doc = context.get("doc")
    field_list = parse_field_list(config.get("fields"))
    if not field_list:
        return []

    filters = {f: doc.get(f) for f in field_list if doc.get(f)}
    if doc.name:
        filters["name"] = ["!=", doc.name]
    if config.get("ignore_cancelled", True):
        filters["docstatus"] = ["!=", 2]

    return frappe.get_all(doc.doctype, filters=filters, pluck="name")


def check_duplicate_and_prevent_save(context, config):
    """Block save if exact duplicate exists."""
    duplicates = find_duplicates_by_fields(context, config)
    if duplicates:
        frappe.throw(
            _("Duplicate found: {0} has identical critical fields.").format(
                duplicates[0]
            ),
            exc=frappe.DuplicateEntryError,
        )
    return True


def check_similar_and_prevent_save(context, config):
    """Block save if similar records exist (fuzzy match)."""
    matches = find_similar_records(context, config)
    if matches:
        names = ", ".join([m["name"] for m in matches[:3]])
        if len(matches) > 3:
            names += _(" and {0} others").format(len(matches) - 3)
        frappe.throw(
            _("Potential duplicates found: {0}").format(names),
            exc=frappe.DuplicateEntryError,
        )
    return matches


def mark_as_duplicate(context, config):
    """Mark document as duplicate of another."""
    master = config.get("master_document")
    doc = context.get("doc")
    if not master:
        return False

    if hasattr(doc, "is_duplicate"):
        doc.is_duplicate = 1
    if hasattr(doc, "master_record"):
        doc.master_record = master
    return master


def find_duplicates_in_child_table(context, config):
    """Find duplicates based on values in a child table."""
    child_field = config.get("child_table_field")
    search_field = config.get("child_search_field")
    doc = context.get("doc")
    if not doc:
        return []

    vals = [
        r.get(search_field) for r in (doc.get(child_field) or []) if r.get(search_field)
    ]
    if not vals:
        return []

    # Resolve child doctype
    child_dt = None
    for df in frappe.get_meta(doc.doctype).fields:
        if df.fieldname == child_field and df.fieldtype == "Table":
            child_dt = df.options
            break
    if not child_dt:
        return []

    filters = {
        search_field: ["in", vals],
        "parenttype": doc.doctype,
        "docstatus": ["!=", 2],
    }
    if doc.name and not doc.is_new():
        filters["parent"] = ["!=", doc.name]

    return frappe.get_all(child_dt, filters=filters, pluck="parent", distinct=True)


# ============================================================
# DISPATCHER
# ============================================================

_OPERATIONS = {
    "find_duplicates": find_similar_records,  # Alias
    "find_similar_records": find_similar_records,
    "find_duplicates_by_fields": find_duplicates_by_fields,
    "check_duplicate_and_prevent_save": check_duplicate_and_prevent_save,
    "check_similar_and_prevent_save": check_similar_and_prevent_save,
    "mark_as_duplicate": mark_as_duplicate,
    "find_duplicates_in_child_table": find_duplicates_in_child_table,
}


def execute(context, func=None, config=None):
    if not func:
        frappe.throw(_("Operation function name is required"))
    if func not in _OPERATIONS:
        frappe.throw(_("Unknown operation: {0}").format(func))
    return _OPERATIONS[func](context, config or {})
