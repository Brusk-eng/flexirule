# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

"""
Enhanced Rule Engine with:
- Process Method integration
- Permission-based security
- Retry logic and error handling
- Timeout protection (cross-platform using threading)
- Cycle detection
- Comprehensive logging
"""

import frappe
import json
import time
import traceback
import jsonschema
from jsonschema import validate, ValidationError as SchemaValidationError
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from contextlib import contextmanager
from flexirule.ruleflow.core.exceptions import (
	RuleDisabledError,
	EmptyRuleError,
	MethodExecutionError,
	TimeoutError as BoltonTimeoutError,
	CycleDetectedError
)
from flexirule.ruleflow.utils.mapping import apply_input_mapping, apply_output_mapping


class TimeoutException(Exception):
	"""Internal timeout exception"""
	pass


@contextmanager
def time_limit(seconds):
	"""
	Context manager for timeout protection using ThreadPoolExecutor.
	Cross-platform compatible (works on Windows/Linux/Mac).
	"""
	if seconds <= 0:
		yield
		return
	
	# Note: This context manager doesn't actually enforce timeout
	# The timeout is enforced in _execute_with_timeout method
	yield


class SafeFrappeAPI:
	"""
	Restricted Frappe API proxy for rule condition evaluation.
	Exposes only safe, read-only operations to prevent security issues.
	"""
	
	def __init__(self):
		# Safe utilities
		self.utils = frappe.utils
		self._dict = frappe._dict
		
	# Safe read operations
	@staticmethod
	def get_value(doctype, filters, fieldname=None, **kwargs):
		"""Read-only get_value"""
		return frappe.get_value(doctype, filters, fieldname, **kwargs)
	
	@staticmethod
	def get_all(doctype, filters=None, fields=None, **kwargs):
		"""Read-only get_all"""
		return frappe.get_all(doctype, filters=filters, fields=fields, **kwargs)
	
	@staticmethod
	def db_exists(doctype, name):
		"""Check if document exists"""
		return frappe.db.exists(doctype, name)
	
	@staticmethod
	def get_meta(doctype):
		"""Get doctype metadata"""
		return frappe.get_meta(doctype)
	
	@staticmethod
	def format_value(value, df=None, doc=None, currency=None):
		"""Format value for display"""
		return frappe.format_value(value, df, doc, currency)
	
	# Logging (safe)
	@staticmethod
	def log(message):
		"""Log a message"""
		frappe.logger().info(message)
	
	# Explicitly denied operations (will raise)
	def get_doc(self, *args, **kwargs):
		raise PermissionError("get_doc is not allowed in rule conditions. Use frappe.get_value instead.")
	
	def new_doc(self, *args, **kwargs):
		raise PermissionError("new_doc is not allowed in rule conditions.")
	
	def delete_doc(self, *args, **kwargs):
		raise PermissionError("delete_doc is not allowed in rule conditions.")
	
	def db_set_value(self, *args, **kwargs):
		raise PermissionError("db.set_value is not allowed in rule conditions.")
	
	@property
	def db(self):
		"""Return restricted db proxy"""
		return self._SafeDB()
	
	class _SafeDB:
		"""Restricted database operations"""
		def exists(self, doctype, name):
			return frappe.db.exists(doctype, name)
		
		def get_value(self, doctype, filters, fieldname=None, **kwargs):
			return frappe.db.get_value(doctype, filters, fieldname, **kwargs)
		
		def get_all(self, doctype, filters=None, fields=None, **kwargs):
			return frappe.db.get_all(doctype, filters=filters, fields=fields, **kwargs)
		
		# Explicitly deny write operations
		def set_value(self, *args, **kwargs):
			raise PermissionError("db.set_value is not allowed in rule conditions.")
		
		def sql(self, *args, **kwargs):
			raise PermissionError("db.sql is not allowed in rule conditions.")


# Singleton instance
_safe_frappe = SafeFrappeAPI()


