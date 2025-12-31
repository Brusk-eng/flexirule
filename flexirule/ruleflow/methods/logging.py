# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Logging process methods
"""

import frappe
import flexirule

@flexirule.processmethod(
    category="Custom",
    side_effects="External Call",
    description="Log a message to the system console/log",
    creates_new_docs=False, # Standard logging doesn't create a DocType unless we use System Log
    transactional=False
)
def system_log(context, message=None, level="Info", **kwargs):
    """
    Log to Frappe logger
    """
    doc = context.get('doc')
    msg = frappe.render_template(message or '', {'doc': doc})
    
    if level == "Error":
        frappe.log_error(msg, title=f"Rule Log: {doc.name}")
    else:
        # Just print to stdout/stderr in current process or use logger
        frappe.logger().info(f"[Rule {doc.name}] {msg}")
    
    return True

@flexirule.processmethod(
    category="Custom",
    side_effects="External Call",
    creates_new_docs=True,
    description="Create a System Log entry",
    transactional=False
)
def create_system_log(context, message=None, type="Info", **kwargs):
    """
    Create a persistent log entry document (mock example)
    """
    if not message:
        return
        
    doc = context.get('doc')
    rendered_msg = frappe.render_template(message, {'doc': doc})
    
    # Assuming a Generic Log doctype exists, or just use Note
    # For demo we will use Note
    log = frappe.get_doc({
        "doctype": "Note",
        "title": f"Rule Log: {doc.name}",
        "content": rendered_msg,
        "public": 0
    })
    log.insert(ignore_permissions=True)
    return log.name
