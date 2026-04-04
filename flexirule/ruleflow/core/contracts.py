# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Unified Backend/Frontend Contract for FlexiRule Action Types

This module defines the contract for action types that is shared between:
- Backend validation (Rule.validate)
- Frontend rendering (rule_builder/store.js)
"""

from __future__ import annotations

import json

# Action Type Contract
# Each action type defines:
# - required_fields: Fields that must be set for this action type
# - has_next_true: Whether next_step_if_true is valid
# - has_next_false: Whether next_step_if_false is valid
# - terminal: Whether this action ends the flow
# - validation: Additional validation rules

ACTION_TYPE_CONTRACT = {
	"Entry Action": {
		"required_fields": [],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-play", "color": "#22c55e"},
		"field_labels": {},
	},
	"Condition": {
		"required_fields": ["condition_json"],
		"has_next_true": True,
		"has_next_false": True,
		"terminal": False,
		"css": {"icon": "fa fa-code-fork", "color": "#3b82f6"},
		"validation": {"frontend": "validate_condition"},
		"field_labels": {"compiled_expression": "Compiled Expression (Python)"},
	},
	"Process": {
		"required_fields": ["process_name", "operation"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-cog", "color": "#8b5cf6"},
		"dynamic_fields": True,
		"field_labels": {
			"operation": "Process Operation",
			"mutation_mode": "Result Handling",
			"return_type": "Result Type",
		},
		"allowed_mutations": [
			"Set Context Variable",
			"Update Context Variable",
			"Append to Context Variable",
			"Set Doc Field",
			"Update Doc Field",
			"Batch Database Set",
		],
		"allowed_return_types": [
			"Yes / No",
			"Single Record",
			"List of Values",
			"List of Records",
			"Full Document",
		],
		"show_return_type": True,
		"require_return_type": False,
	},
	"Loop": {
		"required_fields": ["config"],  # config must have iterator
		"has_next_true": True,  # Loop body
		"has_next_false": True,  # Loop exit
		"terminal": False,
		"css": {"icon": "fa fa-refresh", "color": "#f59e0b"},
	},
	"Stop": {
		"required_fields": ["operation"],
		"has_next_true": False,
		"has_next_false": False,
		"terminal": True,
		"css": {"icon": "fa fa-stop", "color": "#ef4444"},
		"operation_label": "Terminal Mode",
		"operation_options": ["Success", "Error"],
		"mandatory_fields": {
			"Error": ["value_template"],
		},
		"field_labels": {"operation": "Terminal Mode"},
	},
	"Switch": {
		"required_fields": ["config"],  # config must have cases
		"has_next_true": False,  # Uses cases instead
		"has_next_false": True,  # Default case
		"terminal": False,
		"css": {"icon": "fa fa-random", "color": "#06b6d4"},
	},
	"Wait": {
		"required_fields": [],  # config.duration optional
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-clock-o", "color": "#64748b"},
		"field_labels": {"operation": "Wait Mode"},
	},
	"Sub-Rule": {
		"required_fields": ["rule"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-cube", "color": "#ec4899"},
		"field_labels": {
			"rule": "Sub-Rule Name",
			"skip_conditions": "Skip Compatibility Check",
			"return_type": "Sub-Rule Result Type",
		},
		"allowed_mutations": [
			"Set Context Variable",
			"Update Context Variable",
			"Append to Context Variable",
		],
		"allowed_return_types": [
			"Single Record",
			"List of Records",
		],
		"default_return_type": "Single Record",
		"show_return_type": True,
		"require_return_type": False,
	},
	"Set Value": {
		"required_fields": ["target_field", "value_template"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-edit", "color": "#14b8a6"},
		"validation": {
			"check_target_field_editable": True,
		},
		"field_labels": {"target_field": "Field to Update", "value_template": "Value Template"},
	},
	"Notify": {
		"required_fields": ["value_template", "operation"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-bell", "color": "#0ea5e9"},
		"operation_label": "Notification Type",
		"operation_options": ["Toast", "System", "Email", "System Notification", "Provider"],
		"field_labels": {"operation": "Notification Type"},
	},
	"Raise Error": {
		"required_fields": ["value_template"],
		"has_next_true": False,
		"has_next_false": False,
		"terminal": True,
		"css": {"icon": "fa fa-exclamation-triangle", "color": "#dc2626"},
		"field_labels": {"value_template": "Error Message Template"},
	},
	"Query Records": {
		"required_fields": ["reference_doctype", "operation"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-search", "color": "#0891b2"},
		"operation_label": "Query Mode",
		"operation_options": [
			"Query List",
			"Query Doc",
			"Exist Record",
			"Query Report",
			"Count",
			"Sum",
			"Average",
			"Min",
			"Max",
			"Group By",
		],
		"allowed_mutations": [
			"Set Context Variable",
			"Append to Context Variable",
			"Update Context Variable",
		],
		"allowed_return_types": [
			"Yes / No",
			"Single Record",
			"List of Values",
			"List of Records",
		],
		"default_return_type": "List of Records",
		"show_return_type": True,
		"require_return_type": False,
		"mandatory_fields": {
			"Exist Record": ["reference_doctype"],
		},
		"operation_policies": {
			"Query List": {
				"allowed_return_types": ["List of Records"],
				"default_return_type": "List of Records",
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Rows Output Type"},
			},
			"Query Doc": {
				"allowed_return_types": ["Single Record", "Full Document"],
				"default_return_type": "Single Record",
				"show_return_type": True,
				"require_return_type": True,
				"field_labels": {"return_type": "Record Output Type"},
			},
			"Exist Record": {
				"allowed_return_types": ["Yes / No"],
				"default_return_type": "Yes / No",
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Boolean Output Type"},
			},
			"Query Report": {
				"allowed_return_types": ["List of Records"],
				"default_return_type": "List of Records",
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Report Output Type"},
			},
			"Count": {
				"allowed_return_types": ["List of Values"],
				"default_return_type": "List of Values",
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Metric Output Type"},
			},
			"Sum": {
				"allowed_return_types": ["List of Values"],
				"default_return_type": "List of Values",
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Metric Output Type"},
			},
			"Average": {
				"allowed_return_types": ["List of Values"],
				"default_return_type": "List of Values",
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Metric Output Type"},
			},
			"Min": {
				"allowed_return_types": ["List of Values"],
				"default_return_type": "List of Values",
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Metric Output Type"},
			},
			"Max": {
				"allowed_return_types": ["List of Values"],
				"default_return_type": "List of Values",
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Metric Output Type"},
			},
			"Group By": {
				"allowed_return_types": ["List of Records"],
				"default_return_type": "List of Records",
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Grouped Output Type"},
			},
		},
		"field_labels": {
			"operation": "Query Mode",
			"reference_doctype": "Target DocType",
			"reference_docname": "Target Record",
			"mutation_mode": "Result Handling",
			"return_type": "Result Type",
		},
	},
	"Document Action": {
		"required_fields": ["reference_doctype", "operation"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-file-text", "color": "#059669"},
		"operation_label": "Document Mode",
		"operation_options": ["Create New", "Update Existing", "Delete Record", "Create ToDo", "Add Comment"],
		"allowed_mutations": [
			"Set Doc Field",
			"Set Context Variable",
		],
		"allowed_return_types": [
			"Single Record",
			"Full Document",
			"Yes / No",
		],
		"default_return_type": "Single Record",
		"show_return_type": True,
		"require_return_type": False,
		"operation_policies": {
			"Create New": {
				"allowed_return_types": ["Single Record", "Full Document"],
				"default_return_type": "Single Record",
				"allowed_mutations": ["Set Context Variable", "Update Context Variable"],
				"show_return_type": True,
				"require_return_type": True,
				"field_labels": {"return_type": "Created Document Output"},
			},
			"Update Existing": {
				"allowed_return_types": ["Single Record", "Full Document"],
				"default_return_type": "Single Record",
				"allowed_mutations": ["Set Context Variable", "Update Context Variable", "Set Doc Field"],
				"show_return_type": True,
				"require_return_type": True,
				"field_labels": {"return_type": "Updated Document Output"},
			},
			"Delete Record": {
				"allowed_return_types": ["Yes / No"],
				"default_return_type": "Yes / No",
				"allowed_mutations": ["Set Context Variable"],
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Deletion Result Type"},
			},
			"Create ToDo": {
				"allowed_return_types": ["Single Record"],
				"default_return_type": "Single Record",
				"allowed_mutations": ["Set Context Variable", "Update Context Variable"],
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "ToDo Output Type"},
			},
			"Add Comment": {
				"allowed_return_types": ["Single Record"],
				"default_return_type": "Single Record",
				"allowed_mutations": ["Set Context Variable", "Update Context Variable"],
				"show_return_type": False,
				"require_return_type": False,
				"field_labels": {"return_type": "Comment Output Type"},
			},
		},
		"field_labels": {
			"operation": "Document Mode",
			"reference_doctype": "Target DocType",
			"reference_docname": "Target Record",
			"mutation_mode": "Result Handling",
			"return_type": "Result Type",
		},
	},
}

ACTION_TYPES_WITH_REFERENCE_CONTEXT = {"Query Records", "Document Action", "Process"}
ACTION_TYPES_WITH_RETURN_SCHEMA = {"Process", "Query Records", "Document Action"}
CONFIG_MODAL_TYPES = {
	"Process",
	"Condition",
	"Set Value",
	"Stop",
	"Raise Error",
	"Notify",
	"Wait",
	"Sub-Rule",
	"Query Records",
	"Document Action",
}

RELEASE_DISABLED_ACTION_TYPES = {"Loop", "Switch"}
RETURN_TYPE_OPTIONS = [
	"Yes / No",
	"Single Record",
	"List of Values",
	"List of Records",
	"Full Document",
]
MUTATION_MODE_OPTIONS = [
	"Set Doc Field",
	"Update Doc Field",
	"Set Context Variable",
	"Update Context Variable",
	"Append to Context Variable",
	"Batch Database Set",
]

# Trigger Type Contract
# Defines which fields are required, optional, or hidden for each trigger_type.
TRIGGER_TYPE_CONTRACT = {
	"DocType Event": {
		"required_fields": ["document_type", "trigger_event"],
		"optional_fields": ["trigger_condition", "compiled_expression"],
		"hidden_fields": [],
	},
	"Scheduler Event": {
		"required_fields": [],
		"optional_fields": ["document_type"],
		"hidden_fields": ["trigger_event", "trigger_condition", "compiled_expression"],
	},
	"Callable Event": {
		"required_fields": [],
		"optional_fields": ["document_type", "trigger_condition", "compiled_expression"],
		"hidden_fields": ["trigger_event"],
	},
}


def get_contract(action_type: str) -> dict:
	"""Get contract for an action type, with defaults for unknown types"""
	action_type = normalize_action_type(action_type)
	return ACTION_TYPE_CONTRACT.get(
		action_type,
		{
			"required_fields": [],
			"has_next_true": True,
			"has_next_false": False,
			"terminal": False,
		},
	)


def is_terminal_action(action_type: str) -> bool:
	"""Check if action type terminates the flow"""
	return get_contract(action_type).get("terminal", False)


def get_required_fields(action_type: str) -> list:
	"""Get required fields for an action type"""
	return get_contract(action_type).get("required_fields", [])


def is_release_disabled_action(action_type: str) -> bool:
	"""Check if an action type is intentionally disabled for the current release."""
	action_type = normalize_action_type(action_type)
	return action_type in RELEASE_DISABLED_ACTION_TYPES


def normalize_action_type(action_type: str | None) -> str:
	"""Return the action type directly as legacy aliases have been removed."""
	if not action_type:
		return ""
	return action_type


def get_trigger_type_contract(trigger_type: str) -> dict:
	"""Get contract for a trigger type."""
	return TRIGGER_TYPE_CONTRACT.get(
		trigger_type,
		{
			"required_fields": [],
			"optional_fields": [],
			"hidden_fields": [],
		},
	)


def get_contract_dto() -> dict:
	"""Export a frontend-safe contract payload from backend single source of truth."""
	return {
		"action_type_contract": ACTION_TYPE_CONTRACT,
		"trigger_type_contract": TRIGGER_TYPE_CONTRACT,
		"runtime_field_aliases": {
			"Sub-Rule": {
				"sub_rule_name": "rule",
			},
		},
		"release_disabled_action_types": sorted(RELEASE_DISABLED_ACTION_TYPES),
		"return_type_options": RETURN_TYPE_OPTIONS,
		"mutation_mode_options": MUTATION_MODE_OPTIONS,
		"action_types_with_reference_context": sorted(ACTION_TYPES_WITH_REFERENCE_CONTEXT),
		"action_types_with_return_schema": sorted(ACTION_TYPES_WITH_RETURN_SCHEMA),
		"config_modal_types": sorted(CONFIG_MODAL_TYPES),
	}


def infer_process_operation_policy(process_operation: dict | None) -> dict:
	"""Infer runtime/UI policy from Process Operation metadata."""
	policy: dict = {}
	if not isinstance(process_operation, dict):
		return policy

	writes_to = (process_operation.get("writes_to") or "None").strip()
	if writes_to == "Document":
		policy["allowed_mutations"] = [
			"Set Doc Field",
			"Update Doc Field",
			"Set Context Variable",
			"Update Context Variable",
		]
	elif writes_to == "Database":
		policy["allowed_mutations"] = [
			"Set Context Variable",
			"Update Context Variable",
			"Batch Database Set",
		]
	elif writes_to == "Context":
		policy["allowed_mutations"] = [
			"Set Context Variable",
			"Update Context Variable",
			"Append to Context Variable",
		]
	else:
		policy["allowed_mutations"] = [
			"Set Context Variable",
			"Update Context Variable",
		]

	output_schema = process_operation.get("output_schema")
	allowed_return_types = []
	default_return_type = None
	field_labels = {}
	show_return_type = True
	require_return_type = False

	if output_schema:
		try:
			schema = json.loads(output_schema) if isinstance(output_schema, str) else output_schema
			if isinstance(schema, dict):
				schema_type = schema.get("type")
				if schema_type == "array":
					allowed_return_types = ["List of Records", "List of Values"]
					default_return_type = "List of Records"
					field_labels["return_type"] = "Collection Output Type"
					show_return_type = True
					require_return_type = False
				elif schema_type == "boolean":
					allowed_return_types = ["Yes / No"]
					default_return_type = "Yes / No"
					field_labels["return_type"] = "Boolean Output Type"
					show_return_type = False
					require_return_type = False
				elif schema_type == "object":
					allowed_return_types = ["Single Record", "Full Document"]
					default_return_type = "Single Record"
					field_labels["return_type"] = "Record Output Type"
					show_return_type = True
					require_return_type = False
				elif schema_type in ("string", "number", "integer"):
					allowed_return_types = ["List of Values"]
					default_return_type = "List of Values"
					field_labels["return_type"] = "Value Output Type"
					show_return_type = False
					require_return_type = False
		except Exception:
			pass

	if not allowed_return_types:
		allowed_return_types = [
			"Yes / No",
			"Single Record",
			"List of Values",
			"List of Records",
			"Full Document",
		]
		default_return_type = "Single Record"
		field_labels["return_type"] = "Result Type"
		show_return_type = True
		require_return_type = False

	policy["allowed_return_types"] = allowed_return_types
	policy["default_return_type"] = default_return_type
	policy["show_return_type"] = show_return_type
	policy["require_return_type"] = require_return_type
	if field_labels:
		policy["field_labels"] = field_labels
	return policy


def get_effective_action_policy(
	action_type: str | None,
	operation: str | None = None,
	process_operation: dict | None = None,
) -> dict:
	"""Resolve action policy including operation-level overrides."""
	contract = get_contract(action_type or "")
	policy: dict = {
		"allowed_mutations": list(contract.get("allowed_mutations", []) or []),
		"allowed_return_types": list(contract.get("allowed_return_types", []) or []),
		"default_return_type": contract.get("default_return_type"),
		"field_labels": dict(contract.get("field_labels", {}) or {}),
		"show_return_type": contract.get("show_return_type"),
		"require_return_type": contract.get("require_return_type", False),
	}

	op_policy = {}
	if operation:
		op_policy = dict((contract.get("operation_policies", {}) or {}).get(operation, {}) or {})

	if action_type == "Process" and process_operation:
		dynamic_policy = infer_process_operation_policy(process_operation)
		for key, value in dynamic_policy.items():
			if value is not None:
				op_policy[key] = value

	for key in ("allowed_mutations", "allowed_return_types"):
		if op_policy.get(key):
			policy[key] = list(op_policy[key])
	if op_policy.get("default_return_type"):
		policy["default_return_type"] = op_policy["default_return_type"]
	if op_policy.get("show_return_type") is not None:
		policy["show_return_type"] = op_policy.get("show_return_type")
	if op_policy.get("require_return_type") is not None:
		policy["require_return_type"] = op_policy.get("require_return_type")
	if op_policy.get("field_labels"):
		policy["field_labels"].update(op_policy.get("field_labels", {}))

	return policy
