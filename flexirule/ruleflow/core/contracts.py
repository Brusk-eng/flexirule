# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Unified Backend/Frontend Contract for FlexiRule Action Types

This module defines the contract for action types that is shared between:
- Backend validation (Rule.validate)
- Frontend rendering (rule_builder/store.js)
"""

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
	},
	"Condition": {
		"required_fields": ["condition_json"],
		"has_next_true": True,
		"has_next_false": True,
		"terminal": False,
		"css": {"icon": "fa fa-code-fork", "color": "#3b82f6"},
		"validation": {"frontend": "validate_condition"},
	},
	"Process": {
		"required_fields": ["process_name", "operation"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-cog", "color": "#8b5cf6"},
		"dynamic_fields": True,
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
	},
	"Sub-Rule": {
		"required_fields": ["rule"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-cube", "color": "#ec4899"},
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
	},
	"Notify": {
		"required_fields": ["value_template", "operation"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-bell", "color": "#0ea5e9"},
		"operation_label": "Notification Type",
		"operation_options": ["Toast", "System", "Email", "System Notification", "Provider"],
	},
	"Raise Error": {
		"required_fields": ["value_template"],
		"has_next_true": False,
		"has_next_false": False,
		"terminal": True,
		"css": {"icon": "fa fa-exclamation-triangle", "color": "#dc2626"},
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
		"mandatory_fields": {
			"Exist Record": ["reference_doctype"],
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
RETURN_TYPE_OPTIONS = ["Boolean", "Dict", "List", "List of Dict", "Doc as Dict"]

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
		"optional_fields": ["document_type"],
		"hidden_fields": ["trigger_event", "trigger_condition", "compiled_expression"],
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
		"release_disabled_action_types": sorted(RELEASE_DISABLED_ACTION_TYPES),
		"return_type_options": RETURN_TYPE_OPTIONS,
		"action_types_with_reference_context": sorted(ACTION_TYPES_WITH_REFERENCE_CONTEXT),
		"action_types_with_return_schema": sorted(ACTION_TYPES_WITH_RETURN_SCHEMA),
		"config_modal_types": sorted(CONFIG_MODAL_TYPES),
	}
