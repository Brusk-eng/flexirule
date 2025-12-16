# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Whitelisted API functions for Bolton Rule Engine
"""

import frappe
from frappe import _
import json


# Layout fieldtypes to exclude by default
LAYOUT_FIELDTYPES = [
    "Tab Break", "Section Break", "Column Break", 
    "HTML", "Fold", "Heading"
]

# System fields
SYSTEM_FIELDS = [
    {"value": "name", "label": "ID (name)", "fieldtype": "Data", "group": "System"},
    {"value": "owner", "label": "Created By (owner)", "fieldtype": "Link", "group": "System"},
    {"value": "creation", "label": "Created On (creation)", "fieldtype": "Datetime", "group": "System"},
    {"value": "modified", "label": "Modified On (modified)", "fieldtype": "Datetime", "group": "System"},
    {"value": "modified_by", "label": "Modified By (modified_by)", "fieldtype": "Link", "group": "System"},
    {"value": "docstatus", "label": "Document Status (docstatus)", "fieldtype": "Int", "group": "System"},
]


@frappe.whitelist()
def get_doctype_fields(doctype, filters=None):
    """
    Get fields for DocField autocomplete - grouped by parent/child tables
    
    Args:
        doctype: DocType name
        filters: JSON string with options:
            - include_child_fields: bool (default: true)
            - include_system_fields: bool (default: false)
            - fieldtypes: list (whitelist specific types)
            - exclude_fieldtypes: list (blacklist types)
    
    Returns:
        dict: {
            "parent_fields": [...],
            "child_tables": [
                {"table_name": "items", "doctype": "Sales Invoice Item", "fields": [...]}
            ],
            "system_fields": [...] if include_system_fields
        }
    """
    if not doctype:
        return {"parent_fields": [], "child_tables": [], "system_fields": []}
    
    # Parse filters
    if isinstance(filters, str):
        filters = json.loads(filters) if filters else {}
    elif filters is None:
        filters = {}
    
    include_child = filters.get("include_child_fields", True)
    include_system = filters.get("include_system_fields", False)
    allowed_types = filters.get("fieldtypes")
    excluded_types = filters.get("exclude_fieldtypes", LAYOUT_FIELDTYPES)
    
    # Get meta
    try:
        meta = frappe.get_meta(doctype)
    except Exception:
        return {"parent_fields": [], "child_tables": [], "system_fields": []}
    
    result = {
        "parent_fields": [],
        "child_tables": [],
        "system_fields": []
    }
    
    # Process parent fields
    for df in meta.fields:
        if should_include_field(df, allowed_types, excluded_types):
            result["parent_fields"].append({
                "value": df.fieldname,
                "label": f"{df.label or df.fieldname}",
                "fieldtype": df.fieldtype,
                "options": df.options,
                "description": f"{df.fieldtype}" + (f" → {df.options}" if df.options else "")
            })
    
    # Process child tables
    if include_child:
        for df in meta.fields:
            if df.fieldtype == "Table" and df.options:
                child_fields = get_child_table_fields(
                    df.options, 
                    df.fieldname,
                    allowed_types, 
                    excluded_types
                )
                if child_fields:
                    result["child_tables"].append({
                        "table_fieldname": df.fieldname,
                        "table_label": df.label or df.fieldname,
                        "child_doctype": df.options,
                        "fields": child_fields
                    })
    
    # Add system fields
    if include_system:
        result["system_fields"] = SYSTEM_FIELDS
    
    return result


def get_child_table_fields(child_doctype, table_fieldname, allowed_types=None, excluded_types=None):
    """Get fields from a child table doctype"""
    try:
        meta = frappe.get_meta(child_doctype)
    except Exception:
        return []
    
    fields = []
    for df in meta.fields:
        if should_include_field(df, allowed_types, excluded_types):
            fields.append({
                "value": f"{table_fieldname}.{df.fieldname}",
                "label": f"{df.label or df.fieldname}",
                "fieldtype": df.fieldtype,
                "options": df.options,
                "description": f"{df.fieldtype}" + (f" → {df.options}" if df.options else "")
            })
    
    return fields


def should_include_field(df, allowed_types=None, excluded_types=None):
    """Check if field should be included based on filters"""
    # Check whitelist
    if allowed_types and df.fieldtype not in allowed_types:
        return False
    
    # Check blacklist
    if excluded_types and df.fieldtype in excluded_types:
        return False
    
    return True


@frappe.whitelist()
def test_rule(rule_name, doctype, docname):
    """Test a rule against a specific document"""
    try:
        from flexirule.ruleflow.core.engine import RuleEngine
        
        rule_doc = frappe.get_doc("Rule", rule_name)
        doc = frappe.get_doc(doctype, docname)
        
        # Check if rule is actually applicable (User Request: filters must apply)
        from flexirule.ruleflow.core.coordinator import RuleCoordinator
        is_eligible, reason = RuleCoordinator.check_eligibility(
             rule_doc, doc, event_name="Manual Test", skip_event_check=True
        )
        
        if not is_eligible:
             return {
                 "success": False,
                 "message": _("Rule Skipped: {0}").format(reason),
                 "execution_log": {}
             }
        
        engine = RuleEngine(rule_doc, {'test_mode': True})
        result = engine.execute(doc)
        
        return {
            "success": True,
            "message": _("Rule '{0}' executed successfully").format(rule_doc.rule_name),
            "execution_log": engine.execution_log
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def clear_cache(doctype=None):
    """Clear rule cache"""
    try:
        from flexirule.ruleflow.core.coordinator import RuleCoordinator
        RuleCoordinator.clear_cache(doctype)
        return {"success": True, "message": _("Cache cleared")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_process_methods(category=None):
    """Get available process methods"""
    filters = {"is_enabled": 1}
    if category:
        filters["category"] = category
    
    return frappe.get_all(
        "Process Method",
        filters=filters,
        fields=["name", "method_name", "category", "description", "config_schema"],
        order_by="category, method_name"
    )


@frappe.whitelist()
def get_schema_field_options(schema_field, parent_doctype, current_values=None):
    """
    Get options for a schema field dynamically
    Used for dependent DocField sources
    """
    if not schema_field or not parent_doctype:
        return []
    
    field = json.loads(schema_field) if isinstance(schema_field, str) else schema_field
    current = json.loads(current_values) if isinstance(current_values, str) else (current_values or {})
    
    # Resolve options source
    options = field.get("options", "")
    
    if options == "parent.document_type":
        target_dt = parent_doctype
    elif options in current:
        target_dt = current[options]
    else:
        target_dt = options
    
    if not target_dt:
        return []
    
    return get_doctype_fields(target_dt, json.dumps(field.get("filters", {})))


@frappe.whitelist()
def get_rule_versions(rule_name, limit=20):
    """Get version history for a rule"""
    from flexirule.ruleflow.doctype.rule.rule_version_hooks import get_rule_versions as _get_versions
    return _get_versions(rule_name, int(limit))


@frappe.whitelist()
def restore_rule_version(rule_name, version_name):
    """Restore a rule to a previous version"""
    from flexirule.ruleflow.doctype.rule.rule_version_hooks import restore_rule_version as _restore
    return _restore(rule_name, version_name)


@frappe.whitelist()
def export_rule(rule_name):
    """Export a rule to JSON"""
    from flexirule.ruleflow.utils.import_export import export_rule as _export
    return _export(rule_name)


@frappe.whitelist()
def import_rule(import_data, overwrite=False):
    """Import a rule from JSON"""
    from flexirule.ruleflow.utils.import_export import import_rule as _import
    overwrite = frappe.parse_json(overwrite) if isinstance(overwrite, str) else overwrite
    return _import(import_data, overwrite)


@frappe.whitelist()
def get_action_context_schema(rule_name, action_id):
    """
    Get available context variables for a specific action in rule flow.
    Used by UI to enable context-aware field selection.
    """
    rule = frappe.get_doc("Rule", rule_name)
    
    result = {
        "doc_fields": [],
        "predecessor_outputs": []
    }
    
    # Get doc fields
    try:
        fields_data = get_doctype_fields(rule.document_type)
        result["doc_fields"] = fields_data.get("parent_fields", [])
    except Exception:
        pass
    
    # Build action maps
    action_map = {}
    for a in rule.actions:
        key = a.action_id or a.name
        action_map[key] = a
    
    # Find predecessors by traversing graph backwards
    predecessors = set()
    queue = [action_id]
    visited = set()
    
    while queue:
        current_id = queue.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)
        
        for action in rule.actions:
            action_key = action.action_id or action.name
            if action.next_step_if_true == current_id or action.next_step_if_false == current_id:
                predecessors.add(action_key)
                queue.append(action_key)
    
    # Get output schemas for predecessors
    for pred_id in predecessors:
        action = action_map.get(pred_id)
        if not action or not action.process_method:
            continue
        
        output_schema = None
        try:
            method = frappe.get_cached_doc("Process Method", action.process_method)
            if method.output_schema:
                output_schema = json.loads(method.output_schema)
        except Exception:
            pass
        
        result["predecessor_outputs"].append({
            "action_id": action.action_id or action.name,
            "action_label": action.action_label,
            "return_variable": action.return_variable,
            "output_schema": output_schema
        })
    
    return result
