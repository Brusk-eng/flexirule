/**
 * CoreUtils.js
 * Shared logic for FlexiRule configuration engines.
 * Unifies validation, normalization, and condition evaluation.
 */

export default {
    /**
     * Map internal system fieldtypes to Frappe standard fieldtypes.
     */
    map_fieldtype(fieldtype) {
        const mapping = {
            DocField: "Autocomplete",
            MultiDocField: "MultiSelectList",
        };
        return mapping[fieldtype] || fieldtype;
    },

    /**
     * Safe evaluation of python-like conditions in JS.
     * @param {string} expression 
     * @param {object} context 
     */
    eval_condition(expression, context) {
        if (!expression) return true;
        if (expression.startsWith("eval:")) expression = expression.slice(5);
        try {
            return frappe.utils.eval(expression, context);
        } catch (e) {
            console.warn(`Dependency Eval Failed: "${expression}"`, e);
            return false;
        }
    },

    /**
     * Validates a configuration object against a normalized schema.
     * Returns standardized error object { valid: boolean, errors: string[] }
     * @param {object} config - The data object to validate
     * @param {Array} normalized_fields - Flattened array of field definitions
     * @param {object} dependency_states - (Optional) Current visibility/mandatory state of fields
     */
    validate_schema(config, normalized_fields, dependency_states = {}) {
        const errors = [];
        const rootState = dependency_states["root"] || {};

        for (const field of normalized_fields) {
            // Skip special types not relevant for data validation
            if (["Section Break", "Column Break", "HTML", "Button"].includes(field.fieldtype)) continue;

            // Handle Child Tables
            if (field.fieldtype === "Table") {
                // Tables handle their own internal validation usually, 
                // but we check if the table *itself* is mandatory (at least one row)
                const tableState = rootState[field.fieldname] || field;
                if (tableState.hidden) continue;

                const rows = config[field.fieldname] || [];
                if (tableState.reqd && rows.length === 0) {
                    errors.push(__("{0} requires at least one row", [field.label || field.fieldname]));
                }

                // Deep validation of rows
                this._validate_table_rows(rows, field, dependency_states, errors);
                continue;
            }

            // Handle Standard Fields
            const state = rootState[field.fieldname] || field;
            if (state.hidden) continue;

            if (state.reqd) {
                const value = config[field.fieldname];
                const has_value = value !== undefined && value !== null && value !== "";
                if (!has_value) {
                    errors.push(__("{0} is mandatory", [field.label || field.fieldname]));
                }
            }
        }

        return {
            valid: errors.length === 0,
            errors: errors
        };
    },

    _validate_table_rows(rows, table_field, dependency_states, errors) {
        if (!rows || !rows.length) return;
        const child_fields = table_field.fields || [];

        rows.forEach((row, idx) => {
            const row_name = row.name; // assuming dependency_states uses row name
            const rowHelper = (row_name && dependency_states[row_name]) ? dependency_states[row_name] : {};

            child_fields.forEach(cf => {
                if (["Section Break", "Column Break", "HTML"].includes(cf.fieldtype)) return;

                const fieldState = rowHelper[cf.fieldname] || cf;
                if (fieldState.hidden) return;

                if (fieldState.reqd) {
                    const value = row[cf.fieldname];
                    const has_value = value !== undefined && value !== null && value !== "";
                    if (!has_value) {
                        errors.push(__("Row #{0}: {1} is mandatory", [idx + 1, cf.label || cf.fieldname]));
                    }
                }
            });
        });
    }
};
