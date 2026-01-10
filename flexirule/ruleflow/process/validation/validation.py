# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Validation Process
File-backed execution for validation operations.
Unifies legacy validation and advanced validation methods.
"""

import json
import re
import frappe
from frappe import _
from flexirule.ruleflow.utils.field_resolver import parse_field_list, parse_pattern_type


# ============================================================
# OPERATIONS
# ============================================================


def required_fields(context, config):
    """Validate that specified fields have values"""
    doc = context.get("doc")
    if not doc:
        return True

    field_list = parse_field_list(config.get("fields"))
    missing_fields = []

    for field in field_list:
        value = doc.get(field)
        if not value and value != 0:
            # Check if it's a fieldname or a label
            meta = frappe.get_meta(doc.doctype)
            df = meta.get_field(field)
            label = _(df.label) if df else field
            missing_fields.append(label)

    if missing_fields:
        frappe.throw(
            _("Required fields are missing: {0}").format(", ".join(missing_fields)),
            title=_("Validation Error"),
        )

    return True


def field_pattern(context, config):
    """Validate that a field value matches a regex pattern"""
    doc = context.get("doc")
    field = config.get("field")
    if not doc or not field:
        return True

    value = doc.get(field)
    if not value:
        return True  # Empty values pass

    pattern_type = config.get("pattern_type")
    pattern = config.get("pattern")
    error_message = config.get("error_message")

    actual_pattern = parse_pattern_type(pattern_type, pattern)

    if not actual_pattern or not re.match(actual_pattern, str(value)):
        msg = error_message or _("Field {0} does not match required pattern").format(
            field
        )
        frappe.throw(msg, title=_("Pattern Mismatch"))

    return True


def value_in_range(context, config):
    """Validate that a numeric field is within a specified range"""
    doc = context.get("doc")
    field = config.get("field")
    if not doc or not field:
        return True

    value = doc.get(field)
    if value is None:
        return True

    try:
        num_value = float(value)
    except (ValueError, TypeError):
        frappe.throw(_("Field {0} must be a number").format(field))

    min_val = config.get("min_value")
    max_val = config.get("max_value")

    if min_val is not None and num_value < float(min_val):
        frappe.throw(_("Field {0} must be at least {1}").format(field, min_val))

    if max_val is not None and num_value > float(max_val):
        frappe.throw(_("Field {0} must be at most {1}").format(field, max_val))

    return True


def unique_field(context, config):
    """Validate field value is unique across documents"""
    doc = context.get("doc")
    field = config.get("field")
    if not doc or not field:
        return True

    value = doc.get(field)
    if not value:
        return True

    filters = {field: value}
    if doc.name:
        filters["name"] = ["!=", doc.name]
    if config.get("ignore_cancelled", True):
        filters["docstatus"] = ["!=", 2]

    existing = frappe.db.exists(doc.doctype, filters)
    if existing:
        frappe.throw(
            _("Value '{0}' for {1} already exists in {2}").format(
                value, field, existing
            ),
            title=_("Duplicate Value"),
        )

    return True


def conditional_required(context, config):
    """Make fields required when a condition is met"""
    doc = context.get("doc")
    condition_field = config.get("condition_field")
    condition_value = config.get("condition_value")

    if not doc or not condition_field:
        return True

    # Check if condition is met
    actual_value = doc.get(condition_field)
    if str(actual_value) != str(condition_value):
        return True

    # Validate required fields
    required_fields_list = parse_field_list(config.get("required_fields"))
    missing = []

    for field in required_fields_list:
        value = doc.get(field)
        if not value and value != 0:
            missing.append(field)

    if missing:
        frappe.throw(
            _("When {0} is {1}, the following fields are required: {2}").format(
                condition_field, condition_value, ", ".join(missing)
            )
        )

    return True


def child_table_rows(context, config):
    """Validate rows in a child table against configured rules."""
    doc = context.get("doc")
    child_table = config.get("child_table")
    validations = config.get("validations")

    if not doc or not child_table or not validations:
        return True

    rows = doc.get(child_table) or []
    if not rows:
        return True

    errors = []
    for idx, row in enumerate(rows, start=1):
        for v in validations:
            v_type = v.get("type")
            error_msg = v.get("error_message", _("Validation failed"))

            field1 = v.get("field1")
            field2 = v.get("field2")
            val1 = row.get(field1)
            val2 = row.get(field2)

            if v_type == "fields_not_equal":
                if val1 and val2 and str(val1) == str(val2):
                    errors.append(_("Row {0}: {1}").format(idx, error_msg))
            elif v_type == "fields_equal":
                if val1 and val2 and str(val1) != str(val2):
                    errors.append(_("Row {0}: {1}").format(idx, error_msg))
            elif v_type == "field_required":
                if not val1 and val1 != 0:
                    errors.append(_("Row {0}: {1}").format(idx, error_msg))
            elif v_type == "field_greater_than":
                threshold = v.get("value", 0)
                try:
                    if val1 is not None and float(val1) <= float(threshold):
                        errors.append(_("Row {0}: {1}").format(idx, error_msg))
                except (ValueError, TypeError):
                    pass

    if errors:
        frappe.throw("<br>".join(errors), title=_("Table Validation Error"))

    return True


def composite_uniqueness(context, config):
    """Check for duplicates based on parent and child table fields."""
    doc = context.get("doc")
    parent_fields = parse_field_list(config.get("parent_fields"))
    child_table = config.get("child_table")
    child_fields = parse_field_list(config.get("child_fields"))
    match_mode = config.get("match_mode", "any")

    if not doc or not parent_fields or not child_table or not child_fields:
        return True

    parent_filters = {f: doc.get(f) for f in parent_fields if doc.get(f)}
    if not parent_filters:
        return True

    if doc.name:
        parent_filters["name"] = ["!=", doc.name]
    parent_filters["docstatus"] = ["!=", 2]

    # Get current values
    current_child_values = []
    for row in doc.get(child_table) or []:
        row_vals = tuple(row.get(f) for f in child_fields)
        if all(v is not None for v in row_vals):
            current_child_values.append(row_vals)

    if not current_child_values:
        return True

    candidates = frappe.get_all(doc.doctype, filters=parent_filters, pluck="name")
    if not candidates:
        return True

    child_dt = frappe.get_meta(doc.doctype).get_field(child_table).options

    for cand in candidates:
        cand_rows = frappe.get_all(
            child_dt, filters={"parent": cand}, fields=child_fields
        )
        cand_vals = [tuple(r.get(f) for f in child_fields) for r in cand_rows]

        if match_mode == "any":
            for cv in current_child_values:
                if cv in cand_vals:
                    frappe.throw(_("Duplicate found in {0}").format(cand))
        elif match_mode == "all":
            if set(current_child_values) == set(cand_vals):
                frappe.throw(_("Identical entry found in {0}").format(cand))

    return True


def role_check(context, config):
    """Check if current user has or doesn't have required roles"""
    roles = parse_field_list(config.get("roles"))
    mode = config.get("mode", "has_any")  # has_any, has_all, not_has_any

    user_roles = frappe.get_roles()

    if mode == "has_any":
        result = any(r in user_roles for r in roles)
    elif mode == "has_all":
        result = all(r in user_roles for r in roles)
    elif mode == "not_has_any":
        result = not any(r in user_roles for r in roles)
    else:
        result = False

    if config.get("store_result"):
        context["vars"][config.get("store_result")] = result

    return result


