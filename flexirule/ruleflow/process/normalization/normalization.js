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

    /**
     * Get default configuration for a specific operation
     */
    get_default_config(operation_name) {
        const operation = this.get_operation(operation_name);
        if (!operation || typeof operation.get_config_fields !== 'function') {
            return {};
        }

        const defaults = {};
        const raw_fields = operation.get_config_fields({});

        raw_fields.forEach(field => {
            // Skip layout fields
            if (['Section Break', 'Column Break', 'HTML'].includes(field.fieldtype)) {
                return;
            }

            // Handle Table fields
            if (field.fieldtype === 'Table') {
                defaults[field.fieldname] = [];
                return;
            }

            // Regular field
            if (field.default !== undefined) {
                defaults[field.fieldname] = field.default;
            }
        });

        return defaults;
    },

    /**
     * Validate configuration
     */
    validate(operation_name, config, context = {}) {
        const operation = this.get_operation(operation_name);
        if (!operation || typeof operation.validate !== 'function') {
            return [];
        }

        const msg = operation.validate(config, context);
        if (msg) {
            return [{ fieldname: '_general', message: msg }];
        }

        return [];
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
                        options: "vars.document_type",
                        reqd: 1
                    },
                    { fieldtype: "Column Break" },
                    {
                        fieldname: "target_field",
                        label: __("Target Field (Optional)"),
                        fieldtype: "DocField",
                        options: "vars.document_type",
                        description: __("If empty, normalizes in-place.")
                    },
                    {
                        fieldtype: "Section Break",
                        label: __("Transformation Rules")
                    },
                    profile_field,
                    {
                        ...transformation_field,
                        read_only_depends_on: "eval:doc.profile && doc.profile !== ''"
                    },
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
                        options: "vars.document_type",
                        reqd: 1
                    },
                    { fieldtype: "Column Break" },
                    {
                        fieldname: "context_key",
                        label: __("Variable Name"),
                        fieldtype: "Data",
                        description: __("Key to store in 'vars'. Defaults to normalized_{source_field}")
                    },
                    {
                        fieldtype: "Section Break",
                        label: __("Transformation Rules")
                    },
                    profile_field,
                    {
                        ...transformation_field,
                        read_only_depends_on: "eval:doc.profile && doc.profile !== ''"
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
                        fieldtype: "Section Break",
                        label: __("Field Selection")
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
                                options: "vars.document_type",
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
        fieldtype: "MultiCheck",
        columns: 3,
        options: get_transformation_options(),
        reqd: 1
    };
}

function get_transformation_field_multiselect() {
    return {
        fieldname: "transformations",
        label: __("Transformations"),
        fieldtype: "MultiCheck",
        columns: 2,
        options: get_transformation_options(),
        reqd: 1
    };
}

function get_transformation_options() {
    return [
        { label: __("Trim"), value: "trim", description: __("Remove leading and trailing whitespace") },
        { label: __("Lowercase"), value: "lowercase", description: __("Convert all characters to lowercase") },
        { label: __("Uppercase"), value: "uppercase", description: __("Convert all characters to uppercase") },
        { label: __("Casefold"), value: "casefold", description: __("Aggressive lowercase for caseless matching (supports special Unicode characters)") },
        { label: __("Unicode Normalize"), value: "unicode_normalize", description: __("Normalize Unicode characters to NFKD form for consistent representation") },
        { label: __("Translate Chars"), value: "translate_chars", description: __("Translate Arabic/Special characters to their standard base forms") },
        { label: __("Remove Spaces"), value: "remove_spaces", description: __("Remove all spaces from the text") },
        { label: __("Remove Extra Spaces"), value: "remove_extra_spaces", description: __("Replace multiple consecutive spaces with a single space") },
        { label: __("Remove Punctuation"), value: "remove_punctuation", description: __("Remove all punctuation and special characters") },
        { label: __("Remove Numbers"), value: "remove_numbers", description: __("Remove all numeric characters") },
        { label: __("Numeric Only"), value: "numeric_only", description: __("Keep only numeric characters") },
        { label: __("Alphanumeric Only"), value: "alphanumeric_only", description: __("Keep only letters and numbers (removes symbols and spaces)") },
        { label: __("Slug"), value: "slug", description: __("Convert text to a URL-friendly slug (lowercase, alphanumeric, and hyphens)") },
        { label: __("Title Case"), value: "title_case", description: __("Capitalize the first letter of each word") },
        { label: __("Email Normalize"), value: "email_normalize", description: __("Standardize email format (lowercase, remove dots/plus in Gmail addresses)") }
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
                // Use spread to copy array and prevent mutation of the PROFILES constant
                const transforms = [...(PROFILES[val] || [])];
                ctx.update_field("transformations", transforms);
            }
        }
    };
}