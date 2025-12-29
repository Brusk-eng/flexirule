# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Deduplication Process

File-backed execution for deduplication operations.
Wraps the existing deduplication methods from flexirule.ruleflow.methods.deduplication.
"""

import frappe
from frappe import _

# Import the actual implementation from methods module
from flexirule.ruleflow.methods.deduplication import (
    find_similar_records as _find_similar_records,
    find_duplicates_by_fields as _find_duplicates_by_fields,
    check_duplicate_and_prevent_save as _check_duplicate_and_prevent_save,
    check_similar_and_prevent_save as _check_similar_and_prevent_save,
    mark_as_duplicate as _mark_as_duplicate,
    find_duplicates_in_child_table as _find_duplicates_in_child_table,
)


# ============================================================
# OPERATION WRAPPERS
# ============================================================

def find_similar_records(context, config):
    """Find similar records using configurable algorithms."""
    return _find_similar_records(context, **config)


def find_duplicates_by_fields(context, config):
    """Find exact duplicate records based on field values."""
    return _find_duplicates_by_fields(context, **config)


def check_duplicate_and_prevent_save(context, config):
    """Block save if exact duplicate exists."""
    return _check_duplicate_and_prevent_save(context, **config)


def check_similar_and_prevent_save(context, config):
    """Block save if similar records exist (fuzzy match)."""
    return _check_similar_and_prevent_save(context, **config)


def mark_as_duplicate(context, config):
    """Mark document as duplicate of another."""
    return _mark_as_duplicate(context, **config)


def find_duplicates_in_child_table(context, config):
    """Find duplicates based on values in a child table."""
    return _find_duplicates_in_child_table(context, **config)


# ============================================================
# DISPATCHER — single entry point
# ============================================================

_OPERATIONS = {
    "find_similar_records": find_similar_records,
    "find_duplicates_by_fields": find_duplicates_by_fields,
    "check_duplicate_and_prevent_save": check_duplicate_and_prevent_save,
    "check_similar_and_prevent_save": check_similar_and_prevent_save,
    "mark_as_duplicate": mark_as_duplicate,
    "find_duplicates_in_child_table": find_duplicates_in_child_table,
}


def execute(context, func=None, config=None):
    """
    Execute a deduplication operation.
    
    Args:
        context: Execution context with 'doc', 'dry_run', etc.
        func: Operation function name
        config: Configuration dict
    
    Returns:
        Operation result
    """
    if not func:
        frappe.throw(_("Operation function name is required"))
    
    if func not in _OPERATIONS:
        frappe.throw(_("Unknown operation: {0}. Available: {1}").format(
            func, ", ".join(_OPERATIONS.keys())
        ))
    
    return _OPERATIONS[func](context, config or {})
