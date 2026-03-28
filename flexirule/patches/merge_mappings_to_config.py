import json

import frappe


def execute():
	"""Migrate `input_mapping` and `output_mapping` into the `config` JSON column for all existing `Rule Action` rows."""
	has_input = frappe.db.has_column("Rule Action", "input_mapping")
	has_output = frappe.db.has_column("Rule Action", "output_mapping")

	if not has_input and not has_output:
		return

	# Fetch all Rule Actions that have mapping data
	conditions = []
	if has_input:
		conditions.append("(input_mapping IS NOT NULL AND input_mapping != '')")
	if has_output:
		conditions.append("(output_mapping IS NOT NULL AND output_mapping != '')")

	columns = ["name", "config"]
	if has_input:
		columns.append("input_mapping")
	if has_output:
		columns.append("output_mapping")

	query = f"SELECT `{',`'.join(columns)}` FROM `tabRule Action` WHERE {' OR '.join(conditions)}"

	actions = frappe.db.sql(query, as_dict=True)

	for action in actions:
		config = {}
		if action.config:
			try:
				config = json.loads(action.config)
			except Exception:
				pass

		if has_input and action.get("input_mapping"):
			config["input_mapping"] = action.input_mapping
		if has_output and action.get("output_mapping"):
			config["output_mapping"] = action.output_mapping

		frappe.db.sql(
			"UPDATE `tabRule Action` SET config = %s WHERE name = %s", (json.dumps(config), action.name)
		)

	# Drop old columns
	try:
		if has_input:
			frappe.db.sql("ALTER TABLE `tabRule Action` DROP COLUMN `input_mapping`")
		if has_output:
			frappe.db.sql("ALTER TABLE `tabRule Action` DROP COLUMN `output_mapping`")
	except Exception:
		pass
