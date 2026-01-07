// Copyright (c) 2025, FlexiRule and contributors
frappe.provide("flexirule.processes");

/**
 * Deduplication Process Adapter
 * Standardizes configuration for deduplication operations.
 */
flexirule.processes.Deduplication = {
    meta: {
        version: '1.0',
        title: __('Deduplication')
    },

    setup(context) {
        // No global setup required
    },

    onload(operation_name, context) {
        const operation = this.get_operation(operation_name);
        if (operation && typeof operation.setup === 'function') {
            operation.setup(context.config, context);
        }
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

    operations: [
        {
            func_name: "find_similar_records",
            label: __("Find Similar Records"),
            description: __("Find similar records using configurable algorithms"),
            category: "Matching",
            icon: "search",
            color: "#f59e0b",
            setup: (cfg, ctx) => {
                if (!cfg.overall_threshold) ctx.update_field('overall_threshold', 0.8);
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
            get_config_fields: () => [
                {
                    fieldtype: "Section Break",
                    label: __("Configuration")
                },
                {
                    fieldname: "overall_threshold",
                    fieldtype: "Float",
                    label: __("Overall Threshold"),
                    default: 0.8,
                    reqd: 1,
                    description: __("Minimum match score required to consider a record similar (0.0 - 1.0)"),
                    columns: 1
                },
                {
                    fieldname: "minimum_fields_matched",
                    fieldtype: "Int",
                    label: __("Min Fields to Match"),
                    default: 1,
                    description: __("Minimum number of fields that must meet their individual thresholds"),
                    columns: 1
                },
                {
                    fieldname: "stop_after_first_match",
                    fieldtype: "Check",
                    label: __("Stop After First Match"),
                    default: 0,
                    description: __("Stop searching once a match is found")
                },
                {
                    fieldtype: "Section Break",
                    label: __("Rules")
                },
                {
                    fieldname: "help_html",
                    fieldtype: "HTML",
                    options: `<div class="text-muted small">
                        Define how each field should be compared. 
                        <b>Fuzzy</b> handles typos. <b>Exact</b> requires precise match. 
                        <b>Numeric/Date</b> allow ranges.
                    </div>`
                },
                {
                    fieldname: "fields_config",
                    fieldtype: "Table",
                    label: __("Field Comparison Rules"),
                    reqd: 1,
                    fields: get_dedupe_table_fields()
                }
            ],
            get_output_schema: (config, context) => {
                // Return schema for "List of Matches"
                // The output is a list of objects, but Frappe Field schema usually describes a single field.
                // For variables, we might return the structure of the *value*.
                // If it's a list of objects, we might want to describe the object structure.

                // Construct dynamic field schema based on configured fields
                const match_fields = [
                    { fieldname: "name", fieldtype: "Data", label: __("Document Name") },
                    { fieldname: "score", fieldtype: "Float", label: __("Match Score") },
                    { fieldname: "doctype", fieldtype: "Link", options: "DocType", label: __("DocType") }
                ];

                if (config.fields_config && Array.isArray(config.fields_config)) {
                    // Add matched fields structure
                    // This is a bit complex for a flat schema, but we can represent 'fields' as a generic Object or dict
                    match_fields.push({
                        fieldname: "fields",
                        fieldtype: "Object",
                        label: __("Matched Fields"),
                        description: __("Dictionary of matched field scores: { field: score }")
                    });
                }

                // We return this as the schema for the variable itself (which is of type Array/List)
                // Or if the variable is just a "List", we describe the Item?
                // For now, let's return the properties of the OBJECT in the list.
                return match_fields;
            }
        },
        {
            func_name: "find_duplicates_by_fields",
            label: __("Find Exact Duplicates"),
            category: "Matching",
            icon: "duplicate",
            color: "#ef4444",
            validate: (cfg) => {
                if (!cfg.fields || cfg.fields.length === 0) return __("Please select at least one field to match.");
            },
            get_config_fields: () => [
                {
                    fieldname: "fields",
                    fieldtype: "MultiDocField",
                    label: __("Fields to Match"),
                    options: "parent.document_type",
                    reqd: 1,
                    description: __("Select fields that must match exactly")
                },
                {
                    fieldname: "ignore_cancelled",
                    fieldtype: "Check",
                    label: __("Ignore Cancelled Documents"),
                    default: 1
                }
            ]
        },
        {
            func_name: "check_duplicate_and_prevent_save",
            label: __("Block If Duplicate Exists"),
            category: "Validation",
            icon: "block",
            color: "#dc2626",
            validate: (cfg) => {
                if (!cfg.fields || cfg.fields.length === 0) return __("Please define unique fields.");
            },
            get_config_fields: () => [
                {
                    fieldname: "fields",
                    fieldtype: "MultiDocField",
                    label: __("Unique Fields"),
                    options: "parent.document_type",
                    reqd: 1,
                    description: __("If a document exists with these exact values, save will be blocked.")
                }
            ]
        },
        {
            func_name: "check_similar_and_prevent_save",
            label: __("Block If Similar Exists"),
            category: "Validation",
            icon: "block",
            color: "#b91c1c",
            setup: (cfg, ctx) => {
                if (!cfg.overall_threshold) ctx.update_field('overall_threshold', 0.8);
            },
            validate: (cfg) => {
                if (!cfg.fields_config || cfg.fields_config.length === 0) return __("Please add comparison rules.");
            },
            get_config_fields: () => [
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
                    reqd: 1,
                    fields: get_dedupe_table_fields()
                }
            ]
        },
        {
            func_name: "mark_as_duplicate",
            label: __("Mark as Duplicate"),
            category: "Actions",
            icon: "link",
            color: "#8b5cf6",
            get_config_fields: () => [
                {
                    fieldname: "master_document",
                    fieldtype: "Data", // Should ideally be a dynamic picker or expression
                    label: __("Master Document ID"),
                    reqd: 1,
                    description: __("Field containing the Master Document Name or ID")
                }
            ]
        },
        {
            func_name: "find_duplicates_in_child_table",
            label: __("Find Duplicates in Child Table"),
            category: "Matching",
            icon: "table",
            color: "#0ea5e9",
            get_config_fields: () => [
                { fieldname: "child_table_field", fieldtype: "Data", label: __("Child Table Field"), reqd: 1 },
                { fieldname: "child_search_field", fieldtype: "Data", label: __("Field to Check"), reqd: 1 }
            ]
        }
    ],

    get_operation(name) {
        return this.operations.find(op => op.func_name === name);
    },

    get_visible_operations() {
        return this.operations.filter(op => op.visible !== false);
    }
};

// ============================================================
// SHARED UTILITIES
// ============================================================

const SHARED = {
    validTypes: ['Data', 'Link', 'Text', 'Phone', 'Email', 'Small Text', 'Date', 'Int', 'Float', 'Currency'],

    get_field_options(doc_meta) {
        if (!doc_meta?.fields) return [];
        return doc_meta.fields
            .filter(f => SHARED.validTypes.includes(f.fieldtype))
            .map(f => ({
                label: `${f.label} (${f.fieldtype})`,
                value: f.fieldname
            }));
    },

    on_algorithm_change(value, context) {
        const defaults = {
            'Exact': { threshold: 1.0, tolerance: 0 },
            'Phonetic': { threshold: 0.9, tolerance: 0 },
            'Fuzzy': { threshold: 0.8, tolerance: 0 },
            'Date Distance': { threshold: 0, tolerance: 30 },
            'Numeric Range': { threshold: 0, tolerance: 30 },
            'Contains': { threshold: 0.8, tolerance: 0 }
        };
        const config = defaults[value] || {};
        if (config.threshold !== undefined) context.update_field('threshold', config.threshold);
        if (config.tolerance !== undefined) context.update_field('tolerance', config.tolerance);
    }
};

/**
 * Returns the schema for the Fields Configuration table
 */
function get_dedupe_table_fields() {
    return [
        {
            fieldname: "fieldname",
            fieldtype: "DocField", // Runtime will map to Autocomplete
            options: "parent.document_type",
            label: __("Field"),
            reqd: 1,
            columns: 2,
            in_list_view: 1,
            get_options: (row, context, meta) => SHARED.get_field_options(meta)
        },
        {
            fieldname: "algorithm",
            fieldtype: "Select",
            label: __("Algorithm"),
            options: "Exact\nFuzzy\nPhonetic\nContains\nNumeric Range\nDate Distance",
            reqd: 1,
            default: "Fuzzy",
            columns: 2,
            in_list_view: 1,
            onchange: (val, row, ctx) => SHARED.on_algorithm_change(val, ctx)
        },
        {
            fieldname: "weight",
            fieldtype: "Float",
            label: __("Weight"),
            default: 0.5,
            columns: 1,
            in_list_view: 1
        },
        {
            fieldname: "threshold",
            fieldtype: "Float",
            label: __("Threshold"),
            default: 0.8,
            columns: 1,
            in_list_view: 1,
            depends_on: "eval:doc.algorithm !== 'Exact'",
            mandatory_depends_on: "eval:doc.algorithm !== 'Exact'" // Example of conditional mandatory
        },
        {
            fieldname: "tolerance",
            fieldtype: "Int",
            label: __("Tolerance"),
            default: 30,
            columns: 1,
            in_list_view: 1,
            depends_on: "eval:['Numeric Range', 'Date Distance'].includes(doc.algorithm)",
            mandatory_depends_on: "eval:['Numeric Range', 'Date Distance'].includes(doc.algorithm)"
        },
        {
            fieldname: "normalize",
            fieldtype: "Check",
            label: __("Normalize"),
            default: 1,
            columns: 1,
            in_list_view: 1
        },
        {
            fieldname: "included_in_filters",
            fieldtype: "Check",
            label: __("Blocking"),
            default: 1,
            columns: 1,
            in_list_view: 1,
            description: __("Use this field for blocking checks")
        }
    ];
}
