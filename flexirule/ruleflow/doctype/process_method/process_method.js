// Copyright (c) 2025, Abdo Ruzaqi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Process Method", {
	refresh(frm) {
		if (!frm.is_new()) {
			// Dashboard (Rules using this method)
			frm.dashboard.render_graph = false;

			// "Test Method" Button
			frm.add_custom_button(__("Test Method"), () => {
				frm.events.show_test_dialog(frm);
			});
		}
	},

	show_test_dialog(frm) {
		let fields = [];
		let schema = null;

		// Try to parse config_schema first, then input_schema
		try {
			if (frm.doc.config_schema) {
				schema = JSON.parse(frm.doc.config_schema);
			} else if (frm.doc.input_schema) {
				schema = JSON.parse(frm.doc.input_schema);
			}
		} catch (e) {
			console.error("Invalid Schema JSON", e);
			frappe.msgprint(
				__("Invalid Config/Input Schema in document. Cannot generate test form.")
			);
			return;
		}

		if (schema && schema.fields) {
			// Convert schema fields to Dialog fields
			fields = schema.fields.map((f) => {
				// Ensure required props mapping matches Dialog expectations
				return {
					label: f.label,
					fieldname: f.fieldname,
					fieldtype: f.fieldtype || "Data",
					options: f.options,
					reqd: f.reqd,
					default: f.default,
				};
			});
		} else {
			// Fallback if no schema: JSON editor
			fields = [
				{
					label: "Configuration (JSON)",
					fieldname: "manual_config",
					fieldtype: "Code",
					options: "JSON",
					default: "{}",
				},
			];
		}

		let d = new frappe.ui.Dialog({
			title: __("Test Process Method"),
			fields: fields,
			primary_action_label: __("Run Test"),
			primary_action(values) {
				let config = values;

				// If fallback manual config
				if (values.manual_config) {
					try {
						config = JSON.parse(values.manual_config);
					} catch (e) {
						frappe.msgprint(__("Invalid JSON in configuration"));
						return;
					}
				}

				frappe.call({
					method: "flexirule.ruleflow.doctype.process_method.process_method.test_method",
					args: {
						method_name: frm.doc.name,
						config: config,
					},
					freeze: true,
					freeze_message: __("Executing Method..."),
					callback: (r) => {
						d.hide();
						if (r.message) {
							let result = r.message;
							let status = result.success ? "Success" : "Failed";
							let color = result.success ? "green" : "red";

							let message = `
                                <div>
                                    <h4 style="color: ${color}">${status}</h4>
                                    <p><b>Execution Time:</b> ${result.execution_time} ms</p>
                                    <hr>
                                    <p><b>Result:</b></p>
                                    <pre>${JSON.stringify(result.result, null, 2)}</pre>
                                </div>
                            `;

							if (result.error) {
								message += `
                                    <hr>
                                    <p style="color: red"><b>Error:</b> ${result.error}</p>
                                `;
							}

							frappe.msgprint({
								title: __("Test Result"),
								message: message,
								indicator: color,
								wide: true,
							});
						}
					},
				});
			},
		});

		d.show();
	},
});
