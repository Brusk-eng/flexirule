# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
User-friendly error handling for Bolton Rule Engine
"""

import frappe
from frappe import _


class BoltonError(Exception):
    """Base Bolton error with user-friendly message"""
    
    def __init__(self, message, title=None, indicator="red"):
        self.message = message
        self.title = title or _("Rule Error")
        self.indicator = indicator
        super().__init__(message)
    
    def show(self):
        frappe.msgprint(
            msg=self.message,
            title=self.title,
            indicator=self.indicator
        )


class RuleValidationError(BoltonError):
    """Validation failed"""
    def __init__(self, message, field=None):
        title = _("Validation Error")
        if field:
            message = _("Field '{0}': {1}").format(field, message)
        super().__init__(message, title, "orange")


class RuleExecutionError(BoltonError):
    """Rule execution failed"""
    def __init__(self, rule_name, action=None, original_error=None):
        if action:
            message = _("Rule '{0}' failed at action '{1}'").format(rule_name, action)
        else:
            message = _("Rule '{0}' failed to execute").format(rule_name)
        
        if original_error:
            message += f": {str(original_error)}"
        
        super().__init__(message, _("Rule Execution Failed"), "red")


class RuleConfigError(BoltonError):
    """Rule configuration error"""
    def __init__(self, rule_name, issue):
        message = _("Rule '{0}' has configuration issue: {1}").format(rule_name, issue)
        super().__init__(message, _("Configuration Error"), "orange")


class RulePermissionError(BoltonError):
    """Permission denied"""
    def __init__(self, rule_name=None, action=None):
        if rule_name:
            message = _("You don't have permission to execute rule '{0}'").format(rule_name)
        else:
            message = _("Permission denied for this operation")
        super().__init__(message, _("Permission Denied"), "red")


class DuplicateError(BoltonError):
    """Duplicate record found"""
    def __init__(self, doctype, duplicates, fields):
        field_labels = ", ".join(fields)
        dup_links = ", ".join([f"<a href='/app/{doctype}/{d}'>{d}</a>" for d in duplicates[:3]])
        message = _(
            "Duplicate found based on: {0}<br>"
            "Matching records: {1}"
        ).format(field_labels, dup_links)
        super().__init__(message, _("Duplicate Found"), "orange")


def handle_rule_error(func):
    """Decorator for user-friendly error handling"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BoltonError:
            raise
        except frappe.ValidationError:
            raise
        except Exception as e:
            frappe.log_error(
                title="Bolton Rule Error",
                message=str(e)
            )
            raise BoltonError(
                _("An unexpected error occurred. Please contact support."),
                _("System Error")
            )
    return wrapper
