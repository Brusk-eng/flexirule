export const RESULT_SHAPES = Object.freeze({
	documentNames: "document_names",
	wholeDocuments: "whole_documents",
	selectedFields: "selected_fields",
	embeddedChildren: "embedded_children",
});
export const AGGREGATE_FUNCTIONS = Object.freeze(["count", "sum", "avg", "min", "max"]);
const AGGREGATE_SET = new Set(AGGREGATE_FUNCTIONS);
const ALIAS_PATTERN = /^[A-Za-z_][A-Za-z0-9_]*$/;
function clone(value) {
	if (value === undefined) return undefined;
	return JSON.parse(JSON.stringify(value));
}
function isObject(value) {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}
export function isCustomResultShape(shape) {
	return shape === RESULT_SHAPES.selectedFields || shape === RESULT_SHAPES.embeddedChildren;
}
export function isChildFieldSelection(value) {
	if (!isObject(value)) return false;
	return Object.entries(value).some(([key, nested]) => key !== "as" && Array.isArray(nested));
}
function isAggregateDescriptor(value) {
	if (!isObject(value)) return false;
	return Object.keys(value).some((key) => AGGREGATE_SET.has(key.toLowerCase()));
}
export function inferResultShape(fields, explicitShape) {
	if (Object.values(RESULT_SHAPES).includes(explicitShape)) return explicitShape;
	if (fields === "*" || (Array.isArray(fields) && fields.length === 1 && fields[0] === "*")) {
		return RESULT_SHAPES.wholeDocuments;
	}
	if (fields == null || fields === "" || (Array.isArray(fields) && fields.length === 0)) {
		return RESULT_SHAPES.documentNames;
	}
	if (Array.isArray(fields) && fields.length === 1 && fields[0] === "name") {
		return RESULT_SHAPES.documentNames;
	}
	const list = Array.isArray(fields) ? fields : [fields];
	if (list.some((item) => isChildFieldSelection(item) && !isAggregateDescriptor(item))) {
		return RESULT_SHAPES.embeddedChildren;
	}
	return RESULT_SHAPES.selectedFields;
}
function parseAlias(expression) {
	const match = String(expression)
		.trim()
		.match(/^(.+?)\s+as\s+([A-Za-z_][A-Za-z0-9_]*)$/i);
	if (!match) return { expression: String(expression).trim(), alias: "" };
	return { expression: match[1].trim(), alias: match[2] };
}
function createRow(kind, index, values = {}) {
	return {
		id: "output-" + index,
		kind,
		field: "",
		alias: "",
		functionName: "count",
		tableField: "",
		fields: [],
		expression: "",
		originalValue: undefined,
		dirty: false,
		...values,
	};
}
function parseTextField(value, index) {
	const raw = String(value ?? "").trim();
	const withAlias = parseAlias(raw);
	const functionMatch = withAlias.expression.match(
		/^(count|sum|avg|min|max)\s*\(\s*([^)]+?)\s*\)$/i
	);
	if (functionMatch) {
		return createRow("function", index, {
			functionName: functionMatch[1].toLowerCase(),
			field: functionMatch[2].trim(),
			alias: withAlias.alias,
		});
	}
	if (
		raw === "" ||
		/^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$/.test(withAlias.expression)
	) {
		return createRow("field", index, { field: withAlias.expression, alias: withAlias.alias });
	}
	return createRow("raw", index, { expression: raw, originalValue: raw });
}
/**
 * Convert persisted Frappe field grammar into editable rows.
 * Aggregate descriptors are accepted on input so the UI can recognize them,
 * but normalized to native Frappe v15 string expressions on save. Branch capability
 * tests show get_query rejects aggregate dictionaries.
 */
