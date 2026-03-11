# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""
Batch Process - Execute rules against multiple documents.

Operations:
- execute_for_documents: Run rule on explicit document list
- execute_from_filter: Run rule on documents matching filter
"""

import json

import frappe
from frappe import _


def execute_for_documents(context, config):
	"""
	Execute a rule for multiple documents.

	Config:
	    rule: Rule name
	    doctype: Target DocType
	    documents: List of document names or JSON string
	    batch_size: Commit interval (default: 100)
	    on_error: "skip" or "stop"
	"""
	rule_name = config.get("rule")
	doctype = config.get("doctype")
	documents = config.get("documents", [])
	batch_size = int(config.get("batch_size") or 100)
	on_error = config.get("on_error", "skip")

	if isinstance(documents, str):
		try:
			documents = json.loads(documents)
		except Exception:
			documents = []

	if not documents:
		return {"success": 0, "failed": 0, "message": "No documents provided"}

	batch_id = f"BATCH-PROC-{frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}"

	results = {"success": 0, "failed": 0, "batch_id": batch_id, "errors": []}

	for i, doc_name in enumerate(documents):
		try:
			_execute_single(rule_name, doctype, doc_name, batch_id, i + 1, len(documents))
			results["success"] += 1
		except Exception as e:
			results["failed"] += 1
			error_msg = f"{doc_name}: {e!s}"
			results["errors"].append(error_msg)
			if on_error == "stop":
				break

		if (i + 1) % batch_size == 0:
			if not getattr(frappe.flags, "in_test", False):
				frappe.db.commit()
			_publish_progress(batch_id, i + 1, len(documents))

	if not getattr(frappe.flags, "in_test", False):
		frappe.db.commit()
	return results


def execute_from_filter(context, config):
	"""
	Execute rule for documents matching a filter.

	Config:
	    rule: Rule name
	    doctype: Target DocType
	    filters: Frappe filter dict or JSON
	    limit: Max documents (default: 1000)
	"""
	doctype = config.get("doctype")
	filters = config.get("filters", {})
	limit = int(config.get("limit") or 1000)

	if isinstance(filters, str):
		try:
			filters = json.loads(filters)
		except Exception:
			filters = {}

	documents = frappe.get_all(doctype, filters=filters, pluck="name", limit=limit)

	return execute_for_documents(context, {**config, "documents": documents})


def _execute_single(rule_name, doctype, doc_name, batch_id, index, total):
	"""Execute rule for single document with logging."""
	from flexirule.ruleflow.core.coordinator import RuleCoordinator

	doc = frappe.get_doc(doctype, doc_name)

	# Context that will be logged in Rule Execution Log
	context = {
		"doc": doc,
		"batch_id": batch_id,
		"batch_index": index,
		"batch_total": total,
		# 'scheduler' field is not set here since this is triggered by Process, not RuleScheduler doc
	}

	RuleCoordinator.execute_rule(rule_name, context)


def _publish_progress(batch_id, processed, total):
	frappe.publish_realtime(
		"batch_progress",
		{"batch_id": batch_id, "processed": processed, "total": total},
	)


_OPERATIONS = {
	"execute_for_documents": execute_for_documents,
	"execute_from_filter": execute_from_filter,
}


def execute(context, func=None, config=None):
	if not func:
		return None
	if func not in _OPERATIONS:
		frappe.throw(_("Unknown operation: {0}").format(func))
	return _OPERATIONS[func](context, config or {})
