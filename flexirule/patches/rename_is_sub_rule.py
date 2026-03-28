import frappe


def execute():
	"""Migrate legacy `is_sub_rule` to `exposed_as_subrule`"""
	if frappe.db.has_column("Rule", "is_sub_rule") and frappe.db.has_column("Rule", "exposed_as_subrule"):
		# Both columns exist, migrate data from old to new
		frappe.db.sql("UPDATE `tabRule` SET `exposed_as_subrule` = `is_sub_rule` WHERE `is_sub_rule` = 1")

		# Drop old column to clean up DB
		try:
			frappe.db.sql("ALTER TABLE `tabRule` DROP COLUMN `is_sub_rule`")
		except Exception:
			pass
