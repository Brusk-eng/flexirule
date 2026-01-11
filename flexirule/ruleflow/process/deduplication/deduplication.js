// Copyright (c) 2025, FlexiRule and contributors
frappe.provide("flexirule.processes");

/**
 * Deduplication Process Adapter
 * Standardizes configuration for deduplication operations.
 * Directly compatible with the ConfigurableAction runtime.
 */
flexirule.processes.Deduplication = {
	meta: {
		version: "1.0",
		title: __("Deduplication"),
	},

	setup(ctx) {
		// Global setup for the entire adapter
	},

	/**
	 * Returns the schema for a specific operation.
	 * If omitted, the runtime falls back to operation.get_config_fields().
	 */
	get_schema(operation_name, ctx) {
		const operation = this.get_operation(operation_name);
		if (!operation) return [];

		return typeof operation.get_config_fields === "function"
			? operation.get_config_fields(ctx)
			: [];
	},

	operations: [
		{
			func_name: "find_similar_records",
			label: __("Find Similar Records"),
			description: __("Find similar records using configurable algorithms"),
			category: "Matching",
			icon: "search",
			color: "#f59e0b",
			setup: (cfg, ctx) => {
				// Initialize defaults if missing
				if (cfg.overall_threshold === undefined) {
					ctx.update_field("overall_threshold", 0.8);
				}
			},
			validate: (cfg, ctx) => {
				if (cfg.overall_threshold < 0 || cfg.overall_threshold > 1) {
					return __("Overall Threshold must be between 0.0 and 1.0");
				}
				if (!cfg.fields_config || cfg.fields_config.length === 0) {
					return __("At least one Field Comparison Rule is required.");
				}
				return null;
			},
			get_config_fields: (ctx) => [
				{
					fieldtype: "Section Break",
					label: __("Configuration"),
				},
				{
					fieldname: "overall_threshold",
					fieldtype: "Float",
					label: __("Overall Threshold"),
					default: 0.8,
					reqd: 1,
					description: __(
						"Minimum match score required to consider a record similar (0.0 - 1.0)"
					),
					columns: 1,
				},
				{
					fieldname: "minimum_fields_matched",
					fieldtype: "Int",
					label: __("Min Fields to Match"),
					default: 1,
					description: __(
						"Minimum number of fields that must meet their individual thresholds"
					),
					columns: 1,
				},
				{
					fieldname: "stop_after_first_match",
					fieldtype: "Check",
					label: __("Stop After First Match"),
					default: 0,
					description: __("Stop searching once a match is found"),
				},
				{
					fieldtype: "Section Break",
					label: __("Rules"),
				},
				{
					fieldname: "help_html",
					fieldtype: "HTML",
					options: `<div class="text-muted small">
                        Define how each field should be compared. 
                        <b>Fuzzy</b> handles typos. <b>Exact</b> requires precise match. 
                        <b>Numeric/Date</b> allow ranges.
                    </div>`,
				},
				{
					fieldname: "fields_config",
					fieldtype: "Table",
					label: __("Field Comparison Rules"),
					reqd: 1,
					fields: get_dedupe_table_fields(),
				},
			],
		},
		{
			func_name: "find_duplicates_by_fields",
			label: __("Find Exact Duplicates"),
			category: "Matching",
			icon: "duplicate",
			color: "#ef4444",
			validate: (cfg, ctx) => {
				if (!cfg.fields || cfg.fields.length === 0) {
					return __("Please select at least one field to match.");
				}
			},
			get_config_fields: (ctx) => [
				{
					fieldname: "fields",
					fieldtype: "MultiDocField",
					label: __("Fields to Match"),
					options: "vars.document_type",
					reqd: 1,
					description: __("Select fields that must match exactly"),
				},
				{
					fieldname: "ignore_cancelled",
					fieldtype: "Check",
					label: __("Ignore Cancelled Documents"),
					default: 1,
				},
			],
		},
		{
			func_name: "check_duplicate_and_prevent_save",
			label: __("Block If Duplicate Exists"),
			category: "Validation",
			icon: "block",
			color: "#dc2626",
			validate: (cfg, ctx) => {
				if (!cfg.fields || cfg.fields.length === 0) {
					return __("Please define unique fields.");
				}
			},
			get_config_fields: (ctx) => [
				{
					fieldname: "fields",
					fieldtype: "MultiDocField",
					label: __("Unique Fields"),
					options: "vars.document_type",
					reqd: 1,
					description: __(
						"If a document exists with these exact values, save will be blocked."
					),
				},
			],
		},
		{
			func_name: "check_similar_and_prevent_save",
			label: __("Block If Similar Exists"),
			category: "Validation",
			icon: "block",
			color: "#b91c1c",
			setup: (cfg, ctx) => {
				if (cfg.overall_threshold === undefined) {
					ctx.update_field("overall_threshold", 0.8);
				}
			},
			validate: (cfg, ctx) => {
				if (!cfg.fields_config || cfg.fields_config.length === 0) {
					return __("Please add comparison rules.");
				}
			},
			get_config_fields: (ctx) => [
				{
					fieldname: "overall_threshold",
					fieldtype: "Float",
					label: __("Overall Threshold"),
					default: 0.8,
					reqd: 1,
				},
				{
					fieldname: "fields_config",
					fieldtype: "Table",
					label: __("Field Comparison Rules"),
					reqd: 1,
					fields: get_dedupe_table_fields(),
				},
			],
		},
		{
			func_name: "mark_as_duplicate",
			label: __("Mark as Duplicate"),
			category: "Actions",
			icon: "link",
			color: "#8b5cf6",
			get_config_fields: (ctx) => [
				{
					fieldname: "master_document",
					fieldtype: "Data",
					label: __("Master Document ID"),
					reqd: 1,
					description: __("Field containing the Master Document Name or ID"),
				},
			],
		},
		{
			func_name: "find_duplicates_in_child_table",
			label: __("Find Duplicates in Child Table"),
			category: "Matching",
			icon: "table",
			color: "#0ea5e9",
			get_config_fields: (ctx) => [
				{
					fieldname: "child_table_field",
					fieldtype: "Data",
					label: __("Child Table Field"),
					reqd: 1,
				},
				{
					fieldname: "child_search_field",
					fieldtype: "Data",
					label: __("Field to Check"),
					reqd: 1,
				},
			],
		},
	],

	/**
	 * Get an operation definition by name
	 */
	get_operation(name) {
		return this.operations.find((op) => op.func_name === name);
	},
};

// = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
// SHARED UTILITIES
// = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

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

		// Do not return the promise chain here to avoid deadlock with the runtime's internal sequencer.
		// Each update_field call will append itself to the chain automatically.
		if (config.threshold !== undefined) ctx.update_field("threshold", config.threshold);
		if (config.tolerance !== undefined) ctx.update_field("tolerance", config.tolerance);
		if (config.weight !== undefined) ctx.update_field("weight", config.weight);
	},
};

/**
 * Returns the schema for the Fields Configuration table
 */
function get_dedupe_table_fields() {
	return [
		{
			fieldname: "sb_rule_def",
			fieldtype: "Section Break",
			label: __("Rule Definition"),
		},
		{
			fieldname: "fieldname",
			fieldtype: "DocField",
			options: "vars.document_type",
			label: __("Field"),
			reqd: 1,
			columns: 2,
			in_list_view: 1,
			get_options: (cfg, ctx, meta) => SHARED.get_field_options(meta),
		},
		{
			fieldname: "cb_rule_def",
			fieldtype: "Column Break",
		},
		{
			fieldname: "algorithm",
			fieldtype: "Select",
			label: __("Algorithm"),
			options: "Exact\nFuzzy\nPhonetic\nContains\nNumeric Range\nDate Distance",
			reqd: 1,
			default: "Fuzzy",
			columns: 1,
			in_list_view: 1,
			onchange: (val, row, ctx) => SHARED.on_algorithm_change(val, ctx),
		},
		{
			fieldname: "sb_params",
			fieldtype: "Section Break",
			label: __("Parameters"),
		},
		{
			fieldname: "weight",
			fieldtype: "Float",
			label: __("Weight"),
			default: 0.5,
			columns: 1,
			in_list_view: 1,
		},
		{
			fieldname: "cb_params",
			fieldtype: "Column Break",
		},
		{
			fieldname: "threshold",
			fieldtype: "Float",
			label: __("Threshold"),
			default: 0.8,
			columns: 1,
			in_list_view: 1,
			depends_on: "eval:doc.algorithm !== 'Exact'",
			mandatory_depends_on: "eval:doc.algorithm !== 'Exact'",
		},
		{
			fieldname: "tolerance",
			fieldtype: "Int",
			label: __("Tolerance"),
			default: 30,
			columns: 1,
			in_list_view: 1,
			depends_on: "eval:in_list(['Numeric Range', 'Date Distance'], doc.algorithm)",
			mandatory_depends_on: "eval:in_list(['Numeric Range', 'Date Distance'], doc.algorithm)",
			description: __("Allowed deviation (±)"),
		},
		{
			fieldname: "sb_options",
			fieldtype: "Section Break",
			label: __("Options"),
			collapsible: 1,
		},
		{
			fieldname: "normalize",
			fieldtype: "Check",
			label: __("Normalize Values"),
			default: 1,
			columns: 1,
			in_list_view: 1,
		},
		{
			fieldname: "cb_options",
			fieldtype: "Column Break",
		},
		{
			fieldname: "included_in_filters",
			fieldtype: "Check",
			label: __("Blocking Filter"),
			default: 1,
			columns: 1,
			in_list_view: 1,
			description: __("Use this field for blocking checks"),
		},
	];
}
