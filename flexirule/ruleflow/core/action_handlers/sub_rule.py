# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Sub-Rule Action Handler.

Executes another Rule as a nested sub-rule with proper context isolation
and cycle detection.
"""

import json

import frappe
from frappe import _

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry
from flexirule.ruleflow.core.exceptions import CycleDetectedError, MethodExecutionError

# Maximum nesting depth for sub-rule calls
MAX_SUB_RULE_DEPTH = 2


class SubRuleHandler(ActionHandler):
	"""Handler for Sub-Rule action type."""

	action_type = "Sub-Rule"

	def execute(self, action, context, engine):
		"""
		Execute a Sub-Rule with proper isolation and cycle detection.

		Features:
		- Cross-rule cycle detection via execution_stack
		- Depth limiting (MAX_SUB_RULE_DEPTH)
		- Optional bypass of sub-rule trigger conditions
		- Optional bypass of permission checks
		- Context merging (vars propagate back to parent)

		Returns:
		    Tuple of (None, next_action_id)
		"""
		try:
			# Determine Sub Rule name
			sub_rule_name = getattr(action, "rule", None)
			if not sub_rule_name and getattr(action, "config", None):
				try:
					cfg = json.loads(action.config)
					sub_rule_name = cfg.get("rule")
				except Exception:
					engine._log("WARNING", _("Failed to parse Sub-Rule config JSON"))

			if not sub_rule_name:
				engine._log("WARNING", _("Sub-Rule action missing rule reference"))
				return None, getattr(action, "next_step_if_true", None)

			if not frappe.db.exists("Rule", sub_rule_name):
				raise MethodExecutionError(_("Sub-Rule {0} not found").format(sub_rule_name))

			sub_rule_doc = frappe.get_cached_doc("Rule", sub_rule_name)

			if not sub_rule_doc.is_active:
				raise MethodExecutionError(_("Sub-Rule {0} is not active").format(sub_rule_name))

			if sub_rule_doc.document_type != engine.rule.document_type:
				raise MethodExecutionError(
					_("Sub-Rule {0} expects {1}, but current context is {2}").format(
						sub_rule_name,
						sub_rule_doc.document_type,
						engine.rule.document_type,
					)
				)

			# Cross-rule cycle detection
			execution_stack = context.get("meta", {}).get("execution_stack", [])
			if sub_rule_name in execution_stack:
				cycle_path = " → ".join([*execution_stack, sub_rule_name])
				raise CycleDetectedError(_("Cross-rule cycle detected: {0}").format(cycle_path))

			# Determine bypass flags
			skip_conditions = self._get_skip_conditions(action)
			skip_permissions = int(getattr(action, "skip_permissions", 0))

			engine._log(
				"INFO",
				_("Sub-Rule {0}: skip_conditions={1}, skip_permissions={2}").format(
					sub_rule_name, skip_conditions, skip_permissions
				),
			)

			# Evaluate trigger condition if not skipped
			if not skip_conditions and sub_rule_doc.trigger_condition:
				if not sub_rule_doc.trigger_condition_expression:
					from flexirule.ruleflow.core.compiler import ConditionCompiler

					sub_rule_doc.trigger_condition_expression = ConditionCompiler().compile(
						sub_rule_doc.trigger_condition
					)

				is_eligible = engine._evaluate_python_condition(
					sub_rule_doc.trigger_condition_expression, context
				)
				if not is_eligible:
					engine._log(
						"INFO",
						_("Sub-Rule {0}: Trigger condition failed. Skipping execution.").format(
							sub_rule_name
						),
					)
					return None, getattr(action, "next_step_if_true", None)

			# Log permission bypass for audit
			if skip_permissions:
				engine._log(
					"AUDIT",
					_("Sub-Rule {0}: Executing with skip_permissions=True by user {1}").format(
						sub_rule_name, frappe.session.user
					),
				)

			engine._log("INFO", _("BEGIN Sub-Rule: {0}").format(sub_rule_name))

			# Prepare sub-context
			sub_context = context.copy()
			sub_context["meta"] = context.get("meta", {}).copy()
			sub_context["meta"]["parent_rule"] = engine.rule.name
			sub_context["meta"]["execution_stack"] = [*execution_stack, engine.rule.name]

			# Check depth limit
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
			# Import here to avoid circular import
			from flexirule.ruleflow.core.engine import RuleEngine

			sub_engine = RuleEngine(sub_rule_doc, execution_context=sub_context)
			result_context = sub_engine.execute(context.get("doc"))

			# Merge results back to parent context
			context["vars"].update(result_context.get("vars", {}))
			engine._log("INFO", _("END Sub-Rule: {0}").format(sub_rule_name))

			return None, getattr(action, "next_step_if_true", None)

		except Exception as e:
			engine._log("ERROR", _("Sub-Rule execution failed: {0}").format(str(e)))
			raise

	def _get_skip_conditions(self, action):
		"""Get skip_conditions value from action or config."""
		if hasattr(action, "skip_conditions"):
			return int(action.skip_conditions)

		if getattr(action, "config", None):
			try:
				cfg = json.loads(action.config)
				return int(cfg.get("skip_conditions", 1))
			except Exception:
				pass

		return 1  # Default: skip conditions


# Register the handler
HandlerRegistry.register(SubRuleHandler())
