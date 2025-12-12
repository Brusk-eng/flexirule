frappe.ui.form.on('Rule', {
    refresh: function (frm) {
        if (!frm.is_new()) {
            // Primary button - Visual Builder
            frm.add_custom_button(__('Visual Builder'), function () {
                frappe.set_route('rule-builder', frm.doc.name);
            }, null, 'primary');

            // Secondary buttons
            frm.add_custom_button(__('Test Rule'), function () {
                test_rule(frm);
            });

            frm.add_custom_button(__('Clear Cache'), function () {
                clear_rule_cache(frm);
            });
        }

        // JSON field helpers
        add_json_helpers(frm);

        // Show execution stats
        if (frm.doc.execution_count) {
            frm.dashboard.add_indicator(
                __('Executed {0} times', [frm.doc.execution_count]),
                'blue'
            );
        }

        if (frm.doc.last_error) {
            frm.dashboard.add_indicator(__('Has Errors'), 'red');
        }
    },

    conditions_json: function (frm) {
        validate_json(frm, 'conditions_json');
    },

    actions_json: function (frm) {
        validate_json(frm, 'actions_json');
    },

    options_json: function (frm) {
        validate_json(frm, 'options_json');
    }
});

function validate_json(frm, fieldname) {
    let value = frm.doc[fieldname];
    if (value) {
        try {
            JSON.parse(value);
            frm.set_df_property(fieldname, 'description', '✓ Valid JSON');
        } catch (e) {
            frm.set_df_property(fieldname, 'description', '✗ Invalid JSON: ' + e.message);
        }
    }
}

function add_json_helpers(frm) {
    // Add format buttons for JSON fields
    ['conditions_json', 'actions_json', 'options_json'].forEach(fieldname => {
        const field = frm.fields_dict[fieldname];
        if (field && field.$wrapper && !field.$wrapper.find('.format-btn').length) {
            const $btn = $(`<button class="btn btn-xs btn-default format-btn" style="margin-top:5px">
                <i class="fa fa-align-left"></i> Format
            </button>`);
            $btn.on('click', () => {
                try {
                    const formatted = JSON.stringify(JSON.parse(frm.doc[fieldname] || '{}'), null, 2);
                    frm.set_value(fieldname, formatted);
                } catch { }
            });
            field.$wrapper.find('.control-value').append($btn);
        }
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
        primary_action: function (values) {
            frappe.call({
                method: 'flexirule.ruleflow.api.test_rule',
                args: {
                    rule_name: frm.doc.name,
                    doctype: values.doctype,
                    docname: values.docname
                },
                callback: function (r) {
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
        callback: function () {
            frappe.show_alert({
                message: __('Cache cleared'),
                indicator: 'green'
            });
        }
    });
}
