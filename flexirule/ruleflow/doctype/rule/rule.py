# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

import json

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
		from frappe.core.doctype.has_role.has_role import HasRole
		from frappe.types import DF

		from flexirule.ruleflow.doctype.rule_action.rule_action import RuleAction

		actions: DF.Table[RuleAction]
		debug_mode: DF.Check
		description: DF.Text | None
		document_type: DF.Link
		execution_count: DF.Int
		execution_mode: DF.Literal["Synchronous", "Asynchronous"]
		is_active: DF.Check
		is_sub_rule: DF.Check
		last_error: DF.Text | None
		last_executed: DF.Datetime | None
		max_execution_time: DF.Int
		priority: DF.Int
		rule_name: DF.Data
		skip_for_roles: DF.TableMultiSelect[HasRole]
		status: DF.Literal["Draft", "Active", "Disabled", "Invalid", "Error", "Archived"]
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
		self.reorder_actions()
		self.compile_conditions()
		self.validate_actions()
		self.validate_no_sub_rule_cycles()
		self.validate_variable_availability()
		self.validate_active_rule_lock()

		# New strict validations
		self.validate_strict_requirements()

		self.status = self.get_computed_status()

	def validate_strict_requirements(self):
		"""
		Perform strict checks when rule is active.
		"""
		if not self.is_active:
			return

		# 1. Enforce Reachability (No orphans)
		from flexirule.ruleflow.utils.graph_validator import validate_graph_integrity

		validate_graph_integrity(self)

		# 2. Enforce exactly one Entry Action
		entry_nodes = [a for a in self.actions if a.action_type == "Entry Action"]
		if len(entry_nodes) != 1:
			frappe.throw(_("Active Rule must have exactly one Entry Action (Start) node."))

		# 3. Enforce Trigger Alignment (Doc-editing actions vs Trigger Event)
		self.validate_trigger_alignment()

	def validate_trigger_alignment(self, rule_doc=None, visited_rules=None, is_after_event_context=None):
		"""
		Ensure document-editing actions are only present in 'Before' triggers.
		Recursively checks sub-rules.

		Manual triggers are allowed to define doc-editing actions (for use as sub-rules),
		but their usage is restricted based on the calling rule's trigger.
		"""
		if visited_rules is None:
			visited_rules = set()

		doc_to_check = rule_doc or self

		if doc_to_check.name in visited_rules:
			return
		visited_rules.add(doc_to_check.name)

		# Define 'Before' events that allow document modification
		before_events = [
			"Before Naming",
			"Before Insert",
			"Before Save",
			"Validate",
			"Before Submit",
		]

		# Local context: Manual rules are not considered 'after events' when defined.
		# They only become 'after events' if called from an after-event parent.
		is_manual = doc_to_check.trigger_event == "Manual"
		local_is_after_event = doc_to_check.trigger_event not in before_events and not is_manual

		# Effective context: inherited from parent or determined locally for root rule
		effective_after_event = (
			is_after_event_context if is_after_event_context is not None else local_is_after_event
		)

		for action in doc_to_check.actions:
			# Check Set Value
			if action.action_type == "Set Value" and effective_after_event:
				frappe.throw(
					_(
						"Action '{0}' (Set Value) in Rule '{1}' is not allowed in current execution context. "
						"Document modification is restricted after the document is saved. "
						"Parent/Trigger: {2}"
					).format(action.action_label, doc_to_check.name, self.trigger_event)
				)

			# Check Process operations that write to Document
			if action.action_type == "Process" and effective_after_event:
				if action.process_name and action.operation:
					try:
						process = frappe.get_cached_doc("Process", action.process_name)
						op = process.get_operation(action.operation)
						if op and op.writes_to == "Document":
							frappe.throw(
								_(
									"Action '{0}' in Rule '{1}' uses operation '{2}' which modifies the document. "
									"This is restricted in current execution context (Parent/Trigger: {3})."
								).format(
									action.action_label,
									doc_to_check.name,
									action.operation,
									self.trigger_event,
								)
							)
					except Exception:
						pass  # Handled by other validations

			# Recursive check for Sub-Rules
			if action.action_type == "Sub-Rule" and action.rule:
				sub_rule = frappe.get_doc("Rule", action.rule)
				self.validate_trigger_alignment(sub_rule, visited_rules, effective_after_event)

	def validate_active_rule_lock(self):
		"""
		Governance: Prevent editing of Active rules.
		User must deactivate (Draft) to edit.
		"""
		if self.is_new() or self.flags.ignore_validate:
			return

		# Check prior state
		old_doc = self.get_doc_before_save()
		if not old_doc:
			return

		# If rule was active and is still active
		if old_doc.is_active and self.is_active:
			# Allow saving ONLY if it's a programmatic update (like stats or error log)
			# but usually those use ignore_validate=True.
			# If we are here, it's likely a user edit.
			frappe.throw(
				_("Cannot edit an Active Rule. Please set to 'Disabled' (Draft) before making changes.")
			)

	def before_insert(self):
		self.ensure_start_node()

	def ensure_start_node(self):
		"""Ensure a Start Node (Entry Action) exists"""
		# Check if an Entry Action already exists (by type or by the standard 'root' ID)
		root_action = next(
			(a for a in self.actions if a.action_type == "Entry Action" or a.get("action_id") == "root"),
			None,
		)

		if not root_action:
			# Determine next step if there are existing actions
			# We pick the first action that is NOT 'root'
			first_action_id = None
			existing_actions = [a for a in self.actions if a.get("action_id") != "root"]
			if existing_actions:
				first_action_id = existing_actions[0].get("action_id") or existing_actions[0].name

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

	def reorder_actions(self):
		"""Ensure Entry Action is the first action (idx=1)"""
		if not self.actions:
			return

		# Find entry action index
		# Priority: action_id='root' OR action_type='Entry Action'
		entry_index = -1
		for i, action in enumerate(self.actions):
			if action.action_id == "root" or action.action_type == "Entry Action":
				entry_index = i
				break

		if entry_index > 0:
			# Move to top
			entry_action = self.actions.pop(entry_index)
			self.actions.insert(0, entry_action)

		# Re-assign idx
		for i, action in enumerate(self.actions):
			action.idx = i + 1

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
			if action.action_type == "Condition" and action.condition_json:
				try:
					action.condition_expression = compiler.compile(action.condition_json)
					# Validate compiled expression
					is_valid, error = compiler.validate(action.condition_expression)
					if not is_valid:
						frappe.throw(
							_("Invalid Condition in Action {0}: {1}").format(action.action_label, error)
						)
				except ValueError as e:
					frappe.throw(
						_("Error compiling Action {0} Condition: {1}").format(action.action_label, str(e))
					)
				except Exception as e:
					frappe.throw(
						_("Error compiling Action {0} Condition: {1}").format(action.action_label, str(e))
					)

			# 1. Validate JSON fields syntax
			# Use new 'config' field with backward compatibility
			config_value = getattr(action, "config", None) or getattr(action, "method_config", None)
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
				parsed_vars = json.loads(writes_vars) if isinstance(writes_vars, str) else writes_vars
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
		Uses ACTION_TYPE_CONTRACT for unified backend/frontend validation.
		"""
		from flexirule.ruleflow.core.contracts import get_contract, get_required_fields

		action_type = action.action_type
		contract = get_contract(action_type)

		# 1. Contract: Required fields check
		for field in get_required_fields(action_type):
			if not getattr(action, field, None):
				frappe.throw(
					_("Action '{0}' ({1}) requires field '{2}'").format(
						action.action_label, action_type, field
					)
				)

		# 2. Contract: Terminal action should not have next_step
		if contract.get("terminal"):
			if action.next_step_if_true or action.next_step_if_false:
				frappe.throw(
					_("Action '{0}' ({1}) is terminal and should not have next steps").format(
						action.action_label, action_type
					)
				)

		# 3. Contract: Check has_next_false for non-branching actions
		if not contract.get("has_next_false") and action.next_step_if_false:
			frappe.throw(
				_("Action '{0}' ({1}) does not support 'next step if false'").format(
					action.action_label, action_type
				)
			)

		# Type-specific validations
		if action_type == "Sub-Rule":
			# Prevent self-reference
			if action.rule == self.name:
				frappe.throw(
					_("Action '{0}' cannot reference its own Rule as Sub-Rule.").format(action.action_label)
				)

		elif action_type == "Condition":
			if not action.condition_json and not action.condition_expression:
				frappe.throw(
					_("Action '{0}' is a Condition but no condition is defined.").format(action.action_label)
				)

		elif action_type == "Loop":
			config = self._parse_json_field(action.config)
			if not config.get("iterator_var") and not config.get("collection"):
				frappe.msgprint(
					_("Action '{0}' is a Loop but iterator configuration may be incomplete.").format(
						action.action_label
					),
					alert=True,
				)

		elif action_type == "Switch":
			config = self._parse_json_field(action.config)
			if not config.get("cases"):
				frappe.msgprint(
					_("Action '{0}' is a Switch but no cases are defined.").format(action.action_label),
					alert=True,
				)

		elif action_type == "Set Value":
			# Check if target field is editable given trigger event
			self._validate_set_value_editable(action)

	def _validate_set_value_editable(self, action):
		"""Check if Set Value target field is editable for current trigger event"""
		target_field = getattr(action, "target_field", None)
		if not target_field or not self.document_type:
			return

		# Only check for after-submit events
		after_submit_events = ["On Submit", "On Update After Submit"]
		if self.trigger_event not in after_submit_events:
			return

		try:
			meta = frappe.get_meta(self.document_type)
			df = meta.get_field(target_field)
			if df and not df.allow_on_submit:
				frappe.throw(
					_(
						"Cannot set field '{0}' after submit. Field does not have 'Allow on Submit' enabled."
					).format(target_field)
				)
		except Exception:
			# Handle any exception that might occur during field validation
			frappe.throw(_("Error validating field '{0}'.").format(target_field))

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
				cycle_path = [*path[cycle_start:], current_rule]
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
				cycle = dfs_detect_cycle(sub_rule, initial_path.copy(), globally_visited)
				if cycle:
					frappe.throw(_("Cycle detected in sub-rule graph: {0}").format(cycle))

	def validate_variable_availability(self):
		"""
		Check if variables used in templates are defined before use.
		User requested: throw on undefined variables.
		"""
		if not self.actions:
			return

		# Track available variables after each action in execution order
		available_vars = {"doc", "old_doc", "frappe", "utils", "vars"}

		# Build action map for traversal
		action_map = {a.action_id: a for a in self.actions if a.action_id}

		# Start from root and traverse the graph
		visited = set()
		queue = []

		# Find root node
		for action in self.actions:
			if action.action_id == "root" or action.action_type == "Entry Action":
				queue.append(action)
				break

		if not queue:
			return  # No root node, skip validation

		while queue:
			action = queue.pop(0)
			action_id = action.action_id or action.name

			if action_id in visited:
				continue
			visited.add(action_id)

			# Check templates for undefined variables
			self._check_template_variables(action, available_vars)

			# Add this action's return_variable to available set
			if action.return_variable:
				available_vars.add(action.return_variable)

			# Queue next actions
			if action.next_step_if_true:
				next_action = action_map.get(action.next_step_if_true)
				if next_action:
					queue.append(next_action)
			if action.next_step_if_false:
				next_action = action_map.get(action.next_step_if_false)
				if next_action:
					queue.append(next_action)

	def _check_template_variables(self, action, available_vars):
		"""Check Jinja template for undefined variable references"""
		import re

		# Templates to check based on action type
		templates_to_check = []
		if action.action_type == "Set Value":
			templates_to_check.append(("value_template", getattr(action, "value_template", "")))
		elif action.action_type == "Raise Error":
			templates_to_check.append(("error_template", getattr(action, "error_template", "")))
		elif action.action_type == "Notify":
			templates_to_check.append(("notification_template", getattr(action, "notification_template", "")))

		# Extract variable references from Jinja templates (e.g., {{ vars.foo }})
		var_pattern = re.compile(r"\{\{\s*vars\.(\w+)")

		for _field_name, template in templates_to_check:
			if not template:
				continue

			matches = var_pattern.findall(template)
			for var_name in matches:
				if var_name not in available_vars:
					frappe.throw(
						_(
							"Action '{0}' uses undefined variable 'vars.{1}'. "
							"Ensure a previous action sets return_variable='{1}'."
						).format(action.action_label, var_name)
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
			fields=["status", "message", "execution_path", "context_snapshot"],
		)

		log_data = logs[0] if logs else {}

		# Parse JSON fields
		if log_data.get("execution_path"):
			try:
				log_data["execution_path"] = json.loads(log_data["execution_path"])
			except Exception:
				pass

		if log_data.get("context_snapshot"):
			try:
				log_data["context_snapshot"] = json.loads(log_data["context_snapshot"])
			except Exception:
				pass

	except Exception as e:
		return {"success": False, "status": _("Failed"), "error": str(e)}

	return {
		"success": True,
		"status": _(log_data.get("status", "Success")),
		"execution_log": log_data,
		"execution_path": log_data.get("execution_path", []),
		"context_snapshot": log_data.get("context_snapshot", {}),
		"message": _("Rule {0} executed.").format(rule_name),
	}
