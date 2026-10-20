# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

import operator
import time
from collections.abc import Callable
from typing import Any, ClassVar, Optional

import frappe

from flexirule.ruleflow.core.condition_payload import parse_condition_payload
from flexirule.ruleflow.core.evaluator import check_link_match
from flexirule.ruleflow.tests.condition_benchmark.candidate_approach_b import (
	OPERATOR_ALIAS_MAP,
	UNARY_LEAF_OPERATORS,
)
from flexirule.ruleflow.tests.condition_benchmark.comparison_api import (
	BaseConditionCandidate,
	EvaluationResult,
	PreparedCondition,
)
from flexirule.ruleflow.utils.field_resolver import FieldResolver


class ApproachCCandidate(BaseConditionCandidate):
	"""Approach C: Direct Normalized JSON Tree Evaluator.

	Evaluates normalized JSON condition trees directly at runtime without pre-building
	an intermediate AST plan object. Resolves field references, operands, and operators
	by walking the JSON dict structure directly.
	"""

	candidate_name = "Approach C (Direct JSON Tree Evaluator)"

	OPERATOR_MAP: ClassVar[dict[str, Callable[[Any, Any], bool]]] = {
		"==": operator.eq,
		"!=": operator.ne,
		">": operator.gt,
		"<": operator.lt,
		">=": operator.ge,
		"<=": operator.le,
		"in": lambda a, b: a in b if b is not None else False,
		"not in": lambda a, b: a not in b if b is not None else True,
		"contains": lambda a, b: b in str(a) if a is not None else False,
		"not_contains": lambda a, b: b not in str(a) if a is not None else True,
		"is_set": lambda a, b: a is not None and a != "",
		"is_not_set": lambda a, b: a is None or a == "",
		"is_empty": lambda a, b: (
			a is None
			or a == ""
			or (isinstance(a, str) and not a.strip())
			or (isinstance(a, list | tuple | dict | set) and len(a) == 0)
		),
		"is_not_empty": lambda a, b: (
			not (
				a is None
				or a == ""
				or (isinstance(a, str) and not a.strip())
				or (isinstance(a, list | tuple | dict | set) and len(a) == 0)
			)
		),
	}

	def prepare(self, condition_payload: Any, metadata_context: dict | None = None) -> PreparedCondition:
		start_time = time.perf_counter()
		parsed = parse_condition_payload(condition_payload)

		if parsed is None:
			tree = None
		elif isinstance(parsed, str):
			raise ValueError("Approach C requires structured JSON condition tree")
		elif isinstance(parsed, list):
			tree = {"op": "and", "conditions": parsed}
		elif isinstance(parsed, dict):
			tree = parsed
		else:
			raise ValueError(f"Unsupported condition payload type: {type(parsed).__name__}")

		prep_time = time.perf_counter() - start_time
		return PreparedCondition(
			candidate_name=self.candidate_name,
			prepared_object=tree,
			preparation_time_seconds=prep_time,
		)

	def evaluate(
		self,
		prepared_condition: PreparedCondition,
		document_context: Any,
		execution_context: dict | None = None,
	) -> EvaluationResult:
		tree = prepared_condition.prepared_object
		if tree is None:
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=True,
				execution_time_seconds=0.0,
			)

		doc = document_context
		row = None
		if isinstance(document_context, dict) and "doc" in document_context:
			doc = document_context.get("doc")
			row = document_context.get("row")

		start_time = time.perf_counter()
		try:
			res = self._evaluate_node(tree, doc, row, execution_context or {})
			exec_time = time.perf_counter() - start_time
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=bool(res),
				execution_time_seconds=exec_time,
			)
		except Exception as exc:
			exec_time = time.perf_counter() - start_time
			return EvaluationResult(
				candidate_name=self.candidate_name,
				result=None,
				execution_time_seconds=exec_time,
				error=str(exc),
			)

	def _evaluate_node(
		self, node: dict, doc: Any, row: Any = None, extra_context: dict | None = None
	) -> bool:
		if not isinstance(node, dict):
			return True

		# 1. Collection Node
		if "collection" in node or (node.get("op") in {"any", "all", "none"} and "where" in node):
			collection_path = str(node.get("collection") or "")
			if collection_path.startswith(("doc.", "row.")):
				collection_path = collection_path.split(".", 1)[1]

			logic = str(node.get("op", "any")).lower()
			alias = str(node.get("alias", "row"))
			where_node = node.get("where", {})

			rows = FieldResolver.resolve(doc, collection_path)
			if not isinstance(rows, list):
				return False

			ctx = dict(extra_context or {})

			if logic == "any":
				for r in rows:
					ctx[alias] = r
					if self._evaluate_node(where_node, doc, r, ctx):
						return True
				return False
			elif logic == "all":
				if not rows:
					return True
				for r in rows:
					ctx[alias] = r
					if not self._evaluate_node(where_node, doc, r, ctx):
						return False
				return True
			elif logic == "none":
				for r in rows:
					ctx[alias] = r
					if self._evaluate_node(where_node, doc, r, ctx):
						return False
				return True
			return False

		# 2. Group Node
		if "conditions" in node:
			conditions_list = node.get("conditions")
			if not isinstance(conditions_list, list):
				return True

			op_raw = str(node.get("op") or node.get("logical_operator") or "and").lower()
			if not conditions_list:
				return True if op_raw == "and" else False

			if op_raw == "or":
				for child in conditions_list:
					if self._evaluate_node(child, doc, row, extra_context):
						return True
				return False
			else:  # "and"
				for child in conditions_list:
					if not self._evaluate_node(child, doc, row, extra_context):
						return False
				return True

		# 3. Leaf Condition Node
		if "left" in node:
			left_data = node.get("left")
			left_val = self._resolve_operand(left_data, doc, row, extra_context)

			op_raw = str(node.get("op", "=="))
			op_norm = OPERATOR_ALIAS_MAP.get(op_raw) or OPERATOR_ALIAS_MAP.get(op_raw.lower(), "==")

			if op_norm in ["is_set", "is_not_set", "is_empty", "is_not_empty"]:
				return self.OPERATOR_MAP[op_norm](left_val, None)

			if op_norm == "has_changed":
				old_doc = getattr(doc, "_doc_before_save", None) or (
					doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
				)
				if old_doc is not None:
					old_val = self._resolve_operand(left_data, old_doc, row, extra_context)
					return left_val != old_val
				return bool(left_val is not None and left_val != "")

			if op_norm == "is_submittable":
				if not left_val:
					return False
				dt = getattr(left_val, "doctype", left_val) if not isinstance(left_val, str) else left_val
				meta = frappe.get_meta(dt) if dt else None
				return bool(getattr(meta, "is_submittable", 0))

			right_data = node.get("right")
			right_val = (
				self._resolve_operand(right_data, doc, row, extra_context) if right_data is not None else None
			)

			if op_norm == "has_field":
				if not left_val or not right_val:
					return False
				dt = getattr(left_val, "doctype", left_val) if not isinstance(left_val, str) else left_val
				meta = frappe.get_meta(dt) if dt else None
				return bool(meta.has_field(str(right_val))) if meta else False

			if isinstance(right_val, list | tuple) and len(right_val) == 2 and isinstance(right_val[0], str):
				is_link_tuple = False
				if op_norm in ["==", "!="]:
					is_link_tuple = True
				elif op_norm in ["in", "not in"] and isinstance(right_val[1], list | tuple):
					is_link_tuple = True

				if is_link_tuple:
					return check_link_match(left_val, right_val, op_norm)

			if op_norm in {"length_eq", "length_gt", "length_gte", "length_lt", "length_lte"}:
				length = 0
				if left_val is not None:
					length = (
						len(left_val.strip())
						if isinstance(left_val, str)
						else len(left_val)
						if hasattr(left_val, "__len__")
						else 0
					)
				target_len = int(right_val) if right_val is not None else 0
				if op_norm == "length_eq":
					return length == target_len
				if op_norm == "length_gt":
					return length > target_len
				if op_norm == "length_gte":
					return length >= target_len
				if op_norm == "length_lt":
					return length < target_len
				if op_norm == "length_lte":
					return length <= target_len

			op_func = self.OPERATOR_MAP.get(op_norm)
			if not op_func:
				return False

			return op_func(left_val, right_val)

		return True

	def _resolve_operand(
		self, operand_data: Any, doc: Any, row: Any = None, extra_context: dict | None = None
	) -> Any:
		if not isinstance(operand_data, dict):
			return operand_data

		if "ref" in operand_data:
			ref_path = str(operand_data["ref"] or "").strip()
			if not ref_path:
				return None

			parts = ref_path.split(".", 1)
			scope = parts[0]
			subpath = parts[1] if len(parts) > 1 else ""

			target = doc
			if scope in ["row", "item"]:
				target = row if row is not None else doc
			elif scope == "old_doc":
				if hasattr(doc, "_doc_before_save") and doc._doc_before_save:
					target = doc._doc_before_save
				elif hasattr(doc, "get_doc_before_save"):
					target = doc.get_doc_before_save()
				else:
					target = None
			elif extra_context and scope in extra_context:
				target = extra_context[scope]

			if target is None:
				return None

			if not subpath:
				return target

			return FieldResolver.resolve(target, subpath)

		if "value" in operand_data:
			val = operand_data["value"]
			if isinstance(val, dict) and "mode" in val:
				mode = (val.get("mode") or "static").strip().lower()
				if mode in {"static", "link", "dynamic_link"}:
					return val.get("value")
				if mode == "variable":
					path = val.get("path") or val.get("value") or ""
					return FieldResolver.resolve(row or doc, path) if path else None
			return val

		return None
