# Copyright (c) 2026, Bolton and contributors
# For license information, please see license.txt

"""
Query Records Action Handler

Modes:
- Query List: frappe.get_list() — returns list of dicts
- Query Doc: frappe.get_doc() — returns doc as dict
- Exist Record: frappe.db.exists() — returns boolean
- Query Report: frappe.desk.query_report.run() — returns report data
- Query API: Call a whitelisted API method — returns result
"""

import json

import frappe
from frappe import _

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry
from flexirule.ruleflow.utils.mapping import apply_input_mapping


class QueryRecordsHandler(ActionHandler):
	"""Handler for querying records from DocTypes."""

	action_type = "Query Records"

	def execute(self, action, context, engine):
		"""Execute a query based on the configured mode (operation field)."""
		mode = action.operation
		reference_doctype = action.reference_doctype
		config = self._parse_config(action.config)
		ignore_permissions = bool(action.skip_permissions)

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
			"Query API": self._query_api,
		}

		handler_fn = mode_handlers.get(mode)
		if not handler_fn:
			frappe.throw(_("Unknown Query Records mode: {0}").format(mode))

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

		if mode == "Query API":
			config = self._parse_config(action.config)
			if not config.get("method"):
				errors.append(_("Query API mode requires method in config"))

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

	def _query_list(self, reference_doctype, config, context, action, ignore_permissions):
		"""Execute frappe.get_list with configured filters, fields, etc."""
		filters = config.get("filters", {})
		fields = config.get("fields", ["name"])
		limit = config.get("limit", 20)
		order_by = config.get("order_by", "modified desc")
		group_by = config.get("group_by")

		# Resolve template expressions in filters
		filters = self._resolve_filters(filters, context)

		kwargs = {
			"doctype": reference_doctype,
			"filters": filters,
			"fields": fields,
			"limit_page_length": limit,
			"order_by": order_by,
			"ignore_permissions": ignore_permissions,
		}
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
		"""Run a report and return results."""
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

		return {
			"columns": result.get("columns", []),
			"result": result.get("result", []),
		}

	def _query_api(self, reference_doctype, config, context, action, ignore_permissions):
		"""Call a whitelisted API method."""
		method = config.get("method")
		if not method:
			frappe.throw(_("method is required in config for Query API mode"))

		# Security: validate method is allowed
		from flexirule.ruleflow.core.permissions import check_method_permission

		check_method_permission(method)

		args = config.get("args", {})
		# Resolve template expressions in args
		args = self._resolve_filters(args, context)

		result = frappe.call(method, **args)
		return result

	def _resolve_filters(self, filters, context):
		"""
		Resolve template expressions in filter values.
		Supports {doc.fieldname} and {vars.varname} syntax.
		"""
		if not isinstance(filters, dict):
			return filters

		resolved = {}
		for key, value in filters.items():
			if isinstance(value, str) and "{" in value:
				try:
					resolved[key] = self._safe_eval(value.replace("{", "").replace("}", ""), context)
				except Exception:
					resolved[key] = value
			else:
				resolved[key] = value

		return resolved

	def _safe_eval(self, expression, context):
		"""Evaluate expressions using SafeFrappeAPI from context."""
		safe_frappe = context.get("frappe") or frappe
		return frappe.safe_eval(expression, eval_globals={"frappe": safe_frappe}, eval_locals=context)


# Register handler
HandlerRegistry.register(QueryRecordsHandler())
