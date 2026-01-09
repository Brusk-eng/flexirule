// Hooks for Rule DocType form to include custom script
frappe.ui.form.on("Rule", {
	refresh: function (frm) {
		frm.add_custom_button("Visual Builder", () => {
			frm.events.open_visual_builder(frm);
		});
	},

	open_visual_builder: function (frm) {
		frappe.set_route("rule-builder", frm.doc.name);
	},

	setup: function (frm) {
		// Initialize builder
		frm.rule_builder_initialized = false;
	},
});
