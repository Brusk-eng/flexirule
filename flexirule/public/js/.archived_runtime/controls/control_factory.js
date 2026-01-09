/**
 * FlexiRule Control Factory
 *
 * Wraps frappe.ui.form.make_control for consistent control instantiation.
 * Handles both standard form controls and table cell controls.
 *
 * All controls created through this factory follow Frappe patterns
 * and can be cleanly destroyed.
 */

flexirule.ControlFactory = {};

/**
 * Create a standard Frappe control.
 *
 * @param {Object} opts - Control options
 * @param {HTMLElement|jQuery} opts.parent - DOM element to append control to
 * @param {Object} opts.df - DocField definition
 * @param {Object} opts.doc - Document object for value binding
 * @param {Function} opts.on_change - Change callback
 * @param {Object} opts.context - Additional context for evaluations
 * @returns {Object} - Frappe control instance
 */
flexirule.ControlFactory.create_control = function (opts) {
	const { parent, df, doc, on_change, context } = opts;

	// Clone df to avoid mutating the original
	const field_df = Object.assign({}, df);

	// Attach change handler
	if (on_change) {
		field_df.onchange = function () {
			// `this` is the control instance
			const value = this.get_value();
			on_change(field_df.fieldname, value, this);
		};
	}

	// Create control using Frappe factory
	const control = frappe.ui.form.make_control({
		parent: parent instanceof jQuery ? parent.get(0) : parent,
		df: field_df,
		doc: doc || {},
		only_input: false,
		render_input: true,
	});

	// Store reference to context for dependency evaluation
	control._flexirule_context = context || {};

	// Ensure control is refreshed to apply initial state
	if (control.refresh) {
		control.refresh();
	}

	return control;
};

/**
 * Create a table cell control (minimal wrapper, input only).
 *
 * @param {Object} opts - Control options
 * @param {HTMLElement|jQuery} opts.parent - Cell element
 * @param {Object} opts.df - DocField definition
 * @param {Object} opts.row - Row data object (acts as doc)
 * @param {Function} opts.on_change - Change callback (fieldname, value, control)
 * @param {number} opts.row_idx - Row index in table
 * @returns {Object} - Frappe control instance
 */
flexirule.ControlFactory.create_cell_control = function (opts) {
	const { parent, df, row, on_change, row_idx } = opts;

	// Clone df
	const field_df = Object.assign({}, df);

	// Attach change handler
	if (on_change) {
		field_df.onchange = function () {
			const value = this.get_value();
			on_change(field_df.fieldname, value, this, row_idx);
		};
	}

	// Create control with only_input for table cells
	const control = frappe.ui.form.make_control({
		parent: parent instanceof jQuery ? parent.get(0) : parent,
		df: field_df,
		doc: row || {},
		only_input: true, // No label/wrapper for table cells
		render_input: true,
	});

	// Store row reference
	control._flexirule_row = row;
	control._flexirule_row_idx = row_idx;

	// Set initial value if present in row
	if (row && row[field_df.fieldname] !== undefined) {
		control.set_value(row[field_df.fieldname]);
	}

	// Refresh to apply state
	if (control.refresh) {
		control.refresh();
	}

	return control;
};

/**
 * Destroy a control and clean up its DOM.
 *
 * @param {Object} control - Frappe control instance
 */
flexirule.ControlFactory.destroy_control = function (control) {
	if (!control) return;

	// Remove DOM wrapper
	if (control.$wrapper) {
		control.$wrapper.remove();
	} else if (control.wrapper) {
		$(control.wrapper).remove();
	}

	// Clear references
	control._flexirule_context = null;
	control._flexirule_row = null;
};

/**
 * Refresh a control with new doc/row values.
 *
 * @param {Object} control - Frappe control instance
 * @param {Object} doc - New document values
 */
flexirule.ControlFactory.refresh_control = function (control, doc) {
	if (!control) return;

	// Update doc reference
	if (doc) {
		control.doc = doc;

		// Update value from doc
		const fieldname = control.df.fieldname;
		if (doc[fieldname] !== undefined) {
			control.set_value(doc[fieldname]);
		}
	}

	// Refresh display state
	if (control.refresh) {
		control.refresh();
	}
};

/**
 * Update control df properties and refresh.
 * Used by dependency engine to toggle hidden/readonly/reqd.
 *
 * @param {Object} control - Frappe control instance
 * @param {Object} props - Properties to update { hidden, read_only, reqd }
 */
flexirule.ControlFactory.update_control_props = function (control, props) {
	if (!control || !control.df) return;

	let needs_refresh = false;

	if (props.hasOwnProperty("hidden")) {
		if (control.df.hidden !== props.hidden) {
			control.df.hidden = props.hidden;
			needs_refresh = true;
		}
	}

	if (props.hasOwnProperty("read_only")) {
		if (control.df.read_only !== props.read_only) {
			control.df.read_only = props.read_only;
			needs_refresh = true;
		}
	}

	if (props.hasOwnProperty("reqd")) {
		if (control.df.reqd !== props.reqd) {
			control.df.reqd = props.reqd;
			needs_refresh = true;
		}
	}

	if (needs_refresh && control.refresh) {
		control.refresh();
	}
};