def on_field_change(context, config):
    """Check if specified fields have changed"""
    doc = context.get("doc")
    old_doc = context.get("old_doc")
    watched_fields = parse_field_list(config.get("watched_fields"))
    match_mode = config.get("match_mode", "Any")

    if not watched_fields:
        return False

    changed_fields = []
    for field in watched_fields:
        if old_doc is None:  # New document
            changed_fields.append(field)
        elif doc.get(field) != old_doc.get(field):
            changed_fields.append(field)

    if config.get("store_result"):
        context.setdefault("vars", {})[config.get("store_result")] = changed_fields

    if match_mode == "All":
        return len(changed_fields) == len(watched_fields)
    return len(changed_fields) > 0


# ============================================================
# DISPATCHER
# ============================================================

_OPERATIONS = {
    "required_fields": required_fields,
    "field_pattern": field_pattern,
    "value_in_range": value_in_range,
    "unique_field": unique_field,
    "conditional_required": conditional_required,
    "child_table_rows": child_table_rows,
    "composite_uniqueness": composite_uniqueness,
    "role_check": role_check,
    "on_field_change": on_field_change,
}


def execute(context, func=None, config=None):
    if not func:
        frappe.throw(_("Operation function name is required"))
    if func not in _OPERATIONS:
        frappe.throw(_("Unknown validation operation: {0}").format(func))

    return _OPERATIONS[func](context, config or {})
