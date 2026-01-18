/*******************************************************
 * Rule (Parent)
 *******************************************************/
frappe.ui.form.on("Rule", {
	onload(frm) {
		frm._process_ops_cache = {};

		const grid = frm.get_field("actions").grid;
		const op_field = grid.get_field("operation");

		// Set get_data once on the column field - most robust for Autocomplete
		op_field.get_data = function () {
			const row = this.grid_row.doc;
			if (!row || !row.process_name || row.action_type !== "Process") return [];

			const cached = frm._process_ops_cache[row.process_name];
			if (cached) {
				return cached.map(op => ({ value: op, description: "" }));
			}

			// Fallback: fetch and return promise
			return frappe.call({
				method: "flexirule.ruleflow.api.get_process_operations",
				args: { process_name: row.process_name },
			}).then(r => {
				const ops = r.message || [];
				frm._process_ops_cache[row.process_name] = ops;
				return ops.map(op => ({ value: op, description: "" }));
			});
		};
	},

	refresh(frm) {
		if (frm.is_new()) return;

		// Primary action
		frm.page.clear_primary_action();
		frm.page.set_primary_action(__("Visual Builder"), () => {
			frappe.set_route("rule-builder", frm.doc.name);
		});

		// Actions
		frm.page.clear_custom_actions();
		frm.add_custom_button(__("Test Rule"), () => test_rule(frm), __("Actions"));
		frm.add_custom_button(__("Clear Cache"), () => clear_rule_cache(frm), __("Actions"));

		if (frm.dashboard) {
			frm.dashboard.clear_headline();
			if (frm.doc.execution_count) {
				frm.dashboard.add_indicator(
					__("Executed {0} times", [frm.doc.execution_count]),
					"blue"
				);
			}
			if (frm.doc.last_error) {
				frm.dashboard.add_indicator(__("Has Errors"), "red");
			}
		}

		// Initialize operation options for all rows
		if (frm.doc.actions && frm.doc.actions.length) {
			frm.doc.actions.forEach(row => {
				update_operation_options(frm, "Rule Action", row.name);
			});
		}
	},

	before_insert(frm) {
		if (
			frm.doc.document_type &&
			frm.doc.trigger_event &&
			(!frm.doc.actions || !frm.doc.actions.length)
		) {
			const row = frm.add_child("actions", {
				action_id: "root",
				action_type: "Entry Action",
				is_enabled: 1,
			});
			frm.refresh_field("actions");
		}
	},
});

/*******************************************************
 * Rule Action (Child Table)
 *******************************************************/
frappe.ui.form.on("Rule Action", {
	form_render(frm, cdt, cdn) {
		toggle_action_fields(frm, cdt, cdn);
		update_operation_options(frm, cdt, cdn);
	},

	refresh(frm, cdt, cdn) {
		toggle_action_fields(frm, cdt, cdn);
		update_operation_options(frm, cdt, cdn);
	},

	action_type(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.action_type !== "Process") {
			frappe.model.set_value(cdt, cdn, "process_name", null);
			frappe.model.set_value(cdt, cdn, "operation", null);
			frappe.model.set_value(cdt, cdn, "config", null);
		}
		toggle_action_fields(frm, cdt, cdn);
	},

	process_name(frm, cdt, cdn) {
		// reset operation when process changes
		frappe.model.set_value(cdt, cdn, "operation", null);
		frappe.model.set_value(cdt, cdn, "config", null);
		update_operation_options(frm, cdt, cdn);
	},

	// Button field from DocType
	configure_operation(frm, cdt, cdn) {
		configure_operation_from_form(frm, cdt, cdn);
	},
});

/*******************************************************
 * Field Visibility (Grid-safe)
 *******************************************************/
function toggle_action_fields(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const grid = frm.get_field("actions").grid;
	const grid_row = grid.get_row(cdn);

	if (!grid_row) return;

	const hide_all = [
		"process_name",
		"operation",
		"config",
		"timeout",
		"retry_count",
		"is_async",
		"on_error",
		"condition_expression",
		"condition_json",
		"next_step_if_false",
		"rule",
		"skip_conditions",
		"skip_permissions",
		"configure_operation",
	];

	hide_all.forEach(f => grid_row.toggle_display(f, false));

	switch (row.action_type) {
		case "Process":
			[
				"process_name",
				"operation",
				"config",
				"timeout",
				"is_async",
				"on_error",
				"configure_operation",
			].forEach(f => grid_row.toggle_display(f, true));
			break;

		case "Condition":
			[
				"condition_expression",
				"condition_json",
				"next_step_if_false",
			].forEach(f => grid_row.toggle_display(f, true));
			break;

		case "Sub-Rule":
			[
				"rule",
				"skip_conditions",
				"skip_permissions",
			].forEach(f => grid_row.toggle_display(f, true));
			break;
	}
}

