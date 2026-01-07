# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

import frappe
from frappe import _
import re
import unicodedata
from typing import Any, List, Dict


def execute(context, func=None, config=None):
    """
    Execute a normalization operation.
    """
    if not func:
        frappe.throw(_("Operation function name is required"))
    
    if func not in _OPERATIONS:
        frappe.throw(_("Unknown operation: {0}. Available: {1}").format(
            func, ", ".join(_OPERATIONS.keys())
        ))
    
    return _OPERATIONS[func](context, config or {}) 

# =============================================================================
# TRANSLATION TABLE (borrowed conceptually from UPH)
# =============================================================================

TRANSLATION_TABLE = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا",
    "ى": "ي", "ة": "ه",
    "ؤ": "و", "ئ": "ي",
    "ـ": "",
    **{chr(0x660 + i): str(i) for i in range(10)},  # Arabic digits
})

# =============================================================================
# TRANSFORMATIONS (single-arg, stateless)
# =============================================================================

TRANSFORMATIONS: Dict[str, callable] = {
    "trim": lambda x: x.strip() if isinstance(x, str) else x,
    "lowercase": lambda x: x.lower() if isinstance(x, str) else x,
    "uppercase": lambda x: x.upper() if isinstance(x, str) else x,
    "casefold": lambda x: x.casefold() if isinstance(x, str) else x,

    "unicode_normalize": lambda x: unicodedata.normalize("NFKD", x)
        if isinstance(x, str) else x,

    "translate_chars": lambda x: x.translate(TRANSLATION_TABLE)
        if isinstance(x, str) else x,

    "remove_spaces": lambda x: x.replace(" ", "") if isinstance(x, str) else x,
    "remove_extra_spaces": lambda x: re.sub(r"\s+", " ", x).strip()
        if isinstance(x, str) else x,

    "remove_punctuation": lambda x: re.sub(r"[^\w\s]", "", x)
        if isinstance(x, str) else x,

    "remove_numbers": lambda x: re.sub(r"\d+", "", x)
        if isinstance(x, str) else x,

    "numeric_only": lambda x: re.sub(r"\D", "", x)
        if isinstance(x, str) else x,

    "alphanumeric_only": lambda x: re.sub(r"[^\w]", "", x)
        if isinstance(x, str) else x,

    "slug": lambda x: re.sub(r"[^\w\s-]", "", x)
        .strip().lower().replace(" ", "-")
        if isinstance(x, str) else x,

    "title_case": lambda x: x.title() if isinstance(x, str) else x,

    "email_normalize": lambda x: (
        f"{x.split('@')[0].split('+')[0].replace('.', '').lower()}@{x.split('@')[1].lower()}"
        if isinstance(x, str) and "@" in x else x
    ),
}

# =============================================================================
# CORE HELPERS
# =============================================================================

def apply_transformations(value, transformations):
    """
    Apply a list of transformation keys to a value.
    """
    if value is None: # Keep original None handling
        return None
    
    if not transformations:
        return value
    
    # Handle list of dicts (Table format from UI)
    # [{ "transformation": "trim" }, ...]
    if isinstance(transformations, list) and transformations and isinstance(transformations[0], dict):
        transformations = [t.get('transformation') for t in transformations if t.get('transformation')]
    
    # Handle Comma Separated Strings (MultiSelect Tags format)
    if isinstance(transformations, str):
        transformations = [t.strip() for t in transformations.split(',') if t.strip()]

    for transform_name in transformations: # Renamed 'transform' to 'transform_name' to avoid conflict with TRANSFORMATIONS
        # Backward compat: ignore invalid types
        if not isinstance(transform_name, str): 
            continue
            
        transform_name = transform_name.lower().strip()
        func = TRANSFORMATIONS.get(transform_name)
        if not func:
            frappe.logger().warning(f"Unknown transformation: {transform_name}") # Keep original warning
            continue

        try:
            value = func(value) # Apply transformation to 'value' directly
        except Exception as e: # Keep original error logging
            frappe.log_error(
                title="FlexiRule Normalization Error",
                message=f"Step: {transform_name}\nValue: {value}\n{e}",
            )
    return result

# =============================================================================
# OPERATIONS
# =============================================================================

def normalize_field(context, config):
    """
    Normalize a field in-place or to a target field.
    """
    doc = context.get('doc')
    if not doc:
        return None

    source_field = config.get('source_field')
    transformations = config.get('transformations')
    target_field = config.get('target_field')

    # Convert frontend string (newline-separated) into a list
    if isinstance(transformations, str):
        transformations = [t.strip() for t in transformations.split("\n") if t.strip()]

    # Ensure we have a list
    if not isinstance(transformations, list):
        transformations = [transformations] if transformations else []

    value = doc.get(source_field)
    if value is None:
        return None

    normalized = apply_transformations(value, transformations)

    # Set to target field (or source field if not specified)
    dest_field = target_field or source_field
    doc.set(dest_field, normalized)

    return normalized

def normalize_field_to_context(context, config):
    """
    Normalize a field value and store in context (vars).
    Does NOT modify the document.
    """
    doc = context.get('doc')
    if not doc:
        return None

    source_field = config.get('source_field')
    transformations = config.get('transformations')
    context_key = config.get('context_key')

    # Parse transformations if passed as string/JSON
    if isinstance(transformations, str):
        try:
            import json
            transformations = json.loads(transformations)
        except (ValueError, TypeError):
            transformations = [t.strip() for t in transformations.split(',') if t.strip()]
    
    if not isinstance(transformations, list):
         transformations = [transformations] if transformations else []
    
    value = doc.get(source_field)
    if value is None:
        return None
    
    normalized = apply_transformations(value, transformations)
    
    key = context_key or f"normalized_{source_field}"
    
    if 'vars' not in context:
        context['vars'] = {}
    
    context['vars'][key] = normalized
    
    return key


def normalize_multiple_fields(context, config):
    """
    Batch normalize multiple fields with their own transformation configs.
    """
    doc = context.get('doc')
    if not doc:
        return {}
    
    field_config = config.get('field_config')
    store_in_context = config.get('store_in_context')

    # Parse field_config if passed as string/JSON
    if isinstance(field_config, str):
        import json
        try:
            field_config = json.loads(field_config)
        except Exception:
            field_config = []
    
    if not field_config:
        return {}

    results = {}
    
    for item in field_config:
        fieldname = item.get('fieldname')
        transformations = item.get('transformations', [])
        target_field = item.get('target_field')
        
        if not fieldname:
            continue
        
        value = doc.get(fieldname)
        if value is None:
            continue

        # Handle transformations string format
        if isinstance(transformations, str):
             transformations = [t.strip() for t in transformations.split("\n") if t.strip()]
        
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

# Whitelisted API for testing/preview
@frappe.whitelist()
def preview_normalization(text, transformations):
    """
    Preview normalization result without saving
    """
    import json
    if isinstance(transformations, str):
        try:
            transformations = json.loads(transformations)
        except Exception:
            transformations = [t.strip() for t in transformations.split(',')]
    
    return apply_transformations(text, transformations)


# ============================================================
# DISPATCHER
# ============================================================

_OPERATIONS = {
    "normalize_field": normalize_field,
    "normalize_field_to_context": normalize_field_to_context,
    "normalize_multiple_fields": normalize_multiple_fields
}

