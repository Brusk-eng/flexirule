# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

import json
import frappe


def parse_field_list(fields) -> list[str]:
    """Parse fields from multiple formats (list, newline, comma, JSON)"""
    if not fields:
        return []
    if isinstance(fields, list):
        return [f.strip() if isinstance(f, str) else f for f in fields]
    if isinstance(fields, str):
        fields = fields.strip()
        if fields.startswith("["):
            try:
                return json.loads(fields)
            except json.JSONDecodeError:
                pass
        if "\n" in fields:
            return [f.strip() for f in fields.split("\n") if f.strip()]
        if "," in fields:
            return [f.strip() for f in fields.split(",") if f.strip()]
        return [fields]
    return []


def parse_pattern_type(pattern_type, custom_pattern=None):
    """Return regex pattern based on type"""
    patterns = {
        "Email": r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        "Phone": r"^\+?1?\d{9,15}$",
        "URL": r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+",
        "Alphanumeric": r"^[a-zA-Z0-9 ]*$",
        "Numeric": r"^-?\d*\.?\d*$",
    }
    if pattern_type == "Custom Regex":
        return custom_pattern
    return patterns.get(pattern_type, custom_pattern)


def parse_field_mapping(mapping) -> dict:
    """Parse field mapping from list of dicts (table) or JSON string"""
    if not mapping:
        return {}

    if isinstance(mapping, str):
        try:
            mapping = json.loads(mapping)
        except json.JSONDecodeError:
            return {}

    if isinstance(mapping, list):
        # Convert list of dicts to a single dict
        result = {}
        for item in mapping:
            if isinstance(item, dict):
                source = item.get("source_field")
                target = item.get("target_field")
                if source and target:
                    result[source] = target
        return result

    if isinstance(mapping, dict):
        return mapping

    return {}
