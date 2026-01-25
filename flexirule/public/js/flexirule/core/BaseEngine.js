import SchemaUtils from "./schema.js";

export default class BaseEngine {
    constructor(opts = {}) {
        Object.assign(this, opts);
        this.dependency_states = opts.dependency_states || {};
        this.field_map = {};
    }

    async _normalize_schema(raw_fields) {
        if (!raw_fields) return [];
        const normalized = [];
        for (const field of raw_fields) {
            const processed = await SchemaUtils.normalizeField(
                field,
                this.config,
                this._get_context(),
                this.optionsResolver ? this.optionsResolver.bind(this) : null
            );
            if (processed) normalized.push(processed);
        }
        return normalized;
    }

    async _resolve_options(field, config, context = {}) {
        return await SchemaUtils.resolveOptions(field, config, context);
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
        return await SchemaUtils.evaluateDependencies(
            config,
            row,
            table_fieldname,
            normalized_fields,
            this.field_map,
            this._get_context(row),
            this.dependency_states
        );
    }

    async validate() {
        return SchemaUtils.validate(this.config, this.normalized_fields, this.dependency_states);
    }

    _get_context(row = null) {
        throw new Error("_get_context must be implemented");
    }
}
