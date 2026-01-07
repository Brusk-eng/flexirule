/**
 * FlexiRule Field Selector Widget
 *
 * A custom widget for selecting fields from multiple sources:
 * - DocType fields
 * - Context variables
 *
 * Produces a structured value:
 * [source, doctype_or_context_key, fieldname, fieldtype, options]
 *
 * This follows the same lifecycle contract as Frappe controls:
 * render(), refresh(), destroy()
 */

frappe.provide("flexirule");

flexirule.FieldSelector = class FieldSelector {
    /**
     * Create a FieldSelector widget.
     *
     * @param {Object} opts - Options
     * @param {HTMLElement|jQuery} opts.parent - Container element
     * @param {Object} opts.df - Field definition (for label, reqd etc.)
     * @param {Object} opts.value - Initial value array
     * @param {Function} opts.on_change - Change callback (value)
     * @param {Object} opts.context - Context for options { doctypes: [], context_vars: {} }
     */
    constructor(opts) {
        this.parent = opts.parent instanceof jQuery ? opts.parent : $(opts.parent);
        this.df = opts.df || {};
        this.value = opts.value || null;
        this.on_change = opts.on_change;
        this.context = opts.context || {};

        // DOM references
        this.$wrapper = null;
        this.$source_select = null;
        this.$doctype_area = null;
        this.$field_area = null;

        // Internal controls
        this.source_control = null;
        this.doctype_control = null;
        this.field_input = null;
        this.awesomplete = null;

        // Field options cache
        this.field_options = [];
        this.fields_by_name = {};
    }

    /**
     * Render the widget.
     */
    render() {
        this._create_wrapper();
        this._create_source_select();
        this._create_doctype_select();
        this._create_field_select();

        // Set initial value if provided
        if (this.value) {
            this._set_value_internal(this.value);
        }
    }

    /**
     * Create wrapper element.
     * @private
     */
    _create_wrapper() {
        this.$wrapper = $('<div class="flexi-field-selector">');
        this.$wrapper.css({
            display: 'flex',
            gap: '8px',
            alignItems: 'flex-start',
        });
        this.parent.append(this.$wrapper);
    }

    /**
     * Create source selector (DocType vs Context).
     * @private
     */
    _create_source_select() {
        const $source_container = $('<div class="field-selector-source" style="flex: 0 0 120px;">');

        this.source_control = frappe.ui.form.make_control({
            parent: $source_container.get(0),
            df: {
                fieldtype: 'Select',
                fieldname: '_source',
                options: [
                    { value: 'doctype', label: __('DocType') },
                    { value: 'context', label: __('Context Var') },
                ],
                onchange: () => {
                    this._on_source_change();
                },
            },
            only_input: true,
            render_input: true,
        });

        this.source_control.set_value('doctype');
        this.$wrapper.append($source_container);
    }

    /**
     * Create DocType/context key selector.
     * @private
     */
    _create_doctype_select() {
        this.$doctype_area = $('<div class="field-selector-doctype" style="flex: 0 0 150px;">');

        // Initially render DocType selector
        this._render_doctype_control();

        this.$wrapper.append(this.$doctype_area);
    }

    /**
     * Render DocType link control.
     * @private
     */
    _render_doctype_control() {
        this.$doctype_area.empty();

        const doctypes = this.context.doctypes || [];

        if (doctypes.length > 0) {
            // Use select with provided doctypes
            this.doctype_control = frappe.ui.form.make_control({
                parent: this.$doctype_area.get(0),
                df: {
                    fieldtype: 'Select',
                    fieldname: '_doctype',
                    options: doctypes.map(dt => ({ value: dt, label: __(dt) })),
                    onchange: () => {
                        this._on_doctype_change();
                    },
                },
                only_input: true,
                render_input: true,
            });
        } else {
            // Use Link to DocType
            this.doctype_control = frappe.ui.form.make_control({
                parent: this.$doctype_area.get(0),
                df: {
                    fieldtype: 'Link',
                    fieldname: '_doctype',
                    options: 'DocType',
                    onchange: () => {
                        this._on_doctype_change();
                    },
                },
                only_input: true,
                render_input: true,
            });
        }
    }

    /**
     * Render context variable selector.
     * @private
     */
    _render_context_control() {
        this.$doctype_area.empty();

        const context_vars = this.context.context_vars || {};
        const options = Object.keys(context_vars).map(key => ({
            value: key,
            label: key,
        }));

        this.doctype_control = frappe.ui.form.make_control({
            parent: this.$doctype_area.get(0),
            df: {
                fieldtype: 'Select',
                fieldname: '_context_key',
                options: options,
                onchange: () => {
                    this._on_context_key_change();
                },
            },
            only_input: true,
            render_input: true,
        });
    }

    /**
     * Create field autocomplete.
     * @private
     */
    _create_field_select() {
        this.$field_area = $('<div class="field-selector-field" style="flex: 1;">');

        this.field_input = $('<input class="form-control input-xs" placeholder="' + __('Select Field') + '">')
            .appendTo(this.$field_area);

        this.awesomplete = new Awesomplete(this.field_input.get(0), {
            minChars: 0,
            maxItems: 99,
            autoFirst: true,
            list: [],
            item: (item) => {
                return $(`<li class="filter-field-select"><p>${item.label}</p></li>`)
                    .data('item.autocomplete', item)
                    .get(0);
            },
        });

        this.field_input.on('click', () => {
            this.field_input.select();
            if (this.field_options.length > 0) {
                this.awesomplete.evaluate();
            }
        });

        this.field_input.on('awesomplete-select', (e) => {
            const item = this.awesomplete.get_item(e.originalEvent.text.value);
            this._on_field_select(item);
        });

        this.field_input.on('awesomplete-selectcomplete', (e) => {
            const item = this.awesomplete.get_item(e.originalEvent.text.value);
            this.field_input.val(item.label);
        });

        this.$wrapper.append(this.$field_area);
    }

    /**
     * Handle source change.
     * @private
     */
    _on_source_change() {
        const source = this.source_control.get_value();

        // Clear field
        this.field_input.val('');
        this.field_options = [];
        this.awesomplete.list = [];

        if (source === 'doctype') {
            this._render_doctype_control();
        } else {
            this._render_context_control();
        }
    }

    /**
     * Handle doctype change.
     * @private
     */
    _on_doctype_change() {
        const doctype = this.doctype_control.get_value();
        if (!doctype) {
            this.field_options = [];
            this.awesomplete.list = [];
            return;
        }

        // Load fields for doctype
        frappe.model.with_doctype(doctype, () => {
            this._build_field_options(doctype);
        });
    }

    /**
     * Handle context key change.
     * @private
     */
    _on_context_key_change() {
        const key = this.doctype_control.get_value();
        const context_vars = this.context.context_vars || {};
        const var_def = context_vars[key];

        if (!var_def) {
            this.field_options = [];
            this.awesomplete.list = [];
            return;
        }

        // Build options from context variable definition
        this._build_context_field_options(key, var_def);
    }

    /**
     * Build field options for a DocType.
     * @private
     */
    _build_field_options(doctype) {
        this.field_options = [];
        this.fields_by_name = {};

        const meta = frappe.get_meta(doctype);
        if (!meta) return;

        // Add standard fields
        const std_fields = frappe.model.std_fields.filter(f =>
            !frappe.model.no_value_type.includes(f.fieldtype)
        );

        std_fields.forEach(df => {
            this._add_field_option({
                fieldname: df.fieldname,
                label: __(df.label),
                fieldtype: df.fieldtype,
                options: df.options || doctype,
                parent: doctype,
            });
        });

        // Add doctype fields
        (meta.fields || []).forEach(df => {
            if (frappe.model.no_value_type.includes(df.fieldtype)) return;
            if (df.is_virtual) return;

            this._add_field_option({
                fieldname: df.fieldname,
                label: __(df.label),
                fieldtype: df.fieldtype,
                options: df.options,
                parent: doctype,
            });
        });

        // Update awesomplete
        this.awesomplete.list = this.field_options;
    }

    /**
     * Build options from context variable.
     * @private
     */
    _build_context_field_options(key, var_def) {
        this.field_options = [];
        this.fields_by_name = {};

        // Context var might be an object with field definitions
        if (var_def.fields && Array.isArray(var_def.fields)) {
            var_def.fields.forEach(df => {
                this._add_field_option({
                    fieldname: df.fieldname || df.name,
                    label: __(df.label || df.fieldname || df.name),
                    fieldtype: df.fieldtype || 'Data',
                    options: df.options || '',
                    parent: key,
                });
            });
        } else if (var_def.doctype) {
            // Context var references a doctype
            frappe.model.with_doctype(var_def.doctype, () => {
                this._build_field_options(var_def.doctype);
            });
            return;
        }

        this.awesomplete.list = this.field_options;
    }

    /**
     * Add a field option.
     * @private
     */
    _add_field_option(opts) {
        const option = {
            value: `${opts.parent}.${opts.fieldname}`,
            label: opts.label,
            fieldname: opts.fieldname,
            fieldtype: opts.fieldtype,
            options: opts.options,
            parent: opts.parent,
        };

        this.field_options.push(option);
        this.fields_by_name[opts.fieldname] = option;
    }

    /**
     * Handle field selection.
     * @private
     */
    _on_field_select(item) {
        const source = this.source_control.get_value();
        const doctype_or_key = this.doctype_control.get_value();

        // Build value array
        this.value = [
            source,
            doctype_or_key,
            item.fieldname,
            item.fieldtype,
            item.options || '',
        ];

        if (this.on_change) {
            this.on_change(this.value);
        }
    }

    /**
     * Get current value.
     *
     * @returns {Array|null} - [source, doctype_or_key, fieldname, fieldtype, options]
     */
    get_value() {
        return this.value;
    }

    /**
     * Set value.
     *
     * @param {Array} value - Value array
     */
    set_value(value) {
        this._set_value_internal(value);
    }

    /**
     * Set value internally.
     * @private
     */
    _set_value_internal(value) {
        if (!value || !Array.isArray(value) || value.length < 3) {
            this.value = null;
            return;
        }

        const [source, doctype_or_key, fieldname, fieldtype, options] = value;

        // Set source
        this.source_control.set_value(source);

        // Re-render appropriate control
        if (source === 'doctype') {
            this._render_doctype_control();
        } else {
            this._render_context_control();
        }

        // Set doctype/key
        setTimeout(() => {
            this.doctype_control.set_value(doctype_or_key);

            // Set field after options load
            setTimeout(() => {
                const item = this.fields_by_name[fieldname];
                if (item) {
                    this.field_input.val(item.label);
                } else {
                    this.field_input.val(fieldname);
                }
                this.value = value;
            }, 100);
        }, 50);
    }

    /**
     * Refresh with new context.
     *
     * @param {Object} opts - { context, value }
     */
    refresh(opts = {}) {
        if (opts.context) {
            this.context = opts.context;
        }

        if (opts.value !== undefined) {
            this._set_value_internal(opts.value);
        }
    }

    /**
     * Destroy the widget.
     */
    destroy() {
        // Destroy controls
        if (this.source_control && this.source_control.$wrapper) {
            this.source_control.$wrapper.remove();
        }
        if (this.doctype_control && this.doctype_control.$wrapper) {
            this.doctype_control.$wrapper.remove();
        }

        // Destroy awesomplete
        if (this.awesomplete) {
            this.awesomplete.destroy();
        }

        // Remove DOM
        if (this.$wrapper) {
            this.$wrapper.remove();
        }

        // Clear references
        this.$wrapper = null;
        this.source_control = null;
        this.doctype_control = null;
        this.field_input = null;
        this.awesomplete = null;
        this.field_options = [];
        this.fields_by_name = {};
    }
};
