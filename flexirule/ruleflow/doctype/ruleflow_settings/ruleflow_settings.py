# Copyright (c) 2026, FlexiRule Contributors and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RuleFlowSettings(Document):
	pass


def get_settings():
	"""Get cached RuleFlow Settings."""
	return frappe.get_cached_doc("RuleFlow Settings")
