# Copyright (c) 2026, Bolton and contributors
# For license information, please see license.txt

"""
Create Docs Action Handler

Modes:
- Create New: Creates a new document with field mappings
- Update Existing: Updates an existing document with field mappings
"""

import json

import frappe
from frappe import _

from flexirule.ruleflow.core.action_handlers import ActionHandler, HandlerRegistry


class CreateDocHandler(ActionHandler):
	"""Handler for creating or updating documents."""

	action_type = "Create Docs"

	def execute(self, action, context, engine):
		"""Execute document creation/update based on mode."""
		mode = action.operation
		reference_doctype = action.reference_doctype
		config = self._parse_config(action.config)
		ignore_permissions = bool(action.skip_permissions)
		is_async = bool(action.is_async)

		if not mode:
			frappe.throw(_("Operation/Mode is required for Create Docs action"))

		if not reference_doctype:
			frappe.throw(_("Reference DocType is required for Create Docs action"))

		# Dispatch to mode handler
		if mode == "Create New":
			result = self._create_new(
				reference_doctype, config, context, action, ignore_permissions, is_async
			)
		elif mode == "Update Existing":
			result = self._update_existing(
				reference_doctype, config, context, action, ignore_permissions
			)
		else:
			frappe.throw(_("Unknown Create Docs mode: {0}").format(mode))

		# Store result in return variable if specified
		if action.return_variable:
			context.setdefault("vars", {})[action.return_variable] = result

		next_action = action.next_step_if_true
		return result, next_action

	def validate(self, action, context):
		"""Validate Create Docs action configuration."""
		errors = []
		if not action.operation:
			errors.append(_("Operation/Mode is required"))
		if not action.reference_doctype:
			errors.append(_("Reference DocType is required"))

		mode = action.operation
		if mode == "Update Existing" and not action.reference_docname:
			config = self._parse_config(action.config)
			if not config.get("docname_expression"):
				errors.append(
					_(
						"Update Existing mode requires either a Reference Document "
						"or a docname_expression in config"
					)
				)
		return errors

	def _parse_config(self, config_str):
		"""Safely parse config JSON."""
		if not config_str:
			return {}
		if isinstance(config_str, dict):
			return config_str
		try:
			return json.loads(config_str)
		except (json.JSONDecodeError, TypeError):
			return {}

	def _resolve_field_mappings(self, mappings, context):
		"""
		Resolve field mappings from context to target values.

		Mapping format:
		[
		    {"source": "doc.customer", "target": "customer"},
		    {"source": "vars.calculated_total", "target": "grand_total"},
		    {"source": "'Fixed Value'", "target": "status"},
		]
		"""
		resolved = {}
		for mapping in mappings:
			source = mapping.get("source", "")
			target = mapping.get("target", "")
			if not target:
				continue

			try:
				# Resolve source expression
				value = frappe.safe_eval(
					source,
					eval_globals={"frappe": frappe},
					eval_locals=context,
				)
				resolved[target] = value
			except Exception as e:
				frappe.logger().warning(
					f"Failed to resolve field mapping '{source}' -> '{target}': {e}"
				)

		return resolved

	def _create_new(self, reference_doctype, config, context, action, ignore_permissions, is_async):
		"""Create a new document with field mappings."""
		field_mappings = config.get("field_mappings", [])
		static_values = config.get("static_values", {})

		# Build document data
		doc_data = {"doctype": reference_doctype}

		# Apply static values first
		doc_data.update(static_values)

		# Apply dynamic field mappings (overrides static)
		if field_mappings:
			resolved = self._resolve_field_mappings(field_mappings, context)
			doc_data.update(resolved)

		if is_async:
			# Enqueue document creation
			frappe.enqueue(
				"flexirule.ruleflow.core.action_handlers.create_doc._async_create_doc",
				queue="default",
				doc_data=doc_data,
				ignore_permissions=ignore_permissions,
			)
			return {"enqueued": True, "doctype": reference_doctype}

		# Synchronous creation
		new_doc = frappe.get_doc(doc_data)
		new_doc.insert(ignore_permissions=ignore_permissions)

		return new_doc.as_dict()

	def _update_existing(self, reference_doctype, config, context, action, ignore_permissions):
		"""Update an existing document with field mappings."""
		docname = action.reference_docname or config.get("docname")

		# Support dynamic docname from expression
		if not docname and config.get("docname_expression"):
			docname = frappe.safe_eval(
				config["docname_expression"],
				eval_globals={"frappe": frappe},
				eval_locals=context,
			)

		if not docname:
			frappe.throw(_("No document name specified for Update Existing"))

		doc = frappe.get_doc(reference_doctype, docname)
		if not ignore_permissions:
			doc.check_permission("write")

		# Apply field mappings
		field_mappings = config.get("field_mappings", [])
		static_values = config.get("static_values", {})

		# Apply static values
		for field, value in static_values.items():
			doc.set(field, value)

		# Apply dynamic field mappings
		if field_mappings:
			resolved = self._resolve_field_mappings(field_mappings, context)
			for field, value in resolved.items():
				doc.set(field, value)

		doc.save(ignore_permissions=ignore_permissions)

		return doc.as_dict()


def _async_create_doc(doc_data, ignore_permissions=False):
	"""Background job for async document creation."""
	new_doc = frappe.get_doc(doc_data)
	new_doc.insert(ignore_permissions=ignore_permissions)
	if not frappe.flags.in_test:
		frappe.db.commit()


# Register handler
HandlerRegistry.register(CreateDocHandler())
