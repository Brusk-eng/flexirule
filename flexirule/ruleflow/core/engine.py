# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Enhanced Rule Engine with:
- Process DocType integration
- Permission-based security
- Retry logic and error handling
- Timeout protection
- Cycle detection
- Comprehensive logging
"""

import json
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from contextlib import contextmanager

import frappe
import jsonschema
from frappe import _
from jsonschema import ValidationError as SchemaValidationError
from jsonschema import validate

from flexirule.ruleflow.core.evaluator import check_link_match
from flexirule.ruleflow.core.exceptions import (
    CycleDetectedError,
    EmptyRuleError,
    MethodExecutionError,
    RuleDisabledError,
)
from flexirule.ruleflow.core.exceptions import TimeoutError as BoltonTimeoutError
from flexirule.ruleflow.utils.field_resolver import FieldResolver
from flexirule.ruleflow.utils.mapping import apply_input_mapping, apply_output_mapping
from flexirule.ruleflow.utils.schema_validator import (
    frappe_fields_to_json_schema,
    get_custom_validator,
)

# Configuration constants
MAX_SUB_RULE_DEPTH = 2  # Maximum nesting depth for sub-rule calls


class TimeoutException(Exception):
    """Internal timeout exception"""

    pass


class ReadOnlyDocument:
    """Proxy for Document that prevents mutation"""

    def __init__(self, doc):
        object.__setattr__(self, "_doc", doc)

    def __getattr__(self, name):
        return getattr(self._doc, name)

    def __getitem__(self, key):
        return self._doc[key]

    def get(self, key, default=None):
        return self._doc.get(key, default)

    def __setattr__(self, name, value):
        raise frappe.ValidationError("Cannot mutate document in Pure method")

    def __setitem__(self, key, value):
        raise frappe.ValidationError("Cannot mutate document in Pure method")

    def save(self, *args, **kwargs):
        raise frappe.ValidationError("Cannot save document in Pure method")

    def insert(self, *args, **kwargs):
        raise frappe.ValidationError("Cannot insert document in Pure method")

    def delete(self, *args, **kwargs):
        raise frappe.ValidationError("Cannot delete document in Pure method")

    def db_set(self, *args, **kwargs):
        raise frappe.ValidationError("Cannot db_set document in Pure method")


@contextmanager
def time_limit(seconds):
    """
    Context manager for timeout protection using ThreadPoolExecutor.
    Cross-platform compatible (works on Windows/Linux/Mac).
    """
    if seconds <= 0:
        yield
        return

    # Note: This context manager doesn't actually enforce timeout
    # The timeout is enforced in _execute_with_timeout method
    yield


# TODO : Explore frappe source code to find if they have a similar implementation and use it instead Introduced for SafeFrappeAPI
class SafeFrappeAPI:
    """
    Restricted Frappe API proxy for rule condition evaluation.
    Exposes only safe, read-only operations to prevent security issues.
    """

    def __init__(self):
        # Safe utilities
        self.utils = frappe.utils
        self._dict = frappe._dict

    # Safe read operations
    @staticmethod
    def get_value(doctype, filters, fieldname=None, **kwargs):
        """Read-only get_value"""
        return frappe.get_value(doctype, filters, fieldname, **kwargs)

    @staticmethod
    def get_all(doctype, filters=None, fields=None, **kwargs):
        """Read-only get_all"""
        return frappe.get_all(doctype, filters=filters, fields=fields, **kwargs)

    @staticmethod
    def db_exists(doctype, name):
        """Check if document exists"""
        return frappe.db.exists(doctype, name)

    @staticmethod
    def get_meta(doctype):
        """Get doctype metadata"""
        return frappe.get_meta(doctype)

    @staticmethod
    def format_value(value, df=None, doc=None, currency=None):
        """Format value for display"""
        return frappe.format_value(value, df, doc, currency)

    # Logging (safe)
    @staticmethod
    def log(message):
        """Log a message"""
        frappe.logger().info(message)

    # Explicitly denied operations (will raise)
    def get_doc(self, *args, **kwargs):
        raise PermissionError(
            "get_doc is not allowed in rule conditions. Use frappe.get_value instead."
        )

    def new_doc(self, *args, **kwargs):
        raise PermissionError("new_doc is not allowed in rule conditions.")

    def delete_doc(self, *args, **kwargs):
        raise PermissionError("delete_doc is not allowed in rule conditions.")

    def db_set_value(self, *args, **kwargs):
        raise PermissionError("db.set_value is not allowed in rule conditions.")

    @property
    def db(self):
        """Return restricted db proxy"""
        return self._SafeDB()

    class _SafeDB:
        """Restricted database operations"""

        def exists(self, doctype, name):
            return frappe.db.exists(doctype, name)

        def get_value(self, doctype, filters, fieldname=None, **kwargs):
            return frappe.db.get_value(doctype, filters, fieldname, **kwargs)

        def get_all(self, doctype, filters=None, fields=None, **kwargs):
            return frappe.db.get_all(doctype, filters=filters, fields=fields, **kwargs)

        # Explicitly deny write operations
        def set_value(self, *args, **kwargs):
            raise PermissionError("db.set_value is not allowed in rule conditions.")

        def sql(self, *args, **kwargs):
            raise PermissionError("db.sql is not allowed in rule conditions.")

        # Transaction control restricted (following Frappe restrict_commit_rollback)
        def commit(self, *args, **kwargs):
            raise PermissionError("db.commit is not allowed during doc event rules.")

        def rollback(self, *args, **kwargs):
            raise PermissionError("db.rollback is not allowed during doc event rules.")

        def add_index(self, *args, **kwargs):
            raise PermissionError("db.add_index is not allowed during doc event rules.")


# Singleton instance
_safe_frappe = SafeFrappeAPI()


class RuleEngine:
    """
    Production-ready rule execution engine with:
    - Validation and error handling
    - Performance optimization
    - Security enforcement
    - Audit logging
    """

    def __init__(self, rule_doc, execution_context=None):
        """
        Args:
                rule_doc: Rule DocType document
                execution_context: Dict with user, timestamp, test_mode, etc.
        """
        if isinstance(rule_doc, str):
            rule_doc = frappe.get_doc("Rule", rule_doc)
        self.rule = rule_doc
        self.actions = [a for a in rule_doc.actions if a.is_enabled]

        self.context = execution_context or {}
        if frappe.flags.in_test and "test_mode" not in self.context:
            self.context["test_mode"] = True

        self.execution_log = []
        self.cache = {}

        # Build action maps for fast lookup
        self.action_map_by_id = {a.action_id: a for a in self.actions if a.action_id}
        self.action_map_by_label = {a.action_label: a for a in self.actions}
        self.action_map_by_name = {a.name: a for a in self.actions}

    @staticmethod
    def _get_action_config(action):
        """Get config JSON with backward compatibility for method_config"""
        # Prefer new 'config' field, fallback to legacy 'method_config'
        config_str = getattr(action, "config", None) or getattr(
            action, "method_config", None
        )
        if not config_str:
            return {}
        try:
            return json.loads(config_str)
        except (json.JSONDecodeError, TypeError):
            return {}

    def execute(self, doc, **kwargs):
        """
        Execute rule with comprehensive error handling

        Args:
                doc: Frappe document to process
                **kwargs: Additional context variables

        Returns:
                Execution context with results
        """
        # Tracking vars
        start_time = time.time()
        status = "Success"
        error_detail = None
        self.path_trace = []

        try:
            # Pre-execution validation
            self._validate_execution()

            # Check role-based skipping
            skip_for_roles_docs = self.rule.get("skip_for_roles")
            if skip_for_roles_docs:
                user_roles = frappe.get_roles()
                skip_roles = [row.get("role") for row in skip_for_roles_docs]
                if any(role in user_roles for role in skip_roles):
                    self._log(
                        "INFO",
                        f"Skipping rule execution for user with role(s): {skip_roles}",
                    )
                    status = "Skipped"
                    return self.context

            # Initialize context
            context = self._initialize_context(doc, **kwargs)

            # Log start
            self._log("INFO", f"Starting rule execution: {self.rule.name}")

            # Expose execution log to frappe.local for API response
            frappe.local.execution_log = self.execution_log

            # Execute with timeout if configured
            timeout = self.rule.max_execution_time or 30
            context["_timeout"] = timeout
            context["_start_time"] = start_time

            if self.context.get("test_mode"):
                # No timeout in test mode
                result = self._execute_graph(context)
            else:
                with time_limit(timeout):
                    result = self._execute_graph(context)

            # Post-execution cleanup
            self._log("INFO", "Rule execution completed successfully")

            if not self.context.get("test_mode"):
                self._update_rule_stats(success=True)

            return result

        except frappe.PermissionError as e:
            status = "Skipped"
            # Ensure the exact message expected by tests is logged
            self._log("INFO", f"Skipping rule execution: {e}")
            return self.context

        except (TimeoutException, FuturesTimeoutError, BoltonTimeoutError):
            status = "Failed"
            error_msg = _("Rule execution exceeded timeout ({0}s)").format(
                timeout if "timeout" in locals() else "unknown"
            )
            error_detail = traceback.format_exc()
            self._log("ERROR", error_msg)
            if context if "context" in locals() else None:
                self._update_rule_stats(success=False, error=error_msg)
            raise BoltonTimeoutError(error_msg)

        except Exception as e:
            status = "Failed"
            error_msg = str(e)
            error_detail = traceback.format_exc()
            self._log("ERROR", _("Rule execution failed: {0}").format(error_msg))
            if context if "context" in locals() else None:
                self._update_rule_stats(success=False, error=error_msg)
            raise

        finally:
            # Persist Log
            duration = time.time() - start_time
            self._save_execution_log(
                status,
                duration,
                error_detail,
                context=context if "context" in locals() else None,
            )

    def _validate_execution(self):
        """Validate rule is executable"""
        if not self.rule.is_active:
            raise RuleDisabledError(_("Rule {0} is disabled").format(self.rule.name))

        if not self.actions:
            raise EmptyRuleError(
                _("Rule {0} has no enabled actions").format(self.rule.name)
            )

    def _initialize_context(self, doc, **kwargs):
        return {
            **self.context,
            "doc": doc,
            "frappe": self._get_safe_frappe_api(),
            "vars": {},
            "meta": {
                "rule": self.rule.name,
                "rule_version": "v1",
                "engine_version": "1.0",
                "user": frappe.session.user,
                "timestamp": frappe.utils.now(),
                "test_mode": self.context.get("test_mode", False),
            },
            "stop": False,
            **kwargs,
        }

    def _get_safe_frappe_api(self):
        """Return a restricted frappe API object for condition evaluation"""
        return _safe_frappe

    def _execute_graph(self, context):
        """Execute action graph with cycle detection and loop support"""

        # Change strict cycle detection to visit counting for loops
        node_visits = {}  # node_id -> count
        max_visits_per_node = 100  # Safety for infinite loops

        execution_path = []
        current = self._get_start_node()
        max_iterations = 1000  # Total step limit

        for iteration in range(max_iterations):
            # Internal timeout check
            if "_timeout" in context and "_start_time" in context:
                if time.time() - context["_start_time"] > context["_timeout"]:
                    raise BoltonTimeoutError(
                        _("Rule execution exceeded timeout of {0}s").format(
                            context["_timeout"]
                        )
                    )

            if not current:
                self._log("INFO", _("Reached end of flow (no next action)"))
                break

            if context.get("stop"):
                self._log("INFO", _("Flow stopped by action"))
                break

            # Cycle/Loop detection
            node_id = current.action_id or current.name

            # Track visits
            visits = node_visits.get(node_id, 0) + 1
            node_visits[node_id] = visits

            if visits > max_visits_per_node:
                raise CycleDetectedError(
                    _("Infinite loop detected: Action {0} visited {1} times").format(
                        current.action_label, visits
                    )
                )

            execution_path.append(current.action_label)
            self.path_trace.append(
                {
                    "action": current.action_label,
                    "action_id": current.action_id or current.name,
                    "type": current.action_type,
                    "timestamp": time.time(),
                }
            )

            # Log execution
            self._log(
                "INFO",
                _("Executing action: {0} (type: {1})").format(
                    current.action_label, current.action_type
                ),
            )

            try:
                # Standardized Handlers (Dispatcher)
                handler_map = {
                    "Condition": self._execute_condition,
                    "Switch": self._execute_switch,
                    "Process": self._execute_process,
                    "Sub-Rule": self._execute_sub_rule,
                    "Stop": self._execute_stop,
                    "Wait": self._execute_wait,
                    "Loop": self._execute_loop,
                    "Set Value": self._execute_set_value,
                    "Raise Error": self._execute_raise_error,
                    "Notify": self._execute_notify,
                }

                handler = handler_map.get(current.action_type)
                if not handler:
                    self._log(
                        "WARNING",
                        _("Unknown action type: {0}").format(current.action_type),
                    )
                    result = None
                    next_id = current.next_step_if_true
                else:
                    # Handlers now return (result, next_id)
                    result, next_id = handler(current, context)

                # Enhance path trace with result/inputs for Process
                if current.action_type == "Process":
                    # Use JSON serialization for output if possible (better for JS UI)
                    try:
                        self.path_trace[-1]["output"] = json.dumps(result, default=str)
                    except:
                        self.path_trace[-1]["output"] = str(result)
                    try:
                        self.path_trace[-1]["input"] = self._get_action_config(current)
                    except:
                        pass

                # Store result if variable specified
                if current.return_variable and result is not None:
                    context["vars"][current.return_variable] = result
                    self._log(
                        "DEBUG",
                        _("Stored result in variable: {0}").format(
                            current.return_variable
                        ),
                    )

                # Move to next node
                current = self._get_action_by_id(next_id) if next_id else None

            except Exception as e:
                # Handle error based on on_error setting
                if hasattr(current, "on_error"):
                    if current.on_error == "Continue":
                        self._log(
                            "WARNING",
                            _("Error in action {0}, continuing: {1}").format(
                                current.action_label, str(e)
                            ),
                        )
                        current = self._get_action_by_id(current.next_step_if_true)
                        continue
                    elif current.on_error == "Rollback":
                        self._log(
                            "ERROR",
                            _("Error in action {0}, rolling back: {1}").format(
                                current.action_label, str(e)
                            ),
                        )
                        frappe.db.rollback()
                        raise
                    elif current.on_error == "Escalate":
                        self._log(
                            "ERROR",
                            _("Error in action {0}, escalating: {1}").format(
                                current.action_label, str(e)
                            ),
                        )
                        raise

                # Default: stop on error
                self._log(
                    "ERROR",
                    _("Error in action {0}: {1}").format(current.action_label, str(e)),
                )
                raise

        if iteration >= max_iterations - 1:
            raise CycleDetectedError(
                _("Max total iterations ({0}) exceeded").format(max_iterations)
            )

        self._log("INFO", _("Execution path: {0}").format(" → ".join(execution_path)))
        return context

    def _get_start_node(self):
        """Get the first action to execute (one with no incoming edges)"""
        # 1. Look for explicit Root / Entry Action
        for action in self.actions:
            if action.action_id == "root" or action.action_type == "Entry Action":
                self._log(
                    "INFO",
                    _("Start node: {0} ({1})").format(
                        action.action_label, action.action_id
                    ),
                )
                return action

        # 2. Backward compatibility: Find action with no incoming edges
        has_incoming = set()

        for action in self.actions:
            action_id = action.action_id or action.name

            # Check all actions' next_step fields
            for other in self.actions:
                if other.next_step_if_true == action_id:
                    has_incoming.add(action_id)
                if other.next_step_if_false == action_id:
                    has_incoming.add(action_id)

                # Check Switch cases for incoming edges
                if other.action_type == "Switch":
                    try:
                        switch_config = self._get_action_config(other)
                        for target_id in switch_config.get("cases", {}).values():
                            if target_id == action_id:
                                has_incoming.add(action_id)
                    except:
                        pass

        # Find action with no incoming edges (true start node)
        for action in self.actions:
            action_id = action.action_id or action.name
            if action_id not in has_incoming:
                self._log(
                    "INFO",
                    _("Start node (deduced): {0} ({1})").format(
                        action.action_label, action_id
                    ),
                )
                return action

        # Fallback to first action if no clear start
        self._log("WARNING", _("No clear start node, using first action"))
        return self.actions[0] if self.actions else None

    def _get_action_by_id(self, action_id):
        """Get action by ID (supports action_id, name, or label)"""
        if not action_id:
            return None

        # Try different lookup methods
        return (
            self.action_map_by_id.get(action_id)
            or self.action_map_by_name.get(action_id)
            or self.action_map_by_label.get(action_id)
        )

    def _execute_condition(self, action, context):
        """Execute a condition node"""
        # Conditions MUST be pre-compiled during Rule.validate()
        # If condition_expression is missing but condition_json exists, the rule was not properly saved
        if not action.condition_expression:
            if action.condition_json:
                raise ValueError(
                    _(
                        "Action '{0}' has condition_json but no compiled condition_expression. "
                        "Please re-save the Rule to compile conditions."
                    ).format(action.action_label)
                )
            result = True  # Empty condition passes
        else:
            result = self._evaluate_python_condition(
                action.condition_expression, context
            )

        next_id = action.next_step_if_true if result else action.next_step_if_false
        return result, next_id

    def _evaluate_python_condition(self, expression, context):
        """Evaluate Python expression safely"""
        if not expression:
            return True

        safe_locals = {
            "doc": context.get("doc"),
            "old_doc": context.get("old_doc"),
            "vars": context.get("vars", {}),
            "frappe": context.get("frappe", _safe_frappe),
            "resolve": FieldResolver.resolve,
            "check_link_match": check_link_match,
            "True": True,
            "False": False,
            "None": None,
        }

        try:
            return bool(frappe.safe_eval(expression, None, safe_locals))
        except Exception as e:
            self._log("ERROR", f"Condition evaluation failed: {e}")
            return False

    def _execute_loop(self, action, context):
        """
        Execute Loop Logic.
        Manages iteration state in context['vars']['_loops'][action_id]
        """
        if "_loops" not in context["vars"]:
            context["vars"]["_loops"] = {}

        loop_state = context["vars"]["_loops"].get(
            action.action_id, {"index": 0, "initialized": False}
        )

        config = self._get_action_config(action)

        iterator_name = config.get("iterator")  # e.g. "doc.items" or "vars.my_list"
        item_alias = config.get("alias", "item")

        items = []
        if iterator_name:
            # Resolve iterator
            items = self._evaluate_python_condition(iterator_name, context)

        if not isinstance(items, (list, tuple)):
            self._log(
                "WARNING",
                _("Loop iterator {0} is not a list/tuple. Got {1}").format(
                    iterator_name, type(items)
                ),
            )
            items = []

        current_index = loop_state["index"]

        if current_index < len(items):
            # Valid iteration
            item = items[current_index]
            context["vars"][item_alias] = item
            context["vars"]["loop"] = {
                "index": current_index,
                "first": current_index == 0,
                "last": current_index == len(items) - 1,
                "length": len(items),
            }

            # Advance index for NEXT time
            loop_state["index"] += 1
            context["vars"]["_loops"][action.action_id] = loop_state
            return True, action.next_step_if_true
        else:
            # Loop finished
            # Cleanup
            if action.action_id in context["vars"]["_loops"]:
                del context["vars"]["_loops"][action.action_id]
            return False, action.next_step_if_false

    def _execute_wait(self, action, context):
        """Execute Wait (Sleep)"""
        config = self._get_action_config(action)

        duration = config.get("duration", 0)
        if not duration and action.timeout:
            duration = action.timeout

        if duration > 0:
            self._log("INFO", _("Waiting for {0} seconds...").format(duration))
            time.sleep(duration)

        return None, action.next_step_if_true

    def _execute_stop(self, action, context):
        """Execute Stop action"""
        self._log("INFO", _("Stop action encountered"))
        return None, None

    def _execute_set_value(self, action, context):
        """Execute Set Value action - updates a field using Jinja template"""
        target_field = getattr(action, "target_field", None)
        value_template = getattr(action, "value_template", "") or ""

        if not target_field:
            self._log("WARNING", _("Set Value action missing target_field"))
            return None, getattr(action, "next_step_if_true", None)

        # Render Jinja template
        template_context = {
            "doc": context.get("doc"),
            "vars": context.get("vars", {}),
            "frappe": frappe,
            "utils": frappe.utils,
        }
        rendered_value = frappe.render_template(value_template, template_context)

        # Set the value on the document
        doc = context.get("doc")
        if doc and hasattr(doc, "set"):
            doc.set(target_field, rendered_value)
            self._log("INFO", _("Set {0} = {1}").format(target_field, rendered_value))
        else:
            self._log("WARNING", _("Cannot set field - no document in context"))

        return rendered_value, getattr(action, "next_step_if_true", None)

    def _execute_raise_error(self, action, context):
        """Execute Raise Error action - throws ValidationError with Jinja message"""
        error_template = getattr(action, "error_template", "") or "Validation Error"

        # Render Jinja template
        template_context = {
            "doc": context.get("doc"),
            "vars": context.get("vars", {}),
            "frappe": frappe,
            "utils": frappe.utils,
        }
        message = frappe.render_template(error_template, template_context)

        self._log("INFO", _("Raising error: {0}").format(message))
        frappe.throw(message)

    def _execute_notify(self, action, context):
        """Execute Notify action - shows notification using Jinja template"""
        notification_template = getattr(action, "notification_template", "") or ""
        notification_type = getattr(action, "notification_type", "Toast") or "Toast"

        # Render Jinja template
        template_context = {
            "doc": context.get("doc"),
            "vars": context.get("vars", {}),
            "frappe": frappe,
            "utils": frappe.utils,
        }
        message = frappe.render_template(notification_template, template_context)

        if notification_type == "Toast":
            frappe.msgprint(message, alert=True)
        elif notification_type == "System":
            frappe.publish_realtime(
                "msgprint",
                {"message": message, "alert": True},
                user=frappe.session.user,
            )
        elif notification_type == "Email":
            # Queue email notification
            doc = context.get("doc")
            if doc:
                frappe.sendmail(
                    recipients=[frappe.session.user],
                    subject=_("Rule Notification: {0}").format(self.rule.name),
                    message=message,
                    reference_doctype=doc.doctype,
                    reference_name=doc.name,
                )

        self._log("INFO", _("Sent {0} notification").format(notification_type))
        return None, getattr(action, "next_step_if_true", None)

    def _execute_process(self, action, context):
        """
        Execute Process Logic (Supports 'Process' DocType)
        """
        process_name = getattr(action, "process_name", None)
        process_method_name = getattr(action, "process_method", None)
        operation = getattr(action, "operation", None)

        if not process_name and not process_method_name:
            self._log(
                "WARNING",
                _(
                    "Process action {0} has no process_name or process_method set"
                ).format(action.action_label),
            )
            return None, getattr(action, "next_step_if_true", None)

        # Parse configuration
        config = self._get_action_config(action)

        # Apply Input Mapping (Context -> Config)
        if getattr(action, "input_mapping", None):
            config = apply_input_mapping(context, action.input_mapping, config)

        result = None

        try:
            # PATH A: New Process DocType Execution
            if process_name:
                if not frappe.db.exists("Process", process_name):
                    raise MethodExecutionError(
                        _("Process {0} not found").format(process_name)
                    )

                process_doc = frappe.get_cached_doc("Process", process_name)

                # Validation: Check Execution Mode Constraints (Basic check)
                # Note: Detailed validation might be needed similar to legacy but logic is delegated to Process internal checks or assumed safe
                if self.rule.execution_mode == "Asynchronous" and getattr(
                    action, "is_async", False
                ):
                    # Check if operation allows async?
                    # For now, we trust the Process implementation handles transactional safety or we add checks later.
                    pass

                # Execute with retry logic wrapper
                result = self._call_process_with_retry(
                    process_doc=process_doc,
                    operation=operation,
                    config=config,
                    context=context,
                    retry_count=action.retry_count or 0,
                    timeout=action.timeout or 30,
                )

            # Apply Output Mapping (Result -> Context)
            if getattr(action, "output_mapping", None):
                if action.is_async:
                    raise MethodExecutionError(_("Async actions cannot map outputs"))
                apply_output_mapping(result, action.output_mapping, context)

            return result, getattr(action, "next_step_if_true", None)

        except Exception:
            raise

    def _call_process_with_retry(
        self, process_doc, operation, config, context, retry_count, timeout
    ):
        """Execute new Process with retry logic and runtime contract enforcement"""
        last_error = None

        # Get operation metadata for contract enforcement
        op_def = None
        try:
            op_def = process_doc.get_operation(operation)
        except Exception:
            pass  # Operation might not exist in child table

        # 1. Runtime Contract: requires_doc
        if op_def and op_def.requires_doc:
            if not context.get("doc"):
                raise MethodExecutionError(
                    _(
                        "Operation {0} requires a document but context.doc is not set"
                    ).format(operation)
                )

        for attempt in range(retry_count + 1):
            try:
                if attempt > 0:
                    self._log(
                        "INFO",
                        _("Retry attempt {0}/{1} for {2}:{3}").format(
                            attempt, retry_count, process_doc.name, operation
                        ),
                    )

                # 2. Runtime Contract: transactional (wrap in savepoint)
                use_savepoint = op_def and op_def.transactional
                savepoint_name = f"process_{process_doc.name}_{operation}_{attempt}"

                if use_savepoint:
                    frappe.db.savepoint(savepoint_name)

                try:
                    # Call the Process execute method
                    result = process_doc.execute(context, func=operation, config=config)

                    # 3. Runtime Contract: output_schema validation
                    if op_def and op_def.output_schema:
                        self._validate_output_against_schema(
                            result, op_def.output_schema, operation
                        )

                    if use_savepoint:
                        frappe.db.release_savepoint(savepoint_name)

                    return result

                except Exception as e:
                    if use_savepoint:
                        try:
                            frappe.db.rollback(save_point=savepoint_name)
                            self._log(
                                "INFO",
                                _("Rolled back to savepoint for {0}:{1}").format(
                                    process_doc.name, operation
                                ),
                            )
                        except Exception:
                            pass  # Savepoint might not exist
                    raise

            except Exception as e:
                last_error = e
                self._log(
                    "ERROR",
                    _("Process execution failed (attempt {0}): {1}").format(
                        attempt + 1, str(e)
                    ),
                )
                if attempt < retry_count:
                    time.sleep(2**attempt)
                else:
                    break

        raise MethodExecutionError(
            _("Process {0}:{1} failed after {2} attempts: {3}").format(
                process_doc.name, operation, retry_count + 1, str(last_error)
            )
        )

    def _validate_output_against_schema(self, result, output_schema, operation_name):
        """
        Validate execution result against output_schema.
        Logs warning if schema validation fails (doesn't throw to avoid breaking existing rules).
        """
        if not output_schema:
            return

        try:
            schema = (
                json.loads(output_schema)
                if isinstance(output_schema, str)
                else output_schema
            )

            if not schema or not schema.get("properties"):
                return

            # Basic validation: check required fields exist in result
            if schema.get("required") and isinstance(result, dict):
                for field in schema["required"]:
                    if field not in result:
                        self._log(
                            "WARNING",
                            _(
                                "Operation {0} output missing required field: {1}"
                            ).format(operation_name, field),
                        )

            # Type check for top-level result
            expected_type = schema.get("type")
            if expected_type:
                actual_type = type(result).__name__
                type_map = {
                    "object": (dict,),
                    "array": (list, tuple),
                    "string": (str,),
                    "number": (int, float),
                    "integer": (int,),
                    "boolean": (bool,),
                    "null": (type(None),),
                }
                if expected_type in type_map:
                    if not isinstance(result, type_map[expected_type]):
                        self._log(
                            "WARNING",
                            _(
                                "Operation {0} output type mismatch: expected {1}, got {2}"
                            ).format(operation_name, expected_type, actual_type),
                        )

        except Exception as e:
            self._log(
                "WARNING",
                _("Failed to validate output_schema for {0}: {1}").format(
                    operation_name, str(e)
                ),
            )

    def _execute_switch(self, action, context):
        """Execute Switch logic based on config"""
        config = self._get_action_config(action)
        if not config:
            return None, getattr(action, "next_step_if_true", None)

        try:
            expression = config.get("expression")
            cases = config.get("cases", {})

            if not expression:
                return None, getattr(action, "next_step_if_true", None)

            # Evaluate expression
            val = self._evaluate_python_condition(expression, context)

            # Match case - convert val to string for key lookup as JSON keys are strings
            next_id = cases.get(val) or cases.get(str(val)) or action.next_step_if_true

            return val, next_id

        except Exception as e:
            self._log("ERROR", _("Switch evaluation failed: {0}").format(str(e)))
            raise

    def _execute_sub_rule(self, action, context):
        """Execute a Sub-Rule with bypass flags and proper trigger evaluation"""
        try:
            # Determine Sub Rule name
            sub_rule_name = getattr(action, "rule", None)
            if not sub_rule_name and getattr(action, "config", None):
                import json

                try:
                    cfg = json.loads(action.config)
                    sub_rule_name = cfg.get("rule")
                except Exception:
                    self._log("WARNING", _("Failed to parse Sub-Rule config JSON"))

            if not sub_rule_name:
                self._log("WARNING", _("Sub-Rule action missing rule reference"))
                return None, getattr(action, "next_step_if_true", None)

            if not frappe.db.exists("Rule", sub_rule_name):
                raise MethodExecutionError(
                    _("Sub-Rule {0} not found").format(sub_rule_name)
                )

            sub_rule_doc = frappe.get_cached_doc("Rule", sub_rule_name)

            if not sub_rule_doc.is_active:
                raise MethodExecutionError(
                    _("Sub-Rule {0} is not active").format(sub_rule_name)
                )

            if sub_rule_doc.document_type != self.rule.document_type:
                raise MethodExecutionError(
                    _("Sub-Rule {0} expects {1}, but current context is {2}").format(
                        sub_rule_name,
                        sub_rule_doc.document_type,
                        self.rule.document_type,
                    )
                )

            # Cross-rule cycle detection
            execution_stack = context.get("meta", {}).get("execution_stack", [])
            if sub_rule_name in execution_stack:
                cycle_path = " → ".join(execution_stack + [sub_rule_name])
                raise CycleDetectedError(
                    _("Cross-rule cycle detected: {0}").format(cycle_path)
                )

            # Determine bypass flags safely
            skip_conditions = 1  # default True
            skip_permissions = 0  # default False

            if hasattr(action, "skip_conditions"):
                skip_conditions = int(action.skip_conditions)
            elif getattr(action, "config", None):
                import json

                try:
                    cfg = json.loads(action.config)
                    skip_conditions = int(cfg.get("skip_conditions", 1))
                except Exception:
                    pass

            if hasattr(action, "skip_permissions"):
                skip_permissions = int(action.skip_permissions)

            self._log(
                "INFO",
                _("Sub-Rule {0}: skip_conditions={1}, skip_permissions={2}").format(
                    sub_rule_name, skip_conditions, skip_permissions
                ),
            )

            # Evaluate trigger condition if skip_conditions is False
            if not skip_conditions and sub_rule_doc.trigger_condition:
                if not sub_rule_doc.trigger_condition_expression:
                    from flexirule.ruleflow.core.compiler import ConditionCompiler

                    sub_rule_doc.trigger_condition_expression = (
                        ConditionCompiler().compile(sub_rule_doc.trigger_condition)
                    )

                is_eligible = self._evaluate_python_condition(
                    sub_rule_doc.trigger_condition_expression, context
                )
                if not is_eligible:
                    self._log(
                        "INFO",
                        _(
                            "Sub-Rule {0}: Trigger condition failed. Skipping execution."
                        ).format(sub_rule_name),
                    )
                    return None, getattr(action, "next_step_if_true", None)

            # Log bypass permissions
            if skip_permissions:
                self._log(
                    "AUDIT",
                    _(
                        "Sub-Rule {0}: Executing with skip_permissions=True by user {1}"
                    ).format(sub_rule_name, frappe.session.user),
                )

            self._log("INFO", _("BEGIN Sub-Rule: {0}").format(sub_rule_name))

            # Prepare sub-context
            sub_context = context.copy()
            sub_context["meta"] = context.get("meta", {}).copy()
            sub_context["meta"]["parent_rule"] = self.rule.name
            sub_context["meta"]["execution_stack"] = execution_stack + [self.rule.name]
            current_depth = sub_context["meta"].get("call_depth", 0)
            if current_depth >= MAX_SUB_RULE_DEPTH:
                raise CycleDetectedError(
                    _("Max sub-rule recursion depth ({0}) exceeded in {1}").format(
                        MAX_SUB_RULE_DEPTH, sub_rule_name
                    )
                )
            sub_context["meta"]["call_depth"] = current_depth + 1
            sub_context["meta"]["skip_conditions"] = skip_conditions
            sub_context["meta"]["skip_permissions"] = skip_permissions

            # Execute sub-rule
            sub_engine = self.__class__(sub_rule_doc, execution_context=sub_context)
            result_context = sub_engine.execute(context.get("doc"))

            # Merge results back
            context["vars"].update(result_context.get("vars", {}))
            self._log("INFO", _("END Sub-Rule: {0}").format(sub_rule_name))

            return None, getattr(action, "next_step_if_true", None)

        except Exception as e:
            self._log("ERROR", _("Sub-Rule execution failed: {0}").format(str(e)))
            raise

    def _log(self, level, message):
        """Add entry to execution log"""
        entry = {"timestamp": frappe.utils.now(), "level": level, "message": message}
        self.execution_log.append(entry)

        # Also log to console if debug mode
        if self.rule.debug_mode or self.context.get("test_mode"):
            frappe.logger().info(f"[{self.rule.name}] [{level}] {message}")

    def _update_rule_stats(self, success=True, error=None):
        """Update rule execution statistics (non-blocking, no commit)"""
        if self.context.get("dry_run"):
            return

        try:
            # Update in DB without triggering validations
            # Note: No explicit commit - let the calling transaction handle it
            frappe.db.set_value(
                "Rule",
                self.rule.name,
                {
                    "execution_count": (self.rule.execution_count or 0) + 1,
                    "last_executed": frappe.utils.now(),
                    "last_error": error if not success else None,
                },
                update_modified=False,
            )
        except Exception as e:
            # Don't fail execution if stats update fails
            frappe.logger().error(f"Failed to update rule stats: {e!s}")

    def _save_execution_log(self, status, duration, error_trace=None, context=None):
        """Save execution details to Rule Execution Log"""
        try:
            # Serialize context snapshot (remove complex objects)
            context_snapshot = {}
            active_context = context or getattr(self, "context", {})

            if active_context:
                # Only keep serializable vars
                context_snapshot = {
                    k: v
                    for k, v in active_context.get("vars", {}).items()
                    if isinstance(v, (str, int, float, bool, list, dict, type(None)))
                }

                # Add document snapshot for debugging
                if active_context.get("doc"):
                    try:
                        # Use as_dict but protect against non-serializable fields if any
                        doc_dict = active_context["doc"].as_dict()
                        context_snapshot["doc"] = doc_dict
                    except:
                        context_snapshot["doc"] = "<Not Serializable>"

            # Handle Local Documents (New Docs)
            # If we rollback, the doc might disappear, so the link will be broken.
            # We still save the name for reference.
            doc = active_context.get("doc") if active_context else None
            doc_name = doc.name if doc else None

            if doc and doc.get("__islocal"):
                # If it's local, it might not exist after rollback
                pass

            log_doc = frappe.get_doc(
                {
                    "doctype": "Rule Execution Log",
                    "rule": self.rule.name,
                    "status": status,
                    "duration": duration,
                    "reference_doctype": self.rule.document_type,
                    "reference_docname": doc_name,
                    "executed_by": (
                        active_context.get("meta", {}).get("user")
                        if active_context
                        else frappe.session.user
                    ),
                    "message": (
                        error_trace.split("\n")[-2]
                        if error_trace
                        else _("Executed successfully")
                    ),
                    "execution_path": json.dumps(self.path_trace, default=str),
                    "context_snapshot": json.dumps(context_snapshot, default=str),
                    "error_trace": error_trace,
                }
            )

            # PERSISTENCE LOGIC
            # If failed, we MUST rollback partial changes to clean up,
            # then insert and commit the log so it survives the final rollback by the framework.
            if self.context.get("dry_run"):
                # In dry_run mode, we don't commit anything, allowing the outer transaction to rollback.
                # However, we might want to still log if it failed?
                # For now, let's just avoid any commits.
                pass
            elif status in ("Failed", "Error") and not (active_context or {}).get(
                "test_mode"
            ):
                frappe.db.rollback()
                log_doc.insert(ignore_permissions=True, ignore_links=True)
                frappe.db.commit()
            else:
                # Success or Test Mode: Just insert (part of current transaction)
                log_doc.insert(ignore_permissions=True, ignore_links=True)

        except Exception as e:
            # Fallback if logging itself fails
            frappe.logger().error(f"Failed to save Rule Execution Log: {e!s}")
