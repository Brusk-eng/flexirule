# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Validation process methods for the Bolton Rule Engine
"""

import frappe
from frappe import _
import re
from .utils import parse_field_list, parse_pattern_type


def validate_required_fields(context, fields=None, **kwargs):
    """
    Validate that specified fields have values
    
    Args:
        context: Execution context containing 'doc'
        fields: List/text of field names to validate
    
    Returns:
        Boolean: True if all fields have values
    """
    doc = context.get('doc')
    field_list = parse_field_list(fields)
    
    missing_fields = []
    for field in field_list:
        value = doc.get(field)
        if not value and value != 0:
            missing_fields.append(field)
    
    if missing_fields:
        frappe.throw(
            _("Required fields are missing: {0}").format(", ".join(missing_fields))
        )
    
    return True


def validate_field_pattern(context, field=None, pattern=None, pattern_type=None, error_message=None, **kwargs):
    """
    Validate that a field value matches a regex pattern
    
    Args:
        context: Execution context containing 'doc'
        field: Field name to validate
        pattern: Regex pattern (used if pattern_type is Custom Regex)
        pattern_type: Preset pattern type (Email, Phone, URL, etc.)
        error_message: Custom error message
    """
    doc = context.get('doc')
    value = doc.get(field)
    if not value:
        return True  # Empty values pass
    
    # Get pattern from type or use custom
    actual_pattern = parse_pattern_type(pattern_type, pattern) if pattern_type else pattern
    
    if not actual_pattern or not re.match(actual_pattern, str(value)):
        msg = error_message or _(f"Field {field} does not match required pattern")
        frappe.throw(msg)
    
    return True


def validate_value_in_range(context, field=None, min_value=None, max_value=None, **kwargs):
    """
    Validate that a numeric field is within a specified range
    """
    doc = context.get('doc')
    value = doc.get(field)
    
    if value is None:
        return True  # Empty values pass
    
    try:
        num_value = float(value)
    except (ValueError, TypeError):
        frappe.throw(_(f"Field {field} must be a number"))
        return False
    
    if min_value is not None and num_value < float(min_value):
        frappe.throw(_(f"Field {field} must be at least {min_value}"))
    
    if max_value is not None and num_value > float(max_value):
        frappe.throw(_(f"Field {field} must be at most {max_value}"))
    
    return True


def validate_unique_field(context, field=None, ignore_cancelled=True, **kwargs):
    """
    Validate field value is unique across documents
    """
    doc = context.get('doc')
    value = doc.get(field)
    
    if not value:
        return True
    
    filters = {field: value}
    if doc.name:
        filters['name'] = ['!=', doc.name]
    if ignore_cancelled:
        filters['docstatus'] = ['!=', 2]
    
    existing = frappe.db.exists(doc.doctype, filters)
    if existing:
        frappe.throw(_(f"Value '{value}' for {field} already exists in {existing}"))
    
    return True


def validate_conditional_required(context, condition_field=None, condition_value=None, required_fields=None, **kwargs):
    """
    Make fields required when a condition is met
    """
    doc = context.get('doc')
    
    # Check if condition is met
    actual_value = doc.get(condition_field)
    if str(actual_value) != str(condition_value):
        return True  # Condition not met, pass
    
    # Validate required fields
    field_list = parse_field_list(required_fields)
    missing = []
    
    for field in field_list:
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
