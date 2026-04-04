import frappe

RETURN_TYPE_MAP = {
	"Boolean": "Yes / No",
	"Dict": "Single Record",
	"List": "List of Values",
	"List of Dict": "List of Records",
	"Doc as Dict": "Full Document",
}


def execute():
	if not frappe.db.has_column("Rule Action", "return_type"):
		return

	actions = frappe.get_all("Rule Action", fields=["name", "return_type"], limit=0)
	for action in actions:
		current = (action.get("return_type") or "").strip()
		normalized = RETURN_TYPE_MAP.get(current)
		if normalized and normalized != current:
			frappe.db.set_value(
				"Rule Action", action["name"], "return_type", normalized, update_modified=False
			)
