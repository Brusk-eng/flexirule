/**
 * FlexiRule Table Row
 *
 * Manages a single row in FlexiTable including:
 * - Cell control instantiation and destruction
 * - Variant column switching
 * - Row-level change propagation
 *
 * Each row owns its cell controls and is responsible for cleanup.
 */

frappe.provide("flexirule");

flexirule.FlexiTableRow = class FlexiTableRow {
    /**
     * Create a table row handler.
     *
     * @param {Object} opts - Options
     * @param {Object} opts.table - Parent FlexiTable instance
     * @param {Object} opts.row_data - Row data object
     * @param {number} opts.row_idx - Row index in table
     * @param {Array} opts.columns - Normalized column definitions
     * @param {Function} opts.on_change - Change callback (fieldname, value, row_idx)
     * @param {Function} opts.on_delete - Delete callback (row_idx)
     */
    constructor(opts) {
        this.table = opts.table;
        this.row_data = opts.row_data || {};
        this.row_idx = opts.row_idx;
        this.columns = opts.columns || [];
        this.on_change = opts.on_change;
        this.on_delete = opts.on_delete;

        // Cell control storage: { fieldname: control }
        this.cell_controls = {};

        // Variant keys for change detection: { fieldname: 'fieldtype:options' }
        this.variant_keys = {};

        // DOM references
        this.$row = null;
        this.cells = {}; // { fieldname: $td }

        // Dependency context
        this.context = opts.context || {};
    }

    /**
     * Render the row into the table body.
     *
     * @param {jQuery} $tbody - Table body element
     */
    render($tbody) {
        this.$row = flexirule.utils.dom.create_body_row({ row_idx: this.row_idx });

        // Create cells for each column
        this.columns.forEach(col => {
            const $td = flexirule.utils.dom.create_cell({ fieldname: col.fieldname });
            this.cells[col.fieldname] = $td;
            this.$row.append($td);

            // Render control or widget
            this._render_cell(col, $td);
        });

        // Add actions cell (delete button)
        const $actions_td = $('<td class="flexi-table-actions">');
        const $delete_btn = $(`<button class="btn btn-xs btn-danger" title="${__('Delete')}">`)
            .html(frappe.utils.icon('delete'))
            .on('click', () => {
                if (this.on_delete) {
                    this.on_delete(this.row_idx);
                }
            });
        $actions_td.append($delete_btn);
        this.$row.append($actions_td);

        $tbody.append(this.$row);
    }

    /**
     * Render a single cell.
     * @private
     */
    _render_cell(column, $td) {
        // Resolve variant for this row
        const df = flexirule.FlexiTableSchema.resolve_variant(column, this.row_data, this.context);
        const variant_key = flexirule.FlexiTableSchema.get_variant_key(df);

        // Store for change detection
        this.variant_keys[column.fieldname] = variant_key;

        // Check if column has custom render function (widget)
        if (column.render && typeof column.render === 'function') {
            this._render_widget(column, $td, df);
            return;
        }

        // Create Frappe control
        const control = flexirule.ControlFactory.create_cell_control({
            parent: $td,
            df: df,
            row: this.row_data,
            row_idx: this.row_idx,
            on_change: (fieldname, value, ctrl, idx) => {
                // Update row data
                this.row_data[fieldname] = value;

                // Check for adapter-level onchange
                if (df.onchange && typeof df.onchange === 'function') {
                    df.onchange(value, this.row_data, this._get_adapter_context());
                }

                // Check if variant needs to change
                this._check_variant_changes();

                // Refresh the row to show side-effects in OTHER cells
                this.refresh();

                // Propagate change
                if (this.on_change) {
                    this.on_change(fieldname, value, this.row_idx);
                }
            },
        });

        this.cell_controls[column.fieldname] = control;
    }

    /**
     * Render a custom widget in a cell.
     * @private
     */
    _render_widget(column, $td, df) {
        const widget = column.render({
            parent: $td.get(0),
            df: df,
            row: this.row_data,
            row_idx: this.row_idx,
            on_change: (fieldname, value) => {
                this.row_data[fieldname] = value;
                this._check_variant_changes();
                if (this.on_change) {
                    this.on_change(fieldname, value, this.row_idx);
                }
            },
            context: this.context,
        });

        // MUST call render on the widget
        widget.render();

        // Store widget with control-like interface
        this.cell_controls[column.fieldname] = widget;
    }

    /**
     * Check if any variant columns need to be re-rendered.
     * @private
     */
    _check_variant_changes() {
        this.columns.forEach(col => {
            if (!flexirule.FlexiTableSchema.has_variants(col)) return;

            const new_df = flexirule.FlexiTableSchema.resolve_variant(col, this.row_data, this.context);
            const new_key = flexirule.FlexiTableSchema.get_variant_key(new_df);
            const old_key = this.variant_keys[col.fieldname];

            if (new_key !== old_key) {
                // Variant changed - destroy old control and create new one
                this._destroy_cell_control(col.fieldname);
                this.cells[col.fieldname].empty();
                this._render_cell(col, this.cells[col.fieldname]);
            }
        });
    }

    /**
     * Destroy a single cell control.
     * @private
     */
    _destroy_cell_control(fieldname) {
        const control = this.cell_controls[fieldname];
        if (!control) return;

        if (control.destroy && typeof control.destroy === 'function') {
            // Widget with destroy method
            control.destroy();
        } else {
            // Frappe control
            flexirule.ControlFactory.destroy_control(control);
        }

        delete this.cell_controls[fieldname];
        delete this.variant_keys[fieldname];
    }

    /**
     * Refresh all controls with current row data.
     */
    refresh() {
        // Check for variant changes first
        this._check_variant_changes();

        // Refresh each control
        for (const fieldname in this.cell_controls) {
            const control = this.cell_controls[fieldname];
            const value = this.row_data[fieldname];

            if (control.refresh && typeof control.refresh === 'function') {
                // Widget
                control.refresh({ row: this.row_data, context: this.context });
            } else if (control.set_value) {
                // Frappe control
                control.set_value(value);
            }
        }
    }

    /**
     * Update row data.
     *
     * @param {Object} data - New row data
     */
    set_data(data) {
        this.row_data = data;
        this.refresh();
    }

    /**
     * Update row index (after reordering).
     *
     * @param {number} idx - New index
     */
    set_idx(idx) {
        this.row_idx = idx;
        this.$row.attr('data-row-idx', idx);

        // Update control references
        for (const fieldname in this.cell_controls) {
            const control = this.cell_controls[fieldname];
            if (control._flexirule_row_idx !== undefined) {
                control._flexirule_row_idx = idx;
            }
        }
    }

    /**
     * Get controls for dependency evaluation.
     *
     * @returns {Array} - Array of controls
     */
    get_controls() {
        return Object.values(this.cell_controls).filter(c => c && c.df);
    }

    /**
     * Destroy the row and all its controls.
     */
    destroy() {
        // Destroy all cell controls
        for (const fieldname in this.cell_controls) {
            this._destroy_cell_control(fieldname);
        }

        // Remove DOM
        if (this.$row) {
            this.$row.remove();
            this.$row = null;
        }

        // Clear references
        this.cells = {};
        this.cell_controls = {};
        this.variant_keys = {};
        this.row_data = null;
        this.table = null;
    }

    /**
     * Get context object for adapter callbacks within a row.
     * @private
     */
    _get_adapter_context() {
        return Object.assign({}, this.context, {
            doc: this.row_data, // In a row, 'doc' usually refers to the row itself
            row: this.row_data,
            update_field: (fieldname, value) => {
                this.row_data[fieldname] = value;
                this.refresh();
                if (this.on_change) {
                    this.on_change(fieldname, value, this.row_idx);
                }
            },
            refresh: () => this.refresh(),
        });
    }
};
