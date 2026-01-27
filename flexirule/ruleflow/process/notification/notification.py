# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from flexirule.ruleflow.utils.field_resolver import parse_field_list


def send_email(context, config=None, **kwargs):
	"""
	Send an email notification.

	config: {
	    "recipients": "email@example.com",
	    "subject": "Subject",
	    "message": "Message body",
	    "attach_doc": 0/1
	}
	"""
	doc = context.get("doc")
	if not doc or not config:
		return

	recipients = parse_field_list(config.get("recipients"))
	subject = config.get("subject", "")
	message = config.get("message", "")
	attach_doc = config.get("attach_doc", 0)

	if not recipients or not subject:
		return

	# Render with Jinja
	rendered_subject = frappe.render_template(subject, {"doc": doc, "frappe": frappe, "context": context})
	rendered_message = frappe.render_template(message, {"doc": doc, "frappe": frappe, "context": context})

	attachments = []
	if attach_doc:
		try:
			pdf = frappe.attach_print(doc.doctype, doc.name, doc=doc)
			attachments.append(pdf)
		except Exception as e:
			frappe.log_error(f"Notification: Failed to attach PDF: {e}", "Notification Error")

	frappe.sendmail(
		recipients=recipients,
		subject=rendered_subject,
		message=rendered_message,
		attachments=attachments,
		reference_doctype=doc.doctype,
		reference_name=doc.name,
	)
	return recipients


def create_todo(context, config=None, **kwargs):
	"""
	Create a ToDo assignment.

	config: {
	    "assigned_to": "User",
	    "description": "Task description",
	    "priority": "Medium"
	}
	"""
	doc = context.get("doc")
	if not doc or not config:
		return

	assigned_to = config.get("assigned_to")
	description = config.get("description", "")
	priority = config.get("priority", "Medium")

	if not assigned_to:
		return

	# Render description
	rendered_desc = frappe.render_template(description, {"doc": doc, "frappe": frappe, "context": context})

	todo = frappe.get_doc(
		{
			"doctype": "ToDo",
			"allocated_to": assigned_to,
			"description": rendered_desc,
			"priority": priority,
			"reference_type": doc.doctype,
			"reference_name": doc.name,
		}
	)
	todo.insert(ignore_permissions=True)
	return todo.name


def create_system_notification(context, config=None, **kwargs):
	"""
	Create an in-app Notification Log.
	"""
	doc = context.get("doc")
	if not doc or not config:
		return

	for_user = config.get("for_user") or doc.owner
	subject = config.get("subject", "")
	message = config.get("message", "")

	# Render
	rendered_subject = frappe.render_template(subject, {"doc": doc, "frappe": frappe, "context": context})
	rendered_message = frappe.render_template(message, {"doc": doc, "frappe": frappe, "context": context})

	notification = frappe.get_doc(
		{
			"doctype": "Notification Log",
			"for_user": for_user,
			"subject": rendered_subject,
			"email_content": rendered_message,
			"document_type": doc.doctype,
			"document_name": doc.name,
		}
	)
	notification.insert(ignore_permissions=True)
	return notification.name


def add_comment(context, config=None, **kwargs):
	"""
	Add a comment to the document timeline.
	"""
	doc = context.get("doc")
	if not doc or not config:
		return

	comment_text = config.get("comment_text", "")
	comment_type = config.get("comment_type", "Comment")

	if not comment_text:
		return

	rendered_text = frappe.render_template(comment_text, {"doc": doc, "frappe": frappe, "context": context})

	comment = frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": comment_type,
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"content": rendered_text,
		}
	)
	comment.insert(ignore_permissions=True)
	return comment.name


def send_via_provider(context, config=None, **kwargs):
	"""
	Dispatch notification to an external provider (Slack, WhatsApp, etc).
	Providers are registered via 'flexirule_notification_providers' hook.

	config: {
	    "provider": "slack",
	    "recipient": "#channel",
	    "message": "Hello"
	}
	"""
	doc = context.get("doc")
	if not doc or not config:
		return

	provider_name = config.get("provider")

	# Get providers from hooks
	providers = {}
	for app in frappe.get_installed_apps():
		app_providers = frappe.get_hooks("flexirule_notification_providers", app_name=app)
		if app_providers:
			# Expected hook format: {"slack": "app.module.send_slack"}
			if isinstance(app_providers, list):
				# If list, iterate and update
				for p_dict in app_providers:
					if isinstance(p_dict, dict):
						providers.update(p_dict)
			elif isinstance(app_providers, dict):
				providers.update(app_providers)

	if provider_name not in providers:
		frappe.log_error(f"Notification: Provider '{provider_name}' not found.", "Notification Error")
		return False

	# Dispatch to the provider function
	method_path = providers[provider_name]
	try:
		# Render message before sending
		message = config.get("message", "")
		rendered_message = frappe.render_template(message, {"doc": doc, "frappe": frappe, "context": context})

		# Call provider method: func(recipient, message, doc, context, **config)
		return frappe.get_attr(method_path)(
			recipient=config.get("recipient"),
			message=rendered_message,
			doc=doc,
			context=context,
			config=config,
		)
	except Exception as e:
		frappe.log_error(
			f"Notification: Provider '{provider_name}' failed: {e}",
			"Notification Error",
		)
		return False


# ============================================================
# DISPATCHER
# ============================================================

_OPERATIONS = {
	"send_email": send_email,
	"create_todo": create_todo,
	"create_system_notification": create_system_notification,
	"add_comment": add_comment,
	"send_via_provider": send_via_provider,
}


def execute(context, func=None, config=None):
	if not func:
		frappe.throw(_("Operation function name is required"))
	if func not in _OPERATIONS:
		frappe.throw(_("Unknown notification operation: {0}").format(func))

	return _OPERATIONS[func](context, config or {})
