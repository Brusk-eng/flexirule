// Copyright (c) 2025, FlexiRule and contributors
// For license information, please see license.txt

/**
 * Deduplication Process - Rule Builder Adapter
 * Demonstrates field hooks: get_options, onchange, depends_on_fields
 */

flexirule.processes = flexirule.processes || {};

// Child table definitions with hooks
flexirule.processes._child_tables = flexirule.processes._child_tables || {};

flexirule.processes._child_tables["Dedupe Field Config"] = [
    {
        fieldname: "fieldname",
        fieldtype: "Select",
        label: __("Field"),
        reqd: 1,
        in_list_view: 1,
        width: "150px",
        // Dynamic options from document type fields
        get_options: function (row_values, parent_values, doc_meta) {
            if (!doc_meta || !doc_meta.fields) {
                return [];
            }
            // Return fields that are suitable for comparison
            const validTypes = ['Data', 'Text', 'Phone', 'Email', 'Small Text', 'Date', 'Int', 'Float', 'Currency'];
            return doc_meta.fields
                .filter(f => validTypes.includes(f.fieldtype))
                .map(f => ({
                    label: f.label || f.fieldname,
                    value: f.fieldname
                }));
        }
    },
    {
        fieldname: "algorithm",
        fieldtype: "Select",
        label: __("Algorithm"),
        options: "Exact\nFuzzy\nPhonetic\nContains\nNumeric Range\nDate Distance",
        reqd: 1,
        default: "Fuzzy",
        in_list_view: 1,
        width: "120px",
        // When algorithm changes, update related fields
        onchange: function (value, row_values, context) {
            // Set sensible defaults based on algorithm
            if (value === 'Exact') {
                context.update_field('threshold', 1.0);
            } else if (value === 'Phonetic') {
                context.update_field('threshold', 0.9);
            } else if (value === 'Fuzzy') {
                context.update_field('threshold', 0.8);
            } else if (value === 'Date Distance' || value === 'Numeric Range') {
                context.update_field('threshold', 0);
                context.update_field('tolerance', 30);
            }
        }
    },
    {
        fieldname: "weight",
        fieldtype: "Float",
        label: __("Weight"),
        default: 0.5,
        in_list_view: 1,
        width: "80px"
    },
    {
        fieldname: "threshold",
        fieldtype: "Float",
        label: __("Threshold"),
        default: 0.8,
        in_list_view: 1,
        width: "80px",
        // Depends on algorithm
        depends_on_fields: ["algorithm"]
    },
    {
        fieldname: "tolerance",
        fieldtype: "Int",
        label: __("Tolerance"),
        default: 30,
        width: "80px",
        // Only show tolerance description if Date/Numeric
        depends_on_fields: ["algorithm"]
    },
    {
        fieldname: "normalize",
        fieldtype: "Check",
        label: __("Normalize"),
        default: 1,
        width: "60px"
    },
    {
        fieldname: "included_in_filters",
        fieldtype: "Check",
        label: __("Blocking"),
        default: 1,
        width: "60px"
    }
];

flexirule.processes["Deduplication"] = {
    operations: [
        {
            func_name: "find_similar_records",
            label: __("Find Similar Records"),
            description: __("Find similar records using configurable algorithms"),
            category: "Matching",
            icon: "search",
            color: "#f59e0b",

            // Called when operation is first selected
            setup: function (config, context) {
                // Set defaults if empty
                if (!config.overall_threshold) {
                    context.update_field('overall_threshold', 0.8);
                }
            },

            get_config_fields: function (frm) {
                return [
                    {
                        fieldname: "overall_threshold",
                        fieldtype: "Float",
                        label: __("Overall Threshold"),
                        default: 0.8,
                        reqd: 1
                    },
                    {
                        fieldname: "minimum_fields_matched",
                        fieldtype: "Int",
                        label: __("Min Fields to Match"),
                        default: 1
                    },
                    {
                        fieldname: "stop_after_first_match",
                        fieldtype: "Check",
                        label: __("Stop After First Match"),
                        default: 0
                    },
                    {
                        fieldname: "fields_config",
                        fieldtype: "Table",
                        label: __("Field Comparison Rules"),
                        options: "Dedupe Field Config",
                        reqd: 1,
                        table_fields: flexirule.processes._child_tables["Dedupe Field Config"]
                    }
                ];
            }
        },
        {
            func_name: "find_duplicates_by_fields",
            label: __("Find Exact Duplicates"),
            description: __("Find exact duplicate records based on field values"),
            category: "Matching",
            icon: "duplicate",
            color: "#ef4444",

            get_config_fields: function (frm) {
                return [
                    {
                        fieldname: "fields",
                        fieldtype: "Small Text",
                        label: __("Fields to Match"),
                        reqd: 1
                    },
                    {
                        fieldname: "ignore_cancelled",
                        fieldtype: "Check",
                        label: __("Ignore Cancelled"),
                        default: 1
                    }
                ];
            }
        },
        {
            func_name: "check_duplicate_and_prevent_save",
            label: __("Block If Duplicate Exists"),
            description: __("Block save if exact duplicate exists"),
            category: "Validation",
            icon: "block",
            color: "#dc2626",

            get_config_fields: function (frm) {
                return [
                    {
                        fieldname: "fields",
                        fieldtype: "Small Text",
                        label: __("Unique Fields"),
                        reqd: 1
                    }
                ];
            }
        },
        {
            func_name: "check_similar_and_prevent_save",
            label: __("Block If Similar Exists"),
            description: __("Block save if similar records exist"),
            category: "Validation",
            icon: "block",
            color: "#b91c1c",

            get_config_fields: function (frm) {
                return [
                    {
                        fieldname: "overall_threshold",
                        fieldtype: "Float",
                        label: __("Overall Threshold"),
                        default: 0.8,
                        reqd: 1
                    },
                    {
                        fieldname: "fields_config",
                        fieldtype: "Table",
                        label: __("Field Comparison Rules"),
                        options: "Dedupe Field Config",
                        reqd: 1,
                        table_fields: flexirule.processes._child_tables["Dedupe Field Config"]
                    }
                ];
            }
        },
        {
            func_name: "mark_as_duplicate",
            label: __("Mark as Duplicate"),
            description: __("Mark document as duplicate of another"),
            category: "Actions",
            icon: "link",
            color: "#8b5cf6",

            get_config_fields: function (frm) {
                return [
                    {
                        fieldname: "master_document",
                        fieldtype: "Data",
                        label: __("Master Document"),
                        reqd: 1
                    }
                ];
            }
        },
        {
            func_name: "find_duplicates_in_child_table",
            label: __("Find Duplicates in Child Table"),
            description: __("Find duplicates based on values in a child table"),
            category: "Matching",
            icon: "table",
            color: "#0ea5e9",

            get_config_fields: function (frm) {
                return [
                    {
                        fieldname: "child_table_field",
                        fieldtype: "Data",
                        label: __("Child Table Field"),
                        reqd: 1
                    },
                    {
                        fieldname: "child_search_field",
                        fieldtype: "Data",
                        label: __("Field to Check"),
                        reqd: 1
                    }
                ];
            }
        }
    ],

    get_operation: function (func_name) {
        return this.operations.find(op => op.func_name === func_name);
    },

    get_visible_operations: function () {
        return this.operations.filter(op => op.visible !== false);
    },

    get_child_table_def: function (table_name) {
        return flexirule.processes._child_tables[table_name] || [];
    }
};
