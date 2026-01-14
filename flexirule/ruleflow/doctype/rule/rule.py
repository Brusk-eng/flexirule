# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from flexirule.ruleflow.utils.graph_validator import validate_graph_integrity
from flexirule.ruleflow.utils.schema_validator import validate_config


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
        priority: DF.Int
        rule_name: DF.Data
        skip_for_roles: DF.TableMultiSelect[HasRole]
        status: DF.Literal[
            "Draft", "Active", "Disabled", "Invalid", "Error", "Archived"
        ]
        trigger_condition: DF.Code | None
        trigger_condition_expression: DF.Code | None
        trigger_event: DF.Literal[
            "Manual",
            "Before Naming",
            "Before Insert",
            "Before Save",
            "Validate",
            "Before Submit",
            "After Insert",
            "After Save",
            "On Submit",
            "Before Cancel",
            "On Cancel",
            "On Trash",
            "On Update After Submit",
            "On Change",
        ]

    # end: auto-generated types
    def validate(self):
        """
        Validate Rule Configuration
        """
        self.ensure_start_node()
        self.compile_conditions()
        self.validate_actions()
        self.validate_no_sub_rule_cycles()
        self.status = self.get_computed_status()

    def before_insert(self):
        self.ensure_start_node()

    def ensure_start_node(self):
        """Ensure a Start Node (Entry Action) exists with ID 'root'"""
        # Check if root exists
        root_action = next((a for a in self.actions if a.action_id == "root"), None)

        if not root_action:
            # Determine next step if there are existing actions
            # We pick the first action that is NOT 'root'
            first_action_id = None
            existing_actions = [a for a in self.actions if a.action_id != "root"]
            if existing_actions:
                first_action_id = (
                    existing_actions[0].action_id or existing_actions[0].name
                )

            self.append(
                "actions",
                {
                    "action_type": "Entry Action",
                    "action_label": _(self.trigger_event or "Start"),
                    "action_id": "root",
                    "is_enabled": 1,
                    "position_x": 50,
                    "position_y": 250,
                    "next_step_if_true": first_action_id,  # Link to first existing action
                },
            )

    def compile_conditions(self):
        from flexirule.ruleflow.core.compiler import ConditionCompiler

        compiler = ConditionCompiler()

        # Compile Trigger
        if self.trigger_condition:
            try:
                self.trigger_condition_expression = compiler.compile(
                    self.trigger_condition
                )
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
            if action.action_type == "Condition" and action.condition_json:
                try:
                    action.condition_expression = compiler.compile(
                        action.condition_json
                    )
                    # Validate compiled expression
                    is_valid, error = compiler.validate(action.condition_expression)
                    if not is_valid:
                        frappe.throw(
                            _("Invalid Condition in Action {0}: {1}").format(
                                action.action_label, error
                            )
                        )
                except ValueError as e:
                    frappe.throw(
                        _("Error compiling Action {0} Condition: {1}").format(
                            action.action_label, str(e)
                        )
                    )
                except Exception as e:
                    frappe.throw(
                        _("Error compiling Action {0} Condition: {1}").format(
                            action.action_label, str(e)
                        )
                    )

            # 1. Validate JSON fields syntax
            # Use new 'config' field with backward compatibility
            config_value = getattr(action, "config", None) or getattr(
                action, "method_config", None
            )
            self._validate_json_field(
                config_value, _("Action {0}: Configuration").format(action.action_label)
            )
            self._validate_json_field(
                action.input_mapping,
                _("Action {0}: Input Mapping").format(action.action_label),
            )
            self._validate_json_field(
                action.output_mapping,
                _("Action {0}: Output Mapping").format(action.action_label),
            )

            # 2. Check Process config against Schema
            if action.action_type == "Process" and action.process_name:
                self._validate_action_config(action)

            # 3. Validate action type-specific constraints
            self._validate_all_action_types(action)

    def get_computed_status(self):
        if self.get("is_archived"):
            return "Archived"

        if not self.is_active:
            return "Disabled"

        if not self.actions:
            return "Invalid"

        if self.trigger_condition and not self.trigger_condition_expression:
            return "Invalid"

        if self.last_error:
            return "Error"

        return "Active"

    def _validate_json_field(self, json_str, label):
        if not json_str:
            return
        import json

        try:
            json.loads(json_str)
        except json.JSONDecodeError as e:
            frappe.throw(_("Invalid JSON in {0}: {1}").format(label, str(e)))

    def _validate_action_config(self, action):
        if not frappe.db.exists("Process", action.process_name):
            frappe.throw(_("Process not found: {0}").format(action.process_name))

        process = frappe.get_cached_doc("Process", action.process_name)

        # If operation is set, validate existence and contracts
        if action.operation:
            try:
                op = process.get_operation(action.operation)

                # Validate return_variable mandatory for context-writing operations
                self._validate_return_variable_requirement(action, op)

            except Exception as e:
                frappe.throw(str(e))

    def _validate_return_variable_requirement(self, action, operation):
        """
        Enforce return_variable is set when operation writes to context.
        """
        if not operation:
            return

        writes_to = operation.writes_to
        writes_vars = operation.writes_vars
        output_schema = operation.output_schema

        requires_return_var = False

        # Check if operation writes to context
        if writes_to == "Context":
            requires_return_var = True

        # Check if operation declares writes_vars
        if writes_vars:
            try:
                parsed_vars = (
                    json.loads(writes_vars)
                    if isinstance(writes_vars, str)
                    else writes_vars
                )
                if parsed_vars and len(parsed_vars) > 0:
                    requires_return_var = True
            except Exception:
                pass

        # Check if operation has output_schema
        if output_schema:
            requires_return_var = True

        if requires_return_var and not action.return_variable:
            frappe.throw(
                _(
                    "Action '{0}' uses operation '{1}' which writes to context. "
                    "Please specify a Return Variable Name."
                ).format(action.action_label, action.operation)
            )

    def _validate_all_action_types(self, action):
        """
        Validate constraints specific to each action type.
        """
        action_type = action.action_type

        if action_type == "Sub-Rule":
            if not action.rule:
                frappe.throw(
                    _("Action '{0}' is a Sub-Rule but no Rule is selected.").format(
                        action.action_label
                    )
                )
            # Prevent self-reference
            if action.rule == self.name:
                frappe.throw(
                    _("Action '{0}' cannot reference its own Rule as Sub-Rule.").format(
                        action.action_label
                    )
                )

        elif action_type == "Condition":
            if not action.condition_json and not action.condition_expression:
                frappe.throw(
                    _(
                        "Action '{0}' is a Condition but no condition is defined."
                    ).format(action.action_label)
                )

        elif action_type == "Loop":
            # Loop actions should have a valid iterator configuration
            config = self._parse_json_field(action.config)
            if not config.get("iterator_var") and not config.get("collection"):
                frappe.msgprint(
                    _(
                        "Action '{0}' is a Loop but iterator configuration may be incomplete."
                    ).format(action.action_label),
                    alert=True,
                )

        elif action_type == "Switch":
            # Switch should have cases defined
            config = self._parse_json_field(action.config)
            if not config.get("cases"):
                frappe.msgprint(
                    _("Action '{0}' is a Switch but no cases are defined.").format(
                        action.action_label
                    ),
                    alert=True,
                )

    def _parse_json_field(self, json_str):
        """Parse JSON field safely, return empty dict on failure."""
        if not json_str:
            return {}
        try:
            return json.loads(json_str) if isinstance(json_str, str) else json_str
        except Exception:
            return {}

    def validate_no_sub_rule_cycles(self):
        """
        Detect direct or indirect cycles in sub-rule references.
        Uses DFS with path tracking to detect any cycle in the full sub-rule graph.
        """
        # Collect sub-rule names referenced by this rule
        sub_rules = set()
        for action in self.actions or []:
            if action.action_type == "Sub-Rule" and action.rule:
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
                    "rule": ["is", "set"],
                },
                pluck="rule",
            )

        def dfs_detect_cycle(current_rule, path, globally_visited):
            """DFS with path tracking to detect any cycle"""
            if current_rule in path:
                # Cycle detected - build cycle path from where it starts
                cycle_start = path.index(current_rule)
                cycle_path = path[cycle_start:] + [current_rule]
                return " → ".join(cycle_path)

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
                cycle = dfs_detect_cycle(
                    sub_rule, initial_path.copy(), globally_visited
                )
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

    is_eligible, reason = RuleCoordinator.check_eligibility(
        rule, doc, event_name="Manual Test", skip_event_check=True
    )

    if not is_eligible:
        return {
            "success": False,
            "status": _("Skipped"),
            "message": frappe._("Rule Skipped: {0}").format(reason),
            "execution_log": {},
        }

    try:
        # Run in test_mode to prevent rollback of the rule itself during tests
        engine = RuleEngine(rule, {"test_mode": True})
        engine.execute(doc)

        # Get log from memory (engine.execution_log is list of dicts, not the Doc)
        # But _save_execution_log inserts a doc. We can fetch it if needed,
        # or just rely on what we have.
        # The test expects 'status', 'message', 'execution_path'.

        # Fetch the latest log (created by engine even in test mode)
        # Since we are in the same transaction, we should find it.
        logs = frappe.get_all(
            "Rule Execution Log",
            filters={"rule": rule_name, "reference_docname": doc.name},
            order_by="creation desc",
            limit=1,
            fields=["status", "message", "execution_path"],
        )

        log_data = logs[0] if logs else {}

        return {
            "success": True,
            "status": _(log_data.get("status", "Success")),
            "execution_log": log_data,
            "message": _("Rule {0} executed.").format(rule_name),
        }
    except Exception as e:
        return {"success": False, "status": _("Failed"), "error": str(e)}
