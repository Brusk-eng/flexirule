/**
 * FlexiRule Integration Example
 *
 * This file demonstrates how to integrate the FlexiRule runtime
 * with existing process adapters in a Rule Builder context.
 *
 * This is NOT a production file - it's documentation and example code.
 */

/**
 * Example 1: Using the runtime with Deduplication process
 *
 * This shows how to open a configuration dialog for a process action.
 */
function example_open_deduplication_config(action_node, rule_context) {
    // 1. Create adapter from existing process
    const adapter = flexirule.adapters.create_from_process(
        'Deduplication',                    // Process name
        'find_similar_records',             // Operation name
        {
            document_type: rule_context.doctype,  // Context for field resolution
            config: action_node.config || {},
        }
    );

    if (!adapter) {
        frappe.msgprint(__('Failed to load adapter for this action.'));
        return;
    }

    // 2. Create ConfigurableAction
    const configurable_action = new flexirule.ConfigurableAction({
        action_type: 'process',
        adapter: adapter,
        initial_config: action_node.config || {},
        on_change: (config) => {
            // Track changes for dirty detection
            console.log('[FlexiRule] Config changed:', config);
        },
    });

    // 3. Create Dialog with HTML field for custom rendering
    const dialog = new frappe.ui.Dialog({
        title: __('Configure: Find Similar Records'),
        size: 'large',
        fields: [
            {
                fieldname: 'config_area',
                fieldtype: 'HTML',
            }
        ],
        primary_action_label: __('Save'),
        primary_action: () => {
            // Validate before saving
            const validation = configurable_action.validate();

            if (!validation.valid) {
                frappe.msgprint({
                    title: __('Validation Error'),
                    indicator: 'red',
                    message: validation.errors.map(e => e.message).join('<br>'),
                });
                return;
            }

            // Save config back to action node
            action_node.config = configurable_action.get_config();

            // Cleanup and close
            ui_runtime.destroy();
            dialog.hide();

            // Trigger rule save or mark dirty
            if (typeof rule_context.on_config_save === 'function') {
                rule_context.on_config_save(action_node);
            }
        },
    });

    // 4. Render UIRuntime into dialog
    const $container = dialog.fields_dict.config_area.$wrapper;
    const ui_runtime = new flexirule.UIRuntime({
        parent: $container,
        configurable_action: configurable_action,
        context: {
            doc: action_node.config || {},
            doctype: rule_context.doctype,
        },
    });

    ui_runtime.render();
    dialog.show();

    // Cleanup on dialog close
    dialog.$wrapper.on('hidden.bs.modal', () => {
        ui_runtime.destroy();
        configurable_action.destroy();
    });
}


/**
 * Example 2: Programmatic FlexiTable usage
 *
 * Standalone table without full runtime.
 */
function example_standalone_table(container_element, initial_rows) {
    const table = new flexirule.FlexiTable({
        parent: container_element,
        schema: {
            columns: [
                {
                    fieldname: 'fieldname',
                    label: __('Field'),
                    fieldtype: 'Data',
                    reqd: 1,
                },
                {
                    fieldname: 'algorithm',
                    label: __('Algorithm'),
                    fieldtype: 'Select',
                    options: 'Exact\nFuzzy\nPhonetic',
                    default: 'Fuzzy',
                },
                {
                    fieldname: 'threshold',
                    label: __('Threshold'),
                    fieldtype: 'Float',
                    default: 0.8,
                    // Only show when algorithm is not Exact
                    depends_on: "eval:row.algorithm !== 'Exact'",
                },
                {
                    fieldname: 'tolerance',
                    label: __('Tolerance'),
                    fieldtype: 'Int',
                    default: 30,
                    // Show for range-based algorithms
                    depends_on: "eval:['Numeric Range', 'Date Distance'].includes(row.algorithm)",
                },
            ],
        },
        model: {
            rows: initial_rows || [],
        },
        on_change: (action, data) => {
            console.log('[FlexiTable] Change:', action, data);
        },
    });

    table.render();

    return table;
}


/**
 * Example 3: Variant column usage
 *
 * Table where a column's control type changes based on row state.
 */
function example_variant_column_table(container_element) {
    const table = new flexirule.FlexiTable({
        parent: container_element,
        schema: {
            columns: [
                {
                    fieldname: 'source',
                    label: __('Source'),
                    fieldtype: 'Data',
                    reqd: 1,
                },
                {
                    fieldname: 'mode',
                    label: __('Mode'),
                    fieldtype: 'Select',
                    options: 'constant\nfield\nexpression',
                    default: 'constant',
                },
                {
                    fieldname: 'value',
                    label: __('Value'),
                    fieldtype: 'Data', // Base type
                    variants: [
                        // When mode is 'constant', use Data field
                        {
                            condition: "row.mode === 'constant'",
                            fieldtype: 'Data',
                        },
                        // When mode is 'field', use Link to DocField
                        {
                            condition: "row.mode === 'field'",
                            fieldtype: 'Link',
                            options: 'DocField',
                        },
                        // When mode is 'expression', use Code field
                        {
                            condition: "row.mode === 'expression'",
                            fieldtype: 'Code',
                            options: 'Python',
                        },
                    ],
                },
            ],
        },
        model: { rows: [] },
        on_change: (action, data) => {
            console.log('[FlexiTable] Variant change:', action, data.rows);
        },
    });

    table.render();

    // Add initial rows
    table.add_row({ source: 'customer_name', mode: 'constant', value: 'Acme Corp' });
    table.add_row({ source: 'priority', mode: 'field', value: 'status' });

    return table;
}


/**
 * Example 4: Using FieldSelector widget directly
 */
function example_field_selector(container_element) {
    const selector = new flexirule.FieldSelector({
        parent: container_element,
        df: {
            fieldname: 'selected_field',
            label: __('Source Field'),
        },
        context: {
            doctypes: ['Customer', 'Lead', 'Contact'],
            context_vars: {
                'current_user': {
                    fields: [
                        { fieldname: 'email', fieldtype: 'Data' },
                        { fieldname: 'full_name', fieldtype: 'Data' },
                    ]
                },
                'doc': { doctype: 'Customer' }, // References a DocType
            },
        },
        on_change: (value) => {
            console.log('[FieldSelector] Value:', value);
            // value = [source, doctype_or_key, fieldname, fieldtype, options]
        },
    });

    selector.render();

    return selector;
}


/**
 * Example 5: DocFieldWidget in a dialog
 */
function example_docfield_in_dialog(doctype) {
    const dialog = new frappe.ui.Dialog({
        title: __('Select Field'),
        fields: [
            {
                fieldname: 'field_area',
                fieldtype: 'HTML',
            }
        ],
        primary_action_label: __('Select'),
        primary_action: () => {
            const value = widget.get_value();
            console.log('Selected field:', value);
            widget.destroy();
            dialog.hide();
        },
    });

    const widget = new flexirule.DocFieldWidget({
        parent: dialog.fields_dict.field_area.$wrapper,
        df: { options: doctype },
        context: {},
        on_change: (fieldname) => {
            console.log('Field selected:', fieldname);
        },
    });

    widget.render();
    dialog.show();
}
