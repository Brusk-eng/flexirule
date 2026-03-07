/**
 * Validation Process Adapter
 */

// Start Namespace
frappe.provide("flexirule.processes");

flexirule.processes["Validation"] = {
	meta: {
		version: "1.0",
		title: __("Validation"),
	},

	get_schema(operation_name, context) {
		const operation = this.get_operation(operation_name);
		if (!operation) return null;

		return {
			title: operation.label || operation_name,
			size: "large",
			fields:
				typeof operation.get_config_fields === "function"
					? operation.get_config_fields(context)
					: [],
		};
	},

	get_output_schema(operation_name, config, context) {
		const operation = this.get_operation(operation_name);
		if (operation && typeof operation.get_output_schema === "function") {
			return operation.get_output_schema(config, context);
		}
		return [];
	},

	get_operation(name) {
		return this.operations.find((op) => op.func_name === name);
	},

	get_visible_operations() {
		return this.operations.filter((op) => op.visible !== false);
	},

	get_default_config(operation_name) {
		const operation = this.get_operation(operation_name);
		if (!operation || typeof operation.get_config_fields !== "function") {
			return {};
		}

		const defaults = {};
		const raw_fields = operation.get_config_fields({});

		raw_fields.forEach((field) => {
			if (["Section Break", "Column Break", "HTML"].includes(field.fieldtype)) {
				return;
			}
			if (field.fieldtype === "Table") {
				defaults[field.fieldname] = [];
				return;
			}
			if (field.default !== undefined) {
				defaults[field.fieldname] = field.default;
			}
		});

		return defaults;
	},

	// Operations Definition
	operations: [
		{
			func_name: "required_fields",
			label: __("Required Fields"),
			description: __("Validate that specified fields have values"),
			icon: "check-circle",
			color: "#ef4444",
			get_config_fields: (ctx) => [
				{
					fieldname: "fields",
					label: __("Mandatory Fields"),
					fieldtype: "MultiDocField",
					options: "vars.document_type",
					reqd: 1,
					description: __("Select one or more fields that must not be empty"),
				},
			],
		},
		{
			func_name: "field_pattern",
			label: __("Field Pattern"),
			description: __("Validate field matches a preset or custom pattern"),
			icon: "filter",
			color: "#f59e0b",
			get_config_fields: (ctx) => [
				{
					fieldname: "field",
					label: __("Field to Validate"),
					fieldtype: "DocField",
					options: "vars.document_type",
					reqd: 1,
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "pattern_type",
					label: __("Pattern Type"),
					fieldtype: "Select",
					options: [
						"Email",
						"Phone",
						"URL",
						"Alphanumeric",
						"Numeric",
						"Custom Regex",
					].join("\n"),
					default: "Email",
					reqd: 1,
				},
				{
					fieldname: "pattern",
					label: __("Custom Regex"),
					fieldtype: "Data",
					depends_on: "eval:doc.pattern_type === 'Custom Regex'",
					reqd: 1,
				},
				{
					fieldtype: "Section Break",
				},
				{
					fieldname: "error_message",
					label: __("Custom Error Message"),
					fieldtype: "Data",
					description: __("Optional. If empty, a default message will be used."),
				},
			],
		},
		{
			func_name: "value_in_range",
			label: __("Value in Range"),
			description: __("Ensure a numeric value is within bounds"),
			icon: "hash",
			color: "#10b981",
			get_config_fields: (ctx) => [
				{
					fieldname: "field",
					label: __("Numeric Field"),
					fieldtype: "DocField",
					options: "vars.document_type",
					reqd: 1,
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "min_value",
					label: __("Minimum"),
					fieldtype: "Float",
				},
				{
					fieldname: "max_value",
					label: __("Maximum"),
					fieldtype: "Float",
				},
			],
		},
		{
			func_name: "unique_field",
			label: __("Unique Field"),
			description: __("Validate field value is unique across all records"),
			icon: "database",
			color: "#6366f1",
			get_config_fields: (ctx) => [
				{
					fieldname: "field",
					label: __("Field for Uniqueness"),
					fieldtype: "DocField",
					options: "vars.document_type",
					reqd: 1,
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "ignore_cancelled",
					label: __("Ignore Cancelled"),
					fieldtype: "Check",
					default: 1,
				},
			],
		},
		{
			func_name: "conditional_required",
			label: __("Conditional Required"),
			description: __("Make fields mandatory based on another field's value"),
			icon: "help-circle",
			color: "#ec4899",
			get_config_fields: (ctx) => [
				{
					fieldname: "condition_field",
					label: __("When Field"),
					fieldtype: "DocField",
					options: "vars.document_type",
					reqd: 1,
				},
				{
					fieldname: "condition_value",
					label: __("Equals Value"),
					fieldtype: "Data",
					reqd: 1,
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "required_fields",
					label: __("Then Required"),
					fieldtype: "MultiDocField",
					options: "vars.document_type",
					reqd: 1,
				},
			],
		},
		{
			func_name: "child_table_rows",
			label: __("Child Table Rows"),
			description: __("Validate each row in a child table"),
			icon: "list",
			color: "#8b5cf6",
			get_config_fields: (ctx) => [
				{
					fieldname: "child_table",
					label: __("Child Table Field"),
					fieldtype: "DocField",
					options: "vars.document_type",
					reqd: 1,
				},
				{
					fieldtype: "Section Break",
					label: __("Validation Rules"),
				},
				{
					fieldname: "validations",
					label: __("Rules"),
					fieldtype: "Table",
					fields: [
						{
							fieldname: "type",
							label: __("Type"),
							fieldtype: "Select",
							options: [
								"field_required",
								"fields_not_equal",
								"fields_equal",
								"field_greater_than",
							].join("\n"),
							in_list_view: 1,
							columns: 3,
						},
						{
							fieldname: "field1",
							label: __("Field 1"),
							fieldtype: "Data",
							in_list_view: 1,
							columns: 2,
						},
						{
							fieldname: "field2",
							label: __("Field 2"),
							fieldtype: "Data",
							in_list_view: 1,
							columns: 2,
						},
						{
							fieldname: "value",
							label: __("Threshold"),
							fieldtype: "Data",
							in_list_view: 1,
							columns: 2,
						},
						{
							fieldname: "error_message",
							label: __("Message"),
							fieldtype: "Data",
							in_list_view: 1,
							columns: 3,
						},
					],
				},
			],
		},
		{
			func_name: "composite_uniqueness",
			label: __("Composite Uniqueness"),
			description: __("Unique check across parent and child fields"),
			icon: "activity",
			color: "#0ea5e9",
			get_config_fields: (ctx) => [
				{
					fieldname: "parent_fields",
					label: __("Parent Fields"),
					fieldtype: "MultiDocField",
					options: "vars.document_type",
					reqd: 1,
				},
				{
					fieldname: "child_table",
					label: __("Child Table"),
					fieldtype: "DocField",
					options: "vars.document_type",
					reqd: 1,
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "child_fields",
					label: __("Child Fields"),
					fieldtype: "MultiDocField",
					options: "child_table", // Dynamic options based on child_table field
					reqd: 1,
				},
				{
					fieldname: "match_mode",
					label: __("Match Mode"),
					fieldtype: "Select",
					options: "any\nall",
					default: "any",
				},
			],
		},
		{
			func_name: "role_check",
			label: __("Role Check"),
			description: __("Check current user permissions/roles"),
			icon: "users",
			color: "#64748b",
			get_config_fields: (ctx) => [
				{
					fieldname: "roles",
					label: __("Roles"),
					fieldtype: "MultiSelect",
					options: "Role",
					reqd: 1,
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "mode",
					label: __("Rule"),
					fieldtype: "Select",
					options: ["has_any", "has_all", "not_has_any"].join("\n"),
					default: "has_any",
				},
				{
					fieldname: "store_result",
					label: __("Store Result in Variable"),
					fieldtype: "Data",
					description: __("Optional variable name for the boolean result"),
				},
			],
			get_output_schema: (config, ctx) => {
				if (config.store_result) {
					return [
						{
							label: config.store_result,
							value: config.store_result,
							type: "Data",
						},
					];
				}
				return null;
			},
		},
		{
			func_name: "on_field_change",
			label: __("On Field Change"),
			description: __("Detect if specific fields were modified"),
			icon: "refresh-cw",
			color: "#14b8a6",
			get_config_fields: (ctx) => [
				{
					fieldname: "watched_fields",
					label: __("Watch Fields"),
					fieldtype: "MultiDocField",
					options: "vars.document_type",
					reqd: 1,
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "match_mode",
					label: __("Match Mode"),
					fieldtype: "Select",
					options: "Any\nAll",
					default: "Any",
				},
				{
					fieldname: "store_result",
					label: __("Store Changed Fields List In"),
					fieldtype: "Data",
				},
			],
			get_output_schema: (config, ctx) => {
				if (config.store_result) {
					return [
						{
							label: config.store_result,
							value: config.store_result,
							type: "JSON", // Changed to JSON since it stores a list of fields
						},
					];
				}
				return null;
			},
		},
	],
};
