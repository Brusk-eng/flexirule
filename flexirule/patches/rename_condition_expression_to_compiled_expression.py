import frappe


def execute():
	has_legacy = frappe.db.has_column("Rule Action", "condition_expression")
	has_compiled = frappe.db.has_column("Rule Action", "compiled_expression")

	if not has_legacy or not has_compiled:
		return

	actions = frappe.get_all(
		"Rule Action",
		filters={"condition_expression": ["is", "set"]},
		fields=["name", "condition_expression", "compiled_expression"],
		limit=0,
	)
	for action in actions:
		if not action.get("compiled_expression"):
			frappe.db.set_value(
				"Rule Action",
				action["name"],
				"compiled_expression",
				action.get("condition_expression"),
				update_modified=False,
			)
