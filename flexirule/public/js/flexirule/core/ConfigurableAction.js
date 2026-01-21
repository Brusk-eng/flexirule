
//This implementation is to run configuration Dialog from Standard frappe form render.
//Please don't edit for any reason regarding vue based app opended model requirments.
frappe.provide("flexirule.ui");
frappe.provide("flexirule.integration");

import CoreUtils from "./CoreUtils";

flexirule.integration.create_configurable_action = function (opts) {
	return new flexirule.ui.ConfigurableAction(opts);
};


frappe.provide("flexirule.ui");

export default class ConfigurableAction {
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
		this._updating_fields = {}; // Race condition guard
	}

	async init() {
		// Force clear cache for this doctype to ensure fresh metadata (descriptions)
		if (this.document_type) {
			delete flexirule.meta_cache[this.document_type];
			if (flexirule.meta_cache[`${this.document_type}:doc`]) {
				delete flexirule.meta_cache[`${this.document_type}:doc`];
			}
		}

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



	update_field(fieldname, value, row_context = null) {
		// Race Condition Guard: Prevent re-entry for the same field while it's updating
		// We use a composite key for row-level fields
		const lock_key = row_context ? `${row_context.name}:${fieldname}` : fieldname;

		if (this._updating_fields[lock_key]) {
			// Already updating this field, skip (or queue if strict coherence needed, but skip is usually safer for UI loops)
			return Promise.resolve();
		}

		// Asynchronous Sequencing Guard: ensures updates happen in order
		this.current_update_promise = this.current_update_promise.then(async () => {
			this._updating_fields[lock_key] = true;
			try {
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
			} finally {
				delete this._updating_fields[lock_key];
			}
		});

		return this.current_update_promise;
	}

	get_config() {
		return { ...this.config };
	}

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

			// Helper Data
			vars: this._get_vars_dict(),

			// Polyfills for standard Frappe eval helpers
			in_list: (list, item) => list && list.includes(item),
			has_common: (l1, l2) => l1 && l2 && l1.some((i) => l2.includes(i)),

			// The Mutation API
			update_field: (field, val) => this.update_field(field, val, row),
		};
	}



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
		f.fieldtype = CoreUtils.map_fieldtype(f.fieldtype);

		// Use standard Autocomplete
		if (f.fieldtype === "Autocomplete" || f.fieldtype === "DocField") {
			f.fieldtype = "Autocomplete";
			f.options = await this._resolve_docfield_options(f.options);
		} else if (f.fieldtype === "MultiSelectList" || f.fieldtype === "MultiDocField") {
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
				state.hidden = CoreUtils.eval_condition(field.depends_on, eval_context) ? 0 : 1;
			}

			// 2. Mandatory (mandatory_depends_on)
			if (field.mandatory_depends_on) {
				state.reqd = CoreUtils.eval_condition(field.mandatory_depends_on, eval_context) ? 1 : 0;
			}

			// 3. Read Only (read_only_depends_on)
			if (field.read_only_depends_on) {
				state.read_only = CoreUtils.eval_condition(field.read_only_depends_on, eval_context)
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



	_get_vars_dict() {
		return {}; // Placeholder - implement actual var retrieval if needed
	}
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
		let errors = [];

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

					// Collect explicit error message
					errors.push(__("Row #{0}: {1} is required", [row.idx || (row_idx + 1), cf.label || cf.fieldname]));
				}
			});
		});

		if (!grid_valid) {
			if (errors.length > 0) {
				frappe.msgprint({
					title: __("Validation Error in {0}", [table_field.label]),
					message: errors.join("<br>"),
					indicator: "orange"
				});
			}
		}
		return grid_valid;
	}

	validate() {
		// 1. Generic Schema Validation (Unified API)
		// We use dependency_states for accurate visibility/mandatory logic
		const coreValidation = CoreUtils.validate_schema(this.config, this.normalized_fields, this.dependency_states);

		if (!coreValidation.valid) {
			// Maintain legacy behavior: Show error list via msgprint
			// ConfigurableAction usually shows all errors.
			frappe.msgprint({
				title: __("Validation Error"),
				message: `<ul class="text-left">${coreValidation.errors.map(e => `<li>${e}</li>`).join("")}</ul>`,
				indicator: "orange"
			});
			return false;
		}

		// 2. Validate against config_schema (if defined)
		const config_schema = this._get_config_schema();
		if (config_schema && typeof config_schema === "object" && Object.keys(config_schema).length > 0) {
			const schemaErrors = this._validate_against_schema(this.config, config_schema);
			if (schemaErrors.length > 0) {
				frappe.msgprint({
					title: __("Configuration Schema Error"),
					message: `<ul class="text-left">${schemaErrors.map(e => `<li>${e}</li>`).join("")}</ul>`,
					indicator: "red",
				});
				return false;
			}
		}

		// 3. Run adapter's custom validate function
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

	_get_config_schema() {
		// Priority 1: From operation_def (DocType field or adapter-resolved)
		if (this.operation_def?.config_schema) {
			try {
				return typeof this.operation_def.config_schema === "string"
					? JSON.parse(this.operation_def.config_schema)
					: this.operation_def.config_schema;
			} catch (e) {
				console.warn("Failed to parse config_schema:", e);
			}
		}

		// Priority 2: From adapter.get_config_schema if available
		if (this.adapter && typeof this.adapter.get_config_schema === "function") {
			return this._safe_run("get_config_schema", () =>
				this.adapter.get_config_schema(this.operation_name, this._get_context())
			);
		}

		return null;
	}

	_validate_against_schema(config, schema) {
		const errors = [];

		// Simple JSON Schema validation (properties, required, types)
		if (!schema.properties) return errors;

		// Check required fields
		if (schema.required && Array.isArray(schema.required)) {
			for (const fieldname of schema.required) {
				const val = config[fieldname];
				if (val === undefined || val === null || val === "") {
					const prop = schema.properties[fieldname] || {};
					errors.push(__("{0} is required", [prop.title || fieldname]));
				}
			}
		}

		// Check types for each property
		for (const [fieldname, propSchema] of Object.entries(schema.properties)) {
			const val = config[fieldname];
			if (val === undefined || val === null) continue; // Skip missing optional fields

			// Type validation
			if (propSchema.type) {
				const expectedType = propSchema.type;
				const actualType = Array.isArray(val) ? "array" : typeof val;

				if (expectedType === "integer" && typeof val !== "number") {
					errors.push(__("{0} must be a number", [propSchema.title || fieldname]));
				} else if (expectedType === "string" && typeof val !== "string") {
					errors.push(__("{0} must be a string", [propSchema.title || fieldname]));
				} else if (expectedType === "array" && !Array.isArray(val)) {
					errors.push(__("{0} must be an array", [propSchema.title || fieldname]));
				} else if (expectedType === "object" && (typeof val !== "object" || Array.isArray(val))) {
					errors.push(__("{0} must be an object", [propSchema.title || fieldname]));
				}
			}

			// Enum validation
			if (propSchema.enum && Array.isArray(propSchema.enum)) {
				if (!propSchema.enum.includes(val)) {
					errors.push(__("{0} must be one of: {1}", [propSchema.title || fieldname, propSchema.enum.join(", ")]));
				}
			}

			// MinLength validation
			if (propSchema.minLength && typeof val === "string" && val.length < propSchema.minLength) {
				errors.push(__("{0} must be at least {1} characters", [propSchema.title || fieldname, propSchema.minLength]));
			}
		}

		return errors;
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

				this._bind_grid_input_change(grid, table_field);
				this._bind_grid_row_add(grid, table_field);
				this._bind_grid_row_remove(grid, table_field);

				// Initial Refresh to catch pre-loaded rows
				if (grid.grid_rows && grid.grid_rows.length > 0) {
					// We use a microtask to allow grid to fully settle
					setTimeout(() => this._refresh_dialog_ui(), 10);
				}
			});
	}

	_bind_grid_input_change(grid, table_field) {
		// Namespace event to allow clean removal
		// Use passive listeners where possible? Frappe doesn't support that easily here.
		$(grid.wrapper).on("change.flexirule_config", "input, select, textarea", (e) => {
			try {
				this._handle_grid_input_change(e, grid, table_field);
			} catch (err) {
				console.error("FlexiRule: Grid input change error", err);
			}
		});
	}

	_bind_grid_row_add(grid, table_field) {
		const original_add = grid.on_row_add;
		grid.on_row_add = (row) => {
			if (original_add) original_add.call(grid, row);

			// Ensure name for registry
			if (!row.doc.name) {
				row.doc.name = frappe.utils.get_random(10);
			}

			// Table Ownership Marker
			row.doc.__table_fieldname = table_field.fieldname;

			const table_schema = this.field_map[table_field.fieldname];
			const child_fields = table_schema.fields || [];

			// 1. Trigger Runtime Updates for Defaults
			// This ensures that default values defined in the schema are propagated
			// to the internal config model immediately.
			// 4. Force Validation & Refresh on Add
			// New rows need full dependency evaluation
			// We use a small timeout to let Grid finish its internal row setup
			setTimeout(async () => {
				const keys = Object.keys(row.doc);
				// We can't know which fields are relevant easily, so we eval dependencies for the row
				await this.evaluate_dependencies(this.config, row.doc, table_field.fieldname);
				this._refresh_dialog_ui(row.doc);
			}, 50);
		};
	}

	_bind_grid_row_remove(grid, table_field) {
		// Hook into standard grid remove event if available, or patch
		// Frappe Grid doesn't have a clean 'on_remove' hook in some versions,
		// but we can listen to the event if triggered or patch the method.
		// A safer play in standard UI is to listen to the grid wrapper
		if (!grid.wrapper) return;

		// We assume 'grid-row-removed' event might be emitted or we need to intercept
		// In Frappe v13/14, best way is often to override grid.grid_remove_row

		// Guard: method might not exist in all grid implementations
		if (typeof grid.grid_remove_row !== 'function') return;

		const original_remove = grid.grid_remove_row.bind(grid);
		grid.grid_remove_row = (row) => {
			const row_name = row.doc.name;

			// 1. Cleanup State (Memory Leak Fix)
			if (row_name && this.dependency_states[row_name]) {
				delete this.dependency_states[row_name];
			}

			// 2. Call Original
			original_remove(row);

			// 3. Trigger Root Refresh (in case of aggregates)
			// Trigger on parent
			this._handle_change(table_field.fieldname, this.config[table_field.fieldname], null);
		};
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

		// 1. Root Fields: Sync Properties & Value
		this.normalized_fields.forEach((f) => {
			this._sync_root_field(f);
		});

		// 2. Grids: Isolate & Update Rows
		Object.values(this.active_grids).forEach((grid) => {
			if (!grid.df || !grid.df.fields) return;
			const shared_fields = grid.df.fields;

			grid.grid_rows.forEach((row) => {
				if (!row.doc) return;
				this._sync_grid_row(row, grid, shared_fields);
			});
		});

		this._refreshing_ui = false;
	}

	/**
	 * Syncs a single root field's value and properties (reqd, read_only, hidden)
	 * between the config model and the UI control.
	 */
	_sync_root_field(f) {
		if (f.fieldtype === "Section Break" || f.fieldtype === "Column Break") return;

		// Table Handling (Special Sync for Grids)
		if (f.fieldtype === "Table") {
			const grid_obj = this.active_dialog.fields_dict[f.fieldname];
			if (grid_obj && grid_obj.grid) {
				const model_val = this.config[f.fieldname] || [];
				const grid_val = grid_obj.grid.get_data() || [];

				// Sync Model -> Grid (Programmatic Updates)
				if (JSON.stringify(model_val) !== JSON.stringify(grid_val)) {
					grid_obj.grid.df.data = model_val;
					grid_obj.grid.refresh();
				}

				// Sync Properties
				["reqd", "read_only", "hidden"].forEach((prop) => {
					if (grid_obj.df[prop] !== f[prop]) {
						grid_obj.df[prop] = f[prop];
						grid_obj.refresh();
					}
				});
			}
			return;
		}

		const field = this.active_dialog.fields_dict[f.fieldname];
		if (field) {
			let dirty = false;

			// Sync Value
			const model_val = this.config[f.fieldname];
			const ui_val = field.get_value();
			if (model_val !== ui_val && JSON.stringify(model_val) !== JSON.stringify(ui_val)) {
				try {
					field.set_value(model_val);
				} catch (e) {
					console.warn("Sync error", e);
				}
			}

			// Sync Properties
			const runtime_state = (this.dependency_states["root"] || {})[f.fieldname] || {};
			["reqd", "read_only", "hidden"].forEach((prop) => {
				const target_val = runtime_state[prop] !== undefined ? runtime_state[prop] : f[prop];
				if (field.df[prop] !== target_val) {
					field.df[prop] = target_val;
					if (prop === "read_only" && typeof field.set_read_only === "function") {
						field.set_read_only(target_val);
					}
					dirty = true;
				}
			});

			// Sync Options
			if (runtime_state.options !== undefined && runtime_state.options !== null) {
				if (JSON.stringify(field.df.options) !== JSON.stringify(runtime_state.options)) {
					field.df.options = runtime_state.options;
					dirty = true;
				}
			}

			if (dirty) field.refresh();
		}
	}

	_sync_grid_row(row, grid, shared_fields) {
		// A. ENFORCE ISOLATION
		// Ensure every row has its OWN field definitions.
		// If row.docfields is missing or points to shared array, CLONE IT.
		if (
			!row.docfields ||
			row.docfields === shared_fields ||
			!row._flexirule_isolated
		) {
			const source = row.docfields || shared_fields || [];
			row.docfields = source.map((df) => ({ ...df })); // Deep-ish clone (new objects)
			row.docfields.forEach(df => df._flexirule_isolated = true);
			row._flexirule_isolated = true;

			// Force immediate re-render to bind columns to these new DFs
			// This is cleaner than manual patching here.
			row.refresh();
		}

		// Get latest state
		const row_state = this.dependency_states[row.doc.name] || {};
		let row_dirty = false;
		const child_fields = grid.df.fields || [];

		child_fields.forEach((cf) => {
			// Skip layout fields for value/control sync
			if (["Section Break", "Column Break"].includes(cf.fieldtype)) return;

			// B. FIND LOCAL DEFINITION
			// We must modify ONLY the definition belonging to this row.
			const isolated_df = row.docfields.find((d) => d.fieldname === cf.fieldname);
			if (!isolated_df) return;

			// C. SYNC VALUES & REFERENCE SAFETY
			let control = null;
			try {
				// GridRow.get_field throws string exception if not found!
				control = row.get_field(cf.fieldname);
			} catch (e) {
				// Fallback to simple column lookup if form field not active
				control = row.columns ? row.columns[cf.fieldname] : null;
			}

			if (control) {
				// JUST-IN-TIME REFERENCE PATCHING
				// If the control's DF doesn't match our isolated DF, patch it now.
				// This catches any controls created before isolation or by rogue refresh.
				if (control.df !== isolated_df) {
					control.df = isolated_df;
				}

				// Sync Value
				const model_val = row.doc[cf.fieldname];
				const ui_val = control.get_value ? control.get_value() : control.value;
				if (model_val !== ui_val && JSON.stringify(model_val) !== JSON.stringify(ui_val)) {
					if (typeof control.set_value === "function") {
						control.set_value(model_val);
					} else {
						control.value = model_val;
						if (control.refresh) control.refresh();
					}
				}
			}

			// D. APPLY PROPERTIES
			// Now it's safe to mutate isolated_df properties.
			const state = row_state[cf.fieldname];
			if (!state) return;

			let prop_changed = false;
			// Apply properties
			const apply_prop = (prop, val) => {
				if (isolated_df[prop] !== val) {
					isolated_df[prop] = val;
					// If we have the control, apply directly too for instant feedback 
					// (avoiding full row refresh if possible)
					if (control) {
						if (control.df !== isolated_df) {
							control.df = isolated_df; // Patch grid cell ref
						}
						if (prop === 'read_only' && control.set_read_only) control.set_read_only(val);
						if (prop === 'hidden' && control.toggle_display) control.toggle_display(!val);
						if (prop === 'reqd' && control.set_working_mandatory) control.set_working_mandatory(val);
					}

					// CRITICAL: Also update the Grid Form (Modal) control if it exists!
					if (row.grid_form && row.grid_form.fields_dict && row.grid_form.fields_dict[cf.fieldname]) {
						const form_control = row.grid_form.fields_dict[cf.fieldname];
						// Ensure it shares the isolated DF
						if (form_control.df !== isolated_df) form_control.df = isolated_df;

						// Apply Prop
						if (prop === 'read_only' && form_control.set_read_only) form_control.set_read_only(val);
						if (prop === 'hidden' && form_control.toggle_display) form_control.toggle_display(!val);
						if (prop === 'reqd' && form_control.set_working_mandatory) form_control.set_working_mandatory(val);
					}

					prop_changed = true;
					row_dirty = true;
				}
			};

			if (state.read_only !== undefined) apply_prop("read_only", state.read_only);
			if (state.hidden !== undefined) apply_prop("hidden", state.hidden);
			if (state.reqd !== undefined) apply_prop("reqd", state.reqd);

			if (state.options !== undefined && state.options !== null) {
				// Optimization: Use deep equality instead of stringify
				// frappe.utils.deep_equal is standard, fallback if missing
				const is_equal = frappe.utils.deep_equal
					? frappe.utils.deep_equal(isolated_df.options, state.options)
					: JSON.stringify(isolated_df.options) === JSON.stringify(state.options);

				if (!is_equal) {
					isolated_df.options = state.options;
					if (control && control.set_options) control.set_options(state.options);
					row_dirty = true;
				}
			}
		});

		// E. FINAL REFRESH
		// If properties changed structurally (hidden/reqd), refresh the row entirely
		// to ensure layout verification and valid state.
		if (row_dirty) {
			row.refresh();
		}
	}



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

			// Resolve and save output schema
			const output_schema = this._resolve_output_schema(clean_config);
			if (output_schema) {
				this.node_data.resolved_output_schema = JSON.stringify(output_schema);
			} else {
				this.node_data.resolved_output_schema = null;
			}
		}
	}

	_resolve_output_schema(config) {
		// Priority 1: Adapter.get_output_schema(config, context)
		if (this.adapter && typeof this.adapter.get_output_schema === "function") {
			const schema = this._safe_run("get_output_schema", () =>
				this.adapter.get_output_schema(config, this._get_context())
			);
			if (schema) return schema;
		}

		// Priority 2: Operation Definition output_schema
		if (this.operation_def?.output_schema) {
			try {
				return typeof this.operation_def.output_schema === "string"
					? JSON.parse(this.operation_def.output_schema)
					: this.operation_def.output_schema;
			} catch (e) {
				console.warn("Failed to parse static output_schema:", e);
			}
		}

		return null;
	}

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
flexirule.ui.ConfigurableAction = ConfigurableAction;