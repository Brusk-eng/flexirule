// Copyright (c) 2025, FlexiRule and contributors
frappe.provide("flexirule.processes");

flexirule.processes["Deduplication"] = {
	meta: {
		version: "2.0",
		title: __("Deduplication"),
	},

	get_schema(operation_name, ctx) {
		const operation = this.get_operation(operation_name);
		if (!operation) return [];
		return typeof operation.get_config_fields === "function"
			? operation.get_config_fields(ctx)
			: [];
	},

	get_output_schema(operation_name, config, context) {
		const op_name =
			typeof operation_name === "string"
				? operation_name
				: context?.operation_name || context?.operation || config?.operation;
		const operation = this.get_operation(op_name);
		if (operation && typeof operation.get_output_schema === "function") {
			return operation.get_output_schema(
				typeof operation_name === "string" ? config : operation_name,
				typeof operation_name === "string" ? context : config
			);
		}
		return [];
	},

	operations: [
		{
			func_name: "find_matching_records",
			label: __("Find Matching Records"),
			description: __(
				"Fetch candidate records with blocking filters, score them against the current document, and return structured match details."
			),
			category: "Matching",
			icon: "search",
			color: "#f59e0a",
			validate: (cfg) => {
				if ((!cfg.fields_config || cfg.fields_config.length === 0) && !cfg.fields) {
					return __("Add comparison rules or exact-match fields.");
				}
				return null;
			},
			get_config_fields: (ctx) => [
				{
					fieldtype: "Section Break",
					label: __("Candidate Selection"),
				},
				{
					fieldname: "candidate_doctype",
					fieldtype: "Link",
					options: "DocType",
					label: __("Candidate DocType"),
					description: __("Defaults to the current document DocType if left blank."),
				},
				{
					fieldname: "candidate_limit",
					fieldtype: "Int",
					label: __("Candidate Limit"),
					default: 1000,
				},
				{
					fieldname: "ignore_cancelled",
					fieldtype: "Check",
					label: __("Ignore Cancelled Documents"),
					default: 1,
				},
				{
					fieldname: "exclude_current_document",
					fieldtype: "Check",
					label: __("Exclude Current Document"),
					default: 1,
				},
				{
					fieldname: "stop_after_first_match",
					fieldtype: "Check",
					label: __("Stop After First Match"),
					default: 0,
				},
				{
					fieldtype: "Section Break",
					label: __("Scoring Rules"),
				},
				{
					fieldname: "overall_threshold",
					fieldtype: "Float",
					label: __("Overall Threshold"),
					default: 0.8,
					reqd: 1,
				},
				{
					fieldname: "minimum_fields_matched",
					fieldtype: "Int",
					label: __("Minimum Fields Matched"),
					default: 1,
				},
				{
					fieldname: "fields_config",
					fieldtype: "Table",
					label: __("Field Comparison Rules"),
					reqd: 1,
					fields: get_dedupe_table_fields(),
				},
			],
			get_output_schema: () => [
				{ label: __("Has Match"), value: "has_match", type: "Check" },
				{ label: __("Match Count"), value: "match_count", type: "Int" },
				{ label: __("Best Match"), value: "best_match", type: "JSON" },
				{ label: __("Matches"), value: "matches", type: "JSON" },
				{ label: __("Criteria"), value: "criteria", type: "JSON" },
			],
		},
		{
			func_name: "find_duplicates_in_child_table",
			label: __("Find Child Table Matches"),
			description: __(
				"Find parent documents whose child-table rows contain values already present in the current document."
			),
			category: "Matching",
			icon: "table",
			color: "#0ea5e9",
			validate: (cfg) => {
				if (!cfg.child_table_field) return __("Child Table Field is required.");
				if (!cfg.child_search_field) return __("Child Search Field is required.");
				return null;
			},
			get_config_fields: () => [
				{
					fieldname: "child_table_field",
					fieldtype: "Data",
					label: __("Child Table Field"),
					reqd: 1,
				},
				{
					fieldname: "child_search_field",
					fieldtype: "Data",
					label: __("Field to Compare"),
					reqd: 1,
				},
				{
					fieldname: "normalize_values",
					fieldtype: "Check",
					label: __("Normalize Values"),
					default: 1,
				},
				{
					fieldname: "ignore_cancelled",
					fieldtype: "Check",
					label: __("Ignore Cancelled Documents"),
					default: 1,
				},
				{
					fieldname: "result_limit",
					fieldtype: "Int",
					label: __("Result Limit"),
					default: 1000,
				},
			],
			get_output_schema: () => [
				{ label: __("Has Match"), value: "has_match", type: "Check" },
				{ label: __("Match Count"), value: "match_count", type: "Int" },
				{ label: __("Best Match"), value: "best_match", type: "JSON" },
				{ label: __("Matches"), value: "matches", type: "JSON" },
				{ label: __("Values Checked"), value: "values_checked", type: "JSON" },
			],
		},
	],

	get_operation(name) {
		return this.operations.find((op) => op.func_name === name);
	},
};

