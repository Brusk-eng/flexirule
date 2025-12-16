# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Notification process methods for the Bolton Rule Engine
"""

import frappe
from frappe import _
from frappe import _
from .utils import parse_field_list
from flexirule.ruleflow.decorators import process_method

@process_method(
    category="Notification",
    side_effects="External Call",
    description="Send email to recipients",
    config_schema={
        "fields": [
            {
                "fieldname": "recipients",
                "fieldtype": "Small Text",
                "label": "Recipients",
                "reqd": 1,
                "description": "Email addresses (one per line)"
            },
            {
                "fieldname": "subject",
                "fieldtype": "Data",
                "label": "Subject",
                "reqd": 1
            },
            {
                "fieldname": "message",
                "fieldtype": "Text Editor",
                "label": "Message",
                "reqd": 1
            },
            {
                "fieldname": "attach_document",
                "fieldtype": "Check",
                "label": "Attach Document PDF"
            }
        ]
    }
)
def send_email_notification(context, recipients=None, subject=None, message=None, attach_document=False, **kwargs):
    doc = context.get('doc')
    
    # Parse recipients
    recipient_list = parse_field_list(recipients)
    
    if not recipient_list or not subject:
        return None
    
    # Render message with doc context
    rendered_message = frappe.render_template(message or '', {'doc': doc})
    rendered_subject = frappe.render_template(subject, {'doc': doc})
    
    attachments = []
    if attach_document:
        try:
            pdf = frappe.attach_print(doc.doctype, doc.name, print_format=None, doc=doc)
            attachments.append(pdf)
        except Exception:
            pass
    
    frappe.sendmail(
        recipients=recipient_list,
        subject=rendered_subject,
        message=rendered_message,
        attachments=attachments,
        reference_doctype=doc.doctype,
        reference_name=doc.name
    )
    
    return recipient_list


@process_method(
    category="Notification",
    side_effects="External Call",
    creates_new_docs=True,
    description="Create a TODO task",
    config_schema={
        "fields": [
            {
                "fieldname": "assigned_to",
                "fieldtype": "Link",
                "label": "Assign To",
                "reqd": 1,
                "options": "User"
            },
            {
                "fieldname": "description",
                "fieldtype": "Small Text",
                "label": "Description",
                "reqd": 1
            },
            {
                "fieldname": "priority",
                "fieldtype": "Select",
                "label": "Priority",
                "options": "Low\nMedium\nHigh",
                "default": "Medium"
            }
        ]
    }
)
def create_todo(context, assigned_to=None, description=None, priority='Medium', **kwargs):
    """
    Create a TODO task for a user
    """
    doc = context.get('doc')
    
    todo = frappe.get_doc({
        'doctype': 'ToDo',
        'owner': assigned_to,
        'allocated_to': assigned_to,
        'description': frappe.render_template(description, {'doc': doc}),
        'priority': priority,
        'reference_type': doc.doctype,
        'reference_name': doc.name
    })
    todo.insert(ignore_permissions=True)
    
    return todo.name


@process_method(
    category="Notification",
    side_effects="External Call",
    creates_new_docs=True,
    description="Create in-app notification",
    config_schema={
        "fields": [
            {
                "fieldname": "for_user",
                "fieldtype": "Link",
                "label": "For User",
                "reqd": 1,
                "options": "User"
            },
            {
                "fieldname": "subject",
                "fieldtype": "Data",
                "label": "Subject",
                "reqd": 1
            },
            {
                "fieldname": "message",
                "fieldtype": "Small Text",
                "label": "Message",
                "reqd": 1
            }
        ]
    }
)
def create_notification_log(context, for_user=None, subject=None, message=None, **kwargs):
    """
    Create in-app notification
    """
    doc = context.get('doc')
    
    # Handle Document Owner option
    if for_user == 'Document Owner' or not for_user:
        for_user = doc.owner
    
    notification = frappe.get_doc({
        'doctype': 'Notification Log',
        'for_user': for_user,
        'subject': frappe.render_template(subject, {'doc': doc}),
        'document_type': doc.doctype,
        'document_name': doc.name,
        'email_content': frappe.render_template(message or '', {'doc': doc})
    })
    notification.insert(ignore_permissions=True)
    
    return notification.name


@process_method(
    category="Notification",
    side_effects="External Call",
    creates_new_docs=True,
    description="Add a comment to the document",
    config_schema={
        "fields": [
            {
                "fieldname": "comment_text",
                "fieldtype": "Small Text",
                "label": "Comment",
                "reqd": 1
            },
            {
                "fieldname": "comment_type",
                "fieldtype": "Select",
                "label": "Type",
                "options": "Comment\nInfo\nWorkflow",
                "default": "Comment"
            }
        ]
    }
)
def create_comment(context, comment_text=None, comment_type='Comment', **kwargs):
    """
    Add a comment to the document
    """
    doc = context.get('doc')
    
    comment = frappe.get_doc({
        'doctype': 'Comment',
        'comment_type': comment_type,
        'reference_doctype': doc.doctype,
        'reference_name': doc.name,
        'content': frappe.render_template(comment_text or '', {'doc': doc})
    })
    comment.insert(ignore_permissions=True)
    
    return comment.name
