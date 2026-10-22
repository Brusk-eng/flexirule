import assert from "node:assert/strict";
import {
	isFilterLeafValid,
	validateFilterLeaf,
	isValueConfigured,
} from "./query_filter_validation.js";

// Global mock for translation __
if (typeof globalThis.__ !== "function") {
	globalThis.__ = (str, args) => {
		if (!args || !args.length) return str;
		return str.replace(/\{(\d+)\}/g, (_, index) => args[index] ?? "");
	};
}

function humanize(raw) {
	if (!raw) return "";
	return String(raw)
		.replace(/_/g, " ")
		.replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatSingleValue(val) {
	if (val === null || val === undefined || val === "") return "";
	if (typeof val === "object" && val.mode) {
		if (val.mode === "static") {
			return formatSingleValue(val.value);
		}
		if (val.mode === "variable") {
			const varName = val.value || val.variable || "";
			return __("Variable ({0})", [varName]);
		}
		if (val.mode === "resolver" || val.resolver_type) {
			const name = val.resolver_type || val.mode || "Resolver";
			return humanize(name);
		}
		return humanize(val.mode);
	}
	if (Array.isArray(val)) {
		return val.map(formatSingleValue).filter(Boolean).join(", ");
	}
	return String(val);
}

// Validity checks using imported production validator
assert.equal(
	isFilterLeafValid({ field: "", operator: "=", value: { mode: "static", value: "" } }),
	false
);
assert.equal(
	isFilterLeafValid({ field: "status", operator: "=", value: { mode: "static", value: "" } }),
	false
);
assert.equal(
	isFilterLeafValid({ field: "status", operator: "=", value: { mode: "static", value: "Open" } }),
	true
);
assert.equal(
	isFilterLeafValid({ field: "status", operator: "is", value: { mode: "static", value: "set" } }),
	true
);
assert.equal(
	isFilterLeafValid({
		field: "amount",
		operator: "Between",
		value: [
			{ mode: "static", value: 10 },
			{ mode: "static", value: 50 },
		],
	}),
	true
);
assert.equal(
	isFilterLeafValid({
		field: "amount",
		operator: "Between",
		value: [{ mode: "static", value: 10 }],
	}),
	false
);
assert.equal(
	isFilterLeafValid({
		field: "customer",
		operator: "=",
		value: { mode: "variable", value: "doc.customer" },
	}),
	true
);

// Operator compatibility check
assert.equal(
	isFilterLeafValid(
		{
			field: "creation",
			operator: "invalid_op",
			value: { mode: "static", value: "2026-01-01" },
		},
		{ fieldDef: { fieldtype: "Datetime" } }
	),
	false
);

// Detailed validation result test
assert.equal(validateFilterLeaf({ field: "", operator: "=" }).valid, false);
assert.equal(
	validateFilterLeaf({ field: "status", operator: "=", value: { mode: "static", value: "Open" } })
		.valid,
	true
);

// Value formatting checks
assert.equal(formatSingleValue({ mode: "static", value: "Open" }), "Open");
assert.equal(
	formatSingleValue({ mode: "variable", value: "doc.customer" }),
	"Variable (doc.customer)"
);
assert.equal(
	formatSingleValue([
		{ mode: "static", value: "A" },
		{ mode: "static", value: "B" },
	]),
	"A, B"
);

console.log("filter leaf summary unit tests passed");
