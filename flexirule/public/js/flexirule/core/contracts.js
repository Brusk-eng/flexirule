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
		icon: "fa fa-play",
		color: "#22c55e",
		description: "The starting point of your rule flow. Defines when the rule is triggered.",
	},
	Condition: {
		required_fields: ["condition_json"],
		has_next_true: true,
		has_next_false: true,
		terminal: false,
		icon: "fa fa-code-fork",
		color: "#3b82f6",
		description:
			"Branch your flow based on a logical condition. If true, following the 'True' path; otherwise, follow 'False'.",
	},
	Process: {
		required_fields: ["process_name", "operation"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		dynamic_fields: true, // Fields come from operation schema
		icon: "fa fa-cog",
		color: "#8b5cf6",
		description:
			"Execute a specific business process or operation. Operations can interact with the database, current document, or external systems.",
	},
	Loop: {
		required_fields: ["config"],
		has_next_true: true,
		has_next_false: true,
		terminal: false,
		icon: "fa fa-refresh",
		color: "#f59e0b",
		description: "Iterate over a list of items and execute actions for each item.",
	},
	Stop: {
		required_fields: [],
		has_next_true: false,
		has_next_false: false,
		terminal: true,
		icon: "fa fa-stop",
		color: "#ef4444",
		description: "Terminates the rule execution immediately.",
	},
	Switch: {
		required_fields: ["config"],
		has_next_true: false,
		has_next_false: true,
		terminal: false,
		icon: "fa fa-random",
		color: "#06b6d4",
		description:
			"Direct the flow to different paths based on the value of a specific field or expression.",
	},
	Wait: {
		required_fields: [],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		icon: "fa fa-clock-o",
		color: "#64748b",
		description: "Introduce a delay or wait for a specific event before proceeding.",
	},
	"Sub-Rule": {
		required_fields: ["rule"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		icon: "fa fa-cube",
		color: "#ec4899",
		description: "Invoke another rule as a reusable component within this flow.",
	},
	"Set Value": {
		required_fields: ["target_field", "value_template"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		icon: "fa fa-edit",
		color: "#14b8a6",
		description: "Update a field in the current document with a calculated value.",
		validation: {
			check_target_field_editable: true,
		},
	},
	"Raise Error": {
		required_fields: ["error_template"],
		has_next_true: false,
		has_next_false: false,
		terminal: true,
		icon: "fa fa-exclamation-triangle",
		color: "#dc2626",
		description: "Stop execution and display an error message to the user.",
	},
	Notify: {
		required_fields: ["notification_template"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		icon: "fa fa-bell",
		color: "#0ea5e9",
		description: "Send a notification (toast, system message, or email) to the user.",
	},
	"Query Records": {
		required_fields: ["reference_doctype", "operation"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		allowed_mutations: ["Set Context Variable", "Append to Context Variable"],
		icon: "fa fa-search",
		color: "#0891b2",
		description:
			"Query records from a DocType. Supports Query List, Query Doc, Exist Record, Query Report, and Query API modes.",
	},
	"Aggregate Records": {
		required_fields: ["reference_doctype", "operation", "config"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		allowed_mutations: [
			"Set Context Variable",
			"Append to Context Variable",
			"Update Context Variable",
		],
		icon: "fa fa-calculator",
		color: "#d97706",
		description:
			"Aggregate data from records using operations like sum, avg, count, min, max, or group_by.",
	},
	"Create Docs": {
		required_fields: ["reference_doctype", "operation"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		allowed_mutations: ["Set Doc Field", "Set Context Variable"],
		icon: "fa fa-plus-circle",
		color: "#059669",
		description:
			"Create new documents or update existing ones with field mappings from the current context.",
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
	return Object.keys(ACTION_TYPE_CONTRACT);
}

/**
 * Check if action type supports dynamic fields (e.g., Process with operation schema)
 */
export function hasDynamicFields(actionType) {
	return getContract(actionType).dynamic_fields || false;
}

// Export as default for convenience
export default ACTION_TYPE_CONTRACT;
