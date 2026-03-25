# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from flexirule.ruleflow.utils.field_resolver import parse_field_list, parse_field_mapping


def calculate_value(context, config=None, **kwargs):
	"""
	Calculate a field value using a Python formula (Safe Eval).

	config: {
	    "target_field": "fieldname",
	    "formula": "doc.qty * doc.rate"
	}
	"""
	doc = context.get("doc")
	if not doc or not config:
		return

	target_field = config.get("target_field")
	formula = config.get("formula")

	if not target_field or not formula:
		return

	# Safe evaluation context
	eval_context = {
		"doc": doc,
		"frappe": frappe,
		"context": context,
		"_": _,
		"abs": abs,
		"int": int,
		"float": float,
		"round": round,
		"max": max,
		"min": min,
	}

	try:
		result = frappe.safe_eval(formula, None, eval_context)
		doc.set(target_field, result)
		return result
	except Exception as e:
		frappe.log_error(
			f"Enrichment: Formula evaluation failed for {target_field}: {e}",
			"Enrichment Error",
		)
		raise


def linked_doc_autocomplete(context, config=None, **kwargs):
	"""
	Copy field values from a linked document.

	config: {
	    "source_link_field": "fieldname",
	    "field_mapping": [{"source_field": "x", "target_field": "y"}]
	}
	"""
	doc = context.get("doc")
	if not doc or not config:
		return

	source_link_field = config.get("source_link_field")
	field_mapping = config.get("field_mapping")

	if not source_link_field or not field_mapping:
		return

	# Get the linked document
	link_doctype = frappe.get_meta(doc.doctype).get_field(source_link_field).options
	link_value = doc.get(source_link_field)

	if not link_value:
		return {}

	linked_doc = frappe.get_doc(link_doctype, link_value)
	mapping = parse_field_mapping(field_mapping)

	results = {}
	for source_field, target_field in mapping.items():
		value = linked_doc.get(source_field)
		if value is not None:
			doc.set(target_field, value)
			results[target_field] = value

	return results


def copy_from_template(context, config=None, **kwargs):
	"""
	Copy field values from a template document.

	config: {
	    "template_doctype": "DocType",
	    "template_name": "Name",
	    "field_list": ["f1", "f2"]
	}
	"""
	doc = context.get("doc")
	if not doc or not config:
		return

	template_doctype = config.get("template_doctype")
	template_name = config.get("template_name")
	field_list = parse_field_list(config.get("field_list"))

	if not template_doctype or not template_name or not field_list:
		return {}

	template = frappe.get_doc(template_doctype, template_name)

	results = {}
	for field in field_list:
		value = template.get(field)
		if value is not None:
			doc.set(field, value)
			results[field] = value

	return results


# ============================================================
# DISPATCHER
# ============================================================

_OPERATIONS = {
	"calculate_value": calculate_value,
	"linked_doc_autocomplete": linked_doc_autocomplete,
	"copy_from_template": copy_from_template,
}


def execute(context, func=None, config=None):
	if not func:
		frappe.throw(_("Operation function name is required"))
	if func not in _OPERATIONS:
		frappe.throw(_("Unknown enrichment operation: {0}").format(func))

	return _OPERATIONS[func](context, config or {})
