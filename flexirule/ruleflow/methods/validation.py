# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Validation process methods for the Bolton Rule Engine
"""

import frappe
from frappe import _
import re
from .utils import parse_field_list, parse_pattern_type
import flexirule


@flexirule.processmethod(
    category="Validation",
    side_effects="Pure",
    return_type="Boolean",
    config_schema={
        "fields": [
            {
                "fieldname": "fields",
                "fieldtype": "MultiDocField",
                "label": "Required Fields",
                "reqd": 1,
                "options": "parent.document_type"
            }
        ]
    },
    description="Validate that specified fields have values"
)
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


@flexirule.processmethod(
    category="Validation",
    side_effects="Pure",
    return_type="Boolean",
    config_schema={
        "fields": [
            {
                "fieldname": "field",
                "fieldtype": "DocField",
                "label": "Field",
                "reqd": 1,
                "options": "parent.document_type"
            },
            {
                "fieldname": "pattern_type",
                "fieldtype": "Select",
                "label": "Pattern Type",
                "reqd": 1,
                "options": "Email\nPhone\nURL\nAlphanumeric\nNumeric\nCustom Regex",
                "default": "Email"
            },
            {
                "fieldname": "pattern",
                "fieldtype": "Data",
                "label": "Custom Pattern",
                "depends_on": "eval:doc.pattern_type=='Custom Regex'"
            },
            {
                "fieldname": "error_message",
                "fieldtype": "Data",
                "label": "Error Message"
            }
        ]
    },
    description="Validate field matches a pattern"
)
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


@flexirule.processmethod(
    category="Validation",
    side_effects="Pure",
    return_type="Boolean",
    config_schema={
        "fields": [
            {
                "fieldname": "field",
                "fieldtype": "DocField",
                "label": "Field",
                "reqd": 1,
                "options": "parent.document_type"
            },
            {
                "fieldname": "min_value",
                "fieldtype": "Float",
                "label": "Minimum Value"
            },
            {
                "fieldname": "max_value",
                "fieldtype": "Float",
                "label": "Maximum Value"
            }
        ]
    },
    description="Validate numeric field is within range"
)
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


@flexirule.processmethod(
    category="Validation",
    side_effects="Pure",
    return_type="Boolean",
    config_schema={
        "fields": [
            {
                "fieldname": "field",
                "fieldtype": "DocField",
                "label": "Field",
                "reqd": 1,
                "options": "parent.document_type"
            },
            {
                "fieldname": "ignore_cancelled",
                "fieldtype": "Check",
                "label": "Ignore Cancelled",
                "default": 1
            }
        ]
    },
    description="Validate field value is unique"
)
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


@flexirule.processmethod(
    category="Validation",
    side_effects="Pure",
    return_type="Boolean",
    config_schema={
        "fields": [
            {
                "fieldname": "condition_field",
                "fieldtype": "DocField",
                "label": "When Field",
                "reqd": 1,
                "options": "parent.document_type"
            },
            {
                "fieldname": "condition_value",
                "fieldtype": "Data",
                "label": "Equals",
                "reqd": 1
            },
            {
                "fieldname": "required_fields",
                "fieldtype": "MultiDocField",
                "label": "Make Required",
                "reqd": 1,
                "options": "parent.document_type"
            }
        ]
    },
    description="Make fields required based on condition"
)
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
