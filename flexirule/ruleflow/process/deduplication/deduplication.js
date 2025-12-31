// Copyright (c) 2025, FlexiRule and contributors
frappe.provide("flexirule.processes");

/** * Reusable Components & Logic 
 */
const SHARED_LOGIC = {
    validTypes: ['Data', 'Text', 'Phone', 'Email', 'Small Text', 'Date', 'Int', 'Float', 'Currency'],

    getFieldOptions: (doc_meta) => {
        if (!doc_meta?.fields) return [];
        return doc_meta.fields
            .filter(f => SHARED_LOGIC.validTypes.includes(f.fieldtype))
            .map(f => ({ label: f.label || f.fieldname, value: f.fieldname }));
    },

    onAlgorithmChange: (value, context) => {
        const defaults = {
            'Exact': { threshold: 1.0, tolerance: 0 },
            'Phonetic': { threshold: 0.9, tolerance: 0 },
            'Fuzzy': { threshold: 0.8, tolerance: 0 },
            'Date Distance': { threshold: 0, tolerance: 30 },
            'Numeric Range': { threshold: 0, tolerance: 30 }
        };
        const config = defaults[value] || {};
        if (config.threshold !== undefined) context.update_field('threshold', config.threshold);
        if (config.tolerance !== undefined) context.update_field('tolerance', config.tolerance);
    }
};

/** * Returns the inline field schema for Deduplication tables 
 */
const getDedupeTableFields = () => [
    {
        fieldname: "fieldname",
        fieldtype: "Data",
        options: "Field Picker",
        label: __("Field"),
        reqd: 1,
        in_list_view: 1,
        width: "150px",
        get_options: (row, parent, meta) => SHARED_LOGIC.getFieldOptions(meta)
    },
    {
        fieldname: "algorithm",
        fieldtype: "Select",
        label: __("Algorithm"),
        options: "Exact\nFuzzy\nPhonetic\nContains\nNumeric Range\nDate Distance",
        reqd: 1,
        default: "Fuzzy",
        in_list_view: 1,
        onchange: (val, row, ctx) => SHARED_LOGIC.onAlgorithmChange(val, ctx)
    },
    { fieldname: "weight", fieldtype: "Float", label: __("Weight"), default: 0.5, in_list_view: 1, width: "80px" },
    { fieldname: "threshold", fieldtype: "Float", label: __("Threshold"), default: 0.8, in_list_view: 1, depends_on_fields: ["algorithm"] },
    { fieldname: "tolerance", fieldtype: "Int", label: __("Tolerance"), default: 30, depends_on_fields: ["algorithm"] },
    { fieldname: "normalize", fieldtype: "Check", label: __("Normalize"), default: 1 },
    { fieldname: "included_in_filters", fieldtype: "Check", label: __("Blocking"), default: 1 }
];

/**
 * Deduplication Process Definition
 */
flexirule.processes["Deduplication"] = {
    operations: [
        {
            func_name: "find_similar_records",
            label: __("Find Similar Records"),
            description: __("Find similar records using configurable algorithms"),
            category: "Matching",
            icon: "search",
            color: "#f59e0b",
            setup: (cfg, ctx) => !cfg.overall_threshold && ctx.update_field('overall_threshold', 0.8),
            get_config_fields: () => [
                { fieldname: "overall_threshold", fieldtype: "Float", label: __("Overall Threshold"), default: 0.8, reqd: 1 },
                { fieldname: "minimum_fields_matched", fieldtype: "Int", label: __("Min Fields to Match"), default: 1 },
                { fieldname: "stop_after_first_match", fieldtype: "Check", label: __("Stop After First Match"), default: 0 },
                {
                    fieldname: "fields_config",
                    fieldtype: "Table",
                    label: __("Field Comparison Rules"),
                    reqd: 1,
                    fields: getDedupeTableFields() // Inline fields
                }
            ]
        },
        {
            func_name: "find_duplicates_by_fields",
            label: __("Find Exact Duplicates"),
            category: "Matching",
            icon: "duplicate",
            color: "#ef4444",
            get_config_fields: () => [
                { fieldname: "fields", fieldtype: "Small Text", label: __("Fields to Match"), reqd: 1 },
                { fieldname: "ignore_cancelled", fieldtype: "Check", label: __("Ignore Cancelled"), default: 1 }
            ]
        },
        {
            func_name: "check_duplicate_and_prevent_save",
            label: __("Block If Duplicate Exists"),
            category: "Validation",
            icon: "block",
            color: "#dc2626",
            get_config_fields: () => [{ fieldname: "fields", fieldtype: "Small Text", label: __("Unique Fields"), reqd: 1 }]
        },
        {
            func_name: "check_similar_and_prevent_save",
            label: __("Block If Similar Exists"),
            category: "Validation",
            icon: "block",
            color: "#b91c1c",
            get_config_fields: () => [
                { fieldname: "overall_threshold", fieldtype: "Float", label: __("Overall Threshold"), default: 0.8, reqd: 1 },
                { fieldname: "fields_config", fieldtype: "Table", label: __("Field Comparison Rules"), reqd: 1, fields: getDedupeTableFields() }
            ]
        },
        {
            func_name: "mark_as_duplicate",
            label: __("Mark as Duplicate"),
            category: "Actions",
            icon: "link",
            color: "#8b5cf6",
            get_config_fields: () => [{ fieldname: "master_document", fieldtype: "Data", label: __("Master Document"), reqd: 1 }]
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

    get_operation: function (name) { return this.operations.find(op => op.func_name === name); },
    get_visible_operations: function () { return this.operations.filter(op => op.visible !== false); }
};