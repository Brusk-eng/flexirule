# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

import frappe
import json
from frappe import _

def validate_config(config_json, schema_json):
    """
    Validate configuration against a schema
    
    Args:
        config_json (str|dict): Configuration data
        schema_json (str): JSON Schema definition
    """
    if not schema_json:
        return
        
    try:
        from jsonschema import validate, ValidationError
    except ImportError:
        frappe.throw("jsonschema library not found. Please pip install jsonschema")

    # Parse inputs if they are strings
    config = _parse_json(config_json)
    schema = _parse_json(schema_json)
    
    if not schema:
        return

    try:
        validate(instance=config, schema=schema)
    except ValidationError as e:
        frappe.throw(_("Configuration Error: {0}").format(e.message))

def _parse_json(data):
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {}
    return data or {}
