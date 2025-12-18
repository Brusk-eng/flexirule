# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from flexirule.ruleflow.utils.schema_validator import validate_config
from flexirule.ruleflow.utils.graph_validator import validate_graph_integrity

class Rule(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from flexirule.ruleflow.doctype.rule_action.rule_action import RuleAction
        from frappe.core.doctype.has_role.has_role import HasRole
        from frappe.types import DF

        actions: DF.Table[RuleAction]
        apply_to_child_tables: DF.Check
        debug_mode: DF.Check
        description: DF.Text | None
        document_type: DF.Link
        execution_count: DF.Int
        execution_mode: DF.Literal["Synchronous", "Asynchronous"]
        is_active: DF.Check
        last_error: DF.Text | None
        last_executed: DF.Datetime | None
        max_execution_time: DF.Int
        options_json: DF.Code | None
        priority: DF.Int
        rule_name: DF.Data
        skip_for_roles: DF.TableMultiSelect[HasRole]
        trigger_condition: DF.Code | None
        trigger_event: DF.Literal["Manual", "Before Naming", "Before Insert", "Before Save", "Validate", "Before Submit", "After Insert", "After Save", "On Submit", "Before Cancel", "On Cancel", "On Trash", "On Update After Submit", "On Change"]
        trigger_filters: DF.Code | None
    # end: auto-generated types
    def validate(self):
        """
        Validate Rule Configuration
        """
        self.validate_actions()
        
    def validate_actions(self):
        if not self.actions:
            return

        for action in self.actions:
            # 1. Validate JSON fields syntax
            self._validate_json_field(action.method_config, _("Action {0}: Configuration").format(action.action_label))
            self._validate_json_field(action.input_mapping, _("Action {0}: Input Mapping").format(action.action_label))
            self._validate_json_field(action.output_mapping, _("Action {0}: Output Mapping").format(action.action_label))
            
            # 2. Check Process Method config against Schema
            if action.action_type == 'Process' and action.process_method:
                self._validate_action_config(action)
                
    def _validate_json_field(self, json_str, label):
        if not json_str: 
            return
        import json
        try:
            json.loads(json_str)
        except json.JSONDecodeError as e:
            frappe.throw(_("Invalid JSON in {0}: {1}").format(label, str(e)))

    def _validate_action_config(self, action):
        if not frappe.db.exists("Process Method", action.process_method):
            frappe.throw(_("Process Method not found: {0}").format(action.process_method))
            
        method = frappe.get_cached_doc("Process Method", action.process_method)
        
        # Validate Config against config_schema (if defined)
        # Note: We prioritize config_schema mostly for UI builder, 
        # but input_schema is for strict validation if present.
        schema = method.input_schema or method.config_schema
        if schema and action.method_config:
            validate_config(action.method_config, schema)

    def on_update(self):
        """
        Perform heavier checks on update, especially if Active
        """
        if self.is_active:
            validate_graph_integrity(self)

@frappe.whitelist()
def test_rule(rule_name, doctype=None, docname=None, document_json=None):
    """
    Test a rule against a document.
    Supports either an existing document (by docname) or a transient document (by document_json).
    """
    import json
    
    rule = frappe.get_doc("Rule", rule_name)
    
    if docname:
        doc = frappe.get_doc(doctype, docname)
    elif document_json:
        doc_data = json.loads(document_json)
        doc = frappe.get_doc(doc_data)
        # Transient docs might need to be 'local'
        doc.flags.ignore_permissions = True
    else:
        frappe.throw(_("Either docname or document_json must be provided"))
    
    from flexirule.ruleflow.core.coordinator import RuleCoordinator
    
    # Capture logs if possible? 
    # The requirement was "return execution logs". 
    
    from flexirule.ruleflow.core.engine import RuleEngine
    # Check if rule is actually applicable (User Request: filters must apply)
    from flexirule.ruleflow.core.coordinator import RuleCoordinator
    
    is_eligible, reason = RuleCoordinator.check_eligibility(
            rule, doc, event_name="Manual Test", skip_event_check=True
    )
    
    if not is_eligible:
            return {
                "success": False,
                "status": _("Skipped"),
                "message": frappe._("Rule Skipped: {0}").format(reason),
                "execution_log": {}
            }
    
    try:
        # Run in test_mode to prevent rollback of the rule itself during tests
        engine = RuleEngine(rule, {'test_mode': True})
        engine.execute(doc)
        
        # Get log from memory (engine.execution_log is list of dicts, not the Doc)
        # But _save_execution_log inserts a doc. We can fetch it if needed, 
        # or just rely on what we have.
        # The test expects 'status', 'message', 'execution_path'.
        
        # Fetch the latest log (created by engine even in test mode)
        # Since we are in the same transaction, we should find it.
        logs = frappe.get_all("Rule Execution Log", 
                             filters={"rule": rule_name, "reference_docname": doc.name},
                             order_by="creation desc",
                             limit=1,
                             fields=["status", "message", "execution_path"])
        
        log_data = logs[0] if logs else {}
        
        return {
            "success": True,
            "status": _(log_data.get("status", "Success")),
            "execution_log": log_data,
            "message": _("Rule {0} executed.").format(rule_name)
        }
    except Exception as e:
        return {
            "success": False,
            "status": _("Failed"),
            "error": str(e)
        }
