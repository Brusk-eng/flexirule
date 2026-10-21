import assert from "node:assert/strict";

// Setup global Frappe translation helper for unit tests
globalThis.__ = (s, args) => {
	if (!args) return s;
	if (Array.isArray(args)) {
		args.forEach((a, i) => {
			s = s.replace(`{${i}}`, a);
		});
	}
	return s;
};

import {
	hasResolvedOutputSchema,
	requiresReturnVariable,
	validateAgainstContract,
	ACTION_TYPES_WITH_RETURN_SCHEMA,
	ACTION_TYPE_CONTRACT,
} from "./contracts.js";

// Setup mock contract state for unit tests matching backend DTO defaults
ACTION_TYPES_WITH_RETURN_SCHEMA.add("Query Records");
ACTION_TYPES_WITH_RETURN_SCHEMA.add("Process");

ACTION_TYPE_CONTRACT["Assignment"] = {
	required_fields: ["config"],
	allowed_mutations: ["Set Context Variable", "Update Context Variable"],
	produces_result: true,
};
ACTION_TYPE_CONTRACT["Query Records"] = {
	required_fields: ["reference_doctype"],
	supports_return_schema: true,
	allowed_return_types: ["List of Documents", "Document", "Value / Primitive"],
	allowed_mutations: ["Set Context Variable", "Update Context Variable"],
	produces_result: true,
};
ACTION_TYPE_CONTRACT["Stop"] = {
	required_fields: [],
	terminal: true,
	produces_result: false,
};

// --- 1. Test hasResolvedOutputSchema ---
console.log("Testing hasResolvedOutputSchema...");

assert.equal(hasResolvedOutputSchema(null), false);
assert.equal(hasResolvedOutputSchema(undefined), false);
assert.equal(hasResolvedOutputSchema(""), false);
assert.equal(hasResolvedOutputSchema("null"), false);
assert.equal(hasResolvedOutputSchema("[]"), false);
assert.equal(hasResolvedOutputSchema("{}"), false);
assert.equal(hasResolvedOutputSchema('""'), false);
assert.equal(hasResolvedOutputSchema([]), false);
assert.equal(hasResolvedOutputSchema({}), false);
assert.equal(hasResolvedOutputSchema({ fields: [] }), false);
assert.equal(hasResolvedOutputSchema({ properties: {} }), false);

// Valid populated schema representations
assert.equal(hasResolvedOutputSchema([{ fieldname: "total", fieldtype: "Currency" }]), true);
assert.equal(hasResolvedOutputSchema(JSON.stringify([{ fieldname: "total" }])), true);
assert.equal(hasResolvedOutputSchema({ fields: [{ fieldname: "items" }] }), true);
assert.equal(hasResolvedOutputSchema({ properties: { age: { type: "integer" } } }), true);

// --- 2. Test requiresReturnVariable ---
console.log("Testing requiresReturnVariable...");

// Action with no requirements
assert.equal(requiresReturnVariable({ action_type: "Assignment" }), false);

// Action with mutation mode
assert.equal(
	requiresReturnVariable({ action_type: "Assignment", mutation_mode: "Set Context Variable" }),
	true
);

// Stale return_type or output_schema when action policy produces_result is false
const stopNodeWithStaleData = {
	action_type: "Stop",
	return_type: "Document",
	resolved_output_schema: [{ fieldname: "total" }],
};
assert.equal(requiresReturnVariable(stopNodeWithStaleData), false);

// Action with supports_return_schema: true (e.g. Query Records or Process) and return_type
const queryRecordsNode = {
	action_type: "Query Records",
	return_type: "List of Documents",
};
assert.equal(requiresReturnVariable(queryRecordsNode), true);

// Query Records node with populated output schema
const queryRecordsNodeWithSchema = {
	action_type: "Query Records",
	resolved_output_schema: [{ fieldname: "name" }],
};
assert.equal(requiresReturnVariable(queryRecordsNodeWithSchema), true);

// Query Records node with empty/stale output schema "[]" and no return_type
const queryRecordsNodeWithEmptySchema = {
	action_type: "Query Records",
	resolved_output_schema: "[]",
};
assert.equal(requiresReturnVariable(queryRecordsNodeWithEmptySchema), false);

// --- 3. Test validateAgainstContract deduplication ---
console.log("Testing validateAgainstContract...");

// Node missing return variable when required should produce exactly 1 error for missing return variable
const nodeMissingReturnVar = {
	action_type: "Query Records",
	return_type: "List of Documents",
	resolved_output_schema: [{ fieldname: "name" }],
	return_variable: "",
	reference_doctype: "Customer",
};

const validation = validateAgainstContract(nodeMissingReturnVar);
assert.equal(validation.valid, false);
const returnVarErrors = validation.errors.filter((e) =>
	e.includes("Return Variable Name is required")
);
assert.equal(
	returnVarErrors.length,
	1,
	`Expected 1 return variable error, got ${returnVarErrors.length}: ${JSON.stringify(validation.errors)}`
);

console.log("All contract unit tests passed!");
