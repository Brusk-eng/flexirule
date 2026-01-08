/**
 * Enhanced Grid Controller that extends Frappe's grid functionality
 * with custom cell rendering capabilities
 */
frappe.provide("flexirule.grid");

flexirule.grid.EnhancedGridController = class EnhancedGridController {
    constructor(grid, schema, context) {
        this.grid = grid;
        this.schema = schema;
        this.context = context;
        this.custom_renderers = new Map(); // fieldname -> renderer function
        this.cell_hooks = new Map(); // fieldname -> hooks object
        this.dependency_engine = new flexirule.DependencyEngine(context);
        
        this._initialize_hooks();
    }

    /**
     * Register a custom renderer for a specific field
     */
    register_custom_renderer(fieldname, renderer) {
        this.custom_renderers.set(fieldname, renderer);
    }

    /**
     * Register hooks for a specific field
     */
    register_hooks(fieldname, hooks) {
        this.cell_hooks.set(fieldname, hooks);
    }

    /**
     * Initialize hooks for the grid
     * @private
     */
    _initialize_hooks() {
        // Hook into row creation
        const original_refresh = this.grid.refresh;
        this.grid.refresh = () => {
            original_refresh.call(this.grid);
            this._enhance_grid();
        };

        // Hook into row addition
        const original_add_row = this.grid.add_new_row;
        this.grid.add_new_row = (idx, scroll_to_row, is_duplicate) => {
            const row = original_add_row.call(this.grid, idx, scroll_to_row, is_duplicate);
            this._enhance_row(row);
            return row;
        };

        // Hook into row refresh
        if (this.grid.grid_rows_by_docname) {
            // Enhance existing rows
            Object.values(this.grid.grid_rows_by_docname).forEach(row => {
                this._enhance_row(row);
            });
        }
    }

    /**
     * Enhance the entire grid with custom functionality
     * @private
     */
    _enhance_grid() {
        if (this.grid.grid_rows_by_docname) {
            Object.values(this.grid.grid_rows_by_docname).forEach(row => {
                this._enhance_row(row);
            });
        }
    }

    /**
     * Enhance a single row with custom renderers and hooks
     * @private
     */
    _enhance_row(row) {
        if (!row || !row.doc) return;

        // Process each field in the row
        this.schema.fields.forEach(field => {
            const fieldname = field.fieldname;
            
            // Apply custom renderer if available
            if (this.custom_renderers.has(fieldname)) {
                const custom_renderer = this.custom_renderers.get(fieldname);
                const cell = this._get_cell_for_field(row, fieldname);
                
                if (cell) {
                    // Clear the cell and render custom content
                    cell.empty();
                    custom_renderer.render(cell, row.doc, this.context);
                }
            }
            
            // Apply hooks if available
            if (this.cell_hooks.has(fieldname)) {
                const hooks = this.cell_hooks.get(fieldname);
                const control = this._get_control_for_field(row, fieldname);
                
                if (control && hooks.on_render) {
                    hooks.on_render(control, row.doc, this.context);
                }
            }
            
            // Apply dependency evaluation for this row
            this.dependency_engine.evaluate_row([row], row.doc);
        });
    }

    /**
     * Get the cell element for a specific field in a row
     * @private
     */
    _get_cell_for_field(row, fieldname) {
        // Try to get the control's wrapper first
        if (row.docfields && row.docfields[fieldname]) {
            const field_control = row.grid_form.fields_dict[fieldname];
            if (field_control && field_control.$wrapper) {
                return field_control.$wrapper;
            }
        }
        
        // Fallback: find by data attribute
        return $(row.row).find(`[data-fieldname="${fieldname}"]`);
    }

    /**
     * Get the control for a specific field in a row
     * @private
     */
    _get_control_for_field(row, fieldname) {
        return row.grid_form?.fields_dict?.[fieldname] || null;
    }

    /**
     * Update context and refresh dependencies
     */
    update_context(new_context) {
        Object.assign(this.context, new_context);
        this.dependency_engine.set_doc(new_context.doc || {});
        
        // Re-evaluate dependencies for all rows
        if (this.grid.grid_rows_by_docname) {
            Object.values(this.grid.grid_rows_by_docname).forEach(row => {
                if (row.doc) {
                    this.dependency_engine.evaluate_row([row], row.doc);
                }
            });
        }
    }
};