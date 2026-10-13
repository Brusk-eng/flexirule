# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

"""Public interface contract helpers for callable Rules exposed as Sub-Rules."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

FIELDNAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _get(value: Any, key: str, default=None):
	if isinstance(value, Mapping):
		return value.get(key, default)
	getter = getattr(value, "get", None)
	if callable(getter):
		try:
			return getter(key, default)
		except TypeError:
			pass
	return getattr(value, key, default)


def _truthy_flag(value: Any) -> int:
	if value is True or value == 1:
		return 1
	return 1 if str(value if value is not None else "").strip().lower() in {"1", "true", "yes"} else 0


def _parse_schema(raw: Any, schema_label: str, *, output: bool = False, default_source_kind: str = "manual"):
	"""Parse and normalize a JSON field schema; None means no explicit contract was supplied."""
	declared = raw is not None and raw != ""
	if not declared:
		return None, [], False

	if isinstance(raw, str):
		try:
			raw = json.loads(raw)
		except (TypeError, ValueError):
			return [], [f"{schema_label} must contain valid JSON."], True

	if not isinstance(raw, list):
		return [], [f"{schema_label} must be a JSON array."], True

	errors: list[str] = []
	normalized = []
	for index, field in enumerate(raw, start=1):
		path = f"{schema_label} field {index}"
		if not isinstance(field, Mapping):
			errors.append(f"{path} must be an object.")
			continue

		fieldname = str(field.get("fieldname") or "").strip()
		if not FIELDNAME_PATTERN.fullmatch(fieldname):
			errors.append(f"{path} must have a simple identifier fieldname.")
			continue

		fieldtype = str(field.get("fieldtype") or "Data").strip() or "Data"
		item = dict(field)
		item.pop("mandatory", None)
		item["fieldname"] = fieldname
		item["label"] = str(field.get("label") or fieldname.replace("_", " ").title())
		item["fieldtype"] = fieldtype
		item["reqd"] = _truthy_flag(field.get("reqd", field.get("mandatory", 0)))

		if "children" in field:
			children = field.get("children")
			if not isinstance(children, list):
				errors.append(f"{path}.children must be an array.")
				item.pop("children", None)
			else:
				child_fields = []
				for child_index, child in enumerate(children, start=1):
					child_path = f"{path}.children field {child_index}"
					if not isinstance(child, Mapping):
						errors.append(f"{child_path} must be an object.")
						continue
					child_name = str(child.get("fieldname") or "").strip()
					if not FIELDNAME_PATTERN.fullmatch(child_name):
						errors.append(f"{child_path} must have a simple identifier fieldname.")
						continue
					child_item = dict(child)
					child_item.pop("mandatory", None)
					child_item["fieldname"] = child_name
					child_item["label"] = str(child.get("label") or child_name.replace("_", " ").title())
					child_item["fieldtype"] = str(child.get("fieldtype") or "Data").strip() or "Data"
					child_item["reqd"] = _truthy_flag(child.get("reqd", child.get("mandatory", 0)))
					if output:
						source = child.get("source")
						source = dict(source) if isinstance(source, Mapping) else {}
						source["kind"] = (
							str(source.get("kind") or default_source_kind).strip() or default_source_kind
						)
						child_item["source"] = source
					child_fields.append(child_item)
				item["children"] = child_fields

		if output:
			source = field.get("source")
			source = dict(source) if isinstance(source, Mapping) else {}
			source["kind"] = str(source.get("kind") or default_source_kind).strip() or default_source_kind
			item["source"] = source
		normalized.append(item)

	names = [field["fieldname"] for field in normalized]
	duplicates = sorted({name for name in names if names.count(name) > 1})
	if duplicates:
		errors.append(f"{schema_label} has duplicate fieldnames: {', '.join(duplicates)}.")
	return normalized, errors, True


def _inferred_input_schema(rule_doc) -> list[dict[str, Any]]:
	"""Infer required caller inputs for legacy Rules that have no explicit input schema."""
	try:
		from flexirule.ruleflow.core.validation_service import _get_required_variables_for_rule

		names = _get_required_variables_for_rule(rule_doc)
	except Exception:
		names = []
	return [
		{
			"fieldname": name,
			"label": name.replace("_", " ").title(),
			"fieldtype": "Data",
			"reqd": 1,
			"source": {"kind": "inferred_input"},
		}
		for name in names
		if FIELDNAME_PATTERN.fullmatch(str(name or ""))
	]


def _parse_list(value) -> list:
	if isinstance(value, list):
		return value
	if isinstance(value, str) and value.strip():
		try:
			parsed = json.loads(value)
		except (TypeError, ValueError):
			return []
		return parsed if isinstance(parsed, list) else []
	return []


def _return_type_fieldtype(return_type: str | None) -> str:
	if return_type == "Yes / No":
		return "Check"
	if return_type in {"List of Records", "List of Values"}:
		return "Table"
	return "Data"


def _inferred_output_schema(rule_doc) -> list[dict[str, Any]]:
	"""Infer the Sub-Rule's visible result roots from values written by its actions."""
	actions = list(_get(rule_doc, "actions", []) or [])
	outputs: list[dict[str, Any]] = []
	seen: set[str] = set()
	rule_name = _get(rule_doc, "name") or _get(rule_doc, "rule_name") or ""

	def add_output(fieldname, label=None, fieldtype="Data", source=None, children=None, return_type=None):
		name = str(fieldname or "").strip()
		if not FIELDNAME_PATTERN.fullmatch(name) or name in seen:
			return
		seen.add(name)
		item: dict[str, Any] = {
			"fieldname": name,
			"label": str(label or name.replace("_", " ").title()),
			"fieldtype": fieldtype or "Data",
			"reqd": 0,
			"source": {
				"kind": "sub_rule_output",
				"fieldname": name,
				"rule": rule_name,
				**(source or {}),
			},
		}
		if children:
			item["children"] = children
		if return_type:
			item["return_type"] = return_type
		outputs.append(item)

	try:
		from flexirule.ruleflow.core.validation_service import _build_operation_metadata

		operation_metadata = _build_operation_metadata(actions)
	except Exception:
		operation_metadata = {}

	for action in actions:
		action_type = _get(action, "action_type") or ""
		action_id = _get(action, "action_id") or _get(action, "name")
		action_label = _get(action, "action_label") or action_id
		return_variable = str(_get(action, "return_variable") or "").strip()
		return_type = _get(action, "return_type")
		children = []
		raw_children = _parse_list(_get(action, "resolved_output_schema"))
		if raw_children:
			children, _child_errors, _ = _parse_schema(
				raw_children,
				f"{action_label} output schema",
				output=True,
				default_source_kind="sub_rule_output",
			)

		if return_variable:
			add_output(
				return_variable,
				label=action_label or return_variable,
				fieldtype=_return_type_fieldtype(return_type),
				source={"action_id": action_id, "action_type": action_type},
				children=children,
				return_type=return_type,
			)

		if action_type == "Process":
			op_key = f"{_get(action, 'process_name') or ''}:{_get(action, 'operation') or ''}"
			op_meta = operation_metadata.get(op_key, {})
			for definition in _parse_list(op_meta.get("writes_vars")):
				if isinstance(definition, str):
					name, label, fieldtype = definition, definition, "Data"
				elif isinstance(definition, Mapping):
					name = str(definition.get("fieldname") or definition.get("name") or "").strip()
					label = str(definition.get("label") or name)
					fieldtype = str(definition.get("fieldtype") or definition.get("type") or "Data")
				else:
					continue
				add_output(
					name,
					label=label,
					fieldtype=fieldtype,
					source={
						"action_id": action_id,
						"action_type": action_type,
						"process": _get(action, "process_name"),
					},
				)

		if action_type == "Assignment":
			for assignment in _parse_list(_get(action, "config")):
				if not isinstance(assignment, Mapping):
					continue
				target = str(assignment.get("target") or "").strip()
				if not target.startswith("vars."):
					continue
				root = target[5:].split(".", 1)[0]
				add_output(
					root,
					label=root.replace("_", " ").title(),
					source={"action_id": action_id, "action_type": action_type},
				)

	return outputs


