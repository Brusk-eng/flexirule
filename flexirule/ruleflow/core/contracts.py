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
	},
	"Condition": {
		"required_fields": ["condition_json"],
		"has_next_true": True,
		"has_next_false": True,
		"terminal": False,
	},
	"Process": {
		"required_fields": ["process_name", "operation"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
	},
	"Loop": {
		"required_fields": ["config"],  # config must have iterator
		"has_next_true": True,  # Loop body
		"has_next_false": True,  # Loop exit
		"terminal": False,
	},
	"Stop": {
		"required_fields": [],
		"has_next_true": False,
		"has_next_false": False,
		"terminal": True,
	},
	"Switch": {
		"required_fields": ["config"],  # config must have cases
		"has_next_true": False,  # Uses cases instead
		"has_next_false": True,  # Default case
		"terminal": False,
	},
	"Wait": {
		"required_fields": [],  # config.duration optional
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
	},
	"Sub-Rule": {
		"required_fields": ["rule"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
	},
	"Set Value": {
		"required_fields": ["target_field", "value_template"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"validation": {
			"check_target_field_editable": True,
		},
	},
	"Raise Error": {
		"required_fields": ["error_template"],
		"has_next_true": False,
		"has_next_false": False,
		"terminal": True,
	},
	"Notify": {
		"required_fields": ["notification_template"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
	},
	"Query Records": {
		"required_fields": ["reference_doctype", "operation"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
		"allowed_mutations": [
			"Set Context Variable",
			"Append to Context Variable",
		],
	},
	"Aggregate Records": {
		"required_fields": ["reference_doctype", "operation", "config"],
		"has_next_true": True,
		"has_next_false": False,
		"terminal": False,
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
		"allowed_mutations": [
			"Set Doc Field",
			"Set Context Variable",
		],
	},
}


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
