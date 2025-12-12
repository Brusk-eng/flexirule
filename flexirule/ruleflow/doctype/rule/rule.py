# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

import frappe
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
        document_type_filters: DF.Code | None
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
        trigger_event: DF.Literal["Before Insert", "Before Save", "Validate", "After Insert", "After Save", "Before Submit", "On Submit", "Before Cancel", "On Cancel", "On Trash"]
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
            self._validate_json_field(action.configuration, f"Action {action.action_label}: Configuration")
            self._validate_json_field(action.input_mapping, f"Action {action.action_label}: Input Mapping")
            self._validate_json_field(action.output_mapping, f"Action {action.action_label}: Output Mapping")
            
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
            frappe.throw(f"Invalid JSON in {label}: {str(e)}")

    def _validate_action_config(self, action):
        if not frappe.db.exists("Process Method", action.process_method):
            frappe.throw(f"Process Method not found: {action.process_method}")
            
        method = frappe.get_cached_doc("Process Method", action.process_method)
        
        # Validate Config against config_schema (if defined)
        # Note: We prioritize config_schema mostly for UI builder, 
        # but input_schema is for strict validation if present.
        schema = method.input_schema or method.config_schema
        if schema and action.configuration:
            validate_config(action.configuration, schema)

    def on_update(self):
        """
        Perform heavier checks on update, especially if Active
        """
        if self.is_active:
            validate_graph_integrity(self)
