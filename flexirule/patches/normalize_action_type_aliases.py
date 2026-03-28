import frappe


def execute():
	"""Migrate legacy action type aliases to their canonical action types."""

	LEGACY_ALIASES = {
		"Aggregate Records": "Query Records",
		"Create Docs": "Document Action",
		"Sub-rule": "Sub-Rule",
		"Raise Error": "Stop",
	}

	for legacy, canonical in LEGACY_ALIASES.items():
		# Update Rule Action docs
		frappe.db.sql(
			"UPDATE `tabRule Action` SET action_type = %s WHERE action_type = %s", (canonical, legacy)
		)

		# Also update Data Review Task if it stores action type
		if frappe.db.exists("DocType", "Data Review Task"):
			try:
				if frappe.db.has_column("Data Review Task", "action_type"):
					frappe.db.sql(
						"UPDATE `tabData Review Task` SET action_type = %s WHERE action_type = %s",
						(canonical, legacy),
					)
			except Exception:
				pass

	frappe.db.commit()
