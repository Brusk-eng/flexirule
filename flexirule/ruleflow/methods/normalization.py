# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Normalization process methods for the Bolton Rule Engine
Provides text cleaning and standardization as reusable process methods

All methods use the context-first pattern:
    def method_name(context, **kwargs):
        doc = context.get('doc')
        ...
"""

import frappe
from frappe import _
import re
from typing import Any, List, Dict, Optional


# Built-in transformations (same as NormalizationPipeline)
TRANSFORMATIONS = {
    'trim': lambda x: x.strip() if isinstance(x, str) else x,
    'lowercase': lambda x: x.lower() if isinstance(x, str) else x,
    'uppercase': lambda x: x.upper() if isinstance(x, str) else x,
    'remove_spaces': lambda x: x.replace(' ', '') if isinstance(x, str) else x,
    'remove_punctuation': lambda x: re.sub(r'[^\w\s]', '', x) if isinstance(x, str) else x,
    'remove_extra_spaces': lambda x: re.sub(r'\s+', ' ', x).strip() if isinstance(x, str) else x,
    'remove_numbers': lambda x: re.sub(r'\d+', '', x) if isinstance(x, str) else x,
    'remove_special_chars': lambda x: re.sub(r'[^a-zA-Z0-9\s]', '', x) if isinstance(x, str) else x,
    'slug': lambda x: re.sub(r'[^\w\s-]', '', x).strip().lower().replace(' ', '-') if isinstance(x, str) else x,
    'alphanumeric_only': lambda x: re.sub(r'[^a-zA-Z0-9]', '', x) if isinstance(x, str) else x,
    'digits_only': lambda x: re.sub(r'[^\d]', '', x) if isinstance(x, str) else x,
    'title_case': lambda x: x.title() if isinstance(x, str) else x,
}


def apply_transformations(value: Any, transformations: List[str]) -> Any:
    """
    Apply a list of transformations to a value
    
    Args:
        value: Value to transform
        transformations: List of transformation names
        
    Returns:
        Transformed value
    """
    if value is None:
        return None
    
    result = value
    
    for transform_name in transformations:
        transform_func = TRANSFORMATIONS.get(transform_name)
        if transform_func:
            try:
                result = transform_func(result)
            except Exception as e:
                frappe.log_error(
                    title=f"Normalization Error: {transform_name}",
                    message=f"Value: {value}\nError: {str(e)}"
                )
        else:
            frappe.logger().warning(f"Unknown transformation: {transform_name}")
    
    return result


def normalize_field(context, source_field, transformations, target_field=None, **kwargs):
    """
    Normalize a field in-place or to a target field
    
    Args:
        context: Execution context containing 'doc'
        source_field: Field to normalize
        transformations: List of transformation names (e.g., ['trim', 'lowercase'])
        target_field: Optional target field (defaults to source_field)
        
    Returns:
        Normalized value
    """
    doc = context.get('doc')
    
    # Parse transformations if passed as string/JSON
    if isinstance(transformations, str):
        import json
        try:
            transformations = json.loads(transformations)
        except json.JSONDecodeError:
            # Try comma-separated
            transformations = [t.strip() for t in transformations.split(',')]
    
    value = doc.get(source_field)
    if value is None:
        return None
    
    normalized = apply_transformations(value, transformations)
    
    # Set to target field (or source field if not specified)
    dest_field = target_field or source_field
    doc.set(dest_field, normalized)
    
    return normalized


def normalize_field_to_context(context, source_field, transformations, context_key=None, **kwargs):
    """
    Normalize a field value and store in context for fuzzy matching
    Does NOT modify the document
    
    Args:
        context: Execution context (must have 'vars' dict and 'doc')
        source_field: Field to normalize
        transformations: List of transformation names
        context_key: Key to store in context['vars'] (defaults to 'normalized_{source_field}')
        
    Returns:
        The context key where value was stored
    """
    doc = context.get('doc')
    
    # Parse transformations if passed as string/JSON
    if isinstance(transformations, str):
        import json
        try:
            transformations = json.loads(transformations)
        except json.JSONDecodeError:
            transformations = [t.strip() for t in transformations.split(',')]
    
    value = doc.get(source_field)
    if value is None:
        return None
    
    normalized = apply_transformations(value, transformations)
    
    # Store in context for later use (e.g., fuzzy matching)
    key = context_key or f"normalized_{source_field}"
    
    if 'vars' not in context:
        context['vars'] = {}
    
    context['vars'][key] = normalized
    
    return key


def normalize_multiple_fields(context, field_config, store_in_context=False, **kwargs):
    """
    Batch normalize multiple fields with their own transformation configs
    
    Args:
        context: Execution context containing 'doc'
        field_config: List of dicts with keys:
            - fieldname: Field to normalize
            - transformations: List of transformation names
            - target_field: Optional target field
        store_in_context: If True, store normalized values in context instead of doc
        
    Returns:
        Dict of field -> normalized value
    """
    doc = context.get('doc')
    
    # Parse field_config if passed as string/JSON
    if isinstance(field_config, str):
        import json
        field_config = json.loads(field_config)
    
    results = {}
    
    for config in field_config:
        fieldname = config.get('fieldname')
        transformations = config.get('transformations', [])
        target_field = config.get('target_field')
        
        if not fieldname:
            continue
        
        value = doc.get(fieldname)
        if value is None:
            continue
        
        normalized = apply_transformations(value, transformations)
        
        if store_in_context:
            # Store in context
            key = target_field or f"normalized_{fieldname}"
            if 'vars' not in context:
                context['vars'] = {}
            context['vars'][key] = normalized
        else:
            # Set on document
            dest_field = target_field or fieldname
            doc.set(dest_field, normalized)
        
        results[fieldname] = normalized
    
    return results


def normalize_for_comparison(context, source_field, transformations, **kwargs):
    """
    Normalize a field for comparison purposes WITHOUT modifying the document
    Useful for fuzzy matching where you want to compare normalized values
    
    Args:
        context: Execution context containing 'doc'
        source_field: Field to normalize
        transformations: List of transformation names
        
    Returns:
        Normalized value (doc is not modified)
    """
    doc = context.get('doc')
    
    # Parse transformations if passed as string/JSON
    if isinstance(transformations, str):
        import json
        try:
            transformations = json.loads(transformations)
        except json.JSONDecodeError:
            transformations = [t.strip() for t in transformations.split(',')]
    
    value = doc.get(source_field)
    if value is None:
        return None
    
    return apply_transformations(value, transformations)


def get_available_transformations(**kwargs):
    """
    Helper function to get list of available transformation names
    
    Returns:
        List of transformation names
    """
    return list(TRANSFORMATIONS.keys())


# Whitelisted API for testing/preview
@frappe.whitelist()
def preview_normalization(text, transformations):
    """
    Preview normalization result without saving
    
    Args:
        text: Text to normalize
        transformations: JSON array or comma-separated list of transformation names
        
    Returns:
        Normalized text
    """
    import json
    
    if isinstance(transformations, str):
        try:
            transformations = json.loads(transformations)
        except json.JSONDecodeError:
            transformations = [t.strip() for t in transformations.split(',')]
    
    return apply_transformations(text, transformations)
