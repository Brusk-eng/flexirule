# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import uuid


class RuleAction(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		action_id: DF.Data
		action_label: DF.Data
		action_type: DF.Literal["Condition", "Process", "Loop", "Stop"]
		condition_expression: DF.Code | None
		condition_json: DF.Code | None
		configuration: DF.Code | None
		description: DF.Text | None
		input_mapping: DF.Code | None
		is_async: DF.Check
		is_enabled: DF.Check
		next_step_if_false: DF.Data | None
		next_step_if_true: DF.Data | None
		on_error: DF.Literal["Stop", "Continue", "Retry", "Rollback"]
		output_mapping: DF.Code | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		position_x: DF.Int
		position_y: DF.Int
		priority: DF.Int
		process_method: DF.Link | None
		retry_count: DF.Int
		return_variable: DF.Data | None
		timeout: DF.Int
	# end: auto-generated types
	"""
	Rule Action child table - individual action nodes in a rule flow
	"""
	
	def before_insert(self):
		"""Generate action_id if not provided"""
		if not self.action_id:
			# Generate short unique ID
			self.action_id = str(uuid.uuid4())[:8]
	
	def validate(self):
		"""Validate action configuration"""
		# Validate process method exists if action_type is Process
		if self.action_type == 'Process' and self.process_method:
			if not frappe.db.exists('Process Method', self.process_method):
				frappe.throw(f'Process Method {self.process_method} does not exist')
		
		# Validate condition is provided for Condition type
		if self.action_type == 'Condition':
			if not self.condition_expression and not self.condition_json:
				frappe.throw('Condition actions must have either condition_expression or condition_json')
		
		# Validate configuration JSON if provided
		if self.configuration:
			try:
				import json
				json.loads(self.configuration)
			except json.JSONDecodeError as e:
				frappe.throw(f'Invalid JSON in configuration: {str(e)}')
