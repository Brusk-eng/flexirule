# Copyright (c) 2026, Bolton and contributors
# For license information, please see license.txt

"""
Aggregate Records Action Handler

Performs aggregate operations (sum, avg, count, min, max, group_by) on records.
"""

import json
from typing import ClassVar

import frappe
from frappe import _

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry
from flexirule.ruleflow.utils.mapping import apply_input_mapping


class AggregateRecordsHandler(ActionHandler):
	"""Handler for aggregating records from DocTypes."""

	action_type = "Aggregate Records"

	SUPPORTED_OPERATIONS: ClassVar[set[str]] = {"sum", "avg", "count", "min", "max", "group_by"}

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

		# Apply input mapping (Context -> Config)
		if getattr(action, "input_mapping", None):
			config = apply_input_mapping(context, action.input_mapping, config)

		# Basic permission check for aggregate queries
		if not ignore_permissions and not frappe.has_permission(reference_doctype, "read"):
			frappe.throw(
				_("You don't have read permission for {0}").format(reference_doctype),
				frappe.PermissionError,
			)

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
			errors.append(_("{0} operation requires 'field' in config").format(action.operation))

		return errors

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
		query = self._apply_qb_filters(query, table, filters)

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
		query = self._apply_qb_filters(query, table, filters)

		return query.run(as_dict=True)

	def _apply_qb_filters(self, query, table, filters):
		"""Helper to apply filters (dict or list) to a query builder object."""
		if isinstance(filters, dict):
			for field, val in filters.items():
				query = self._apply_single_qb_filter(query, table, field, val)
		elif isinstance(filters, list):
			for f in filters:
				if len(f) == 4:
					# [dt, field, op, val]
					_dt, field, op, val = f
					query = self._apply_single_qb_filter(query, table, field, [op, val])
				elif len(f) == 3:
					# [field, op, val]
					field, op, val = f
					query = self._apply_single_qb_filter(query, table, field, [op, val])
				elif len(f) == 2:
					# [field, val] or [field, [op, val]]
					field, val = f
					query = self._apply_single_qb_filter(query, table, field, val)
		return query

	def _apply_single_qb_filter(self, query, table, field, value):
		"""Apply a single filter field/value to the query."""
		if isinstance(value, list) and len(value) == 2:
			op, val = value
			if op == "=":
				return query.where(table[field] == val)
			if op == "!=":
				return query.where(table[field] != val)
			if op == ">":
				return query.where(table[field] > val)
			if op == ">=":
				return query.where(table[field] >= val)
			if op == "<":
				return query.where(table[field] < val)
			if op == "<=":
				return query.where(table[field] <= val)
			if op == "like":
				return query.where(table[field].like(val))
			if op == "not like":
				return query.where(table[field].not_like(val))
			if op == "in":
				return query.where(table[field].isin(val))
			if op == "not in":
				return query.where(table[field].notin(val))

		# Default equality
		return query.where(table[field] == value)


# Register handler
HandlerRegistry.register(AggregateRecordsHandler())
