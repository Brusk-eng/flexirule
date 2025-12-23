
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
    found_methods = set()

    for module_name in allowed_modules:
        try:
            # Import module
            module = importlib.import_module(module_name)
            
            # Inspect members
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) and getattr(obj, "_is_process_method", False):
                    # Standardized Process Method discovery
                    method_path = f"{module_name}.{name}"
                    try:
                        _sync_single_method(module_name, name, obj)
                        count += 1
                        found_methods.add(method_path)
                    except Exception as e:
                        frappe.log_error(f"Sync Error: {method_path}", str(e))
                        errors += 1
                        print(_("Failed to sync {0}: {1}").format(method_path, str(e)))

        except ImportError:
            print(_("Could not import module: {0}").format(module_name))
            errors += 1
        except Exception as e:
            print(_("Error scanning module {0}: {1}").format(module_name, str(e)))
            errors += 1

    # Prune orphaned methods (Managed only)
    managed_methods_in_db = frappe.get_all(
        "Process Method", 
        filters={"is_managed": 1}, 
        pluck="name", 
        ignore_permissions=True 
    ) or []

    methods_to_delete = set(managed_methods_in_db) - found_methods

    if methods_to_delete:
        print(_("Pruning {0} orphaned methods...").format(len(methods_to_delete)))
        for path in methods_to_delete:
            # Check for dependencies before deleting
            if frappe.db.count("Rule Action", filters={"process_method": path}) > 0:
                print(_("Skipping {0}: Used in active Rules.").format(path))
                errors += 1
                continue
            
            frappe.delete_doc("Process Method", path, force=1)
            print(_("Deleted {0}").format(path))

    frappe.db.commit()
    print(_("Sync Complete. Synced: {0}, Pruned: {1}, Errors: {2}").format(count, len(methods_to_delete), errors))


def _sync_single_method(module_name, func_name, func):
    """
    Sync a single function to Process Method DocType
    """
    metadata = getattr(func, "_metadata", {})
    method_path = f"{module_name}.{func_name}"

    # Prepare data 
    doc_data = {
        "doctype": "Process Method",
        "method_name": metadata.get("method_name") or frappe.unscrub(func_name),
        "module": "Ruleflow",
        "category": metadata.get("category", "Custom"),
        "method_path": method_path,
        "return_type": metadata.get("return_type", "None"),
        "description": metadata.get("description") or func.__doc__,
        "is_managed": 1  # Mark as code-driven
    }

    if frappe.db.exists("Process Method", method_path):
        doc = frappe.get_doc("Process Method", method_path)
        doc.update(doc_data)
        doc.save(ignore_permissions=True)
    else:
        doc_data["name"] = method_path
        doc = frappe.get_doc(doc_data)
        doc.insert(ignore_permissions=True)

