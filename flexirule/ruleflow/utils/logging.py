# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Logging utilities for FlexiRule rule execution.
Provides transaction-safe logging that survives rollbacks.
"""

import frappe


def persist_execution_log(log_data: dict):
    """
    Persist an execution log entry in a separate transaction.
    This is called via frappe.enqueue to ensure the log is saved
    even when the main transaction rolls back.

    Args:
        log_data: Dictionary containing all fields for Rule Execution Log
    """
    try:
        log_doc = frappe.get_doc({"doctype": "Rule Execution Log", **log_data})
        log_doc.insert(ignore_permissions=True, ignore_links=True)
        frappe.db.commit()
    except Exception as e:
        frappe.logger().error(f"Failed to persist Rule Execution Log: {e!s}")
