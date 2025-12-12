# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Rule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actions_json: DF.Code | None
		conditions_json: DF.Code | None
		debug_mode: DF.Check
		document_type: DF.Link
		execution_count: DF.Int
		is_active: DF.Check
		last_error: DF.Text | None
		last_executed: DF.Datetime | None
		options_json: DF.Code | None
		priority: DF.Int
		rule_name: DF.Data
		rule_type: DF.Literal["Validation", "Deduplication", "Transformation", "Enrichment"]
		trigger_event: DF.Literal["before_insert", "before_save", "validate", "after_insert", "after_save", "before_submit", "on_submit", "before_cancel", "on_cancel", "on_trash"]
	# end: auto-generated types

	pass
