/**
 * FlexiRule UI Runtime
 *
 * Renders UI from ConfigurableAction schema using wrapped Frappe controls.
 * Handles field instantiation, event wiring, and dependency evaluation.
 *
 * The UI runtime consumes schema blindly - it does not contain
 * business logic specific to any action type.
 */

frappe.provide("flexirule");

flexirule.UIRuntime = class UIRuntime {
    /**
     * Create a UI Runtime.
     *
     * @param {Object} opts - Options
     * @param {HTMLElement|jQuery} opts.parent - Container element
     * @param {Object} opts.configurable_action - ConfigurableAction instance
     * @param {Object} opts.context - Additional context { doc, parent }
     */
    constructor(opts) {
        this.parent = opts.parent instanceof jQuery ? opts.parent.get(0) : opts.parent;
        this.$parent = $(this.parent);
        this.action = opts.configurable_action;
        this.context = opts.context || {};

        // Controls storage: { fieldname: control }
        this.controls = {};

        // Tables storage: { fieldname: FlexiTable }
        this.tables = {};

        // Widgets storage: { fieldname: widget }
        this.widgets = {};

        // DOM reference
        this.$wrapper = null;

        // Dependency engine
        this.dependency_engine = new flexirule.DependencyEngine({
            doc: this.action.get_config(),
            parent: this.context.parent || {},
        });
    }

    /**
     * Render the UI from schema.
     */
    render() {
        this._create_wrapper();

        const schema = this.action.get_ui_schema();
        const config = this.action.get_config();

        // Render regular fields
        if (schema.fields && schema.fields.length > 0) {
            this._render_fields(schema.fields, config);
        }

        // Render tables
        if (schema.tables && schema.tables.length > 0) {
            this._render_tables(schema.tables, config);
        }

        // Initial dependency evaluation
        this.dependency_engine.evaluate_all();
    }

    /**
     * Create wrapper element.
     * @private
     */
    _create_wrapper() {
        this.$wrapper = $('<div class="flexi-ui-runtime">');
        this.$parent.append(this.$wrapper);
    }

    /**
     * Render standard fields.
     * @private
     */
    _render_fields(fields, config) {
        const $fields_container = $('<div class="flexi-fields-container">');
        this.$wrapper.append($fields_container);

        fields.forEach(field_def => {
            if (field_def.hidden) return;

            const $field_wrapper = $('<div class="flexi-field-wrapper mb-3">');
            $fields_container.append($field_wrapper);

            // Check for custom widget
            if (field_def.widget) {
                this._render_widget(field_def, $field_wrapper, config);
                return;
            }

            // Create Frappe control
            const control = flexirule.ControlFactory.create_control({
                parent: $field_wrapper,
                df: Object.assign({}, field_def, {
                    // Ensure we don't have stale onchange
                    onchange: null,
                }),
                doc: config,
                on_change: (fieldname, value, ctrl) => {
                    this._handle_field_change(fieldname, value);
                    // Execute adapter-level onchange if it exists
                    if (field_def.onchange && typeof field_def.onchange === 'function') {
                        field_def.onchange(value, config, this._get_adapter_context());
                    }
                },
                context: this._get_adapter_context(),
            });

            // Set initial value
            if (config[field_def.fieldname] !== undefined) {
                control.set_value(config[field_def.fieldname]);
            }

            this.controls[field_def.fieldname] = control;
            this.dependency_engine.register_control(control);
        });
    }

    /**
     * Render a custom widget.
     * @private
     */
    _render_widget(field_def, $container, config) {
        const widget_class = field_def.widget;
        const Widget = typeof widget_class === 'string'
            ? this._resolve_widget_class(widget_class)
            : widget_class;

        if (!Widget) {
            console.warn(`[FlexiRule] Unknown widget: ${widget_class}`);
            return;
        }

        const widget = new Widget({
            parent: $container,
            df: field_def,
            value: config[field_def.fieldname],
            on_change: (value) => {
                this._handle_field_change(field_def.fieldname, value);
            },
            context: Object.assign({}, this.context, {
                doc: config,
            }),
        });

        widget.render();
        this.widgets[field_def.fieldname] = widget;
    }

    /**
     * Resolve widget class by name.
     * @private
     */
    _resolve_widget_class(name) {
        // Check in flexirule namespace
        if (flexirule[name]) {
            return flexirule[name];
        }

        // Check in global
        if (window[name]) {
            return window[name];
        }

        return null;
    }

    /**
     * Render table fields.
     * @private
     */
    _render_tables(tables, config) {
        tables.forEach(table_def => {
            const $table_wrapper = $('<div class="flexi-table-wrapper-outer mb-3">');

            // Add label
            if (table_def.label) {
                $('<label class="control-label">')
                    .text(__(table_def.label))
                    .appendTo($table_wrapper);
            }

            this.$wrapper.append($table_wrapper);

            // Create FlexiTable
            const table = new flexirule.FlexiTable({
                parent: $table_wrapper,
                schema: {
                    columns: table_def.columns || [],
                },
                model: {
                    rows: config[table_def.fieldname] || [],
                },
                context: Object.assign({}, this.context, {
                    doc: config,
                }),
                on_change: (action, data) => {
                    this._handle_table_change(table_def.fieldname, action, data);
                },
            });

            table.render();
            this.tables[table_def.fieldname] = table;
        });
    }

    /**
     * Handle field value change.
     * @private
     */
    _handle_field_change(fieldname, value) {
        // Update ConfigurableAction
        this.action.set_value(fieldname, value);

        // Update dependency context
        this.dependency_engine.set_doc(this.action.get_config());

        // Re-evaluate dependencies
        this.dependency_engine.evaluate_all();

        // Refresh everything to show side-effects
        this.refresh();
    }

    /**
     * Get context object for adapter callbacks.
     * @private
     */
    _get_adapter_context() {
        return Object.assign({}, this.context, {
            doc: this.action.get_config(),
            update_field: (fieldname, value) => {
                this._handle_field_change(fieldname, value);
            },
            refresh: () => this.refresh(),
        });
    }

    /**
     * Handle table change.
     * @private
     */
    _handle_table_change(table_fieldname, action, data) {
        // Update ConfigurableAction
        this.action.set_value(table_fieldname, data.rows);

        // Update dependency context
        this.dependency_engine.set_doc(this.action.get_config());
    }

    /**
     * Refresh all tables with current context.
     * @private
     */
    _refresh_tables() {
        const config = this.action.get_config();

        for (const fieldname in this.tables) {
            const table = this.tables[fieldname];
            table.set_context({
                doc: config,
                parent: this.context.parent || {},
            });
        }
    }

    /**
     * Get a specific control by fieldname.
     *
     * @param {string} fieldname - Field name
     * @returns {Object|null} - Control or null
     */
    get_control(fieldname) {
        return this.controls[fieldname] || this.widgets[fieldname] || null;
    }

    /**
     * Get a specific table by fieldname.
     *
     * @param {string} fieldname - Table field name
     * @returns {FlexiTable|null}
     */
    get_table(fieldname) {
        return this.tables[fieldname] || null;
    }

    /**
     * Refresh all controls and tables with current config.
     */
    refresh() {
        const config = this.action.get_config();

        // Refresh controls
        for (const fieldname in this.controls) {
            const control = this.controls[fieldname];
            const value = config[fieldname];

            if (value !== undefined) {
                control.set_value(value);
            }
        }

        // Refresh widgets
        for (const fieldname in this.widgets) {
            const widget = this.widgets[fieldname];
            if (widget.refresh) {
                widget.refresh({
                    value: config[fieldname],
                    context: { doc: config },
                });
            }
        }

        // Refresh tables
        for (const fieldname in this.tables) {
            const table = this.tables[fieldname];
            table.set_rows(config[fieldname] || []);
        }

        // Re-evaluate dependencies
        this.dependency_engine.set_doc(config);
        this.dependency_engine.evaluate_all();
    }

    /**
     * Validate all inputs.
     *
     * @returns {Object} - { valid: boolean, errors: Array }
     */
    validate() {
        return this.action.validate();
    }

    /**
     * Destroy the runtime and clean up.
     */
    destroy() {
        // Destroy controls
        for (const fieldname in this.controls) {
            flexirule.ControlFactory.destroy_control(this.controls[fieldname]);
        }
        this.controls = {};

        // Destroy widgets
        for (const fieldname in this.widgets) {
            const widget = this.widgets[fieldname];
            if (widget.destroy) {
                widget.destroy();
            }
        }
        this.widgets = {};

        // Destroy tables
        for (const fieldname in this.tables) {
            this.tables[fieldname].destroy();
        }
        this.tables = {};

        // Destroy dependency engine
        this.dependency_engine.destroy();

        // Remove DOM
        if (this.$wrapper) {
            this.$wrapper.remove();
            this.$wrapper = null;
        }
    }
};
