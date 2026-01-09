/**
 * FlexiRule Dependency Engine
 *
 * Evaluates depends_on, mandatory_depends_on, and read_only_depends_on
 * expressions for controls and updates their state accordingly.
 *
 * This replaces the form.ScriptManager dependency handling for our custom runtime.
 */

frappe.provide("flexirule");

flexirule.DependencyEngine = class DependencyEngine {
	/**
	 * Create a dependency engine.
	 *
	 * @param {Object} opts - Options
	 * @param {Object} opts.doc - Main document object
	 * @param {Object} opts.parent - Parent document (optional)
	 */
	constructor(opts = {}) {
		this.doc = opts.doc || {};
		this.parent = opts.parent || {};
		this.controls = [];
	}

	/**
	 * Register a control for dependency tracking.
	 *
	 * @param {Object} control - Frappe control instance
	 */
	register_control(control) {
		if (control && !this.controls.includes(control)) {
			this.controls.push(control);
		}
	}

	/**
	 * Unregister a control from dependency tracking.
	 *
	 * @param {Object} control - Frappe control instance
	 */
	unregister_control(control) {
		const idx = this.controls.indexOf(control);
		if (idx !== -1) {
			this.controls.splice(idx, 1);
		}
	}

	/**
	 * Clear all registered controls.
	 */
	clear_controls() {
		this.controls = [];
	}

	/**
	 * Update the document context.
	 *
	 * @param {Object} doc - New document values
	 */
	set_doc(doc) {
		this.doc = doc || {};
	}

	/**
	 * Evaluate dependencies for all registered controls.
	 *
	 * @param {Object} context_override - Optional context override { doc, parent, row }
	 */
	evaluate_all(context_override = {}) {
		const context = {
			doc: context_override.doc || this.doc,
			parent: context_override.parent || this.parent,
			row: context_override.row || null,
		};

		this.controls.forEach((control) => {
			this.evaluate_control(control, context);
		});
	}

	/**
	 * Evaluate dependencies for a single control.
	 *
	 * @param {Object} control - Frappe control instance
	 * @param {Object} context - Evaluation context { doc, parent, row }
	 */
	evaluate_control(control, context) {
		if (!control || !control.df) return;

		const df = control.df;
		const props = {};

		// Evaluate depends_on (visibility)
		if (df.depends_on) {
			const visible = flexirule.utils.safe_eval(df.depends_on, context);
			props.hidden = visible ? 0 : 1;
		}

		// Evaluate mandatory_depends_on
		if (df.mandatory_depends_on) {
			const mandatory = flexirule.utils.safe_eval(df.mandatory_depends_on, context);
			props.reqd = mandatory ? 1 : 0;
		}

		// Evaluate read_only_depends_on
		if (df.read_only_depends_on) {
			const readonly = flexirule.utils.safe_eval(df.read_only_depends_on, context);
			props.read_only = readonly ? 1 : 0;
		}

		// Apply property changes
		if (Object.keys(props).length > 0) {
			flexirule.ControlFactory.update_control_props(control, props);
		}
	}

	/**
	 * Evaluate dependencies for a specific row in a table.
	 *
	 * @param {Array} row_controls - Array of controls for the row
	 * @param {Object} row - Row data object
	 */
	evaluate_row(row_controls, row) {
		const context = {
			doc: this.doc,
			parent: this.parent,
			row: row,
		};

		row_controls.forEach((control) => {
			this.evaluate_control(control, context);
		});
	}

	/**
	 * Create a row-level evaluator function for use in FlexiTable.
	 *
	 * @param {Object} parent_doc - Parent document context
	 * @returns {Function} - Evaluator function(row_controls, row)
	 */
	create_row_evaluator(parent_doc) {
		return (row_controls, row) => {
			const context = {
				doc: parent_doc,
				parent: this.parent,
				row: row,
			};

			row_controls.forEach((control) => {
				this.evaluate_control(control, context);
			});
		};
	}

	/**
	 * Destroy the engine and clear all references.
	 */
	destroy() {
		this.controls = [];
		this.doc = null;
		this.parent = null;
	}
};
