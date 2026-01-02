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
		action_type: DF.Literal["Entry Action", "Condition", "Process", "Loop", "Stop", "Switch", "Wait", "Sub-Rule"]
		condition_expression: DF.Code | None
		condition_json: DF.Code | None
		config: DF.Code | None
		description: DF.Text | None
		input_mapping: DF.Code | None
		is_async: DF.Check
		is_enabled: DF.Check
		next_step_if_false: DF.Data | None
		next_step_if_true: DF.Autocomplete | None
		on_error: DF.Literal["Stop", "Continue", "Retry", "Rollback", "Escalate"]
		operation: DF.Autocomplete | None
		output_mapping: DF.Code | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		position_x: DF.Int
		position_y: DF.Int
		priority: DF.Int
		process_method: DF.Link | None
		process_name: DF.Link | None
		retry_count: DF.Int
		return_variable: DF.Data | None
		rule: DF.Link | None
		skip_conditions: DF.Check
		skip_permissions: DF.Check
		timeout: DF.Int
	# end: auto-generated types
	"""
	Rule Action child table - individual action nodes in a rule flow
	"""