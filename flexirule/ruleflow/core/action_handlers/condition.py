# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Condition Action Handler.

Evaluates a compiled Python condition expression and routes to
next_step_if_true or next_step_if_false based on the result.
"""

from frappe import _

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry


class ConditionHandler(ActionHandler):
    """Handler for Condition action type."""

    action_type = "Condition"

    def execute(self, action, context, engine):
        """
        Execute condition evaluation.

        The condition_expression should already be compiled from condition_json
        during Rule.validate(). If condition_expression is missing but
        condition_json exists, the rule was not properly saved.

        Returns:
            Tuple of (boolean_result, next_action_id)
        """
        if not action.condition_expression:
            if action.condition_json:
                raise ValueError(
                    _(
                        "Action '{0}' has condition_json but no compiled condition_expression. "
                        "Please re-save the Rule to compile conditions."
                    ).format(action.action_label)
                )
            # Empty condition passes
            result = True
        else:
            result = engine._evaluate_python_condition(
                action.condition_expression, context
            )

        next_id = action.next_step_if_true if result else action.next_step_if_false
        return result, next_id

    def validate(self, action, context):
        """Validate condition action configuration."""
        errors = []
        if action.condition_json and not action.condition_expression:
            errors.append(
                _("Condition '{0}' needs to be compiled. Re-save the rule.").format(
                    action.action_label
                )
            )
        return errors


# Register the handler
HandlerRegistry.register(ConditionHandler())
