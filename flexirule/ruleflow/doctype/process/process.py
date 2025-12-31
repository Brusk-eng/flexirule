# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

import json
from pathlib import Path

import frappe
from frappe import _
from frappe.model.document import Document


class Process(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from flexirule.ruleflow.doctype.process_operation.process_operation import ProcessOperation
        from frappe.types import DF

        module: DF.Link
        process_name: DF.Data
        operations: DF.Table[ProcessOperation]
    # end: auto-generated types

    def on_update(self):
        """Clear metadata cache when process is updated."""
        clear_process_cache(self.name)

    def after_insert(self):
        """Create boilerplate files in developer_mode."""
        if frappe.conf.developer_mode:
            self.create_boilerplate_files()
    
    def create_boilerplate_files(self):
        """
        Create {name}.json, {name}.py, {name}.js boilerplate files.
        Mirrors Report boilerplate creation pattern.
        """
        module_path = Path(frappe.get_module_path(self.module))
        process_folder = module_path / "process" / frappe.scrub(self.name)
        
        # Create directory
        process_folder.mkdir(parents=True, exist_ok=True)
        
        # Create __init__.py
        init_file = process_folder / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# Copyright (c) 2025, FlexiRule and contributors\n# For license information, please see license.txt\n")
        
        scrubbed_name = frappe.scrub(self.name)
        
        # Create {name}.json
        json_file = process_folder / f"{scrubbed_name}.json"
        if not json_file.exists():
            json_content = {
                "process_name": self.name,
                "module": self.module,
                "description": f"{self.name} process operations",
                "operations": []
            }
            import json as json_module
            json_file.write_text(json_module.dumps(json_content, indent=2))
        
        # Create {name}.py
        py_file = process_folder / f"{scrubbed_name}.py"
        if not py_file.exists():
            py_content = f'''# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
{self.name} Process

File-backed execution following the Frappe Script Report pattern.
"""

import frappe
from frappe import _


# ============================================================
# OPERATIONS
# ============================================================

def example_operation(context, config):
    """
    Example operation.
    
    Args:
        context: Execution context with 'doc', 'dry_run', etc.
        config: Configuration dict
    
    Returns:
        Result value
    """
    doc = context.get("doc")
    # TODO: Implement operation logic
    return None


# ============================================================
# DISPATCHER — single entry point
# ============================================================

_OPERATIONS = {{
    "example_operation": example_operation,
}}


def execute(context, func=None, config=None):
    """
    Execute a process operation.
    
    Args:
        context: Execution context
        func: Operation function name
        config: Configuration dict
    
    Returns:
        Operation result
    """
    if not func:
        frappe.throw(_("Operation function name is required"))
    
    if func not in _OPERATIONS:
        frappe.throw(_("Unknown operation: {{0}}").format(func))
    
    return _OPERATIONS[func](context, config or {{}})
'''
            py_file.write_text(py_content)
        
        # Create {name}.js
        js_file = process_folder / f"{scrubbed_name}.js"
        if not js_file.exists():
            js_content = f'''// Copyright (c) 2025, FlexiRule and contributors
// For license information, please see license.txt

/**
 * {self.name} Process - Rule Builder Adapter
 */

flexirule.processes = flexirule.processes || {{}};

flexirule.processes["{self.name}"] = {{
    operations: [
        {{
            func_name: "example_operation",
            label: __("Example Operation"),
            description: __("Example operation description"),
            category: "{self.name}",
            icon: "play",
            color: "#6366f1",
            
            get_config_fields: function(frm) {{
                return [
                    // Add config fields here
                ];
            }}
        }}
    ],
    
    get_operation: function(func_name) {{
        return this.operations.find(op => op.func_name === func_name);
    }},
    
    get_visible_operations: function() {{
        return this.operations.filter(op => op.visible !== false);
    }}
}};
'''
            js_file.write_text(js_content)
        
        frappe.msgprint(_(
            "Created boilerplate files at {0}. "
            "Please edit the files to add your operations."
        ).format(str(process_folder)), indicator="green")

    def execute_operation(self, func_name, context, config=None):
        """
        Execute a single operation from this process.
        
        Args:
            func_name: Operation function name
            context: Execution context dict
            config: Configuration dict (merged with DB overrides)
        
        Returns:
            Operation result
        """
        # 1. Find operation row in child table
        operation = None
        for op in self.operations:
            if op.func_name == func_name:
                operation = op
                break
        
        if not operation:
            frappe.throw(_("Operation {0} not configured in process {1}").format(
                func_name, self.name
            ))
        
        # 2. Check enabled
        if not operation.enabled:
            frappe.throw(_("Operation {0} is disabled").format(func_name))
        
        # 3. Merge configs: provided config overrides DB config
        db_config = frappe.parse_json(operation.config_json or "{}")
        merged_config = {**db_config, **(config or {})}
        
        # 4. Resolve module and call execute()
        result = self._call_execute(func_name, context, merged_config)
        
        return result
    
    def _call_execute(self, func_name, context, config):
        """
        Resolve module path and call execute().
        Mirrors Report.execute_module() pattern.
        """
        method_path = get_process_module_dotted_path(self.module, self.name) + ".execute"
        
        execute_fn = frappe.get_attr(method_path)
        
        return execute_fn(context, func=func_name, config=config)


# ============================================================
# MODULE PATH RESOLUTION
# ============================================================

def get_process_module_dotted_path(module, process_name):
    """
    Get module path for process file.
    Mirrors get_report_module_dotted_path() from Frappe.
    
    Convention: {app}.{module}.process.{name}.{name}
    Example: flexirule.ruleflow.process.mdm.mdm
    """
    return (
        frappe.local.module_app[frappe.scrub(module)]
        + "."
        + frappe.scrub(module)
        + ".process."
        + frappe.scrub(process_name)
        + "."
        + frappe.scrub(process_name)
    )


# ============================================================
# METADATA LOADING
# ============================================================

def get_process_metadata(process_name):
    """
    Load process_name.json from file.
    Same pattern as Report.execute_module().
    """
    try:
        process_doc = frappe.get_cached_doc("Process", process_name)
    except frappe.DoesNotExistError:
        return None
        
    module = process_doc.module or "Ruleflow"
    
    # Build path: {app}/{module}/process/{name}/{name}.json
    app = frappe.local.module_app.get(frappe.scrub(module))
    if not app:
        return None
    
    json_path = (
        Path(frappe.get_app_path(app))
        / frappe.scrub(module)
        / "process"
        / frappe.scrub(process_name)
        / f"{frappe.scrub(process_name)}.json"
    )
    
    if json_path.exists():
        with open(json_path) as f:
            return json.load(f)
    
    return None


# ============================================================
# CACHING LAYER — avoids file I/O on every execution
# ============================================================

def get_cached_process_metadata(process_name):
    """Load and cache process_name.json. Invalidate on Process save."""
    cache_key = f"process_metadata:{process_name}"
    metadata = frappe.cache.get_value(cache_key)
    if metadata is None:
        metadata = get_process_metadata(process_name)
        if metadata:
            frappe.cache.set_value(cache_key, metadata)
    return metadata


def get_cached_operation_def(process_name, func_name):
    """Get cached operation definition."""
    metadata = get_cached_process_metadata(process_name)
    if not metadata:
        return {}
    for op in metadata.get("operations", []):
        if op.get("func_name") == func_name:
            return op
    return {}


def clear_process_cache(process_name=None):
    """Clear cache. Call from Process.on_update()."""
    if process_name:
        frappe.cache.delete_value(f"process_metadata:{process_name}")
    else:
        frappe.cache.delete_keys("process_metadata:*")


# ============================================================
# CONFIG VALIDATION
# ============================================================

def validate_config_against_schema(config, schema):
    """Validate config values against Frappe field schema."""
    fields = schema.get("fields", [])
    
    for field in fields:
        fieldname = field.get("fieldname")
        value = config.get(fieldname)
        
        # Check required
        if field.get("reqd") and not value and value != 0:
            frappe.throw(_("Field {0} is required").format(field.get("label") or fieldname))
        
        # Check options for Select
        if field.get("fieldtype") == "Select" and value:
            options = (field.get("options") or "").split("\n")
            if value not in options:
                frappe.throw(_("Invalid value '{0}' for {1}").format(value, field.get("label") or fieldname))


# ============================================================
# WHITELISTED APIs FOR FRONTEND
# ============================================================

@frappe.whitelist()
def get_process_js_paths():
    """
    Get JS adapter paths for all processes.
    Returns dict mapping process_name -> JS file path (if exists).
    Uses Frappe's module path for cross-app extensibility.
    """
    processes = frappe.get_all("Process", fields=["name", "module"])
    result = {}
    
    for proc in processes:
        scrubbed = frappe.scrub(proc.name)
        
        try:
            # Get module path using Frappe's API
            module_path = Path(frappe.get_module_path(proc.module))
            js_file = module_path / "process" / scrubbed / f"{scrubbed}.js"
            
            if js_file.exists():
                # Convert to web-accessible path
                # Format: /assets/{app}/js/process/{name}/{name}.js (copied via build)
                # OR use frappe.get_pymodule_path and convert to assets path
                
                # Get app name from module
                app = frappe.db.get_value("Module Def", proc.module, "app_name") or "flexirule"
                
                # Return path relative to assets
                result[proc.name] = f"/assets/{app}/ruleflow/process/{scrubbed}/{scrubbed}.js"
        except Exception:
            pass  # JS not available
    
    return result


@frappe.whitelist()
def get_process_js_content(process_name):
    """
    Get the JS content for a process adapter.
    Returns the raw JS file content or None if not found.
    """
    if not process_name:
        return None
    
    proc = frappe.get_doc("Process", process_name)
    scrubbed = frappe.scrub(proc.name)
    
    try:
        module_path = Path(frappe.get_module_path(proc.module))
        js_file = module_path / "process" / scrubbed / f"{scrubbed}.js"
        
        if js_file.exists():
            return js_file.read_text()
    except Exception:
        pass
    
    return None

