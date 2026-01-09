# DEPRECTATED
from functools import wraps

import frappe


def processmethod(
    category="Custom",
    description=None,
    version="1.0",
    return_type="None",
    side_effects="Pure",
    transactional=False,
    creates_new_docs=False,
    input_schema=None,
    output_schema=None,
    config_schema=None,
    usage_example=None,
    requires_permission=None,
):
    """
    Decorator to register a Process Method.
    Metadata is attached to the function object and synced to the database.

    Args:
        category (str): Category (Validation, Enrichment, etc.)
        description (str): Method description
        version (str): Method version
        return_type (str): Return type string
        side_effects (str): "Pure", "Modifies Doc", "External Call"
        transactional (bool): If True, method handles DB transactions (sync only)
        creates_new_docs (bool): If True, method creates NEW docs (allowed in Async)
        input_schema (dict/str): JSON Schema for input mapping
        output_schema (dict/str): JSON Schema for output mapping
        config_schema (dict/str): JSON Schema for configuration
        usage_example (dict/str): Example usage config
        requires_permission (str): Role needed to run
    """

    def decorator(func):
        # Attach metadata to the function
        func._is_process_method = True
        func._metadata = {
            "method_name": frappe.unscrub(func.__name__),
            "category": category,
            "description": description or func.__doc__,
            "version": version,
            "return_type": return_type,
            "side_effects": side_effects,
            "transactional": transactional,
            "creates_new_docs": creates_new_docs,
            "input_schema": input_schema,
            "output_schema": output_schema,
            "config_schema": config_schema,
            "usage_example": usage_example,
            "requires_permission": requires_permission,
        }

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Ensure wrapper has the metadata too
        wrapper._is_process_method = True
        wrapper._metadata = func._metadata

        return wrapper

    return decorator
