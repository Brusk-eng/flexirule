/**
 * FlexiRule Integration Bridge for Rule Builder
 *
 * This module provides integration between the new FlexiRule runtime
 * and the existing Rule Builder configurable_action.js.
 *
 * It provides a migration path where the new runtime can be used
 * alongside or instead of the existing Dialog-based implementation.
 */

frappe.provide("flexirule.integration");
console.log("[FlexiRule] Integration Bridge Loading...");

/**
 * Creates a ConfigurableAction dialog using the new FlexiRule runtime.
 *
 * This is a drop-in replacement for flexirule.ui.ConfigurableAction.show_dialog()
 * that uses the new runtime internally.
 *
 * @param {Object} opts - Options
 * @param {string} opts.process_name - Process name (e.g., 'Deduplication')
 * @param {string} opts.operation_name - Operation name (e.g., 'find_similar_records')
 * @param {Object} opts.node_data - Node data containing config
 * @param {string} opts.document_type - Document type context
 * @param {Object} opts.doc_meta - Document metadata
 * @param {Function} opts.on_save - Save callback
 * @returns {Promise<frappe.ui.Dialog>}
 */
flexirule.integration.show_config_dialog = async function (opts) {
	const { process_name, operation_name, node_data, document_type, doc_meta, on_save } = opts;

	// 1. Get process adapter directly
	const process_adapter = flexirule.processes[process_name];
	if (!process_adapter) {
		frappe.msgprint(__("Process adapter not found: {0}", [process_name]));
		return null;
	}

	// Create a compatible adapter object using the process adapter's methods
	const adapter = {
		process_name: process_name,
		operation_name: operation_name,
		context: {
			document_type: document_type,
			doc_meta: doc_meta,
		},

		get_default_config() {
			return process_adapter.get_default_config(operation_name, {
				document_type: document_type,
				doc_meta: doc_meta,
				parent: {
					document_type: document_type,
				},
			});
		},

		get_ui_schema(config) {
			return process_adapter.get_ui_schema(operation_name, config, {
				document_type: document_type,
				doc_meta: doc_meta,
				parent: {
					document_type: document_type,
				},
			});
		},

		validate(config) {
			return process_adapter.validate(operation_name, config, {
				document_type: document_type,
				doc_meta: doc_meta,
				parent: {
					document_type: document_type,
				},
			});
		},
	};

	// 2. Load initial config from node
	let initial_config = {};
	if (node_data?.config) {
		try {
			initial_config =
				typeof node_data.config === "object"
					? node_data.config
					: JSON.parse(node_data.config);
		} catch (e) {
			initial_config = {};
		}
	}

	// 3. Create ConfigurableAction
	const configurable_action = new flexirule.ConfigurableAction({
		action_type: "process",
		adapter: adapter,
		initial_config: initial_config,
		on_change: (config) => {
			// Optional: Track dirty state
		},
	});

	// 4. Get operation label
	const process_op_adapter = flexirule.processes[process_name];
	const operation = process_op_adapter?.get_operation?.(operation_name);
	const title = operation?.label || operation_name;

	// 5. Create Dialog
	const dialog = new frappe.ui.Dialog({
		title: __(title),
		size: "extra-large",
		fields: [
			{
				fieldname: "config_area",
				fieldtype: "HTML",
			},
		],
		primary_action_label: __("Save"),
		primary_action: () => {
			// Validate
			const validation = configurable_action.validate();

			if (!validation.valid) {
				frappe.msgprint({
					title: __("Validation Error"),
					indicator: "red",
					message: validation.errors.map((e) => e.message).join("<br>"),
				});
				return;
			}

			// Get config
			const config = configurable_action.get_config();

			// Save to node (as JSON string for Rule Builder compatibility)
			if (node_data) {
				node_data.config = JSON.stringify(config, null, 2);
			}

			// Callback
			if (on_save) {
				on_save(config);
			}

			// Cleanup
			ui_runtime.destroy();
			dialog.hide();
		},
	});

	// 6. Render UIRuntime into dialog
	const $container = dialog.fields_dict.config_area.$wrapper;
	const ui_runtime = new flexirule.UIRuntime({
		parent: $container,
		configurable_action: configurable_action,
		context: {
			doc: initial_config,
			document_type: document_type,
			doctype: document_type,
		},
	});

	ui_runtime.render();
	dialog.show();

	// Cleanup on close
	dialog.$wrapper.on("hidden.bs.modal", () => {
		ui_runtime.destroy();
		configurable_action.destroy();
	});

	return dialog;
};

