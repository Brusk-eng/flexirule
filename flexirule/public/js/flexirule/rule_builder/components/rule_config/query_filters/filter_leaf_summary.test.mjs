import assert from "node:assert/strict";

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

function isValueConfigured(val) {
	if (val === null || val === undefined || val === "") return false;
	if (typeof val === "object" && val.mode) {
		if (val.mode === "static") return isValueConfigured(val.value);
		return Boolean(val.value || val.expression || val.resolver_type);
	}
	if (Array.isArray(val)) return val.length > 0 && val.every(isValueConfigured);
	return String(val).trim() !== "";
}

function isLeafValid(node) {
	if (!node?.field) return false;
	if (!node?.operator) return false;
	const op = node.operator;
	if (op === "Between") {
		const arr = Array.isArray(node?.value) ? node.value : [];
		return arr.length >= 2 && isValueConfigured(arr[0]) && isValueConfigured(arr[1]);
	}
	if (String(op).toLowerCase() === "is") {
		const val = node?.value;
		const raw = typeof val === "object" && val?.mode === "static" ? val.value : val;
		if (typeof raw === "string" && ["set", "not set"].includes(raw.trim().toLowerCase())) {
			return true;
		}
		return isValueConfigured(val);
	}
	return isValueConfigured(node?.value);
}

// Validity checks
assert.equal(
	isLeafValid({ field: "", operator: "=", value: { mode: "static", value: "" } }),
	false
);
assert.equal(
	isLeafValid({ field: "status", operator: "=", value: { mode: "static", value: "" } }),
	false
);
assert.equal(
	isLeafValid({ field: "status", operator: "=", value: { mode: "static", value: "Open" } }),
	true
);
assert.equal(
	isLeafValid({ field: "status", operator: "is", value: { mode: "static", value: "set" } }),
	true
);
assert.equal(
	isLeafValid({
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
	isLeafValid({ field: "amount", operator: "Between", value: [{ mode: "static", value: 10 }] }),
	false
);
assert.equal(
	isLeafValid({
		field: "customer",
		operator: "=",
		value: { mode: "variable", value: "doc.customer" },
	}),
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
