import { reactive } from "vue";
import ProcessRuntime from "../../../../core/ProcessRuntime.js";

/**
 * ProcessEngine
 * Vue-native equivalent of ConfigurableAction.js.
 * Extends ProcessRuntime for logic, adds Vue reactivity.
 */
export default class ProcessEngine extends ProcessRuntime {
    constructor(opts = {}) {
        // Inject reactive dependency state
        super({ ...opts, dependency_states: reactive({}) });
        this.initialized = false;
    }

    // Override _get_context to use our async handler
    _get_context(row = null) {
        return {
            doc: row || this.config,
            row: row,
            parent: this.config,
            config: this.config,
            document_type: this.document_type,
            process_name: this.process_name,
            operation_name: this.operation_name,
            vars: this._get_vars_dict ? this._get_vars_dict() : {},
            in_list: (l, i) => l && l.includes(i),
            has_common: (l1, l2) => l1 && l2 && l1.some((i) => l2.includes(i)),
            update_field: (field, val) => this.handleFieldChange(field, val, row),
        };
    }

    async handleFieldChange(fieldname, value, row = null) {
        if (row) {
            row[fieldname] = value;
        } else {
            this.config[fieldname] = value;
        }

        // Re-evaluate dependencies
        // Try to identify table if row provided
        let table_name = row ? (row.__table_fieldname || null) : null;

        await this.evaluate_dependencies(
            this.config,
            row,
            table_name,
            this.normalized_fields
        );

        // Run onchange logic
        // TODO: Handle name collisions properly (currently uses last-write wins from field_map)
        const fieldDef = this.field_map[fieldname];

        if (fieldDef && fieldDef._onchange_logic) {
            await fieldDef._onchange_logic(value, row, this._get_context(row));

            // Re-evaluate to ensure UI stays in sync after logic
            await this.evaluate_dependencies(
                this.config,
                row,
                table_name,
                this.normalized_fields
            );
        }
    }

    // Helper implementation for vars if needed (ConfigurableAction had empty)
    _get_vars_dict() {
        if (!this.available_variables) return {};
        if (Array.isArray(this.available_variables)) {
            const dict = {};
            this.available_variables.forEach(v => dict[v.value] = v.label || true);
            return dict;
        }
        return this.available_variables;
    }
}
