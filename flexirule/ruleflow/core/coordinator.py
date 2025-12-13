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
		Check if a doctype has any active rules for an event
		"""
		cache_key = f"has_rules:{doctype}:{event_name}"
		cached = frappe.cache().get_value(cache_key)
		
		if cached is not None:
			return cached
			
		# Check DB
		exists = frappe.db.exists("Rule", {
			"is_active": 1,
			"document_type": doctype,
			"trigger_event": event_name
		})
		
		# Cache for 1 hour (cleared on Rule save)
		frappe.cache().set_value(cache_key, 1 if exists else 0, expires_in_sec=3600)
		return bool(exists)

	@staticmethod
	def execute_rules(doc, event_name: str):
		"""
		Main entry point called from doc_events hooks
		
		Args:
			doc: Frappe document
			event_name: Event that triggered execution (before_save, validate, etc.)
		"""
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
		
		# Execute each rule
		for rule_doc in rules:
			try:
				RuleCoordinator.execute_single_rule(doc, rule_doc)
			except Exception as e:
				# Log error but don't break on single rule failure
				rule_doc.db_set('last_error', str(e))
				if rule_doc.debug_mode:
					frappe.log_error(
						title=f"Rule Execution Failed: {rule_doc.rule_name}",
						message=f"DocType: {doc.doctype}\\nDoc: {doc.name}\\nError: {str(e)}"
					)
	
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
		if doctype:
			# Clear specific doctype
			events = ['before_insert', 'before_save', 'validate', 'after_insert', 
					  'after_save', 'before_submit', 'on_submit', 'before_cancel', 
					  'on_cancel', 'on_trash']
			for event in events:
				cache_key = f"rules:{doctype}:{event}"
				frappe.cache().delete_value(cache_key)
			
			events_keys = [f"has_rules:{doctype}:{e}" for e in events]
			for k in events_keys:
				frappe.cache().delete_value(k)
		else:
			# Clear all rule caches
			frappe.cache().delete_keys("rules:*")
			frappe.cache().delete_keys("has_rules:*")

def execute_rules(doc, event_name):
	"""
	Wrapper for RuleCoordinator.execute_rules to be used in hooks
	"""
	return RuleCoordinator.execute_rules(doc, event_name)
