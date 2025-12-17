import frappe
import importlib
import inspect
import json
from frappe import _

def sync_process_methods():
    """
    Synchronize Process Methods from code to the database.
    Scans modules defined in 'flexirule_allowed_modules' hook.
    """
    allowed_modules = frappe.get_hooks("flexirule_allowed_modules")
    if not allowed_modules:
        frappe.msgprint(_("No flexirule_allowed_modules defined in hooks."))
        return

    count = 0
    errors = 0
    
    # Track found methods to identify what to disable (optional, skipping for now)
    found_methods = set()

    for module_name in allowed_modules:
        try:
            # Import module
            module = importlib.import_module(module_name)
            
            # Inspect members
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) and getattr(obj, "_is_process_method", False):
                    try:
                        _sync_single_method(module_name, name, obj)
                        count += 1
                        found_methods.add(f"{module_name}.{name}")
                    except Exception as e:
                        frappe.log_error(_("Process Method Sync Error"), f"Failed to sync {module_name}.{name}: {str(e)}")
                        errors += 1
                        print(f"Failed to sync {module_name}.{name}: {str(e)}")

        except ImportError:
            print(f"Could not import module: {module_name}")
            errors += 1
        except Exception as e:
            print(f"Error scanning module {module_name}: {str(e)}")
            errors += 1

    # Prune orphaned methods (Managed only)
    # Fetch all managed methods from DB
    managed_methods_in_db = frappe.get_all("Process Method", 
                                          filters={"is_managed": 1}, 
                                          pluck="method_path")
    
    methods_to_delete = set(managed_methods_in_db) - found_methods
    
    if methods_to_delete:
        print(f"Pruning {len(methods_to_delete)} orphaned methods...")
        for path in methods_to_delete:
            # Check for dependencies before deleting
            if frappe.db.count("Rule Action", filters={"process_method": path}) > 0:
                print(f"Skipping {path}: Used in active Rules. Please remove usage first.")
                errors += 1
                continue
                
            frappe.delete_doc("Process Method", path, force=1)
            print(f"Deleted {path}")

    frappe.db.commit()
    print(f"Sync Complete. Synced: {count}, Pruned: {len(methods_to_delete)}, Errors: {errors}")


def _sync_single_method(module_name, func_name, func):
    """
    Sync a single function to Process Method DocType
    """
    metadata = getattr(func, "_metadata", {})
    method_path = f"{module_name}.{func_name}"
    
    # Prepare data
    doc_data = {
        "method_name": metadata.get("method_name") or frappe.unscrub(func_name),
        "module": "Ruleflow",
        "category": metadata.get("category", "Custom"),
        "method_path": method_path,
        "return_type": metadata.get("return_type", "None"),
        "description": metadata.get("description"),
        "version": metadata.get("version", "1.0"),
        "side_effects": metadata.get("side_effects", "Pure"),
        "transactional": 1 if metadata.get("transactional") else 0,
        "creates_new_docs": 1 if metadata.get("creates_new_docs") else 0,
        "requires_permission": metadata.get("requires_permission"),
        "is_managed": 1
    }
    
    # handle schemas (stringify if dict)
    for field in ["input_schema", "output_schema", "config_schema", "usage_example"]:
        val = metadata.get(field)
        if isinstance(val, (dict, list)):
            doc_data[field] = json.dumps(val, indent=4)
        elif val:
            doc_data[field] = val
    
    # Upsert
    if frappe.db.exists("Process Method", method_path):
        doc = frappe.get_doc("Process Method", method_path)
        doc.update(doc_data)
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.get_doc({
            "doctype": "Process Method",
            **doc_data
        })
        doc.insert(ignore_permissions=True)
