# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
ConditionEvaluator - Evaluates JSON-based rule conditions
Supports nested AND/OR logic, field comparisons, and various operators
"""

import frappe
import json
import operator
import re
from typing import Any, Dict
from frappe.utils import getdate, cint, flt


class ConditionEvaluator:
	"""Evaluates rule conditions against a document"""
	
	# Operator mapping
	OPERATORS = {
		'==': operator.eq,
		'!=': operator.ne,
		'>': operator.gt,
		'<': operator.lt,
		'>=': operator.ge,
		'<=': operator.le,
		'in': lambda a, b: a in b if b else False,
		'not_in': lambda a, b: a not in b if b else True,
		'contains': lambda a, b: b in str(a) if a else False,
		'not_contains': lambda a, b: b not in str(a) if a else True,
		'is_set': lambda a, b: a is not None and a != '',
		'is_not_set': lambda a, b: a is None or a == '',
		'regex': lambda a, b: bool(re.search(b, str(a))) if a and b else False,
	}
	
	def __init__(self, conditions_json: str):
		"""
		Initialize evaluator with conditions JSON
		
		Args:
			conditions_json: JSON string containing conditions array
		"""
		self.conditions = json.loads(conditions_json) if conditions_json else []
	
	def evaluate(self, doc) -> bool:
		"""
		Evaluate all conditions against a document
		
		Args:
			doc: Frappe document
			
		Returns:
			bool: True if all conditions pass
		"""
		if not self.conditions:
			return True
		
		return self._evaluate_group(self.conditions, doc)
	
	def _evaluate_group(self, conditions: list, doc) -> bool:
		"""
		Evaluate a group of conditions with AND/OR logic
		
		Args:
			conditions: List of condition dictionaries
			doc: Frappe document
			
		Returns:
			bool: Result of group evaluation
		"""
		if not conditions:
			return True
		
		# Default to AND logic
		result = True
		current_operator = 'AND'
		
		for condition in conditions:
			# Check if this is a nested group
			if 'conditions' in condition:
				# Recursive evaluation for nested groups
				group_result = self._evaluate_group(condition['conditions'], doc)
			else:
				# Evaluate single condition
				group_result = self._evaluate_single(condition, doc)
			
			# Apply logical operator
			if current_operator == 'AND':
				result = result and group_result
			else:  # OR
				result = result or group_result
			
			# Get next operator (default AND)
			current_operator = condition.get('logical_operator', 'AND')
		
		return result
	
	def _evaluate_single(self, condition: Dict, doc) -> bool:
		"""
		Evaluate a single condition
		
		Args:
			condition: Condition dictionary with left, operator, right
			doc: Frappe document
			
		Returns:
			bool: Result of condition evaluation
		"""
		try:
			# Get left value
			left = self._resolve_value(condition.get('left'), doc)
			
			# Get operator
			op = condition.get('operator', '==')
			
			# Special case for operators that don't need right value
			if op in ['is_set', 'is_not_set']:
				return self.OPERATORS[op](left, None)
			
			# Get right value
			right = self._resolve_value(condition.get('right'), doc)
			
			# Get operator function
			op_func = self.OPERATORS.get(op)
			if not op_func:
				frappe.log_error(f"Unknown operator: {op}", "ConditionEvaluator")
				return False
			
			# Evaluate
			return op_func(left, right)
			
		except Exception as e:
			frappe.log_error(
				title="Condition Evaluation Error",
				message=f"Condition: {json.dumps(condition)}\\nError: {str(e)}"
			)
			return False
	
	def _resolve_value(self, value_def: Any, doc) -> Any:
		"""
		Resolve a value from its definition
		
		Value can be:
		- {"type": "field", "value": "fieldname"}
		- {"type": "literal", "value": "some value"}
		- {"type": "method", "value": "method.path", "args": {...}}
		- Simple scalar value (treated as literal)
		
		Args:
			value_def: Value definition
			doc: Frappe document
			
		Returns:
			Resolved value
		"""
		if value_def is None:
			return None
		
		# If it's a simple scalar, return as-is
		if not isinstance(value_def, dict):
			return value_def
		
		value_type = value_def.get('type', 'literal')
		value = value_def.get('value')
		
		if value_type == 'field':
			# Resolve field value from document
			return self._get_field_value(doc, value)
		
		elif value_type == 'literal':
			# Return literal value
			return value
		
		elif value_type == 'method':
			# Call method and return result
			args = value_def.get('args', {})
			return frappe.call(value, **args)
		
		else:
			return value
	
	def _get_field_value(self, doc, fieldname: str) -> Any:
		"""
		Get field value from document, supports dot notation and aggregates
		
		Args:
			doc: Frappe document
			fieldname: Field name (supports dot notation and aggregates)
			
		Returns:
			Field value
		"""
		if not fieldname:
			return None
		
		# Use FieldResolver for advanced resolution
		from flexirule.ruleflow.utils.field_resolver import FieldResolver
		return FieldResolver.resolve(doc, fieldname)
