# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Process Action Handler.

Executes a Process operation with configuration, input/output mapping,
and retry logic.
"""

import frappe
from frappe import _

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry
from flexirule.ruleflow.core.exceptions import MethodExecutionError
from flexirule.ruleflow.utils.mapping import apply_input_mapping


class ProcessHandler(ActionHandler):
	"""Handler for Process action type."""

	action_type = "Process"

	def execute(self, action, context, engine):
		"""
		Execute a Process operation.

		Process actions are the primary way to execute business logic.
		They support:
		- Input mapping (context vars -> config)
		- Output mapping (result -> context vars)
		- Retry logic with exponential backoff
		- Timeout protection
		- Savepoint transactions

		Returns:
		    Tuple of (operation_result, next_action_id)
		"""
		process_name = getattr(action, "process_name", None)
		operation = getattr(action, "operation", None)

		if not process_name:
			engine._log(
				"WARNING",
				_("Process action {0} has no process_name set").format(action.action_label),
			)
			return None, getattr(action, "next_step_if_true", None)

		# Parse configuration
		config = engine._get_action_config(action)

		# Apply Input Mapping (Context -> Config)
		if getattr(action, "input_mapping", None):
			config = apply_input_mapping(context, action.input_mapping, config)

		result = None

		# Execute via Process DocType
		if not frappe.db.exists("Process", process_name):
			raise MethodExecutionError(_("Process {0} not found").format(process_name))

		process_doc = frappe.get_cached_doc("Process", process_name)

		# Execute with retry logic
		result = engine._call_process_with_retry(
			process_doc=process_doc,
			operation=operation,
			config=config,
			context=context,
			retry_count=action.retry_count or 0,
			timeout=action.timeout or 30,
		)

		return result, getattr(action, "next_step_if_true", None)

	def validate(self, action, context):
		"""Validate process action configuration."""
		errors = []
		if not getattr(action, "process_name", None):
			errors.append(_("Process action '{0}' requires a process_name").format(action.action_label))
		return errors


# Register the handler
HandlerRegistry.register(ProcessHandler())
