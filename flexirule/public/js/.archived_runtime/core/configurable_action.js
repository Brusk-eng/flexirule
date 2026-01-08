/**
 * FlexiRule ConfigurableAction
 *
 * Single source of truth for action configuration state.
 * Provides API for UI to read/write configuration values,
 * manage dirty state, and validate inputs.
 *
 * The UI never owns business state - it reads from and writes to
 * ConfigurableAction exclusively.
 */

frappe.provide("flexirule");

flexirule.ConfigurableAction = class ConfigurableAction {
    /**
     * Create a ConfigurableAction instance.
     *
     * @param {Object} opts - Options
     * @param {string} opts.action_type - Type of action (e.g., 'process')
     * @param {Object} opts.adapter - Adapter providing schema and defaults
     * @param {Object} opts.initial_config - Initial configuration values
     * @param {Function} opts.on_change - Called when config changes
     */
    constructor(opts = {}) {
        this.action_type = opts.action_type || '';
        this.adapter = opts.adapter || null;
        this.on_change = opts.on_change || null;

        // Internal state
        this._config = {};
        this._dirty = false;
        this._errors = [];

        // Initialize with defaults, then apply initial config
        this._apply_defaults();
        if (opts.initial_config) {
            this.set_config(opts.initial_config, { silent: true });
        }
    }

    /**
     * Get current configuration values.
     *
     * @returns {Object} - Current config (deep copy)
     */
    get_config() {
        return JSON.parse(JSON.stringify(this._config));
    }

    /**
     * Set configuration values.
     *
     * @param {Object} config - New configuration values
     * @param {Object} opts - Options { silent: boolean, merge: boolean }
     */
    set_config(config, opts = {}) {
        if (!config) return;

        if (opts.merge !== false) {
            // Merge with existing config
            this._config = this._deep_merge(this._config, config);
        } else {
            // Replace entirely
            this._config = JSON.parse(JSON.stringify(config));
        }

        if (!opts.silent) {
            this.mark_dirty();
        }
    }

    /**
     * Get a single config value by path.
     *
     * @param {string} path - Dot-separated path (e.g., 'process_name' or 'rows.0.field')
     * @returns {*} - Value at path
     */
    get_value(path) {
        return this._get_path(this._config, path);
    }

    /**
     * Set a single config value by path.
     *
     * @param {string} path - Dot-separated path
     * @param {*} value - Value to set
     * @param {Object} opts - Options { silent: boolean }
     */
    set_value(path, value, opts = {}) {
        this._set_path(this._config, path, value);

        if (!opts.silent) {
            this.mark_dirty();
        }
    }

    /**
     * Get UI schema from adapter.
     *
     * @returns {Object} - Normalized UI schema with fields, tables, dependencies
     */
    get_ui_schema() {
        if (this.adapter && this.adapter.get_ui_schema) {
            return this.adapter.get_ui_schema(this._config);
        }

        // Default empty schema
        return {
            fields: [],
            tables: [],
        };
    }

    /**
     * Get default configuration from adapter.
     *
     * @returns {Object} - Default config values
     */
    get_default_config() {
        if (this.adapter && this.adapter.get_default_config) {
            return this.adapter.get_default_config();
        }
        return {};
    }

    /**
     * Validate current configuration.
     *
     * @returns {Object} - { valid: boolean, errors: Array }
     */
    validate() {
        this._errors = [];

        // Get schema for validation
        const schema = this.get_ui_schema();

        // Validate required fields
        schema.fields?.forEach(field => {
            if (field.reqd) {
                const value = this._config[field.fieldname];
                if (this._is_empty(value)) {
                    this._errors.push({
                        fieldname: field.fieldname,
                        message: __('"{0}" is required', [__(field.label || field.fieldname)]),
                    });
                }
            }
        });

        // Validate tables
        schema.tables?.forEach(table => {
            const rows = this._config[table.fieldname] || [];

            if (table.reqd && rows.length === 0) {
                this._errors.push({
                    fieldname: table.fieldname,
                    message: __('"{0}" requires at least one row', [__(table.label || table.fieldname)]),
                });
            }

            // Validate each row
            rows.forEach((row, idx) => {
                table.columns?.forEach(col => {
                    if (col.reqd) {
                        const value = row[col.fieldname];
                        if (this._is_empty(value)) {
                            this._errors.push({
                                fieldname: `${table.fieldname}.${idx}.${col.fieldname}`,
                                message: __('Row {0}: "{1}" is required', [idx + 1, __(col.label || col.fieldname)]),
                            });
                        }
                    }
                });
            });
        });

        // Run adapter validation if available
        if (this.adapter && this.adapter.validate) {
            const adapter_errors = this.adapter.validate(this._config);
            if (adapter_errors && adapter_errors.length) {
                this._errors = this._errors.concat(adapter_errors);
            }
        }

        return {
            valid: this._errors.length === 0,
            errors: this._errors,
        };
    }

    /**
     * Get validation errors from last validate() call.
     *
     * @returns {Array} - Array of error objects
     */
    get_errors() {
        return this._errors;
    }

    /**
     * Mark configuration as dirty (changed).
     */
    mark_dirty() {
        this._dirty = true;

        if (this.on_change) {
            this.on_change(this._config);
        }
    }

    /**
     * Clear dirty flag.
     */
    clear_dirty() {
        this._dirty = false;
    }

    /**
     * Check if configuration is dirty.
     *
     * @returns {boolean}
     */
    is_dirty() {
        return this._dirty;
    }

    // --- Table Operations ---

    /**
     * Add a row to a table field.
     *
     * @param {string} table_fieldname - Table field name
     * @param {Object} row_data - Initial row data (optional)
     * @returns {Object} - The added row
     */
    add_row(table_fieldname, row_data = {}) {
        if (!this._config[table_fieldname]) {
            this._config[table_fieldname] = [];
        }

        const schema = this.get_ui_schema();
        const table_schema = schema.tables?.find(t => t.fieldname === table_fieldname);

        // Apply column defaults
        const row = {};
        if (table_schema && table_schema.columns) {
            table_schema.columns.forEach(col => {
                if (col.default !== undefined) {
                    row[col.fieldname] = col.default;
                }
            });
        }

        // Merge provided data
        Object.assign(row, row_data);

        // Add internal idx
        row._idx = this._config[table_fieldname].length;

        this._config[table_fieldname].push(row);
        this.mark_dirty();

        return row;
    }

    /**
     * Remove a row from a table field.
     *
     * @param {string} table_fieldname - Table field name
     * @param {number} row_idx - Row index to remove
     */
    remove_row(table_fieldname, row_idx) {
        if (!this._config[table_fieldname]) return;

        this._config[table_fieldname].splice(row_idx, 1);

        // Reindex
        this._config[table_fieldname].forEach((row, idx) => {
            row._idx = idx;
        });

        this.mark_dirty();
    }

    /**
     * Update a row in a table field.
     *
     * @param {string} table_fieldname - Table field name
     * @param {number} row_idx - Row index
     * @param {Object} row_data - Data to merge into row
     */
    update_row(table_fieldname, row_idx, row_data) {
        if (!this._config[table_fieldname]) return;
        if (!this._config[table_fieldname][row_idx]) return;

        Object.assign(this._config[table_fieldname][row_idx], row_data);
        this.mark_dirty();
    }

    /**
     * Get rows from a table field.
     *
     * @param {string} table_fieldname - Table field name
     * @returns {Array} - Array of rows
     */
    get_rows(table_fieldname) {
        return this._config[table_fieldname] || [];
    }

    // --- Private Helpers ---

    /**
     * Apply default values from adapter.
     * @private
     */
    _apply_defaults() {
        const defaults = this.get_default_config();
        this._config = JSON.parse(JSON.stringify(defaults));
    }

    /**
     * Check if a value is empty.
     * @private
     */
    _is_empty(value) {
        if (value === null || value === undefined) return true;
        if (typeof value === 'string' && value.trim() === '') return true;
        if (Array.isArray(value) && value.length === 0) return true;
        return false;
    }

    /**
     * Get value at dot-separated path.
     * @private
     */
    _get_path(obj, path) {
        if (!path) return obj;
        const parts = path.split('.');
        let current = obj;

        for (const part of parts) {
            if (current === null || current === undefined) return undefined;
            current = current[part];
        }

        return current;
    }

    /**
     * Set value at dot-separated path.
     * @private
     */
    _set_path(obj, path, value) {
        const parts = path.split('.');
        let current = obj;

        for (let i = 0; i < parts.length - 1; i++) {
            const part = parts[i];
            if (current[part] === undefined) {
                // Create intermediate object or array
                current[part] = isNaN(parts[i + 1]) ? {} : [];
            }
            current = current[part];
        }

        current[parts[parts.length - 1]] = value;
    }

    /**
     * Deep merge objects.
     * @private
     */
    _deep_merge(target, source) {
        const result = JSON.parse(JSON.stringify(target));

        for (const key in source) {
            if (source.hasOwnProperty(key)) {
                if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                    result[key] = this._deep_merge(result[key] || {}, source[key]);
                } else {
                    result[key] = source[key];
                }
            }
        }

        return result;
    }

    /**
     * Destroy and clear all references.
     */
    destroy() {
        this._config = null;
        this._errors = null;
        this.adapter = null;
        this.on_change = null;
    }
};
