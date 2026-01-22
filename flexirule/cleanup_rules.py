import frappe


def execute():
    frappe.db.delete("Rule", {"rule_name": ["like", "Test Dry Run%"]})
    frappe.db.delete("Rule Execution Log", {"rule": ["like", "Test Dry Run%"]})
    frappe.db.commit()
    print("Cleaned up Test Dry Run rules.")


if __name__ == "__main__":
    execute()
