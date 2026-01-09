/* eslint-disable */
// Copyright (c) {{ year }}, {{ app_publisher }} and contributors
// For license information, please see license.txt

frappe.provide("flexirule.processes");

/**
 * {{ name }} Process Adapter
 *
 * This adapter defines the operations and configuration schema for the {{ name }} process.
 * Each operation should have a corresponding Python function in the controller.py file.
 */
flexirule.processes["{{ name }}"] = {
	setup(context) {
		// context: { process_name, document_type, doc_meta }
	},

	onload(operation_name, context) {
		// context: { process_name, operation_name, document_type, doc_meta, config, update_field }
	},

	/**
	 * Get the configuration schema for an operation
	 * @param {string} operation_name - The func_name of the operation
	 * @returns {Object}
	 */
	get_schema(operation_name, context) {
		const operation = this.get_operation(operation_name);
		if (!operation) return null;

		return {
			title: operation.label || operation_name,
			size: operation.dialog_size || "large",
			fields:
				typeof operation.get_config_fields === "function"
					? operation.get_config_fields(context)
					: [],
		};
	},

	/**
	 * Operations exposed by this process
	 * Each operation must have a func_name matching a Python function in controller.py
	 */
	operations: [
		// {
		// 	func_name: "my_operation",
		// 	label: __("My Operation"),
		// 	description: __("Does something useful"),
		// 	category: "General",
		// 	icon: "tool",
		// 	color: "#3498db",
		// 	get_config_fields: (ctx) => [
		// 		{ fieldname: "field1", fieldtype: "Data", label: __("Field 1"), reqd: 1 },
		// 		{ fieldname: "field2", fieldtype: "Select", label: __("Field 2"), options: "Option1\nOption2" }
		// 	]
		// }
	],

	// Helper methods
	get_operation(name) {
		return this.operations.find((op) => op.func_name === name);
	},

	get_visible_operations() {
		return this.operations.filter((op) => op.visible !== false);
	},
};
