import ProcessRuntime from "./ProcessRuntime.js";
import AsyncJobQueue from "./AsyncJobQueue.js";

/**
 * ProcessConfigurator
 * Bridge for standard Frappe forms to use FlexiRule Process Adapters.
 */
export default class ProcessConfigurator extends ProcessRuntime {
	constructor(opts) {
		super(opts);

		// State
		this.config = this._load_config(opts.node_data);

		// UI Binding
		this.active_dialog = null;
		this.active_grids = {};

		// Async Sequencing
		this.job_queue = new AsyncJobQueue();

		// Recursion Guards
		this._refreshing_ui = false;
		this._disposed = false;

		// Default variable resolver
		if (!this.get_variable_options) {
			this.get_variable_options = async () => {
				return await this._fetch_variables_from_server();
			};
		}
	}

	async init() {
		if (this.initialized) return;

		if (this.document_type && !this.doc_meta) {
			try {
				this.doc_meta = await flexirule.utils.get_doctype_meta(this.document_type);
			} catch (e) {
				console.warn("ProcessConfigurator: Failed to load meta", e);
			}
		}

		await super.init();
	}

	_load_config(node_data) {
		if (!node_data) return {};
		let config = node_data.config && node_data.config !== "null" ? node_data.config : {};
		if (typeof config === "string" && config.trim()) {
			try {
				config = JSON.parse(config);
			} catch (e) {
				config = {};
			}
		}
		return config;
	}

	async update_field(fieldname, value, row_context = null) {
		const key = row_context ? `${row_context.name}:${fieldname}` : fieldname;

		return this.job_queue.run(key, async () => {
			if (row_context) {
				row_context[fieldname] = value;
			} else {
				this.config[fieldname] = value;
			}
			await this._handle_change(fieldname, value, row_context);
		});
	}

	async _handle_change(fieldname, value, row_context) {
		if (row_context) {
			const table_fieldname =
				row_context.__table_fieldname || this._find_table_of_row(row_context);
			if (table_fieldname) row_context.__table_fieldname = table_fieldname;

			await this.evaluate_dependencies(
				this.config,
				row_context,
				table_fieldname,
				this.normalized_fields
			);
		} else {
			await this.evaluate_dependencies(this.config, null, null, this.normalized_fields);
			for (const [table_fieldname, grid] of Object.entries(this.active_grids)) {
				for (const row of grid.grid_rows || []) {
					if (row.doc) {
						row.doc.__table_fieldname = table_fieldname;
						await this.evaluate_dependencies(
							this.config,
							row.doc,
							table_fieldname,
							this.normalized_fields
						);
					}
				}
			}
		}

		const field_def = this.field_map[fieldname];
		if (field_def && typeof field_def._onchange_logic === "function") {
			await field_def._onchange_logic(value, row_context, this._get_context(row_context));
		}

		if (this.active_dialog) {
			this._refresh_dialog_ui(row_context, fieldname);
		}
	}

	_find_table_of_row(row) {
		for (const [fieldname, val] of Object.entries(this.config)) {
			if (Array.isArray(val) && val.some((r) => r.name === row.name || r === row)) {
				return fieldname;
			}
		}
		return null;
	}

	_get_context(row = null) {
		return {
			doc: row || this.config,
			row: row,
			parent: this.config,
			config: this.config,
			document_type: this.document_type,
			process_name: this.process_name,
			operation_name: this.operation_name,
			meta: this.doc_meta,
			doc_meta: this.doc_meta,
			vars: this._get_vars_dict(),
			in_list: (list, item) => list && list.includes(item),
			has_common: (l1, l2) => l1 && l2 && l1.some((i) => l2.includes(i)),
			update_field: (field, val) => this.update_field(field, val, row),
		};
	}

	_get_vars_dict() {
		return {};
	}

