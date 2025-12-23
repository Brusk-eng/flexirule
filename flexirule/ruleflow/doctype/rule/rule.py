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
        trigger_condition_expression: DF.Code | None
    # end: auto-generated types
    def validate(self):
        """
        Validate Rule Configuration
        """
        self.ensure_start_node()
        self.compile_conditions()
        self.validate_actions()
        self.validate_no_sub_rule_cycles()

    def before_insert(self):
        self.ensure_start_node()

    def ensure_start_node(self):
        """Ensure a Start Node (Entry Action) exists with ID 'root'"""
        # Check if root exists
        root_action = next((a for a in self.actions if a.action_id == 'root'), None)
        
        if not root_action:
            # Determine next step if there are existing actions
            # We pick the first action that is NOT 'root'
            first_action_id = None
            existing_actions = [a for a in self.actions if a.action_id != 'root']
            if existing_actions:
                first_action_id = existing_actions[0].action_id or existing_actions[0].name

            self.append('actions', {
                "action_type": "Entry Action",
                "action_label": _(self.trigger_event or "Start"),
                "action_id": "root",
                "is_enabled": 1,
                "position_x": 50,
                "position_y": 250,
                "next_step_if_true": first_action_id # Link to first existing action
            })
    def compile_conditions(self):
        from flexirule.ruleflow.core.compiler import ConditionCompiler
        compiler = ConditionCompiler()
        
        # Compile Trigger
        if self.trigger_condition:
            try:
                self.trigger_condition_expression = compiler.compile(self.trigger_condition)
                # Validate compiled expression
                is_valid, error = compiler.validate(self.trigger_condition_expression)
                if not is_valid:
                    frappe.throw(_("Invalid Trigger Condition: {0}").format(error))
            except ValueError as e:
                frappe.throw(_("Error compiling Trigger Condition: {0}").format(str(e)))
            except Exception as e:
                frappe.throw(_("Error compiling Trigger Condition: {0}").format(str(e)))
        
    def validate_actions(self):
        if not self.actions:
            return

        from flexirule.ruleflow.core.compiler import ConditionCompiler
        compiler = ConditionCompiler()

        for action in self.actions:
            # Compile Action Condition
            if action.action_type == 'Condition' and action.condition_json:
                try:
                    action.condition_expression = compiler.compile(action.condition_json)
                    # Validate compiled expression
                    is_valid, error = compiler.validate(action.condition_expression)
                    if not is_valid:
                        frappe.throw(_("Invalid Condition in Action {0}: {1}").format(action.action_label, error))
                except ValueError as e:
                    frappe.throw(_("Error compiling Action {0} Condition: {1}").format(action.action_label, str(e)))
                except Exception as e:
                    frappe.throw(_("Error compiling Action {0} Condition: {1}").format(action.action_label, str(e)))

            # 1. Validate JSON fields syntax
            # Use new 'config' field with backward compatibility
            config_value = getattr(action, 'config', None) or getattr(action, 'method_config', None)
            self._validate_json_field(config_value, _("Action {0}: Configuration").format(action.action_label))
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
        schema = method.input_schema or method.config_schema
        
        # Use new 'config' field with backward compatibility for 'method_config'
        config_value = getattr(action, 'config', None) or getattr(action, 'method_config', None)
        
        if schema and config_value:
            # Extract mapped fields to skip required check in static config
            mapped_fields = []
            if action.input_mapping:
                try:
                    mapping = frappe.parse_json(action.input_mapping)
                    if isinstance(mapping, dict):
                        mapped_fields = list(mapping.keys())
                except:
                    pass
            
            # Use new 'config' field with backward compatibility for 'method_config'
            config_value = getattr(action, 'config', None) or getattr(action, 'method_config', None)
            validate_config(config_value, schema, mapped_fields=mapped_fields)

    def validate_no_sub_rule_cycles(self):
        """
        Detect direct or indirect cycles in sub-rule references.
        Uses DFS with path tracking to detect any cycle in the full sub-rule graph.
        """
        # Collect sub-rule names referenced by this rule
        sub_rules = set()
        for action in (self.actions or []):
            if action.action_type == 'Sub-Rule' and action.rule:
                sub_rules.add(action.rule)
        
        if not sub_rules:
            return  # No sub-rules, no cycles possible
        
        def get_child_sub_rules(rule_name):
            """Get all sub-rule references from a rule"""
            return frappe.db.get_all(
                "Rule Action",
                filters={
                    "parent": rule_name,
                    "action_type": "Sub-Rule",
                    "rule": ["is", "set"]
                },
                pluck="rule"
            )
        
        def dfs_detect_cycle(current_rule, path, globally_visited):
            """DFS with path tracking to detect any cycle"""
            if current_rule in path:
                # Cycle detected - build cycle path from where it starts
                cycle_start = path.index(current_rule)
                cycle_path = path[cycle_start:] + [current_rule]
                return ' → '.join(cycle_path)
            
            if current_rule in globally_visited:
                return None  # Already fully explored, no cycle from here
            
            path.append(current_rule)
            
            child_sub_rules = get_child_sub_rules(current_rule)
            for child in child_sub_rules:
                if child:
                    result = dfs_detect_cycle(child, path.copy(), globally_visited)
                    if result:
                        return result
            
            globally_visited.add(current_rule)
            return None
        
        # Start DFS from this rule
        globally_visited = set()
        initial_path = [self.name]
        
        for sub_rule in sub_rules:
            if sub_rule:
                cycle = dfs_detect_cycle(sub_rule, initial_path.copy(), globally_visited)
                if cycle:
                    frappe.throw(
                        _("Cycle detected in sub-rule graph: {0}").format(cycle)
                    )

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