export function parseOutputFields(value) {
	let list;
	if (Array.isArray(value)) {
		list = value;
	} else if (typeof value === "string" && value.trim()) {
		const raw = value.trim();
		if (raw === "*" || /[()]/.test(raw)) list = [raw];
		else
			list = raw
				.split(",")
				.map((part) => part.trim())
				.filter(Boolean);
	} else {
		list = [];
	}
	const rows = [];
	let index = 0;
	for (const item of list) {
		if (typeof item === "string" || typeof item === "number") {
			rows.push(parseTextField(item, index++));
			continue;
		}
		if (isObject(item)) {
			const aggregateKey = Object.keys(item).find((key) =>
				AGGREGATE_SET.has(key.toLowerCase())
			);
			if (aggregateKey) {
				rows.push(
					createRow("function", index++, {
						functionName: aggregateKey.toLowerCase(),
						field: String(item[aggregateKey] ?? ""),
						alias: String(item.as ?? ""),
						originalValue: clone(item),
					})
				);
				continue;
			}
			const childEntries = Object.entries(item).filter(
				([key, nested]) => key !== "as" && Array.isArray(nested)
			);
			if (childEntries.length) {
				for (const [tableField, childFields] of childEntries) {
					rows.push(
						createRow("child", index++, { tableField, fields: clone(childFields) })
					);
				}
				continue;
			}
		}
		rows.push(
			createRow("raw", index++, {
				expression: JSON.stringify(item),
				originalValue: clone(item),
			})
		);
	}
	return rows;
}
export function serializeOutputFields(rows) {
	return (Array.isArray(rows) ? rows : []).map((row) => {
		if (row.kind === "field") {
			const field = String(row.field ?? "").trim();
			const alias = String(row.alias ?? "").trim();
			return field && alias ? field + " as " + alias : field;
		}
		if (row.kind === "function") {
			const fn = String(row.functionName ?? "count").toLowerCase();
			const field = String(row.field ?? "").trim();
			const alias = String(row.alias ?? "").trim();
			const expression = fn + "(" + field + ")";
			return alias ? expression + " as " + alias : expression;
		}
		if (row.kind === "child") {
			const tableField = String(row.tableField ?? "").trim();
			const fields = Array.isArray(row.fields) ? clone(row.fields) : [];
			return tableField ? { [tableField]: fields } : {};
		}
		if (row.dirty) {
			const expression = String(row.expression ?? "").trim();
			try {
				return JSON.parse(expression);
			} catch {
				return expression;
			}
		}
		return clone(row.originalValue !== undefined ? row.originalValue : row.expression);
	});
}
export function validateOutputFields(rows, shape, groupBy = "") {
	const errors = [];
	const list = Array.isArray(rows) ? rows : [];
	const hasAggregate = list.some((row) => row.kind === "function");
	const hasRegularField = list.some((row) => ["field", "raw"].includes(row.kind));

	if (hasAggregate && hasRegularField && !String(groupBy || "").trim()) {
		errors.push(
			"Aggregate functions mixed with regular fields require Group By. Configure Group By under Retrieval Settings, or remove regular output fields."
		);
	}
	const aliases = new Set();
	if (!list.length) errors.push("Add at least one output field.");
	if (shape === RESULT_SHAPES.embeddedChildren && !list.some((row) => row.kind === "child")) {
		errors.push("Embedded children requires at least one child-table selection.");
	}
	for (const [index, row] of list.entries()) {
		const prefix = "Output field " + (index + 1) + ": ";
		if (row.kind === "field") {
			const fieldPath = String(row.field ?? "").trim();
			if (!fieldPath) errors.push(prefix + "select a field.");
			else if (fieldPath.split(".").length > 2) {
				errors.push(
					prefix +
						"Frappe v15 supports only one-level Link or child-table field paths in this selection."
				);
			}
		} else if (row.kind === "function") {
			const fn = String(row.functionName ?? "").toLowerCase();
			const field = String(row.field ?? "").trim();
			const alias = String(row.alias ?? "").trim();
			if (!AGGREGATE_SET.has(fn)) errors.push(prefix + "choose a supported function.");
			if (!field) errors.push(prefix + "select a field for the function.");
			else if (field.includes(".")) {
				errors.push(
					prefix +
						"aggregate functions currently support root DocType fields only; child/link aggregates need backend support."
				);
			}
			if (!alias) errors.push(prefix + "enter an output alias for the function.");
			else if (!ALIAS_PATTERN.test(alias)) {
				errors.push(
					prefix +
						"alias must start with a letter or underscore and contain only letters, numbers, and underscores."
				);
			}
		} else if (row.kind === "child") {
			if (!String(row.tableField ?? "").trim()) errors.push(prefix + "select a child table.");
			if (!Array.isArray(row.fields) || !row.fields.length) {
				errors.push(prefix + "select at least one child field.");
			}
		} else if (row.kind === "raw" && !String(row.expression ?? "").trim()) {
			errors.push(prefix + "enter a field expression.");
		}
		const alias = String(row.alias ?? "").trim();
		if (alias) {
			if (!ALIAS_PATTERN.test(alias)) {
				if (row.kind !== "function") {
					errors.push(
						prefix +
							"alias must start with a letter or underscore and contain only letters, numbers, and underscores."
					);
				}
			} else if (aliases.has(alias)) {
				errors.push(prefix + "Alias '" + alias + "' is already used.");
			} else {
				aliases.add(alias);
			}
		}
	}
	return errors;
}
