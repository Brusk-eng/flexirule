frappe.ui.form.on("Data Review Task", {
	refresh(frm) {
		if (frm.doc.status !== "Resolved" && frm.doc.rule) {
			frm.add_custom_button(
				__("Resolve Issue"),
				() => {
					resolve_issue(frm);
				},
				__("Actions")
			);
		}
	},
});

function resolve_issue(frm) {
	let method_inputs = {};
	try {
		method_inputs = JSON.parse(frm.doc.method_inputs || "{}");
	} catch (e) {
		frappe.msgprint(__("Invalid JSON in Method Inputs"));
		return;
	}

	const d = new frappe.ui.Dialog({
		title: __("Resolve Issue"),
		fields: [
			{
				label: "Inputs",
				fieldname: "inputs",
				fieldtype: "Code",
				options: "JSON",
				default: JSON.stringify(method_inputs, null, 4),
			},
		],
		primary_action_label: __("Execute Rule"),
		primary_action(values) {
			let inputs = {};
			try {
				inputs = JSON.parse(values.inputs);
			} catch (e) {
				frappe.msgprint(__("Invalid JSON inputs"));
				return;
			}

			// We use test_rule for manual execution from Data Review Task
			// This bypasses trigger conditions as the user is explicitly resolving this task.
			frappe.call({
				method: "flexirule.ruleflow.api.test_rule",
				args: {
					rule_name: frm.doc.rule,
					doctype: frm.doc.source_doctype,
					docname: frm.doc.source_document,
				},
				freeze: true,
				callback(r) {
					if (r.message && r.message.success) {
						frappe.msgprint({
							title: __("Success"),
							message: __("Resolution rule executed successfully."),
							indicator: "green",
						});
						frm.reload_doc();
						d.hide();
					} else if (r.message && r.message.error) {
						frappe.msgprint({
							title: __("Error"),
							message: r.message.error,
							indicator: "red",
						});
					}
				},
			});
		},
	});

	d.show();
}