/**
 * Wrapper class that mimics flexirule.ui.ConfigurableAction API
 * but uses the new runtime internally.
 *
 * This allows gradual migration - you can swap implementations
 * per action type.
 */
flexirule.integration.ConfigurableActionV2 = class ConfigurableActionV2 {
	constructor(opts) {
		Object.assign(this, opts);
		this.config = this._load_config();

		// Internal state
		this._adapter = null;
		this._action = null;
		this._runtime = null;
		this.active_dialog = null;
	}

	async init() {
		// Resolve variables if callback exists
		let context_vars = {};
		if (typeof this.get_variable_options === "function") {
			const vars = await this.get_variable_options();
			// Transform to format expected by FieldSelector
			vars.forEach((v) => {
				const source = v.source === "Document" ? "doc" : v.source || "vars";
				context_vars[source] = context_vars[source] || { fields: [] };
				context_vars[source].fields.push({
					fieldname: v.fieldname,
					label: v.label,
					fieldtype: v.type,
				});
			});
		}

		// Get process adapter directly
		const proc_adapter = flexirule.processes[this.process_name];
		if (!proc_adapter) {
			throw new Error(__("Process adapter not found: {0}", [this.process_name]));
		}

		// Create a compatible adapter object using the process adapter's methods
		this._adapter = {
			process_name: this.process_name,
			operation_name: this.operation_name,
			context: {
				document_type: this.document_type,
				doc_meta: this.doc_meta,
				context_vars: context_vars,
			},

			get_default_config() {
				return proc_adapter.get_default_config(this.operation_name, {
					document_type: this.document_type,
					doc_meta: this.doc_meta,
					context_vars: context_vars,
					parent: {
						document_type: this.document_type,
					},
				});
			},

			get_ui_schema(config) {
				return proc_adapter.get_ui_schema(this.operation_name, config, {
					document_type: this.document_type,
					doc_meta: this.doc_meta,
					context_vars: context_vars,
					parent: {
						document_type: this.document_type,
					},
				});
			},

			validate(config) {
				return proc_adapter.validate(this.operation_name, config, {
					document_type: this.document_type,
					doc_meta: this.doc_meta,
					context_vars: context_vars,
					parent: {
						document_type: this.document_type,
					},
				});
			},
		};

		// Create ConfigurableAction
		this._action = new flexirule.ConfigurableAction({
			action_type: "process",
			adapter: this._adapter,
			initial_config: this.config,
		});
	}

	async show_dialog(opts = {}) {
		if (!this._adapter) await this.init();

		this.active_dialog = await flexirule.integration.show_config_dialog({
			process_name: this.process_name,
			operation_name: this.operation_name,
			node_data: this.node_data,
			document_type: this.document_type,
			doc_meta: this.doc_meta,
			get_variable_options: this.get_variable_options,
			on_save: (config) => {
				this.config = config;
				if (opts.on_save) opts.on_save(config);
				if (this.on_save_callback) this.on_save_callback(config);
			},
		});

		return this.active_dialog;
	}

	get_config() {
		return this._action ? this._action.get_config() : this.config;
	}

	update_field(fieldname, value) {
		if (this._action) {
			this._action.set_value(fieldname, value);
		} else {
			this.config[fieldname] = value;
		}
	}

	validate() {
		if (this._action) {
			return this._action.validate().valid;
		}
		return true;
	}

	_load_config() {
		const raw = this.node_data?.config || this.node_data?.method_config;
		if (!raw) return {};
		try {
			return typeof raw === "object" ? raw : JSON.parse(raw);
		} catch (e) {
			return {};
		}
	}
};

/**
 * Feature flag to control which implementation to use.
 * Set to true to use the new runtime, false for legacy.
 */
flexirule.integration.USE_NEW_RUNTIME = false;

/**
 * Factory that returns either V1 or V2 ConfigurableAction based on feature flag.
 */
flexirule.integration.create_configurable_action = function (opts) {
	if (flexirule.integration.USE_NEW_RUNTIME) {
		return new flexirule.integration.ConfigurableActionV2(opts);
	} else {
		return new flexirule.ui.ConfigurableAction(opts);
	}
};
