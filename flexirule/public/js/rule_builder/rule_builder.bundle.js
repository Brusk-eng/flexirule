import { createApp } from "vue";
import { createPinia } from "pinia";
import { useStore } from "./store";
import RuleBuilderComponent from "./RuleBuilder.vue";

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
        this.page.add_button(__("Reset Changes"), () => {
            this.store.fetch();
        }, { icon: "refresh" });

        // Menu items
        this.page.add_menu_item(__("Go to Rule"), () => {
            frappe.set_route("Form", "Rule", this.rule);
        });

        this.page.add_menu_item(__("Test Rule"), () => {
            this.show_test_dialog();
        });
    }

    setup_app() {
        // Create Pinia instance
        let pinia = createPinia();

        // Create Vue app
        let app = createApp(RuleBuilderComponent, { rule: this.rule });
        SetVueGlobals(app);
        app.use(pinia);

        // Get store reference
        this.store = useStore();
        this.store.rule_name = this.rule;

        // Watch for dirty state
        this.store.$subscribe((mutation, state) => {
            this.update_save_button(state.is_dirty);
        });

        // Mount app
        this.$rule_builder = app.mount(this.$wrapper.get(0));
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
