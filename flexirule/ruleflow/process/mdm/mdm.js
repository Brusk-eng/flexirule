/**
 * MDM Process Adapter
 * Provides high-quality UI for Master Data Management operations.
 */

frappe.provide("flexirule.processes");

flexirule.processes["MDM"] = {
	meta: {
		version: "1.0",
		title: __("Master Data"),
	},

	get_schema(operation_name, ctx) {
		const operation = this.get_operation(operation_name);
		if (!operation) return [];
		return typeof operation.get_config_fields === "function"
			? operation.get_config_fields(ctx)
			: [];
	},

	operations: [
		{
			func_name: "find_duplicates_and_task",
			label: __("Find Duplicates & Task"),
			description: __("Auto-detect duplicates and create review tasks."),
			icon: "duplicate",
			get_config_fields: (ctx) => {
				const doc_fields = flexirule.processes.MDM.get_doc_fields(ctx);
				return [
					{
						fieldname: "overall_threshold",
						fieldtype: "Percent",
						label: __("Overall Similarity Threshold"),
						default: 80,
						description: __("Minimum score to flag as duplicate (0-100)."),
						reqd: 1,
					},
					{
						fieldname: "max_tasks",
						fieldtype: "Int",
						label: __("Max Tasks to Create"),
						default: 5,
					},
					{
						fieldname: "fields_config",
						fieldtype: "Table",
						label: __("Comparison Fields"),
						reqd: 1,
						fields: [
							{
								fieldname: "fieldname",
								fieldtype: "Select",
								label: __("Field"),
								options: doc_fields,
								reqd: 1,
								columns: 4,
							},
							{
								fieldname: "weight",
								fieldtype: "Percent",
								label: __("Weight"),
								default: 100,
								columns: 3,
							},
							{
								fieldname: "algorithm",
								fieldtype: "Select",
								label: __("Algorithm"),
								options: "Exact\nFuzzy\nPhonetic\nContains",
								default: "Exact",
								columns: 5,
							},
						],
					},
				];
			},
		},
		{
			func_name: "batch_normalize",
			label: __("Batch Normalize"),
			description: __("Normalize all records of a DocType in background."),
			icon: "refresh",
			get_config_fields: (ctx) => [
				{
					fieldname: "doctype",
					fieldtype: "Link",
					label: __("Target DocType"),
					options: "DocType",
					reqd: 1,
					onchange: (val, row, ctx) => {
						ctx.update_field("field", {
							options: flexirule.processes.MDM.get_doc_fields({
								default_ref_doctype: val,
							}),
						});
					},
				},
				{
					fieldname: "field",
					fieldtype: "Select",
					label: __("Source Field"),
					options: [],
					reqd: 1,
				},
				{
					fieldname: "transformations",
					fieldtype: "MultiSelect",
					label: __("Transformations"),
					options: "lowercase\nuppercase\ntrim\nremove_special_chars",
					default: "trim,lowercase",
					reqd: 1,
				},
				{
					fieldname: "batch_size",
					fieldtype: "Int",
					label: __("Batch Size"),
					default: 100,
				},
			],
		},
		{
			func_name: "batch_dedupe",
			label: __("Batch Dedupe"),
			description: __("Scan all records for duplicates in background."),
			icon: "layers",
			get_config_fields: (ctx) => [
				{
					fieldname: "doctype",
					fieldtype: "Link",
					label: __("Target DocType"),
					options: "DocType",
					reqd: 1,
				},
				{
					fieldname: "overall_threshold",
					fieldtype: "Percent",
					label: __("Threshold"),
					default: 80,
					reqd: 1,
				},
				{
					fieldname: "batch_size",
					fieldtype: "Int",
					label: __("Batch Size"),
					default: 50,
				},
			],
		},
	],

	get_operation(name) {
		return this.operations.find((op) => op.func_name === name);
	},

	get_doc_fields(context) {
		const doctype = context.default_ref_doctype;
		if (!doctype) return [{ label: __("Select DocType first"), value: "" }];

		const fields = frappe
			.get_meta(doctype)
			.fields.filter((f) => !frappe.model.no_value_type.includes(f.fieldtype))
			.map((f) => ({
				label: `${__(f.label)} (${f.fieldname})`,
				value: f.fieldname,
			}));

		return [{ label: __("Select field..."), value: "" }, ...fields];
	},
};
