// Copyright (c) 2026, FlexiRule and contributors
// For license information, please see license.txt

frappe.provide("flexirule.ui");
frappe.provide("flexirule.integration");

/**
 * Factory for creating ConfigurableAction instances.
 * Used by Sidebar.vue to instantiate the runtime for a node.
 */
flexirule.integration.create_configurable_action = function (opts) {
	return new flexirule.ui.ConfigurableAction(opts);
};

// PATCH REMOVED: User requested no global overrides.

/**
 * ConfigurableAction - Runtime Primitive for Process Configuration
 *
 * DESIGN GUARANTEES:
 * 1. Runtime Owns Persistence: schema is immutable, config is the single source of truth.
 * 2. Strict Context: mutations only via ctx.update_field().
 * 3. Passive Fields: fields react to state, never mutate each other directly.
 * 4. Native Frappe Semantics: supports depends_on, mandatory_depends_on, eval scops.
 */
flexirule.ui.ConfigurableAction = class ConfigurableAction {
	constructor(opts) {
		// Options: process_name, operation_name, node_data, document_type, doc_meta
		Object.assign(this, opts);

		// State
		this.config = this._load_config();

		// Cache
		this.adapter = null;
		this.operation_def = null;
		this.schema = null; // The Raw Adapter Schema
		this.normalized_fields = []; // The Compiled Runtime Fields
		this.field_map = {}; // Fast Lookup

		// UI Binding (Ephemeral)
		this.active_dialog = null;
		this.active_grids = {}; // fieldname -> grid instance

		// Runtime Meta Registry (Isolated from Schema)
		// Structure: { [context_id]: { [fieldname]: { reqd, read_only, hidden } } }
		// context_id: "root" or row.name
		this.dependency_states = {};

		// Async Sequencing (Concurrency Guard)
		this.current_update_promise = Promise.resolve();

		// Recursion Guards
		this._refreshing_ui = false;
		this._disposed = false;
	}

	/**
	 * Initialize the runtime. Must be called before usage.
	 * Resolves schema, fetches async options, prepares runtime.
	 */
	async init() {
		await this._load_adapter();
		this.schema = this._resolve_schema();
		this.normalized_fields = await this._normalize_schema(this.schema);
		this._build_field_map();

		// 1. Run initial dependency check on loaded config (Root)
		await this.evaluate_dependencies(this.config);

		// 2. Recursively evaluate dependencies for all child rows
		const evaluate_recursive = async (data) => {
			for (const key in data) {
				if (Array.isArray(data[key])) {
					for (const row of data[key]) {
						if (row && typeof row === "object" && row.name) {
							// Find table fieldname if possible or fallback to key
							const tf = row.__table_fieldname || key;
							await this.evaluate_dependencies(this.config, row, tf);
							await evaluate_recursive(row);
						}
					}
				}
			}
		};
		await evaluate_recursive(this.config);
	}

	// ============================================================
	// 1. STATE & CONTEXT API
	// ============================================================

	/**
	 * The Single Mutation Surface.
	 * All UI changes must pass through here.
	 */
	update_field(fieldname, value, row_context = null) {
		// Asynchronous Sequencing Guard: ensures updates happen in order
		this.current_update_promise = this.current_update_promise.then(async () => {
			// 1. Mutate State
			if (row_context) {
				// Row Level Mutation
				// row_context is the actual row object (doc)
				row_context[fieldname] = value;
			} else {
				// Root Level Mutation
				this.config[fieldname] = value;
			}

			// 2. Trigger Reactive Logic
			await this._handle_change(fieldname, value, row_context);
		});

		return this.current_update_promise;
	}

	get_config() {
		return { ...this.config };
	}

	/**
	 * Construct the standard ctx object for hooks/eval
	 */
	_get_context(row = null) {
		return {
			doc: row || this.config, // If row provided, 'doc' is the row (Frappe standard)
			row: row, // Alias for current row (if any)
			parent: this.config, // Link to root config
			config: this.config, // Alias for root config

			// Meta linkage
			document_type: this.document_type,
			process_name: this.process_name,
			operation_name: this.operation_name,

			// The Mutation API
			update_field: (field, val) => this.update_field(field, val, row),
		};
	}

	// ============================================================
	// 2. SCHEMA & NORMALIZATION
	// ============================================================

	async _load_adapter() {
		await flexirule.utils.load_process_adapter(this.process_name);
		this.adapter = flexirule.utils.get_process_adapter(this.process_name);

		if (this.adapter && this.adapter.get_operation) {
			this.operation_def = this.adapter.get_operation(this.operation_name);
		}

		// Run Adapter Setup (Global Context Enrichment)
		if (this.adapter && typeof this.adapter.setup === "function") {
			await this._safe_run("setup", () => this.adapter.setup(this._get_context()));
		}

		// Run Operation Setup (Context Enrichment)
		if (this.operation_def && typeof this.operation_def.setup === "function") {
			await this._safe_run("operation_setup", () =>
				this.operation_def.setup(this.config, this._get_context())
			);
		}
	}

	_resolve_schema() {
		if (!this.adapter) return [];

		// Priority 1: Adapter.get_schema(operation_name, context)
		if (typeof this.adapter.get_schema === "function") {
			const schema = this._safe_run("get_schema", () =>
				this.adapter.get_schema(this.operation_name, this._get_context())
			);
			if (schema && schema.fields) return schema.fields;
			if (Array.isArray(schema)) return schema;
		}

		// Priority 2: Operation.get_config_fields(context) (Legacy/Simple)
		if (this.operation_def && typeof this.operation_def.get_config_fields === "function") {
			return this._safe_run("get_config_fields", () =>
				this.operation_def.get_config_fields(this._get_context())
			);
		}

		return [];
	}

	_resolve_actions() {
		if (!this.adapter) return [];

		let actions = [];

		// 1. Adapter global actions
		if (typeof this.adapter.get_actions === "function") {
			const res = this._safe_run("get_actions", () =>
				this.adapter.get_actions(this.operation_name, this._get_context())
			);
			if (Array.isArray(res)) actions = actions.concat(res);
		}

		// 2. Operation specific actions
		if (this.operation_def && typeof this.operation_def.get_actions === "function") {
			const res = this._safe_run("get_operation_actions", () =>
				this.operation_def.get_actions(this._get_context())
			);
			if (Array.isArray(res)) actions = actions.concat(res);
		}

		return actions;
	}

	/**
	 * Compiles the raw schema into a Frappe-compatible field list.
	 * Handles type conversions (DocField -> Autocomplete) and Option loading.
	 */
	async _normalize_schema(raw_fields) {
		if (!raw_fields) return [];
		const normalized = [];

		for (const field of raw_fields) {
			const processed = await this._normalize_field(field);
			if (processed) normalized.push(processed);
		}
		return normalized;
	}

	async _normalize_field(field) {
		// Clone to protect immutability
		const f = { ...field };

		// 1. Standardize Flags
		f.reqd = f.reqd || 0;
		f.read_only = f.read_only || 0;
		f.hidden = f.hidden || 0;

		// Legacy Compatibility: Default to visible in Grid unless explicitly hidden
		// Standard Frappe defaults to 0, but FlexiRule adapters assume 1
		if (f.in_list_view === undefined) {
			f.in_list_view = 1;
		}

		// Map width to columns (Grid specific)
		if (f.width) {
			f.columns = f.width;
		}

		// 2. Resolve 'System' Types to Frappe Types
		f.fieldtype = this._map_fieldtype(f.fieldtype);

		if (f.fieldtype === "Autocomplete" || f.fieldtype === "MultiSelectList") {
			f.options = await this._resolve_docfield_options(f.options);
		} else if (f.fieldtype === "Table") {
			// Recursively normalize child fields
			const children = f.fields || f.table_fields || [];
			// Re-normalization should be safe but let's avoid it if already normalized
			if (!f._is_normalized) {
				f.fields = await this._normalize_schema(children);
				f._is_normalized = true;
			}
			// Ensure data init in config if missing
			if (this.config[f.fieldname] === undefined) {
				this.config[f.fieldname] = [];
			}
			f.data = this.config[f.fieldname];
		}

		// 3. Resolve Options
		f.options = await this._resolve_options(f, this.config, this._get_context());

		// 4. Grid Formatting
		if (f.fieldtype === "MultiCheck" && !f.formatter) {
			f.formatter = (value) => {
				if (Array.isArray(value)) return value.join(", ");
				return value || "";
			};
		}

		// 5. Separate Business Logic from UI Binding
		// We move the adapter's 'onchange' to a private key so that we don't
		// confuse it with the UI binding 'onchange' we will inject later.
		if (f.onchange) {
			f._onchange_logic = f.onchange;
			delete f.onchange; // Prevent double-execution or recursion
		}

		return f;
	}

	/**
	 * Resolve options for a field based on context
	 */
	async _resolve_options(field, config, context = {}) {
		// 1. Support function-based options (get_options or options)
		const getter =
			field.get_options || (typeof field.options === "function" ? field.options : null);
		if (getter) {
			try {
				return await getter(config, context, this.doc_meta);
			} catch (e) {
				console.warn(`Failed to resolve dynamic options for ${field.fieldname}`, e);
				return [];
			}
		}

		// 2. Support context-based string options
		if (typeof field.options === "string") {
			// doc.fieldname -> values from current configuration
			if (field.options.startsWith("doc.")) {
				const key = field.options.replace("doc.", "");
				return config[key] || "";
			}
			// vars.fieldname -> values from context variables (backwards compatibility with parent. prefix too if needed)
			if (field.options.startsWith("vars.") || field.options.startsWith("parent.")) {
				const key = field.options.replace("vars.", "").replace("parent.", "");
				return context[key] || (context.parent ? context.parent[key] : "");
			}
		}

		return field.options || "";
	}

	/**
	 * Map custom fieldtypes to standard Frappe types
	 */
	_map_fieldtype(fieldtype) {
		const mapping = {
			DocField: "Autocomplete",
			MultiDocField: "MultiSelectList",
		};
		return mapping[fieldtype] || fieldtype;
	}

	_build_field_map() {
		this.field_map = {};
		const traverse = (fields) => {
			fields.forEach((f) => {
				this.field_map[f.fieldname] = f;
				if (f.fieldtype === "Table" && f.fields) {
					traverse(f.fields);
				}
			});
		};
		traverse(this.normalized_fields);
	}

	// ============================================================
	// 3. REACTIVITY & DEPENDENCY ENGINE
	// ============================================================

	/**
	 * Central Change Handler
	 * Fires after a field mutation -> Recalculates -> Refreshes UI
	 */
	async _handle_change(fieldname, value, row_context) {
		// 1. Evaluate Dependencies
		// If root field changed, re-evaluate root AND ALL child rows (because children might depend on root)
		// If child field changed, re-evaluate only that row.

		if (row_context) {
			// Find which table this row belongs to
			// USE table ownership marker if available for performance
			const table_fieldname = row_context.__table_fieldname || null;

			await this.evaluate_dependencies(this.config, row_context, table_fieldname);
		} else {
			await this.evaluate_dependencies(this.config); // Root

			// Also re-evaluate all child rows in all grids as they may depend on root state
			for (const [table_fieldname, grid] of Object.entries(this.active_grids)) {
				for (const row of grid.grid_rows) {
					if (row.doc) await this.evaluate_dependencies(this.config, row.doc, table_fieldname);
				}
			}
		}

		// 2. Trigger 'onchange' hooks (Business Logic)
		const field_def = this.field_map[fieldname];
		// Use strict internal key to avoid recursion with UI bindings
		if (field_def && typeof field_def._onchange_logic === "function") {
			const ctx = this._get_context(row_context);
			// Safe execution - MUST AWAIT for sequential consistency in Promise Chain
			await this._safe_run(`onchange:${fieldname}`, () =>
				field_def._onchange_logic(value, row_context, ctx)
			);
		}

		// 3. Refresh UI
		if (this.active_dialog) {
			this._refresh_dialog_ui(row_context);
		}
	}

	/**
	 * Evaluates 'depends_on', 'mandatory_depends_on', 'read_only_depends_on'
	 * Scope:
	 *   If row is null: Evaluates top-level fields against config
	 *   If row exists: Evaluates child-fields of that row against row+config
	 */
	async evaluate_dependencies(doc, row = null, table_fieldname = null) {
		const context_id = row ? row.name : "root";
		if (!this.dependency_states[context_id]) {
			this.dependency_states[context_id] = {};
		}

		let target_fields = [];
		if (row) {
			// If table_fieldname provided, use it. Otherwise fallback to old traversal.
			if (table_fieldname) {
				const field_def = this.field_map[table_fieldname];
				target_fields = field_def ? field_def.fields || [] : [];
			} else {
				target_fields = this._get_table_fields_for_row(row);
			}
		} else {
			target_fields = this.normalized_fields.filter((f) => f.fieldtype !== "Table");
		}

		const eval_context = this._get_context(row);

		for (const field of target_fields) {
			const state = {
				reqd: field.reqd || 0,
				read_only: field.read_only || 0,
				hidden: field.hidden || 0,
				options: null, // Only filled if dynamic
			};

			// 1. Visibility (depends_on)
			if (field.depends_on) {
				state.hidden = this._eval_condition(field.depends_on, eval_context) ? 0 : 1;
			}

			// 2. Mandatory (mandatory_depends_on)
			if (field.mandatory_depends_on) {
				state.reqd = this._eval_condition(field.mandatory_depends_on, eval_context) ? 1 : 0;
			}

			// 3. Read Only (read_only_depends_on)
			if (field.read_only_depends_on) {
				state.read_only = this._eval_condition(field.read_only_depends_on, eval_context)
					? 1
					: 0;
			}

			// 4. Dynamic Options
			// Re-resolve if the field has dynamic options logic
			const has_dynamic_options =
				field.get_options ||
				typeof field.options === "function" ||
				(typeof field.options === "string" &&
					(field.options.startsWith("doc.") ||
						field.options.startsWith("vars.") ||
						field.options.startsWith("parent.")));

			if (has_dynamic_options) {
				state.options = await this._resolve_options(field, eval_context.doc, eval_context);
			}

			this.dependency_states[context_id][field.fieldname] = state;
		}
	}

	_eval_condition(expression, context) {
		if (!expression) return true;
		if (expression.startsWith("eval:")) {
			expression = expression.slice(5);
		}
		try {
			return frappe.utils.eval(expression, context);
		} catch (e) {
			console.warn(`Dependency Eval Failed: ${expression}`, e);
			return false;
		}
	}

	_get_table_fields_for_row(row) {
		// Find which table this row belongs to?
		// In a flat traversal, this is hard without parent pointer.
		// Optimization: We just iterate ALL table schemas and check if row looks like it?
		// Or better: Pass the table field name when calling evaluate.
		// For now, we iterate all defined table schemas in our normalized fields.
		let schemas = [];
		for (const f of this.normalized_fields) {
			if (f.fieldtype === "Table" && f.fields) {
				schemas = schemas.concat(f.fields);
			}
		}
		return schemas;
	}

	// ============================================================
	// 4. UI: DIALOG IMPLEMENTATION
	// ============================================================

	/**
	 * Builds and shows a standard Frappe Dialog connected to this runtime.
	 */
	async show_dialog(opts = {}) {
		if (!this.schema) await this.init();

		const dialog = new frappe.ui.Dialog({
			title: this.operation_def?.label || this.operation_name,
			fields: this.normalized_fields,
			size: "extra-large",
			primary_action: () => {
				// 1. Frappe Standard Validation
				const values = dialog.get_values();
				if (!values) return;

				// 2. Strict / Double-Check Mandatory (User Request)
				if (!this._check_mandatory()) return;

				// 3. Sync Grid Data (Crucial for Tables)
				// Dialog.get_values() often misses child tables in custom layouts.
				// We manually extract data from active grids.

				// Robustness: ensure we check ALL table fields, even if not in active_grids cache yet
				const table_fields = this.normalized_fields.filter((f) => f.fieldtype === "Table");

				table_fields.forEach((tf) => {
					let grid = this.active_grids[tf.fieldname];

					// Fallback: Try to find grid instance directly if missing from cache
					if (
						!grid &&
						dialog.fields_dict[tf.fieldname] &&
						dialog.fields_dict[tf.fieldname].grid
					) {
						grid = dialog.fields_dict[tf.fieldname].grid;
						this.active_grids[tf.fieldname] = grid; // Cache it
					}

					if (grid) {
						// grid.get_data() safely returns the current rows
						// We must ensure we update 'values' or 'this.config' directly.
						const rows = grid.get_data() || [];
						values[tf.fieldname] = rows;
						this.config[tf.fieldname] = rows; // Sync to config immediately
					}
				});

				// 4. Merge Values & Validation
				// Now unsafe Object.assign won't wipe tables because values[fieldname] is populated
				Object.assign(this.config, values);

				if (!this.validate()) return;

				// 5. Save & Close
				this._sync_to_node();
				if (typeof opts.on_save === "function") {
					this._safe_run("on_save", () => opts.on_save(this.config));
				}
				if (this.on_save_callback) {
					this._safe_run("on_save_callback", () => this.on_save_callback(this.config));
				}
				dialog.hide();
			},
		});

		this.active_dialog = dialog;

		// Cleanup events on hide (preserve existing handler)
		const original_on_hide = dialog.on_hide;
		dialog.on_hide = () => {
			Object.values(this.active_grids).forEach((grid) => {
				if (grid && grid.wrapper) {
					$(grid.wrapper).off(".flexirule_config");
				}
			});
			this.active_grids = {};
			this.active_dialog = null;
			if (typeof original_on_hide === "function") {
				original_on_hide.call(dialog);
			}
		};

		// 1. Hydrate Initial State
		dialog.set_values(this.config);

		// 2. Bind Root Fields
		this._bind_dialog_events(dialog);

		// 3. Add Custom Quick Actions
		const custom_actions = this._resolve_actions();
		custom_actions.forEach((action) => {
			if (!action.label || !action.click) return;
			dialog.add_custom_button(__(action.label), () => {
				action.click(this.config, this._get_context());
			});
		});

		dialog.show();

		// 3. Bind Grid Fields (Tables) - MOVED AFTER SHOW to ensure Grid DOM/Object exists
		this._bind_grid_events(dialog);

		// Final refresh to run policies
		this._refresh_dialog_ui();

		return dialog;
	}

	/**
	 * Explicitly check if required fields are filled.
	 * Provides standard UI feedback (Red borders/scrolling).
	 * NOW SUPPORTS CHILD TABLES.
	 */
	_check_mandatory() {
		if (!this.active_dialog) return true;
		let is_valid = true;
		let first_error_field = null;

		// 1. Validate Root Fields
		for (const f of this.normalized_fields) {
			const field_obj = this.active_dialog.fields_dict[f.fieldname];
			if (!field_obj) continue;

			if (f.fieldtype === "Table") {
				// Delegate to Grid Validation
				if (!this._check_grid_mandatory(f, field_obj)) {
					is_valid = false;
					// We don't break here, we want to highlight all errors
				}
				continue;
			}

			// Skip invalid types
			if (f.hidden || ["Section Break", "Column Break", "HTML"].includes(f.fieldtype))
				continue;

			// Is it required?
			const reqd = field_obj.df.reqd || f.reqd;
			if (!reqd) continue;

			// Get Value
			const val = field_obj.get_value();
			const has_value = val !== undefined && val !== null && val !== "";

			if (!has_value) {
				is_valid = false;
				if (!first_error_field) first_error_field = field_obj;

				// UI Feedback
				try {
					field_obj.set_invalid
						? field_obj.set_invalid()
						: $(field_obj.input).addClass("is-invalid");
				} catch (e) { }
			} else {
				try {
					$(field_obj.input).removeClass("is-invalid");
				} catch (e) { }
			}
		}

		if (!is_valid) {
			frappe.msgprint(__("Missing required fields"));
			if (first_error_field && first_error_field.is_focus_able) {
				// Try to focus
				setTimeout(() => first_error_field.set_focus(), 100);
			}
		}
		return is_valid;
	}

	_check_grid_mandatory(table_field, grid_obj) {
		// Robustness: ensure grid is found
		const grid = grid_obj.grid || this.active_grids[table_field.fieldname];
		if (!grid) return true; // Can't validate if no grid

		// The table itself might be required (at least 1 row)
		// but typically 'reqd' on table means non-empty data.
		if (table_field.reqd && grid.grid_rows.length === 0) {
			frappe.msgprint(__("Table {0} requires at least one row", [table_field.label]));
			return false;
		}

		let grid_valid = true;

		// Iterate Rows
		grid.grid_rows.forEach((row, row_idx) => {
			if (!row.doc) return;

			// Check each column in the child schema
			const child_fields = table_field.fields || [];
			const row_state = this.dependency_states[row.doc.name] || {};

			child_fields.forEach((cf) => {
				const field_state = row_state[cf.fieldname] || {};
				const is_hidden = field_state.hidden !== undefined ? field_state.hidden : cf.hidden;
				if (is_hidden) return;

				const is_reqd = field_state.reqd !== undefined ? field_state.reqd : cf.reqd;
				if (!is_reqd) return;

				const val = row.doc[cf.fieldname];
				const has_value = val !== undefined && val !== null && val !== "";

				if (!has_value) {
					grid_valid = false;
					// UI Feedback
					row.show_error && row.show_error(`${cf.label || cf.fieldname} is required`);
					const $cell = row.get_cell ? row.get_cell(cf.fieldname) : null;
					if ($cell) $cell.addClass("error");
				}
			});
		});

		if (!grid_valid) {
			// maybe collapse open the grid helper?
		}
		return grid_valid;
	}

	/**
	 * Run custom validation logic
	 */
	validate() {
		if (this.operation_def && typeof this.operation_def.validate === "function") {
			return this._safe_run("validate", () => {
				const err = this.operation_def.validate(this.config, this._get_context());
				if (err) {
					frappe.throw(err);
					return false;
				}
				return true;
			});
		}
		return true;
	}

	_bind_dialog_events(dialog) {
		this.normalized_fields.forEach((f) => {
			if (
				f.fieldtype === "Table" ||
				f.fieldtype === "Section Break" ||
				f.fieldtype === "Column Break"
			)
				return;

			const field_obj = dialog.fields_dict[f.fieldname];
			if (!field_obj) return;

			// Native onchange injection
			const original_change = field_obj.df.onchange;
			field_obj.df.onchange = () => {
				const val = field_obj.get_value();
				this.update_field(f.fieldname, val, null);
				if (original_change) original_change();
			};
		});
	}

	_bind_grid_events(dialog) {
		this.normalized_fields
			.filter((f) => f.fieldtype === "Table")
			.forEach((table_field) => {
				const grid_obj = dialog.fields_dict[table_field.fieldname];
				if (!grid_obj || !grid_obj.grid) return;

				const grid = grid_obj.grid;
				this.active_grids[table_field.fieldname] = grid;

				// Hook into Grid Rows
				// Frappe Grid doesn't have a single "on_cell_change".
				// We use the standard methodology: monitoring the form actions within the grid.
				// But actually, we can leverage grid.refresh_row or the field 'onchange' logic inside the grid schema.

				// We ALREADY injected onchange hooks into the schema during normalization (if they existed in adapter).
				// BUT those hooks were "Business Logic" hooks.
				// We need "Runtime Binding" hooks.

				// Strategy: Mutate the Grid's internal Field Docs to point to our runtime updater
				// This is tricky because Grid re-renders.
				// Best approach: Use the global grid event if available or specific field bindings.

				// Frappe Grid uses 'frappe.ui.form.Control' for cells.
				// We can listen to 'change' on the wrapper, like the user's previous code, which is robust.

				// Namespace event to allow clean removal
				$(grid.wrapper).on("change.flexirule_config", "input, select, textarea", (e) => {
					try {
						this._handle_grid_input_change(e, grid, table_field);
					} catch (err) {
						console.error("FlexiRule: Grid input change error", err);
					}
				});

				// Hook into Row Add to trigger defaults/dependencies
				const original_add = grid.on_row_add;
				grid.on_row_add = (row) => {
					if (original_add) original_add.call(grid, row);

					// Ensure name for registry if not present (should be handled by hydrate)
					if (!row.doc.name) {
						row.doc.name = frappe.utils.get_random(10);
					}

					// Table Ownership Marker (MANDATORY for Release)
					row.doc.__table_fieldname = table_field.fieldname;

					const table_schema = this.field_map[table_field.fieldname];
					const child_fields = table_schema.fields || [];

					// 1. Trigger Runtime Updates for Defaults
					child_fields.forEach((cf) => {
						if (row.doc[cf.fieldname] !== undefined && cf._onchange_logic) {
							// For new rows, we update the model and trigger logic
							this.update_field(cf.fieldname, row.doc[cf.fieldname], row.doc);
						}
					});

					// 2. Evaluate Dependencies for the new row
					this.evaluate_dependencies(this.config, row.doc, table_field.fieldname)
						.then(() => {
							// 3. UI Sync (Refreshes properties for the new row)
							this._refresh_dialog_ui(row.doc);
						})
						.catch((err) => {
							console.error("FlexiRule: Failed to evaluate dependencies for new row", err);
						});
				};
			});
	}

	async _handle_grid_input_change(e, grid, table_field) {
		const $input = $(e.currentTarget);
		const $row = $input.closest(".grid-row");
		const row_idx = $row.attr("data-idx"); // 1-based index
		if (!row_idx) return;

		const row = grid.get_row(row_idx - 1);
		if (!row || !row.doc) return;

		const fieldname = $input.closest("[data-fieldname]").attr("data-fieldname");
		if (!fieldname) return;

		// Robust value extraction:
		// Attempt to get the latest value from the control directly if possible,
		// otherwise fallback to doc which should have been updated by now.
		const control = row.columns[fieldname];
		let val = row.doc[fieldname];

		if (control) {
			if (typeof control.get_value === "function") {
				val = control.get_value();
			} else if (control.input) {
				const $i = $(control.input);
				if ($i.attr("type") === "checkbox") {
					val = $i.is(":checked") ? 1 : 0;
				} else {
					val = $i.val();
				}
			}
		}

		// Trigger Runtime Update
		await this.update_field(fieldname, val, row.doc);
	}

	_refresh_dialog_ui(row_context = null) {
		if (!this.active_dialog) return;

		// Recursion guard to prevent infinite loops
		if (this._refreshing_ui) return;
		this._refreshing_ui = true;

		// 1. Root Fields: Sync Properties (reqd, read_only, hidden) & Value
		// Frappe Dialog doesn't automatically watch these properties on the DF object
		// We must manually refresh the field if properties changed.
		this.normalized_fields.forEach((f) => {
			if (f.fieldtype === "Section Break" || f.fieldtype === "Column Break") return;

			// Table Handling (Special Sync for Grids to support programmatic updates like Profile)
			if (f.fieldtype === "Table") {
				const grid_obj = this.active_dialog.fields_dict[f.fieldname];
				if (grid_obj && grid_obj.grid) {
					const model_val = this.config[f.fieldname] || [];
					const grid_val = grid_obj.grid.get_data() || []; // UI state

					// Check for divergence (Programmatic update vs UI state)
					// Simple length check or JSON stringify to detect changes
					if (JSON.stringify(model_val) !== JSON.stringify(grid_val)) {
						// Model has changed (e.g. Profile applied new rows)
						// Sync Model -> Grid
						grid_obj.grid.df.data = model_val;
						grid_obj.grid.refresh();
					}

					// Also refresh property changes if needed (reqd, read_only)
					["reqd", "read_only", "hidden"].forEach((prop) => {
						if (grid_obj.df[prop] !== f[prop]) {
							grid_obj.df[prop] = f[prop];
							grid_obj.refresh(); // Refresh wrapper
						}
					});
				}
				return;
			}

			const field = this.active_dialog.fields_dict[f.fieldname];
			if (field) {
				let dirty = false;

				// 1. Sync Value (Model -> UI)
				// If the model value changed (side-effect), update the UI.
				// We check strict inequality.
				const model_val = this.config[f.fieldname];
				const ui_val = field.get_value();

				// Handle array comparison for MultiSelect/Table? (Table excluded here)
				// For MultiSelect, generic JSON comparison or simple check.
				// Frappe's set_value usually handles no-op if same.

				// Simple equality check might fail for arrays/objects, but let's try shallow or strict
				if (model_val !== ui_val) {
					// For arrays (MultiSelect), strict equality fails.
					// We only want to set_value if logic updated it.
					// To avoid loops (UI -> update_field -> refresh -> set_value -> onchange -> ...),
					// we need to be careful.
					// But standard field 'set_value' normally triggers onchange?
					// Wait, field.set_value() typically triggers onchange.
					// If we set_value, we might trigger infinite loop if onchange calls update_field.

					// ConfigurableAction.update_field is the SOURCE of truth.
					// If UI triggered update_field, model matches UI.
					// If Logic triggered update_field, model != UI.
					// So validating model_val !== ui_val is correct.

					// Is deep compare needed?
					let diff = model_val !== ui_val;
					if (Array.isArray(model_val) && Array.isArray(ui_val)) {
						diff = JSON.stringify(model_val) !== JSON.stringify(ui_val);
					}

					if (diff) {
						try {
							field.set_value(model_val);
							// Setting value programmatically might trigger on_change again depending on Frappe version.
							// To be safe, we rely on the check above to stop cycles.
						} catch (e) {
							console.warn("Sync error", e);
						}
					}
				}

				// 2. Sync Properties (reqd, read_only, hidden)
				// Check for property divergence via registry
				const runtime_state = (this.dependency_states["root"] || {})[f.fieldname] || {};

				["reqd", "read_only", "hidden"].forEach((prop) => {
					const target_val = runtime_state[prop] !== undefined ? runtime_state[prop] : f[prop];
					if (field.df[prop] !== target_val) {
						field.df[prop] = target_val;
						// Also apply some properties directly to the control instance
						// as refresh() behavior varies across controls.
						if (prop === "read_only" && typeof field.set_read_only === "function") {
							field.set_read_only();
						}
						dirty = true;
					}
				});

				// 3. Sync Options (Dynamic)
				if (runtime_state.options !== undefined && runtime_state.options !== null) {
					// Compare with current options
					if (JSON.stringify(field.df.options) !== JSON.stringify(runtime_state.options)) {
						field.df.options = runtime_state.options;
						dirty = true;
					}
				}

				if (dirty) field.refresh();
			}
		});

		// 2. Grids: Isolated Row Refresh
		// We iterate all grids and all rows to ensure visibility/read_only/reqd/options are applied
		// from the dependency_states registry.
		Object.values(this.active_grids).forEach((grid) => {
			grid.grid_rows.forEach((row) => {
				if (!row.doc) return;

				const row_state = this.dependency_states[row.doc.name] || {};
				let row_dirty = false;
				const child_fields = grid.df.fields || [];

				child_fields.forEach((cf) => {
					const control = row.columns[cf.fieldname];
					if (!control) return;

					// 🔒 CRITICAL: Isolate DF FIRST, before ANY property access or modification
					// Frappe shares the 'df' object across all controls in a grid column.
					// We MUST clone it before reading/writing any properties to prevent leakage.
					if (!control.df._flexirule_isolated) {
						// Clone the df to isolate this control from others
						control.df = { ...control.df };
						control.df._flexirule_isolated = true;
						// Reset dynamic properties to schema defaults for the fresh isolated df
						// This ensures new rows don't inherit stale state from previous row mutations
						control.df.read_only = cf.read_only || 0;
						control.df.hidden = cf.hidden || 0;
						control.df.reqd = cf.reqd || 0;
					}

					// 1. Sync Value (Model -> UI)
					const model_val = row.doc[cf.fieldname];
					const ui_val = control.get_value ? control.get_value() : control.value;

					let diff = model_val !== ui_val;
					if (Array.isArray(model_val) && Array.isArray(ui_val)) {
						diff = JSON.stringify(model_val) !== JSON.stringify(ui_val);
					}

					if (diff) {
						if (typeof control.set_value === "function") {
							control.set_value(model_val);
						} else {
							control.value = model_val;
							if (control.refresh) control.refresh();
						}
						row_dirty = true;
					}

					// 2. Apply row-specific state from dependency evaluation
					const state = row_state[cf.fieldname];
					if (!state) return;

					// Apply read_only state
					if (state.read_only !== undefined) {
						control.df.read_only = state.read_only;
						// Use Frappe's method to apply visual state
						if (control.set_read_only) {
							control.set_read_only(state.read_only);
						} else if (control.$input) {
							control.$input.prop("disabled", !!state.read_only);
						}
					}

					// Apply hidden state
					if (state.hidden !== undefined) {
						control.df.hidden = state.hidden;
						if (control.toggle_display) {
							control.toggle_display(!state.hidden);
						}
					}

					// Apply mandatory state
					if (state.reqd !== undefined) {
						control.df.reqd = state.reqd;
						if (control.set_working_mandatory) {
							control.set_working_mandatory(state.reqd);
						}
					}

					// Apply dynamic options
					if (state.options !== undefined && state.options !== null) {
						if (JSON.stringify(control.df.options) !== JSON.stringify(state.options)) {
							control.df.options = state.options;
							// For select-like controls, update the options display
							if (control.set_options) {
								control.set_options(state.options);
							}
							row_dirty = true;
						}
					}
				});

				// Only refresh if values changed, not for property changes
				// Property changes are applied directly to avoid losing isolation
				if (row_dirty) {
					// Re-apply isolation after refresh since Frappe recreates controls
					row.refresh();
					// Re-isolate controls after refresh
					child_fields.forEach((cf) => {
						const control = row.columns[cf.fieldname];
						if (control && control.df) {
							control.df = { ...control.df };
							control.df._flexirule_isolated = true;
							// Re-apply state after refresh
							const state = row_state[cf.fieldname];
							if (state) {
								if (state.read_only !== undefined) {
									control.df.read_only = state.read_only;
									control.set_read_only && control.set_read_only(state.read_only);
								}
								if (state.hidden !== undefined) {
									control.df.hidden = state.hidden;
									control.toggle_display && control.toggle_display(!state.hidden);
								}
								if (state.reqd !== undefined) {
									control.df.reqd = state.reqd;
									control.set_working_mandatory && control.set_working_mandatory(state.reqd);
								}
							}
						}
					});
				}
			});
		});

		// Clear recursion guard
		this._refreshing_ui = false;
	}

	// ============================================================
	// 5. INTERNAL HELPERS
	// ============================================================

	_load_config() {
		const raw = this.node_data?.config || this.node_data?.method_config;
		let config = {};
		if (raw) {
			try {
				config = typeof raw === "object" ? raw : JSON.parse(raw);
			} catch (e) {
				config = {};
			}
		}

		// Hydrate for UI lifecycle (add unique IDs, etc.)
		this._hydrate_for_ui(config);
		return config;
	}

	_sync_to_node() {
		if (this.node_data) {
			// Clean before saving
			const clean_config = this._clean_for_storage(this.config);
			this.node_data.config = JSON.stringify(clean_config);
		}
	}

	/**
	 * Prepares configuration data for the UI.
	 * Frappe Grids require 'name' and unique keys for rows to function correctly.
	 */
	_hydrate_for_ui(data, table_fieldname = null) {
		if (!data || typeof data !== "object") return;

		// Traverse keys
		for (const key in data) {
			if (Array.isArray(data[key])) {
				// This is likely a Child Table
				data[key].forEach((row, idx) => {
					if (typeof row === "object" && row !== null) {
						// Ensure ID
						if (!row.name) {
							row.name = frappe.utils.get_random(10);
							row.__islocal = 1; // Mark as local so we know to strip it later
						}
						// Ensure idx
						if (row.idx === undefined) {
							row.idx = idx + 1;
						}

						// Table Ownership Marker (MANDATORY for Release)
						row.__table_fieldname = key;

						// Recursive hydration
						this._hydrate_for_ui(row, key);
					}
				});
			} else if (typeof data[key] === "object") {
				this._hydrate_for_ui(data[key]);
			}
		}
	}

	/**
	 * Strips UI-only fields from the configuration data.
	 */
	_clean_for_storage(data) {
		if (!data) return data;

		// Deep clone to avoid mutating the active state
		const clean = JSON.parse(JSON.stringify(data));

		const traverse_and_clean = (obj) => {
			if (Array.isArray(obj)) {
				obj.forEach((item) => traverse_and_clean(item));
			} else if (typeof obj === "object" && obj !== null) {
				// Determine if local before stripping flags
				const is_local = !!obj.__islocal;

				// Strip UI fields
				const keys_to_remove = [
					"__islocal",
					"__checked",
					"__unsaved",
					"__table_fieldname",
					"docstatus",
					"parent",
					"parenttype",
					"parentfield",
					"owner",
					"creation",
					"modified",
				];

				keys_to_remove.forEach((k) => delete obj[k]);

				// Remove 'name' logic:
				// 1. If it was marked local, definitely remove name.
				// 2. If name looks like a temporary ID (10 chars random), remove it to be safe
				//    (in case __islocal was lost or not set but it's logically local).
				// 3. User reported "row 1" as name, implying some Grids use that.
				//    Strictly speaking, if we hydrate with random ID, we want to strip it.
				//    Valid DocNames are usually alphanumeric or contain special chars but purely
				//    config objects shouldn't rely on 'name' for identity across saves unless established.

				if (
					is_local ||
					(obj.name && obj.name.length === 10) ||
					(obj.name && obj.name.startsWith("row "))
				) {
					delete obj.name;
				}

				// Also remove 'idx' as order is preserved in array
				delete obj.idx;

				for (const key in obj) {
					traverse_and_clean(obj[key]);
				}
			}
		};

		traverse_and_clean(clean);
		return clean;
	}

	async _resolve_docfield_options(ref) {
		if (!ref) return [];

		let target = this.document_type;
		let is_meta_only = false;

		if (ref === "Variables" || ref === "Field Picker") {
			is_meta_only = true;
		} else if (ref !== "DocField" && ref.indexOf(".") === -1) {
			target = ref;
		}

		// Get variables from instance
		const context_vars =
			typeof this.get_variable_options === "function"
				? await this._safe_run("get_variable_options", () => this.get_variable_options())
				: [];

		if (is_meta_only) {
			return context_vars.map((v) => v.value);
		}

		// Use global utility for combined result
		return await flexirule.utils.get_combined_fields(target, context_vars);
	}

	/**
	 * Safe Runner for Adapter Hooks
	 */
	_safe_run(hook_name, fn) {
		try {
			const res = fn();
			if (res instanceof Promise) {
				return res.catch((e) => {
					console.error(`FlexiRule Adapter Async Error [${hook_name}]:`, e);
					return null;
				});
			}
			return res;
		} catch (e) {
			console.error(`FlexiRule Adapter Error [${hook_name}]:`, e);
			// Show message for critical hooks
			if (["validate", "setup"].includes(hook_name)) {
				frappe.msgprint({
					title: __("Process Adapter Error"),
					message: e.message,
					indicator: "red",
				});
			}
			return null;
		}
	}

	/**
	 * Dispose of the runtime instance and cleanup resources.
	 * Call this when the ConfigurableAction is no longer needed.
	 */
	dispose() {
		if (this._disposed) return;
		this._disposed = true;

		// Cleanup grid event handlers
		if (this.active_grids) {
			Object.values(this.active_grids).forEach((grid) => {
				if (grid && grid.wrapper) {
					$(grid.wrapper).off(".flexirule_config");
				}
			});
		}

		// Hide and cleanup dialog
		if (this.active_dialog) {
			try {
				this.active_dialog.hide();
			} catch (e) {
				// Dialog may already be hidden
			}
		}

		// Clear references
		this.active_dialog = null;
		this.active_grids = {};
		this.dependency_states = {};
		this.normalized_fields = [];
		this.field_map = {};
		this.adapter = null;
		this.operation_def = null;
		this.schema = null;
	}
};