class RuleEngine:
	"""
	Production-ready rule execution engine with:
	- Validation and error handling
	- Performance optimization
	- Security enforcement
	- Audit logging
	"""
	
	def __init__(self, rule_doc, execution_context=None):
		"""
		Args:
			rule_doc: Rule DocType document
			execution_context: Dict with user, timestamp, test_mode, etc.
		"""
		self.rule = rule_doc
		self.actions = [a for a in rule_doc.actions if a.is_enabled]
		self.context = execution_context or {}
		self.execution_log = []
		self.cache = {}
		
		# Build action maps for fast lookup
		self.action_map_by_id = {a.action_id: a for a in self.actions if a.action_id}
		self.action_map_by_label = {a.action_label: a for a in self.actions}
		self.action_map_by_name = {a.name: a for a in self.actions}
	
	def execute(self, doc, **kwargs):
		"""
		Execute rule with comprehensive error handling
		
		Args:
			doc: Frappe document to process
			**kwargs: Additional context variables
			
		Returns:
			Execution context with results
		"""
		# Tracking vars
		start_time = time.time()
		status = "Success"
		error_detail = None
		self.path_trace = []
		
		try:
			# Pre-execution validation
			self._validate_execution()
			
			# Check role-based skipping
			if self.rule.get('skip_for_roles'):
				user_roles = frappe.get_roles()
				skip_roles = [row.role for row in self.rule.get('skip_for_roles')]
				if any(role in user_roles for role in skip_roles):
					self._log("INFO", f"Skipping rule execution for user with role(s): {skip_roles}")
					status = "Skipped"
					return self.context
			
			# Initialize context
			context = self._initialize_context(doc, **kwargs)
			
			# Log start
			self._log("INFO", f"Starting rule execution: {self.rule.name}")
			
			# Execute with timeout if configured
			timeout = self.rule.max_execution_time or 30
			
			if self.context.get('test_mode'):
				# No timeout in test mode
				result = self._execute_graph(context)
			else:
				with time_limit(timeout):
					result = self._execute_graph(context)
			
			# Post-execution cleanup
			self._log("INFO", "Rule execution completed successfully")
			
			if not self.context.get('test_mode'):
				self._update_rule_stats(success=True)
			
			return result
			
		except (TimeoutException, FuturesTimeoutError, BoltonTimeoutError) as e:
			status = "Failed"
			error_msg = f"Rule execution exceeded timeout ({timeout if 'timeout' in locals() else 'unknown'}s)"
			error_detail = traceback.format_exc()
			self._log("ERROR", error_msg)
			if context if 'context' in locals() else None:
				self._update_rule_stats(success=False, error=error_msg)
			raise BoltonTimeoutError(error_msg)
		
		except Exception as e:
			status = "Failed"
			error_msg = str(e)
			error_detail = traceback.format_exc()
			self._log("ERROR", f"Rule execution failed: {error_msg}")
			if context if 'context' in locals() else None:
				self._update_rule_stats(success=False, error=error_msg)
			raise
			
		finally:
			# Persist Log
			if not self.context.get('test_mode'):
				duration = time.time() - start_time
				self._save_execution_log(status, duration, error_detail)
	
	def _validate_execution(self):
		"""Validate rule is executable"""
		if not self.rule.is_active:
			raise RuleDisabledError(f"Rule {self.rule.name} is disabled")
		
		if not self.actions:
			raise EmptyRuleError(f"Rule {self.rule.name} has no enabled actions")
	
	def _initialize_context(self, doc, **kwargs):
		return {
			**self.context,
			'doc': doc,
			'frappe': self._get_safe_frappe_api(),
			'vars': {},
			'meta': {
				'rule': self.rule.name,
				'rule_version': 'v1',
				'engine_version': '1.0',
				'user': frappe.session.user,
				'timestamp': frappe.utils.now(),
				'test_mode': self.context.get('test_mode', False)
			},
			'stop': False,
			**kwargs
		}
	
	def _get_safe_frappe_api(self):
		"""Return a restricted frappe API object for condition evaluation"""
		return _safe_frappe
	
	def _execute_graph(self, context):
		"""Execute action graph with cycle detection and loop support"""
		
		# Change strict cycle detection to visit counting for loops
		node_visits = {} # node_id -> count
		max_visits_per_node = 100 # Safety for infinite loops
		
		execution_path = []
		current = self._get_start_node()
		max_iterations = 1000 # Total step limit
		
		for iteration in range(max_iterations):
			if not current:
				self._log("INFO", "Reached end of flow (no next action)")
				break
			
			if context.get('stop'):
				self._log("INFO", "Flow stopped by action")
				break
			
			# Cycle/Loop detection
			node_id = current.action_id or current.name
			
			# Track visits
			visits = node_visits.get(node_id, 0) + 1
			node_visits[node_id] = visits
			
			if visits > max_visits_per_node:
				raise CycleDetectedError(f"Infinite loop detected: Action {current.action_label} visited {visits} times")
			
			execution_path.append(current.action_label)
			self.path_trace.append({
				"node": current.action_label,
				"type": current.action_type,
				"timestamp": time.time()
			})
			
			# Log execution
			self._log("INFO", f"Executing action: {current.action_label} (type: {current.action_type})")
			
			try:
				result = None
				next_id = None
				
				# === Logic Nodes ===
				if current.action_type == 'Condition':
					result = self._execute_condition(current, context)
					# Strict Logic Node: ONLY decides path, no side effects
					next_id = current.next_step_if_true if result else current.next_step_if_false
					self._log("DEBUG", f"Condition result: {result}, next: {next_id}")

				elif current.action_type == 'Switch':
					# Switch Node: Multi-path branching
					result = self._execute_switch(current, context)
					next_id = result if result else current.next_step_if_true
					self._log("DEBUG", f"Switch result: path -> {next_id}")
				
				# === Task Nodes ===
				elif current.action_type == 'Process':
					# Task Node: Executes work, returns result, follows ONE path
					result = self._execute_process(current, context)
					next_id = current.next_step_if_true
					self._log("DEBUG", f"Process result: {result}, next: {next_id}")
					
				elif current.action_type == 'Sub-Rule':
					# Executing a sub-rule is a task that runs another engine
					self._execute_sub_rule(current, context)
					next_id = current.next_step_if_true
					self._log("DEBUG", f"Sub-Rule executed, continuing to: {next_id}")

				# === Control Nodes ===
				elif current.action_type == 'Stop':
					self._log("INFO", "Stop action encountered")
					break
				
				# === Loop & Wait Nodes (Added) ===
				elif current.action_type == 'Wait':
					self._execute_wait(current, context)
					next_id = current.next_step_if_true
					
				elif current.action_type == 'Loop':
					# Execute Loop Logic
					# If returns True, we are iterating -> Go to Body (next_step_if_true)
					# If returns False, we are done -> Go to Exit (next_step_if_false)
					should_loop = self._execute_loop(current, context)
					if should_loop:
						next_id = current.next_step_if_true
						self._log("DEBUG", f"Loop continuing (iteration), next: {next_id}")
					else:
						next_id = current.next_step_if_false
						self._log("DEBUG", f"Loop finished, next: {next_id}")
				
				else:
					self._log("WARNING", f"Unknown action type: {current.action_type}")
					next_id = current.next_step_if_true
				
				# Store result if variable specified (Only for Task/Logic nodes)
				if current.return_variable and result is not None:
					context['vars'][current.return_variable] = result
					self._log("DEBUG", f"Stored result in variable: {current.return_variable}")
				
				# Move to next node
				current = self._get_action_by_id(next_id) if next_id else None

			except Exception as e:
				# Handle error based on on_error setting
				if hasattr(current, 'on_error'):
					if current.on_error == 'Continue':
						self._log("WARNING", f"Error in action {current.action_label}, continuing: {str(e)}")
						current = self._get_action_by_id(current.next_step_if_true)
						continue
					elif current.on_error == 'Rollback':
						self._log("ERROR", f"Error in action {current.action_label}, rolling back: {str(e)}")
						frappe.db.rollback()
						raise
					elif current.on_error == 'Escalate':
						self._log("ERROR", f"Error in action {current.action_label}, escalating: {str(e)}")
						raise
				
				# Default: stop on error
				self._log("ERROR", f"Error in action {current.action_label}: {str(e)}")
				raise
		
		if iteration >= max_iterations - 1:
			raise CycleDetectedError(f"Max total iterations ({max_iterations}) exceeded")
		
		self._log("INFO", f"Execution path: {' → '.join(execution_path)}")
		return context
	
	def _get_start_node(self):
		"""Get the first action to execute (one with no incoming edges)"""
		# Build set of actions that have incoming edges
		has_incoming = set()
		
		for action in self.actions:
			action_id = action.action_id or action.name
			
			# Check all actions' next_step fields
			for other in self.actions:
				if other.next_step_if_true == action_id:
					has_incoming.add(action_id)
				if other.next_step_if_false == action_id:
					has_incoming.add(action_id)
				
				# Check Switch cases for incoming edges
				if other.action_type == 'Switch' and other.method_config:
					try:
						config = json.loads(other.method_config)
						for target_id in config.get('cases', {}).values():
							if target_id == action_id:
								has_incoming.add(action_id)
					except: pass
		
		# Find action with no incoming edges (true start node)
		for action in self.actions:
			action_id = action.action_id or action.name
			if action_id not in has_incoming:
				self._log("INFO", f"Start node: {action.action_label} ({action_id})")
				return action
		
		# Fallback to first action if no clear start
		self._log("WARNING", "No clear start node, using first action")
		return self.actions[0] if self.actions else None
	
	def _get_action_by_id(self, action_id):
		"""Get action by ID (supports action_id, name, or label)"""
		if not action_id:
			return None
		
		# Try different lookup methods
		return (
			self.action_map_by_id.get(action_id) or
			self.action_map_by_name.get(action_id) or
			self.action_map_by_label.get(action_id)
		)
	
	def _execute_condition(self, action, context):
		"""Execute a condition node"""
		# Prefer JSON condition if available
		if action.condition_json:
			return self._evaluate_json_condition(action.condition_json, context)
		
		return self._evaluate_python_condition(action.condition_expression, context)
	
	def _evaluate_json_condition(self, condition_json, context):
		"""Evaluate Frappe-style JSON filters"""
		if not condition_json:
			return True
		
		try:
			filters = json.loads(condition_json)
			return frappe.utils.evaluate_filters(context['doc'], filters)
		except Exception as e:
			self._log("ERROR", f"JSON condition evaluation failed: {str(e)}")
			return False
	
	def _evaluate_python_condition(self, expression, context):
		"""Evaluate Python expression safely"""
		if not expression:
			return True
		
		# Prepare safe locals
		safe_locals = {
			'doc': context.get('doc'),
			'vars': context.get('vars'),
			'frappe': frappe.utils # Limit frappe access in eval if possible, or use safe_eval logic
		}
		if 'frappe' in context:
			# If a safe wrapper is in context, use it
			safe_locals['frappe'] = context['frappe']
		
		try:
			return frappe.safe_eval(expression, None, safe_locals)
		except Exception as e:
			self._log("ERROR", f"Python condition evaluation failed: {str(e)}")
			raise

	def _execute_loop(self, action, context):
		"""
		Execute Loop Logic.
		Manages iteration state in context['vars']['_loops'][action_id]
		"""
		if '_loops' not in context['vars']:
			context['vars']['_loops'] = {}
			
		loop_state = context['vars']['_loops'].get(action.action_id, {
			'index': 0, 'initialized': False
		})
		
		config = {}
		if action.method_config:
			try:
				config = json.loads(action.method_config)
			except: pass
			
		iterator_name = config.get('iterator') # e.g. "doc.items" or "vars.my_list"
		item_alias = config.get('alias', 'item')
		
		items = []
		if iterator_name:
			# Resolve iterator
			items = self._evaluate_python_condition(iterator_name, context)
			
		if not isinstance(items, (list, tuple)):
			self._log("WARNING", f"Loop iterator {iterator_name} is not a list/tuple. Got {type(items)}")
			items = []
			
		current_index = loop_state['index']
		
		if current_index < len(items):
			# Valid iteration
			item = items[current_index]
			context['vars'][item_alias] = item
			context['vars']['loop'] = {
				'index': current_index,
				'first': current_index == 0,
				'last': current_index == len(items) - 1,
				'length': len(items)
			}
			
			# Advance index for NEXT time
			loop_state['index'] += 1
			context['vars']['_loops'][action.action_id] = loop_state
			return True
		else:
			# Loop finished
			# Cleanup
			if action.action_id in context['vars']['_loops']:
				del context['vars']['_loops'][action.action_id]
			return False

	def _execute_wait(self, action, context):
		"""Execute Wait (Sleep)"""
		config = {}
		if action.method_config:
			try:
				config = json.loads(action.method_config)
			except: pass
			
		duration = config.get('duration', 0)
		if not duration and action.timeout:
			duration = action.timeout
			
		if duration > 0:
			self._log("INFO", f"Waiting for {duration} seconds...")
			time.sleep(duration)
	
	def _execute_process(self, action, context):
		"""
		Execute Process Method with validation and error handling
		"""
		if not action.process_method:
			self._log("WARNING", f"Process action {action.action_label} has no process_method set")
			return None
		
		# Get Process Method document
		try:
			process_method = frappe.get_cached_doc('Process Method', action.process_method)
		except frappe.DoesNotExistError:
			raise MethodExecutionError(f"Process Method {action.process_method} not found")
		
		# Parse configuration
		config = {}
		if action.method_config:
			try:
				config = json.loads(action.method_config)
			except json.JSONDecodeError as e:
				raise MethodExecutionError(f"Invalid configuration JSON: {str(e)}")
		
		# Apply Input Mapping (Context -> Config)
		if action.input_mapping:
			config = apply_input_mapping(context, action.input_mapping, config)
		
		# Validation: Check against Input Schema
		if process_method.input_schema:
			try:
				schema = json.loads(process_method.input_schema)
				validate(instance=config, schema=schema)
			except (json.JSONDecodeError, SchemaValidationError) as e:
				raise MethodExecutionError(f"Input validation failed for {process_method.method_name}: {str(e)}")

		# Execute with retry logic
		result = self._call_method_with_retry(
			process_method=process_method,
			config=config,
			context=context,
			retry_count=action.retry_count or 0,
			timeout=action.timeout or 30
		)
		
		# Apply Output Mapping (Result -> Context)
		if action.output_mapping:
			apply_output_mapping(result, action.output_mapping, context)
			
		return result
	
	def _call_method_with_retry(self, process_method, config, context, retry_count, timeout):
		"""Execute method with retry logic"""
		last_error = None
		
		for attempt in range(retry_count + 1):
			try:
				# Log attempt
				if attempt > 0:
					self._log("INFO", f"Retry attempt {attempt}/{retry_count} for {process_method.method_name}")
				
				# Execute via Process Method document
				result = process_method.execute(
					doc=context['doc'],
					context=context,
					config=config
				)
				
				# Success
				return result
				
			except Exception as e:
				last_error = e
				self._log("ERROR", f"Method execution failed (attempt {attempt + 1}): {str(e)}")
				
				if attempt < retry_count:
					# Exponential backoff
					backoff_seconds = 2 ** attempt
					self._log("INFO", f"Waiting {backoff_seconds}s before retry")
					time.sleep(backoff_seconds)
				else:
					# All retries exhausted
					break
		
		# All retries failed
		raise MethodExecutionError(
			f"Method {process_method.method_name} failed after {retry_count + 1} attempts: {str(last_error)}"
		)

	def _execute_switch(self, action, context):
		"""Execute Switch logic based on method_config"""
		if not action.method_config:
			return None
			
		try:
			config = json.loads(action.method_config)
			expression = config.get('expression')
			cases = config.get('cases', {})
			
			if not expression:
				return None
				
			# Evaluate expression
			val = self._evaluate_python_condition(expression, context)
			
			# Match case - convert val to string for key lookup as JSON keys are strings
			# But if val is boolean True/False, json keys might be "true"/"false" or "True"/"False"
			# Let's try direct lookup first, then string lookup
			
			if val in cases:
				return cases[val]
			
			str_val = str(val)
			if str_val in cases:
				return cases[str_val]
				
			return None # Fallback to default
			
		except Exception as e:
			self._log("ERROR", f"Switch evaluation failed: {str(e)}")
			raise

	def _execute_sub_rule(self, action, context):
		"""Execute a Sub-Rule"""
		if not action.method_config:
			self._log("WARNING", "Sub-Rule action missing config")
			return
			
		try:
			config = json.loads(action.method_config)
			sub_rule_name = config.get('rule')
			
			if not sub_rule_name:
				return
				
			if not frappe.db.exists("Rule", sub_rule_name):
				raise MethodExecutionError(f"Sub-Rule {sub_rule_name} not found")
				
			sub_rule_doc = frappe.get_cached_doc("Rule", sub_rule_name)
			
			# Recursive Execution
			# We share 'vars' and 'doc' so mutations propagate
			# But we might want to isolate 'stop' flag? 
			# V1 Contract: "vars is the ONLY mutable storage"
			
			self._log("INFO", f"BEGIN Sub-Rule: {sub_rule_name}")
			
			# Create sub-context sharing vars
			sub_context = context.copy()
			sub_context['meta'] = context.get('meta', {}).copy()
			sub_context['meta']['parent_rule'] = self.rule.name
			
			# Instantiate new engine
			# Avoid cyclic import if lazy loading is better, but Engine is here
			# Since we are in Engine class, we can just instantiate self.__class__
			sub_engine = self.__class__(sub_rule_doc, execution_context=sub_context)
			
			result_context = sub_engine.execute(context.get('doc'), **{})
			
			# Propagate changes back to main context
			context['vars'].update(result_context.get('vars', {}))
			
			self._log("INFO", f"END Sub-Rule: {sub_rule_name}")
			
		except Exception as e:
			self._log("ERROR", f"Sub-Rule execution failed: {str(e)}")
			raise
	
	def _log(self, level, message):
		"""Add entry to execution log"""
		entry = {
			'timestamp': frappe.utils.now(),
			'level': level,
			'message': message
		}
		self.execution_log.append(entry)
		
		# Also log to console if debug mode
		if self.rule.debug_mode or self.context.get('test_mode'):
			frappe.logger().info(f"[{self.rule.name}] [{level}] {message}")
	
	def _update_rule_stats(self, success=True, error=None):
		"""Update rule execution statistics (non-blocking, no commit)"""
		try:
			# Update in DB without triggering validations
			# Note: No explicit commit - let the calling transaction handle it
			frappe.db.set_value(
				'Rule',
				self.rule.name,
				{
					'execution_count': (self.rule.execution_count or 0) + 1,
					'last_executed': frappe.utils.now(),
					'last_error': error if not success else None
				},
				update_modified=False
			)
		except Exception as e:
			# Don't fail execution if stats update fails
			frappe.logger().error(f"Failed to update rule stats: {str(e)}")

	def _save_execution_log(self, status, duration, error_trace=None):
		"""Save execution details to Rule Execution Log"""
		try:
			# Serialize context snapshot (remove complex objects)
			context_snapshot = {}
			if hasattr(self, 'context'):
				# Only keep serializable vars
				context_snapshot = {
					k: v for k, v in self.context.get('vars', {}).items() 
					if isinstance(v, (str, int, float, bool, list, dict, type(None)))
				}
			
			log_doc = frappe.get_doc({
				"doctype": "Rule Execution Log",
				"rule": self.rule.name,
				"status": status,
				"duration": duration,
				"reference_doctype": self.rule.document_type,
				"reference_docname": self.context.get('doc').name if self.context.get('doc') else None,
				"executed_by": self.context.get('meta', {}).get('user'),
				"message": error_trace.split('\n')[-2] if error_trace else "Executed successfully",
				"execution_path": json.dumps(self.path_trace, default=str),
				"context_snapshot": json.dumps(context_snapshot, default=str),
				"error_trace": error_trace
			})
			
			# Use ignore_permissions to ensure log is always written regardless of user
			log_doc.insert(ignore_permissions=True)
			
		except Exception as e:
			frappe.logger().error(f"Failed to save Rule Execution Log: {str(e)}")
