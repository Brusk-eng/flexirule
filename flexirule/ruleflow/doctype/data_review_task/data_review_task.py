# Copyright (c) 2025, Bolton and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DataReviewTask(Document):
    def validate(self):
        pass
    
    def before_save(self):
        # Auto-set resolved info when status changes to Resolved
        if self.status == 'Resolved' and not self.resolved_by:
            self.resolved_by = frappe.session.user
            self.resolved_on = frappe.utils.now()
    
    def on_update(self):
        pass
