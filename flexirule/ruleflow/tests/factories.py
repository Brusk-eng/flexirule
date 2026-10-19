import frappe

from flexirule.ruleflow.tests.test_doctypes import setup_test_doctypes


def make_test_contact(test_case=None, **kwargs):
	setup_test_doctypes()
	defaults = {
		"doctype": "Test Contact",
		"first_name": "John",
		"last_name": "Doe",
		"email_id": "john@example.com",
		"phone": "+1234567890",
		"status": "Open",
	}
	do_not_save = kwargs.pop("do_not_save", False)
	defaults.update(kwargs)
	doc = frappe.get_doc(defaults)
	if not do_not_save:
		doc.insert(ignore_permissions=True)
		if test_case and hasattr(test_case, "addCleanup"):
			test_case.addCleanup(
				lambda dt=doc.doctype, dn=doc.name: (
					frappe.delete_doc(dt, dn, force=True, ignore_permissions=True)
					if frappe.db.exists(dt, dn)
					else None
				)
			)
	return doc


def make_test_customer(test_case=None, **kwargs):
	setup_test_doctypes()
	do_not_save = kwargs.pop("do_not_save", False)
	defaults = {
		"doctype": "Test Customer",
		"customer_name": "Acme Corp",
		"email_id": "acme@example.com",
		"customer_group": "Commercial",
		"territory": "United States",
		"credit_limit": 5000,
		"status": "Active",
	}
	defaults.update(kwargs)
	doc = frappe.get_doc(defaults)
	if not do_not_save:
		doc.insert(ignore_permissions=True)
		if test_case and hasattr(test_case, "addCleanup"):
			test_case.addCleanup(
				lambda dt=doc.doctype, dn=doc.name: (
					frappe.delete_doc(dt, dn, force=True, ignore_permissions=True)
					if frappe.db.exists(dt, dn)
					else None
				)
			)
	return doc


def make_test_lead(test_case=None, **kwargs):
	setup_test_doctypes()
	do_not_save = kwargs.pop("do_not_save", False)
	defaults = {
		"doctype": "Test Lead",
		"first_name": "Jane",
		"email_id": "jane@example.com",
		"status": "Lead",
	}
	defaults.update(kwargs)
	doc = frappe.get_doc(defaults)
	if not do_not_save:
		doc.insert(ignore_permissions=True)
		if test_case and hasattr(test_case, "addCleanup"):
			test_case.addCleanup(
				lambda dt=doc.doctype, dn=doc.name: (
					frappe.delete_doc(dt, dn, force=True, ignore_permissions=True)
					if frappe.db.exists(dt, dn)
					else None
				)
			)
	return doc
