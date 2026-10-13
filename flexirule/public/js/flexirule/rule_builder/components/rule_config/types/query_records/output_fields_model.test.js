import assert from "node:assert/strict";
import {
	buildResolvedOutputSchema,
	inferResultShape,
	scrubOutputAlias,
	parseOutputFields,
	RESULT_SHAPES,
	serializeOutputFields,
	validateOutputFields,
} from "./output_fields_model.js";

assert.equal(inferResultShape(undefined), RESULT_SHAPES.documentNames);
assert.equal(inferResultShape("*"), RESULT_SHAPES.wholeDocuments);
assert.equal(
	inferResultShape(["name", { items: ["item_code", "qty"] }]),
	RESULT_SHAPES.embeddedChildren
);
assert.equal(
	inferResultShape(["name"], RESULT_SHAPES.selectedFields),
	RESULT_SHAPES.selectedFields
);

const source = [
	"name",
	"customer.customer_name as customer_name",
	{ items: ["item_code", "qty"] },
	{ COUNT: "name", as: "total_users" },
];
const rows = parseOutputFields(source);
assert.deepEqual(
	rows.map((row) => row.kind),
	["field", "field", "child", "function"]
);
assert.deepEqual(serializeOutputFields(rows), [
	"name",
	"customer.customer_name as customer_name",
	{ items: ["item_code", "qty"] },
	"count(name) as total_users",
]);

const expressionRows = parseOutputFields(["sum(grand_total) as total_value"]);
assert.equal(expressionRows[0].kind, "function");
assert.deepEqual(serializeOutputFields(expressionRows), ["sum(grand_total) as total_value"]);
assert.deepEqual(validateOutputFields(expressionRows, RESULT_SHAPES.selectedFields), []);

const mixedAggregateRows = parseOutputFields(["customer", "count(name) as total_users"]);
assert.ok(
	validateOutputFields(mixedAggregateRows, RESULT_SHAPES.selectedFields).some((error) =>
		error.includes("require Group By")
	)
);
assert.deepEqual(
	validateOutputFields(mixedAggregateRows, RESULT_SHAPES.selectedFields, "customer"),
	[]
);

const invalidChildShape = parseOutputFields(["name"]);
assert.ok(
	validateOutputFields(invalidChildShape, RESULT_SHAPES.embeddedChildren).some((error) =>
		error.includes("child-table selection")
	)
);

const invalidMultiLevelPath = parseOutputFields(["customer.address.country"]);
assert.ok(
	validateOutputFields(invalidMultiLevelPath, RESULT_SHAPES.selectedFields).some((error) =>
		error.includes("only one-level Link or child-table field paths")
	)
);

const invalidChildAggregate = parseOutputFields(["sum(items.qty) as total_qty"]);
assert.ok(
	validateOutputFields(invalidChildAggregate, RESULT_SHAPES.selectedFields).some((error) =>
		error.includes("child/link aggregates need backend support")
	)
);

const commaDelimitedFields = parseOutputFields("name, status as status_label");
assert.deepEqual(serializeOutputFields(commaDelimitedFields), ["name", "status as status_label"]);

const commaDelimitedAggregates = parseOutputFields(
	"count(name) as total_users, sum(grand_total) as total_value"
);
assert.deepEqual(
	commaDelimitedAggregates.map((row) => row.kind),
	["function", "function"]
);
assert.deepEqual(serializeOutputFields(commaDelimitedAggregates), [
	"count(name) as total_users",
	"sum(grand_total) as total_value",
]);

const nestedCommasStayInsideExpressions = parseOutputFields(
	"first_name, concat(first_name, last_name) as full_name"
);
assert.equal(nestedCommasStayInsideExpressions.length, 2);
assert.equal(nestedCommasStayInsideExpressions[1].kind, "raw");

const aggregateOnlyRows = parseOutputFields(["count(name) as total_users"]);
assert.deepEqual(validateOutputFields(aggregateOnlyRows, RESULT_SHAPES.selectedFields), []);

assert.equal(scrubOutputAlias("Reference Doctype"), "reference_doctype");
assert.equal(scrubOutputAlias("totalCount"), "total_count");
assert.equal(scrubOutputAlias("Total-Count"), "total_count");

const aliasedSchema = buildResolvedOutputSchema({
	shape: RESULT_SHAPES.selectedFields,
	fields: ["voucher_type as reference_doctype", "title", "count(name) as totals"],
	fieldInfoByPath: {
		voucher_type: { label: "Voucher Type", fieldtype: "Select" },
		title: { label: "Title", fieldtype: "Data" },
		name: { label: "ID (name)", fieldtype: "Data" },
	},
});
assert.deepEqual(
	aliasedSchema.map(({ fieldname, label, fieldtype }) => ({ fieldname, label, fieldtype })),
	[
		{ fieldname: "reference_doctype", label: "Reference Doctype", fieldtype: "Select" },
		{ fieldname: "title", label: "Title", fieldtype: "Data" },
		{ fieldname: "totals", label: "Totals", fieldtype: "Int" },
	]
);

const wholeDocumentSchema = buildResolvedOutputSchema({
	shape: RESULT_SHAPES.wholeDocuments,
	wholeDocumentFields: [
		{ fieldname: "title", label: "Title", fieldtype: "Data" },
		{ fieldname: "status", label: "Status", fieldtype: "Select" },
	],
	systemFields: [
		{ fieldname: "name", label: "ID (name)", fieldtype: "Data" },
		{ fieldname: "owner", label: "Created By (owner)", fieldtype: "Link", options: "User" },
	],
});
assert.deepEqual(
	wholeDocumentSchema.map((field) => field.fieldname),
	["title", "status", "name", "owner"]
);

console.log("output fields model tests passed");
