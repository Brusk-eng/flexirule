import frappe
from frappe import _

def execute():
    frappe.reload_doc("ruleflow", "doctype", "rule_action")
    frappe.reload_doc("ruleflow", "doctype", "rule")
    
    rules = frappe.get_all("Rule", fields=["name", "trigger_event"])
    
    for rule_data in rules:
        rule = frappe.get_doc("Rule", rule_data.name)
        
        # Check if root exists
        if any(a.action_id == 'root' for a in rule.actions):
            continue
            
        print(f"Migrating Rule: {rule.name}")
        
        # Find the 'effective' start node (no incoming edges)
        # We reuse the logic we just put in engine but simplified here
        # Actually simpler: just find the first action as per current logic
        
        first_action_id = None
        if rule.actions:
            # Simple heuristic: The one with idx=1 or just the first one
            # Ideally we check connectivity but for now assuming first defined is start is safe enough
            # as previously Engine used to fall back to first action.
             first_action_id = rule.actions[0].action_id
        
        # Create Root Node
        root_action = rule.append("actions", {
            "action_type": "Entry Action",
            "action_label": _(rule.trigger_event or "Start"),
            "action_id": "root",
            "is_enabled": 1,
            "position_x": 50,
            "position_y": 250,
            # If we found a first action, we point to it
            "next_step_if_true": first_action_id
        })
        
        # Shift other nodes to the right so they don't overlap
        for action in rule.actions:
            if action.action_id != 'root':
                action.position_x = (action.position_x or 0) + 200
        
        rule.save(ignore_permissions=True)
