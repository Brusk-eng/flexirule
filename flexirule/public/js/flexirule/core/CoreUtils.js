/**
 * CoreUtils.js
 * Shared logic for FlexiRule configuration engines.
 * Unifies validation, normalization, and condition evaluation.
 */

// Ensure translation function is available
const __ = window.__ || ((s, args) => {
    if (!args) return s;
    if (Array.isArray(args)) {
        args.forEach((a, i) => { s = s.replace(`{${i}}`, a); });
    }
    return s;
});

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
            if (typeof frappe !== "undefined" && frappe.utils && frappe.utils.eval) {
                return frappe.utils.eval(expression, context);
            }
            // Fallback for simple evaluation if frappe is missing (e.g. testing)
            return true;
        } catch (e) {
            console.warn(`Dependency Eval Failed: "${expression}"`, e);
            return false;
        }
    },

    /**
     * Validates a configuration object against a normalized schema.
     */
    validate_schema(config, normalized_fields, dependency_states = {}) {
        const errors = [];
        const rootState = dependency_states["root"] || {};

        for (const field of normalized_fields) {
            if (["Section Break", "Column Break", "HTML", "Button"].includes(field.fieldtype)) continue;

            if (field.fieldtype === "Table") {
                const tableState = rootState[field.fieldname] || field;
                if (tableState.hidden) continue;

                const rows = config[field.fieldname] || [];
                if (tableState.reqd && rows.length === 0) {
                    errors.push(__("{0} requires at least one row", [field.label || field.fieldname]));
                }
                this._validate_table_rows(rows, field, dependency_states, errors);
                continue;
            }

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

        return { valid: errors.length === 0, errors: errors };
    },

    _validate_table_rows(rows, table_field, dependency_states, errors) {
        if (!rows || !rows.length) return;
        const child_fields = table_field.fields || [];

        rows.forEach((row, idx) => {
            const row_name = row.name;
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
    },

    /**
     * Lightweight JSON Schema Validator.
     */
    validate_json_schema(data, schema, path = "") {
        const errors = [];
        if (!schema) return errors;

        const type = Array.isArray(data) ? "array" : typeof data;
        const expectedType = schema.type;

        if (expectedType && type !== expectedType) {
            if (!(expectedType === "integer" && Number.isInteger(data))) {
                errors.push(__("{0}: expected type {1}, got {2}", [path || "root", expectedType, type]));
                return errors;
            }
        }

        if (schema.enum && !schema.enum.includes(data)) {
            errors.push(__("{0}: must be one of {1}", [path || "root", schema.enum.join(", ")]));
        }

        if (type === "object" && schema.properties) {
            if (schema.required) {
                schema.required.forEach(prop => {
                    if (data[prop] === undefined || data[prop] === null || data[prop] === "") {
                        errors.push(__("{0}: {1} is required", [path || "root", prop]));
                    }
                });
            }
            Object.keys(schema.properties).forEach(prop => {
                if (data[prop] !== undefined) {
                    const sub = this.validate_json_schema(data[prop], schema.properties[prop], path ? `${path}.${prop}` : prop);
                    errors.push(...sub);
                }
            });
        }

        if (type === "array" && schema.items && data.length > 0) {
            data.forEach((item, idx) => {
                const sub = this.validate_json_schema(item, schema.items, `${path}[${idx}]`);
                errors.push(...sub);
            });
        }

        return errors;
    }
};
