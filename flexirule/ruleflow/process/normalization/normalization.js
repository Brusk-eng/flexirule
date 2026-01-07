/**
 * Normalization Process Adapter
 */

// Define Profiles (Syncd with Python)
const PROFILES = {
    "default": [
        "trim", "unicode_normalize", "casefold", "translate_chars", "remove_extra_spaces"
    ],
    "arabic_strict": [
        "trim", "unicode_normalize", "casefold", "translate_chars", "remove_punctuation", "remove_extra_spaces"
    ],
    "email": [
        "trim", "lowercase", "email_normalize"
    ],
    "phone": [
        "numeric_only"
    ],
    "slug": [
        "trim", "lowercase", "remove_punctuation", "remove_extra_spaces", "slug"
    ]
};

// Start Namespace
frappe.provide('flexirule.processes');

flexirule.processes["Normalization"] = {

    meta: {
        version: '1.0',
        title: __('Normalization')
    },

    get_schema(operation_name, context) {
        const operation = this.get_operation(operation_name);
        if (!operation) return null;

        return {
            title: operation.label || operation_name,
            size: 'large',
            fields: typeof operation.get_config_fields === 'function'
                ? operation.get_config_fields(context)
                : []
        };
    },

    get_output_schema(operation_name, config, context) {
        const operation = this.get_operation(operation_name);
        if (operation && typeof operation.get_output_schema === 'function') {
            return operation.get_output_schema(config, context);
        }
        return [];
    },

    get_operation(name) {
        return this.operations.find(op => op.func_name === name);
    },

    get_visible_operations() {
        return this.operations.filter(op => op.visible !== false);
    },

    // Operations Definition
    operations: [
        {
            func_name: "normalize_field",
            label: __("Normalize Field"),
            description: __("Normalize a field in-place or to a target field"),
            icon: "edit",
            color: "#3b82f6",
            get_config_fields: (ctx) => {
                const transformation_field = get_transformation_field_table();
                const profile_field = get_profile_field(true); // Table target

                return [
                    {
                        fieldname: "source_field",
                        label: __("Source Field"),
                        fieldtype: "DocField",
                        options: ctx.document_type || "DocField",
                        reqd: 1
                    },
                    profile_field,
                    {
                        ...transformation_field,
                        read_only_depends_on: "eval:doc.profile && doc.profile !== ''"
                    },
                    {
                        fieldname: "target_field",
                        label: __("Target Field (Optional)"),
                        fieldtype: "DocField",
                        options: ctx.document_type || "DocField",
                        description: __("If empty, normalizes in-place.")
                    }
                ];
            }
        },
        {
            func_name: "normalize_field_to_context",
            label: __("Normalize to Variable"),
            description: __("Normalize a field and store it in context (vars)"),
            icon: "variable",
            color: "#10b981",
            get_config_fields: (ctx) => {
                const transformation_field = get_transformation_field_table();
                const profile_field = get_profile_field(true); // Table target

                return [
                    {
                        fieldname: "source_field",
                        label: __("Source Field"),
                        fieldtype: "DocField",
                        options: ctx.document_type,
                        reqd: 1
                    },
                    profile_field,
                    {
                        ...transformation_field,
                        read_only_depends_on: "eval:doc.profile && doc.profile !== ''"
                    },
                    {
                        fieldname: "context_key",
                        label: __("Variable Name"),
                        fieldtype: "Data",
                        description: __("Key to store in 'vars'. Defaults to normalized_{source_field}")
                    }
                ];
            },
            get_output_schema: (config, ctx) => {
                const key = config.context_key || (config.source_field ? `normalized_${config.source_field}` : "normalized_value");
                return [
                    {
                        label: key,
                        value: key,
                        type: "Data"
                    }
                ];
            }
        },
        {
            func_name: "normalize_multiple_fields",
            label: __("Batch Normalize"),
            description: __("Batch normalize multiple fields"),
            icon: "list",
            color: "#8b5cf6",
            get_config_fields: (ctx) => {
                const transformation_field = get_transformation_field_multiselect();
                const profile_field = get_profile_field(false); // MultiSelect target

                return [
                    {
                        fieldname: "store_in_context",
                        label: __("Store in Context (Variables)"),
                        fieldtype: "Check",
                        default: 0
                    },
                    {
                        fieldname: "field_config",
                        label: __("Field Configuration"),
                        fieldtype: "Table",
                        reqd: 1,
                        fields: [
                            {
                                fieldname: "fieldname",
                                label: __("Field"),
                                fieldtype: "DocField",
                                options: ctx.document_type,
                                reqd: 1,
                                in_list_view: 1,
                                columns: 3
                            },
                            {
                                ...profile_field,
                                label: __("Profile"),
                                in_list_view: 1,
                                columns: 2
                            },
                            {
                                ...transformation_field,
                                in_list_view: 1,
                                columns: 4,
                                read_only_depends_on: "eval:doc.profile && doc.profile !== ''"
                            },
                            {
                                fieldname: "target_field",
                                label: __("Target Field / Variable"),
                                fieldtype: "Data",
                                in_list_view: 1,
                                columns: 2
                            }
                        ]
                    }
                ];
            },
            get_output_schema: (config, ctx) => {
                if (config.store_in_context) {
                    const fields = config.field_config || [];
                    return fields.map(f => {
                        const key = f.target_field || (f.fieldname ? `normalized_${f.fieldname}` : "var");
                        return { label: key, value: key, type: "Data" };
                    });
                }
                return null;
            }
        }
    ]
};

