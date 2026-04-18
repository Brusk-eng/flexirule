import frappe
from frappe.model.document import Document


def run():
	frappe.init(site="insight.test")
	frappe.connect()
	try:
		doc = frappe.get_doc(
			{
				"doctype": "Rule",
				"rule_name": "Test Query Records",
				"trigger_type": "DocType Event",
				"trigger_event": "Before Save",
				"document_type": "User",
				"actions": [
					{
						"action_id": "act_test",
						"action_type": "Query Records",
						"action_label": "Test Query",
						"operation": "Query List",
						"reference_doctype": "User",
						"skip_permissions": 0,
						"config": "{}",
					}
				],
			}
		)
		try:
			doc.insert()
			print("Successfully inserted!")
			frappe.db.rollback()
		except Exception as e:
			print("Insert failed!")
			print(f"Exception Type: {type(e)}")
			print(f"Exception message: {e!s}")
			from frappe.utils import get_traceback

			print(get_traceback())

	finally:
		frappe.destroy()


if __name__ == "__main__":
	run()
