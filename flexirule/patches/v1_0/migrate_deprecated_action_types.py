import frappe


def execute():
	"""
	Migrates deprecated Rule Action types to their new consolidated equivalents.
	- 'Aggregate Records' -> 'Query Records'
	- 'Create Docs' -> 'Document Action'
	"""

	# Migrate 'Aggregate Records' to 'Query Records'
	frappe.db.sql("""
		UPDATE `tabRule Action`
		SET action_type = 'Query Records'
		WHERE action_type = 'Aggregate Records'
	""")

	# Migrate 'Create Docs' to 'Document Action'
	frappe.db.sql("""
		UPDATE `tabRule Action`
		SET action_type = 'Document Action'
		WHERE action_type = 'Create Docs'
	""")
