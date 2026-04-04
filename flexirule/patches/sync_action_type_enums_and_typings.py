import frappe


def execute():
	for dt in ("Rule", "Rule Action", "Rule Execution Log"):
		try:
			frappe.clear_cache(doctype=dt)
		except Exception:
			pass
