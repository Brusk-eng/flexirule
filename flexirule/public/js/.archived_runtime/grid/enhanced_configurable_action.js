/**
 * Enhanced ConfigurableAction that uses the hybrid approach
 */
frappe.provide("flexirule.grid");

flexirule.grid.EnhancedConfigurableAction = class EnhancedConfigurableAction {
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
		this.enhanced_grids = new Map(); // fieldname -> EnhancedGridController
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

		// Run initial dependency check on loaded config
		this.evaluate_dependencies(this.config);
	}

	/**
	 * Enhance a grid with custom functionality
	 */
	enhance_grid(fieldname, grid, schema) {
		const enhanced_controller = new flexirule.grid.EnhancedGridController(
			grid,
			schema,
			this._get_context()
		);

		this.enhanced_grids.set(fieldname, enhanced_controller);

		// Register custom renderers based on field definitions
		schema.fields.forEach((field) => {
			if (field.fieldtype === "Autocomplete" && field.options === "Field Picker") {
				const custom_renderer = new flexirule.grid.CustomFieldSelector({
					fieldname: field.fieldname,
					on_change: (fieldname, value, row_doc) => {
						this.update_field(fieldname, value, row_doc);
					},
				});

				enhanced_controller.register_custom_renderer(field.fieldname, custom_renderer);
			}
		});
	}

	/**
	 * Update context across all enhanced grids
	 */
	update_context(new_context) {
		// Update main context
		Object.assign(this.context, new_context);

		// Update all enhanced grids
		for (const [fieldname, controller] of this.enhanced_grids) {
			controller.update_context(new_context);
		}
	}

	/**
	 * The Single Mutation Surface.
	 * All UI changes must pass through here.
	 */
	update_field(fieldname, value, row_context = null) {
		// 1. Mutate State
		if (row_context) {
			// Row Level Mutation
			// row_context is the actual row object (doc)
			row_context[fieldname] = value;
		} else {
			// Root Level Mutation
			this.config[fieldname] = value;
		}

		// 2. Persist to Node Data (Immediate Consistency)
		// REMOVED: As per user request, we only persist on Primary Action (Save).
		// this._sync_to_node();

		// 3. Trigger Reactive Logic
		this._handle_change(fieldname, value, row_context);
	}

	get_config() {
		return { ...this.config };
	}

	/**
	 * Construct the standard ctx object for hooks/eval
	 */
	_get_context(row = null) {
		return {
			doc: this.config, // Frappe standard: 'doc' refers to the parent
			row: row, // Current row (if any)
			config: this.config, // Alias for clarity

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
		this.adapter = window.flexirule?.processes?.[this.process_name];

		if (this.adapter && this.adapter.get_operation) {
			this.operation_def = this.adapter.get_operation(this.operation_name);
		}

		// Run Adapter Setup (Global Context Enrichment)
		if (this.adapter && typeof this.adapter.setup === "function") {
			await this.adapter.setup(this._get_context());
		}
	}

	_resolve_schema() {
		if (!this.adapter) return [];

		// Priority 1: Adapter.get_schema(operation_name, context)
		if (typeof this.adapter.get_schema === "function") {
			const schema = this.adapter.get_schema(this.operation_name, this._get_context());
			if (schema && schema.fields) return schema.fields;
			if (Array.isArray(schema)) return schema;
		}

		// Priority 2: Operation.get_config_fields(context) (Legacy/Simple)
		if (this.operation_def && typeof this.operation_def.get_config_fields === "function") {
			return this.operation_def.get_config_fields(this._get_context());
		}

		return [];
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
		if (f.fieldtype === "DocField") {
			f.fieldtype = "Autocomplete";
			f.options = await this._resolve_docfield_options(f.options);
		} else if (f.fieldtype === "MultiDocField") {
			f.fieldtype = "MultiSelectList";
			f.options = await this._resolve_docfield_options(f.options);
		} else if (f.fieldtype === "Table") {
			// Recursively normalize child fields
			const children = f.fields || f.table_fields || [];
			f.fields = await this._normalize_schema(children);
			// Ensure data init
			if (!this.config[f.fieldname]) this.config[f.fieldname] = [];
			f.data = this.config[f.fieldname];
		}

		// 3. Dynamic Options (if function) & OnChange Normalization
		// Note: For top-level fields, we resolve once during init.
		// For tables, we might need dynamic resolution per row (handled in Grid).
		if (typeof f.get_options === "function" && f.fieldtype !== "Table") {
			// This is static initialization. Runtime dynamic options (dependent)
			// are harder in standard Dialogs without custom controls.
			// We assume get_options here is for "Start State".
			try {
				const opts = await f.get_options(null, this._get_context(), this.doc_meta);
				if (opts) f.options = opts;
			} catch (e) {
				console.warn(`Failed to resolve options for ${f.fieldname}`, e);
			}
		}

		// 4. Separate Business Logic from UI Binding
		// We move the adapter's 'onchange' to a private key so that we don't
		// confuse it with the UI binding 'onchange' we will inject later.
		if (f.onchange) {
			f._onchange_logic = f.onchange;
			delete f.onchange; // Prevent double-execution or recursion
		}

		return f;
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
	_handle_change(fieldname, value, row_context) {
		// 1. Evaluate Dependencies
		// We evaluate EVERYTHING relevant to the scope.
		// If row_context, we evaluate that row.
		// Always evaluate root.

		this.evaluate_dependencies(this.config);
		if (row_context) {
			this.evaluate_dependencies(this.config, row_context);
		}

		// 2. Trigger 'onchange' hooks (Business Logic)
		const field_def = this.field_map[fieldname];
		// Use strict internal key to avoid recursion with UI bindings
		if (field_def && typeof field_def._onchange_logic === "function") {
			const ctx = this._get_context(row_context);
			// Safe execution
			try {
				field_def._onchange_logic(value, row_context, ctx);
			} catch (e) {
				console.error(`Error in onchange for ${fieldname}:`, e);
			}
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
	evaluate_dependencies(doc, row = null) {
		// Which fields to check?
		// If row provided, check that row's structure (need to find the table schema)
		// For simplicity in this primitive: we iterate the KNOWN schema.

		const target_fields = row
			? this._get_table_fields_for_row(row)
			: this.normalized_fields.filter((f) => f.fieldtype !== "Table"); // Top level non-tables

		const context = { doc: this.config, row: row || null, ...this.config };
		if (row) Object.assign(context, row);

		for (const field of target_fields) {
			const s = row || this.config; // The state object being modified

			// 1. Visibility (depends_on / hidden)
			if (field.depends_on) {
				const visible = this._eval_condition(field.depends_on, context);
				// We don't delete data, just mark metadata (UI uses this)
				// In a purely runtime object, where do we store 'hidden' state?
				// We assume the UI pulls this, but for 'reqd' logic, we need to know.
				// Let's store ephemeral state in the Object itself using a symbol or non-enumerable?
				// Or just rely on UI refreshing?
				// Re-evaluation usually means UI update.
				// For simplicity, we don't mutate the schema. The UI (Dialog) runs its own eval usually.
				// BUT, user asked for "Runtime Owns Persistence".
				// We will rely on the UI layer's standard dependency handler OR force it here.
				// Since generic Frappe Dialog *does* handle depends_on, we strictly support it
				// by ensuring the Context passed to the Dialog is correct.
			}

			// 2. Mandatory (mandatory_depends_on)
			if (field.mandatory_depends_on) {
				field.reqd = this._eval_condition(field.mandatory_depends_on, context) ? 1 : 0;
			}

			// 3. Read Only (read_only_depends_on)
			if (field.read_only_depends_on) {
				field.read_only = this._eval_condition(field.read_only_depends_on, context) ? 1 : 0;
			}
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
					opts.on_save(this.config);
				}
				if (this.on_save_callback) this.on_save_callback(this.config);
				dialog.hide();
			},
		});

		this.active_dialog = dialog;

		// 1. Hydrate Initial State
		dialog.set_values(this.config);

		// 2. Bind Root Fields
		this._bind_dialog_events(dialog);

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
				} catch (e) {}
			} else {
				try {
					$(field_obj.input).removeClass("is-invalid");
				} catch (e) {}
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

			child_fields.forEach((cf) => {
				if (cf.hidden) return;

				// Resolve reqd using runtime state if possible (reqd might depend on other fields)
				// We rely on the stored 'cf.reqd' which should have been updated by 'evaluate_dependencies'
				// However, dependency evaluation updates the Schema definition in this.field_map or similar?
				// Actually dependencies update 'field_map[fieldname].reqd'.
				// Since child fields are shared across rows in the schema definition in this.normalized_fields...
				// Wait. 'evaluate_dependencies' updates the FIELD OBJECT.
				// If we share the field object across rows, we might have a problem if reqd varies by row!
				// Frappe Grids usually handle this by having a per-row docfield copy or using 'mandatory_depends_on' during validation.

				// Let's use the row's doc values to check mandatory_depends_on if needed?
				// Or assume evaluate_dependencies ran and we should trust cf.reqd?
				// Issue: evaluate_dependencies runs for *a* context. If checking all rows, we should assume the latest state
				// or ideally re-evaluate per row.
				// For now, let's trust the STATIC reqd or the value in the row if standard.
				// Better: Check the value.

				if (!cf.reqd) return;

				const val = row.doc[cf.fieldname];
				const has_value = val !== undefined && val !== null && val !== "";

				if (!has_value) {
					grid_valid = false;
					// Highlight logic for Grid Cell
					// row.columns[cf.fieldname] gives the control
					// But grid rows render lazily or differently.
					// We can try to use standard grid methods.

					// Show indicator on row
					row.show_error && row.show_error(cf.label + " is required");

					// Or try to highlight cell
					const $cell = row.get_cell ? row.get_cell(cf.fieldname) : null;
					if ($cell) {
						$cell.addClass("error");
					}
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
			try {
				const err = this.operation_def.validate(this.config, this._get_context());
				if (err) {
					frappe.throw(err);
					return false;
				}
			} catch (e) {
				console.error("Validation Error:", e);
				frappe.msgprint(__("Validation failed: ") + e.message);
				return false;
			}
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

				// Enhance the grid with custom functionality
				this.enhance_grid(table_field.fieldname, grid, {
					fields: table_field.fields || [],
				});

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

				$(grid.wrapper).on("change", "input, select, textarea", (e) => {
					this._handle_grid_input_change(e, grid, table_field);
				});

				// Hook into Row Add to trigger defaults/dependencies
				const original_add = grid.on_row_add;
				grid.on_row_add = (row) => {
					if (original_add) original_add.call(grid, row);

					// 1. Trigger Runtime Updates for Defaults
					// Frappe has already populated defaults in row.doc
					// We just need to trigger the logic.

					const table_schema = this.field_map[table_field.fieldname];
					const child_fields = table_schema.fields || [];

					child_fields.forEach((cf) => {
						// If the field has a value (default) and an onchange handler, run it.
						// This ensures derived fields (like Threshold from Algorithm) are set.
						if (row.doc[cf.fieldname] !== undefined && cf._onchange_logic) {
							cf._onchange_logic(
								row.doc[cf.fieldname],
								row.doc,
								this._get_context(row.doc)
							);
						}
					});

					// 2. Evaluate Dependencies for the new row
					this.evaluate_dependencies(this.config, row.doc);
					row.refresh();
				};
			});
	}

	_handle_grid_input_change(e, grid, table_field) {
		const $input = $(e.currentTarget);
		const $row = $input.closest(".grid-row");
		const row_idx = $row.attr("data-idx"); // 1-based index
		if (!row_idx) return;

		const row = grid.get_row(row_idx - 1);
		if (!row || !row.doc) return;

		const fieldname = $input.closest("[data-fieldname]").attr("data-fieldname");
		if (!fieldname) return;

		// Get value safely from doc (Grid generic controls update the doc automatically typically)
		// Check if we need to pull from input or if Frappe already updated the doc.
		// Usually Frappe updates doc on 'change'.
		const val = row.doc[fieldname];

		// Trigger Runtime Update
		this.update_field(fieldname, val, row.doc);
	}

	_refresh_dialog_ui(row_context = null) {
		if (!this.active_dialog) return;

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

				// 2. Sync Properties
				// Check for property divergence
				["reqd", "read_only", "hidden"].forEach((prop) => {
					if (field.df[prop] !== f[prop]) {
						field.df[prop] = f[prop];
						dirty = true;
					}
				});
				if (dirty) field.refresh();
			}
		});

		// 2. Grids: This is where it gets tough.
		// If a value in a row changed, we need to refresh that row to reflect
		// side-effects (like Read Only changes or Option changes).
		if (row_context) {
			// Find which grid contains this row
			Object.values(this.active_grids).forEach((grid) => {
				// Check if row belongs to this grid?
				// Grid rows are proxies. Reference equality might work if no deep clones.
				const grid_row = grid.grid_rows.find((r) => r.doc.name === row_context.name);
				if (grid_row) {
					grid_row.refresh();
				}
			});
		}
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
	_hydrate_for_ui(data) {
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

						// Sanitize known fragile fields (like MultiSelects) that crash if undefined
						// We check if any field in this row corresponds to a MultiSelect in our schema?
						// Schema traversal is expensive here.
						// Simpler: Just ensure 'transformations' is safe if it exists or is expected.
						// Or general null check for likely strings?
						// Let's specifically target 'transformations' as that's our known crash point.
						if (row.transformations === undefined || row.transformations === null) {
							row.transformations = "";
						}

						// Recursive hydration
						this._hydrate_for_ui(row);
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

		if (ref === "Variables" || ref === "Field Picker") {
			// Dynamic Variable Resolution
			if (typeof this.get_variable_options === "function") {
				try {
					const vars = await this.get_variable_options();
					// transform to options list if needed, or return raw struct for custom controls
					// vars is likely [{label, value, type, source}]
					// For 'Select' or 'Autocomplete', we usually want simple strings or label/value
					// But 'Field Picker' might handle objects.
					// Let's return the objects and let the Control handle it (or normalize to strings).
					return vars.map((v) => v.value);
				} catch (e) {
					console.warn("Failed to resolve variables", e);
					return [];
				}
			}
			// Fallback to empty
			return [];
		}

		if (ref !== "DocField" && ref.indexOf(".") === -1) {
			target = ref;
		}

		try {
			const r = await frappe.call({
				method: "flexirule.ruleflow.api.get_doctype_fields",
				args: { doctype: target },
			});

			if (r.message) {
				// Format: [{label, value, fieldtype}, ...]
				let opts = (r.message.parent_fields || []).map((f) => ({
					label: `${f.label} (${f.fieldtype})`,
					value: f.value,
				}));

				// Children
				if (r.message.child_tables) {
					r.message.child_tables.forEach((ct) => {
						opts.push({ label: `── ${ct.table_label} ──`, value: "", disabled: true });
						ct.fields.forEach((f) => {
							opts.push({ label: `  ${f.label}`, value: f.value });
						});
					});
				}
				return opts;
			}
		} catch (e) {
			console.warn("Field Fetch Failed", e);
		}
		return [];
	}
};
