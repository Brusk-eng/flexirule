/**
 * MDM Process Adapter
 * Provides high-quality UI for Master Data Management operations.
 */

flexirule.rule_builder.mdm = {
	/**
	 * Get the process schema metadata
	 */
	get_schema() {
		return {
			name: "MDM",
			label: __("Master Data"),
			description: __("Manage data quality, review tasks, and batch deduplication."),
			icon: "database",
			color: "indigo"
		};
	},

	/**
	 * Get a specific operation by name
	 */
	get_operation(func_name) {
		const operations = {
			create_review_task: {
				label: __("Create Review Task"),
				description: __("Manually flag a record for steward review."),
				icon: "task"
			},
			find_duplicates_and_task: {
				label: __("Find Duplicates & Task"),
				description: __("Auto-detect duplicates and create review tasks."),
				icon: "duplicate"
			},
			batch_normalize: {
				label: __("Batch Normalize"),
				description: __("Normalize all records of a DocType in background."),
				icon: "refresh"
			},
			batch_dedupe: {
				label: __("Batch Dedupe"),
				description: __("Scan all records for duplicates in background."),
				icon: "layers"
			}
		};
		return operations[func_name];
	},

	/**
	 * Get visible operations
	 */
	get_visible_operations() {
		return ["create_review_task", "find_duplicates_and_task", "batch_normalize", "batch_dedupe"];
	},

	/**
	 * Get default configuration
	 */
	get_default_config(operation) {
		const defaults = {
			create_review_task: { task_type: "Data Quality", priority: "Medium", description: "" },
			find_duplicates_and_task: {
				overall_threshold: 0.8,
				max_tasks: 5,
				task_type: "Duplicate Review",
				priority: "Medium",
				fields_config: []
			},
			batch_normalize: { doctype: "", field: "", transformations: [], batch_size: 100 },
			batch_dedupe: { doctype: "", overall_threshold: 0.8, fields_config: [], batch_size: 50 }
		};
		return defaults[operation] || {};
	},

	/**
	 * Get UI fields for configuration
	 */
	get_config_fields(operation, context) {
		const doc_fields = this.get_doc_fields(context);

		if (operation === "create_review_task") {
			return [
				{
					fieldname: "task_type",
					fieldtype: "Select",
					label: __("Task Type"),
					options: "Data Quality\nDuplicate Review\nMerge Request",
					default: "Data Quality",
					reqd: 1
				},
				{
					fieldname: "priority",
					fieldtype: "Select",
					label: __("Priority"),
					options: "Low\nMedium\nHigh\nUrgent",
					default: "Medium"
				},
				{
					fieldname: "description",
					fieldtype: "Small Text",
					label: __("Description"),
					description: __("Supports Jinja templates."),
					reqd: 1
				}
			];
		}

		if (operation === "find_duplicates_and_task") {
			return [
				{
					fieldname: "overall_threshold",
					fieldtype: "Percent",
					label: __("Overall Similarity Threshold"),
					default: 80,
					description: __("Minimum score to flag as duplicate (0-100)."),
					reqd: 1
				},
				{
					fieldname: "max_tasks",
					fieldtype: "Int",
					label: __("Max Tasks to Create"),
					default: 5
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
							columns: 4
						},
						{
							fieldname: "weight",
							fieldtype: "Percent",
							label: __("Weight"),
							default: 100,
							columns: 3
						},
						{
							fieldname: "algorithm",
							fieldtype: "Select",
							label: __("Algorithm"),
							options: "Exact\nFuzzy\nPhonetic\nContains",
							default: "Exact",
							columns: 5
						}
					]
				}
			];
		}

		if (operation === "batch_normalize") {
			return [
				{
					fieldname: "doctype",
					fieldtype: "Link",
					label: __("Target DocType"),
					options: "DocType",
					reqd: 1,
					onchange: (val, ctx) => {
						ctx.update_field("field", { options: this.get_doc_fields({ default_ref_doctype: val }) });
					}
				},
				{
					fieldname: "field",
					fieldtype: "Select",
					label: __("Source Field"),
					options: [],
					reqd: 1
				},
				{
					fieldname: "transformations",
					fieldtype: "MultiSelect",
					label: __("Transformations"),
					options: "lowercase\nuppercase\ntrim\nremove_special_chars",
					default: "trim,lowercase",
					reqd: 1
				},
				{
					fieldname: "batch_size",
					fieldtype: "Int",
					label: __("Batch Size"),
					default: 100
				}
			];
		}

		if (operation === "batch_dedupe") {
			return [
				{
					fieldname: "doctype",
					fieldtype: "Link",
					label: __("Target DocType"),
					options: "DocType",
					reqd: 1
				},
				{
					fieldname: "overall_threshold",
					fieldtype: "Percent",
					label: __("Threshold"),
					default: 80,
					reqd: 1
				},
				{
					fieldname: "batch_size",
					fieldtype: "Int",
					label: __("Batch Size"),
					default: 50
				}
			];
		}

		return [];
	},

	/**
	 * Helper to get fields from context
	 */
	get_doc_fields(context) {
		const doctype = context.default_ref_doctype;
		if (!doctype) return [{ label: __("Select DocType first"), value: "" }];

		const fields = frappe.get_meta(doctype).fields
			.filter(f => !frappe.model.no_value_type.includes(f.fieldtype))
			.map(f => ({
				label: `${__(f.label)} (${f.fieldname})`,
				value: f.fieldname
			}));

		return [{ label: __("Select field..."), value: "" }, ...fields];
	}
};
