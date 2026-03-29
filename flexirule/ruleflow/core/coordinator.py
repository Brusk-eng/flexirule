# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
RuleCoordinator - Main entry point for rule execution
Finds applicable rules and dispatches them to appropriate executors
"""

from typing import Any, ClassVar

import frappe
from frappe import _


class RuleCoordinator:
	"""Coordinates rule loading, filtering, and execution"""

	# Cache key for unified rule map (follows Frappe server_script_map pattern)
	CACHE_KEY = "flexirule_map"

	BLOCKING_EVENTS: ClassVar[set[str]] = {
		"Before Naming",
		"Before Insert",
		"Before Save",
		"Validate",
		"Before Submit",
		"On Submit",
		"Before Cancel",
		"On Cancel",
		"On Trash",
		"On Update After Submit",
		"Before Rename",
		"After Rename",
		"Before Print",
	}

	@staticmethod
	def execute_rule(rule: Any, context: dict | None = None, dry_run: bool = False) -> dict:
		"""
		Pure execution API for a single rule.
		Can be used for replay, dry-runs, and deterministic testing.

		Args:
		    rule: Rule name or Rule document
		    context: Execution context (doc, vars, etc.)
		    dry_run: If True, wraps execution in a transaction that is rolled back.

		Returns:
		    Final execution context
		"""
		if isinstance(rule, str):
			rule = frappe.get_doc("Rule", rule)

		context = context or {}
		doc = context.get("doc")

		if not doc:
			frappe.throw(_("Document is required for rule execution"))

		# Convert to Document object if it's a dict/string (for API calls)
		if isinstance(doc, dict) and doc.get("doctype") and doc.get("name"):
			doc = frappe.get_doc(doc.get("doctype"), doc.get("name"))
			context["doc"] = doc
		elif isinstance(doc, str):
			# If doc is just name, try to use rule's document_type
			if rule.document_type:
				doc = frappe.get_doc(rule.document_type, doc)
				context["doc"] = doc
			else:
				frappe.throw(_("Cannot resolve document from name without document type"))

		from flexirule.ruleflow.core.engine import RuleEngine

		def _run():
			engine = RuleEngine(rule, execution_context=context)
			# Ensure engine knows about dry_run (it can use it for logging/behavior)
			engine.context["dry_run"] = dry_run
			# Persist logs for non-dry_run API calls to match hooks behavior
			if not dry_run:
				engine.context["save_log"] = True
			return engine.execute(doc, event_name=rule.trigger_event)

		if dry_run:
			savepoint_name = "flexirule_dry_run"
			try:
				frappe.db.savepoint(savepoint_name)
				result = _run()
				return result
			finally:
				frappe.db.rollback(save_point=savepoint_name)
		else:
			return _run()

	@staticmethod
	def get_rule_map() -> dict:
		"""
		Get unified rule map from cache or rebuild.
		Structure: {doctype: {event: [rule_names sorted by priority]}}
		"""

		def generator():
			# Redis cache lookup with graceful fallback to DB
			rule_map = None
			try:
				rule_map = frappe.cache.get_value(RuleCoordinator.CACHE_KEY)
			except Exception:
				# Cache unreachable - fall back to DB build (don't skip rules)
				frappe.log_error("FlexiRule: Cache unreachable, falling back to DB.")
				return RuleCoordinator._build_rule_map()

			if rule_map is None:
				try:
					rule_map = RuleCoordinator._build_rule_map()
					frappe.cache.set_value(RuleCoordinator.CACHE_KEY, rule_map)
				except Exception:
					frappe.log_error("FlexiRule: Cache write failed.")
					return rule_map or {}

			return rule_map or {}

		# Use the SAME local cache key as hooks.py for unified access
		# Note: hooks.py calls it via frappe.local_cache("flexirule_map", "unified", generator)
		# So we should match that or adapt RuleCoordinator to retrieve the "unified" key if it exists.
		if hasattr(frappe.local, "flexirule_map") and "unified" in frappe.local.flexirule_map:
			return frappe.local.flexirule_map["unified"] or {}

		return frappe.local_cache("flexirule_map", "unified", generator) or {}

	@staticmethod
	def _build_rule_map() -> dict:
		"""Build complete rule map from database"""
		rule_map: dict = {}

		# Fetch all active DocType Event rules with priority ordering
		active_rules = frappe.get_all(
			"Rule",
			filters={"is_active": 1, "trigger_type": "DocType Event"},
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
	def execute_rules_from_event(doc: Any, event_name: str):
		"""
		Find and execute rules triggered by a specific document event.
		Logic decoupled from Frappe hook flags.

		Args:
		    doc: Frappe document
		    event_name: Event name (Before Save, Validate, etc.)
		"""
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
		old_doc = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None

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
				RuleCoordinator.execute_single_rule(doc, rule_doc, old_doc=old_doc, event_name=event_name)
			except Exception as e:
				if rule_doc.debug_mode:
					frappe.log_error(
						title=_("Rule Execution Failed: {0}").format(rule_doc.name),
						message=_("DocType: {0} Doc: {1} Error: {2}").format(doc.doctype, doc.name, str(e)),
					)

				if event_name in RuleCoordinator.BLOCKING_EVENTS or isinstance(e, frappe.ValidationError):
					raise

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

		return RuleCoordinator.execute_rules_from_event(doc, event_name)

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
		# We now rely solely on compiled_expression which is the compiled version of trigger_condition
		if rule_doc.get("compiled_expression"):
			try:
				from flexirule.ruleflow.core.evaluator import check_link_match
				from flexirule.ruleflow.utils.field_resolver import FieldResolver

				# Fetch old_doc if missing
				if not old_doc and hasattr(doc, "get_doc_before_save"):
					old_doc = doc.get_doc_before_save()

				# Use SafeFrappeAPI to prevent write operations in trigger conditions
				from flexirule.ruleflow.core.engine import SafeFrappeAPI

				eval_globals = {
					"doc": doc,
					"old_doc": old_doc,
					"frappe": SafeFrappeAPI(),
					"resolve": FieldResolver.resolve,
					"check_link_match": check_link_match,
					"True": True,
					"False": False,
					"None": None,
				}

				if not frappe.safe_eval(rule_doc.get("compiled_expression"), None, eval_globals):
					return False, _("Trigger Conditions failed")

			except Exception as e:
				return False, _("Trigger Evaluation Error: {0}").format(str(e))

		# Conditions MUST be pre-compiled - no runtime JSON parsing
		elif rule_doc.get("trigger_condition"):
			return False, _("Rule has trigger_condition but no compiled_expression. Please re-save the Rule.")

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
	def execute_single_rule(doc, rule_doc, old_doc=None, event_name=None):
		"""
		Execute a single rule against a document

		Args:
		        doc: Frappe document
		        rule_doc: Rule document
		        old_doc: Document state before save (optional)
		        event_name: Trigger event name (optional)
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

		# Execute using new Engine
		# Pass old_doc in context
		execution_context = {"old_doc": old_doc}
		if frappe.flags.in_test:
			execution_context["test_mode"] = True
			execution_context["save_log"] = True

		engine = RuleEngine(rule_doc, execution_context=execution_context)
		engine.execute(doc, event_name=event_name)

	@staticmethod
	def run_rule_background(rule_name, doc_doctype, doc_name):
		"""
		Background job entry point
		"""
		try:
			rule_doc = frappe.get_doc("Rule", rule_name)
			doc = frappe.get_doc(doc_doctype, doc_name)

			from flexirule.ruleflow.core.engine import RuleEngine

			engine = RuleEngine(rule_doc)
			engine.execute(doc)

		except Exception as e:
			frappe.log_error(_("Async Rule Execution Failed: {0}").format(rule_name), str(e))

	@staticmethod
	def clear_cache(doctype: str | None = None):
		"""
		Clear cached rules. Always clears entire map (atomic rebuild).
		"""
		# Clear Redis cache
		frappe.cache.delete_value(RuleCoordinator.CACHE_KEY)

		# Clear request-level cache
		if hasattr(frappe.local, "flexirule_map"):
			delattr(frappe.local, "flexirule_map")

		# Clear frappe.local_cache
		if hasattr(frappe.local, "cache") and "flexirule_map" in frappe.local.cache:
			frappe.local.cache.pop("flexirule_map")

		# Notify distributed workers (v16 pattern)
		frappe.publish_realtime(  # nosemgrep: frappe-realtime-pick-room
			"flexirule_cache_clear",
			{"doctype": doctype},
			after_commit=True,
		)


def execute_rules(doc, event_name):
	"""
	Wrapper for RuleCoordinator.execute_rules to be used in hooks
	"""
	return RuleCoordinator.execute_rules(doc, event_name)
