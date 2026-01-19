import BaseEngine from "./BaseEngine.js";

/**
 * ProcessRuntime (ProcessEngine Logic)
 * Shared business logic for Process Adapters (Dialog & Vue).
 * Handles: Adapter Loading, Schema Resolution, Advanced Validation, DocField resolution.
 */
export default class ProcessRuntime extends BaseEngine {
    constructor(opts = {}) {
        super(opts);
        this.adapter = null;
        this.operation_def = null;
        this.schema = null;
        this.normalized_fields = [];
        this.initialized = false;
    }

    async init() {
        if (this.initialized) return;

        // 1. Load Adapter
        await this._load_adapter();

        // 2. Resolve Schema
        this.schema = this._resolve_schema();
        this.normalized_fields = await this._normalize_schema(this.schema);
        this._build_field_map(this.normalized_fields);

        // 3. Initial Dependency Evaluation
        await this.evaluate_dependencies(this.config, null, null, this.normalized_fields);

        // 4. Evaluate Child Rows (Recursively)
        const traverse_evaluate = async (fields, data) => {
            for (const field of fields) {
                if (field.fieldtype === "Table" && Array.isArray(data[field.fieldname])) {
                    for (const row of data[field.fieldname]) {
                        // Find table fieldname if possible or fallback
                        const table_name = row.__table_fieldname || field.fieldname;
                        await this.evaluate_dependencies(this.config, row, table_name, this.normalized_fields);

                        // Recurse if table inside table? (Not common but possible)
                        if (field.fields) {
                            await traverse_evaluate(field.fields, row);
                        }
                    }
                }
            }
        };
        await traverse_evaluate(this.normalized_fields, this.config);

        this.initialized = true;
    }

    async _load_adapter() {
        if (!flexirule.utils.load_process_adapter) {
            console.error("flexirule.utils.load_process_adapter is missing");
            return;
        }
        await flexirule.utils.load_process_adapter(this.process_name);
        this.adapter = flexirule.utils.get_process_adapter(this.process_name);

        if (this.adapter && this.adapter.get_operation) {
            this.operation_def = this.adapter.get_operation(this.operation_name);
        }

        // Run Setup Hooks
        const ctx = this._get_context();
        if (this.adapter && typeof this.adapter.setup === "function") {
            await this.adapter.setup(ctx);
        }
        if (this.operation_def && typeof this.operation_def.setup === "function") {
            await this.operation_def.setup(this.config, ctx);
        }
    }

    _resolve_schema() {
        if (!this.adapter) return [];
        const ctx = this._get_context();

        // 1. Adapter Dynamic Schema
        if (typeof this.adapter.get_schema === "function") {
            const schema = this.adapter.get_schema(this.operation_name, ctx);
            if (schema && schema.fields) return schema.fields;
            if (Array.isArray(schema)) return schema;
        }

        // 2. Operation specific config fields
        if (this.operation_def && typeof this.operation_def.get_config_fields === "function") {
            return this.operation_def.get_config_fields(ctx);
        }

        // 3. Static fields
        if (this.operation_def && this.operation_def.fields) {
            return this.operation_def.fields;
        }

        // 4. Adapter global schema fallback
        if (this.adapter.fields && !this.operation_name) {
            return this.adapter.fields;
        }

        return [];
    }

    _resolve_actions() {
        if (!this.adapter) return [];
        let actions = [];
        const ctx = this._get_context();

        // 1. Adapter global actions
        if (typeof this.adapter.get_actions === "function") {
            const res = this.adapter.get_actions(this.operation_name, ctx);
            if (Array.isArray(res)) actions = actions.concat(res);
        }

        // 2. Operation actions
        if (this.operation_def && typeof this.operation_def.get_actions === "function") {
            const res = this.operation_def.get_actions(ctx);
            if (Array.isArray(res)) actions = actions.concat(res);
        }

        return actions;
    }

