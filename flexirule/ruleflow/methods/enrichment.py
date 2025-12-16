# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Enrichment process methods for the Bolton Rule Engine
"""

import frappe
from frappe import _
from .utils import parse_field_list, parse_field_mapping
from flexirule.ruleflow.decorators import process_method


@process_method(
    category="Enrichment",
    side_effects="Modifies Doc",
    return_type="Object",
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
                "fieldname": "default_value",
                "fieldtype": "Data",
                "label": "Default Value",
                "reqd": 1
            },
            {
                "fieldname": "overwrite",
                "fieldtype": "Check",
                "label": "Overwrite existing value",
                "default": 0
            }
        ]
    },
    input_schema={
        "type": "object",
        "properties": {
            "field": {"type": "string"},
            "default_value": {"type": ["string", "number", "boolean", "null"]},
            "overwrite": {"type": "boolean", "default": False}
        },
        "required": ["field"]
    },
    description="Set a default value for a field if empty"
)
def set_default_value(context, field=None, default_value=None, overwrite=False, **kwargs):
    """
    Set a default value for a field if empty (or always if overwrite=True)
    """
    doc = context.get('doc')
    current_value = doc.get(field)
    
    if overwrite or not current_value:
        doc.set(field, default_value)
        return default_value
    
    return current_value


@process_method(
    category="Enrichment",
    side_effects="Modifies Doc",
    return_type="Object",
    config_schema={
        "fields": [
            {
                "fieldname": "target_field",
                "fieldtype": "DocField",
                "label": "Target Field",
                "reqd": 1,
                "options": "parent.document_type"
            },
            {
                "fieldname": "formula",
                "fieldtype": "Small Text",
                "label": "Formula",
                "reqd": 1,
                "description": "Python expression: doc.qty * doc.rate"
            }
        ]
    },
    input_schema={
        "type": "object",
        "properties": {
            "target_field": {"type": "string"},
            "formula": {"type": "string", "description": "Python expression using doc, frappe, context"}
        },
        "required": ["target_field", "formula"]
    },
    description="Calculate a field value using a Python formula"
)
def calculate_field_value(context, target_field=None, formula=None, **kwargs):
    """
    Calculate a field value using a Python formula
    
    The formula can reference:
    - doc: the current document
    - frappe: frappe module
    - context: execution context
    """
    doc = context.get('doc')
    
    if not formula:
        return None
    
    # Safe evaluation context
    eval_context = {
        'doc': doc,
        'frappe': frappe,
        'context': context,
        '_': _
    }
    
    try:
        result = eval(formula, {"__builtins__": {}}, eval_context)
        doc.set(target_field, result)
        return result
    except Exception as e:
        frappe.log_error(
            title="Calculate Field Value Error",
            message=f"Formula: {formula}\nError: {str(e)}"
        )
        raise


@process_method(
    category="Enrichment",
    side_effects="Modifies Doc",
    return_type="Dict",
    config_schema={
        "fields": [
            {
                "fieldname": "source_link_field",
                "fieldtype": "DocField",
                "label": "Link Field",
                "reqd": 1,
                "options": "parent.document_type"
            },
            {
                "fieldname": "field_mapping",
                "fieldtype": "Table",
                "label": "Field Mapping",
                "reqd": 1,
                "table_fields": [
                    {
                        "fieldname": "source_field",
                        "fieldtype": "Data",
                        "label": "From Field",
                        "reqd": 1
                    },
                    {
                        "fieldname": "target_field",
                        "fieldtype": "DocField",
                        "label": "To Field",
                        "reqd": 1,
                        "options": "parent.document_type"
                    }
                ]
            }
        ]
    },
    input_schema={
        "type": "object",
        "properties": {
            "source_link_field": {"type": "string", "description": "Field on this doc that links to other doc"},
            "field_mapping": {"type": ["string", "object"], "description": "Map: {source_field: target_field}"}
        },
        "required": ["source_link_field", "field_mapping"]
    },
    description="Copy field values from a linked document"
)
def autocomplete_from_linked_doc(context, source_link_field=None, field_mapping=None, **kwargs):
    """
    Copy field values from a linked document
    """
    doc = context.get('doc')
    
    # Get the linked document
    link_doctype = frappe.get_meta(doc.doctype).get_field(source_link_field).options
    link_value = doc.get(source_link_field)
    
    if not link_value:
        return {}
    
    linked_doc = frappe.get_doc(link_doctype, link_value)
    mapping = parse_field_mapping(field_mapping)
    
    results = {}
    for source_field, target_field in mapping.items():
        value = linked_doc.get(source_field)
        if value is not None:
            doc.set(target_field, value)
            results[target_field] = value
    
    return results


@process_method(
    category="Enrichment",
    side_effects="Modifies Doc",
    return_type="Dict",
    config_schema={
        "fields": [
            {
                "fieldname": "template_doctype",
                "fieldtype": "Link",
                "label": "Template DocType",
                "reqd": 1,
                "options": "DocType"
            },
            {
                "fieldname": "template_name",
                "fieldtype": "Dynamic Link",
                "label": "Template Document",
                "reqd": 1,
                "options": "template_doctype"
            },
            {
                "fieldname": "field_list",
                "fieldtype": "MultiDocField",
                "label": "Fields to Copy",
                "reqd": 1,
                "options": "template_doctype"
            }
        ]
    },
    input_schema={
        "type": "object",
        "properties": {
            "template_doctype": {"type": "string"},
            "template_name": {"type": "string"},
            "field_list": {"type": ["array", "string"], "items": {"type": "string"}}
        },
        "required": ["template_doctype", "template_name", "field_list"]
    },
    description="Copy field values from a template document"
)
def copy_from_template(context, template_doctype=None, template_name=None, field_list=None, **kwargs):
    """
    Copy field values from a template document
    """
    doc = context.get('doc')
    fields = parse_field_list(field_list)
    
    if not template_doctype or not template_name:
        return {}
    
    template = frappe.get_doc(template_doctype, template_name)
    
    results = {}
    for field in fields:
        value = template.get(field)
        if value is not None:
            doc.set(field, value)
            results[field] = value
    
    return results


@process_method(
    category="Enrichment",
    side_effects="Modifies Doc",
    return_type="String",
    config_schema={
        "fields": [
            {
                "fieldname": "naming_series",
                "fieldtype": "Data",
                "label": "Naming Series",
                "reqd": 1,
                "description": "e.g., CUST-.YYYY.-"
            }
        ]
    },
    input_schema={
        "type": "object",
        "properties": {
            "naming_series": {"type": "string"}
        },
        "required": ["naming_series"]
    },
    description="Set naming series for the document"
)
def apply_naming_series(context, naming_series=None, **kwargs):
    """
    Set naming series for the document
    """
    doc = context.get('doc')
    
    if naming_series:
        doc.naming_series = naming_series
    
    return naming_series
