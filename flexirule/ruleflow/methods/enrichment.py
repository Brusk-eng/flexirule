# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Enrichment process methods for the Bolton Rule Engine
"""

import frappe
from frappe import _
from .utils import parse_field_list, parse_field_mapping


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


def apply_naming_series(context, naming_series=None, **kwargs):
    """
    Set naming series for the document
    """
    doc = context.get('doc')
    
    if naming_series:
        doc.naming_series = naming_series
    
    return naming_series
