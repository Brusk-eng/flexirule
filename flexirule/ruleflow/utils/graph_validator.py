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

    # 1. Check for Cycles (DFS with Recursion Stack)
    visited = set()
    recursion_stack = set()

    def detect_cycle(current_id):
        visited.add(current_id)
        recursion_stack.add(current_id)

        current_action = actions.get(current_id)
        if current_action:
            # Get neighbors (next steps)
            neighbors = []
            if current_action.get("next_step_if_true"):
                neighbors.append(current_action.get("next_step_if_true"))
            if current_action.get("action_type") == "Condition" and current_action.get(
                "next_step_if_false"
            ):
                neighbors.append(current_action.get("next_step_if_false"))

            for neighbor in neighbors:
                if neighbor not in visited:
                    if detect_cycle(neighbor):
                        return True
                elif neighbor in recursion_stack:
                    if getattr(current_action, "action_type", "") != "Loop":
                        return True

        recursion_stack.remove(current_id)
        return False

    # Run cycle detection from all nodes (to catch disconnected cycles too)
    for action_id in actions:
        if action_id not in visited:
            if detect_cycle(action_id):
                frappe.throw(
                    _(
                        "Cycle detected in Rule Graph (involving action {0}). Use 'Loop' type for iterations."
                    ).format(action_id)
                )

    # 2. Check for Orphan Nodes (Reachability BFS)
    # Identify Start Node(s)
    start_nodes = []

    # Priority 1: 'root' node or 'Entry Action'
    for a in rule_doc.actions:
        if a.action_id == "root" or a.action_type == "Entry Action":
            start_nodes.append(a.action_id)

    # Priority 2: Legacy 'is_entry_action'
    if not start_nodes:
        start_nodes = [
            a.action_id for a in rule_doc.actions if a.get("is_entry_action")
        ]

    # Priority 3: Fallback to first action
    if not start_nodes and rule_doc.actions:
        start_nodes = [rule_doc.actions[0].action_id]

    reachable = set()
    queue = list(start_nodes)

    while queue:
        node_id = queue.pop(0)
        if node_id in reachable:
            continue
        reachable.add(node_id)

        action = actions.get(node_id)
        if action:
            if action.get("next_step_if_true"):
                queue.append(action.get("next_step_if_true"))
            # Include false paths for Condition, Loop, and Switch actions
            if action.get("action_type") in [
                "Condition",
                "Loop",
                "Switch",
            ] and action.get("next_step_if_false"):
                queue.append(action.get("next_step_if_false"))

    # Check for non-reachable nodes
    orphans = [qid for qid in actions if qid not in reachable]
    if orphans:
        orphan_labels = [actions[o].action_label for o in orphans]
        frappe.throw(
            _("Unreachable (Orphan) Actions found: {0}").format(
                ", ".join(orphan_labels)
            )
        )

    # 3. Check for Dead Ends (Paths not ending in Stop)
    for action in rule_doc.actions:
        if action.action_type in ["Process", "Condition", "Sub-Rule"]:
            # Must have next step OR be explicitly 'Stop' type (which these are not)
            # Process nodes can be terminal if they are the last thing, but V1 expects explicit Stop?
            # Let's enforce that Condition MUST have both paths or explicit Stop
            if action.action_type == "Condition":
                if not action.next_step_if_true:
                    frappe.throw(
                        _("Condition '{0}' missing True path").format(
                            action.action_label
                        )
                    )
                if not action.next_step_if_false:
                    frappe.throw(
                        _("Condition '{0}' missing False path").format(
                            action.action_label
                        )
                    )
