/**
 * Notification Process Adapter
 * Provides a future-proof UI for communication and notification tasks.
 */

frappe.provide("flexirule.processes");

flexirule.processes["Notification"] = {
    meta: {
        version: "1.0",
        title: __("Notification"),
    },

    get_schema(operation_name, ctx) {
        const operation = this.get_operation(operation_name);
        if (!operation) return [];
        return typeof operation.get_config_fields === "function"
            ? operation.get_config_fields(ctx)
            : [];
    },

    operations: [
        {
            func_name: "send_email",
            label: __("Send Email"),
            description: __("Send an email to one or more recipients."),
            icon: "mail",
            get_config_fields: (ctx) => [
                {
                    fieldname: "recipients",
                    fieldtype: "Small Text",
                    label: __("Recipients"),
                    description: __("Email addresses, one per line. Supports Jinja."),
                    reqd: 1,
                },
                {
                    fieldname: "subject",
                    fieldtype: "Data",
                    label: __("Subject"),
                    reqd: 1,
                },
                {
                    fieldname: "message",
                    fieldtype: "Text Editor",
                    label: __("Message"),
                    reqd: 1,
                },
                {
                    fieldname: "attach_doc",
                    fieldtype: "Check",
                    label: __("Attach Document PDF"),
                    default: 0,
                },
            ],
        },
        {
            func_name: "create_todo",
            label: __("Create ToDo"),
            description: __("Assign a task to a user."),
            icon: "list",
            get_config_fields: (ctx) => [
                {
                    fieldname: "assigned_to",
                    fieldtype: "Link",
                    label: __("Assign To"),
                    options: "User",
                    reqd: 1,
                },
                {
                    fieldname: "priority",
                    fieldtype: "Select",
                    label: __("Priority"),
                    options: "Low\nMedium\nHigh",
                    default: "Medium",
                },
                {
                    fieldname: "description",
                    fieldtype: "Small Text",
                    label: __("Description"),
                    description: __("Task details. Supports Jinja."),
                    reqd: 1,
                },
            ],
        },
        {
            func_name: "create_system_notification",
            label: __("System Notification"),
            description: __("Create an in-app notification."),
            icon: "bell",
            get_config_fields: (ctx) => [
                {
                    fieldname: "for_user",
                    fieldtype: "Link",
                    label: __("For User"),
                    options: "User",
                    description: __("Leave empty for document owner."),
                },
                {
                    fieldname: "subject",
                    fieldtype: "Data",
                    label: __("Subject"),
                    reqd: 1,
                },
                {
                    fieldname: "message",
                    fieldtype: "Small Text",
                    label: __("Message"),
                    reqd: 1,
                },
            ],
        },
        {
            func_name: "add_comment",
            label: __("Add Comment"),
            description: __("Post a comment on the document timeline."),
            icon: "chat-dot",
            get_config_fields: (ctx) => [
                {
                    fieldname: "comment_type",
                    fieldtype: "Select",
                    label: __("Type"),
                    options: "Comment\nInfo\nWorkflow",
                    default: "Comment",
                },
                {
                    fieldname: "comment_text",
                    fieldtype: "Small Text",
                    label: __("Comment"),
                    reqd: 1,
                },
            ],
        },
        {
            func_name: "send_via_provider",
            label: __("Send via Provider"),
            description: __("Use external channels like Slack or WhatsApp."),
            icon: "share",
            get_config_fields: (ctx) => [
                {
                    fieldname: "provider",
                    fieldtype: "Select",
                    label: __("Provider"),
                    options: flexirule.processes.Notification.get_provider_options(),
                    reqd: 1,
                    onchange: (val, row, ctx) => {
                        const help = {
                            slack: __("Recipient should be a channel ID or user ID (e.g., #general)."),
                            whatsapp: __("Recipient should be a phone number with country code."),
                            sms: __("Recipient should be a phone number."),
                        };
                        ctx.update_field("recipient", { description: help[val] || "" });
                    },
                },
                {
                    fieldname: "recipient",
                    fieldtype: "Data",
                    label: __("Recipient/Channel"),
                    reqd: 1,
                },
                {
                    fieldname: "message",
                    fieldtype: "Small Text",
                    label: __("Message"),
                    reqd: 1,
                },
            ],
        },
    ],

    get_operation(name) {
        return this.operations.find((op) => op.func_name === name);
    },

    get_provider_options() {
        // Default options, should ideally be synced with server hooks
        return [
            { label: __("Select Provider..."), value: "" },
            { label: "Slack", value: "slack" },
            { label: "WhatsApp", value: "whatsapp" },
            { label: "SMS", value: "sms" },
            { label: "Custom", value: "custom" },
        ];
    },
};
