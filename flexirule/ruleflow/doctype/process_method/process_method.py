# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import json


class ProcessMethod(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        average_execution_time: DF.Float
        category: DF.Literal["Validation", "Enrichment", "Notification", "Deduplication", "Transformation", "Integration", "Custom"]
        config_schema: DF.Code | None
        description: DF.TextEditor | None
        execution_count: DF.Int
        input_schema: DF.Code | None
        is_enabled: DF.Check
        last_executed: DF.Datetime | None
        method_name: DF.Data
        method_path: DF.Data
        module: DF.Link | None
        output_schema: DF.Code | None
        requires_permission: DF.Link | None
        return_type: DF.Literal["None", "Boolean", "String", "Integer", "Float", "Object", "List", "Dict"]
        side_effects: DF.Literal["Pure", "Modifies Doc", "External Call"]
        usage_example: DF.Code | None
        version: DF.Data | None
    # end: auto-generated types
    def validate(self):
        self.method_path = self.method_path.strip() if self.method_path else ""
		
		# 1. Check Allow List (Security)
        self.validate_allowed_module()

		# 2. Check if method exists and is callable
        try:
            method = frappe.get_attr(self.method_path)
            if not callable(method):
                frappe.throw(frappe._("Path '{0}' is not a callable function").format(self.method_path))
        except ImportError:
            frappe.throw(frappe._("Could not import module for '{0}'").format(self.method_path))
        except AttributeError:
            frappe.throw(frappe._("Method '{0}' not found").format(self.method_path))
        except Exception as e:
            frappe.throw(frappe._("Invalid method path: {0}").format(str(e)))
			
		# 3. Validate Schemas
        self._validate_json_schema(self.config_schema, "Config Schema")
        self._validate_json_schema(self.input_schema, "Input Schema")
        self._validate_json_schema(self.output_schema, "Output Schema")

    def validate_allowed_module(self):


        # Get merged hooks from all installed apps
        allowed = frappe.get_hooks("flexirule_allowed_modules")

        # Normalize hook output (can be dict/list/tuple)
        allowed = list(allowed) if allowed else []

        # Determine module path (strip function name)
        module_path = ".".join(self.method_path.split(".")[:-1])

        # 🟡 Policy: If hook is NOT defined at all → allow (dev / legacy)
        if allowed is None:
            return

        # 🔴 Hook exists but empty → block everything
        if not allowed:
            frappe.throw(
                frappe._(
                    "Security Violation: No allowed FlexiRule method modules defined."
                )
            )

        # Check prefixes
        for prefix in allowed:
            if module_path == prefix or module_path.startswith(prefix + "."):
                return

        # ❌ Not allowed
        frappe.throw(
            frappe._("Security Violation: Module '{0}' is not in the Allowed List.").format(
                module_path
            )
            + "<br>"
            + frappe._("Allowed prefixes: {0}").format(", ".join(allowed))
        )

    def _validate_json_schema(self, schema_string, schema_name):
        """Helper to validate if a string is valid JSON."""
        if schema_string:
            try:
                json.loads(schema_string)
            except json.JSONDecodeError as e:
                frappe.throw(frappe._("Invalid {0} JSON: {1}").format(schema_name, str(e)))
    
    def execute(self, context, config=None, **kwargs):
        """
        Execute this process method
        
        Args:
            context: Execution context dict containing 'doc' and other variables
            config: Configuration dict for this method
            
        Returns:
            Result of the method execution
        """
        if not self.is_enabled:
            frappe.throw(f"Process method '{self.method_name}' is disabled")
        
        # Import and call the method
        method = frappe.get_attr(self.method_path)
        
        # Merge config with context-based params
        params = config or {}
        
        # Track execution stats
        import time
        start_time = time.time()
        
        try:
            result = method(context, **params)
            
            # Update stats
            execution_time = (time.time() - start_time) * 1000  # ms
            self.update_execution_stats(execution_time)
            
            return result
        except Exception as e:
            frappe.log_error(
                title=f"Process Method Error: {self.method_name}",
                message=f"Config: {params}\nError: {str(e)}"
            )
            raise
    
    def update_execution_stats(self, execution_time_ms):
        """Update execution statistics"""
        try:
            # Update atomically to avoid race conditions
            frappe.db.sql("""
                UPDATE `tabProcess Method`
                SET 
                    execution_count = execution_count + 1,
                    last_executed = NOW(),
                    average_execution_time = (
                        (average_execution_time * execution_count + %s) / (execution_count + 1)
                    )
                WHERE name = %s
            """, (execution_time_ms, self.name))
        except Exception:
            pass  # Don't fail execution due to stats update failure
    
    def get_schema_fields(self):
        """Parse config_schema and return list of field definitions"""
        if not self.config_schema:
            return []
        
        try:
            schema = json.loads(self.config_schema)
            return schema.get('fields', [])
        except json.JSONDecodeError:
            return []


@frappe.whitelist()
def test_method(method_name, config=None):
    """
    Test a process method with given configuration.
    
    Args:
        method_name: Name of the Process Method document to test
        config: JSON string or dict of configuration parameters
    
    Returns:
        dict: {
            'result': ...,
            'execution_time': 0.00,  # in ms
            'error': str (if any)
        }
    """
    import time
    import json
    
    try:
        # Load Doc (and ensure permissions)
        doc = frappe.get_doc("Process Method", method_name)
        if not doc.has_permission("read"):
            raise frappe.PermissionError
        
        # Parse Config
        if isinstance(config, str):
            config = json.loads(config)
        
        # Dummy Context (expand as needed for realistic tests)
        context = {
            'frappe': frappe,
            'doc': frappe.new_doc("User"), # Placeholder for testing
            'vars': {},
            'test_mode': True
        }
        
        start_time = time.time()
        
        # Execute (wrap in try-except to catch method-specific errors without failing the request)
        try:
            method = frappe.get_attr(doc.method_path)
            # Some methods expect 'doc' in context, others might use kwargs directly
            # Based on current engine.py, methods take (context, **config)
            result = method(context, **(config or {}))
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
            
        end_time = time.time()
        execution_time_ms = (end_time - start_time) * 1000
        
        # Note: We do NOT update statistics for test runs to avoid polluting metrics
        
        return {
            'success': success,
            'result': result,
            'execution_time': round(execution_time_ms, 2),
            'error': error
        }
    
    except Exception as e:
        frappe.log_error("Process Method Test Failed", str(e))
        return {
            'success': False,
            'error': str(e),
            'execution_time': 0
        }

def get_dashboard_data(data):
    """
    Show dashboard for linked Rules.
    Rules link to Process Method via 'actions' child table:
    Rule (parent) -> Rule Action (child) .process_method -> Process Method
    """
    return {
        "fieldname": "process_method",
        "transactions": [
            {
                "label": frappe._("Flows"),
                "items": ["Rule"]
            }
        ]
    }
