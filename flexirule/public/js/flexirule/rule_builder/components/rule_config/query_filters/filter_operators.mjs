// Keep Query Filter operator availability aligned with Frappe 15/16's
// built-in filter control, while exposing small pure functions for regression tests.
export const BASE_FILTER_OPERATORS = [
	"=",
	"!=",
	"like",
	"not like",
	"in",
	"not in",
	">",
	"<",
	">=",
	"<=",
	"is",
];
export const EXTENDED_FILTER_OPERATORS = ["Between", "Timespan", "starts with", "ends with"];
export const NESTED_SET_OPERATORS = [
	"descendants of",
	"descendants of (inclusive)",
	"not descendants of",
	"ancestors of",
	"not ancestors of",
];

const INVALID_OPERATORS_BY_FIELD_TYPE = {
	Date: ["like", "not like"],
	Datetime: ["like", "not like", "in", "not in", "=", "!="],
	Data: ["Between", "Timespan"],
	Time: ["Between", "Timespan"],
	Select: ["like", "not like", "Between", "Timespan", ">", "<", ">=", "<="],
	Link: ["Between", "Timespan", ">", "<", ">=", "<="],
	Currency: ["Between", "Timespan"],
	Color: ["Between", "Timespan", ">", "<", ">=", "<="],
	Int: ["like", "not like", "Between", "in", "not in", "Timespan"],
	Float: ["like", "not like", "Between", "in", "not in", "Timespan"],
	Percent: ["like", "not like", "Between", "in", "not in", "Timespan"],
	Rating: ["like", "not like", "Between", "in", "not in", "Timespan"],
	Code: ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	"HTML Editor": ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	"Markdown Editor": ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	"Text Editor": ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	"Small Text": ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	"Long Text": ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	Text: ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
	Password: ["Between", "Timespan", ">", "<", ">=", "<=", "in", "not in"],
};

export function getFieldType(def) {
	return String(def?.original_type || def?.fieldtype || "").trim();
}

function normalizeDoctypeName(value) {
	return String(value ?? "")
		.trim()
		.toLowerCase();
}

function containsDoctype(doctypes, candidate) {
	const wanted = normalizeDoctypeName(candidate);
	if (!wanted || !Array.isArray(doctypes)) return false;
	return doctypes.some((item) => {
		const name = typeof item === "string" ? item : item?.name || item?.parent;
		return normalizeDoctypeName(name) === wanted;
	});
}

function hasFieldType(def, expectedType) {
	return [def?.fieldtype, def?.original_type].some(
		(fieldType) => String(fieldType || "").trim() === expectedType
	);
}

export function supportsNestedSetOperators(def, { nestedSetDoctypes = [], rootDoctype = "" } = {}) {
	if (hasFieldType(def, "Link") && containsDoctype(nestedSetDoctypes, def?.options)) {
		return true;
	}

	// The name field identifies a node in the selected Tree DocType itself.
	return def?.fieldname === "name" && containsDoctype(nestedSetDoctypes, rootDoctype);
}

export function getFilterOperators(def, options = {}) {
	const fieldType = getFieldType(def);

	// Check values are boolean-like; both equality and inequality are meaningful.
	// Check fields may carry original_type even when a value control adapts fieldtype.
	if (hasFieldType(def, "Check")) return ["=", "!="];

	const invalid = INVALID_OPERATORS_BY_FIELD_TYPE[fieldType] || [];
	const operators = [...BASE_FILTER_OPERATORS, ...EXTENDED_FILTER_OPERATORS].filter(
		(operator) => {
			if (invalid.includes(operator)) return false;
			// These aliases compile to LIKE and must not bypass type restrictions.
			return !(["starts with", "ends with"].includes(operator) && invalid.includes("like"));
		}
	);

	if (supportsNestedSetOperators(def, options)) {
		operators.push(...NESTED_SET_OPERATORS.filter((operator) => !operators.includes(operator)));
	}

	return operators;
}
