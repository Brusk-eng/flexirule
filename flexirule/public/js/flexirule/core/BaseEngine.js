/**
 * BaseEngine.js
 * Contains shared logic for configuration engines (Normalization, Dependency Evaluation, etc.)
 * Extracted from legacy ConfigurableAction.js to be shared between Vue and Frappe Dialog versions.
 */

export default class BaseEngine {
    constructor(opts = {}) {
        Object.assign(this, opts);
        this.dependency_states = opts.dependency_states || {}; // context_id -> { fieldname: { reqd, read_only, hidden, options } }
        this.field_map = {};
    }

    async _normalize_schema(raw_fields) {
        if (!raw_fields) return [];
        const normalized = [];
        for (const field of raw_fields) {
            const processed = await this._normalize_field(field);
            if (processed) normalized.push(processed);
        }
        return normalized;
    }

    async _normalize_field(field) {
        const f = { ...field };
        f.reqd = f.reqd || 0;
        f.read_only = f.read_only || 0;
        f.hidden = f.hidden || 0;

        if (f.in_list_view === undefined) f.in_list_view = 1;
        if (f.width) f.columns = f.width;

        f.fieldtype = this._map_fieldtype(f.fieldtype);

        // Resolve options if they are dynamic
        f.options = await this._resolve_options(f, this.config, this._get_context());

        if (f.fieldtype === "Table") {
            const children = f.fields || f.table_fields || [];
            if (!f._is_normalized) {
                f.fields = await this._normalize_schema(children);
                f._is_normalized = true;
            }
        }

        return f;
    }

    async _resolve_options(field, config, context = {}) {
        const getter = field.get_options || (typeof field.options === "function" ? field.options : null);
        if (getter) {
            try {
                return await getter(config, context, this.doc_meta);
            } catch (e) {
                console.warn(`Failed to resolve dynamic options for ${field.fieldname}`, e);
                return [];
            }
        }

        if (typeof field.options === "string") {
            if (field.options.startsWith("doc.")) {
                const key = field.options.replace("doc.", "");
                return config[key] || "";
            }
            if (field.options.startsWith("vars.") || field.options.startsWith("parent.")) {
                const key = field.options.replace("vars.", "").replace("parent.", "");
                return context[key] || (context.parent ? context.parent[key] : "");
            }
        }

        return field.options || "";
    }

    _map_fieldtype(fieldtype) {
        const mapping = {
            DocField: "Autocomplete",
            MultiDocField: "MultiSelectList",
        };
        return mapping[fieldtype] || fieldtype;
    }

    _build_field_map(fields) {
        this.field_map = {};
        const traverse = (fs) => {
            fs.forEach((f) => {
                this.field_map[f.fieldname] = f;
                if (f.fieldtype === "Table" && f.fields) {
                    traverse(f.fields);
                }
            });
        };
        traverse(fields);
    }

    async evaluate_dependencies(config, row = null, table_fieldname = null, normalized_fields = []) {
        const context_id = row ? row.name : "root";
        if (!this.dependency_states[context_id]) {
            this.dependency_states[context_id] = {};
        }

        let target_fields = [];
        if (row) {
            if (table_fieldname) {
                const field_def = this.field_map[table_fieldname];
                target_fields = field_def ? field_def.fields || [] : [];
            }
        } else {
            target_fields = normalized_fields.filter((f) => f.fieldtype !== "Table");
        }

        const eval_context = this._get_context(row);

        for (const field of target_fields) {
            const state = {
                reqd: field.reqd || 0,
                read_only: field.read_only || 0,
                hidden: field.hidden || 0,
                options: null,
            };

            if (field.depends_on) {
                state.hidden = this._eval_condition(field.depends_on, eval_context) ? 0 : 1;
            }
            if (field.mandatory_depends_on) {
                state.reqd = this._eval_condition(field.mandatory_depends_on, eval_context) ? 1 : 0;
            }
            if (field.read_only_depends_on) {
                state.read_only = this._eval_condition(field.read_only_depends_on, eval_context) ? 1 : 0;
            }

            const has_dynamic_options = field.get_options ||
                typeof field.options === "function" ||
                (typeof field.options === "string" && (field.options.startsWith("doc.") || field.options.startsWith("vars.") || field.options.startsWith("parent.")));

            if (has_dynamic_options) {
                state.options = await this._resolve_options(field, eval_context.doc, eval_context);
            }

            this.dependency_states[context_id][field.fieldname] = state;
        }
    }

    _eval_condition(expression, context) {
        if (!expression) return true;
        if (expression.startsWith("eval:")) expression = expression.slice(5);
        try {
            return frappe.utils.eval(expression, context);
        } catch (e) {
            console.warn(`Dependency Eval Failed: "${expression}"`, e);
            return false;
        }
    }

    // Generic Schema Validation
    async validate() {
        const errors = [];
        const rootState = this.dependency_states["root"] || {};

        // Ensure normalization is done or accessible
        // Use normalized_fields from instance if set, or need arg?
        // BaseEngine doesn't strictly own normalized_fields property in constructor, but subclasses set it.
        // Let's assume this.normalized_fields exists.
        const fields = this.normalized_fields || [];

        for (const field of fields) {
            if (field.fieldtype === "Table") {
                await this._validate_table(field, errors);
                continue;
            }
            const state = rootState[field.fieldname] || field;
            if (state.hidden) continue;

            if (state.reqd) {
                const value = this.config[field.fieldname];
                if (value === null || value === undefined || value === "") {
                    errors.push(`${field.label} is mandatory`);
                }
            }
        }

        return {
            valid: errors.length === 0,
            errors: errors
        };
    }

    async _validate_table(tableField, errors) {
        const rootState = this.dependency_states["root"] || {};
        const tableState = rootState[tableField.fieldname] || tableField;

        if (tableState.hidden) return;

        const rows = this.config[tableField.fieldname] || [];
        if (tableState.reqd && rows.length === 0) {
            errors.push(`${tableField.label} requires at least one row`);
            return;
        }

        for (let i = 0; i < rows.length; i++) {
            const row = rows[i];
            const rowState = this.dependency_states[row.name] || {};

            for (const field of tableField.fields) {
                const fieldState = rowState[field.fieldname] || field;
                if (fieldState.hidden) continue;

                if (fieldState.reqd) {
                    const value = row[field.fieldname];
                    if (value === null || value === undefined || value === "") {
                        errors.push(`Row ${i + 1}: ${field.label} is mandatory`);
                    }
                }
            }
        }
    }

    // Must be implemented by subclasses
    _get_context(row = null) {
        throw new Error("_get_context must be implemented");
    }
}
