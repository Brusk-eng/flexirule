/**
 * Enrichment Process Adapter
 * Provides high-quality UI for document enrichment operations.
 */

flexirule.rule_builder.enrichment = {
    /**
     * Get the process schema metadata
     */
    get_schema() {
        return {
            name: "Enrichment",
            label: __("Enrichment"),
            description: __("Enhance document data using formulas, templates, and lookups."),
            icon: "magic",
            color: "purple"
        };
    },

    /**
     * Get a specific operation by name
     */
    get_operation(func_name) {
        const operations = {
            set_value: {
                label: __("Set Value"),
                description: __("Set a static or dynamic value using Jinja."),
                icon: "edit"
            },
            calculate_value: {
                label: __("Calculate Value"),
                description: __("Compute field values using Python formulas."),
                icon: "calculator"
            },
            linked_doc_autocomplete: {
                label: __("Linked Doc Autocomplete"),
                description: __("Copy data from a document linked to the current record."),
                icon: "link"
            },
            copy_from_template: {
                label: __("Copy from Template"),
                description: __("Populate fields from a predefined template document."),
                icon: "copy"
            },
            apply_naming_series: {
                label: __("Apply Naming Series"),
                description: __("Dynamically set the document's naming series."),
                icon: "tag"
            }
        };
        return operations[func_name];
    },

    /**
     * Get visible operations in the Rule Builder
     */
    get_visible_operations() {
        return ["set_value", "calculate_value", "linked_doc_autocomplete", "copy_from_template", "apply_naming_series"];
    },

    /**
     * Get default configuration for an operation
     */
    get_default_config(operation) {
        const defaults = {
            set_value: { field: "", value: "", overwrite: 0 },
            calculate_value: { target_field: "", formula: "" },
            linked_doc_autocomplete: { source_link_field: "", field_mapping: [] },
            copy_from_template: { template_doctype: "", template_name: "", field_list: [] },
            apply_naming_series: { naming_series: "" }
        };
        return defaults[operation] || {};
    },

    /**
     * Get UI fields for operation configuration
     */
    get_config_fields(operation, context) {
        const doc_fields = this.get_doc_fields(context);

        if (operation === "set_value") {
            return [
                {
                    fieldname: "field",
                    fieldtype: "Select",
                    label: __("Target Field"),
                    options: doc_fields,
                    reqd: 1,
                    columns: 6
                },
                {
                    fieldname: "overwrite",
                    fieldtype: "Check",
                    label: __("Overwrite if exists"),
                    default: 0,
                    columns: 6
                },
                {
                    fieldname: "value",
                    fieldtype: "Small Text",
                    label: __("Value"),
                    description: __("Supports Jinja: {{ today() }}, {{ doc.customer_name }}, etc."),
                    reqd: 1
                }
            ];
        }

        if (operation === "calculate_value") {
            return [
                {
                    fieldname: "target_field",
                    fieldtype: "Select",
                    label: __("Target Field"),
                    options: doc_fields,
                    reqd: 1
                },
                {
                    fieldname: "formula",
                    fieldtype: "Code",
                    label: __("Formula"),
                    options: "Python",
                    description: __("Expression like: doc.base_amount * doc.conversion_rate"),
                    reqd: 1
                }
            ];
        }

        if (operation === "linked_doc_autocomplete") {
            return [
                {
                    fieldname: "source_link_field",
                    fieldtype: "Select",
                    label: __("Link Field"),
                    description: __("Select the Link/Dynamic Link field to pull data from."),
                    options: doc_fields.filter(f => ["Link", "Dynamic Link"].includes(f.fieldtype) || f.value === ""),
                    reqd: 1
                },
                {
                    fieldname: "field_mapping",
                    fieldtype: "Table",
                    label: __("Field Mapping"),
                    reqd: 1,
                    fields: [
                        {
                            fieldname: "source_field",
                            fieldtype: "Data",
                            label: __("Source Field (Linked Doc)"),
                            reqd: 1,
                            columns: 6
                        },
                        {
                            fieldname: "target_field",
                            fieldtype: "Select",
                            label: __("Target Field (Current Doc)"),
                            options: doc_fields,
                            reqd: 1,
                            columns: 6
                        }
                    ]
                }
            ];
        }

        if (operation === "copy_from_template") {
            return [
                {
                    fieldname: "template_doctype",
                    fieldtype: "Link",
                    label: __("Template DocType"),
                    options: "DocType",
                    reqd: 1,
                    onchange: (val, ctx) => {
                        ctx.update_field("template_name", { options: val });
                        ctx.update_field("field_list", { options: "DocField", get_query: () => ({ filters: { parent: val } }) });
                    }
                },
                {
                    fieldname: "template_name",
                    fieldtype: "Dynamic Link",
                    label: __("Template Document"),
                    options: "template_doctype",
                    reqd: 1
                },
                {
                    fieldname: "field_list",
                    fieldtype: "MultiSelect",
                    label: __("Fields to Copy"),
                    description: __("Select one or more fields to overwrite from the template."),
                    reqd: 1
                }
            ];
        }

        if (operation === "apply_naming_series") {
            return [
                {
                    fieldname: "naming_series",
                    fieldtype: "Data",
                    label: __("Naming Series"),
                    description: __("Example: INV-.YYYY.-.####"),
                    reqd: 1
                }
            ];
        }

        return [];
    },

    /**
     * Helper to get fields from context doctype
     */
    get_doc_fields(context) {
        const doctype = context.default_ref_doctype;
        if (!doctype) return [{ label: __("Select DocType first"), value: "" }];

        const fields = frappe.get_meta(doctype).fields
            .filter(f => !frappe.model.no_value_type.includes(f.fieldtype))
            .map(f => ({
                label: `${__(f.label)} (${f.fieldname})`,
                value: f.fieldname,
                fieldtype: f.fieldtype
            }));

        return [{ label: __("Select a field..."), value: "" }, ...fields];
    }
};
