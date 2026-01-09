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

import re
import unicodedata
from typing import Any, Dict, List

import frappe
from frappe import _

import flexirule

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

TRANSFORMATIONS: dict[str, callable] = {
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
# PREDEFINED PROFILES (UI-selectable)
# =============================================================================

NORMALIZATION_PROFILES: dict[str, list[str]] = {
    "default": [
        "trim",
        "unicode_normalize",
        "casefold",
        "translate_chars",
        "remove_extra_spaces",
    ],
    "arabic_strict": [
        "trim",
        "unicode_normalize",
        "casefold",
        "translate_chars",
        "remove_punctuation",
        "remove_extra_spaces",
    ],
    "email": [
        "trim",
        "lowercase",
        "email_normalize",
    ],
    "phone": [
        "numeric_only",
    ],
    "slug": [
        "trim",
        "lowercase",
        "remove_punctuation",
        "remove_extra_spaces",
        "slug",
    ],
}

# =============================================================================
# CORE HELPERS
# =============================================================================

def resolve_transformations(value) -> list[str]:
    """
    Accepts:
    - profile name
    - newline / comma separated string
    - list
    """
    if not value:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, str):
        value = value.strip()

        # profile
        if value in NORMALIZATION_PROFILES:
            return NORMALIZATION_PROFILES[value]

        # multiline / csv
        return [v.strip() for v in re.split(r"[,\n]", value) if v.strip()]

    return []


def apply_transformations(value: Any, transformations: list[str]) -> Any:
    if value is None:
        return None

    result = value

    for name in transformations:
        func = TRANSFORMATIONS.get(name)
        if not func:
            frappe.logger().warning(f"Unknown transformation: {name}")
            continue

        try:
            result = func(result)
        except Exception as e:
            frappe.log_error(
                title="FlexiRule Normalization Error",
                message=f"Step: {name}\nValue: {value}\n{e}",
            )

    return result


@flexirule.processmethod(
    category="Transformation",
    side_effects="Modifies Doc",
    config_schema={
        "fields": [
            {
                "fieldname": "source_field",
                "fieldtype": "DocField",
                "label": "Source Field",
                "reqd": 1,
                "options": "parent.document_type"
            },
            {
                "fieldname": "target_field",
                "fieldtype": "DocField",
                "label": "Target Field",
                "options": "parent.document_type"
            },
     {
    "fieldname": "transformations",
    "fieldtype": "MultiSelectList",
    "label": "Transformations",
    "reqd": 1,
    "options": [
        {"label": "Trim", "value": "trim"},
        {"label": "Lowercase", "value": "lowercase"},
        {"label": "Uppercase", "value": "uppercase"},
        {"label": "Remove Spaces", "value": "remove_spaces"},
        {"label": "Remove Extra Spaces", "value": "remove_extra_spaces"},
        {"label": "Remove Punctuation", "value": "remove_punctuation"},
        {"label": "Remove Numbers", "value": "remove_numbers"},
        {"label": "Slug", "value": "slug"},
        {"label": "Digits Only", "value": "numeric_only"},
        {"label": "Title Case", "value": "title_case"},
    ]
}

        ]
    },
    description="Normalize a field in-place or to a target field."
)
def normalize_field(context, source_field, transformations, target_field=None, **kwargs):
    """
    Normalize a field in-place or to a target field.

    Frontend MultiSelect passes transformations as a newline-separated string.
    Backend JSON Schema expects a list/array for validation.
    """
    doc = context.get('doc')
    if not doc:
        return None

    # Convert frontend string (newline-separated) into a list
    if isinstance(transformations, str):
        transformations = [t.strip() for t in transformations.split("\n") if t.strip()]

    # Ensure we have a list
    if not isinstance(transformations, list):
        transformations = [transformations]

    value = doc.get(source_field)
    if value is None:
        return None

    normalized = apply_transformations(value, transformations)

    # Set to target field (or source field if not specified)
    dest_field = target_field or source_field
    doc.set(dest_field, normalized)

    return normalized

@flexirule.processmethod(
    category="Transformation",
    side_effects="Pure",
    return_type="String",
    config_schema={
        "fields": [
            {
                "fieldname": "source_field",
                "fieldtype": "DocField",
                "label": "Source Field",
                "reqd": 1,
                "options": "parent.document_type"
            },
            {
                "fieldname": "context_key",
                "fieldtype": "Data",
                "label": "Variable Name"
            },
            {
                "fieldname": "transformations",
                "fieldtype": "MultiSelect",
                "label": "Transformations",
                "reqd": 1,
                "options": "trim\nlowercase\nremove_extra_spaces\nremove_punctuation\nnumeric_only"
            }
        ]
    },
    description="Normalize a field and store it in context (vars). Does not modify doc."
)
def normalize_field_to_context(context, source_field, transformations, context_key=None, **kwargs):
    """
    Normalize a field value and store in context for fuzzy matching
    Does NOT modify the document
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


@flexirule.processmethod(
    category="Transformation",
    side_effects="Modifies Doc",
    return_type="Dict",
    config_schema={
        "fields": [
            {
                "fieldname": "field_config",
                "fieldtype": "Table",
                "label": "Field Configuration",
                "reqd": 1,
                "table_fields": [
                    {
                        "fieldname": "fieldname",
                        "fieldtype": "DocField",
                        "label": "Field",
                        "reqd": 1,
                        "options": "parent.document_type"
                    },
                    {
                        "fieldname": "transformations",
                        "fieldtype": "MultiSelect",
                        "label": "Transformations",
                        "reqd": 1,
                        "options": "trim\nlowercase\nremove_extra_spaces\nslug"
                    }
                ]
            },
            {
                "fieldname": "store_in_context",
                "fieldtype": "Check",
                "label": "Store in context",
                "default": 0
            }
        ]
    },
    description="Batch normalize multiple fields."
)
def normalize_multiple_fields(context, field_config, store_in_context=False, **kwargs):
    """
    Batch normalize multiple fields with their own transformation configs
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


@flexirule.processmethod(
    category="Transformation",
    side_effects="Pure",
    return_type="String",
    config_schema={
        "fields": [
            {
                "fieldname": "source_field",
                "fieldtype": "DocField",
                "label": "Source Field",
                "reqd": 1,
                "options": "parent.document_type"
            },
            {
                "fieldname": "transformations",
                "fieldtype": "MultiSelect",
                "label": "Transformations",
                "reqd": 1,
                "options": "trim\nlowercase\nremove_extra_spaces\nremove_punctuation\nnumeric_only"
            }
        ]
    },
    description="Normalize field for comparison only (returns value, no side effects)."
)
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
