// Copyright (c) 2025, Abdo Ruzaqi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Process", {
	refresh: function (frm) {
		// 1️⃣ Make standard processes read-only if not developer
		if (frm.doc.is_standard === "Yes" && !frappe.boot.developer_mode) {
			frm.disable_form();
		} else {
			// Show warning indicator for local changes
			frm.dashboard.clear_headline();
			frm.dashboard.set_headline(
				__(
					"Warning: Changes to this process will only affect local site and may impact updates."
				)
			);
			frm.enable_save();
		}

		// 2️⃣ Toggle Enable/Disable button
		if (frm.doc.is_standard === "Yes" && frm.perm[0].write) {
			frm.add_custom_button(
				frm.doc.disabled ? __("Enable Process") : __("Disable Process"),
				function () {
					frm.call("toggle_disable", {
						disable: frm.doc.disabled ? 0 : 1,
					}).then(() => {
						frm.reload_doc();
					});
				},
				frm.doc.disabled ? "fa fa-check" : "fa fa-off"
			);
		}

		// 3️⃣ Filter reference Doctype (exclude child tables)
		frm.set_query("ref_doctype", () => {
			return {
				filters: {
					istable: 0,
				},
			};
		});
	},
});
