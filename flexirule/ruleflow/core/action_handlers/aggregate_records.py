# Copyright (c) 2026, Bolton and contributors
# For license information, please see license.txt

"""
Aggregate Records Action Handler

Performs aggregate operations (sum, avg, count, min, max, group_by) on records.
"""

import json

import frappe
from frappe import _

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry


class AggregateRecordsHandler(ActionHandler):
	"""Handler for aggregating records from DocTypes."""

	action_type = "Aggregate Records"

	SUPPORTED_OPERATIONS = {"sum", "avg", "count", "min", "max", "group_by"}

	def execute(self, action, context, engine):
		"""Execute aggregation based on configured operation (mode)."""
		mode = action.operation
		reference_doctype = action.reference_doctype
		config = self._parse_config(action.config)
		ignore_permissions = bool(action.skip_permissions)

		if not mode:
			frappe.throw(_("Operation/Mode is required for Aggregate Records action"))

		if not reference_doctype:
			frappe.throw(_("Reference DocType is required for Aggregate Records action"))

		if mode not in self.SUPPORTED_OPERATIONS:
			frappe.throw(
				_("Unsupported aggregation operation: {0}. Supported: {1}").format(
					mode, ", ".join(sorted(self.SUPPORTED_OPERATIONS))
				)
			)

		# Get filters and resolve template values
		filters = config.get("filters", {})
		filters = self._resolve_filters(filters, context)

		# Get the field to aggregate
		aggregate_field = config.get("field", "name")

		# Execute aggregation
		if mode == "count":
			result = self._count(reference_doctype, filters, ignore_permissions)
		elif mode == "group_by":
			group_field = config.get("group_by_field", aggregate_field)
			agg_function = config.get("agg_function", "count")
			agg_field = config.get("agg_field", "name")
			result = self._group_by(
				reference_doctype, filters, group_field, agg_function, agg_field, ignore_permissions
			)
		else:
			# sum, avg, min, max
			result = self._numeric_aggregate(
				reference_doctype, mode, aggregate_field, filters, ignore_permissions
			)

		# Store result in return variable if specified
		if action.return_variable:
			context.setdefault("vars", {})[action.return_variable] = result

		# Apply mutation mode
		mutation_mode = action.mutation_mode
		if mutation_mode and action.return_variable:
			self._apply_mutation(mutation_mode, action.return_variable, result, context)

		next_action = action.next_step_if_true
		return result, next_action

	def validate(self, action, context):
		"""Validate Aggregate Records configuration."""
		errors = []
		if not action.operation:
			errors.append(_("Operation/Mode is required"))
		if not action.reference_doctype:
			errors.append(_("Reference DocType is required"))

		config = self._parse_config(action.config)
		if action.operation in ("sum", "avg", "min", "max") and not config.get("field"):
			errors.append(
				_("{0} operation requires 'field' in config").format(action.operation)
			)

		return errors

	def _parse_config(self, config_str):
		"""Safely parse config JSON."""
		if not config_str:
			return {}
		if isinstance(config_str, dict):
			return config_str
		try:
			return json.loads(config_str)
		except (json.JSONDecodeError, TypeError):
			return {}

	def _count(self, doctype, filters, ignore_permissions):
		"""Count records matching filters."""
		return frappe.db.count(doctype, filters=filters)

	def _numeric_aggregate(self, doctype, operation, field, filters, ignore_permissions):
		"""Perform sum/avg/min/max aggregation using frappe.qb."""
		from frappe.query_builder import DocType
		from frappe.query_builder.functions import Avg, Max, Min, Sum

		table = DocType(doctype)

		agg_functions = {
			"sum": Sum,
			"avg": Avg,
			"min": Min,
			"max": Max,
		}

		agg_fn = agg_functions[operation]
		query = frappe.qb.from_(table).select(agg_fn(table[field]).as_("result"))

		# Apply filters
		for filter_field, filter_value in filters.items():
			if isinstance(filter_value, list) and len(filter_value) == 2:
				# Operator-style filter: [">=", 100]
				op, val = filter_value
				if op == "=":
					query = query.where(table[filter_field] == val)
				elif op == "!=":
					query = query.where(table[filter_field] != val)
				elif op == ">":
					query = query.where(table[filter_field] > val)
				elif op == ">=":
					query = query.where(table[filter_field] >= val)
				elif op == "<":
					query = query.where(table[filter_field] < val)
				elif op == "<=":
					query = query.where(table[filter_field] <= val)
			else:
				query = query.where(table[filter_field] == filter_value)

		result = query.run(as_dict=True)
		return result[0]["result"] if result else 0

	def _group_by(self, doctype, filters, group_field, agg_function, agg_field, ignore_permissions):
		"""Perform group_by aggregation."""
		from frappe.query_builder import DocType
		from frappe.query_builder.functions import Avg, Count, Max, Min, Sum

		table = DocType(doctype)

		agg_functions = {
			"sum": Sum,
			"avg": Avg,
			"min": Min,
			"max": Max,
			"count": Count,
		}

		agg_fn = agg_functions.get(agg_function, Count)
		query = (
			frappe.qb.from_(table)
			.select(table[group_field], agg_fn(table[agg_field]).as_("value"))
			.groupby(table[group_field])
		)

		# Apply filters
		for filter_field, filter_value in filters.items():
			if isinstance(filter_value, list) and len(filter_value) == 2:
				op, val = filter_value
				if op == "=":
					query = query.where(table[filter_field] == val)
				elif op == "!=":
					query = query.where(table[filter_field] != val)
			else:
				query = query.where(table[filter_field] == filter_value)

		return query.run(as_dict=True)

	def _resolve_filters(self, filters, context):
		"""Resolve template expressions in filter values."""
		if not isinstance(filters, dict):
			return filters

		resolved = {}
		for key, value in filters.items():
			if isinstance(value, str) and "{" in value:
				try:
					resolved[key] = frappe.safe_eval(
						value.replace("{", "").replace("}", ""),
						eval_globals={"frappe": frappe},
						eval_locals=context,
					)
				except Exception:
					resolved[key] = value
			else:
				resolved[key] = value

		return resolved

	def _apply_mutation(self, mutation_mode, var_name, result, context):
		"""Apply mutation mode to context."""
		vars_dict = context.setdefault("vars", {})

		if mutation_mode == "Set Context Variable":
			vars_dict[var_name] = result
		elif mutation_mode == "Append to Context Variable":
			existing = vars_dict.get(var_name, [])
			if isinstance(existing, list):
				existing.append(result)
			else:
				vars_dict[var_name] = [existing, result]
		elif mutation_mode == "Update Context Variable":
			existing = vars_dict.get(var_name, {})
			if isinstance(existing, dict) and isinstance(result, dict):
				existing.update(result)
			else:
				vars_dict[var_name] = result


# Register handler
HandlerRegistry.register(AggregateRecordsHandler())
