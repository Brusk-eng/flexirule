"""
Hook wrapper functions for Bolton rule engine
These are called from hooks.py doc_events
Module-level functions only - no class methods in hook paths!
"""

import frappe


def get_excluded_doctypes():
	"""Get list of doctypes to exclude from rule execution (cached per request)."""

	def _build_exclusion_list():
		excluded = frappe.get_hooks("flexirule_excluded_doctypes") or []

		default_excluded = [
			"Error Log",
			"Activity Log",
			"Access Log",
			"Email Queue",
			"Scheduled Job Log",
			"Version",
			"Comment",
			"Communication",
			"File",
			# FlexiRule internal doctypes
			"Rule",
			"Rule Action",
			"Rule Execution Log",
			"Rule Scheduler",
			"Process",
			"Process Operation",
			"Data Review Task",
			"Data Review Related Document",
		]

		try:
			user_excluded = frappe.get_all(
				"RuleFlow Excluded DocType", parent="RuleFlow Settings", pluck="document_type"
			)
			if user_excluded:
				default_excluded.extend(user_excluded)
		except Exception:
			# Table might not exist yet if migrating
			pass

		return list(set(excluded + default_excluded))

	return frappe.local_cache("flexirule_excluded_doctypes", "list", _build_exclusion_list)


def execute_rules(doc, method=None, *args, **kwargs):
	"""
	Standard Frappe doc_event hook entry point.
	Maps Frappe methods to FlexiRule events.
	"""
	event_map = {
		"before_naming": "Before Naming",
		"before_insert": "Before Insert",
		"before_save": "Before Save",
		"validate": "Validate",
		"after_insert": "After Insert",
		"on_update": "After Save",
		"before_submit": "Before Submit",
		"on_submit": "On Submit",
		"on_update_after_submit": "On Update After Submit",
		"on_change": "On Change",
		"before_cancel": "Before Cancel",
		"on_cancel": "On Cancel",
		"on_trash": "On Trash",
		"before_print": "Before Print",
		"before_rename": "Before Rename",
		"after_rename": "After Rename",
	}

	trigger_event = event_map.get(method)
	if not trigger_event:
		return

	return execute_rules_from_event(doc, trigger_event)


def execute_rules_from_event(doc, event):
	"""
	Pure hook logic decoupled from Frappe method names.
	"""
	if frappe.flags.in_import or frappe.flags.in_migrate:
		return

	if doc.doctype in get_excluded_doctypes():
		return

	# Early exit check: Only import coordinator if rules exist for this doctype/event
	rule_map = get_flexirule_map()
	if not rule_map.get(doc.doctype, {}).get(event):
		return

	from flexirule.ruleflow.core.coordinator import RuleCoordinator

	RuleCoordinator.execute_rules_from_event(doc, event)


def get_flexirule_map():
	"""
	Helper function to get the unified rule map with local caching.
	Uses generator pattern to minimize database lookups.
	"""

	def generator():
		# Fallback to coordinator if needed, but try to resolve from cache first
		from flexirule.ruleflow.core.coordinator import RuleCoordinator

		return RuleCoordinator.get_rule_map()

	return frappe.local_cache("flexirule_map", "unified", generator)


def clear_rule_cache(doc=None, method=None, *args, **kwargs):
	"""
	Clear rule cache when Rule document is modified.
	This is a MODULE-LEVEL function callable from hooks.py
	"""
	from flexirule.ruleflow.core.coordinator import RuleCoordinator

	RuleCoordinator.clear_cache()
