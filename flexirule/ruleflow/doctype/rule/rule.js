frappe.ui.form.on('Rule', {
    refresh(frm) {
        if (!frm.doc.__islocal) {

            // primary button
            frm.page.clear_primary_action();
            frm.page.set_primary_action(__('Visual Builder'), () => {
                frappe.set_route('rule-builder', frm.doc.name);
            });

            // custom buttons
            frm.page.clear_custom_actions();
            frm.add_custom_button(__('Test Rule'), () => {
                test_rule(frm);
            }, __('Actions'));

            frm.add_custom_button(__('Clear Cache'), () => {
                clear_rule_cache(frm);
            }, __('Actions'));

            // JSON helpers
            // Ensure wrapper exists before adding buttons
            setTimeout(() => add_json_helpers(frm), 500);
            if (!frm.dashboard) {
                frm.dashboard = new frappe.ui.form.Dashboard({
                    parent: frm.fields_dict ? frm.fields_dict['name'].$wrapper : frm.wrapper,
                    doctype: frm.doc.doctype
                });
            }

            // dashboard indicators
            if (frm.dashboard && frm.dashboard.wrapper) {
                frm.dashboard.wrapper.find('.indicator').remove();

                if (frm.doc.execution_count) {
                    frm.dashboard.add_indicator(
                        __('Executed {0} times', [frm.doc.execution_count]),
                        'blue'
                    );
                }

                if (frm.doc.last_error) {
                    frm.dashboard.add_indicator(__('Has Errors'), 'red');
                }
            }
        }
    },

    conditions_json(frm) {
        validate_json(frm, 'conditions_json');
    },

    actions_json(frm) {
        validate_json(frm, 'actions_json');
    },

    options_json(frm) {
        validate_json(frm, 'options_json');
    }
});


frappe.ui.form.on('Rule Action', {
    // Child table logic aligned with Frappe standard
    refresh(frm) {
        frm.trigger('toggle_fields');
    },

    action_type(frm) {
        frm.trigger('toggle_fields');
    },

    toggle_fields(frm) {
        const type = frm.doc.action_type;
        const fields_to_hide = [
            'process_method', 'method_config', 'timeout', 'retry_count', 'is_async', 'on_error',
            'condition_expression', 'next_step_if_false', 'switch_expression', 'loop_expression',
            'wait_duration', 'sub_rule'
        ];

        frm.toggle_display(fields_to_hide, false);

        if (type === 'Process') {
            frm.toggle_display(['process_method', 'method_config', 'timeout', 'retry_count', 'is_async', 'on_error'], true);
        } else if (type === 'Condition') {
            frm.toggle_display(['condition_expression', 'next_step_if_false'], true);
        } else if (type === 'Switch') {
            frm.toggle_display(['switch_expression'], true);
        } else if (type === 'Loop') {
            frm.toggle_display(['loop_expression'], true);
        } else if (type === 'Wait') {
            frm.toggle_display(['wait_duration'], true);
        } else if (type === 'Sub-Rule') {
            frm.toggle_display(['sub_rule'], true);
        }
    }
});

function validate_json(frm, fieldname) {
    const value = frm.doc[fieldname];
    if (!value) return;

    try {
        JSON.parse(value);
        frm.set_df_property(fieldname, 'description', '✓ Valid JSON');
    } catch (e) {
        frm.set_df_property(fieldname, 'description', '✗ Invalid JSON: ' + e.message);
    }
}

function add_json_helpers(frm) {
    ['conditions_json', 'actions_json', 'options_json'].forEach(fieldname => {
        const field = frm.fields_dict[fieldname];
        if (!field || !field.$wrapper || field.$wrapper.find('.format-btn').length) return;

        const $btn = $(`
            <button class="btn btn-xs btn-default format-btn" style="margin-top:5px">
                <i class="fa fa-align-left"></i> ${__('Format')}
            </button>
        `);

        $btn.on('click', () => {
            try {
                const formatted = JSON.stringify(
                    JSON.parse(frm.doc[fieldname] || '{}'),
                    null,
                    2
                );
                frm.set_value(fieldname, formatted);
            } catch { }
        });

        field.$wrapper.find('.control-value').append($btn);
    });
}

function test_rule(frm) {
    const d = new frappe.ui.Dialog({
        title: __('Test Rule'),
        fields: [
            {
                fieldtype: 'Link',
                fieldname: 'doctype',
                label: __('Document Type'),
                options: 'DocType',
                default: frm.doc.document_type,
                reqd: 1
            },
            {
                fieldtype: 'Dynamic Link',
                fieldname: 'docname',
                label: __('Document'),
                options: 'doctype',
                reqd: 1
            }
        ],
        primary_action_label: __('Test'),
        primary_action(values) {
            frappe.call({
                method: 'flexirule.ruleflow.api.test_rule',
                args: {
                    rule_name: frm.doc.name,
                    doctype: values.doctype,
                    docname: values.docname
                },
                callback(r) {
                    if (r.message && r.message.success) {
                        frappe.msgprint({
                            title: __('Test Complete'),
                            message: r.message.message,
                            indicator: 'green'
                        });
                    } else {
                        frappe.msgprint({
                            title: __('Test Failed'),
                            message: r.message ? r.message.error : __('Unknown error'),
                            indicator: 'red'
                        });
                    }
                    d.hide();
                }
            });
        }
    });

    d.show();
}

function clear_rule_cache(frm) {
    frappe.call({
        method: 'flexirule.ruleflow.api.clear_cache',
        args: { doctype: frm.doc.document_type },
        callback() {
            frappe.show_alert({
                message: __('Cache cleared'),
                indicator: 'green'
            });
        }
    });
}
