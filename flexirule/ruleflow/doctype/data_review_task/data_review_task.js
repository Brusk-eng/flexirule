frappe.ui.form.on("Data Review Task", {
	refresh(frm) {
		if (frm.doc.status !== "Resolved" && frm.doc.process_method) {
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
		primary_action_label: __("Execute"),
		primary_action(values) {
			let inputs = {};
			try {
				inputs = JSON.parse(values.inputs);
			} catch (e) {
				frappe.msgprint(__("Invalid JSON inputs"));
				return;
			}

			frappe.call({
				method: "flexirule.ruleflow.api.execute_process_method",
				args: {
					method_path: frm.doc.process_method,
					params: inputs,
					doc_dict: frm.doc.context_json ? JSON.parse(frm.doc.context_json) : null,
				},
				callback(r) {
					if (!r.exc) {
						frappe.msgprint({
							title: __("Success"),
							message: __("Resolution method executed."),
							indicator: "green",
						});
						frm.reload_doc();
						d.hide();
					}
				},
			});
		},
	});

	d.show();
}
