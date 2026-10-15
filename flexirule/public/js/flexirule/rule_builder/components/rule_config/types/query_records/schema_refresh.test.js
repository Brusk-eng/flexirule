import assert from "node:assert/strict";
import { getQueryRecordsSchemaRefreshSignature } from "./schema_refresh.js";

const base = {
	mode: "Fetch Records",
	referenceDoctype: "Sales Invoice",
	referenceDocname: null,
	config: {
		fields: ["name", "customer"],
		result_shape: "selected_fields",
		filters: [{ field: "status", operator: "=", value: "Paid" }],
		order_by: "modified desc",
		limit: 20,
	},
};
const signature = getQueryRecordsSchemaRefreshSignature(base);

// Row selection options do not alter the exposed output contract.
assert.equal(
	getQueryRecordsSchemaRefreshSignature({
		...base,
		config: {
			...base.config,
			filters: [{ field: "status", operator: "=", value: "Draft" }],
			order_by: "name asc",
			limit: 100,
		},
	}),
	signature
);

// Output-defining inputs do invalidate the signature.
for (const config of [
	{ ...base.config, fields: ["name", "customer", "grand_total"] },
	{ ...base.config, result_shape: "whole_documents" },
	{ ...base.config, fetch_strategy: "Get latest Doc" },
]) {
	assert.notEqual(
		getQueryRecordsSchemaRefreshSignature({ ...base, config }),
		signature
	);
}
assert.notEqual(
	getQueryRecordsSchemaRefreshSignature({ ...base, referenceDoctype: "Customer" }),
	signature
);
assert.notEqual(
	getQueryRecordsSchemaRefreshSignature({ ...base, mode: "Query List" }),
	signature
);
assert.notEqual(
	getQueryRecordsSchemaRefreshSignature({
		...base,
		referenceDocname: "Accounts Receivable",
	}),
	signature
);

console.log("query records schema refresh tests passed");
