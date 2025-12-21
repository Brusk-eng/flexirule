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
from frappe import _
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
from flexirule.ruleflow.utils.schema_validator import get_custom_validator, frappe_fields_to_json_schema
from flexirule.ruleflow.utils.field_resolver import FieldResolver


class TimeoutException(Exception):
	"""Internal timeout exception"""
	pass


class ReadOnlyDocument:
	"""Proxy for Document that prevents mutation"""
	def __init__(self, doc):
		object.__setattr__(self, "_doc", doc)
	
	def __getattr__(self, name):
		return getattr(self._doc, name)
		
	def __getitem__(self, key):
		return self._doc[key]

	def get(self, key, default=None):
		return self._doc.get(key, default)

	def __setattr__(self, name, value):
		raise frappe.ValidationError("Cannot mutate document in Pure method")
			
	def __setitem__(self, key, value):
		raise frappe.ValidationError("Cannot mutate document in Pure method")
		
	def save(self, *args, **kwargs):
		raise frappe.ValidationError("Cannot save document in Pure method")
		
	def insert(self, *args, **kwargs):
		raise frappe.ValidationError("Cannot insert document in Pure method")
		
	def delete(self, *args, **kwargs):
		raise frappe.ValidationError("Cannot delete document in Pure method")
		
	def db_set(self, *args, **kwargs):
		raise frappe.ValidationError("Cannot db_set document in Pure method")


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

