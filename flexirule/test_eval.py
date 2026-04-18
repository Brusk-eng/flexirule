import frappe
from frappe.model.document import Document


def run():
	frappe.init(site="flexist")
	frappe.connect()
	try:
		doc = frappe.get_doc(
			{
				"doctype": "Rule Action",
				"action_id": "root",
				"action_type": "Query Records",
				"action_label": "Testing",
				"operation": "Query List",
				"skip_permissions": 0,
			}
		)
		print("skip_permissions value:", doc.skip_permissions)
		res = doc.evaluate_depends_on_value("eval:doc.skip_permissions", doc.as_dict())
		print("eval result:", res)
	finally:
		frappe.destroy()


if __name__ == "__main__":
	run()
