import { reactive } from "vue";
import BaseEngine from "../../../../core/BaseEngine.js";

/**
 * ConfigurationEngine
 * Specific base class for Vue configuration engines.
 * Manages reactive state and lifecycle.
 */
export default class ConfigurationEngine extends BaseEngine {
    constructor(opts = {}) {
        // Inject reactive dependency state
        super({ ...opts, dependency_states: reactive({}) });
        this.initialized = false;
    }

    async init() {
        // Override in subclasses
        this.initialized = true;
    }

    async getData() {
        // Override in subclasses
        return this.config;
    }

    dispose() {
        // Override in subclasses
    }

    // Helpers for Vue mapping
    _get_context(row = null) {
        return {
            doc: row || this.config,
            row: row,
            parent: this.config,
            config: this.config,
            document_type: this.document_type,
            vars: this._get_vars_dict(),
            update_field: (field, val) => this.handleFieldChange(field, val, row),
        };
    }

    /**
     * Converts available_variables array into a key-value dict for schema 'vars.' lookups.
     */
    _get_vars_dict() {
        if (!this.available_variables) return {};
        if (!Array.isArray(this.available_variables)) return this.available_variables;

        const dict = {};
        this.available_variables.forEach((v) => {
            dict[v.value] = v.label; // Or should we store the whole object? Legacy uses label for display in some places.
            // Actually, for 'vars.' lookups in depends_on, we usually check existence or value.
            // In FlexiRule context, vars[key] usually refers to the variable name itself?
            // Usually vars.some_var in depends_on check if some_var exists.
            dict[v.value] = true;
        });
        return dict;
    }

    async handleFieldChange(fieldname, value, row = null) {
        if (row) {
            row[fieldname] = value;
        } else {
            this.config[fieldname] = value;
        }

        // Re-evaluate dependencies
        await this.evaluate_dependencies(
            this.config,
            row,
            row ? row.__table_fieldname : null,
            this.normalized_fields
        );

        // Run onchange logic if defined in schema
        // Look up field definition. If in a table, try to find it within that table first.
        let fieldDef = null;
        if (row && row.__table_fieldname) {
            const tableDef = this.field_map[row.__table_fieldname];
            if (tableDef && tableDef.fields) {
                fieldDef = tableDef.fields.find(f => f.fieldname === fieldname);
            }
        }

        // Fallback to global map if not found or not in a table
        if (!fieldDef) {
            fieldDef = this.field_map[fieldname];
        }

        if (fieldDef) {
            const onchange = fieldDef.onchange || fieldDef._onchange_logic;
            if (typeof onchange === "function") {
                await onchange(value, row, this._get_context(row));

                // After onchange running, some values might have been updated manually (not via update_field)
                // Re-evaluate to ensure UI stays in sync.
                await this.evaluate_dependencies(
                    this.config,
                    row,
                    row ? row.__table_fieldname : null,
                    this.normalized_fields
                );
            }
        }
    }
}
