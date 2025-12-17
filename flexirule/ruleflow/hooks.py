"""
Hook wrapper functions for Bolton rule engine
These are called from hooks.py doc_events
Module-level functions only - no class methods in hook paths!
"""

import frappe


def get_excluded_doctypes():
    """Get list of doctypes to exclude from rule execution"""
    excluded = frappe.get_hooks("flexirule_excluded_doctypes") or []
    
    default_excluded = [
        "Error Log", "Activity Log", "Access Log", "Email Queue",
        "Scheduled Job Log", "Version", "Comment", "Communication", "File",
        "Rule", "Rule Action", "Process Method"
    ]
    
    return list(set(excluded + default_excluded))


def execute_rules(doc, method=None):
    """
    Hook wrapper to execute rules for a document.
    This is a MODULE-LEVEL function that can be called from hooks.py
    """
    # TODO : Must have a check fieldtype to allow run Rule in_import and default to disallow.
    # TODO : 
    if frappe.flags.in_import or frappe.flags.in_migrate:
        return
    
    if doc.doctype in get_excluded_doctypes():
        return
    
    from flexirule.ruleflow.core.coordinator import RuleCoordinator
    
    event_map = {
        'before_insert': 'Before Insert',
        'before_save': 'Before Save',
        'validate': 'Validate',
        'after_insert': 'After Insert',
        'after_save': 'After Save',
        'before_submit': 'Before Submit',
        'on_submit': 'On Submit',
        'before_cancel': 'Before Cancel',
        'on_cancel': 'On Cancel',
        'on_trash': 'On Trash'
    }
    
    trigger_event = event_map.get(method)
    if trigger_event:
        RuleCoordinator.execute_rules(doc, trigger_event)


def clear_rule_cache(doc=None, method=None):
    """
    Clear rule cache when Rule document is modified.
    This is a MODULE-LEVEL function callable from hooks.py
    """
    from flexirule.ruleflow.core.coordinator import RuleCoordinator
    RuleCoordinator.clear_cache()
