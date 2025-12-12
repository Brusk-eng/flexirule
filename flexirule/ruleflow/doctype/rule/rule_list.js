frappe.listview_settings['Rule'] = {
    add_fields: ['is_active', 'document_type', 'trigger_event', 'rule_type'],
    
    get_indicator: function(doc) {
        if (doc.is_active) {
            return [__("Active"), "green", "is_active,=,1"];
        }
        return [__("Inactive"), "gray", "is_active,=,0"];
    },
    
    formatters: {
        rule_name: function(value, field, doc) {
            // Add builder icon before rule name
            return `
                <span class="rule-name-cell">
                    <a class="builder-icon" 
                       href="/app/rule-builder/${doc.name}" 
                       title="${__('Open in Rule Builder')}"
                       onclick="event.stopPropagation();">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 3L3 9l9 6 9-6-9-6z"/>
                            <path d="M3 15l9 6 9-6"/>
                            <path d="M3 9v6"/>
                            <path d="M21 9v6"/>
                        </svg>
                    </a>
                    ${value}
                </span>
            `;
        }
    },
    
    onload: function(listview) {
        // Add "New with Builder" button
        listview.page.add_inner_button(__('Create with Builder'), function() {
            // Create new rule and open builder
            frappe.prompt([
                {
                    fieldname: 'rule_name',
                    fieldtype: 'Data',
                    label: __('Rule Name'),
                    reqd: 1
                },
                {
                    fieldname: 'document_type',
                    fieldtype: 'Link',
                    label: __('Document Type'),
                    options: 'DocType',
                    reqd: 1,
                    filters: { istable: 0 }
                },
                {
                    fieldname: 'trigger_event',
                    fieldtype: 'Select',
                    label: __('Trigger Event'),
                    options: 'Before Insert\nBefore Save\nValidate\nAfter Insert\nAfter Save\nBefore Submit\nOn Submit\nBefore Cancel\nOn Cancel\nOn Trash',
                    default: 'Validate',
                    reqd: 1
                }
            ], function(values) {
                frappe.call({
                    method: 'frappe.client.insert',
                    args: {
                        doc: {
                            doctype: 'Rule',
                            rule_name: values.rule_name,
                            document_type: values.document_type,
                            trigger_event: values.trigger_event,
                            is_active: 0
                        }
                    },
                    callback: function(r) {
                        if (r.message) {
                            frappe.set_route('rule-builder', r.message.name);
                        }
                    }
                });
            }, __('Create New Rule'), __('Open Builder'));
        });
        
        // Add custom CSS
        if (!document.getElementById('rule-list-styles')) {
            const style = document.createElement('style');
            style.id = 'rule-list-styles';
            style.textContent = `
                .rule-name-cell {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                .builder-icon {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    width: 24px;
                    height: 24px;
                    border-radius: 4px;
                    background: var(--bg-light-gray);
                    color: var(--text-muted);
                    transition: all 0.2s;
                }
                .builder-icon:hover {
                    background: var(--primary);
                    color: white;
                }
            `;
            document.head.appendChild(style);
        }
    }
};
