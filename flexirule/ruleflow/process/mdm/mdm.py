# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
MDM (Master Data Management) Process

This process provides operations for data quality, deduplication, and normalization.
File-backed execution following the Frappe Script Report pattern.
"""

import frappe
from frappe import _


# ============================================================
# OPERATION: create_review_task
# ============================================================

def create_review_task(context, config):
    """
    Create a Data Review Task for steward review.
    
    Args:
        context: Execution context with 'doc', 'dry_run', etc.
        config: Configuration dict with 'task_type', 'priority', 'description'
    
    Returns:
        str: Name of the created task (or None if dry_run)
    """
    doc = context.get("doc")
    if not doc:
        frappe.throw(_("Document is required in context"))
    
    task_type = config.get("task_type", "Duplicate Review")
    priority = config.get("priority", "Medium")
    description = config.get("description", "")
    
    # Check if Data Review Task DocType exists
    if not frappe.db.exists("DocType", "Data Review Task"):
        frappe.throw(_("Data Review Task DocType not found"))
    
    task = frappe.new_doc("Data Review Task")
    task.task_type = task_type
    task.priority = priority
    task.description = description or f"Review {doc.doctype}: {doc.name}"
    task.reference_doctype = doc.doctype
    task.reference_name = doc.name
    
    if context.get("dry_run"):
        return None
    
    task.insert(ignore_permissions=True)
    return task.name


# ============================================================
# OPERATION: find_duplicates
# ============================================================

def find_duplicates(context, config):
    """
    Find potential duplicate records based on similarity.
    
    Args:
        context: Execution context with 'doc'
        config: Configuration dict with 'threshold', 'fields_to_compare', 'max_results'
    
    Returns:
        dict: {duplicates: [...], count: int, threshold: float}
    """
    doc = context.get("doc")
    if not doc:
        frappe.throw(_("Document is required in context"))
    
    threshold = float(config.get("threshold", 0.8))
    fields_str = config.get("fields_to_compare", "")
    max_results = int(config.get("max_results", 10))
    
    # Parse fields
    if fields_str:
        fields = [f.strip() for f in fields_str.split(",") if f.strip()]
    else:
        # Default to name field
        fields = ["name"]
    
    # Simple duplicate detection (placeholder - production would use proper similarity)
    duplicates = []
    
    # Get existing records
    existing = frappe.get_all(
        doc.doctype,
        filters={"name": ["!=", doc.name]},
        fields=["name"] + fields,
        limit=max_results * 2
    )
    
    for record in existing:
        similarity = _calculate_similarity(doc, record, fields)
        if similarity >= threshold:
            duplicates.append({
                "name": record.name,
                "similarity": similarity,
                "fields_matched": fields
            })
    
    # Sort by similarity descending
    duplicates.sort(key=lambda x: x["similarity"], reverse=True)
    duplicates = duplicates[:max_results]
    
    return {
        "duplicates": duplicates,
        "count": len(duplicates),
        "threshold": threshold
    }


def _calculate_similarity(doc1, doc2, fields):
    """Calculate simple field similarity score."""
    if not fields:
        return 0.0
    
    matches = 0
    for field in fields:
        val1 = str(doc1.get(field) or "").lower().strip()
        val2 = str(doc2.get(field) or "").lower().strip()
        if val1 and val2 and val1 == val2:
            matches += 1
    
    return matches / len(fields) if fields else 0.0


# ============================================================
# OPERATION: normalize_field
# ============================================================

def normalize_field(context, config):
    """
    Apply normalization transformations to a field value.
    
    Args:
        context: Execution context with 'doc'
        config: Configuration dict with 'field', 'transformations'
    
    Returns:
        str: The normalized value
    """
    doc = context.get("doc")
    if not doc:
        frappe.throw(_("Document is required in context"))
    
    field = config.get("field")
    if not field:
        frappe.throw(_("Field name is required"))
    
    transformations_str = config.get("transformations", "trim,lowercase")
    transformations = [t.strip() for t in transformations_str.split(",") if t.strip()]
    
    value = doc.get(field)
    if value is None:
        return None
    
    value = str(value)
    
    for transform in transformations:
        if transform == "lowercase":
            value = value.lower()
        elif transform == "uppercase":
            value = value.upper()
        elif transform == "trim":
            value = value.strip()
        elif transform == "remove_special_chars":
            import re
            value = re.sub(r'[^a-zA-Z0-9\s]', '', value)
        elif transform == "title":
            value = value.title()
    
    # Apply to doc if not dry_run
    if not context.get("dry_run"):
        doc.set(field, value)
    
    return value


# ============================================================
# DISPATCHER — single entry point (no registry, no decorators)
# ============================================================

_OPERATIONS = {
    "create_review_task": create_review_task,
    "find_duplicates": find_duplicates,
    "normalize_field": normalize_field,
}


def execute(context, func=None, config=None):
    """
    Execute a process operation.
    
    This is the single entry point for the MDM process, following the
    Frappe Script Report pattern.
    
    Args:
        context: Execution context with 'doc', 'event', 'dry_run', etc.
        func: Operation function name to execute
        config: Configuration dict for the operation
    
    Returns:
        Operation result (varies by operation)
    """
    if not func:
        frappe.throw(_("Operation function name is required"))
    
    if func not in _OPERATIONS:
        frappe.throw(_("Unknown operation: {0}. Available: {1}").format(
            func, ", ".join(_OPERATIONS.keys())
        ))
    
    return _OPERATIONS[func](context, config or {})
