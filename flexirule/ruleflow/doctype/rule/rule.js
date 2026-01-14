frappe.ui.form.on("Rule", {
	refresh(frm) {
		if (!frm.doc.__islocal) {
			// primary button
			frm.page.clear_primary_action();
			frm.page.set_primary_action(__("Visual Builder"), () => {
				frappe.set_route("rule-builder", frm.doc.name);
			});

			// custom buttons
			frm.page.clear_custom_actions();
			frm.add_custom_button(
				__("Test Rule"),
				() => {
					test_rule(frm);
				},
				__("Actions")
			);

			frm.add_custom_button(
				__("Clear Cache"),
				() => {
					clear_rule_cache(frm);
				},
				__("Actions")
			);

			// JSON helpers
			// Ensure wrapper exists before adding buttons
			setTimeout(() => add_json_helpers(frm), 500);
			if (!frm.dashboard) {
				frm.dashboard = new frappe.ui.form.Dashboard({
					parent: frm.fields_dict ? frm.fields_dict["name"].$wrapper : frm.wrapper,
					doctype: frm.doc.doctype,
				});
			}

			// dashboard indicators
			if (frm.dashboard && frm.dashboard.wrapper) {
				frm.dashboard.wrapper.find(".indicator").remove();

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
		}
	},
	before_insert(frm) {
		if (
			frm.doc.document_type &&
			frm.doc.trigger_event &&
			(!frm.doc.actions || frm.doc.actions.length === 0)
		) {
			let child = frm.add_child("actions");

			child.action_type = "Entry Action";
			child.idx = 1;
			child.action_id = "root";

			frm.refresh_field("actions");
		}
	},

	conditions_json(frm) {
		validate_json(frm, "conditions_json");
	},

	actions_json(frm) {
		validate_json(frm, "actions_json");
	},

	options_json(frm) {
		validate_json(frm, "options_json");
	},
});

frappe.ui.form.on("Rule Action", {
	// Child table logic aligned with Frappe standard
	refresh(frm, cdt, cdn) {
		frm.trigger("toggle_fields", cdt, cdn);

		// Add Configure Operation button functionality in the grid
		const row = frm.get_field("actions").grid.grid_rows_by_docname[cdn];
		if (row && row.doc.action_type === "Process" && row.doc.process_name && row.doc.operation) {
			// Add a button to the row if it doesn't exist yet
			if (!row.configure_operation_btn) {
				const configureBtn = $(`<button class="btn btn-xs btn-default configure-operation-btn"
					style="margin-left: 5px;">
					<i class="fa fa-cog"></i> Configure
				</button>`);

				configureBtn.on("click", () => {
					configure_operation_from_form(frm, cdt, cdn);
				});

				// Add button to the row's action area
				row.configure_operation_btn = configureBtn;
				// Find the row's action column and append the button
				const actionCol = row.row.find('.row-actions');
				if (actionCol.length) {
					// Insert before the delete button if it exists
					const delBtn = actionCol.find('.grid-delete-row');
					if (delBtn.length) {
						delBtn.before(configureBtn);
					} else {
						actionCol.append(configureBtn);
					}
				}
			}

			// Show the button if it exists
			if (row.configure_operation_btn) {
				row.configure_operation_btn.show();
			}
		} else if (row && row.configure_operation_btn) {
			// Hide button if conditions are not met
			if (row.configure_operation_btn) {
				row.configure_operation_btn.hide();
			}
		}
	},

	action_type(frm, cdt, cdn) {
		frm.trigger("toggle_fields", cdt, cdn);
	},

	toggle_fields(frm, cdt, cdn) {
		const type = frm.doc.action_type;
		const fields_to_hide = [
			"process_method",
			"method_config",
			"timeout",
			"retry_count",
			"is_async",
			"on_error",
			"condition_expression",
			"next_step_if_false",
			"switch_expression",
			"loop_expression",
			"wait_duration",
			"sub_rule",
		];

		frm.toggle_display(fields_to_hide, false);

		if (type === "Process") {
			frm.toggle_display(
				[
					"process_method",
					"method_config",
					"timeout",
					"retry_count",
					"is_async",
					"on_error",
				],
				true
			);
		} else if (type === "Condition") {
			frm.toggle_display(["condition_expression", "next_step_if_false"], true);
		} else if (type === "Switch") {
			frm.toggle_display(["switch_expression"], true);
		} else if (type === "Loop") {
			frm.toggle_display(["loop_expression"], true);
		} else if (type === "Wait") {
			frm.toggle_display(["wait_duration"], true);
		} else if (type === "Sub-Rule") {
			frm.toggle_display(["sub_rule"], true);
		}
	},

	// Handle the configure_operation button click in the child table
	configure_operation(frm, cdt, cdn) {
		configure_operation_from_form(frm, cdt, cdn);
	}
});

// Function to handle the configuration dialog opening
async function configure_operation_from_form(frm, cdt, cdn) {
	const row = frm.get_field("actions").grid.grid_rows_by_docname[cdn];

	if (!row.doc.process_name || !row.doc.operation) {
		frappe.msgprint(__("Please select a Process and Operation first"));
		return;
	}

	try {
		// Ensure ConfigurableAction is available
		if (typeof flexirule === 'undefined' || typeof flexirule.integration === 'undefined') {
			await frappe.require(['flexirule.bundle.js']);
		}

		// Create ConfigurableAction instance
		const action = flexirule.integration.create_configurable_action({
			process_name: row.doc.process_name,
			operation_name: row.doc.operation,
			node_data: row.doc,
			document_type: frm.doc.document_type,
			doc_meta: null, // Will be fetched by ConfigurableAction if needed
			get_variable_options: async () => {
				// Return available variables for the rule context
				return [];
			},
		});

		// Initialize and show the dialog
		await action.init();
		action.show_dialog({
			on_save: () => {
				// Update the row's config field with the new configuration
				const configStr = JSON.stringify(action.get_config());
				frappe.model.set_value(cdt, cdn, "config", configStr);

				frappe.show_alert({
					message: __("Configuration saved"),
					indicator: "green"
				});
			},
		});
	} catch (error) {
		console.error("Error initializing ConfigurableAction:", error);
		frappe.msgprint({
			message: __("Error initializing configuration: {0}", [error.message || error]),
			indicator: "red"
		});
	}
}

function validate_json(frm, fieldname) {
	const value = frm.doc[fieldname];
	if (!value) return;

	try {
		JSON.parse(value);
		frm.set_df_property(fieldname, "description", "✓ Valid JSON");
	} catch (e) {
		frm.set_df_property(fieldname, "description", "✗ Invalid JSON: " + e.message);
	}
}

function add_json_helpers(frm) {
	["conditions_json", "actions_json", "options_json"].forEach((fieldname) => {
		const field = frm.fields_dict[fieldname];
		if (!field || !field.$wrapper || field.$wrapper.find(".format-btn").length) return;

		const $btn = $(`
            <button class="btn btn-xs btn-default format-btn" style="margin-top:5px">
                <i class="fa fa-align-left"></i> ${__("Format")}
            </button>
        `);

		$btn.on("click", () => {
			try {
				const formatted = JSON.stringify(JSON.parse(frm.doc[fieldname] || "{}"), null, 2);
				frm.set_value(fieldname, formatted);
			} catch {}
		});

		field.$wrapper.find(".control-value").append($btn);
	});
}

function test_rule(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Test Rule"),
		fields: [
			{
				fieldtype: "Link",
				fieldname: "doctype",
				label: __("Document Type"),
				options: "DocType",
				default: frm.doc.document_type,
				reqd: 1,
			},
			{
				fieldtype: "Dynamic Link",
				fieldname: "docname",
				label: __("Document"),
				options: "doctype",
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
					if (r.message && r.message.success) {
						frappe.msgprint({
							title: __("Test Complete"),
							message: r.message.message,
							indicator: "green",
						});
					} else {
						frappe.msgprint({
							title: __("Test Failed"),
							message: r.message ? r.message.error : __("Unknown error"),
							indicator: "red",
						});
					}
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
			frappe.show_alert({
				message: __("Cache cleared"),
				indicator: "green",
			});
		},
	});
}
