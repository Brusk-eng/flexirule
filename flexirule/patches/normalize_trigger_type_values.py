import frappe

TRIGGER_TYPE_MAP = {
	"Scheduled Rule": "Scheduler Event",
	"Scheduler Rule": "Scheduler Event",
	"Callable Rule": "Callable Event",
	"Manual Rule": "Callable Event",
}


def execute():
	if not frappe.db.has_column("Rule", "trigger_type"):
		return

	rules = frappe.get_all("Rule", fields=["name", "trigger_type"], limit=0)
	for rule in rules:
		legacy = (rule.get("trigger_type") or "").strip()
		canonical = TRIGGER_TYPE_MAP.get(legacy)
		if canonical and canonical != legacy:
			frappe.db.set_value("Rule", rule["name"], "trigger_type", canonical, update_modified=False)
