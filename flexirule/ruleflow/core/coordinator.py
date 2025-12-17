# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
RuleCoordinator - Main entry point for rule execution
Finds applicable rules and dispatches them to appropriate executors
"""

import frappe
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
		from flexirule.ruleflow.core.evaluator import ConditionEvaluator
		
		valid_rules = []
		for rule_doc in rules:
			is_eligible, reason = RuleCoordinator.check_eligibility(rule_doc, doc, event_name)
			if is_eligible:
				valid_rules.append(rule_doc)
			else:
				# Optional: Log ineligibility if debug/trace mode is on for this rule
				if rule_doc.debug_mode:
					frappe.log_error(title=f"Rule Skipped: {rule_doc.name}", message=reason)
		
		# Execute eligible rules
		for rule_doc in valid_rules:
			try:
				RuleCoordinator.execute_single_rule(doc, rule_doc)
			except Exception as e:
				# Log error
				error_msg = str(e)
				if len(error_msg) > 139:
					error_msg = error_msg[:139]
				
				rule_doc.db_set('last_error', error_msg)
				
				if rule_doc.debug_mode:
					frappe.log_error(
						title=f"Rule Execution Failed: {rule_doc.name}",
						message=f"DocType: {doc.doctype} Doc: {doc.name}Error: {str(e)}"
					)
				
				# Re-raise blocking exceptions (Stop the save)
				if isinstance(e, frappe.ValidationError):
					raise e@staticmethod
	def check_eligibility(rule_doc, doc, event_name, execution_mode='Synchronous', skip_event_check=False) -> tuple[bool, str]:
		"""
		Strict V1 Contract Eligibility Check
		Returns: (is_eligible: bool, reason: str)
		"""
		# 1. Active Check
		if not rule_doc.is_active:
			return False, "Rule is not active"

		# 2. Event Check
		if not skip_event_check and rule_doc.trigger_event != event_name:
			# This might happen if cache returns mixed results or during manual triggers
			return False, f"Event mismatch: Rule expects {rule_doc.trigger_event}, got {event_name}"

		# 3. Mode Check (Strict)
		# For V1, we enforce that Sync rules run in Sync context.
		# Async is handled by the executor, but we should flag mismatch if needed.
		# Currently, we don't have explicit 'mode' passed from hooks, so we assume Sync.
		# If Rule is Async, it will be queued by execute_single_rule.
		
		# 4. JSON Condition (Fast Pre-filter)
		if rule_doc.trigger_condition:
			try:
				# Use ConditionEvaluator for JSON logic
				from flexirule.ruleflow.core.evaluator import ConditionEvaluator
				evaluator = ConditionEvaluator(rule_doc.trigger_condition)
				if not evaluator.evaluate(doc):
					return False, "Trigger Condition (JSON) mismatch"
			except Exception as e:
				return False, f"Invalid Trigger Condition JSON: {str(e)}"

		# 5. Python Filters (Expression / Advanced)
		if rule_doc.trigger_filters:
			try:
				# Safe Eval
		# Expose doc fields directly for convenience (e.g. 'status == "Open"')
				eval_globals = {'doc': doc, 'frappe': frappe}
				eval_globals.update(doc.as_dict())
				
				if not frappe.safe_eval(rule_doc.trigger_filters, None, eval_globals):					return False, "Trigger Filters (Python) evaluated to False"
			except Exception as e:
				return False, f"Trigger Filters Error: {str(e)}"

		return True, "Eligible"

		return True, "Eligible"
	
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
		
		# Filter by Trigger Condition if doc is provided
		if doc and rules:
			from flexirule.ruleflow.core.evaluator import ConditionEvaluator
			filtered_rules = []
			for rule in rules:
				# Stage 1: Eligibility (Fast Filter)
				if rule.trigger_condition:
					evaluator = ConditionEvaluator(rule.trigger_condition)
					if not evaluator.evaluate(doc):
						continue # Skip rule if trigger condition fails
				filtered_rules.append(rule)
			return filtered_rules
			
		return rules
	
	@staticmethod
	def execute_single_rule(doc, rule_doc):
		"""
		Execute a single rule against a document
		
		Args:
			doc: Frappe document
			rule_doc: Rule document
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
		engine = RuleEngine(rule_doc)
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
			frappe.log_error(f"Async Rule Execution Failed: {rule_name}", str(e))
	
	@staticmethod
	def clear_cache(doctype: str = None):
		"""
		Clear cached rules for a doctype or all doctypes
		
		Args:
			doctype: Optional DocType to clear cache for
		"""
		# Clear Redis Hash for active rules check
		if doctype:
			events = ['Before Insert', 'Before Save', 'Validate', 'After Insert', 
					  'After Save', 'Before Submit', 'On Submit', 'Before Cancel', 
					  'On Cancel', 'On Trash']
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
			
			# Clear local cache (Iterate keys because it's a dict)
			to_remove = [k for k in frappe.local.cache.keys() if k.startswith("flexirule_active:")]
			for k in to_remove:
				del frappe.local.cache[k]

def execute_rules(doc, event_name):
	"""
	Wrapper for RuleCoordinator.execute_rules to be used in hooks
	"""
	return RuleCoordinator.execute_rules(doc, event_name)