	async _fetch_variables_from_server() {
		if (!this.document_type) return [];
		const rule_name =
			this.node_data?.parent ||
			(frappe.get_route()[0] === "Form" && frappe.get_route()[1] === "Rule"
				? frappe.get_route()[2]
				: null);
		const action_id = this.node_data?.action_id;
		if (rule_name && action_id) {
			try {
				const r = await frappe.call({
					method: "flexirule.ruleflow.api.get_action_context_schema",
					args: { rule_name, action_id },
				});
				return r.message || [];
			} catch (e) {
				console.warn("ProcessConfigurator: Failed to fetch context schema", e);
			}
		}
		return [];
	}

	async show_dialog(opts = {}) {
		if (!this.initialized) await this.init();

		const dialog = new frappe.ui.Dialog({
			title: this.operation_def?.label || this.operation_name,
			fields: this.normalized_fields,
			size: "extra-large",
			primary_action: () => {
				const values = dialog.get_values();
				if (!values) return;

				Object.keys(this.active_grids).forEach((fieldname) => {
					const grid = this.active_grids[fieldname];
					if (grid) values[fieldname] = grid.get_data() || [];
				});

				Object.assign(this.config, values);

				const validation = this.validate();
				if (!validation.valid) {
					frappe.msgprint(validation.errors.join("<br>"));
					return;
				}

				this._sync_to_node();
				if (typeof opts.on_save === "function") opts.on_save(this.config);
				dialog.hide();
			},
		});

		this.active_dialog = dialog;

		const original_on_hide = dialog.on_hide;
		dialog.on_hide = () => {
			this.active_grids = {};
			this.active_dialog = null;
			if (typeof original_on_hide === "function") original_on_hide.call(dialog);
			this.dispose();
		};

		dialog.set_values(this.config);

		this.normalized_fields
			.filter((f) => f.fieldtype === "Table")
			.forEach((tf) => {
				const field = dialog.fields_dict[tf.fieldname];
				if (field && field.grid) {
					const grid = field.grid;
					this.active_grids[tf.fieldname] = grid;

					if (this.config[tf.fieldname]) {
						grid.df.data = this.config[tf.fieldname];
						grid.refresh();
					}

					// Ultra-reliable column-level hooking
					grid.df.fields.forEach((df) => {
						// 1. Value change hook
						const original_change = df.change;
						df.change = function () {
							const me = this;
							const row = me.grid_row ? me.grid_row.doc : null;
							if (row) {
								row.__table_fieldname = tf.fieldname;
								dialog._flexirule_configurator.update_field(
									df.fieldname,
									me.get_value(),
									row
								);
							}
							if (typeof original_change === "function") original_change.call(me);
						};

						// 2. Data source hook for Autocomplete
						if (df.fieldtype === "Autocomplete") {
							df.get_data = function () {
								const me = this;
								const row = me.grid_row ? me.grid_row.doc : null;
								const context_id = row ? row.name : "root";
								const table_ctx_id = tf.fieldname;

								const configurator = dialog._flexirule_configurator;
								const state =
									(configurator.dependency_states[context_id] || {})[
										df.fieldname
									] ||
									(configurator.dependency_states[table_ctx_id] || {})[
										df.fieldname
									];

								return state?.options || df.options || [];
							};
						}
					});
				}
			});

		dialog._flexirule_configurator = this;

		this._bind_dialog_events(dialog);

		const custom_actions = this._resolve_actions();
		custom_actions.forEach((action) => {
			dialog.add_custom_button(__(action.label), () => {
				action.click(this.config, this._get_context());
			});
		});

		dialog.show();
		this._refresh_dialog_ui();

		return dialog;
	}

	_bind_dialog_events(dialog) {
		this.normalized_fields.forEach((df) => {
			if (["Section Break", "Column Break", "HTML", "Button", "Table"].includes(df.fieldtype))
				return;
			const field = dialog.fields_dict[df.fieldname];
			if (!field) return;

			const original_change = field.df.change;
			field.df.change = () => {
				if (this._refreshing_ui) return;
				this.job_queue.run(df.fieldname, async () => {
					const val = dialog.get_value(df.fieldname);
					if (this.config[df.fieldname] !== val) {
						this.config[df.fieldname] = val;
						await this._handle_change(df.fieldname, val);
					}
				});
				if (typeof original_change === "function") original_change.call(field);
			};
		});
	}

