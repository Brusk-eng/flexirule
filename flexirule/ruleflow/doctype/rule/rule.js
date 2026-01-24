frappe.ui.form.on("Rule", {
	onload(frm) {
		frm._process_ops_cache = {};

		const grid = frm.get_field("actions").grid;
		const op_field = grid.get_field("operation");

		op_field.get_data = function () {
			const row = this.grid_row.doc;
			if (!row || !row.process_name || row.action_type !== "Process") return [];

			const cached = frm._process_ops_cache[row.process_name];
			if (cached) {
				return cached.map(op => ({ value: op, description: "" }));
			}

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

	is_active(frm) {
		if (frm.doc.is_active === 0 && frm._was_active) {
			frm.set_value("is_active", 1);
			show_deactivation_dialog(frm);
			return;
		}

		apply_active_lock(frm);
		frm.refresh_fields();
		frm._was_active = frm.doc.is_active;
	},

	refresh(frm) {
		if (frm.is_new()) return;

		frm._was_active = frm.doc.is_active;

		frm.page.clear_primary_action();
		frm.page.set_primary_action(__("Visual Builder"), () => {
			frappe.set_route("rule-builder", frm.doc.name);
		});

		frm.page.clear_custom_actions();
		frm.add_custom_button(__("Clone Rule"), () => clone_rule(frm), __("Actions"));
		frm.add_custom_button(__("Test Rule"), () => test_rule(frm), __("Actions"));
		frm.add_custom_button(__("Clear Cache"), () => clear_rule_cache(frm), __("Actions"));

		apply_active_lock(frm);

		update_dashboard_indicators(frm);

		if (frm.doc.actions?.length) {
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
			frm.add_child("actions", {
				action_id: "root",
				action_type: "Entry Action",
				is_enabled: 1,
			});
			frm.refresh_field("actions");
		}
	},
});

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
		frappe.model.set_value(cdt, cdn, "operation", null);
		frappe.model.set_value(cdt, cdn, "config", null);
		update_operation_options(frm, cdt, cdn);
	},

	configure_operation(frm, cdt, cdn) {
		configure_operation_from_form(frm, cdt, cdn);
	},
});

function apply_active_lock(frm) {
	const is_active = !!frm.doc.is_active;

	frm.fields.forEach(field => {
		if (!field.df || field.df.fieldname === "is_active") return;
		frm.set_df_property(field.df.fieldname, "read_only", is_active ? 1 : 0);
	});

	frm.set_df_property("is_active", "read_only", 0);

	Object.values(frm.fields_dict).forEach(f => {
		if (!f.grid) return;
		f.grid.cannot_add_rows = is_active;
		f.grid.cannot_delete_rows = is_active;
		f.grid.only_sortable = is_active;
		f.grid.wrapper
			.find(".grid-row, .grid-add-row")
			.toggleClass("disabled", is_active);
	});

	if (is_active) {
		frm.dashboard.set_headline_alert(
			__("This rule is active and locked. Deactivate it to edit."),
			"orange"
		);
	} else {
		frm.dashboard.clear_headline();
	}
}

function show_deactivation_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Deactivate Rule"),
		fields: [
			{
				fieldtype: "HTML",
				fieldname: "info",
				options: `<p>This rule is active. How would you like to proceed?</p>`,
			},
		],
		primary_action_label: __("Edit Current Rule"),
		primary_action() {
			frm.set_value("is_active", 0);
			apply_active_lock(frm);
			frm.refresh_fields();
			d.hide();
		},
		secondary_action_label: __("Create Copy & Edit"),
		secondary_action() {
			d.hide();
			create_copy_and_edit(frm);
		},
	});

	d.show();
}

function create_copy_and_edit(frm) {
	frappe.call({
		method: "flexirule.ruleflow.api.clone_rule",
		args: {
			rule_name: frm.doc.name,
			new_name: `${frm.doc.rule_name} (Draft)`,
		},
		freeze: true,
		callback(r) {
			if (r.message) {
				frappe.set_route("Form", "Rule", r.message);
			}
		},
	});
}
function update_dashboard_indicators(frm) {
	if (!frm.dashboard) return;

	frm.dashboard.clear_headline();

	if (frm.dashboard.indicator_area) {
		frm.dashboard.indicator_area.empty();
	}

	if (!frm._dashboard_rendered) {
		frm._dashboard_rendered = {};
	}

	const indicators = [];

	if (frm.doc.execution_count) {
		indicators.push({
			label: __("Executed {0} times", [frm.doc.execution_count]),
			color: "blue",
			key: "execution_count"
		});
	}

	if (frm.doc.last_error) {
		indicators.push({
			label: __("Has Errors"),
			color: "red",
			key: "last_error"
		});
	}

	indicators.forEach(ind => {
		if (!frm._dashboard_rendered[ind.key]) {
			frm.dashboard.add_indicator(ind.label, ind.color);
			frm._dashboard_rendered[ind.key] = true;
		}
	});
}

function toggle_action_fields(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const grid_row = frm.get_field("actions").grid.get_row(cdn);
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

	if (row.action_type === "Process") {
		[
			"process_name",
			"operation",
			"config",
			"timeout",
			"is_async",
			"on_error",
			"configure_operation",
		].forEach(f => grid_row.toggle_display(f, true));
	}

	if (row.action_type === "Condition") {
		[
			"condition_expression",
			"condition_json",
			"next_step_if_false",
		].forEach(f => grid_row.toggle_display(f, true));
	}

	if (row.action_type === "Sub-Rule") {
		[
			"rule",
			"skip_conditions",
			"skip_permissions",
		].forEach(f => grid_row.toggle_display(f, true));
	}
}

function update_operation_options(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row || row.action_type !== "Process" || !row.process_name) return;

	const grid_row = frm.get_field("actions").grid.get_row(row.name || cdn);
	if (!grid_row) return;

	const apply_ops = ops => {
		const field = grid_row.get_field("operation");
		if (!field) return;
		field.df.options = ops.join("\n");
		field.set_data?.(ops);
		field.refresh();
	};

	if (frm._process_ops_cache[row.process_name]) {
		apply_ops(frm._process_ops_cache[row.process_name]);
		return;
	}

	frappe.call({
		method: "flexirule.ruleflow.api.get_process_operations",
		args: { process_name: row.process_name },
	}).then(r => {
		const ops = r.message || [];
		frm._process_ops_cache[row.process_name] = ops;
		apply_ops(ops);
	});
}
