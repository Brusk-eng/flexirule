// Copyright (c) 2025, FlexiRule and contributors
// For license information, please see license.txt

/**
 * MDM Process - Rule Builder Adapter
 *
 * This file provides the frontend contract for the Rule Builder Vue app.
 * Following the Frappe Script Report pattern (frappe.query_reports[name]).
 */

flexirule.processes = flexirule.processes || {};

flexirule.processes["MDM"] = {
	// Operation definitions for Rule Builder
	operations: [
		{
			func_name: "create_review_task",
			label: __("Create Review Task"),
			description: __("Create a Data Review Task for steward review"),
			category: "MDM",
			icon: "task",
			color: "#6366f1",

			/**
			 * Get config fields for this operation.
			 * Uses native Frappe field format for form rendering.
			 * @param {Object} frm - Frappe form object (for dynamic options)
			 * @returns {Array} Frappe field definitions
			 */
			get_config_fields: function (frm) {
				return [
					{
						fieldname: "task_type",
						fieldtype: "Select",
						label: __("Task Type"),
						options: "Duplicate Review\nData Quality\nMerge Request",
						reqd: 1,
						default: "Duplicate Review",
					},
					{
						fieldname: "priority",
						fieldtype: "Select",
						label: __("Priority"),
						options: "Low\nMedium\nHigh\nUrgent",
						default: "Medium",
					},
					{
						fieldname: "description",
						fieldtype: "Small Text",
						label: __("Description"),
					},
				];
			},
		},
		{
			func_name: "find_duplicates",
			label: __("Find Duplicates"),
			description: __("Find potential duplicate records based on similarity"),
			category: "Deduplication",
			icon: "duplicate",
			color: "#f59e0b",

			get_config_fields: function (frm) {
				return [
					{
						fieldname: "threshold",
						fieldtype: "Float",
						label: __("Similarity Threshold"),
						default: 0.8,
						reqd: 1,
						description: __("Minimum similarity score (0.0 - 1.0)"),
					},
					{
						fieldname: "fields_to_compare",
						fieldtype: "Small Text",
						label: __("Fields to Compare"),
						description: __("Comma-separated list of field names"),
					},
					{
						fieldname: "max_results",
						fieldtype: "Int",
						label: __("Max Results"),
						default: 10,
					},
				];
			},
		},
		{
			func_name: "normalize_field",
			label: __("Normalize Field"),
			description: __("Apply normalization transformations to a field value"),
			category: "Normalization",
			icon: "format",
			color: "#10b981",

			get_config_fields: function (frm) {
				return [
					{
						fieldname: "field",
						fieldtype: "Data",
						label: __("Field Name"),
						reqd: 1,
					},
					{
						fieldname: "transformations",
						fieldtype: "Small Text",
						label: __("Transformations"),
						description: __(
							"Comma-separated: lowercase, uppercase, trim, remove_special_chars"
						),
						default: "trim,lowercase",
					},
				];
			},
		},
	],

	/**
	 * Get operation by function name.
	 * @param {string} func_name - Function name to find
	 * @returns {Object|undefined} Operation definition
	 */
	get_operation: function (func_name) {
		return this.operations.find((op) => op.func_name === func_name);
	},

	/**
	 * Get all visible operations for the Rule Builder palette.
	 * @returns {Array} Filtered operations
	 */
	get_visible_operations: function () {
		return this.operations.filter((op) => op.visible !== false);
	},

	/**
	 * Get operations by category.
	 * @param {string} category - Category name
	 * @returns {Array} Operations in category
	 */
	get_operations_by_category: function (category) {
		return this.operations.filter((op) => op.category === category);
	},
};
