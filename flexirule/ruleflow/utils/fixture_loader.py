# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

import frappe
import json
import os

def safe_load_process_methods():
    """
    Safely load Process Methods from fixtures
    - Updates code-defined fields (method_path, schemas)
    - Preserves user-defined fields (description, enabled status, timeout)
    - Inserts new methods if missing
    """
    fixture_path = frappe.get_app_path("flexirule", "fixtures/process_method.json")
    
    if not os.path.exists(fixture_path):
        return
        
    with open(fixture_path, 'r') as f:
        methods = json.load(f)
        
    for item in methods:
        method_path = item.get('method_path')
        if not method_path:
            continue
            
        # Check by name (since we enforced name=method_path in Phase 1)
        if frappe.db.exists("Process Method", method_path):
            doc = frappe.get_doc("Process Method", method_path)
            
            # Update ONLY specific code-critical fields
            doc.method_path = item.get('method_path')
            doc.config_schema = item.get('config_schema')
            doc.input_schema = item.get('input_schema')
            doc.output_schema = item.get('output_schema')
            doc.side_effects = item.get('side_effects')
            doc.return_type = item.get('return_type')
            
            # Don't touch: is_enabled, description, usage_example, category (user might reorganize)
            
            doc.save(ignore_permissions=True)
            print(f"Updated: {method_path}")
        else:
            # Insert new
            print(f"Inserting: {method_path}")
            doc = frappe.get_doc(item)
            doc.insert(ignore_permissions=True)
