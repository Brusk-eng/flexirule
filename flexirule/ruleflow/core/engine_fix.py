def _get_start_node_fixed(self):
    """Get the first action to execute (one with no incoming edges)"""
    # Build set of actions that have incoming edges
    has_incoming = set()

    for action in self.actions:
        action_id = action.action_id or action.name

        # Check all actions' next_step fields
        for other in self.actions:
            if other.next_step_if_true == action_id:
                has_incoming.add(action_id)
            if other.next_step_if_false == action_id:
                has_incoming.add(action_id)
   # Find action with no incoming edges (true start node)
    for action in self.actions:
        action_id = action.action_id or action.name
        if action_id not in has_incoming:
            self._log("INFO", f"Start node: {action.action_label} ({action_id})")
            return action

    # Fallback to first action if no clear start
    self._log("WARNING", "No clear start node, using first action")
    return self.actions[0] if self.actions else None
