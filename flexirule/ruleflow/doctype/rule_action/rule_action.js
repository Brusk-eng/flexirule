frappe.ui.form.on('Rule Action', {
    refresh: function(frm) {
        frm.trigger('toggle_fields');
    },
    
    action_type: function(frm) {
        frm.trigger('toggle_fields');
    },
    
    toggle_fields: function(frm) {
        const type = frm.doc.action_type;
        
        // Hide all type-specific fields first
        frm.toggle_display([
            'process_method', 'method_config', 'timeout', 'retry_count', 'is_async', 'on_error', // Process
            'condition_expression', 'next_step_if_false', // Condition
            'switch_expression', // Switch (if implemented)
            'loop_expression', // Loop (if implemented)
            'wait_duration', // Wait (if implemented)
            'sub_rule' // Sub-Rule
        ], false);

        // Show based on type
        if (type === 'Process') {
            frm.toggle_display(['process_method', 'method_config', 'timeout', 'retry_count', 'is_async', 'on_error'], true);
        } else if (type === 'Condition') {
            frm.toggle_display(['condition_expression', 'next_step_if_false'], true);
        } else if (type === 'Switch') {
            frm.toggle_display(['condition_expression'], true); // Switch often uses condition field or specific one
        } else if (type === 'Loop') {
             // Show process fields if Loop acts like a process, or condition for exit
             frm.toggle_display(['condition_expression'], true);
        } else if (type === 'Wait') {
            frm.toggle_display(['timeout'], true);
        } else if (type === 'Sub-Rule') {
             frm.toggle_display(['process_method'], true); // Use process link for subrule? Or generic
        }
    }
});
