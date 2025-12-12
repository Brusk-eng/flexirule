# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class DataQualityIssue(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		assigned_to: DF.Link | None
		details_json: DF.Code | None
		message: DF.Text
		reference_doctype: DF.Link
		reference_name: DF.DynamicLink
		resolution_notes: DF.Text | None
		resolved_at: DF.Datetime | None
		resolved_by: DF.Link | None
		rule: DF.Link
		severity: DF.Literal["High", "Medium", "Low"]
		status: DF.Literal["Open", "In Progress", "Resolved", "Ignored"]
	# end: auto-generated types

	pass
