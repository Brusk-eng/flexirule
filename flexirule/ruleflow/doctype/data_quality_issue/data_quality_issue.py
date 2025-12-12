# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class DataQualityIssue(Document):
	"""Data Quality Issue log for rule violations and quality problems"""
	
	def before_save(self):
		"""Track resolution"""
		if self.status == "Resolved" and not self.resolved_at:
			self.resolved_at = now_datetime()
			self.resolved_by = frappe.session.user
