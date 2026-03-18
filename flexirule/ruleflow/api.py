# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Whitelisted API functions for Bolton Rule Engine
"""

import json
from typing import Any

import frappe
from frappe import _

from flexirule.ruleflow.core.compiler import ConditionCompiler


def _require_api_access():
	"""Check if user has permission to use sensitive API endpoints"""
	if frappe.session.user == "Administrator":
		return

	roles = frappe.get_roles(frappe.session.user)
	if "System Manager" not in roles and "Rule Builder" not in roles:
		frappe.throw(
			_("Not permitted. Requires 'System Manager' or 'Rule Builder' role."), frappe.PermissionError
		)


# Layout fieldtypes to exclude by default
LAYOUT_FIELDTYPES = [
	"Tab Break",
	"Section Break",
	"Column Break",
	"HTML",
	"Fold",
	"Heading",
]

# System fields
SYSTEM_FIELDS = [
	{"value": "name", "label": "ID (name)", "fieldtype": "Data", "group": "System"},
	{
		"value": "owner",
		"label": "Created By (owner)",
		"fieldtype": "Link",
		"group": "System",
	},
	{
		"value": "creation",
		"label": "Created On (creation)",
		"fieldtype": "Datetime",
		"group": "System",
	},
	{
		"value": "modified",
		"label": "Modified On (modified)",
		"fieldtype": "Datetime",
		"group": "System",
	},
	{
		"value": "modified_by",
		"label": "Modified By (modified_by)",
		"fieldtype": "Link",
		"group": "System",
	},
	{
		"value": "docstatus",
		"label": "Document Status (docstatus)",
		"fieldtype": "Int",
		"group": "System",
	},
]


@frappe.whitelist()
def get_doctype_fields(doctype: str, filters: str | dict | None = None):
	"""
	Get fields for DocField autocomplete - grouped by parent/child tables

	Args:
	    doctype: DocType name
	    filters: JSON string with options:
	        - include_child_fields: bool (default: true)
	        - include_system_fields: bool (default: false)
	        - fieldtypes: list (whitelist specific types)
	        - exclude_fieldtypes: list (blacklist types)

	Returns:
	    dict: {
	        "parent_fields": [...],
	        "child_tables": [
	            {"table_name": "items", "doctype": "Sales Invoice Item", "fields": [...]}
	        ],
	        "system_fields": [...] if include_system_fields
	    }
	"""
	if not doctype:
		return {"parent_fields": [], "child_tables": [], "system_fields": []}

	# Parse filters
	if isinstance(filters, str):
		filters = json.loads(filters) if filters else {}
	elif filters is None:
		filters = {}

	include_child = filters.get("include_child_fields", True)
	include_system = filters.get("include_system_fields", False)
	allowed_types = filters.get("fieldtypes")
	excluded_types = filters.get("exclude_fieldtypes", LAYOUT_FIELDTYPES)

	# Get meta
	try:
		meta = frappe.get_meta(doctype)
	except Exception:
		return {"parent_fields": [], "child_tables": [], "system_fields": []}

	result: dict[str, list] = {"parent_fields": [], "child_tables": [], "system_fields": []}

	# Process parent fields
	for df in meta.fields:
		if should_include_field(df, allowed_types, excluded_types):
			result["parent_fields"].append(
				{
					"value": df.fieldname,
					"label": f"{df.label or df.fieldname}",
					"fieldtype": df.fieldtype,
					"options": df.options,
					"description": f"{df.fieldtype}" + (f" → {df.options}" if df.options else ""),
				}
			)

	# Process child tables
	if include_child:
		for df in meta.fields:
			if df.fieldtype == "Table" and df.options:
				child_fields = get_child_table_fields(df.options, df.fieldname, allowed_types, excluded_types)
				if child_fields:
					result["child_tables"].append(
						{
							"table_fieldname": df.fieldname,
							"table_label": df.label or df.fieldname,
							"child_doctype": df.options,
							"fields": child_fields,
						}
					)

	# Add system fields
	if include_system:
		result["system_fields"] = SYSTEM_FIELDS

	return result


def get_child_table_fields(child_doctype, table_fieldname, allowed_types=None, excluded_types=None):
	"""Get fields from a child table doctype"""
	try:
		meta = frappe.get_meta(child_doctype)
	except Exception:
		return []

	fields = []
	for df in meta.fields:
		if should_include_field(df, allowed_types, excluded_types):
			fields.append(
				{
					"value": f"{table_fieldname}.{df.fieldname}",
					"label": f"{df.label or df.fieldname}",
					"fieldtype": df.fieldtype,
					"options": df.options,
					"description": f"{df.fieldtype}" + (f" → {df.options}" if df.options else ""),
				}
			)

	return fields


def should_include_field(df, allowed_types=None, excluded_types=None):
	"""Check if field should be included based on filters"""
	# Check whitelist
	if allowed_types and df.fieldtype not in allowed_types:
		return False

	# Check blacklist
	if excluded_types and df.fieldtype in excluded_types:
		return False

	return True


@frappe.whitelist()
def test_rule(
	rule_name: str,
	doctype: str | None = None,
	docname: str | None = None,
	document_json: str | None = None,
	save_log: int | bool | str = False,
):
	"""
	Test a rule against a document.
	Supports either an existing document (by docname) or a transient document (by document_json).
	"""
	_require_api_access()

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

	# Check if rule is actually applicable (User Request: filters must apply)
	is_eligible, reason = RuleCoordinator.check_eligibility(
		rule, doc, event_name="Manual Test", skip_event_check=True
	)

	if not is_eligible:
		return {
			"success": False,
			"status": _("Skipped"),
			"message": _("Rule Skipped: {0}").format(reason),
			"execution_log": {},
		}

	try:
		from flexirule.ruleflow.core.engine import RuleEngine

		# Run in test_mode to prevent rollback of the rule itself during tests
		engine = RuleEngine(rule, {"test_mode": True, "save_log": frappe.parse_json(save_log)})
		engine.execute(doc)

		# Fetch the latest log (created by engine even in test mode)
		logs = frappe.get_all(
			"Rule Execution Log",
			filters={"rule": rule_name, "reference_docname": doc.name},
			order_by="creation desc",
			limit=1,
			fields=["status", "message", "execution_path", "context_snapshot"],
		)

		log_data = logs[0] if logs else {}

		# Parse JSON fields
		if isinstance(log_data, dict) and log_data.get("execution_path"):
			try:
				log_data["execution_path"] = json.loads(log_data["execution_path"])
			except Exception:
				pass

		if isinstance(log_data, dict) and log_data.get("context_snapshot"):
			try:
				log_data["context_snapshot"] = json.loads(log_data["context_snapshot"])
			except Exception:
				pass

		# Include info about skipped trigger filters for transparency
		info_msg = _("Rule '{0}' executed successfully").format(rule.rule_name)
		if rule.trigger_condition_expression:
			info_msg += _(" (trigger filters were bypassed for manual test)")

		# Capture path trace from engine
		path_trace = getattr(engine, "path_trace", [])

	except Exception as e:
		return {"success": False, "status": _("Failed"), "error": str(e)}

	return {
		"success": True,
		"status": _(log_data.get("status", "Success")),
		"execution_log": log_data,
		"execution_path": log_data.get("execution_path", path_trace or []),
		"context_snapshot": log_data.get("context_snapshot", {}),
		"message": info_msg,
	}


@frappe.whitelist()
def execute_rule(rule_name: str, context: str | dict | None = None, dry_run: bool | str = True):
	"""
	Pure execution API for a rule.
	"""
	_require_api_access()

	from flexirule.ruleflow.core.coordinator import RuleCoordinator

	ctx: dict | None = json.loads(context) if isinstance(context, str) else context

	dry: bool = bool(frappe.parse_json(dry_run))

	try:
		result = RuleCoordinator.execute_rule(rule_name, ctx, dry_run=dry)

		# Clean context for JSON serialization
		if isinstance(result, dict):
			result.pop("frappe", None)
			result.pop("doc", None)
			result.pop("old_doc", None)

		return {
			"success": True,
			"context": result,
			"execution_log": getattr(frappe.local, "execution_log", []),
		}
	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def clear_cache(doctype: str | None = None):
	"""Clear rule cache"""
	_require_api_access()
	try:
		from flexirule.ruleflow.core.coordinator import RuleCoordinator

		RuleCoordinator.clear_cache(doctype)
		return {"success": True, "message": _("Cache cleared")}
	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_operator_config():
	"""
	Get fieldtype-to-operators mapping and operator labels for Condition Builder.
	Returns centralized config from ConditionCompiler.
	"""
	return {
		"fieldtype_operators": ConditionCompiler.FIELDTYPE_OPERATORS,
		"operator_labels": ConditionCompiler.OPERATOR_LABELS,
	}


@frappe.whitelist()
def get_schema_field_options(
	schema_field: str | dict, parent_doctype: str, current_values: str | dict | None = None
):
	"""
	Get options for a schema field dynamically
	Used for dependent DocField sources
	"""
	if not schema_field or not parent_doctype:
		return []

	field = json.loads(schema_field) if isinstance(schema_field, str) else schema_field
	current = json.loads(current_values) if isinstance(current_values, str) else (current_values or {})

	# Resolve options source
	options = field.get("options", "")

	if options == "parent.document_type":
		target_dt = parent_doctype
	elif options in current:
		target_dt = current[options]
	else:
		target_dt = options

	if not target_dt:
		return []

	return get_doctype_fields(target_dt, json.dumps(field.get("filters", {})))


@frappe.whitelist()
def get_rule_versions(rule_name: str, limit: int | str = 20):
	"""Get version history for a rule"""
	_require_api_access()
	from flexirule.ruleflow.doctype.rule.rule_version_hooks import (
		get_rule_versions as _get_versions,
	)

	return _get_versions(rule_name, int(limit))


@frappe.whitelist()
def restore_rule_version(rule_name: str, version_name: str):
	"""Restore a rule to a previous version"""
	_require_api_access()
	from flexirule.ruleflow.doctype.rule.rule_version_hooks import (
		restore_rule_version as _restore,
	)

	return _restore(rule_name, version_name)


@frappe.whitelist()
def export_rule(rule_name: str):
	"""Export a rule to JSON"""
	_require_api_access()
	from flexirule.ruleflow.utils.import_export import export_rule as _export

	return _export(rule_name)


@frappe.whitelist()
def import_rule(import_data: str | dict, overwrite: bool | str = False):
	"""Import a rule from JSON"""
	_require_api_access()
	from flexirule.ruleflow.utils.import_export import import_rule as _import

	overwrite = frappe.parse_json(overwrite) if isinstance(overwrite, str) else overwrite
	return _import(import_data, overwrite)


@frappe.whitelist()
def get_action_context_schema(rule_name: str, action_id: str):
	"""
	Get available context variables for a specific action in rule flow.
	Used by UI to enable context-aware field selection.
	"""
	rule = frappe.get_doc("Rule", rule_name)

	result: dict[str, list] = {"doc_fields": [], "predecessor_outputs": []}

	# Get doc fields
	try:
		fields_data = get_doctype_fields(rule.document_type)
		result["doc_fields"] = fields_data.get("parent_fields", [])
	except Exception:
		pass

	# Build action maps
	action_map = {}
	for a in rule.actions:
		key = a.action_id or a.name
		action_map[key] = a

	# Find predecessors by traversing graph backwards
	predecessors = set()
	queue = [action_id]
	visited = set()

	while queue:
		current_id = queue.pop(0)
		if current_id in visited:
			continue
		visited.add(current_id)

		for action in rule.actions:
			action_key = action.action_id or action.name
			if action.next_step_if_true == current_id or action.next_step_if_false == current_id:
				predecessors.add(action_key)
				queue.append(action_key)

	# Get output schemas for predecessors
	for pred_id in predecessors:
		action = action_map.get(pred_id)
		if not action or not action.process_name:
			continue

		output_schema = None
		try:
			process_doc = frappe.get_cached_doc("Process", action.process_name)
			operation_doc = process_doc.get_operation(action.operation)
			if operation_doc and operation_doc.output_schema:
				import json

				output_schema = json.loads(operation_doc.output_schema)
		except Exception:
			pass

		result["predecessor_outputs"].append(
			{
				"action_id": action.action_id or action.name,
				"action_label": action.action_label,
				"return_variable": action.return_variable,
				"output_schema": output_schema,
			}
		)

	return result


@frappe.whitelist()
def get_process_operations(process_name: str):
	"""
	Get enabled operations for a specific process as normalized DTOs.
	Returns stable shape for both Rule Form and Rule Builder consumers.
	"""
	if not process_name:
		return []

	rows = frappe.get_all(
		"Process Operation",
		filters={
			"parenttype": "Process",
			"parent": process_name,
			"enabled": 1,
		},
		fields=[
			"func_name",
			"label",
			"enabled",
			"visible_in_builder",
			"writes_to",
			"is_terminal",
		],
		order_by="idx asc",
	)

	# Stable DTO with compatibility fields
	return [
		{
			"value": r.get("func_name"),
			"func_name": r.get("func_name"),
			"label": r.get("label") or r.get("func_name"),
			"enabled": r.get("enabled", 1),
			"visible_in_builder": r.get("visible_in_builder", 1),
			"writes_to": r.get("writes_to"),
			"is_terminal": r.get("is_terminal", 0),
		}
		for r in rows
		if r.get("func_name")
	]


@frappe.whitelist()
def clone_rule(rule_name: str, new_name: str | None = None):
	"""
	Clone a rule to create a new version or copy.
	Resets status to Draft (inactive) and clears execution stats.
	"""
	_require_api_access()
	try:
		doc = frappe.get_doc("Rule", rule_name)

		# Use Frappe's copy mechanism
		new_doc = frappe.copy_doc(doc)
		new_doc.is_active = 0
		new_doc.status = "Draft"
		new_doc.last_error = None

		if new_name:
			new_doc.rule_name = new_name

		# If no new name provided, Frappe often appends a number if naming is set,
		# but Rule uses "field:rule_name". We might need to ensure uniqueness if logic requires.
		# However, copy_doc usually clears the name if it's set to autoname.
		# But here autoname="field:rule_name".
		if not new_name:
			new_doc.rule_name = f"{doc.rule_name} (Copy)"

		new_doc.insert()
		return new_doc.name

	except Exception as e:
		frappe.log_error("Rule Clone Failed")
		frappe.throw(_("Failed to clone rule: {0}").format(str(e)))


@frappe.whitelist()
def amend_rule(rule_name: str) -> str:
	"""
	Create a new version (amendment) of a rule.

	The original rule stays active. The copy becomes a draft amendment
	with incremented version and a link back via `previous_rule`.

	Returns:
	    Name of the new amended rule.
	"""
	_require_api_access()
	from flexirule.ruleflow.core.rule_service import amend_rule as _amend_rule

	return _amend_rule(rule_name)


@frappe.whitelist()
def test_action_query(
	rule_name: str,
	action_id: str,
	context_doc: str | dict[str, Any] | None = None,
	overrides: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
	"""
	Execute a single action in isolation for testing.
	Returns detected return fields for auto-populating returns_keys.
	"""
	_require_api_access()
	rule = frappe.get_doc("Rule", rule_name)

	# Find the action
	action = None
	for a in rule.actions:
		if a.action_id == action_id:
			action = a
			break

	if not action:
		frappe.throw(_("Action {0} not found in rule {1}").format(action_id, rule_name))
		raise ValueError("Action not found")

	# Apply overrides if provided (useful for testing UI changes without saving)
	if overrides:
		overrides_dict: dict = json.loads(overrides) if isinstance(overrides, str) else overrides
		for key, val in overrides_dict.items():
			# Config and mapping fields might be strings in DB but dicts/lists in overrides
			json_fields = [
				"config",
				"condition_json",
				"input_mapping",
				"output_mapping",
				"resolved_output_schema",
			]
			if key in json_fields and not isinstance(val, str | bytes):
				setattr(action, key, json.dumps(val))
			elif hasattr(action, key):
				if key == "config" and isinstance(val, dict):
					setattr(action, key, json.dumps(val))
				else:
					setattr(action, key, val)

	# Build a minimal context
	doc = None
	if context_doc:
		import json as json_mod

		doc_data = json_mod.loads(context_doc) if isinstance(context_doc, str) else context_doc
		doc = frappe.get_doc(doc_data)
	elif rule.document_type:
		# Try to get a recent document for testing
		recent = frappe.get_all(rule.document_type, limit=1, pluck="name")
		if recent:
			doc = frappe.get_doc(rule.document_type, recent[0])

	if not doc:
		frappe.throw(_("No document available for testing. Provide context_doc."))

	from flexirule.ruleflow.core.engine import RuleEngine

	engine = RuleEngine(rule, {"test_mode": True})
	context = engine._initialize_context(doc)

	# Execute only this one action via handler
	from flexirule.ruleflow.core.action_handlers import HandlerRegistry

	handler = HandlerRegistry.get(action.action_type)
	if not handler:
		frappe.throw(_("No handler for action type: {0}").format(action.action_type))
		raise ValueError("Handler not found")

	# Re-assert for mypy since throw is not always detected as terminal
	if handler is None:
		return {"success": False, "error": "Handler not found", "result": None, "schema": [], "duration": 0}

	import time

	start = time.time()
	try:
		result, _next_id = handler.execute(action, context, engine)
		# Apply post-processing (output mapping, return validation, mutation)
		engine._post_process_action_result(action, result, context)
		duration = time.time() - start

		# Detect return fields
		schema = []

		# 1. Try to detect from Action Config first (most reliable for Query List)
		if action and action.action_type == "Query Records":
			try:
				config_data: dict = (
					json.loads(action.config) if isinstance(action.config, str) else (action.config or {})
				)
				if config_data is None:
					config_data = {}

				mode = (action.operation or config_data.get("operation")) if action else None

				reference_doctype = action.reference_doctype if action else None

				if mode == "Query List" and reference_doctype:
					fields = config_data.get("fields") or ["name"]
					meta = frappe.get_meta(reference_doctype)
					system_fields = {f["value"]: f for f in SYSTEM_FIELDS}

					for f in fields:
						df = None
						label = f
						if "." in f:
							table_fn, field_fn = f.split(".", 1)
							table_df = meta.get_field(table_fn)
							if table_df and table_df.fieldtype in ["Table", "Table MultiSelect"]:
								child_meta = frappe.get_meta(table_df.options)
								df = child_meta.get_field(field_fn)
								if not df and field_fn in system_fields:
									df = frappe._dict(system_fields[field_fn])

								if df:
									label = f"{table_df.label}: {df.label or df.fieldname}"
						else:
							df = meta.get_field(f)
							if not df and f in system_fields:
								df = frappe._dict(system_fields[f])

							if df:
								label = df.label or df.fieldname

						schema.append(
							{
								"fieldname": f,
								"label": label,
								"fieldtype": df.fieldtype if df else "Data",
								"options": df.options if df else None,
								"mandatory": df.reqd if df and hasattr(df, "reqd") else 0,
							}
						)
				elif mode == "Query Report" and isinstance(result, dict) and "columns" in result:
					columns = result.get("columns") or []
					for c in columns:
						if isinstance(c, dict):
							schema.append(
								{
									"fieldname": c.get("fieldname") or c.get("label"),
									"label": c.get("label") or c.get("fieldname"),
									"fieldtype": c.get("fieldtype") or "Data",
									"options": c.get("options"),
									"mandatory": c.get("mandatory", 0),
								}
							)
						elif isinstance(c, str):
							schema.append(
								{
									"fieldname": c,
									"label": c,
									"fieldtype": "Data",
									"options": None,
									"mandatory": 0,
								}
							)
			except Exception:
				pass

		# 2. Fallback to result inspection if still empty
		if not schema:
			if isinstance(result, dict):
				for k in result.keys():
					schema.append(
						{"fieldname": k, "label": k, "fieldtype": "Data", "options": None, "mandatory": 0}
					)
			elif isinstance(result, list) and result and isinstance(result[0], dict):
				for k in result[0].keys():
					schema.append(
						{"fieldname": k, "label": k, "fieldtype": "Data", "options": None, "mandatory": 0}
					)

		return {
			"success": True,
			"result": result,
			"schema": schema,
			"duration": round(duration, 4),
		}
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), _("Test Query Failed"))
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_rule_stats(rule_name: str):
	"""Compute rule execution stats dynamically from Rule Execution Log"""
	_require_api_access()

	stats = frappe.db.sql(
		"""
		SELECT
			COUNT(*) as execution_count,
			AVG(duration) as avg_execution_time,
			MAX(creation) as last_executed,
			SUM(CASE WHEN status = 'Success' THEN 1 ELSE 0 END) as success_count
		FROM `tabRule Execution Log`
		WHERE rule = %s
		""",
		(rule_name,),
		as_dict=True,
	)

	if not stats or not stats[0].execution_count:
		return {"execution_count": 0, "avg_execution_time": 0.0, "success_rate": 0.0, "last_executed": None}

	result = stats[0]
	execution_count = result.execution_count or 0
	success_count = result.success_count or 0

	success_rate = (success_count / execution_count * 100.0) if execution_count > 0 else 0.0

	return {
		"execution_count": execution_count,
		"avg_execution_time": result.avg_execution_time or 0.0,
		"success_rate": success_rate,
		"last_executed": result.last_executed,
	}
