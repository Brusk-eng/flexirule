# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Notification process methods for the Bolton Rule Engine
"""

import frappe
from frappe import _
from .utils import parse_field_list


def send_email_notification(context, recipients=None, subject=None, message=None, attach_document=False, **kwargs):
    """
    Send email to recipients
    """
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
