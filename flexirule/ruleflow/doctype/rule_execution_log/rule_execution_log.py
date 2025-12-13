# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class RuleExecutionLog(Document):
	def before_insert(self):
		if not self.executed_by:
			self.executed_by = frappe.session.user