const SHARED = {
	validTypes: [
		"Data",
		"Link",
		"Text",
		"Phone",
		"Email",
		"Small Text",
		"Date",
		"Int",
		"Float",
		"Currency",
	],

	async get_field_options(meta) {
		if (!meta?.name) return [];
		const all_fields = await flexirule.utils.get_doctype_fields(meta.name);
		return all_fields
			.filter((f) => SHARED.validTypes.includes(f.fieldtype))
			.map((f) => ({
				label: f.label,
				value: f.value,
				description: f.description,
			}));
	},

	on_algorithm_change(value, ctx) {
		const defaults = {
			Exact: { threshold: 1.0, tolerance: 0, weight: 1.0 },
			Phonetic: { threshold: 0.9, tolerance: 0, weight: 0.5 },
			Fuzzy: { threshold: 0.8, tolerance: 0, weight: 0.5 },
			"Date Distance": { threshold: 0.5, tolerance: 30, weight: 0.4 },
			"Numeric Range": { threshold: 0.5, tolerance: 30, weight: 0.4 },
			Contains: { threshold: 0.8, tolerance: 0, weight: 0.5 },
		};
		const config = defaults[value] || {};
		if (config.threshold !== undefined) ctx.update_field("threshold", config.threshold);
		if (config.tolerance !== undefined) ctx.update_field("tolerance", config.tolerance);
		if (config.weight !== undefined) ctx.update_field("weight", config.weight);
	},
};

function get_dedupe_table_fields() {
	return [
		{
			fieldname: "fieldname",
			fieldtype: "DocField",
			options: "vars.document_type",
			label: __("Field"),
			reqd: 1,
			in_list_view: 1,
			get_options: (cfg, ctx, meta) => SHARED.get_field_options(meta),
		},
		{
			fieldname: "algorithm",
			fieldtype: "Select",
			label: __("Algorithm"),
			options: "Exact\nFuzzy\nPhonetic\nContains\nNumeric Range\nDate Distance",
			reqd: 1,
			default: "Fuzzy",
			in_list_view: 1,
			onchange: (val, row, ctx) => SHARED.on_algorithm_change(val, ctx),
		},
		{
			fieldname: "weight",
			fieldtype: "Float",
			label: __("Weight"),
			default: 0.5,
			in_list_view: 1,
		},
		{
			fieldname: "threshold",
			fieldtype: "Float",
			label: __("Threshold"),
			default: 0.8,
			in_list_view: 1,
			depends_on: "eval:doc.algorithm !== 'Exact'",
		},
		{
			fieldname: "tolerance",
			fieldtype: "Int",
			label: __("Tolerance"),
			default: 30,
			in_list_view: 1,
			depends_on: "eval:in_list(['Numeric Range', 'Date Distance'], doc.algorithm)",
			description: __("Allowed deviation (plus/minus)"),
		},
		{
			fieldname: "normalize",
			fieldtype: "Check",
			label: __("Normalize Values"),
			default: 1,
			in_list_view: 1,
		},
		{
			fieldname: "included_in_filters",
			fieldtype: "Check",
			label: __("Use for Blocking"),
			default: 1,
			in_list_view: 1,
		},
	];
}