    _resolve_output_schema(config) {
        if (this.adapter && typeof this.adapter.get_output_schema === "function") {
            const schema = this.adapter.get_output_schema(config, this._get_context());
            if (schema) return schema;
        }
        if (this.operation_def?.output_schema) {
            try {
                return typeof this.operation_def.output_schema === "string"
                    ? JSON.parse(this.operation_def.output_schema)
                    : this.operation_def.output_schema;
            } catch (e) { }
        }
        return null;
    }

    // Override BaseEngine to support DocField resolution
    async _normalize_field(field) {
        // Clone
        const f = { ...field };

        // Standard Flags
        f.reqd = f.reqd || 0;
        f.read_only = f.read_only || 0;
        f.hidden = f.hidden || 0;
        if (f.in_list_view === undefined) f.in_list_view = 1;

        // Grid width
        if (f.width) f.columns = f.width;

        // Map Flags
        f.fieldtype = this._map_fieldtype(f.fieldtype);

        // Helper: Resolve DocField Options
        if (f.fieldtype === "Autocomplete" || f.fieldtype === "DocField") {
            f.fieldtype = "Autocomplete";
            f.options = await this._resolve_docfield_options(f.options);
        } else if (f.fieldtype === "MultiSelectList" || f.fieldtype === "MultiDocField") {
            f.options = await this._resolve_docfield_options(f.options);
        } else if (f.fieldtype === "Table") {
            const children = f.fields || f.table_fields || [];
            if (!f._is_normalized) {
                f.fields = await this._normalize_schema(children);
                f._is_normalized = true;
            }
            // Ensure data init in config if missing
            if (this.config && this.config[f.fieldname] === undefined) {
                this.config[f.fieldname] = [];
            }
        }

        // Generic Options resolution
        f.options = await this._resolve_options(f, this.config, this._get_context());

        // Grid Formatting (Restore MultiCheck formatter)
        if (f.fieldtype === "MultiCheck" && !f.formatter) {
            f.formatter = (value) => {
                if (Array.isArray(value)) return value.join(", ");
                return value || "";
            };
        }

        // Separate Logic
        if (f.onchange) {
            f._onchange_logic = f.onchange;
            delete f.onchange;
        }

        return f;
    }

    async _resolve_docfield_options(ref) {
        if (!ref) return [];

        let target = this.document_type;
        let is_meta_only = false;

        if (ref === "Variables" || ref === "Field Picker") {
            is_meta_only = true;
        } else if (ref !== "DocField" && typeof ref === "string" && ref.indexOf(".") === -1) {
            target = ref;
        }

        // Get variables from context (if get_variable_options provided in context or instance)
        const context_vars = typeof this.get_variable_options === "function"
            ? (await this.get_variable_options())
            : [];

        // Or check globals/ctx?
        // ConfigurableAction assumed 'this.get_variable_options' might exist.

        if (is_meta_only) {
            return context_vars.map(v => v.value);
        }

        return await flexirule.utils.get_combined_fields(target, context_vars);
    }

    _map_fieldtype(fieldtype) {
        const mapping = {
            DocField: "Autocomplete",
            MultiDocField: "MultiSelectList",
        };
        return mapping[fieldtype] || fieldtype;
    }

    async validate() {
        // 1. Schema Validation (Base Logic)
        const result = await super.validate();
        const errors = result.errors;

        // 2. Adapter/Operation Validation
        if (this.operation_def && typeof this.operation_def.validate === "function") {
            try {
                const customErr = await this.operation_def.validate(this.config, this._get_context());
                if (customErr) {
                    if (Array.isArray(customErr)) errors.push(...customErr);
                    else errors.push(typeof customErr === 'string' ? customErr : "Validation failed");
                }
            } catch (e) {
                console.error("Validation error", e);
                errors.push(e.message);
            }
        }

        return {
            valid: errors.length === 0,
            errors: errors
        };
    }
}