def get_sub_rule_contract(rule_doc) -> dict[str, Any]:
	"""Return the public schema for a callable Rule, inferring a legacy contract where absent."""
	raw_inputs = _get(rule_doc, "input_schema")
	raw_outputs = _get(rule_doc, "output_schema")
	input_schema, input_errors, input_declared = _parse_schema(raw_inputs, "Input Schema", output=False)
	output_schema, output_errors, output_declared = _parse_schema(
		raw_outputs, "Output Schema", output=True, default_source_kind="manual"
	)

	inferred_inputs = _inferred_input_schema(rule_doc)
	inferred_outputs = _inferred_output_schema(rule_doc)
	if not input_declared:
		input_schema = inferred_inputs
	if not output_declared:
		output_schema = inferred_outputs

	errors = [*input_errors, *output_errors]
	if input_declared:
		declared_names = {field["fieldname"] for field in input_schema or []}
		required_names = {field["fieldname"] for field in inferred_inputs}
		undeclared = sorted(required_names - declared_names)
		if undeclared:
			errors.append(
				"Input Schema does not declare variables required by this Rule: "
				+ ", ".join(undeclared)
				+ "."
			)

	if output_declared:
		declared_names = {field["fieldname"] for field in output_schema or []}
		produced_names = {field["fieldname"] for field in inferred_outputs}
		unproduced = sorted(declared_names - produced_names)
		if unproduced:
			errors.append(
				"Output Schema declares fields not produced by this Rule: " + ", ".join(unproduced) + "."
			)

	return {
		"contract_version": 1,
		"rule_name": _get(rule_doc, "name") or _get(rule_doc, "rule_name"),
		"input_schema": input_schema or [],
		"output_schema": output_schema or [],
		"input_schema_declared": input_declared,
		"output_schema_declared": output_declared,
		"input_schema_source": "declared" if input_declared else "inferred",
		"output_schema_source": "declared" if output_declared else "inferred",
		"valid": not errors,
		"errors": errors,
	}


def validate_sub_rule_contract(rule_doc) -> list[str]:
	"""Validate a Rule's public contract if the Rule is exposed as a callable Sub-Rule."""
	trigger_type = _get(rule_doc, "trigger_type")
	exposed = _truthy_flag(_get(rule_doc, "exposed_as_subrule"))
	if trigger_type != "Callable Event" or not exposed:
		return []
	return list(get_sub_rule_contract(rule_doc).get("errors") or [])
