# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Switch Action Handler.

Implements switch/case logic based on expression evaluation.
"""

from frappe import _

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry


class SwitchHandler(ActionHandler):
    """Handler for Switch action type."""

    action_type = "Switch"

    def execute(self, action, context, engine):
        """
        Execute switch/case logic.

        Config structure:
        {
            "expression": "doc.status",  # Expression to evaluate
            "cases": {
                "Draft": "action_id_1",
                "Pending": "action_id_2",
                "Approved": "action_id_3"
            }
        }

        If no case matches, falls through to next_step_if_true.

        Returns:
            Tuple of (expression_value, next_action_id)
        """
        config = engine._get_action_config(action)
        if not config:
            return None, getattr(action, "next_step_if_true", None)

        try:
            expression = config.get("expression")
            cases = config.get("cases", {})

            if not expression:
                return None, getattr(action, "next_step_if_true", None)

            # Evaluate expression to get switch value
            val = engine._evaluate_python_condition(expression, context)

            # Match case - try both original value and string conversion
            # (JSON keys are always strings)
            next_id = cases.get(val) or cases.get(str(val)) or action.next_step_if_true

            return val, next_id

        except Exception as e:
            engine._log("ERROR", _("Switch evaluation failed: {0}").format(str(e)))
            raise


# Register the handler
HandlerRegistry.register(SwitchHandler())
