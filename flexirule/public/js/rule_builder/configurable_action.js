// Copyright (c) 2026, FlexiRule and contributors
// For license information, please see license.txt

frappe.provide("flexirule.ui");

/**
 * ConfigurableAction - Runtime abstraction for node configuration management
 * 
 * Responsibilities:
 * 1. Resolve canonical schema from process+operation
 * 2. Load/save JSON config for the node
 * 3. Build Frappe Dialog fields (UI-agnostic)
 * 4. Handle nested tables, multi-selects, and default values
 * 5. Provide a standard API for Vue components, Dialogs, and Forms
 * 6. Trigger events on field value changes for reactive updates
 */
flexirule.ui.ConfigurableAction = class ConfigurableAction {
    constructor(opts) {
        /*
         * Options:
         *   process_name: string - Name of the Process DocType record
         *   operation_name: string - Name of the operation (func_name)
         *   node_data: object - The node's data object (action data)
         *   document_type: string - The Rule's target DocType
         *   doc_meta: object - Frappe meta for the document_type (optional)
         */
        Object.assign(this, opts);

        this.adapter = null;
        this.operation = null;
        this.schema = null;
        this.config = {};
        this.field_handlers = {};

        this._init();
    }

    _init() {
        // Get adapter from global namespace
        this.adapter = window.flexirule?.processes?.[this.process_name];

        if (this.adapter && this.operation_name) {
            // Get operation definition
            this.operation = this.adapter.get_operation?.(this.operation_name);

            // Call adapter setup if defined
            if (typeof this.adapter.setup === 'function') {
                this.adapter.setup(this._get_context());
            }
        }

        // Load existing config
        this.config = this.load_config();
    }

    _get_context() {
        return {
            process_name: this.process_name,
            operation_name: this.operation_name,
            document_type: this.document_type,
            doc_meta: this.doc_meta,
            config: this.config,
            update_field: (fieldname, value) => this.update_config_value(fieldname, value)
        };
    }

    // ============================================================
    // SCHEMA RESOLUTION
    // ============================================================

    /**
     * Get the canonical schema for this operation
     * Priority: adapter.get_schema() > operation.get_config_fields()
     */
    get_canonical_schema() {
        if (this.schema) return this.schema;

        if (!this.adapter || !this.operation_name) {
            return null;
        }

        // Try get_schema method first (new contract)
        if (typeof this.adapter.get_schema === 'function') {
            this.schema = this.adapter.get_schema(this.operation_name);
            if (this.schema) return this.schema;
        }

        // Fallback to operation.get_config_fields (existing contract)
        if (this.operation && typeof this.operation.get_config_fields === 'function') {
            const fields = this.operation.get_config_fields(this._get_context());
            this.schema = {
                title: this.operation.label || this.operation_name,
                size: 'large',
                fields: fields || []
            };
            return this.schema;
        }

        return null;
    }

    // ============================================================
    // CONFIG LOAD/SAVE
    // ============================================================

    /**
     * Load config from node_data.config JSON
     */
    load_config() {
        if (!this.node_data?.config) return {};

        try {
            const config = JSON.parse(this.node_data.config);
            return config || {};
        } catch (e) {
            console.warn('ConfigurableAction: Failed to parse config', e);
            return {};
        }
    }

    /**
     * Save config values to node_data.config
     */
    save_config(values) {
        // Merge with defaults from schema
        const schema = this.get_canonical_schema();
        const merged = { ...this.config };

        if (schema?.fields) {
            for (const field of schema.fields) {
                if (values[field.fieldname] !== undefined) {
                    merged[field.fieldname] = values[field.fieldname];
                } else if (field.default !== undefined && merged[field.fieldname] === undefined) {
                    merged[field.fieldname] = field.default;
                }
            }
        }

        // Also include any extra values not in schema
        Object.assign(merged, values);

        this.config = merged;

        if (this.node_data) {
            this.node_data.config = JSON.stringify(merged);
        }

        return merged;
    }

    /**
     * Update a single config value
     */
    update_config_value(fieldname, value) {
        this.config[fieldname] = value;
        if (this.node_data) {
            this.node_data.config = JSON.stringify(this.config);
        }
    }

    /**
     * Get current config value
     */
    get_value(fieldname) {
        return this.config[fieldname];
    }

    // ============================================================
    // DIALOG FIELD BUILDING
    // ============================================================

    /**
     * Build Frappe Dialog-compatible fields from schema
     */
    async build_dialog_fields() {
        const schema = this.get_canonical_schema();
        if (!schema?.fields) return [];

        const dialog_fields = [];

        for (const field of schema.fields) {
            const mapped = await this._map_schema_field(field);
            if (mapped) {
                if (Array.isArray(mapped)) {
                    dialog_fields.push(...mapped);
                } else {
                    dialog_fields.push(mapped);
                }
            }
        }

        return dialog_fields;
    }

    /**
     * Map a single schema field to Frappe Dialog field format
     */
    async _map_schema_field(field) {
        const { fieldname, fieldtype, label, reqd, options, description } = field;
        const default_val = field.default;
        const current_val = this.config[fieldname];

        // Base field definition
        const base = {
            fieldname,
            label,
            reqd,
            description,
            default: current_val !== undefined ? current_val : default_val
        };

        switch (fieldtype) {
            case 'DocField':
                // Field Picker → Autocomplete
                return {
                    ...base,
                    fieldtype: 'Autocomplete',
                    options: await this._get_field_options(options)
                };

            case 'MultiDocField':
                // Multi Field Picker → MultiSelectList
                return {
                    ...base,
                    fieldtype: 'MultiSelectList',
                    options: await this._get_field_options(options)
                };

            case 'Table':
                // Inline Table
                return await this._build_table_field(field, base);

            case 'MultiSelect':
                // Multi-select → MultiSelectList
                return {
                    ...base,
                    fieldtype: 'MultiSelectList',
                    options: this._parse_select_options(options)
                };

            case 'Percent':
                return {
                    ...base,
                    fieldtype: 'Float',
                    description: description || __('Value from 0-100')
                };

            case 'Data':
                // Check for Field Picker option
                if (options === 'Field Picker') {
                    return {
                        ...base,
                        fieldtype: 'Autocomplete',
                        options: await this._get_field_options('parent.document_type')
                    };
                }
                return { ...base, fieldtype, options };

            default:
                // Pass through standard Frappe fieldtypes
                return { ...base, fieldtype, options };
        }
    }

    /**
     * Build a Table field with inline child fields
     */
    async _build_table_field(field, base) {
        const child_schema = field.fields || field.table_fields || [];

        if (!child_schema.length) {
            console.warn(`ConfigurableAction: No fields defined for table ${field.fieldname}`);
            return null;
        }

        const child_fields = [];

        for (const cf of child_schema) {
            const mapped = await this._map_child_field(cf);
            if (mapped) {
                mapped.in_list_view = cf.in_list_view !== false ? 1 : 0;
                if (cf.width) mapped.columns = cf.width;
                child_fields.push(mapped);
            }
        }

        return {
            ...base,
            fieldtype: 'Table',
            fields: child_fields,
            data: this.config[field.fieldname] || [],
            cannot_add_rows: field.cannot_add_rows || false,
            in_place_edit: field.in_place_edit || false
        };
    }

    /**
     * Map child table field (simplified for inline editing)
     */
    async _map_child_field(field) {
        const { fieldname, fieldtype, label, reqd, options, description } = field;
        const default_val = field.default;

        const base = {
            fieldname,
            label,
            reqd,
            description,
            default: default_val
        };

        switch (fieldtype) {
            case 'DocField':
                // In child tables, DocField becomes Select with options
                const opts = await this._get_field_options(options);
                return {
                    ...base,
                    fieldtype: 'Select',
                    options: opts.map(o => o.value || o).join('\n')
                };

            case 'MultiDocField':
            case 'MultiSelect':
                // Preserve as Select for simplicity in grids
                return {
                    ...base,
                    fieldtype: 'Select',
                    options: this._parse_select_options(options).map(o => o.value || o).join('\n')
                };

            default:
                return { ...base, fieldtype, options };
        }
    }

    /**
     * Get field options for DocField/Link types
     */
    async _get_field_options(options_ref) {
        let target_doctype = this.document_type;

        if (options_ref === 'parent.document_type') {
            target_doctype = this.document_type;
        } else if (options_ref && !options_ref.includes('.')) {
            target_doctype = options_ref;
        }

        if (!target_doctype) return [];

        try {
            const result = await frappe.call({
                method: 'flexirule.ruleflow.api.get_doctype_fields',
                args: { doctype: target_doctype }
            });

            if (result.message?.parent_fields) {
                const opts = result.message.parent_fields.map(f => ({
                    value: f.value,
                    label: `${f.label} (${f.fieldtype})`
                }));

                // Add child table fields
                if (result.message.child_tables) {
                    result.message.child_tables.forEach(table => {
                        opts.push({ value: '', label: `── ${table.table_label} ──`, disabled: true });
                        table.fields.forEach(f => {
                            opts.push({ value: f.value, label: `  ${f.label}` });
                        });
                    });
                }

                return opts;
            }
        } catch (e) {
            console.error('ConfigurableAction: Failed to fetch field options:', e);
        }

        return [];
    }

    /**
     * Parse select options from newline-separated string
     */
    _parse_select_options(options) {
        if (!options) return [];
        if (Array.isArray(options)) return options;

        return options.split('\n').filter(Boolean).map(opt => ({
            value: opt.trim(),
            label: opt.trim()
        }));
    }

    // ============================================================
    // FIELD CHANGE EVENTS
    // ============================================================

    /**
     * Handle field value change - triggers adapter hooks
     */
    on_field_change(fieldname, value, all_values, row_context = null) {
        // Update internal config
        if (!row_context) {
            this.config[fieldname] = value;
        }

        // Find field definition in schema
        const schema = this.get_canonical_schema();
        if (!schema?.fields) return;

        const field_def = this._find_field_def(schema.fields, fieldname);
        if (!field_def) return;

        // Call field's onchange handler if defined
        if (typeof field_def.onchange === 'function') {
            const ctx = {
                ...this._get_context(),
                row: row_context,
                all_values
            };
            field_def.onchange(value, row_context, ctx);
        }
    }

    /**
     * Recursively find field definition by fieldname
     */
    _find_field_def(fields, fieldname) {
        for (const f of fields) {
            if (f.fieldname === fieldname) return f;

            // Check table child fields
            if (f.fieldtype === 'Table' && (f.fields || f.table_fields)) {
                const child = this._find_field_def(f.fields || f.table_fields, fieldname);
                if (child) return child;
            }
        }
        return null;
    }

    // ============================================================
    // DIALOG HELPERS
    // ============================================================

    /**
     * Open configuration dialog
     */
    async show_dialog(opts = {}) {
        const schema = this.get_canonical_schema();

        if (!schema?.fields?.length) {
            frappe.msgprint(__('No configuration available for this operation'));
            return null;
        }

        // Call adapter onload if defined
        if (typeof this.adapter?.onload === 'function') {
            this.adapter.onload(this.operation_name, this._get_context());
        }

        const dialog_fields = await this.build_dialog_fields();

        const dialog = new frappe.ui.Dialog({
            title: schema.title || __('Configure'),
            size: schema.size || 'extra-large',
            fields: dialog_fields,
            primary_action_label: opts.primary_action_label || __('Save'),
            primary_action: () => {
                const values = this.collect_dialog_values(dialog);
                this.save_config(values);

                if (typeof opts.on_save === 'function') {
                    opts.on_save(values);
                }

                dialog.hide();
            }
        });

        dialog.show();
        this.populate_dialog(dialog);
        this._bind_change_handlers(dialog);

        return dialog;
    }

    /**
     * Collect values from dialog including table data
     */
    collect_dialog_values(dialog) {
        const values = dialog.get_values() || {};
        const schema = this.get_canonical_schema();

        if (schema?.fields) {
            for (const f of schema.fields) {
                if (f.fieldtype === 'Table') {
                    const field = dialog.fields_dict[f.fieldname];
                    if (field?.grid) {
                        values[f.fieldname] = field.grid.get_data();
                    }
                }
            }
        }

        return values;
    }

    /**
     * Populate dialog with current config values
     */
    populate_dialog(dialog) {
        const schema = this.get_canonical_schema();
        if (!schema?.fields) return;

        // Set table data
        setTimeout(() => {
            for (const f of schema.fields) {
                if (f.fieldtype === 'Table' && this.config[f.fieldname]) {
                    const field = dialog.fields_dict[f.fieldname];
                    if (field?.grid) {
                        field.grid.df.data = this.config[f.fieldname];
                        field.grid.refresh();
                    }
                }
            }

            // Set non-table values
            const non_table_config = {};
            for (const [key, value] of Object.entries(this.config)) {
                const field_def = schema.fields.find(f => f.fieldname === key);
                if (field_def && field_def.fieldtype !== 'Table') {
                    non_table_config[key] = value;
                }
            }

            if (Object.keys(non_table_config).length > 0) {
                dialog.set_values(non_table_config);
            }
        }, 150);
    }

    /**
     * Bind change handlers to dialog fields
     */
    _bind_change_handlers(dialog) {
        const schema = this.get_canonical_schema();
        if (!schema?.fields) return;

        for (const f of schema.fields) {
            // Bind top-level field onchange
            if (typeof f.onchange === 'function') {
                const field = dialog.fields_dict[f.fieldname];
                if (field?.$input) {
                    field.$input.on('change', () => {
                        const value = field.get_value();
                        this.on_field_change(f.fieldname, value, dialog.get_values());
                    });
                }
            }

            // Bind table child field onchange handlers
            if (f.fieldtype === 'Table') {
                this._bind_grid_change_handlers(dialog, f);
            }
        }
    }

    /**
     * Bind change handlers for grid (table) child fields
     */
    _bind_grid_change_handlers(dialog, table_field) {
        const field = dialog.fields_dict[table_field.fieldname];
        if (!field?.grid) return;

        const grid = field.grid;
        const child_fields = table_field.fields || table_field.table_fields || [];
        const me = this;

        // Find child fields with onchange handlers
        const fields_with_onchange = child_fields.filter(cf => typeof cf.onchange === 'function');
        if (!fields_with_onchange.length) return;

        // Use grid's on_row_change event or field-level refresh
        // Frappe's grid emits events on field changes
        $(grid.wrapper).on('change', 'input, select, textarea', function (e) {
            const $input = $(this);
            const $row = $input.closest('.grid-row');
            const row_idx = $row.attr('data-idx');

            if (!row_idx) return;

            const row = grid.get_row(cint(row_idx) - 1);
            if (!row) return;

            // Find which field changed
            const $field_wrapper = $input.closest('[data-fieldname]');
            const fieldname = $field_wrapper.attr('data-fieldname');

            if (!fieldname) return;

            // Check if this field has an onchange handler
            const field_def = fields_with_onchange.find(cf => cf.fieldname === fieldname);
            if (!field_def) return;

            // Get the new value
            const value = row.doc[fieldname];

            // Create context for the handler
            const ctx = {
                ...me._get_context(),
                row: row.doc,
                grid: grid,
                update_field: (target_fieldname, target_value) => {
                    // Update the row's field value
                    row.doc[target_fieldname] = target_value;
                    // Refresh the specific field in the grid row
                    if (row.columns && row.columns[target_fieldname]) {
                        row.refresh_field(target_fieldname);
                    }
                    grid.refresh();
                }
            };

            // Call the onchange handler
            field_def.onchange(value, row.doc, ctx);
        });
    }
};
