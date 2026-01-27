# Copyright (c) 2025, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from flexirule.ruleflow.utils.field_resolver import parse_field_list


def create_review_task(context, config=None, **kwargs):
	"""
	Create a Data Review Task for data steward review.

	config: {
	    "task_type": "Duplicate Review",
	    "priority": "Medium",
	    "description": "Please review {{ doc.name }}"
	}
	"""
	doc = context.get("doc")
	if not doc or not config:
		return

	task_type = config.get("task_type", "Data Quality")
	priority = config.get("priority", "Medium")
	description = config.get("description", "")

	# Check if Data Review Task doctype exists
	if not frappe.db.exists("DocType", "Data Review Task"):
		frappe.log_error(_("Data Review Task DocType not found."), "MDM Error")
		return

	# Render description
	rendered_desc = frappe.render_template(description, {"doc": doc, "frappe": frappe, "context": context})

	task = frappe.new_doc("Data Review Task")
	task.task_type = task_type
	task.priority = priority
	task.description = rendered_desc
	task.source_doctype = doc.doctype
	task.source_document = doc.name
	task.status = "Open"

	if context.get("rule"):
		task.rule = context["rule"].name

	task.insert(ignore_permissions=True)
	return task.name


def find_duplicates_and_task(context, config=None, **kwargs):
	"""
	Find similar records and create Data Review Tasks.
	"""
	doc = context.get("doc")
	if not doc or not config:
		return []

	# Import deduplication logic
	from flexirule.ruleflow.process.deduplication.deduplication import (
		find_similar_records,
	)

	# Find similar records
	matches = find_similar_records(
		context,
		config=config,  # Passes overall_threshold, fields_config, etc.
		**kwargs,
	)

	if not matches:
		return []

	created_tasks = []
	max_tasks = config.get("max_tasks", 5)

	for match in matches[:max_tasks]:
		match_name = match.get("name")
		match_score = match.get("score", 0)

		# Skip if task already exists
		if frappe.db.exists(
			"Data Review Task",
			{
				"source_doctype": doc.doctype,
				"source_document": doc.name,
				"related_document": match_name,
				"status": ["in", ["Open", "In Progress"]],
			},
		):
			continue

		description = f"Potential duplicate found with {match_name} (Score: {match_score}%)"

		task_config = {
			"task_type": config.get("task_type", "Duplicate Review"),
			"priority": config.get("priority", "Medium"),
			"description": description,
		}

		task_name = create_review_task(context, task_config)
		if task_name:
			# Update task with match details
			frappe.db.set_value(
				"Data Review Task",
				task_name,
				{"similarity_score": match_score, "related_document": match_name},
			)
			created_tasks.append(task_name)

	return created_tasks


def batch_normalize(context, config=None, **kwargs):
	"""
	Enqueue normalization of all documents in background.
	"""
	doctype = config.get("doctype")
	if not doctype:
		return

	frappe.enqueue(
		"flexirule.ruleflow.process.mdm.mdm.run_batch_normalize",
		doctype=doctype,
		config=config,
		timeout=3600,
		queue="long",
	)
	return True


def run_batch_normalize(doctype, config):
	"""Background job for normalization."""
	from flexirule.ruleflow.process.normalization.normalization import (
		apply_transformations,
	)

	field = config.get("field")
	target_field = config.get("target_field") or field
	transformations = config.get("transformations", [])
	config.get("batch_size", 100)

	filters = config.get("filters") or {"docstatus": ["!=", 2]}

	docs = frappe.get_all(doctype, filters=filters, fields=["name", field])

	for doc_data in docs:
		val = doc_data.get(field)
		if val:
			normalized = apply_transformations(val, transformations)
			frappe.db.set_value(doctype, doc_data.name, target_field, normalized, update_modified=False)

		if frappe.flags.in_test:
			continue  # Don't commit in tests
		frappe.db.commit()


def batch_dedupe(context, config=None, **kwargs):
	"""
	Enqueue duplicate detection of all documents in background.
	"""
	doctype = config.get("doctype")
	if not doctype:
		return

	frappe.enqueue(
		"flexirule.ruleflow.process.mdm.mdm.run_batch_dedupe",
		doctype=doctype,
		config=config,
		timeout=3600,
		queue="long",
	)
	return True


def run_batch_dedupe(doctype, config):
	"""Background job for deduplication."""
	from flexirule.ruleflow.process.deduplication.deduplication import (
		find_similar_records,
	)

	config.get("batch_size", 50)
	filters = config.get("filters") or {"docstatus": ["!=", 2]}

	docs = frappe.get_all(doctype, filters=filters, fields=["name"])

	for doc_data in docs:
		doc = frappe.get_doc(doctype, doc_data.name)
		ctx = {"doc": doc}

		find_duplicates_and_task(ctx, config)

		if frappe.flags.in_test:
			continue
		frappe.db.commit()


# ============================================================
# DISPATCHER
# ============================================================

_OPERATIONS = {
	"create_review_task": create_review_task,
	"find_duplicates_and_task": find_duplicates_and_task,
	"batch_normalize": batch_normalize,
	"batch_dedupe": batch_dedupe,
}


def execute(context, func=None, config=None):
	if not func:
		frappe.throw(_("Operation function name is required"))
	if func not in _OPERATIONS:
		frappe.throw(_("Unknown MDM operation: {0}").format(func))

	return _OPERATIONS[func](context, config or {})
