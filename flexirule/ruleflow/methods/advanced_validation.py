# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Advanced Validation process methods for the FlexiRule Rule Engine

Includes:
- Child table row validation
- Composite uniqueness checks (parent + child fields)
- Role-based permission checks
"""

import frappe
from frappe import _
from .utils import parse_field_list
from typing import Dict, List, Any, Optional
import flexirule


# ============================================================================
# CHILD TABLE VALIDATION
# ============================================================================

@flexirule.processmethod(
    category="Validation",
    side_effects="Pure",
    config_schema={
        "fields": [
            {
                "fieldname": "child_table",
                "fieldtype": "Data",
                "label": "Child Table Name",
                "reqd": 1
            },
            {
                "fieldname": "validations",
                "fieldtype": "Table",
                "label": "Validation Rules",
                "reqd": 1,
                "table_fields": [
                    {
                        "fieldname": "type",
                        "fieldtype": "Select",
                        "label": "Validation Type",
                        "options": "fields_not_equal\nfields_equal\nfield_required\nfield_greater_than\neither_field_required"
                    },
                    {
                        "fieldname": "field1",
                        "fieldtype": "Data",
                        "label": "Field 1"
                    },
                    {
                        "fieldname": "field2",
                        "fieldtype": "Data",
                        "label": "Field 2"
                    },
                    {
                        "fieldname": "value",
                        "fieldtype": "Data",
                        "label": "Value"
                    },
                    {
                        "fieldname": "error_message",
                        "fieldtype": "Data",
                        "label": "Error Message"
                    }
                ]
            }
        ]
    },
    description="Validate rows in a child table against configured rules."
)
def validate_child_table_rows(context, child_table=None, validations=None, **kwargs):
    """
    Validate each row in a child table against specified rules.
    
    Use Cases:
    - Stock Entry: source_warehouse != target_warehouse
    - Sales Order: qty > 0
    - Journal Entry: debit or credit must be > 0
    
    Args:
        context: Execution context containing 'doc'
        child_table: Name of child table field (e.g., 'items', 'accounts')
        validations: List of validation rules:
            [
                {
                    "type": "fields_not_equal",
                    "field1": "s_warehouse",
                    "field2": "t_warehouse",
                    "error_message": "Source and Target warehouse cannot be same"
                },
                {
                    "type": "field_required",
                    "field": "item_code",
                    "error_message": "Item Code is required"
                },
                {
                    "type": "field_greater_than",
                    "field": "qty",
                    "value": 0,
                    "error_message": "Quantity must be greater than 0"
                },
                {
                    "type": "either_field_required",
                    "field1": "debit",
                    "field2": "credit",
                    "error_message": "Either Debit or Credit is required"
                }
            ]
    
    Returns:
        True if all validations pass
        
    Raises:
        frappe.ValidationError if any validation fails
    """
    doc = context.get('doc')
    if not doc or not child_table or not validations:
        return True
    
    rows = doc.get(child_table) or []
    if not rows:
        return True
    
    errors = []
    
    for idx, row in enumerate(rows, start=1):
        for validation in validations:
            v_type = validation.get('type')
            error_msg = validation.get('error_message', _('Validation failed'))
            
            if v_type == 'fields_not_equal':
                field1 = validation.get('field1')
                field2 = validation.get('field2')
                val1 = row.get(field1)
                val2 = row.get(field2)
                
                if val1 and val2 and str(val1) == str(val2):
                    errors.append(f"Row {idx}: {error_msg}")
            
            elif v_type == 'fields_equal':
                field1 = validation.get('field1')
                field2 = validation.get('field2')
                val1 = row.get(field1)
                val2 = row.get(field2)
                
                if val1 and val2 and str(val1) != str(val2):
                    errors.append(f"Row {idx}: {error_msg}")
            
            elif v_type == 'field_required':
                field = validation.get('field')
                value = row.get(field)
                
                if not value and value != 0:
                    errors.append(f"Row {idx}: {error_msg}")
            
            elif v_type == 'field_greater_than':
                field = validation.get('field')
                threshold = validation.get('value', 0)
                value = row.get(field)
                
                try:
                    if value is not None and float(value) <= float(threshold):
                        errors.append(f"Row {idx}: {error_msg}")
                except (ValueError, TypeError):
                    pass
            
            elif v_type == 'field_less_than':
                field = validation.get('field')
                threshold = validation.get('value', 0)
                value = row.get(field)
                
                try:
                    if value is not None and float(value) >= float(threshold):
                        errors.append(f"Row {idx}: {error_msg}")
                except (ValueError, TypeError):
                    pass
            
            elif v_type == 'either_field_required':
                field1 = validation.get('field1')
                field2 = validation.get('field2')
                val1 = row.get(field1)
                val2 = row.get(field2)
                
                # Both empty or both zero
                has_val1 = val1 and (val1 != 0 if isinstance(val1, (int, float)) else True)
                has_val2 = val2 and (val2 != 0 if isinstance(val2, (int, float)) else True)
                
                if not has_val1 and not has_val2:
                    errors.append(f"Row {idx}: {error_msg}")
            
            elif v_type == 'field_in_list':
                field = validation.get('field')
                allowed_values = validation.get('values', [])
                value = row.get(field)
                
                if value and value not in allowed_values:
                    errors.append(f"Row {idx}: {error_msg}")
            
            elif v_type == 'field_not_in_list':
                field = validation.get('field')
                blocked_values = validation.get('values', [])
                value = row.get(field)
                
                if value and value in blocked_values:
                    errors.append(f"Row {idx}: {error_msg}")
            
            elif v_type == 'custom_expression':
                # Evaluate a Python expression
                expression = validation.get('expression')
                if expression:
                    try:
                        result = frappe.safe_eval(expression, {'row': row, 'doc': doc, 'idx': idx})
                        if not result:
                            errors.append(f"Row {idx}: {error_msg}")
                    except Exception as e:
                        frappe.log_error(f"Custom validation expression error: {e}")
    
    if errors:
        frappe.throw("<br>".join(errors), title=_("Validation Error"))
    
    return True


# ============================================================================
# COMPOSITE UNIQUENESS (PARENT + CHILD)
# ============================================================================

@flexirule.processmethod(
    category="Validation",
    side_effects="Pure",
    config_schema={
        "fields": [
            {
                "fieldname": "parent_fields",
                "fieldtype": "MultiDocField",
                "label": "Parent Fields to Match",
                "reqd": 1,
                "options": "parent.document_type"
            },
            {
                "fieldname": "child_table",
                "fieldtype": "Data",
                "label": "Child Table Name",
                "reqd": 1
            },
            {
                "fieldname": "child_fields",
                "fieldtype": "MultiDocField",
                "label": "Child Fields to Match",
                "reqd": 1,
                "options": "child_table"
            },
            {
                "fieldname": "match_mode",
                "fieldtype": "Select",
                "label": "Match Mode",
                "options": "any\nall",
                "default": "any"
            },
            {
                "fieldname": "error_message",
                "fieldtype": "Data",
                "label": "Error Message"
            }
        ]
    },
    description="Check for duplicates based on parent and child table fields."
)
def check_duplicate_with_child_fields(context, parent_fields=None, child_table=None,
                                       child_fields=None, match_mode='any',
                                       error_message=None, **kwargs):
    """
    Check for duplicate documents based on parent fields AND child table fields.
    
    Use Cases:
    - Journal Entry: same date + same party in accounts → duplicate
    - Sales Order: same customer + same item in items → duplicate
    
    Args:
        context: Execution context containing 'doc'
        parent_fields: List of parent field names to match (e.g., ['posting_date'])
        child_table: Name of child table field (e.g., 'accounts')
        child_fields: List of child field names to match (e.g., ['party', 'party_type'])
        match_mode: 'any' (match any row) or 'all' (match all rows)
        error_message: Custom error message
    
    Returns:
        True if no duplicate found
        
    Raises:
        frappe.ValidationError if duplicate found
    """
    doc = context.get('doc')
    if not doc or not parent_fields or not child_table or not child_fields:
        return True
    
    parent_field_list = parse_field_list(parent_fields)
    child_field_list = parse_field_list(child_fields)
    
    # Build parent filters
    parent_filters = {}
    for field in parent_field_list:
        value = doc.get(field)
        if value:
            parent_filters[field] = value
    
    if not parent_filters:
        return True  # No parent values to match
    
    # Exclude self
    if doc.name:
        parent_filters['name'] = ['!=', doc.name]
    parent_filters['docstatus'] = ['!=', 2]
    
    # Get current doc's child values
    current_child_rows = doc.get(child_table) or []
    current_child_values = []
    
    for row in current_child_rows:
        row_values = tuple(row.get(f) for f in child_field_list)
        if all(v for v in row_values):  # Only include if all fields have values
            current_child_values.append(row_values)
    
    if not current_child_values:
        return True  # No child values to match
    
    # Find candidate parent documents
    candidates = frappe.get_all(
        doc.doctype,
        filters=parent_filters,
        pluck='name',
        limit=100
    )
    
    if not candidates:
        return True
    
    # Check each candidate's child table
    meta = frappe.get_meta(doc.doctype)
    child_doctype = None
    for df in meta.fields:
        if df.fieldname == child_table and df.fieldtype == 'Table':
            child_doctype = df.options
            break
    
    if not child_doctype:
        return True
    
    for candidate_name in candidates:
        # Get candidate's child rows
        candidate_child_rows = frappe.get_all(
            child_doctype,
            filters={'parent': candidate_name, 'parenttype': doc.doctype},
            fields=child_field_list
        )
        
        candidate_values = []
        for row in candidate_child_rows:
            row_values = tuple(row.get(f) for f in child_field_list)
            candidate_values.append(row_values)
        
        # Check for matches
        if match_mode == 'any':
            # Any current row matches any candidate row
            for current_val in current_child_values:
                if current_val in candidate_values:
                    msg = error_message or _(
                        "Duplicate found: {0} has the same {1} with matching {2}"
                    ).format(candidate_name, ", ".join(parent_field_list), ", ".join(child_field_list))
                    frappe.throw(msg)
        
        elif match_mode == 'all':
            # All current rows match all candidate rows
            if set(current_child_values) == set(candidate_values):
                msg = error_message or _(
                    "Duplicate found: {0} has identical entries"
                ).format(candidate_name)
                frappe.throw(msg)
    
    return True


    return True


@flexirule.processmethod(
    category="Validation",
    side_effects="Pure",
    input_schema={
        "type": "object",
        "properties": {
            "date_field": {"type": "string"},
            "child_table": {"type": "string"},
            "party_field": {"type": "string"},
            "amount_field": {"type": "string"},
            "amount_tolerance": {"type": "number", "default": 0},
            "error_message": {"type": "string"}
        },
        "required": ["date_field", "child_table", "party_field"]
    },
    description="Check for duplicate Journal Entries (Date + Party + Amount)."
)
def check_duplicate_with_amount(context, date_field=None, child_table=None,
                                 party_field=None, amount_field=None,
                                 amount_tolerance=0, error_message=None, **kwargs):
    """
    Specialized duplicate check for Journal Entries with amount matching.
    
    Checks: same date + same party + same amount → duplicate
    
    Args:
        context: Execution context containing 'doc'
        date_field: Parent date field (e.g., 'posting_date')
        child_table: Child table name (e.g., 'accounts')
        party_field: Party field in child table (e.g., 'party')
        amount_field: Amount field to match (e.g., 'debit' or 'credit')
        amount_tolerance: Tolerance for amount matching (default 0 = exact)
        error_message: Custom error message
    """
    doc = context.get('doc')
    if not doc or not date_field or not child_table or not party_field:
        return True
    
    date_value = doc.get(date_field)
    if not date_value:
        return True
    
    # Build filters
    filters = {date_field: date_value, 'docstatus': ['!=', 2]}
    if doc.name:
        filters['name'] = ['!=', doc.name]
    
    candidates = frappe.get_all(doc.doctype, filters=filters, pluck='name', limit=100)
    if not candidates:
        return True
    
    # Get current doc's party/amount combinations
    current_rows = doc.get(child_table) or []
    current_combos = []
    
    for row in current_rows:
        party = row.get(party_field)
        amount = row.get(amount_field) if amount_field else None
        if party:
            current_combos.append((party, float(amount or 0)))
    
    if not current_combos:
        return True
    
    # Get child doctype
    meta = frappe.get_meta(doc.doctype)
    child_doctype = None
    for df in meta.fields:
        if df.fieldname == child_table and df.fieldtype == 'Table':
            child_doctype = df.options
            break
    
    if not child_doctype:
        return True
    
    # Check candidates
    for candidate_name in candidates:
        fields_to_fetch = [party_field]
        if amount_field:
            fields_to_fetch.append(amount_field)
        
        candidate_rows = frappe.get_all(
            child_doctype,
            filters={'parent': candidate_name, 'parenttype': doc.doctype},
            fields=fields_to_fetch
        )
        
        for current_combo in current_combos:
            current_party, current_amount = current_combo
            
            for cand_row in candidate_rows:
                cand_party = cand_row.get(party_field)
                cand_amount = float(cand_row.get(amount_field) or 0) if amount_field else 0
                
                if cand_party == current_party:
                    # Party matches, check amount if specified
                    if not amount_field:
                        msg = error_message or _(
                            "Duplicate found: {0} has the same date and party"
                        ).format(candidate_name)
                        frappe.throw(msg)
                    
                    # Check amount with tolerance
                    if abs(cand_amount - current_amount) <= amount_tolerance:
                        msg = error_message or _(
                            "Duplicate found: {0} has the same date, party, and amount"
                        ).format(candidate_name)
                        frappe.throw(msg)
    
    return True


# ============================================================================
# ROLE-BASED CHECKS
# ============================================================================

@flexirule.processmethod(
    category="Validation",
    side_effects="Pure",
    return_type="Boolean",
    config_schema={
        "fields": [
            {
                "fieldname": "roles",
                "fieldtype": "MultiSelect",
                "label": "Roles",
                "reqd": 1,
                "options": "Role"
            }
        ]
    },
    description="Check if current user has any of the specified roles (returns True if they do)."
)
def check_user_has_role(context, roles=None, **kwargs):
    """
    Check if current user has any of the specified roles.
    
    Use in Condition node:
    - If True → Skip validation (user has privilege)
    - If False → Continue to validation
    
    Args:
        context: Execution context
        roles: List of role names or comma-separated string
    
    Returns:
        Boolean: True if user has any of the specified roles
    """
    if not roles:
        return False
    
    role_list = parse_field_list(roles)
    user_roles = frappe.get_roles()
    
    for role in role_list:
        if role in user_roles:
            return True
    
    return False


@flexirule.processmethod(
    category="Validation",
    side_effects="Pure",
    return_type="Boolean",
    input_schema={
        "type": "object",
        "properties": {
            "roles": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["roles"]
    },
    description="Check if current user does NOT have permitted roles (returns True if missing roles)."
)
def check_user_not_has_role(context, roles=None, **kwargs):
    """
    Inverse of check_user_has_role.
    
    Returns True if user does NOT have any of the specified roles.
    """
    return not check_user_has_role(context, roles=roles, **kwargs)


@flexirule.processmethod(
    category="Validation",
    side_effects="Pure",
    return_type="Boolean",
    input_schema={
        "type": "object",
        "properties": {
            "doctype": {"type": "string"},
            "perm_type": {"type": "string", "enum": ["read", "write", "create", "delete", "submit", "cancel"], "default": "read"}
        }
    },
    description="Check if user has specific permission on document."
)
def check_user_permission(context, doctype=None, perm_type='read', **kwargs):
    """
    Check if current user has specific permission on a doctype.
    
    Args:
        context: Execution context
        doctype: DocType to check (defaults to current doc's doctype)
        perm_type: Permission type (read, write, create, delete, submit, cancel)
    
    Returns:
        Boolean: True if user has permission
    """
    doc = context.get('doc')
    target_doctype = doctype or (doc.doctype if doc else None)
    
    if not target_doctype:
        return False
    
    return frappe.has_permission(target_doctype, perm_type)
