/**
 * ACTION_TYPE_CONTRACT - Frontend Contract Definition
 *
 * This module defines the unified contract for action types that is used for:
 * - Frontend validation (RuleConfigModal, store validation)
 * - Dynamic UI rendering (ConfigurationPanel)
 * - Required fields checking
 *
 * This is a frontend-first implementation that can be extended independently
 * without requiring server-side changes.
 */

export const ACTION_TYPE_CONTRACT = {
	"Entry Action": {
		required_fields: [],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		css: { icon: "fa fa-play", color: "#22c55e" },
		description: "The starting point of your rule flow. Defines when the rule is triggered.",
	},
	Condition: {
		required_fields: ["condition_json"],
		has_next_true: true,
		has_next_false: true,
		terminal: false,
		css: { icon: "fa fa-code-fork", color: "#3b82f6" },
		description:
			"Branch your flow based on a logical condition. If true, following the 'True' path; otherwise, follow 'False'.",
		validation: { frontend: "validate_condition" },
	},
	Process: {
		required_fields: ["process_name", "operation"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		dynamic_fields: true, // Fields come from operation schema
		css: { icon: "fa fa-cog", color: "#8b5cf6" },
		description:
			"Execute a specific business process or operation. Operations can interact with the database, current document, or external systems.",
	},
	Loop: {
		required_fields: ["config"],
		has_next_true: true,
		has_next_false: true,
		terminal: false,
		css: { icon: "fa fa-refresh", color: "#f59e0b" },
		description: "Iterate over a list of items and execute actions for each item.",
	},
	Stop: {
		required_fields: [],
		has_next_true: false,
		has_next_false: false,
		terminal: true,
		css: { icon: "fa fa-stop", color: "#ef4444" },
		description: "Terminates the rule execution immediately.",
	},
	Switch: {
		required_fields: ["config"],
		has_next_true: false,
		has_next_false: true,
		terminal: false,
		css: { icon: "fa fa-random", color: "#06b6d4" },
		description:
			"Direct the flow to different paths based on the value of a specific field or expression.",
	},
	Wait: {
		required_fields: [],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		css: { icon: "fa fa-clock-o", color: "#64748b" },
		description: "Introduce a delay or wait for a specific event before proceeding.",
	},
	"Sub-Rule": {
		required_fields: ["rule"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		css: { icon: "fa fa-cube", color: "#ec4899" },
		description: "Invoke another rule as a reusable component within this flow.",
	},
	"Set Value": {
		required_fields: ["target_field", "value_template"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		css: { icon: "fa fa-edit", color: "#14b8a6" },
		description: "Update a field in the current document with a calculated value.",
		validation: {
			check_target_field_editable: true,
		},
	},
	"Raise Error": {
		required_fields: ["value_template"],
		has_next_true: false,
		has_next_false: false,
		terminal: true,
		css: { icon: "fa fa-exclamation-triangle", color: "#dc2626" },
		description: "Stop execution and display an error message to the user.",
	},
	Notify: {
		required_fields: ["value_template", "operation"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		css: { icon: "fa fa-bell", color: "#0ea5e9" },
		description:
			"Send a notification as a toast, realtime message, email, Notification Log entry, or provider dispatch.",
		operation_label: "Notification Type",
		operation_options: ["Toast", "System", "Email", "System Notification", "Provider"],
	},
	"Query Records": {
		required_fields: ["reference_doctype", "operation"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		allowed_mutations: [
			"Set Context Variable",
			"Append to Context Variable",
			"Update Context Variable",
		],
		css: { icon: "fa fa-search", color: "#0891b2" },
		description:
			"Query records from a DocType. Supports Query List, Query Doc, Exist Record, Query Report, and Query API modes.",
		operation_label: "Query Mode",
		operation_options: [
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
		mandatory_fields: {
			"Query Doc": ["reference_docname"],
			"Exist Record": ["reference_doctype"],
		},
	},

	"Document Action": {
		required_fields: ["reference_doctype", "operation"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		operation_label: "Document Mode",
		operation_options: [
			"Create New",
			"Update Existing",
			"Delete Record",
			"Create ToDo",
			"Add Comment",
		],
		allowed_mutations: ["Set Doc Field", "Set Context Variable"],
		css: { icon: "fa fa-file-text", color: "#059669" },
		description:
			"Create, update, or delete documents, including convenience modes for linked ToDos and timeline comments.",
	},
};

export const RELEASE_DISABLED_ACTION_TYPES = new Set(["Loop", "Switch"]);

export const TRIGGER_TYPE_CONTRACT = {
	"DocType Event": {
		required_fields: ["document_type", "trigger_event"],
		optional_fields: ["trigger_condition", "trigger_condition_expression"],
		hidden_fields: [],
	},
	"Scheduler Event": {
		required_fields: [],
		optional_fields: ["document_type"],
		hidden_fields: ["trigger_event", "trigger_condition", "trigger_condition_expression"],
	},
	"Callable Event": {
		required_fields: [],
		optional_fields: ["document_type"],
		hidden_fields: ["trigger_event", "trigger_condition", "trigger_condition_expression"],
	},
};

/**
 * Get contract for an action type with sensible defaults
 */
export function getContract(actionType) {
	return (
		ACTION_TYPE_CONTRACT[actionType] || {
			required_fields: [],
			has_next_true: true,
			has_next_false: false,
			terminal: false,
			icon: "fa fa-circle",
			color: "#6b7280",
		}
	);
}

/**
 * Check if action type terminates the flow
 */
export function isTerminalAction(actionType) {
	return getContract(actionType).terminal || false;
}

/**
 * Get required fields for an action type
 */
export function getRequiredFields(actionType) {
	return getContract(actionType).required_fields || [];
}

export function getTriggerTypeContract(triggerType) {
	return (
		TRIGGER_TYPE_CONTRACT[triggerType] || {
			required_fields: [],
			optional_fields: [],
			hidden_fields: [],
		}
	);
}

/**
 * Validate node data against contract
 * @param {Object} nodeData - The node's data object
 * @returns {{ valid: boolean, errors: string[] }}
 */
export function validateAgainstContract(nodeData) {
	if (!nodeData || !nodeData.action_type) {
		return { valid: true, errors: [] };
	}

	const contract = getContract(nodeData.action_type);
	const errors = [];

	if (RELEASE_DISABLED_ACTION_TYPES.has(nodeData.action_type)) {
		errors.push(__("{0} is not available in this release", [nodeData.action_type]));
	}

	// 1. Check required fields
	for (const field of contract.required_fields || []) {
		const value = nodeData[field];
		if (value === undefined || value === null || value === "") {
			errors.push(__("Field '{0}' is required for {1}", [field, nodeData.action_type]));
		}
	}

	// 2. Check terminal action has no next steps
	if (contract.terminal) {
		if (nodeData.next_step_if_true || nodeData.next_step_if_false) {
			errors.push(
				__("{0} is terminal and should not have next steps", [nodeData.action_type])
			);
		}
	}

	if (contract.has_next_false && !nodeData.next_step_if_false) {
		errors.push(__("{0} requires a false path", [nodeData.action_type]));
	}

	// 3. Check has_next_false constraint
	if (!contract.has_next_false && nodeData.next_step_if_false) {
		errors.push(__("{0} does not support 'next step if false'", [nodeData.action_type]));
	}

	// 4. Mutation mode validation
	if (nodeData.mutation_mode) {
		const allowed = contract.allowed_mutations;
		if (Array.isArray(allowed) && allowed.length && !allowed.includes(nodeData.mutation_mode)) {
			errors.push(
				__("Mutation mode '{0}' is not allowed for {1}", [
					nodeData.mutation_mode,
					nodeData.action_type,
				])
			);
		}
		if (!nodeData.return_variable) {
			errors.push(__("Mutation Mode requires a Return Variable Name"));
		}
	}

	// 5. Return schema requires a return variable
	if ((nodeData.return_type || nodeData.resolved_output_schema) && !nodeData.return_variable) {
		errors.push(__("Return Schema requires a Return Variable Name"));
	}

	return {
		valid: errors.length === 0,
		errors,
	};
}

/**
 * Get all action type options for Select field
 */
export function getActionTypeOptions() {
	return Object.keys(ACTION_TYPE_CONTRACT).filter(
		(actionType) => !RELEASE_DISABLED_ACTION_TYPES.has(actionType)
	);
}

/**
 * Check if action type supports dynamic fields (e.g., Process with operation schema)
 */
export function hasDynamicFields(actionType) {
	return getContract(actionType).dynamic_fields || false;
}

// Export as default for convenience
export default ACTION_TYPE_CONTRACT;
