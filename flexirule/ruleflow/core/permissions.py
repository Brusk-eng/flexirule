# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Permission checking for Bolton Rule Engine
"""

import frappe
from frappe import _


def check_rule_permission(rule_doc, throw=True):
    """
    Check if current user can execute a rule
    
    Args:
        rule_doc: Rule DocType document
        throw: Whether to throw error or return bool
        
    Returns:
        Boolean if throw=False
    """
    user = frappe.session.user
    
    # System Manager can always execute
    if "System Manager" in frappe.get_roles(user):
        return True
    
    # Check if user has permission on the target doctype
    target_doctype = rule_doc.document_type
    if not frappe.has_permission(target_doctype, "write"):
        if throw:
            frappe.throw(
                _("You need write permission on {0} to execute this rule").format(target_doctype),
                frappe.PermissionError
            )
        return False
    
    # Check rule-specific allowed roles if defined
    if hasattr(rule_doc, 'allowed_roles') and rule_doc.allowed_roles:
        allowed = [r.role for r in rule_doc.allowed_roles]
        user_roles = frappe.get_roles(user)
        
        if not any(role in user_roles for role in allowed):
            if throw:
                frappe.throw(
                    _("You don't have the required role to execute rule '{0}'").format(rule_doc.rule_name),
                    frappe.PermissionError
                )
            return False
    
    return True


def check_method_permission(method_path, throw=True):
    """
    Check if method is allowed to be executed
    
    Args:
        method_path: Full dotted path to method
        throw: Whether to throw error or return bool
    """
    # Check against blocklist
    blocklist = frappe.get_hooks("flexirule_method_blocklist") or []
    
    if method_path in blocklist:
        if throw:
            frappe.throw(
                _("Method '{0}' is not allowed").format(method_path),
                frappe.PermissionError
            )
        return False
    
    return True


def can_modify_rule(rule_doc, throw=True):
    """Check if user can modify a rule"""
    user = frappe.session.user
    
    # System Manager can always modify
    if "System Manager" in frappe.get_roles(user):
        return True
    
    # Rule Builder role can modify
    if "Rule Builder" in frappe.get_roles(user):
        return True
    
    # Check if user owns the rule
    if rule_doc.owner == user:
        return True
    
    if throw:
        frappe.throw(
            _("You don't have permission to modify this rule"),
            frappe.PermissionError
        )
    return False


def validate_safe_eval(expression):
    """
    Validate that an expression is safe to evaluate
    
    Args:
        expression: Python expression string
        
    Raises:
        ValidationError if unsafe
    """
    # Dangerous patterns
    dangerous = [
        "import ", "__import__", "exec(", "eval(", 
        "open(", "os.", "subprocess", "system(",
        "__class__", "__bases__", "__globals__"
    ]
    
    expr_lower = expression.lower()
    for pattern in dangerous:
        if pattern in expr_lower:
            frappe.throw(
                _("Expression contains forbidden pattern: {0}").format(pattern),
                frappe.ValidationError
            )
