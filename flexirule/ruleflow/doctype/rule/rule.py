# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document

from flexirule.ruleflow.core.contracts import normalize_trigger_type, serialize_trigger_type
from flexirule.ruleflow.utils.graph_validator import validate_graph_integrity


class Rule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.core.doctype.has_role.has_role import HasRole
		from frappe.types import DF

		from flexirule.ruleflow.doctype.rule_action.rule_action import RuleAction
		from flexirule.ruleflow.doctype.rule_permission.rule_permission import RulePermission

		actions: DF.Table[RuleAction]
		debug_mode: DF.Check
		description: DF.Text | None
		document_type: DF.Link | None
		exposed_as_subrule: DF.Check
		execution_mode: DF.Literal["Synchronous", "Asynchronous"]
		is_active: DF.Check
		last_error: DF.Text | None
		max_execution_time: DF.Int
		module: DF.Link | None
		permissions: DF.Table[RulePermission]
		previous_rule: DF.Link | None
		priority: DF.Literal[
			"0",
			"1",
			"2",
			"3",
			"4",
			"5",
			"6",
			"7",
			"8",
			"9",
			"10",
			"11",
			"12",
			"13",
			"14",
			"15",
			"16",
			"17",
			"18",
			"19",
			"20",
		]
		rule_name: DF.Data
		skip_for_roles: DF.TableMultiSelect[HasRole]
		status: DF.Literal["Draft", "Active", "Disabled", "Invalid", "Error", "Archived"]
		trigger_condition: DF.Code | None
		compiled_expression: DF.Code | None
		trigger_event: DF.Literal[
			"",
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
			"Before Rename",
			"After Rename",
			"Before Print",
		]
		trigger_type: DF.Literal["DocType Event", "Scheduled Rule", "Callable Rule"]
		version: DF.Int
		visual_data: DF.Code | None

	# end: auto-generated types
	def validate(self):
		"""
		Validate Rule Configuration
		"""
		self.trigger_type = serialize_trigger_type(self.trigger_type or "DocType Event")
		self.ensure_start_node()
		self.reorder_actions()
		self.compile_conditions()
		self.normalize_trigger_type_fields()
		self.validate_with_service()
		self.validate_no_sub_rule_cycles()
		self.validate_variable_availability()
		self.validate_active_rule_lock()
		self.validate_priority_callable()
		self.validate_version_constraints()

		self.status = self.get_computed_status()

	def validate_with_service(self):
		"""Shared structured validation layer used by form save and builder precheck."""
		from flexirule.ruleflow.core.validation_service import validate_rule_definition

		result = validate_rule_definition(self)
		if result.get("warnings"):
			for warning in result.get("warnings", []):
				frappe.msgprint(warning, alert=True)
		if result.get("valid"):
			return

		message = "<br>".join(result.get("errors", []))
		frappe.throw(_("Rule validation failed:<br>{0}").format(message))

	def before_save(self):
		"""Initialize version for new rules."""
		if self.is_new() and not self.version:
			self.version = 1

	def is_exposed_as_subrule(self):
		"""Return whether the rule is allowed to be targeted by Sub-Rule actions."""
		return bool(self.get("exposed_as_subrule"))

	def validate_priority_callable(self):
		"""Callable rules must remain deterministic and therefore use priority 0."""
		if normalize_trigger_type(self.trigger_type) == "Callable Rule" and str(self.priority) != "0":
			frappe.throw(_("Callable Rule rules must have priority set to 0."))

	def normalize_trigger_type_fields(self):
		"""Clear fields hidden by the selected trigger type."""
		from flexirule.ruleflow.core.contracts import get_trigger_type_contract

		contract = get_trigger_type_contract(self.trigger_type)
		for fieldname in contract.get("hidden_fields", []):
			if self.get(fieldname):
				self.set(fieldname, None)

	def validate_version_constraints(self):
		"""
		Enforce versioning constraints:
		- Only one draft amendment per rule lineage.
		- Cannot amend if a newer draft version already exists.
		"""
		if not self.previous_rule:
			return

		from flexirule.ruleflow.core.rule_service import validate_single_draft_copy

		validate_single_draft_copy(self)

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

		# Callable/Scheduler rules are not considered 'after events' when defined.
		# They only become 'after events' if called from an after-event parent.
		is_non_doc_event = normalize_trigger_type(doc_to_check.trigger_type) in (
			"Callable Rule",
			"Scheduled Rule",
		)
		local_is_after_event = doc_to_check.trigger_event not in before_events and not is_non_doc_event

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
		if self.is_new():
			return

		# Note: We intentionally do NOT skip for ignore_validate flag
		# to prevent accidental bypass of governance rules

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
		if not self.version:
			self.version = 1

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
				compiled_expression = compiler.compile(self.trigger_condition)
				self.compiled_expression = compiled_expression
				is_valid, error = compiler.validate(compiled_expression)
				if not is_valid:
					frappe.throw(_("Invalid Trigger Condition: {0}").format(error))
			except ValueError as e:
				frappe.throw(_("Error compiling Trigger Condition: {0}").format(str(e)))
			except Exception as e:
				frappe.throw(_("Error compiling Trigger Condition: {0}").format(str(e)))

		# Compile Action Conditions
		for action in self.actions:
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

	def get_computed_status(self):
		if not self.is_active:
			# New rule or rule that has never been executed
			if self.is_new() or not frappe.db.exists("Rule Execution Log", {"rule": self.name}):
				return "Draft"
			return "Disabled"

		if not self.actions:
			return "Invalid"

		if self.trigger_condition and not self.compiled_expression:
			return "Invalid"

		if self.last_error:
			return "Error"

		return "Active"

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

	def _validate_set_value_editable(self, action):
		"""Check if Set Value target field is valid and editable for current trigger event"""
		target_field = getattr(action, "target_field", None)
		if not target_field:
			return

		if not self.document_type:
			return

		meta = frappe.get_meta(self.document_type)
		df = meta.get_field(target_field)

		if not df:
			frappe.throw(
				_("Action '{0}': Field '{1}' does not exist on DocType '{2}'").format(
					action.action_label, target_field, self.document_type
				)
			)

		# Only check for after-submit events
		after_submit_events = ["On Submit", "On Update After Submit"]
		if self.trigger_event in after_submit_events:
			if not df.allow_on_submit:
				frappe.throw(
					_(
						"Action '{0}': Cannot set field '{1}' after submit. Field does not have 'Allow on Submit' enabled."
					).format(action.action_label, target_field)
				)

	def validate_sub_rule_target(self, action):
		"""Validate that a Sub-Rule action targets a compatible callable rule."""
		if not action.rule:
			return

		if action.rule == self.name:
			frappe.throw(
				_("Action '{0}' cannot reference its own Rule as Sub-Rule.").format(action.action_label)
			)

		if not frappe.db.exists("Rule", action.rule):
			frappe.throw(_("Action '{0}' references a missing Rule.").format(action.action_label))

		target_rule = frappe.get_cached_doc("Rule", action.rule)
		if hasattr(target_rule, "normalize_sub_rule_exposure_flag"):
			target_rule.normalize_sub_rule_exposure_flag()

		if normalize_trigger_type(target_rule.trigger_type) != "Callable Rule":
			frappe.throw(
				_("Action '{0}' must target a Callable Rule. Selected rule '{1}' uses '{2}'.").format(
					action.action_label, target_rule.name, target_rule.trigger_type
				)
			)

		if not target_rule.is_exposed_as_subrule():
			frappe.throw(
				_(
					"Action '{0}' must target a rule exposed as a sub-rule. Enable 'Exposed As Sub-Rule' on '{1}'."
				).format(action.action_label, target_rule.name)
			)

		if not target_rule.is_active:
			frappe.throw(
				_("Action '{0}' must target an active rule. Activate '{1}' first.").format(
					action.action_label, target_rule.name
				)
			)

		if target_rule.document_type != self.document_type:
			frappe.throw(
				_(
					"Action '{0}' targets Rule '{1}' for DocType '{2}', but the caller rule uses '{3}'."
				).format(
					action.action_label,
					target_rule.name,
					target_rule.document_type or _("None"),
					self.document_type or _("None"),
				)
			)

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
				return " → ".join([str(part) for part in cycle_path if part])

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
		globally_visited: set[str] = set()
		current_rule_name = self.name or self.rule_name or _("(unsaved rule)")
		initial_path = [current_rule_name]

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

		action_map = {a.action_id: a for a in self.actions if a.action_id}

		# Find root node
		start_action = None
		for action in self.actions:
			if action.action_id == "root" or action.action_type == "Entry Action":
				start_action = action
				break

		if not start_action:
			return  # No root node, skip validation

		self._validate_variable_paths(
			start_action,
			{"doc", "old_doc", "frappe", "utils", "vars"},
			action_map,
			set(),
		)

	def _validate_variable_paths(self, action, available_vars, action_map, path):
		"""Validate template variable usage for every reachable execution path."""
		action_id = action.action_id or action.name
		if action_id in path:
			return

		self._check_template_variables(action, available_vars)

		next_available = set(available_vars)
		if action.return_variable:
			next_available.add(action.return_variable)

		next_path = set(path)
		next_path.add(action_id)

		for next_id in [action.next_step_if_true, action.next_step_if_false]:
			if not next_id:
				continue
			next_action = action_map.get(next_id)
			if next_action:
				self._validate_variable_paths(next_action, next_available, action_map, next_path)

	def _check_template_variables(self, action, available_vars):
		"""Check Jinja template for undefined variable references"""
		import re

		# Templates to check based on action type
		templates_to_check = []
		if action.action_type == "Set Value":
			templates_to_check.append(("value_template", getattr(action, "value_template", "")))
		elif action.action_type == "Stop" and getattr(action, "operation", None) == "Error":
			templates_to_check.append(("value_template", getattr(action, "value_template", "")))
		elif action.action_type == "Notify":
			templates_to_check.append(("value_template", getattr(action, "value_template", "")))

		# Extract variable references from Jinja templates (e.g., {{ vars.foo }})
		var_pattern = re.compile(r"\{\{\s*vars\.(\w+)")

		for _field_name, template in templates_to_check:
			if not template:
				continue

			matches = var_pattern.findall(template)
			for var_name in matches:
				if (
					normalize_trigger_type(self.trigger_type) == "Callable Rule"
					and self.is_exposed_as_subrule()
				):
					# Reusable callable rules may receive vars from the caller via Sub-Rule input mapping.
					continue
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

	def on_trash(self):
		"""
		Cleanup when a rule is deleted:
		1. Block if referenced as sub-rule by another rule
		2. Delete linked Rule Scheduler records
		3. Clear rule cache
		"""
		from flexirule.ruleflow.core.coordinator import RuleCoordinator

		# 1. Block if referenced as sub-rule
		refs = frappe.get_all(
			"Rule Action",
			filters={"action_type": "Sub-Rule", "rule": self.name},
			fields=["parent"],
			limit=5,
		)
		if refs:
			names = ", ".join([r.parent for r in refs])
			frappe.throw(
				_("Cannot delete Rule '{0}': referenced as sub-rule by {1}").format(self.name, names)
			)

		# 2. Delete linked schedulers
		for s in frappe.get_all("Rule Scheduler", filters={"rule": self.name}, pluck="name"):
			frappe.delete_doc("Rule Scheduler", s, force=True)

		# 3. Clear cache
		RuleCoordinator.clear_cache()
