import CoreUtils from "./CoreUtils";

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

        f.fieldtype = CoreUtils.map_fieldtype(f.fieldtype);

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
                state.hidden = CoreUtils.eval_condition(field.depends_on, eval_context) ? 0 : 1;
            }
            if (field.mandatory_depends_on) {
                state.reqd = CoreUtils.eval_condition(field.mandatory_depends_on, eval_context) ? 1 : 0;
            }
            if (field.read_only_depends_on) {
                state.read_only = CoreUtils.eval_condition(field.read_only_depends_on, eval_context) ? 1 : 0;
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

    // Generic Schema Validation using CoreUtils
    async validate() {
        // Assume this.normalized_fields is populated by subclass logic
        const fields = this.normalized_fields || [];
        return CoreUtils.validate_schema(this.config, fields, this.dependency_states);
    }

    // Must be implemented by subclasses
    _get_context(row = null) {
        throw new Error("_get_context must be implemented");
    }
}
