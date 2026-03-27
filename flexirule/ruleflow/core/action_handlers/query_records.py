# Copyright (c) 2026, Bolton and contributors
# For license information, please see license.txt

"""
Query Records Action Handler

Modes:
- Query List: frappe.get_list() — returns list of dicts
- Query Doc: frappe.get_doc() — returns doc as dict
- Exist Record: frappe.db.exists() — returns boolean
- Query Report: frappe.desk.query_report.run() — returns report data
"""

import json

import frappe
from frappe import _

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry
from flexirule.ruleflow.core.permissions import can_skip_permissions
from flexirule.ruleflow.utils.mapping import apply_input_mapping


class QueryRecordsHandler(ActionHandler):
	"""Handler for querying records from DocTypes."""

	action_type = "Query Records"

	def execute(self, action, context, engine):
		"""Execute a query based on the configured mode (operation field)."""
		mode = action.operation
		reference_doctype = action.reference_doctype
		config = self._parse_config(action.config)
		ignore_permissions = can_skip_permissions(action, context, throw=True)

		if not mode:
			frappe.throw(_("Operation/Mode is required for Query Records action"))

		if not reference_doctype:
			frappe.throw(_("Reference DocType is required for Query Records action"))

		# Apply input mapping (Context -> Config)
		if getattr(action, "input_mapping", None):
			config = apply_input_mapping(context, action.input_mapping, config)

		# Dispatch to mode handler
		mode_handlers = {
			"Query List": self._query_list,
			"Query Doc": self._query_doc,
			"Exist Record": self._exist_record,
			"Query Report": self._query_report,
			"Count": self._count_records,
			"Sum": self._aggregate,
			"Average": self._aggregate,
			"Min": self._aggregate,
			"Max": self._aggregate,
			"Group By": self._group_by,
		}

		handler_fn = mode_handlers.get(mode)
		if not handler_fn:
			frappe.throw(_("Unknown Query Records mode: {0}").format(mode))
			raise ValueError("Unknown mode for mypy")

		result = handler_fn(
			reference_doctype=reference_doctype,
			config=config,
			context=context,
			action=action,
			ignore_permissions=ignore_permissions,
		)

		# Determine next action
		next_action = action.next_step_if_true
		return result, next_action

	def validate(self, action, context):
		"""Validate Query Records action configuration."""
		errors = []
		if not action.operation:
			errors.append(_("Operation/Mode is required"))
		if not action.reference_doctype:
			errors.append(_("Reference DocType is required"))

		mode = action.operation
		if mode == "Query Doc" and not action.reference_docname:
			config = self._parse_config(action.config)
			if not config.get("docname") and not config.get("docname_expression"):
				errors.append(
					_(
						"Query Doc mode requires either a Reference Document or a docname/docname_expression in config"
					)
				)

		if mode == "Query Report":
			config = self._parse_config(action.config)
			if not config.get("report_name"):
				errors.append(_("Query Report mode requires report_name in config"))

		if mode in ("Sum", "Average", "Min", "Max"):
			config = self._parse_config(action.config)
			if not config.get("field"):
				errors.append(_("{0} operation requires 'field' in config").format(mode))

		return errors

	def _count_records(self, reference_doctype, config, context, action, ignore_permissions):
		"""Count records matching filters."""
		filters = self._resolve_filters(config.get("filters", {}), context)
		# Skip permission check is already handled by frappe.db functions if we don't pass ignore_permissions arg to them,
		# actually frappe.db.count doesn't take ignore_permissions. We check read permission manually if needed.
		if not ignore_permissions and not frappe.has_permission(reference_doctype, "read"):
			frappe.throw(
				_("You don't have read permission for {0}").format(reference_doctype), frappe.PermissionError
			)

		return frappe.db.count(reference_doctype, filters=filters)

	def _aggregate(self, reference_doctype, config, context, action, ignore_permissions):
		"""Perform sum/avg/min/max aggregation using frappe.qb."""
		from frappe.query_builder import DocType
		from frappe.query_builder.functions import Avg, Max, Min, Sum

		if not ignore_permissions and not frappe.has_permission(reference_doctype, "read"):
			frappe.throw(
				_("You don't have read permission for {0}").format(reference_doctype), frappe.PermissionError
			)

		filters = self._resolve_filters(config.get("filters", {}), context)
		field = config.get("field", "name")
		mode = action.operation

		table = DocType(reference_doctype)

		agg_functions = {
			"Sum": Sum,
			"Average": Avg,
			"Min": Min,
			"Max": Max,
		}

		agg_fn = agg_functions[mode]
		query = frappe.qb.from_(table).select(agg_fn(table[field]).as_("result"))
		query = self._apply_qb_filters(query, table, filters)

		result = query.run(as_dict=True)
		return result[0]["result"] if result else 0

	def _group_by(self, reference_doctype, config, context, action, ignore_permissions):
		"""Perform group_by aggregation."""
		from frappe.query_builder import DocType
		from frappe.query_builder.functions import Avg, Count, Max, Min, Sum

		if not ignore_permissions and not frappe.has_permission(reference_doctype, "read"):
			frappe.throw(
				_("You don't have read permission for {0}").format(reference_doctype), frappe.PermissionError
			)

		filters = self._resolve_filters(config.get("filters", {}), context)
		aggregate_field = config.get("field", "name")
		group_field = config.get("group_by_field", aggregate_field)
		agg_function = config.get("agg_function", "count").lower()
		agg_field = config.get("agg_field", "name")

		table = DocType(reference_doctype)

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
					query = self._apply_single_qb_filter(query, table, f[1], [f[2], f[3]])
				elif len(f) == 3:
					query = self._apply_single_qb_filter(query, table, f[0], [f[1], f[2]])
				elif len(f) == 2:
					query = self._apply_single_qb_filter(query, table, f[0], f[1])
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

	def _query_list(self, reference_doctype, config, context, action, ignore_permissions):
		"""Execute frappe.get_list with configured filters, fields, etc."""
		filters = config.get("filters", {})
		or_filters = config.get("or_filters", {})
		fields = config.get("fields", ["name"])
		limit = config.get("limit", 20)
		order_by = config.get("order_by", "modified desc")
		group_by = config.get("group_by")

		# Resolve template expressions in filters
		filters = self._resolve_filters(filters, context)
		if or_filters:
			or_filters = self._resolve_filters(or_filters, context)

		kwargs = {
			"doctype": reference_doctype,
			"filters": filters,
			"fields": fields,
			"limit_page_length": limit,
			"order_by": order_by,
			"ignore_permissions": ignore_permissions,
		}
		if or_filters:
			kwargs["or_filters"] = or_filters
		if group_by:
			kwargs["group_by"] = group_by

		return frappe.get_list(**kwargs)

	def _query_doc(self, reference_doctype, config, context, action, ignore_permissions):
		"""Fetch a single document and return as dict."""
		docname = action.reference_docname or config.get("docname")

		# Support dynamic docname from expression
		if not docname and config.get("docname_expression"):
			docname = self._safe_eval(config["docname_expression"], context)

		if not docname:
			frappe.throw(_("No document name specified for Query Doc"))

		doc = frappe.get_doc(reference_doctype, docname)
		if not ignore_permissions:
			doc.check_permission("read")

		return doc.as_dict()

	def _exist_record(self, reference_doctype, config, context, action, ignore_permissions):
		"""Check if records exist matching filters. Returns boolean."""
		filters = config.get("filters", {})
		filters = self._resolve_filters(filters, context)

		exists = frappe.db.exists(reference_doctype, filters)
		return bool(exists)

	def _query_report(self, reference_doctype, config, context, action, ignore_permissions):
		"""Run a report and return results as a list of dicts."""
		report_name = config.get("report_name")
		if not report_name:
			frappe.throw(_("report_name is required in config for Query Report mode"))

		report_filters = config.get("filters", {})
		report_filters = self._resolve_filters(report_filters, context)

		from frappe.desk.query_report import run as run_report

		result = run_report(
			report_name,
			filters=report_filters,
		)

		data: list = []
		columns: list = []

		if isinstance(result, dict):
			data = result.get("result") or result.get("data") or []
			columns = result.get("columns") or []
		elif isinstance(result, list | tuple) and len(result) >= 2:
			columns = result[0]
			data = result[1]
		elif isinstance(result, list):
			data = result

		# 2. Try to fetch columns from report definition if missing
		if not columns and report_name:
			try:
				report_doc = frappe.get_doc("Report", report_name)
				if report_doc.report_type == "Query Report":
					# Extract columns from query
					pass
				elif report_doc.json:
					report_data = json.loads(report_doc.json)
					columns = report_data.get("columns", [])
			except Exception:
				pass

		# 3. If data is empty, still return columns for schema detection
		if not data:
			return {"columns": columns, "result": []}

		# 4. Transform data (List of Lists/Mixed -> List of Dicts)
		if columns:
			col_names = []
			for col in columns:
				name = None
				if isinstance(col, dict):
					name = col.get("fieldname") or col.get("label")
				elif isinstance(col, str):
					name = col

				if name:
					col_names.append(name)

			if col_names:
				new_data = []
				for row in data:
					if isinstance(row, list | tuple):
						row_dict = {}
						# Handle mixed length or missing columns gracefully
						for i, val in enumerate(row):
							if i < len(col_names):
								row_dict[col_names[i]] = val
						new_data.append(row_dict)
					elif isinstance(row, dict):
						new_data.append(row)
				data = new_data

		return {"columns": columns, "result": data}


# Register handler
HandlerRegistry.register(QueryRecordsHandler())
