import json

import frappe


def execute():
	"""Migrate `input_mapping` and `output_mapping` into the `config` JSON column for all existing `Rule Action` rows."""
	has_input = frappe.db.has_column("Rule Action", "input_mapping")
	has_output = frappe.db.has_column("Rule Action", "output_mapping")

	if not has_input and not has_output:
		return

	filters: dict = {}
	or_filters: list = []

	if has_input:
		or_filters.append(["input_mapping", "!=", ""])
	if has_output:
		or_filters.append(["output_mapping", "!=", ""])

	fields = ["name", "config"]
	if has_input:
		fields.append("input_mapping")
	if has_output:
		fields.append("output_mapping")

	actions = frappe.get_all("Rule Action", filters=filters, or_filters=or_filters, fields=fields)

	for action in actions:
		config = {}
		if action.get("config"):
			try:
				config = json.loads(action["config"])
			except Exception:
				pass

		if has_input and action.get("input_mapping"):
			config["input_mapping"] = action["input_mapping"]
		if has_output and action.get("output_mapping"):
			config["output_mapping"] = action["output_mapping"]

		frappe.db.set_value("Rule Action", action["name"], "config", json.dumps(config))

	# Drop old columns
	try:
		if has_input:
			frappe.db.sql("ALTER TABLE `tabRule Action` DROP COLUMN `input_mapping`")
		if has_output:
			frappe.db.sql("ALTER TABLE `tabRule Action` DROP COLUMN `output_mapping`")
	except Exception:
		pass
