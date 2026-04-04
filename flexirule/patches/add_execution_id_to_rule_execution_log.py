import uuid

import frappe


def execute():
	if not frappe.db.has_column("Rule Execution Log", "execution_id"):
		return

	logs = frappe.get_all(
		"Rule Execution Log",
		filters={"execution_id": ["in", ["", None]]},
		fields=["name"],
		limit=0,
	)
	for row in logs:
		frappe.db.set_value(
			"Rule Execution Log",
			row["name"],
			"execution_id",
			str(uuid.uuid4()),
			update_modified=False,
		)

	try:
		frappe.db.add_index("Rule Execution Log", ["execution_id"], "idx_rule_execution_log_execution_id")
	except Exception:
		# Index may already exist.
		pass
