# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Shared utilities for process methods
"""

import json
from typing import List, Dict, Any


def parse_field_list(fields) -> List[str]:
    """
    Parse fields from multiple formats:
    - Array: ["field1", "field2"]
    - Newline text: "field1\nfield2"
    - Comma text: "field1, field2"
    - JSON string: '["field1", "field2"]'
    
    Returns:
        List of field names
    """
    if not fields:
        return []
    
    # Already a list
    if isinstance(fields, list):
        return [f.strip() if isinstance(f, str) else f for f in fields]
    
    # String - try to parse
    if isinstance(fields, str):
        fields = fields.strip()
        
        # Try JSON first
        if fields.startswith('['):
            try:
                return json.loads(fields)
            except json.JSONDecodeError:
                pass
        
        # Newline separated
        if '\n' in fields:
            return [f.strip() for f in fields.split('\n') if f.strip()]
        
        # Comma separated
        if ',' in fields:
            return [f.strip() for f in fields.split(',') if f.strip()]
        
        # Single field
        return [fields] if fields else []
    
    return []


def parse_field_mapping(mapping) -> Dict[str, str]:
    """
    Parse field mapping from multiple formats:
    - Dict: {"source": "target"}
    - Array: [{"source_field": "a", "target_field": "b"}]
    - Text: "source:target\\nfrom:to"
    - JSON string
    
    Returns:
        Dict of source_field -> target_field
    """
    if not mapping:
        return {}
    
    # Already a dict
    if isinstance(mapping, dict):
        return mapping
    
    # Array of objects
    if isinstance(mapping, list):
        result = {}
        for item in mapping:
            if isinstance(item, dict):
                src = item.get('source_field') or item.get('source')
                tgt = item.get('target_field') or item.get('target')
                if src and tgt:
                    result[src] = tgt
        return result
    
    # String parsing
    if isinstance(mapping, str):
        mapping = mapping.strip()
        
        # Try JSON
        if mapping.startswith('{') or mapping.startswith('['):
            try:
                parsed = json.loads(mapping)
                return parse_field_mapping(parsed)
            except json.JSONDecodeError:
                pass
        
        # Text format: "source:target\nfrom:to"
        result = {}
        for line in mapping.split('\n'):
            line = line.strip()
            if ':' in line:
                parts = line.split(':', 1)
                result[parts[0].strip()] = parts[1].strip()
        return result
    
    return {}


def parse_pattern_type(pattern_type: str, custom_pattern: str = None) -> str:
    """
    Convert pattern type selection to actual regex pattern
    """
    patterns = {
        'Email': r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$',
        'Phone': r'^[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[0-9]{3,4}[-\s\.]?[0-9]{4,6}$',
        'URL': r'^https?://[^\s/$.?#].[^\s]*$',
        'Alphanumeric': r'^[a-zA-Z0-9]+$',
        'Numeric': r'^[0-9]+$',
        'Custom Regex': custom_pattern or '.*'
    }
    return patterns.get(pattern_type, custom_pattern or '.*')
