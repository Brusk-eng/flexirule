/**
 * FlexiRule action contracts
 *
 * Backend is the canonical source. This module keeps a local fallback so the
 * builder still works if the contract API is temporarily unavailable.
 */

const ACTION_TYPE_DESCRIPTION = {
	"Entry Action": "The starting point of your rule flow. Defines when the rule is triggered.",
	Condition:
		"Branch your flow based on a logical condition. If true, following the 'True' path; otherwise, follow 'False'.",
	Process:
		"Execute a specific business process or operation. Operations can interact with the database, current document, or external systems.",
	Loop: "Iterate over a list of items and execute actions for each item.",
	Stop: "Terminates the rule execution as Success or Error.",
	Switch: "Direct the flow to different paths based on the value of a specific field or expression.",
	Wait: "Introduce a delay or wait for a specific event before proceeding.",
	"Sub-Rule": "Invoke another rule as a reusable component within this flow.",
	"Set Value": "Update a field in the current document with a calculated value.",
	Notify: "Send a notification as a toast, realtime message, email, Notification Log entry, or provider dispatch.",
	"Query Records":
		"Query records from a DocType. Supports Query List, Query Doc, Exist Record, and Query Report modes.",
	"Document Action":
		"Create, update, or delete documents, including convenience modes for linked ToDos and timeline comments.",
};