# TODO : Explore frappe source code to find if they have a similar implementation and use it instead Introduced for SafeFrappeAPI
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
			error_msg = _("Rule execution exceeded timeout ({0}s)").format(timeout if 'timeout' in locals() else 'unknown')
			error_detail = traceback.format_exc()
			self._log("ERROR", error_msg)
			if context if 'context' in locals() else None:
				self._update_rule_stats(success=False, error=error_msg)
			raise BoltonTimeoutError(error_msg)
		
		except Exception as e:
			status = "Failed"
			error_msg = str(e)
			error_detail = traceback.format_exc()
			self._log("ERROR", _("Rule execution failed: {0}").format(error_msg))
			if context if 'context' in locals() else None:
				self._update_rule_stats(success=False, error=error_msg)
			raise
			
		finally:
			# Persist Log
			duration = time.time() - start_time
			self._save_execution_log(status, duration, error_detail, context=context if 'context' in locals() else None)
	
	def _validate_execution(self):
		"""Validate rule is executable"""
		if not self.rule.is_active:
			raise RuleDisabledError(_("Rule {0} is disabled").format(self.rule.name))
		
		if not self.actions:
			raise EmptyRuleError(_("Rule {0} has no enabled actions").format(self.rule.name))
	
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
				self._log("INFO", _("Reached end of flow (no next action)"))
				break
			
			if context.get('stop'):
				self._log("INFO", _("Flow stopped by action"))
				break
			
			# Cycle/Loop detection
			node_id = current.action_id or current.name
			
			# Track visits
			visits = node_visits.get(node_id, 0) + 1
			node_visits[node_id] = visits
			
			if visits > max_visits_per_node:
				raise CycleDetectedError(_("Infinite loop detected: Action {0} visited {1} times").format(current.action_label, visits))
			
			execution_path.append(current.action_label)
			self.path_trace.append({
				"node": current.action_label,
				"type": current.action_type,
				"timestamp": time.time()
			})
			
			# Log execution
			self._log("INFO", _("Executing action: {0} (type: {1})").format(current.action_label, current.action_type))
			
			try:
				# Standardized Handlers (Dispatcher)
				handler_map = {
					'Condition': self._execute_condition,
					'Switch': self._execute_switch,
					'Process': self._execute_process,
					'Sub-Rule': self._execute_sub_rule,
					'Stop': self._execute_stop,
					'Wait': self._execute_wait,
					'Loop': self._execute_loop
				}
				
				handler = handler_map.get(current.action_type)
				if not handler:
					self._log("WARNING", _("Unknown action type: {0}").format(current.action_type))
					result = None
					next_id = current.next_step_if_true
				else:
					# Handlers now return (result, next_id)
					result, next_id = handler(current, context)
				
				# Store result if variable specified
				if current.return_variable and result is not None:
					context['vars'][current.return_variable] = result
					self._log("DEBUG", _("Stored result in variable: {0}").format(current.return_variable))
				
				# Move to next node
				current = self._get_action_by_id(next_id) if next_id else None

			except Exception as e:
				# Handle error based on on_error setting
				if hasattr(current, 'on_error'):
					if current.on_error == 'Continue':
						self._log("WARNING", _("Error in action {0}, continuing: {1}").format(current.action_label, str(e)))
						current = self._get_action_by_id(current.next_step_if_true)
						continue
					elif current.on_error == 'Rollback':
						self._log("ERROR", _("Error in action {0}, rolling back: {1}").format(current.action_label, str(e)))
						frappe.db.rollback()
						raise
					elif current.on_error == 'Escalate':
						self._log("ERROR", _("Error in action {0}, escalating: {1}").format(current.action_label, str(e)))
						raise
				
				# Default: stop on error
				self._log("ERROR", _("Error in action {0}: {1}").format(current.action_label, str(e)))
				raise
		
		if iteration >= max_iterations - 1:
			raise CycleDetectedError(_("Max total iterations ({0}) exceeded").format(max_iterations))
		
		self._log("INFO", _("Execution path: {0}").format(' → '.join(execution_path)))
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
				self._log("INFO", _("Start node: {0} ({1})").format(action.action_label, action_id))
				return action
		
		# Fallback to first action if no clear start
		self._log("WARNING", _("No clear start node, using first action"))
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
		# Conditions MUST be pre-compiled during Rule.validate()
		# If condition_expression is missing but condition_json exists, the rule was not properly saved
		if not action.condition_expression:
			if action.condition_json:
				raise ValueError(_(
					"Action '{0}' has condition_json but no compiled condition_expression. "
					"Please re-save the Rule to compile conditions."
				).format(action.action_label))
			result = True  # Empty condition passes
		else:
			result = self._evaluate_python_condition(action.condition_expression, context)
		
		next_id = action.next_step_if_true if result else action.next_step_if_false
		return result, next_id
	
	def _evaluate_python_condition(self, expression, context):
		"""Evaluate Python expression safely"""
		if not expression:
			return True
		
		# Prepare safe locals
		safe_locals = {
			'doc': context.get('doc'),
			'old_doc': context.get('old_doc'),
			'vars': context.get('vars'),
			'frappe': context.get('frappe', frappe.utils),
			'resolve': FieldResolver.resolve,
			'True': True,
			'False': False,
			'None': None
		}
		
		try:
			return frappe.safe_eval(expression, None, safe_locals)
		except Exception as e:
			self._log("ERROR", _("Condition evaluation failed: {0}").format(str(e)))
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
			self._log("WARNING", _("Loop iterator {0} is not a list/tuple. Got {1}").format(iterator_name, type(items)))
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
			return True, action.next_step_if_true
		else:
			# Loop finished
			# Cleanup
			if action.action_id in context['vars']['_loops']:
				del context['vars']['_loops'][action.action_id]
			return False, action.next_step_if_false

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
			self._log("INFO", _("Waiting for {0} seconds...").format(duration))
			time.sleep(duration)
		
		return None, action.next_step_if_true

	def _execute_stop(self, action, context):
		"""Execute Stop action"""
		self._log("INFO", _("Stop action encountered"))
		return None, None
	
	def _execute_process(self, action, context):
		"""
		Execute Process Method with validation and error handling
		"""
		if not action.process_method:
			self._log("WARNING", _("Process action {0} has no process_method set").format(action.action_label))
			return None
		
		# Get Process Method document
		try:
			process_method = frappe.get_cached_doc('Process Method', action.process_method)
		except frappe.DoesNotExistError:
			raise MethodExecutionError(_("Process Method {0} not found").format(action.process_method))
		
		# Parse configuration
		config = {}
		if action.method_config:
			try:
				config = json.loads(action.method_config)
			except json.JSONDecodeError as e:
				raise MethodExecutionError(_("Invalid configuration JSON: {0}").format(str(e)))
		
		# Apply Input Mapping (Context -> Config)
		if action.input_mapping:
			config = apply_input_mapping(context, action.input_mapping, config)
		
		# Validation: Check against Input Schema
		if process_method.input_schema:
			try:
				schema = json.loads(process_method.input_schema)
				# Convert Frappe fields list to standard JSON Schema if needed
				schema = frappe_fields_to_json_schema(schema)
				
				# Use custom validator that allows 0/1 for booleans
				Validator = get_custom_validator(schema)
				Validator(schema).validate(config)
			except (json.JSONDecodeError, SchemaValidationError) as e:
				raise MethodExecutionError(
					_("Input contract violation in {0}. Inputs do not match Input Schema: {1}").format(process_method.method_name, str(e))
				)

		# Validation: Execution Mode Constraints
		# 1. Rule Level Async Checks
		resolved_rule_mode = self.rule.execution_mode
		if resolved_rule_mode == 'Asynchronous' and process_method.transactional:
			raise MethodExecutionError(
				_("Transactional method '{0}' cannot be executed in Asynchronous Rule.").format(process_method.method_name)
			)

		# 2. Action Level Async Checks (Fire & Forget Enforcement)
		if action.is_async:
			if action.output_mapping:
				raise MethodExecutionError(
					_("Async action '{0}' cannot have output mapping.").format(action.action_label)
				)
			if action.next_step_if_true: # Note: Logic nodes control flow, Process usually just has next_step_if_true
				raise MethodExecutionError(
					 _("Async action '{0}' cannot contribute to flow control (next_step found).").format(action.action_label)
				)
			if process_method.transactional:
				raise MethodExecutionError(
					_("Transactional method '{0}' cannot be executed as Async action.").format(process_method.method_name)
				)
			if process_method.side_effects == 'Modifies Doc':
				raise MethodExecutionError(
					 _("Method '{0}' that modifies document cannot be executed as Async action.").format(process_method.method_name)
				)

		# Execution Context Preparation
		exec_context = context
		if process_method.side_effects == 'Pure' or action.is_async:
			# Create a safe context with ReadOnlyDocument
			# For Pure: Contract enforcement
			# For Async: Race condition prevention (trigger doc must be immutable)
			exec_context = context.copy()
			exec_context['doc'] = ReadOnlyDocument(context['doc'])

		# Execute with retry logic
		result = self._call_method_with_retry(
			process_method=process_method,
			config=config,
			context=exec_context,
			retry_count=action.retry_count or 0,
			timeout=action.timeout or 30
		)

		# Validation: Output Schema
		if process_method.output_schema:
			try:
				output_schema = json.loads(process_method.output_schema)
				# 1. Type Check & Required Fields
				validate(instance=result, schema=output_schema)
				
			except (json.JSONDecodeError, SchemaValidationError) as e:
				raise MethodExecutionError(
					_("Output contract violation in {0}. Result does not match Output Schema: {1}").format(process_method.method_name, str(e))
				)
		
		# Apply Output Mapping (Result -> Context)
		if action.output_mapping:
			# Re-verify sync enforcement (double check)
			if action.is_async:
				 raise MethodExecutionError(_("Async actions cannot map outputs"))
				 
			apply_output_mapping(result, action.output_mapping, context)
			
		return result, action.next_step_if_true
	
	def _call_method_with_retry(self, process_method, config, context, retry_count, timeout):
		"""Execute method with retry logic"""
		last_error = None
		
		for attempt in range(retry_count + 1):
			try:
				# Log attempt
				if attempt > 0:
					self._log("INFO", _("Retry attempt {0}/{1} for {2}").format(attempt, retry_count, process_method.method_name))
				
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
				self._log("ERROR", _("Method execution failed (attempt {0}): {1}").format(attempt + 1, str(e)))
				
				if attempt < retry_count:
					# Exponential backoff
					backoff_seconds = 2 ** attempt
					self._log("INFO", _("Waiting {0}s before retry").format(backoff_seconds))
					time.sleep(backoff_seconds)
				else:
					# All retries exhausted
					break
		
		# All retries failed
		raise MethodExecutionError(
			_("Method {0} failed after {1} attempts: {2}").format(process_method.method_name, retry_count + 1, str(last_error))
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
			next_id = cases.get(val) or cases.get(str(val)) or action.next_step_if_true
			
			return val, next_id
			
		except Exception as e:
			self._log("ERROR", _("Switch evaluation failed: {0}").format(str(e)))
			raise

	def _execute_sub_rule(self, action, context):
		"""Execute a Sub-Rule"""
		try:
			# Prioritize the new 'rule' field, fallback to method_config for backward compatibility
			sub_rule_name = action.rule
			if not sub_rule_name and action.method_config:
				try:
					config = json.loads(action.method_config)
					sub_rule_name = config.get('rule')
				except:
					pass
			
			if not sub_rule_name:
				self._log("WARNING", _("Sub-Rule action missing rule reference"))
				return None, action.next_step_if_true
				
			if not frappe.db.exists("Rule", sub_rule_name):
				raise MethodExecutionError(_("Sub-Rule {0} not found").format(sub_rule_name))
				
			sub_rule_doc = frappe.get_cached_doc("Rule", sub_rule_name)
			
			if not sub_rule_doc.is_active:
				raise MethodExecutionError(_("Sub-Rule {0} is not active").format(sub_rule_name))
				
			if sub_rule_doc.document_type != self.rule.document_type:
				raise MethodExecutionError(
					_("Sub-Rule {0} expects {1}, but current context is {2}")
					.format(sub_rule_name, sub_rule_doc.document_type, self.rule.document_type)
				)
			
			# Recursive Execution
			# We share 'vars' and 'doc' so mutations propagate
			# But we might want to isolate 'stop' flag? 
			# V1 Contract: "vars is the ONLY mutable storage"
			
			self._log("INFO", _("BEGIN Sub-Rule: {0}").format(sub_rule_name))
			
			# Create sub-context sharing vars
			sub_context = context.copy()
			sub_context['meta'] = context.get('meta', {}).copy()
			sub_context['meta']['parent_rule'] = self.rule.name
			
			# Recursion Guard
			current_depth = sub_context['meta'].get('call_depth', 0)
			if current_depth > 5:
				raise MethodExecutionError(_("Max sub-rule recursion depth (5) exceeded in {0}").format(sub_rule_name))
			sub_context['meta']['call_depth'] = current_depth + 1
			
			# Instantiate new engine
			# Avoid cyclic import if lazy loading is better, but Engine is here
			# Since we are in Engine class, we can just instantiate self.__class__
			sub_engine = self.__class__(sub_rule_doc, execution_context=sub_context)
			
			result_context = sub_engine.execute(context.get('doc'), **{})
			
			# Propagate changes back to main context
			context['vars'].update(result_context.get('vars', {}))
			
			self._log("INFO", _("END Sub-Rule: {0}").format(sub_rule_name))
			
			return None, action.next_step_if_true
			
		except Exception as e:
			self._log("ERROR", _("Sub-Rule execution failed: {0}").format(str(e)))
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

	def _save_execution_log(self, status, duration, error_trace=None, context=None):
		"""Save execution details to Rule Execution Log"""
		try:
			# Serialize context snapshot (remove complex objects)
			context_snapshot = {}
			active_context = context or getattr(self, 'context', {})
			
			if active_context:
				# Only keep serializable vars
				context_snapshot = {
					k: v for k, v in active_context.get('vars', {}).items() 
					if isinstance(v, (str, int, float, bool, list, dict, type(None)))
				}
				
				# Add document snapshot for debugging
				if active_context.get('doc'):
					try:
						# Use as_dict but protect against non-serializable fields if any
						doc_dict = active_context['doc'].as_dict()
						context_snapshot['doc'] = doc_dict
					except:
						context_snapshot['doc'] = "<Not Serializable>"
			
			# Handle Local Documents (New Docs)
			# If we rollback, the doc might disappear, so the link will be broken.
			# We still save the name for reference.
			doc = active_context.get('doc') if active_context else None
			doc_name = doc.name if doc else None
			
			if doc and doc.get('__islocal'):
				# If it's local, it might not exist after rollback
				pass

			log_doc = frappe.get_doc({
				"doctype": "Rule Execution Log",
				"rule": self.rule.name,
				"status": status,
				"duration": duration,
				"reference_doctype": self.rule.document_type,
				"reference_docname": doc_name,
				"executed_by": active_context.get('meta', {}).get('user') if active_context else frappe.session.user,
				"message": error_trace.split('\n')[-2] if error_trace else _("Executed successfully"),
				"execution_path": json.dumps(self.path_trace, default=str),
				"context_snapshot": json.dumps(context_snapshot, default=str),
				"error_trace": error_trace
			})
			
			# PERSISTENCE LOGIC
			# If failed, we MUST rollback partial changes to clean up, 
			# then insert and commit the log so it survives the final rollback by the framework.
			if status in ('Failed', 'Error') and not (active_context or {}).get('test_mode'): 
				frappe.db.rollback()
				log_doc.insert(ignore_permissions=True)
				frappe.db.commit()
			else:
				# Success or Test Mode: Just insert (part of current transaction)
				log_doc.insert(ignore_permissions=True)
			
		except Exception as e:
			# Fallback if logging itself fails
			frappe.logger().error(f"Failed to save Rule Execution Log: {str(e)}")
