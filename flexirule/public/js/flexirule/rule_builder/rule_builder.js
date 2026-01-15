import { createApp } from "vue";
import { createPinia } from "pinia";

// Import FlexiRule Utilities
import "../utils/utils.js";
import "../utils/patches.js";
import "../controls/flexi_autocomplete.js";
import "../core/ConfigurableAction.js";
import { useStore } from "./store";
import RuleBuilderComponent from "./App.vue";
import { registerGlobalComponents } from "./globals.js";

class RuleBuilder {
	constructor({ wrapper, page, rule }) {
		this.$wrapper = $(wrapper);
		this.page = page;
		this.rule = rule;

		this.init();
	}

	init() {
		this.setup_page();
		this.setup_app();
	}

	setup_page() {
		// Set page title
		this.page.set_title(__("Editing {0}", [this.rule]));

		// Clear existing actions
		this.page.clear_actions();
		this.page.clear_menu();
		this.page.clear_custom_actions();

		// Primary action - Save button
		this.save_btn = this.page.set_primary_action(
			__("Save"),
			() => this.store.save_changes(),
			"save"
		);

		// Secondary button - Reset
		this.page.add_button(
			__("Reset Changes"),
			() => {
				this.store.fetch();
			},
			{ icon: "refresh" }
		);

		// Status Toggle
		this.status_btn = this.page.add_inner_button(__("Draft"), () => {
			this.toggle_rule_active();
		});

		// Dry Run
		this.status_btn = this.page.add_inner_button(__("Test Rule"), () => {
			this.show_test_dialog();
		});

		// Menu items
		this.page.add_menu_item(__("Go to Rule"), () => {
			frappe.set_route("Form", "Rule", this.rule);
		});
	}

	setup_app() {
		// Create Pinia instance
		let pinia = createPinia();

		// Create Vue app
		let app = createApp(RuleBuilderComponent, { rule: this.rule });
		SetVueGlobals(app);
		app.use(pinia);
		registerGlobalComponents(app);

		// Get store reference
		this.store = useStore();
		this.store.rule_name = this.rule;

		// Watch for dirty state
		this.store.$subscribe((mutation, state) => {
			this.update_save_button(state.is_dirty);
			this.update_status_button(state.rule_doc?.is_active);
		});

		// Initial status update after fetch
		// We might need to wait for fetch, but store.$subscribe handles mutations.
		// We can also watch rule_doc specifically if needed, but the main subscribe is usually enough for state changes.
		// Also manual call after mount if data is already there (it fetches async)

		// Use a watcher on rule_doc specifically if the above sub misses deep updates (Pinia default subscribes to all)
		// Checks if rule_doc is loaded
		const unwatch = this.store.$onAction(({ name, after }) => {
			if (name === "fetch") {
				after(() => {
					this.update_status_button(this.store.rule_doc?.is_active);
				});
			}
		});

		// Mount app
		this.$rule_builder = app.mount(this.$wrapper.get(0));
	}

	toggle_rule_active() {
		if (!this.store.rule_doc) return;
		this.store.rule_doc.is_active = this.store.rule_doc.is_active ? 0 : 1;
		this.store.mark_dirty();
		this.update_status_button(this.store.rule_doc.is_active);
	}

	update_status_button(is_active) {
		if (is_active) {
			this.status_btn.text(__("Active"));
			this.status_btn.removeClass("btn-default").addClass("btn-success");
		} else {
			this.status_btn.text(__("Draft"));
			this.status_btn.removeClass("btn-success").addClass("btn-default");
		}
	}

	update_save_button(is_dirty) {
		if (is_dirty) {
			this.save_btn.removeClass("btn-primary-light").addClass("btn-primary");
			this.page.set_indicator(__("Not Saved"), "orange");
		} else {
			this.save_btn.removeClass("btn-primary").addClass("btn-primary-light");
			this.page.clear_indicator();
		}
	}

	show_test_dialog() {
		let d = new frappe.ui.Dialog({
			title: __("Test Rule"),
			fields: [
				{
					fieldtype: "Link",
					fieldname: "doctype",
					label: __("Document Type"),
					options: "DocType",
					default: this.store.rule_doc?.document_type,
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
			primary_action: (values) => {
				frappe.call({
					method: "flexirule.ruleflow.api.test_rule",
					args: {
						rule_name: this.rule,
						doctype: values.doctype,
						docname: values.docname,
					},
					callback: (r) => {
						if (r.message?.success) {
							frappe.msgprint({
								title: __("Success"),
								message: r.message.message,
								indicator: "green",
							});
						} else {
							frappe.msgprint({
								title: __("Error"),
								message: r.message?.error || __("Test failed"),
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
}

frappe.provide("frappe.ui");
frappe.ui.RuleBuilder = RuleBuilder;
export default RuleBuilder;