const DEFAULT_ACTION_TYPE_CONTRACT = {
	"Entry Action": {
		required_fields: [],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		css: { icon: "fa fa-play", color: "#22c55e" },
	},
	Condition: {
		required_fields: ["condition_json"],
		has_next_true: true,
		has_next_false: true,
		terminal: false,
		css: { icon: "fa fa-code-fork", color: "#3b82f6" },
		validation: { frontend: "validate_condition" },
	},
	Process: {
		required_fields: ["process_name", "operation"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		dynamic_fields: true,
		css: { icon: "fa fa-cog", color: "#8b5cf6" },
	},
	Loop: {
		required_fields: ["config"],
		has_next_true: true,
		has_next_false: true,
		terminal: false,
		css: { icon: "fa fa-refresh", color: "#f59e0b" },
	},
	Stop: {
		required_fields: ["operation"],
		has_next_true: false,
		has_next_false: false,
		terminal: true,
		css: { icon: "fa fa-stop", color: "#ef4444" },
		operation_label: "Terminal Mode",
		operation_options: ["Success", "Error"],
		mandatory_fields: {
			Error: ["value_template"],
		},
	},
	Switch: {
		required_fields: ["config"],
		has_next_true: false,
		has_next_false: true,
		terminal: false,
		css: { icon: "fa fa-random", color: "#06b6d4" },
	},
	Wait: {
		required_fields: [],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		css: { icon: "fa fa-clock-o", color: "#64748b" },
	},
	"Sub-Rule": {
		required_fields: ["rule"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		css: { icon: "fa fa-cube", color: "#ec4899" },
	},
	"Set Value": {
		required_fields: ["target_field", "value_template"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		css: { icon: "fa fa-edit", color: "#14b8a6" },
		validation: {
			check_target_field_editable: true,
		},
	},
	Notify: {
		required_fields: ["value_template", "operation"],
		has_next_true: true,
		has_next_false: false,
		terminal: false,
		css: { icon: "fa fa-bell", color: "#0ea5e9" },
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
	},
};

const DEFAULT_TRIGGER_TYPE_CONTRACT = {
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

const DEFAULT_RELEASE_DISABLED_ACTION_TYPES = ["Loop", "Switch"];
const DEFAULT_LEGACY_ACTION_TYPE_ALIASES = {
	"Aggregate Records": "Query Records",
	"Create Docs": "Document Action",
	"Sub-rule": "Sub-Rule",
	"Raise Error": "Stop",
};
const DEFAULT_RETURN_TYPE_OPTIONS = ["Boolean", "Dict", "List", "List of Dict", "Doc as Dict"];

export let ACTION_TYPE_CONTRACT = withDescriptions(DEFAULT_ACTION_TYPE_CONTRACT);
export let TRIGGER_TYPE_CONTRACT = { ...DEFAULT_TRIGGER_TYPE_CONTRACT };
export let RELEASE_DISABLED_ACTION_TYPES = new Set(DEFAULT_RELEASE_DISABLED_ACTION_TYPES);
export let LEGACY_ACTION_TYPE_ALIASES = { ...DEFAULT_LEGACY_ACTION_TYPE_ALIASES };
export let RETURN_TYPE_OPTIONS = [...DEFAULT_RETURN_TYPE_OPTIONS];

let _contractsLoaded = false;

function withDescriptions(contractMap) {
	const merged = {};
	Object.entries(contractMap || {}).forEach(([actionType, contract]) => {
		merged[actionType] = {
			...(contract || {}),
			description: ACTION_TYPE_DESCRIPTION[actionType] || contract?.description || "",
		};
	});
	return merged;
}

function applyContractDto(dto = {}) {
	if (dto.action_type_contract && typeof dto.action_type_contract === "object") {
		ACTION_TYPE_CONTRACT = withDescriptions(dto.action_type_contract);
	}

	if (dto.trigger_type_contract && typeof dto.trigger_type_contract === "object") {
		TRIGGER_TYPE_CONTRACT = { ...dto.trigger_type_contract };
	}

	if (Array.isArray(dto.release_disabled_action_types)) {
		RELEASE_DISABLED_ACTION_TYPES = new Set(dto.release_disabled_action_types);
	}

	if (dto.legacy_action_type_aliases && typeof dto.legacy_action_type_aliases === "object") {
		LEGACY_ACTION_TYPE_ALIASES = { ...dto.legacy_action_type_aliases };
	}

	if (Array.isArray(dto.return_type_options) && dto.return_type_options.length) {
		RETURN_TYPE_OPTIONS = [...dto.return_type_options];
	}
}

export async function loadContractsFromBackend(force = false) {
	if (_contractsLoaded && !force) return;
	if (!window.frappe?.call) return;

	try {
		const response = await frappe.call({
			method: "flexirule.ruleflow.api.get_contract_dto",
		});
		if (response?.message) {
			applyContractDto(response.message);
			_contractsLoaded = true;
		}
	} catch (_error) {
		// Keep local fallbacks silently.
	}
}

// Fire-and-forget canonical sync.
loadContractsFromBackend();

/**
 * Get contract for an action type with sensible defaults.
 */
export function getContract(actionType) {
	actionType = normalizeActionType(actionType);
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

export function normalizeActionType(actionType) {
	if (!actionType) return "";
	return LEGACY_ACTION_TYPE_ALIASES[actionType] || actionType;
}

/**
 * Check if action type terminates the flow.
 */
export function isTerminalAction(actionType) {
	return getContract(actionType).terminal || false;
}

/**
 * Get required fields for an action type.
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

export function getReturnTypeOptions() {
	return [...RETURN_TYPE_OPTIONS];
}

/**
 * Validate node data against contract.
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

	for (const field of contract.required_fields || []) {
		const value = nodeData[field];
		if (value === undefined || value === null || value === "") {
			errors.push(__("Field '{0}' is required for {1}", [field, nodeData.action_type]));
		}
	}

	if (nodeData.operation && contract.mandatory_fields?.[nodeData.operation]) {
		for (const field of contract.mandatory_fields[nodeData.operation]) {
			const value = nodeData[field];
			if (value === undefined || value === null || value === "") {
				errors.push(
					__("Field '{0}' is required for {1} in mode {2}", [
						field,
						nodeData.action_type,
						nodeData.operation,
					])
				);
			}
		}
	}

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

	if (!contract.has_next_false && nodeData.next_step_if_false) {
		errors.push(__("{0} does not support 'next step if false'", [nodeData.action_type]));
	}

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

	if ((nodeData.return_type || nodeData.resolved_output_schema) && !nodeData.return_variable) {
		errors.push(__("Return Schema requires a Return Variable Name"));
	}

	return {
		valid: errors.length === 0,
		errors,
	};
}

/**
 * Get all action type options for Select field.
 */
export function getActionTypeOptions() {
	return Object.keys(ACTION_TYPE_CONTRACT).filter(
		(actionType) => !RELEASE_DISABLED_ACTION_TYPES.has(actionType)
	);
}

/**
 * Check if action type supports dynamic fields (e.g., Process with operation schema).
 */
export function hasDynamicFields(actionType) {
	return getContract(actionType).dynamic_fields || false;
}

export default ACTION_TYPE_CONTRACT;
