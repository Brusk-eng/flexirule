import frappe


def fix_rule():
	frappe.init(site="insight.test")
	frappe.connect()

	rule = frappe.get_doc("Rule", "contacts cleanup")
	for action in rule.actions:
		if action.action_type == "Set Value" and action.return_variable == "loop":
			print(f"Found problematic action: {action.name}")
			action.return_variable = None
			action.mutation_mode = None
			action.save()
			print(f"Fixed action: {action.name}")

	rule.save()
	frappe.db.commit()


if __name__ == "__main__":
	fix_rule()