	_refresh_dialog_ui(row_context = null, trigger_field = null) {
		if (this._refreshing_ui || !this.active_dialog) return;
		this._refreshing_ui = true;

		try {
			const context_id = row_context ? row_context.name : "root";
			const state = this.dependency_states[context_id] || {};

			if (!row_context) {
				// Refresh main dialog fields
				Object.keys(state).forEach((fieldname) => {
					const field_state = state[fieldname];
					const field = this.active_dialog.fields_dict[fieldname];
					if (!field) return;

					this.active_dialog.set_df_property(fieldname, "hidden", field_state.hidden);
					this.active_dialog.set_df_property(fieldname, "reqd", field_state.reqd);
					this.active_dialog.set_df_property(
						fieldname,
						"read_only",
						field_state.read_only
					);
					if (field_state.options !== null) {
						this.active_dialog.set_df_property(
							fieldname,
							"options",
							field_state.options
						);
					}

					if (trigger_field && trigger_field !== fieldname) {
						if (this.active_dialog.get_value(fieldname) !== this.config[fieldname]) {
							this.active_dialog.set_value(fieldname, this.config[fieldname]);
						}
					}
				});

				// Refresh Grid Columns options
				Object.keys(this.active_grids).forEach((table_fieldname) => {
					const grid = this.active_grids[table_fieldname];
					const column_states = this.dependency_states[table_fieldname] || {};
					grid.df.fields.forEach((df) => {
						const col_state = column_states[df.fieldname];
						if (col_state && col_state.options !== null) {
							df.options = col_state.options;
						}
					});
					grid.refresh();
				});
			} else {
				// Refresh grid row fields
				const table_name =
					row_context.__table_fieldname || this._find_table_of_row(row_context);
				const grid = this.active_grids[table_name];
				if (grid) {
					const row_obj = grid.get_row ? grid.get_row(row_context.name) : null;
					if (row_obj) {
						Object.keys(state).forEach((fieldname) => {
							const field_state = state[fieldname];

							// SKIP Section Breaks and Column Breaks (not standard fields in GridRow)
							const field_def = this.field_map[fieldname];
							if (
								field_def &&
								["Section Break", "Column Break", "HTML"].includes(
									field_def.fieldtype
								)
							)
								return;

							if (typeof row_obj.toggle_display === "function") {
								row_obj.toggle_display(fieldname, !field_state.hidden);
							}
							if (typeof row_obj.toggle_editable === "function") {
								row_obj.toggle_editable(fieldname, !field_state.read_only);
							}
							if (field_state.options !== null) {
								try {
									const field_obj = row_obj.get_field(fieldname);
									if (field_obj) field_obj.df.options = field_state.options;
								} catch (e) {
									// Silent catch if get_field fails
								}
							}
							if (trigger_field && trigger_field !== fieldname) {
								if (typeof row_obj.refresh_field === "function") {
									row_obj.refresh_field(fieldname);
								}
							}
						});
					}
				}
			}
		} finally {
			this._refreshing_ui = false;
		}
	}

	_sync_to_node() {
		if (this.node_data) {
			this.node_data.config =
				this.config && Object.keys(this.config).length ? JSON.stringify(this.config) : "";
		}
	}

	dispose() {
		if (this._disposed) return;
		this._disposed = true;
		this.active_dialog = null;
		this.active_grids = {};
	}
}

frappe.provide("flexirule.ui");
frappe.provide("flexirule.integration");

flexirule.integration.create_configurable_action = function (opts) {
	return new ProcessConfigurator(opts);
};

flexirule.ui.ProcessConfigurator = ProcessConfigurator;
flexirule.ui.ConfigurableAction = ProcessConfigurator;