// Helpers
function get_transformation_field_table() {
    return {
        fieldname: "transformations",
        label: __("Transformations"),
        fieldtype: "Table",
        reqd: 1,
        fields: [
            {
                fieldname: "transformation",
                label: __("Transformation"),
                fieldtype: "Select",
                options: get_transformation_options(),
                in_list_view: 1,
                columns: 10,
                reqd: 1
            }
        ]
    };
}

function get_transformation_field_multiselect() {
    return {
        fieldname: "transformations",
        label: __("Transformations"),
        fieldtype: "MultiSelect",
        options: get_transformation_options(),
        default: "", // Critical: Prevent undefined which crashes MultiSelect.get_value
        reqd: 1
    };
}

function get_transformation_options() {
    return [
        { label: "Trim", value: "trim" },
        { label: "Lowercase", value: "lowercase" },
        { label: "Uppercase", value: "uppercase" },
        { label: "Casefold", value: "casefold" },
        { label: "Unicode Normalize", value: "unicode_normalize" },
        { label: "Translate Chars (Common)", value: "translate_chars" },
        { label: "Remove Spaces", value: "remove_spaces" },
        { label: "Remove Extra Spaces", value: "remove_extra_spaces" },
        { label: "Remove Punctuation", value: "remove_punctuation" },
        { label: "Remove Numbers", value: "remove_numbers" },
        { label: "Digits Only", value: "numeric_only" },
        { label: "Alphanumeric Only", value: "alphanumeric_only" },
        { label: "Slugify", value: "slug" },
        { label: "Title Case", value: "title_case" },
        { label: "Email Normalize", value: "email_normalize" }
    ];
}

function get_profile_field(is_table_target = true) {
    return {
        fieldname: "profile",
        label: __("Profile"),
        fieldtype: "Select",
        options: [
            { label: "Custom", value: "" },
            { label: "Default", value: "default" },
            { label: "Arabic Strict", value: "arabic_strict" },
            { label: "Email", value: "email" },
            { label: "Phone", value: "phone" },
            { label: "Slug", value: "slug" }
        ],
        onchange: (val, row, ctx) => {
            if (val) {
                const transforms = PROFILES[val] || [];
                if (is_table_target) {
                    // Map to Table Rows
                    // [{ transformation: 'trim' }, ...]
                    const table_rows = transforms.map(t => ({ transformation: t }));
                    ctx.update_field("transformations", table_rows);
                } else {
                    // Map to Comma Separated String for MultiSelect (Tags)
                    // "trim, lowercase"
                    ctx.update_field("transformations", transforms.join(', '));
                }
            }
        }
    };
}

