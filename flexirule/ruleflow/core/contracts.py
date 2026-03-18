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
		"required_fields": [],
		"has_next_true": False,
		"has_next_false": False,
		"terminal": True,
		"css": {"icon": "fa fa-stop", "color": "#ef4444"},
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
	"Raise Error": {
		"required_fields": ["value_template"],
		"has_next_true": False,
		"has_next_false": False,
		"terminal": True,
		"css": {"icon": "fa fa-exclamation-triangle", "color": "#dc2626"},
	},
	"Notify": {
		"required_fields": ["value_template", "operation"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-bell", "color": "#0ea5e9"},
		"operation_label": "Notification Type",
		"operation_options": ["Toast", "System", "Email"],
	},
	"Query Records": {
		"required_fields": ["reference_doctype", "operation"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-search", "color": "#0891b2"},
		"allowed_mutations": [
			"Set Context Variable",
			"Append to Context Variable",
		],
		"mandatory_fields": {
			"Query Doc": ["reference_docname"],
			"Exist Record": ["reference_doctype"],
		},
	},
	"Aggregate Records": {
		"required_fields": ["reference_doctype", "operation", "config"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-calculator", "color": "#d97706"},
		"allowed_mutations": [
			"Set Context Variable",
			"Append to Context Variable",
			"Update Context Variable",
		],
	},
	"Create Docs": {
		"required_fields": ["reference_doctype", "operation"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"css": {"icon": "fa fa-plus-circle", "color": "#059669"},
		"allowed_mutations": [
			"Set Doc Field",
			"Set Context Variable",
		],
	},
}

RELEASE_DISABLED_ACTION_TYPES = {"Loop", "Switch"}


def get_contract(action_type: str) -> dict:
	"""Get contract for an action type, with defaults for unknown types"""
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
	return action_type in RELEASE_DISABLED_ACTION_TYPES
