# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Utilities for input/output mapping in Rule Actions
"""

import json
from typing import Dict, Any


def apply_input_mapping(context: Dict, mapping_json: str, config: Dict) -> Dict:
    """
    Apply input mapping to merge context variables into config
    
    Args:
        context: Execution context with variables
        mapping_json: JSON string like {"context_var": "param_name"}
        config: Original configuration dict
        
    Returns:
        Updated config with mapped values
    """
    if not mapping_json:
        return config
    
    try:
        mapping = json.loads(mapping_json)
    except json.JSONDecodeError:
        return config
    
    result = dict(config)
    for context_key, param_name in mapping.items():
        if context_key in context:
            result[param_name] = context[context_key]
    
    return result


def apply_output_mapping(result: Any, mapping_json: str, context: Dict) -> Dict:
    """
    Apply output mapping to store result in context
    
    Args:
        result: Method execution result
        mapping_json: JSON string like {"result_key": "context_var"}
        context: Execution context to update
        
    Returns:
        Updated context
    """
    if not mapping_json:
        return context
    
    try:
        mapping = json.loads(mapping_json)
    except json.JSONDecodeError:
        return context
    
    # Handle dict results
    if isinstance(result, dict):
        for result_key, context_var in mapping.items():
            if result_key in result:
                context[context_var] = result[result_key]
    else:
        # For non-dict results, map "result" key to context
        for result_key, context_var in mapping.items():
            if result_key == "result":
                context[context_var] = result
    
    return context
