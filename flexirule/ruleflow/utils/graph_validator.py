# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def validate_graph_integrity(rule_doc):
    """
    Validate connectivity and termination of the Rule Flow graph
    """
    if not rule_doc.actions:
        return

    actions = {a.action_id: a for a in rule_doc.actions}
    
    # 1. Check for Orphan Nodes (Unreachable)
    # Start BFS/DFS from first action (assuming row 1 is start for now, or implicit start)
    # Note: Real start node logic might depend on triggers. 
    # For now, we assume implicit start points to the first action or specific triggers.
    
    # 2. Check for Dead Ends (Paths not ending in Stop)
    for action in rule_doc.actions:
        if action.action_type == 'Process':
            # Check transitions
            if not action.next_step_if_true and action.on_error != 'Stop':
                # Warning: Process dead end? Could be valid if it's the last step.
                # Ideally, explicit Stop node is better.
                pass

        if action.action_type == 'Condition':
             if not action.next_step_if_true:
                 frappe.throw(_("Condition '{0}' missing True path").format(action.action_label))
             # False path is optional (fallthrough)

    # 3. Check for Infinite Loops (unless Loop type)
    # This requires full cycle detection algorithm. 
    # Simplified check: Action pointing to itself
    for action in rule_doc.actions:
        if action.next_step_if_true == action.action_id and action.action_type != 'Loop':
            frappe.throw(_("Action '{0}' points to itself but is not a Loop type").format(action.action_label))
