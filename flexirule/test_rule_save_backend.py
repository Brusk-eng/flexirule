import json

import frappe


def test_lead_nurturing_save():
	frappe.db.rollback()

	rule_name = "Advanced Lead Nurturing Test"
	if frappe.db.exists("Rule", rule_name):
		frappe.delete_doc("Rule", rule_name)

	rule = frappe.get_doc(
		{
			"doctype": "Rule",
			"rule_name": rule_name,
			"document_type": "Contact",
			"trigger_type": "DocType Event",
			"trigger_event": "After Insert",
			"actions": [
				{"action_id": "start", "action_type": "Entry Action", "next_step_if_true": "cond_email"},
				{
					"action_id": "cond_email",
					"action_type": "Condition",
					"action_label": "Has Email?",
					"condition_expression": "doc.email_id",
					"next_step_if_true": "wait_2_hours",
					"next_step_if_false": "notify_missing",
				},
				{
					"action_id": "notify_missing",
					"action_type": "Notify",
					"action_label": "Notify Missing Email",
					"operation": "Toast",
					"config": json.dumps({"message": "No email found for contact"}),
				},
				{
					"action_id": "wait_2_hours",
					"action_type": "Wait",
					"action_label": "Delay 2 Hours",
					"config": json.dumps({"value": 2, "unit": "Hours"}),
					"next_step_if_true": "create_todo",
				},
				{
					"action_id": "create_todo",
					"action_type": "Create Docs",
					"action_label": "Create Follow-up ToDo",
					"operation": "Create ToDo",
					"reference_doctype": "ToDo",
					"mutation_mode": "Single",
					"return_variable": "new_doc",
					"config": json.dumps(
						{
							"assigned_to": "Administrator",
							"description": "Follow up on contact: {{ doc.name }}",
						}
					),
				},
			],
		}
	)

	try:
		rule.insert()
		frappe.db.commit()
		print(f"Successfully saved Rule: {rule.name}")
		return True
	except Exception as e:
		print(f"Failed to save Rule: {e!s}")
		import traceback

		traceback.print_exc()
		return False


if __name__ == "__main__":
	test_lead_nurturing_save()
