# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
RuleCoordinator - Main entry point for rule execution
Finds applicable rules and dispatches them to appropriate executors
"""

from typing import Any, Dict, List

import frappe
from frappe import _


class RuleCoordinator:
    """Coordinates rule loading, filtering, and execution"""

    # Cache key for unified rule map (follows Frappe server_script_map pattern)
    CACHE_KEY = "flexirule_map"

    @staticmethod
    def get_rule_map() -> dict:
        """
        Get unified rule map from cache or rebuild.
        Structure: {doctype: {event: [rule_names sorted by priority]}}
        """
        # Request-level cache first
        if hasattr(frappe.local, "flexirule_map"):
            return frappe.local.flexirule_map

        # Redis cache
        try:
            rule_map = frappe.cache.get_value(RuleCoordinator.CACHE_KEY)
        except Exception:
            # Circuit Breaker: If Redis is down, fail safe (skip rules) -> Don't crash ERP
            # Log only once per request to avoid spamming if possible, but standard log_error is fine
            frappe.log_error("FlexiRule: Cache unreachable, skipping rules.")
            return {}

        if rule_map is None:
            try:
                rule_map = RuleCoordinator._build_rule_map()
                frappe.cache.set_value(RuleCoordinator.CACHE_KEY, rule_map)
            except Exception:
                frappe.log_error("FlexiRule: Cache write failed.")
                # We can still return the computed map for this request
                return rule_map or {}

        # Store in request-level cache
        frappe.local.flexirule_map = rule_map
        return rule_map

    @staticmethod
    def _build_rule_map() -> dict:
        """Build complete rule map from database"""
        rule_map = {}

        # Fetch all active rules with priority ordering
        active_rules = frappe.get_all(
            "Rule",
            filters={"is_active": 1},
            fields=["name", "document_type", "trigger_event", "priority"],
            order_by="priority desc",
        )

        for rule in active_rules:
            doctype = rule.document_type
            event = rule.trigger_event
            rule_map.setdefault(doctype, {}).setdefault(event, []).append(rule.name)

        return rule_map

    @staticmethod
    def has_active_rules(doctype: str, event_name: str) -> bool:
        """Check if there are any active rules for this doctype/event."""
        rule_map = RuleCoordinator.get_rule_map()
        return bool(rule_map.get(doctype, {}).get(event_name))

    @staticmethod
    def execute_rules(doc, event_name: str):
        """
        Main entry point called from doc_events hooks

        Args:
                doc: Frappe document
                event_name: Event that triggered execution (before_save, validate, etc.)
        """
        # TODO : after allowing in_import We must have optimized way to get rules with allowed in_import
        # Skip during import/migration
        if frappe.flags.in_import or frappe.flags.in_migrate:
            return

        # Quick check if any rules exist for this doctype/event
        if not RuleCoordinator.has_active_rules(doc.doctype, event_name):
            return

        # Get applicable rules
        rules = RuleCoordinator.get_applicable_rules(doc.doctype, event_name)

        if not rules:
            return

        # Strict Eligibility Check (V1 Contract)

        from flexirule.ruleflow.utils.field_resolver import FieldResolver

        # Fetch old_doc for change detection
        old_doc = (
            doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
        )

        valid_rules = []
        for rule_doc in rules:
            is_eligible, reason = RuleCoordinator.check_eligibility(
                rule_doc, doc, event_name, old_doc=old_doc
            )
            if is_eligible:
                valid_rules.append(rule_doc)
            else:
                # Optional: Log ineligibility if debug/trace mode is on for this rule
                if rule_doc.debug_mode:
                    frappe.log_error(
                        title=_("Rule Skipped: {0}").format(rule_doc.name),
                        message=_(reason),
                    )

        # Execute eligible rules
        for rule_doc in valid_rules:
            try:
                RuleCoordinator.execute_single_rule(doc, rule_doc, old_doc=old_doc)
            except Exception as e:
                # Log error
                error_msg = str(e)
                if len(error_msg) > 139:
                    error_msg = error_msg[:139]
                # TODO: this may delete the cached
                rule_doc.last_error = error_msg
                rule_doc.flags.ignore_validate = True
                rule_doc.flags.ignore_permissions = True
                rule_doc.save(update_modified=False)

                if rule_doc.debug_mode:
                    frappe.log_error(
                        title=_("Rule Execution Failed: {0}").format(rule_doc.name),
                        message=_("DocType: {0} Doc: {1} Error: {2}").format(
                            doc.doctype, doc.name, str(e)
                        ),
                    )

                # Re-raise blocking exceptions (Stop the save)
                if isinstance(e, frappe.ValidationError):
                    raise e

    @staticmethod
    def check_eligibility(
        rule_doc,
        doc,
        event_name,
        execution_mode="Synchronous",
        skip_event_check=False,
        old_doc=None,
    ) -> tuple[bool, str]:
        """
        Strict V1 Contract Eligibility Check
        Returns: (is_eligible: bool, reason: str)
        """
        # 1. Active Check
        if not rule_doc.is_active:
            return False, _("Rule is not active")

        # 2. Event Check
        if not skip_event_check and rule_doc.trigger_event != event_name:
            # This might happen if cache returns mixed results or during manual triggers
            return False, _("Event mismatch: Rule expects {0}, got {1}").format(
                rule_doc.trigger_event, event_name
            )

        # 3. Mode Check (Strict)
        # For V1, we enforce that Sync rules run in Sync context.
        # Async is handled by the executor, but we should flag mismatch if needed.
        # Currently, we don't have explicit 'mode' passed from hooks, so we assume Sync.
        # If Rule is Async, it will be queued by execute_single_rule.

        # 4. Condition Check (Compiled Expression)
        # We now rely solely on trigger_condition_expression which is the compiled version of trigger_condition
        if rule_doc.get("trigger_condition_expression"):
            try:
                from flexirule.ruleflow.core.evaluator import check_link_match
                from flexirule.ruleflow.utils.field_resolver import FieldResolver

                # Fetch old_doc if missing
                if not old_doc and hasattr(doc, "get_doc_before_save"):
                    old_doc = doc.get_doc_before_save()

                eval_globals = {
                    "doc": doc,
                    "old_doc": old_doc,
                    "frappe": frappe,
                    "resolve": FieldResolver.resolve,
                    "check_link_match": check_link_match,
                    "True": True,
                    "False": False,
                    "None": None,
                }

                if not frappe.safe_eval(
                    rule_doc.get("trigger_condition_expression"), None, eval_globals
                ):
                    return False, _("Trigger Conditions failed")

            except Exception as e:
                return False, _("Trigger Evaluation Error: {0}").format(str(e))

        # Conditions MUST be pre-compiled - no runtime JSON parsing
        elif rule_doc.get("trigger_condition"):
            return False, _(
                "Rule has trigger_condition but no compiled trigger_condition_expression. Please re-save the Rule."
            )

        return True, _("Eligible")

    @staticmethod
    def get_applicable_rules(doctype: str, event_name: str, doc=None) -> list:
        """
        Get active rules for a doctype and event.
        Uses unified cache map for performance.
        """
        rule_map = RuleCoordinator.get_rule_map()
        rule_names = rule_map.get(doctype, {}).get(event_name, [])

        if not rule_names:
            return []

        rules = []
        for name in rule_names:
            try:
                rules.append(frappe.get_cached_doc("Rule", name))
            except frappe.DoesNotExistError:
                # Rule was deleted but cache not cleared - rebuild
                RuleCoordinator.clear_cache()
                return RuleCoordinator.get_applicable_rules(doctype, event_name, doc)

        return rules

    @staticmethod
    def execute_single_rule(doc, rule_doc, old_doc=None):
        """
        Execute a single rule against a document

        Args:
                doc: Frappe document
                rule_doc: Rule document
                old_doc: Document state before save (optional)
        """
        # Check if rule should run asynchronously
        if rule_doc.execution_mode == "Asynchronous":
            # Async only works for saved documents
            if not doc.get("__islocal"):
                frappe.enqueue(
                    "flexirule.ruleflow.core.coordinator.RuleCoordinator.run_rule_background",
                    rule_name=rule_doc.name,
                    doc_doctype=doc.doctype,
                    doc_name=doc.name,
                    queue="default",
                    timeout=rule_doc.max_execution_time or 300,
                )
                return

        from flexirule.ruleflow.core.engine import RuleEngine

        # Increment execution count (Cached in Redis, not DB write)
        frappe.cache().hincrby(f"rule_stats:{rule_doc.name}", "count", 1)
        frappe.cache().hset(
            f"rule_stats:{rule_doc.name}", "last_executed", frappe.utils.now()
        )

        # Execute using new Engine
        # Pass old_doc in context
        execution_context = {"old_doc": old_doc}
        engine = RuleEngine(rule_doc, execution_context=execution_context)
        engine.execute(doc)

    @staticmethod
    def run_rule_background(rule_name, doc_doctype, doc_name):
        """
        Background job entry point
        """
        try:
            rule_doc = frappe.get_doc("Rule", rule_name)
            doc = frappe.get_doc(doc_doctype, doc_name)

            from flexirule.ruleflow.core.engine import RuleEngine

            # Stats for async
            frappe.cache().hincrby(f"rule_stats:{rule_doc.name}", "count", 1)
            frappe.cache().hset(
                f"rule_stats:{rule_doc.name}", "last_executed", frappe.utils.now()
            )

            engine = RuleEngine(rule_doc)
            engine.execute(doc)

        except Exception as e:
            frappe.log_error(
                _("Async Rule Execution Failed: {0}").format(rule_name), str(e)
            )

    @staticmethod
    def clear_cache(doctype: str = None):
        """
        Clear cached rules. Always clears entire map (atomic rebuild).
        """
        # Clear Redis cache
        frappe.cache.delete_value(RuleCoordinator.CACHE_KEY)

        # Clear request-level cache
        if hasattr(frappe.local, "flexirule_map"):
            delattr(frappe.local, "flexirule_map")

        # Notify distributed workers (v16 pattern)
        frappe.publish_realtime(
            "flexirule_cache_clear",
            {"doctype": doctype},
            after_commit=True,
        )


def execute_rules(doc, event_name):
    """
    Wrapper for RuleCoordinator.execute_rules to be used in hooks
    """
    return RuleCoordinator.execute_rules(doc, event_name)
