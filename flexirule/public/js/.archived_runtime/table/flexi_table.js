/**
 * FlexiRule FlexiTable
 *
 * A dynamic table renderer that uses Frappe controls per cell.
 * Supports variant columns where control type changes based on row state.
 *
 * NOT frappe.ui.form.Grid - this is a standalone table renderer
 * without frm dependency.
 */

frappe.provide("flexirule");

flexirule.FlexiTable = class FlexiTable {
	/**
	 * Create a FlexiTable.
	 *
	 * @param {Object} opts - Options
	 * @param {HTMLElement|jQuery} opts.parent - Container element
	 * @param {Object} opts.schema - Table schema with columns
	 * @param {Object} opts.model - Model with rows array
	 * @param {Function} opts.on_change - Change callback (action, data)
	 * @param {Object} opts.context - Evaluation context { doc, parent }
	 */
	constructor(opts) {
		this.parent = opts.parent instanceof jQuery ? opts.parent.get(0) : opts.parent;
		this.$parent = $(this.parent);
		this.schema = opts.schema || {};
		this.model = opts.model || { rows: [] };
		this.on_change = opts.on_change;
		this.context = opts.context || {};

		// Normalize columns
		this.columns = flexirule.FlexiTableSchema.normalize_columns(this.schema.columns || []);

		// Row handlers
		this.rows = [];

		// DOM references
		this.$wrapper = null;
		this.$table = null;
		this.$thead = null;
		this.$tbody = null;
		this.$add_btn = null;

		// Dependency engine for row-level evaluation
		this.dependency_engine = new flexirule.DependencyEngine({
			doc: this.context.doc || {},
			parent: this.context.parent || {},
		});
	}

	/**
	 * Render the table into the parent container.
	 */
	render() {
		this._create_wrapper();
		this._create_table();
		this._create_header();
		this._create_add_button();
		this._render_rows();
	}

	/**
	 * Create wrapper element.
	 * @private
	 */
	_create_wrapper() {
		this.$wrapper = $('<div class="flexi-table-wrapper">');
		this.$parent.append(this.$wrapper);
	}

	/**
	 * Create table structure.
	 * @private
	 */
	_create_table() {
		const table_parts = flexirule.utils.dom.create_table({ parent: this.$wrapper });
		this.$table = table_parts.$table;
		this.$thead = table_parts.$thead;
		this.$tbody = table_parts.$tbody;
	}

	/**
	 * Create table header.
	 * @private
	 */
	_create_header() {
		// Filter visible columns
		const visible_columns = this.columns.filter((col) => !col.hidden);

		const $header_row = flexirule.utils.dom.create_header_row(visible_columns, {
			include_actions: true,
		});

		this.$thead.append($header_row);
	}

	/**
	 * Create add row button.
	 * @private
	 */
	_create_add_button() {
		this.$add_btn = $(`<button class="btn btn-xs btn-default flexi-table-add-btn">`)
			.html(`${frappe.utils.icon("add")} ${__("Add Row")}`)
			.on("click", () => this.add_row());

		const $btn_wrapper = $('<div class="flexi-table-footer mt-2">');
		$btn_wrapper.append(this.$add_btn);
		this.$wrapper.append($btn_wrapper);
	}

	/**
	 * Render all rows from model.
	 * @private
	 */
	_render_rows() {
		const rows_data = this.model.rows || [];

		rows_data.forEach((row_data, idx) => {
			this._add_row_handler(row_data, idx);
		});
	}

	/**
	 * Create row handler and render it.
	 * @private
	 */
	_add_row_handler(row_data, idx) {
		const row_handler = new flexirule.FlexiTableRow({
			table: this,
			row_data: row_data,
			row_idx: idx,
			columns: this.columns.filter((col) => !col.hidden),
			context: this.context,
			on_change: (fieldname, value, row_idx) => {
				this._handle_row_change(fieldname, value, row_idx);
				// The Row handler already calls the adapter-level onchange
			},
			on_delete: (row_idx) => {
				this.remove_row(row_idx);
			},
		});

		row_handler.render(this.$tbody);

		// Register controls for dependency tracking
		row_handler.get_controls().forEach((ctrl) => {
			this.dependency_engine.register_control(ctrl);
		});

		this.rows.push(row_handler);
	}

	/**
	 * Handle row value change.
	 * @private
	 */
	_handle_row_change(fieldname, value, row_idx) {
		// Update model
		if (this.model.rows[row_idx]) {
			this.model.rows[row_idx][fieldname] = value;
		}

		// Evaluate dependencies for this row
		const row_handler = this.rows[row_idx];
		if (row_handler) {
			this.dependency_engine.evaluate_row(row_handler.get_controls(), row_handler.row_data);
		}

		// Emit change
		if (this.on_change) {
			this.on_change("row_change", {
				fieldname: fieldname,
				value: value,
				row_idx: row_idx,
				rows: this.model.rows,
			});
		}
	}

	/**
	 * Add a new row to the table.
	 *
	 * @param {Object} initial_data - Initial row data (optional)
	 * @returns {Object} - The new row data
	 */
	add_row(initial_data = {}) {
		// Get defaults from schema
		const defaults = flexirule.FlexiTableSchema.get_column_defaults(this.columns);
		const row_data = Object.assign({}, defaults, initial_data, {
			_idx: this.model.rows.length,
		});

		// Add to model
		this.model.rows.push(row_data);

		// Create row handler
		this._add_row_handler(row_data, this.model.rows.length - 1);

		// Emit change
		if (this.on_change) {
			this.on_change("row_add", {
				row_idx: this.model.rows.length - 1,
				row_data: row_data,
				rows: this.model.rows,
			});
		}

		return row_data;
	}

	/**
	 * Remove a row from the table.
	 *
	 * @param {number} row_idx - Row index to remove
	 */
	remove_row(row_idx) {
		if (row_idx < 0 || row_idx >= this.rows.length) return;

		// Get row handler
		const row_handler = this.rows[row_idx];

		// Unregister controls
		row_handler.get_controls().forEach((ctrl) => {
			this.dependency_engine.unregister_control(ctrl);
		});

		// Destroy row
		row_handler.destroy();

		// Remove from arrays
		this.rows.splice(row_idx, 1);
		this.model.rows.splice(row_idx, 1);

		// Reindex remaining rows
		this.rows.forEach((handler, idx) => {
			handler.set_idx(idx);
			if (this.model.rows[idx]) {
				this.model.rows[idx]._idx = idx;
			}
		});

		// Emit change
		if (this.on_change) {
			this.on_change("row_remove", {
				row_idx: row_idx,
				rows: this.model.rows,
			});
		}
	}

	/**
	 * Get current rows data.
	 *
	 * @returns {Array} - Array of row data objects
	 */
	get_rows() {
		return this.model.rows;
	}

	/**
	 * Set rows data (replaces all rows).
	 *
	 * @param {Array} rows_data - Array of row data
	 */
	set_rows(rows_data) {
		// Destroy existing rows
		this._destroy_all_rows();

		// Update model
		this.model.rows = rows_data || [];

		// Render new rows
		this._render_rows();
	}

	/**
	 * Refresh all rows.
	 */
	refresh() {
		this.rows.forEach((handler) => handler.refresh());

		// Re-evaluate all dependencies
		this.rows.forEach((handler) => {
			this.dependency_engine.evaluate_row(handler.get_controls(), handler.row_data);
		});
	}

	/**
	 * Update context for evaluations.
	 *
	 * @param {Object} context - New context { doc, parent }
	 */
	set_context(context) {
		this.context = context;
		this.dependency_engine.set_doc(context.doc);
		this.dependency_engine.parent = context.parent;

		// Update row contexts
		this.rows.forEach((handler) => {
			handler.context = context;
		});

		this.refresh();
	}

	/**
	 * Destroy all rows.
	 * @private
	 */
	_destroy_all_rows() {
		this.rows.forEach((handler) => {
			handler.get_controls().forEach((ctrl) => {
				this.dependency_engine.unregister_control(ctrl);
			});
			handler.destroy();
		});
		this.rows = [];
	}

	/**
	 * Destroy the table and clean up.
	 */
	destroy() {
		// Destroy all rows
		this._destroy_all_rows();

		// Destroy dependency engine
		this.dependency_engine.destroy();

		// Remove DOM
		if (this.$wrapper) {
			this.$wrapper.remove();
			this.$wrapper = null;
		}

		// Clear references
		this.$table = null;
		this.$thead = null;
		this.$tbody = null;
		this.$add_btn = null;
		this.model = null;
		this.columns = null;
	}
};
