# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
RuleCoordinator - Main entry point for rule execution
Finds applicable rules and dispatches them to appropriate executors
"""

import frappe
from frappe import _
from typing import List, Dict, Any
import json


class RuleCoordinator:
	"""Coordinates rule loading, filtering, and execution"""
	
	
	@staticmethod
	def has_active_rules(doctype: str, event_name: str) -> bool:
		"""
		Check if there are any active rules for this doctype/event.
		Uses frappe.local.cache for request-level caching.
		"""
		cache_key = f"flexirule_active:{doctype}:{event_name}"
		if cache_key in frappe.local.cache:
			return frappe.local.cache[cache_key]
			
		# Check Redis
		has_rules = frappe.cache().hget('flexirule_active_rules', f"{doctype}:{event_name}")
		
		# If None, it means cache miss/not initialized. 
		# If 0/False, it means strictly no rules.
		
		if has_rules is None:
			# Rebuild cache for this doctype? 
			# Or just query DB once. 
			# Let's query DB to be safe and simple for V1.
			count = frappe.db.count('Rule', {
				'document_type': doctype, 
				'trigger_event': event_name, 
				'is_active': 1
			})
			has_rules = (count > 0)
			# Update Redis to avoid future DB hits
			frappe.cache().hset('flexirule_active_rules', f"{doctype}:{event_name}", 1 if has_rules else 0)
			
		result = bool(has_rules)
		frappe.local.cache[cache_key] = result
		return result

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
		
			return
			
		# Strict Eligibility Check (V1 Contract)

		from flexirule.ruleflow.utils.field_resolver import FieldResolver
		
		# Fetch old_doc for change detection
		old_doc = doc.get_doc_before_save() if hasattr(doc, 'get_doc_before_save') else None
		
		valid_rules = []
		for rule_doc in rules:
			is_eligible, reason = RuleCoordinator.check_eligibility(rule_doc, doc, event_name, old_doc=old_doc)
			if is_eligible:
				valid_rules.append(rule_doc)
			else:
				# Optional: Log ineligibility if debug/trace mode is on for this rule
				if rule_doc.debug_mode:
					frappe.log_error(title=_("Rule Skipped: {0}").format(rule_doc.name), message=_(reason))
		
		# Execute eligible rules
		for rule_doc in valid_rules:
			try:
				RuleCoordinator.execute_single_rule(doc, rule_doc, old_doc=old_doc)
			except Exception as e:
				# Log error
				error_msg = str(e)
				if len(error_msg) > 139:
					error_msg = error_msg[:139]
				
				rule_doc.db_set('last_error', error_msg)
				
				if rule_doc.debug_mode:
					frappe.log_error(
						title=_("Rule Execution Failed: {0}").format(rule_doc.name),
						message=_("DocType: {0} Doc: {1} Error: {2}").format(doc.doctype, doc.name, str(e))
					)
				
				# Re-raise blocking exceptions (Stop the save)
				if isinstance(e, frappe.ValidationError):
					raise e
					
	@staticmethod
	def check_eligibility(rule_doc, doc, event_name, execution_mode='Synchronous', skip_event_check=False, old_doc=None) -> tuple[bool, str]:
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
			return False, _("Event mismatch: Rule expects {0}, got {1}").format(rule_doc.trigger_event, event_name)

		# 3. Mode Check (Strict)
		# For V1, we enforce that Sync rules run in Sync context.
		# Async is handled by the executor, but we should flag mismatch if needed.
		# Currently, we don't have explicit 'mode' passed from hooks, so we assume Sync.
		# If Rule is Async, it will be queued by execute_single_rule.
		
		# 4. Condition Check (Compiled Expression)
		# We now rely solely on trigger_condition_expression which is the compiled version of trigger_condition
		if rule_doc.get('trigger_condition_expression'):
			try:
				from flexirule.ruleflow.utils.field_resolver import FieldResolver
				from flexirule.ruleflow.core.evaluator import check_link_match
				
				# Fetch old_doc if missing
				if not old_doc and hasattr(doc, 'get_doc_before_save'):
					old_doc = doc.get_doc_before_save()

				eval_globals = {
					'doc': doc, 
					'old_doc': old_doc, 
					'frappe': frappe, 
					'resolve': FieldResolver.resolve,
					'check_link_match': check_link_match,
					'True': True,
					'False': False,
					'None': None
				}
				
				if not frappe.safe_eval(rule_doc.get('trigger_condition_expression'), None, eval_globals):
					return False, _("Trigger Conditions failed")
					
			except Exception as e:
				return False, _("Trigger Evaluation Error: {0}").format(str(e))
		
		# Conditions MUST be pre-compiled - no runtime JSON parsing
		elif rule_doc.get('trigger_condition'):
			return False, _("Rule has trigger_condition but no compiled trigger_condition_expression. Please re-save the Rule.")

		return True, _("Eligible")
	
	@staticmethod
	def get_applicable_rules(doctype: str, event_name: str, doc=None) -> List:
		"""
		Get active rules for a doctype and event
		Uses caching for performance
		
		Args:
			doctype: DocType name
			event_name: Trigger event name
			doc: Optional document for evaluating trigger conditions
			
		Returns:
			List of Rule documents
		"""
		cache_key = f"rules:{doctype}:{event_name}"
		
		# Try cache first
		cached = frappe.cache().get_value(cache_key)
		rules = []
		
		if cached:
			try:
				rule_names = json.loads(cached)
				for name in rule_names:
					# Handle stale cache where rule might have been deleted
					try:
						rules.append(frappe.get_cached_doc("Rule", name))
					except (frappe.DoesNotExistError, frappe.ValidationError):
						# Force refresh if any doc is missing
						frappe.cache().delete_value(cache_key)
						return RuleCoordinator.get_applicable_rules(doctype, event_name, doc)
			except Exception:
				# If any json or other error, ignore cache
				pass
		else:
			# Load from database
			rule_list = frappe.get_all(
				"Rule",
				filters={
					"is_active": 1,
					"document_type": doctype,
					"trigger_event": event_name
				},
				fields=["name"],
				order_by="priority DESC"
			)
			
			rule_names = [r.name for r in rule_list]
			
			# Cache for 5 minutes
			frappe.cache().set_value(cache_key, json.dumps(rule_names), expires_in_sec=300)
			
			rules = [frappe.get_cached_doc("Rule", name) for name in rule_names]
		
		# Note: Trigger condition filtering is now handled by check_eligibility 
		# using compiled trigger_condition_expression - no runtime JSON parsing
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
		if rule_doc.execution_mode == 'Asynchronous':
			# Async only works for saved documents
			if not doc.get('__islocal'):
				frappe.enqueue(
					'flexirule.ruleflow.core.coordinator.RuleCoordinator.run_rule_background',
					rule_name=rule_doc.name,
					doc_doctype=doc.doctype,
					doc_name=doc.name,
					queue='default',
					timeout=rule_doc.max_execution_time or 300
				)
				return
		
		from flexirule.ruleflow.core.engine import RuleEngine
		
		# Increment execution count (Cached in Redis, not DB write)
		frappe.cache().hincrby(f"rule_stats:{rule_doc.name}", "count", 1)
		frappe.cache().hset(f"rule_stats:{rule_doc.name}", "last_executed", frappe.utils.now())
		
		# Execute using new Engine
		# Pass old_doc in context
		execution_context = {'old_doc': old_doc}
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
			frappe.cache().hset(f"rule_stats:{rule_doc.name}", "last_executed", frappe.utils.now())
			
			engine = RuleEngine(rule_doc)
			engine.execute(doc)
			
		except Exception as e:
			frappe.log_error(_("Async Rule Execution Failed: {0}").format(rule_name), str(e))
	
	@staticmethod
	def clear_cache(doctype: str = None):
		"""
		Clear cached rules for a doctype or all doctypes
		
		Args:
			doctype: Optional DocType to clear cache for
		"""
		# Clear Redis Hash for active rules check
		if doctype:
			# Get all possible events from Rule metadata
			meta = frappe.get_meta('Rule')
			events = meta.get_field('trigger_event').options.split('\n')
			
			for event in events:
				# Clear Hash Field
				frappe.cache().hdel('flexirule_active_rules', f"{doctype}:{event}")
				
				# Clear Old Keys (Legacy support if any)
				frappe.cache().delete_value(f"rules:{doctype}:{event}")
				
				# Clear Local Cache
				key = f"flexirule_active:{doctype}:{event}"
				if key in frappe.local.cache:
					del frappe.local.cache[key]
		else:
			# Clear all
			frappe.cache().delete_key('flexirule_active_rules')
			frappe.cache().delete_keys("rules:*")
			
			# Clear local cache 
			to_remove = []
			for k in frappe.local.cache.keys():
				if isinstance(k, str) and k.startswith("flexirule_active:"):
					to_remove.append(k)
				elif isinstance(k, bytes) and k.startswith(b"flexirule_active:"):
					to_remove.append(k)
					
			for k in to_remove:
				del frappe.local.cache[k]

def execute_rules(doc, event_name):
	"""
	Wrapper for RuleCoordinator.execute_rules to be used in hooks
	"""
	return RuleCoordinator.execute_rules(doc, event_name)
