# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

"""
Simple Action Handlers.

Contains handlers for simpler action types that don't require
complex logic: Stop, Wait, Set Value, Raise Error, Notify.
"""

import time

import frappe
from frappe import _

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry


class StopHandler(ActionHandler):
    """Handler for Stop action type - terminates rule execution."""

    action_type = "Stop"

    def execute(self, action, context, engine):
        """Stop action - terminates execution by returning None for next_id."""
        engine._log("INFO", _("Stop action encountered"))
        return None, None


class WaitHandler(ActionHandler):
    """Handler for Wait action type - pauses execution."""

    action_type = "Wait"

    def execute(self, action, context, engine):
        """
        Wait action - pauses execution for specified duration.

        Config options:
        - duration: Seconds to wait

        Falls back to action.timeout if duration not in config.
        """
        config = engine._get_action_config(action)

        duration = config.get("duration", 0)
        if not duration and action.timeout:
            duration = action.timeout

        if duration > 0:
            engine._log("INFO", _("Waiting for {0} seconds...").format(duration))
            time.sleep(duration)

        return None, action.next_step_if_true


class SetValueHandler(ActionHandler):
    """Handler for Set Value action type - updates document fields."""

    action_type = "Set Value"

    def execute(self, action, context, engine):
        """
        Set Value action - updates a field using Jinja template.

        Uses action.target_field and action.value_template.
        The template is rendered with access to doc, vars, frappe, utils.
        """
        target_field = getattr(action, "target_field", None)
        value_template = getattr(action, "value_template", "") or ""

        if not target_field:
            engine._log("WARNING", _("Set Value action missing target_field"))
            return None, getattr(action, "next_step_if_true", None)

        # Render Jinja template
        template_context = {
            "doc": context.get("doc"),
            "vars": context.get("vars", {}),
            "frappe": frappe,
            "utils": frappe.utils,
        }
        rendered_value = frappe.render_template(value_template, template_context)

        # Set the value on the document
        doc = context.get("doc")
        if doc and hasattr(doc, "set"):
            doc.set(target_field, rendered_value)
            engine._log("INFO", _("Set {0} = {1}").format(target_field, rendered_value))
        else:
            engine._log("WARNING", _("Cannot set field - no document in context"))

        return rendered_value, getattr(action, "next_step_if_true", None)


class RaiseErrorHandler(ActionHandler):
    """Handler for Raise Error action type - throws ValidationError."""

    action_type = "Raise Error"

    def execute(self, action, context, engine):
        """
        Raise Error action - throws ValidationError with Jinja message.

        Uses action.error_template for the error message.
        """
        error_template = getattr(action, "error_template", "") or "Validation Error"

        # Render Jinja template
        template_context = {
            "doc": context.get("doc"),
            "vars": context.get("vars", {}),
            "frappe": frappe,
            "utils": frappe.utils,
        }
        message = frappe.render_template(error_template, template_context)

        engine._log("INFO", _("Raising error: {0}").format(message))
        frappe.throw(message)


class NotifyHandler(ActionHandler):
    """Handler for Notify action type - sends notifications."""

    action_type = "Notify"

    def execute(self, action, context, engine):
        """
        Notify action - sends notification using Jinja template.

        Supports notification types:
        - Toast: Browser alert message
        - System: Realtime publish
        - Email: Queued email notification
        """
        notification_template = getattr(action, "notification_template", "") or ""
        notification_type = getattr(action, "notification_type", "Toast") or "Toast"

        # Render Jinja template
        template_context = {
            "doc": context.get("doc"),
            "vars": context.get("vars", {}),
            "frappe": frappe,
            "utils": frappe.utils,
        }
        message = frappe.render_template(notification_template, template_context)

        if notification_type == "Toast":
            frappe.msgprint(message, alert=True)
        elif notification_type == "System":
            frappe.publish_realtime(
                "msgprint",
                {"message": message, "alert": True},
                user=frappe.session.user,
            )
        elif notification_type == "Email":
            # Queue email notification
            doc = context.get("doc")
            if doc:
                frappe.sendmail(
                    recipients=[frappe.session.user],
                    subject=_("Rule Notification: {0}").format(engine.rule.name),
                    message=message,
                    reference_doctype=doc.doctype,
                    reference_name=doc.name,
                )

        engine._log("INFO", _("Sent {0} notification").format(notification_type))
        return None, getattr(action, "next_step_if_true", None)


class EntryActionHandler(ActionHandler):
    """Handler for Entry Action type - marks the start node."""

    action_type = "Entry Action"

    def execute(self, action, context, engine):
        """Entry Action - simply passes through to next step."""
        return None, action.next_step_if_true


# Register all handlers
HandlerRegistry.register(StopHandler())
HandlerRegistry.register(WaitHandler())
HandlerRegistry.register(SetValueHandler())
HandlerRegistry.register(RaiseErrorHandler())
HandlerRegistry.register(NotifyHandler())
HandlerRegistry.register(EntryActionHandler())
