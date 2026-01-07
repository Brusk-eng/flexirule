/**
 * FlexiRule Process Adapter Bridge
 *
 * Bridges existing process adapters (flexirule.processes.*) to the
 * new ConfigurableAction runtime API.
 *
 * Existing adapters have:
 *   - get_schema(operation_name, context) -> { fields, title, size }
 *   - get_output_schema(operation_name, config, context)
 *   - operations array with get_config_fields, validate, etc.
 *
 * ConfigurableAction expects:
 *   - get_default_config()
 *   - get_ui_schema(config)
 *   - validate(config)
 */

frappe.provide("flexirule.adapters");

flexirule.adapters = flexirule.adapters || {};

/**
 * Create a ConfigurableAction-compatible adapter from an existing process adapter.
 *
 * @param {string} process_name - Name of the process (e.g., 'Deduplication')
 * @param {string} operation_name - Name of the operation (e.g., 'find_similar_records')
 * @param {Object} context - Context with document_type, config, etc.
 * @returns {Object} - Adapter compatible with ConfigurableAction
 */
flexirule.adapters.create_from_process = function (process_name, operation_name, context = {}) {
    const process_adapter = flexirule.processes[process_name];
    if (!process_adapter) {
        console.warn(`[FlexiRule] Process adapter not found: ${process_name}`);
        return null;
    }

    const operation = process_adapter.get_operation(operation_name);
    if (!operation) {
        console.warn(`[FlexiRule] Operation not found: ${operation_name} in ${process_name}`);
        return null;
    }

    return {
        process_name: process_name,
        operation_name: operation_name,
        context: context,
        operation: operation,

        /**
         * Get default configuration values.
         */
        get_default_config() {
            const defaults = {};
            const schema = this.get_ui_schema({});

            // Extract defaults from fields
            schema.fields?.forEach(field => {
                if (field.default !== undefined) {
                    defaults[field.fieldname] = field.default;
                }
            });

            // Extract defaults from table columns
            schema.tables?.forEach(table => {
                defaults[table.fieldname] = [];
            });

            return defaults;
        },

        /**
         * Get UI schema for ConfigurableAction.
         * Transforms process schema to runtime schema format.
         */
        get_ui_schema(config) {
            const raw_fields = typeof this.operation.get_config_fields === 'function'
                ? this.operation.get_config_fields(this.context)
                : [];

            return this._normalize_schema(raw_fields, config);
        },

        /**
         * Validate configuration.
         */
        validate(config) {
            const errors = [];

            if (typeof this.operation.validate === 'function') {
                const msg = this.operation.validate(config, this.context);
                if (msg) {
                    errors.push({ fieldname: '_general', message: msg });
                }
            }

            return errors;
        },

        /**
         * Normalize process schema to runtime format.
         * @private
         */
        _normalize_schema(raw_fields, config) {
            const fields = [];
            const tables = [];

            raw_fields.forEach(field => {
                // Skip layout fields
                if (['Section Break', 'Column Break'].includes(field.fieldtype)) {
                    return;
                }

                // Skip HTML fields (help text)
                if (field.fieldtype === 'HTML') {
                    return;
                }

                // Handle Table fields
                if (field.fieldtype === 'Table') {
                    tables.push({
                        fieldname: field.fieldname,
                        label: field.label,
                        reqd: field.reqd || 0,
                        columns: this._normalize_columns(field.fields || [], config),
                    });
                    return;
                }

                // Regular field
                fields.push(this._normalize_field(field, config));
            });

            return { fields, tables };
        },

        /**
         * Normalize a single field definition.
         * @private
         */
        _normalize_field(field, config) {
            const normalized = {
                fieldname: field.fieldname,
                label: field.label || frappe.unscrub(field.fieldname || ''),
                fieldtype: this._map_fieldtype(field.fieldtype),
                options: this._resolve_options(field, config),
                reqd: field.reqd || 0,
                read_only: field.read_only || 0,
                hidden: field.hidden || 0,
                default: field.default,
                depends_on: field.depends_on || '',
                mandatory_depends_on: field.mandatory_depends_on || '',
                read_only_depends_on: field.read_only_depends_on || '',
                description: field.description || '',
            };

            // Handle custom fieldtypes that need widgets
            if (field.fieldtype === 'DocField') {
                normalized.render = (opts) => new flexirule.DocFieldWidget(opts);
                normalized.fieldtype = 'Data';
            }

            if (field.fieldtype === 'MultiDocField') {
                normalized.render = (opts) => new flexirule.MultiDocFieldWidget(opts);
                normalized.fieldtype = 'Data';
            }

            // Also support string-based widget lookup in UIRuntime
            if (field.fieldtype === 'DocField') normalized.widget = 'DocFieldWidget';
            if (field.fieldtype === 'MultiDocField') normalized.widget = 'MultiDocFieldWidget';

            // Preserve onchange handler
            if (field.onchange) {
                normalized.onchange = field.onchange;
            }

            // Preserve get_options for dynamic options
            if (field.get_options) {
                normalized.get_options = field.get_options;
            }

            return normalized;
        },

        /**
         * Normalize table columns.
         * @private
         */
        _normalize_columns(columns, config) {
            return columns.map(col => {
                const normalized = this._normalize_field(col, config);

                // Add table-specific properties
                normalized.in_list_view = col.in_list_view !== false;
                normalized.columns = col.columns || 2;

                // Check for variant column patterns
                if (col.depends_on && this._is_fieldtype_variant(col)) {
                    // Convert depends_on that hides/shows fields into variants
                    normalized.variants = this._extract_variants(col);
                }

                return normalized;
            });
        },

        /**
         * Map custom fieldtypes to standard or widget types.
         * @private
         */
        _map_fieldtype(fieldtype) {
            const mapping = {
                'DocField': 'Data', // Will use FieldSelector widget
                'MultiDocField': 'Data', // Will use MultiFieldSelector widget
                // Standard types pass through
            };
            return mapping[fieldtype] || fieldtype;
        },

        /**
         * Resolve options for a field.
         * @private
         */
        _resolve_options(field, config) {
            if (typeof field.options === 'function') {
                return field.options(config, this.context);
            }

            // Handle options referencing parent document
            if (typeof field.options === 'string' && field.options.startsWith('parent.')) {
                const parent_field = field.options.replace('parent.', '');
                return this.context[parent_field] || '';
            }

            return field.options || '';
        },

        /**
         * Check if field definition suggests variant behavior.
         * @private
         */
        _is_fieldtype_variant(col) {
            // If depends_on references algorithm or mode-like fields, might be variant
            const depends_on = col.depends_on || '';
            return depends_on.includes('algorithm') || depends_on.includes('mode');
        },

        /**
         * Extract variant definitions from depends_on pattern.
         * @private
         */
        _extract_variants(col) {
            // This is a simplified extraction - in practice you'd parse the expression
            // For now, we don't create variants automatically; the table handles depends_on
            return [];
        },
    };
};

/**
 * Registry of adapter factories by action type.
 */
flexirule.adapters.registry = {
    /**
     * Get adapter for a process action.
     *
     * @param {Object} action - Action definition with action_type, process_name, operation_name
     * @param {Object} context - Context with document_type, etc.
     * @returns {Object} - ConfigurableAction-compatible adapter
     */
    get_adapter(action, context) {
        if (action.action_type !== 'process') {
            console.warn(`[FlexiRule] Unsupported action type: ${action.action_type}`);
            return null;
        }

        return flexirule.adapters.create_from_process(
            action.process_name,
            action.operation_name,
            context
        );
    }
};
