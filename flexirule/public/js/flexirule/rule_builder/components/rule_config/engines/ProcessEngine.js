import { reactive } from "vue";
import ProcessRuntime from "../../../../core/ProcessRuntime.js";
import AsyncJobQueue from "../../../../core/AsyncJobQueue.js";

/**
 * ProcessEngine
 * Vue-native equivalent of ProcessConfigurator.
 * Extends ProcessRuntime for logic, adds Vue reactivity and serialized updates.
 */
export default class ProcessEngine extends ProcessRuntime {
    constructor(opts = {}) {
        // Inject reactive dependency state
        super({ ...opts, dependency_states: reactive({}) });
        this.job_queue = new AsyncJobQueue();
        this.initialized = false;
    }

    /**
     * Override _get_context to use our serialized update handler.
     */
    _get_context(row = null) {
        return {
            doc: row || this.config,
            row: row,
            parent: this.config,
            config: this.config,
            document_type: this.document_type,
            process_name: this.process_name,
            operation_name: this.operation_name,
            meta: this.doc_meta,
            doc_meta: this.doc_meta,
            vars: this._get_vars_dict(),
            in_list: (l, i) => l && l.includes(i),
            has_common: (l1, l2) => l1 && l2 && l1.some((i) => l2.includes(i)),
            update_field: (field, val) => this.handleFieldChange(field, val, row),
        };
    }

    /**
     * Serialized field update handler.
     */
    async handleFieldChange(fieldname, value, row = null) {
        const key = row ? `${row.name}:${fieldname}` : fieldname;

        return this.job_queue.run(key, async () => {
            // Find global target for mutation
            let target_row = row;
            if (row && row.__table_fieldname) {
                const grid_data = this.config[row.__table_fieldname] || [];
                // Ensure we are mutating the ACTUAL object in engine.config
                const global_row = grid_data.find(r => r.name === row.name);
                if (global_row) target_row = global_row;
            }

            // 1. Mutate State
            if (target_row && target_row !== this.config) {
                target_row[fieldname] = value;
            } else {
                this.config[fieldname] = value;
            }

            // 2. Re-evaluate dependencies and run logic
            await this._handle_change(fieldname, value, target_row);
        });
    }

    async _handle_change(fieldname, value, row) {
        const table_name = row ? (row.__table_fieldname || null) : null;

        // 1. Evaluate Dependencies
        await this.evaluate_dependencies(
            this.config,
            row,
            table_name,
            this.normalized_fields
        );

        // 2. Run onchange logic
        const fieldDef = this.field_map[fieldname];
        if (fieldDef && fieldDef._onchange_logic) {
            await fieldDef._onchange_logic(value, row, this._get_context(row));

            // 3. Re-evaluate to ensure UI stays in sync after logic
            await this.evaluate_dependencies(
                this.config,
                row,
                table_name,
                this.normalized_fields
            );
        }
    }

    _get_vars_dict() {
        if (!this.available_variables) return {};
        return this.available_variables;
    }
}
