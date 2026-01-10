/**
 * Notification Process Adapter
 * Provides a future-proof UI for communication and notification tasks.
 */

flexirule.rule_builder.notification = {
    /**
     * Get the process schema metadata
     */
    get_schema() {
        return {
            name: "Notification",
            label: __("Notification"),
            description: __("Send emails, create tasks, and notify external services."),
            icon: "notification",
            color: "blue"
        };
    },

    /**
     * Get a specific operation by name
     */
    get_operation(func_name) {
        const operations = {
            send_email: {
                label: __("Send Email"),
                description: __("Send an email to one or more recipients."),
                icon: "mail"
            },
            create_todo: {
                label: __("Create ToDo"),
                description: __("Assign a task to a user."),
                icon: "list"
            },
            create_system_notification: {
                label: __("System Notification"),
                description: __("Create an in-app notification."),
                icon: "bell"
            },
            add_comment: {
                label: __("Add Comment"),
                description: __("Post a comment on the document timeline."),
                icon: "chat-dot"
            },
            send_via_provider: {
                label: __("Send via Provider"),
                description: __("Use external channels like Slack or WhatsApp."),
                icon: "share"
            }
        };
        return operations[func_name];
    },

    /**
     * Get visible operations
     */
    get_visible_operations() {
        return ["send_email", "create_todo", "create_system_notification", "add_comment", "send_via_provider"];
    },

    /**
     * Get default configuration
     */
    get_default_config(operation) {
        const defaults = {
            send_email: { recipients: "", subject: "", message: "", attach_doc: 0 },
            create_todo: { assigned_to: "", description: "", priority: "Medium" },
            create_system_notification: { for_user: "", subject: "", message: "" },
            add_comment: { comment_text: "", comment_type: "Comment" },
            send_via_provider: { provider: "", recipient: "", message: "" }
        };
        return defaults[operation] || {};
    },

    /**
     * Get UI fields for configuration
     */
    get_config_fields(operation, context) {
        if (operation === "send_email") {
            return [
                {
                    fieldname: "recipients",
                    fieldtype: "Small Text",
                    label: __("Recipients"),
                    description: __("Email addresses, one per line. Supports Jinja."),
                    reqd: 1
                },
                {
                    fieldname: "subject",
                    fieldtype: "Data",
                    label: __("Subject"),
                    reqd: 1
                },
                {
                    fieldname: "message",
                    fieldtype: "Text Editor",
                    label: __("Message"),
                    reqd: 1
                },
                {
                    fieldname: "attach_doc",
                    fieldtype: "Check",
                    label: __("Attach Document PDF"),
                    default: 0
                }
            ];
        }

        if (operation === "create_todo") {
            return [
                {
                    fieldname: "assigned_to",
                    fieldtype: "Link",
                    label: __("Assign To"),
                    options: "User",
                    reqd: 1
                },
                {
                    fieldname: "priority",
                    fieldtype: "Select",
                    label: __("Priority"),
                    options: "Low\nMedium\nHigh",
                    default: "Medium"
                },
                {
                    fieldname: "description",
                    fieldtype: "Small Text",
                    label: __("Description"),
                    description: __("Task details. Supports Jinja."),
                    reqd: 1
                }
            ];
        }

        if (operation === "create_system_notification") {
            return [
                {
                    fieldname: "for_user",
                    fieldtype: "Link",
                    label: __("For User"),
                    options: "User",
                    description: __("Leave empty for document owner.")
                },
                {
                    fieldname: "subject",
                    fieldtype: "Data",
                    label: __("Subject"),
                    reqd: 1
                },
                {
                    fieldname: "message",
                    fieldtype: "Small Text",
                    label: __("Message"),
                    reqd: 1
                }
            ];
        }

        if (operation === "add_comment") {
            return [
                {
                    fieldname: "comment_type",
                    fieldtype: "Select",
                    label: __("Type"),
                    options: "Comment\nInfo\nWorkflow",
                    default: "Comment"
                },
                {
                    fieldname: "comment_text",
                    fieldtype: "Small Text",
                    label: __("Comment"),
                    reqd: 1
                }
            ];
        }

        if (operation === "send_via_provider") {
            return [
                {
                    fieldname: "provider",
                    fieldtype: "Select",
                    label: __("Provider"),
                    options: this.get_provider_options(),
                    reqd: 1,
                    onchange: (val, ctx) => {
                        // Logic to change help text or fields based on provider if needed
                        const help = {
                            slack: __("Recipient should be a channel ID or user ID (e.g., #general)."),
                            whatsapp: __("Recipient should be a phone number with country code."),
                            sms: __("Recipient should be a phone number.")
                        };
                        ctx.update_field("recipient", { description: help[val] || "" });
                    }
                },
                {
                    fieldname: "recipient",
                    fieldtype: "Data",
                    label: __("Recipient/Channel"),
                    reqd: 1
                },
                {
                    fieldname: "message",
                    fieldtype: "Small Text",
                    label: __("Message"),
                    reqd: 1
                }
            ];
        }

        return [];
    },

    /**
     * Get available notification providers.
     * In a real scenario, this could be fetched from the server.
     */
    get_provider_options() {
        // Default options, should ideally be synced with server hooks
        return [
            { label: __("Select Provider..."), value: "" },
            { label: "Slack", value: "slack" },
            { label: "WhatsApp", value: "whatsapp" },
            { label: "SMS", value: "sms" },
            { label: "Custom", value: "custom" }
        ];
    }
};