/*******************************************************
 * Dynamic Autocomplete Options for `operation`
 *******************************************************/
function update_operation_options(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row || !row.process_name || row.action_type !== "Process") return;

	const grid = frm.get_field("actions").grid;
	// Use row.name if available, else cdn. More stable for existing rows.
	const grid_row = grid.get_row(row.name || cdn);

	if (!grid_row) return;

	const apply_ops = (ops) => {
		const field = grid_row.get_field("operation");
		if (field) {
			field.df.options = ops.join("\n");
			// Autocomplete might need set_data for immediate effect in some versions
			if (field.set_data) field.set_data(ops);
			field.refresh();
		}
	};

	// Use cache if available
	if (frm._process_ops_cache && frm._process_ops_cache[row.process_name]) {
		apply_ops(frm._process_ops_cache[row.process_name]);
		return;
	}

	frappe.call({
		method: "flexirule.ruleflow.api.get_process_operations",
		args: {
			process_name: row.process_name,
		},
	}).then(r => {
		const ops = r.message || [];
		frm._process_ops_cache = frm._process_ops_cache || {};
		frm._process_ops_cache[row.process_name] = ops;
		apply_ops(ops);
	});
}

/*******************************************************
 * Configure Operation Dialog
 *******************************************************/
async function configure_operation_from_form(frm, cdt, cdn) {
	const row = locals[cdt][cdn];

	if (!row.process_name || !row.operation) {
		frappe.msgprint(__("Please select a Process and Operation first"));
		return;
	}

	// Guard: Prevent double-execution (double dialogs)
	if (row.__configuring) return;
	row.__configuring = true;

	try {
		if (typeof flexirule === "undefined") {
			await frappe.require("flexirule.bundle.js");
		}

		const action = flexirule.integration.create_configurable_action({
			process_name: row.process_name,
			operation_name: row.operation,
			node_data: row,
			document_type: frm.doc.document_type,
			get_variable_options: async () => [],
		});

		await action.init();

		action.show_dialog({
			on_save() {
				frappe.model.set_value(
					cdt,
					cdn,
					"config",
					JSON.stringify(action.get_config(), null, 2)
				);

				frappe.show_alert({
					message: __("Configuration saved"),
					indicator: "green",
				});
			},
		});

		// Reset guard when dialog is hidden
		if (action.active_dialog) {
			const original_on_hide = action.active_dialog.on_hide;
			action.active_dialog.on_hide = () => {
				row.__configuring = false;
				if (original_on_hide) original_on_hide();
			};
		} else {
			row.__configuring = false;
		}

	} catch (e) {
		row.__configuring = false;
		console.error(e);
		frappe.msgprint({
			message: __("Failed to configure operation"),
			indicator: "red",
		});
	}
}

/*******************************************************
 * Utilities
 *******************************************************/
function test_rule(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Test Rule"),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "doctype",
				options: "DocType",
				label: __("Document Type"),
				default: frm.doc.document_type,
				reqd: 1,
			},
			{
				fieldtype: "Dynamic Link",
				fieldname: "docname",
				options: "doctype",
				label: __("Document"),
				reqd: 1,
			},
		],
		primary_action_label: __("Test"),
		primary_action(values) {
			frappe.call({
				method: "flexirule.ruleflow.api.test_rule",
				args: {
					rule_name: frm.doc.name,
					doctype: values.doctype,
					docname: values.docname,
				},
				callback(r) {
					frappe.msgprint({
						title: r.message?.success ? __("Success") : __("Failed"),
						message: r.message?.message || r.message?.error,
						indicator: r.message?.success ? "green" : "red",
					});
					d.hide();
				},
			});
		},
	});
	d.show();
}

function clear_rule_cache(frm) {
	frappe.call({
		method: "flexirule.ruleflow.api.clear_cache",
		args: { doctype: frm.doc.document_type },
		callback() {
			frappe.show_alert({ message: __("Cache cleared"), indicator: "green" });
		},
	});
}
