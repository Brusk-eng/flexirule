# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

import operator
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar, Optional, Union

import frappe

from flexirule.ruleflow.core.condition_payload import parse_condition_payload
from flexirule.ruleflow.core.evaluator import check_link_match
from flexirule.ruleflow.tests.condition_benchmark.comparison_api import (
	BaseConditionCandidate,
	EvaluationResult,
	PreparedCondition,
)
from flexirule.ruleflow.utils.field_resolver import FieldResolver

SUPPORTED_LOGICAL_OPERATORS = {"and", "or"}
SUPPORTED_COLLECTION_LOGIC = {"any", "all", "none"}
SUPPORTED_LEAF_OPERATORS = {
	"==",
	"!=",
	">",
	"<",
	">=",
	"<=",
	"in",
	"not in",
	"not_in",
	"contains",
	"not_contains",
	"is_set",
	"is_not_set",
	"is_empty",
	"is_not_empty",
	"is_submittable",
	"has_field",
	"length_eq",
	"length_gt",
	"length_gte",
	"length_lt",
	"length_lte",
	"has_changed",
}
DEFAULT_ALLOWED_SCOPES = {
	"doc",
	"old_doc",
	"row",
	"item",
	"vars",
	"caller",
	"rule",
	"doctype",
}


# --- AST / Plan Data Model ---
class OperandResolver(ABC):
	"""Abstract base class for plan operand resolvers."""

	@abstractmethod
	def resolve_value(self, doc: Any, row: Any = None, extra_context: dict | None = None) -> Any:
		pass


@dataclass
class RefOperand(OperandResolver):
	"""Resolves a scope path reference like 'doc.status' or 'row.qty'."""

	scope: str
	subpath: str

	def resolve_value(self, doc: Any, row: Any = None, extra_context: dict | None = None) -> Any:
		target = doc
		if self.scope == "row" or self.scope == "item":
			target = row if row is not None else doc
		elif self.scope == "old_doc":
			if hasattr(doc, "_doc_before_save") and doc._doc_before_save:
				target = doc._doc_before_save
			elif hasattr(doc, "get_doc_before_save"):
				target = doc.get_doc_before_save()
			else:
				target = None
		elif extra_context and self.scope in extra_context:
			target = extra_context[self.scope]

		if target is None:
			return None

		if not self.subpath:
			return target

		return FieldResolver.resolve(target, self.subpath)


@dataclass
class LiteralOperand(OperandResolver):
	"""Resolves a static literal value or static FlexValue payload."""

	value: Any

	def resolve_value(self, doc: Any, row: Any = None, extra_context: dict | None = None) -> Any:
		if isinstance(self.value, dict) and "mode" in self.value:
			mode = (self.value.get("mode") or "static").strip().lower()
			if mode in {"static", "link", "dynamic_link"}:
				return self.value.get("value")
			if mode == "variable":
				path = self.value.get("path") or self.value.get("value") or ""
				return FieldResolver.resolve(row or doc, path) if path else None

		return self.value


class PlanNode(ABC):
	"""Abstract base class for condition plan nodes."""

	@abstractmethod
	def evaluate(self, doc: Any, row: Any = None, extra_context: dict | None = None) -> bool:
		pass


@dataclass
class GroupPlanNode(PlanNode):
	"""Plan node for logical AND / OR groups."""

	op: str  # "and" or "or"
	conditions: list[PlanNode]

	def evaluate(self, doc: Any, row: Any = None, extra_context: dict | None = None) -> bool:
		op_lower = self.op.lower()
		if not self.conditions:
			# Empty AND group -> True (logical identity); Empty OR group -> False
			return True if op_lower == "and" else False

		if op_lower == "or":
			for child in self.conditions:
				if child.evaluate(doc, row, extra_context):
					return True
			return False
		else:  # "and"
			for child in self.conditions:
				if not child.evaluate(doc, row, extra_context):
					return False
			return True


@dataclass
class LeafPlanNode(PlanNode):
	"""Plan node for single leaf field comparison."""

	left: OperandResolver
	op: str
	right: OperandResolver | None

	OPERATOR_MAP: ClassVar[dict[str, Callable[[Any, Any], bool]]] = {
		"==": operator.eq,
		"!=": operator.ne,
		">": operator.gt,
		"<": operator.lt,
		">=": operator.ge,
		"<=": operator.le,
		"in": lambda a, b: a in b if b is not None else False,
		"not in": lambda a, b: a not in b if b is not None else True,
		"not_in": lambda a, b: a not in b if b is not None else True,
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
		"has_changed": lambda a, b: True,  # Deprecated operator: passes unconditionally
	}

	def evaluate(self, doc: Any, row: Any = None, extra_context: dict | None = None) -> bool:
		left_val = self.left.resolve_value(doc, row, extra_context) if self.left else None

		if self.op in ["is_set", "is_not_set", "is_empty", "is_not_empty", "has_changed"]:
			return self.OPERATOR_MAP[self.op](left_val, None)

		if self.op == "is_submittable":
			if not left_val:
				return False
			dt = getattr(left_val, "doctype", left_val) if not isinstance(left_val, str) else left_val
			meta = frappe.get_meta(dt) if dt else None
			return bool(getattr(meta, "is_submittable", 0))

		right_val = self.right.resolve_value(doc, row, extra_context) if self.right else None

		if self.op == "has_field":
			if not left_val or not right_val:
				return False
			dt = getattr(left_val, "doctype", left_val) if not isinstance(left_val, str) else left_val
			meta = frappe.get_meta(dt) if dt else None
			return bool(meta.has_field(str(right_val))) if meta else False

		# Link / Dynamic Link Tuple handling
		if isinstance(right_val, list | tuple) and len(right_val) == 2 and isinstance(right_val[0], str):
			is_link_tuple = False
			if self.op in ["==", "!="]:
				is_link_tuple = True
			elif self.op in ["in", "not_in", "not in"] and isinstance(right_val[1], list | tuple):
				is_link_tuple = True

			if is_link_tuple:
				return check_link_match(left_val, right_val, self.op)

		if self.op in {"length_eq", "length_gt", "length_gte", "length_lt", "length_lte"}:
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
			if self.op == "length_eq":
				return length == target_len
			if self.op == "length_gt":
				return length > target_len
			if self.op == "length_gte":
				return length >= target_len
			if self.op == "length_lt":
				return length < target_len
			if self.op == "length_lte":
				return length <= target_len

		op_func = self.OPERATOR_MAP.get(self.op) or self.OPERATOR_MAP.get(self.op.replace(" ", "_"))
		if not op_func:
			return False

		return op_func(left_val, right_val)


@dataclass
class CollectionPlanNode(PlanNode):
	"""Plan node for collection logic ('any', 'all', 'none') over child rows."""

	collection_path: str
	logic: str  # "any", "all", "none"
	alias: str
	where: PlanNode

	def evaluate(self, doc: Any, row: Any = None, extra_context: dict | None = None) -> bool:
		path = self.collection_path
		if path.startswith(("doc.", "row.")):
			path = path.split(".", 1)[1]
		rows = FieldResolver.resolve(doc, path)
		if not isinstance(rows, list):
			return False

		ctx = dict(extra_context or {})

		if self.logic == "any":
			for r in rows:
				ctx[self.alias] = r
				if self.where.evaluate(doc, r, ctx):
					return True
			return False
		elif self.logic == "all":
			if not rows:
				return True
			for r in rows:
				ctx[self.alias] = r
				if not self.where.evaluate(doc, r, ctx):
					return False
			return True
		elif self.logic == "none":
			for r in rows:
				ctx[self.alias] = r
				if self.where.evaluate(doc, r, ctx):
					return False
			return True

		return False


@dataclass
class ConditionExecutionPlan:
	"""Compiled and normalized execution plan for Approach B."""

	root_node: PlanNode | None


# --- Plan Builder ---
class ExecutionPlanBuilder:
	"""Validates and builds a typed ConditionExecutionPlan from JSON payloads."""

	def build_plan(self, condition_payload: Any) -> ConditionExecutionPlan:
		parsed = parse_condition_payload(condition_payload)
		if parsed is None:
			return ConditionExecutionPlan(root_node=None)

		if isinstance(parsed, str):
			raise ValueError("Approach B execution plan requires structured JSON condition tree")

		if isinstance(parsed, list):
			tree = {"op": "and", "conditions": parsed}
		elif isinstance(parsed, dict):
			tree = parsed
		else:
			raise ValueError(f"Unsupported payload type: {type(parsed).__name__}")

		root = self._build_node(tree, allowed_scopes=set(DEFAULT_ALLOWED_SCOPES))
		return ConditionExecutionPlan(root_node=root)

	def _build_node(self, node: dict, allowed_scopes: set[str]) -> PlanNode:
		if not isinstance(node, dict):
			raise ValueError(f"Invalid condition node shape: expected dict, got {type(node).__name__}")

		# 1. Collection Node
		if "collection" in node or (node.get("op") in SUPPORTED_COLLECTION_LOGIC and "where" in node):
			collection_path = node.get("collection")
			if not collection_path or not isinstance(collection_path, str) or not collection_path.strip():
				raise ValueError(
					"Collection condition requires a non-empty 'collection' reference (e.g. 'doc.items')"
				)

			logic = (node.get("op") or "any").lower()
			if logic not in SUPPORTED_COLLECTION_LOGIC:
				raise ValueError(f"Unsupported collection logic operator: '{node.get('op')}'")

			alias = node.get("alias") or "row"
			where_payload = node.get("where")
			if not where_payload or not isinstance(where_payload, dict):
				raise ValueError("Collection condition requires a valid dict 'where' clause")

			# Push collection alias to allowed scopes for child 'where' tree
			child_scopes = set(allowed_scopes)
			child_scopes.add(alias)

			where_node = self._build_node(where_payload, allowed_scopes=child_scopes)
			return CollectionPlanNode(
				collection_path=collection_path, logic=logic, alias=alias, where=where_node
			)

		# 2. Group Node
		if "conditions" in node:
			conditions_list = node.get("conditions")
			if not isinstance(conditions_list, list):
				raise ValueError("Group node 'conditions' field must be a list")

			op_raw = node.get("op") or node.get("logical_operator") or "and"
			if not isinstance(op_raw, str):
				raise ValueError("Logical operator must be a string")

			op = op_raw.lower()
			if op not in SUPPORTED_LOGICAL_OPERATORS:
				raise ValueError(f"Unsupported logical operator: '{op_raw}'")

			children = []
			for idx, child in enumerate(conditions_list):
				if not isinstance(child, dict):
					raise ValueError(
						f"Invalid child condition node at index {idx}: expected dict, got {type(child).__name__}"
					)
				children.append(self._build_node(child, allowed_scopes=allowed_scopes))

			return GroupPlanNode(op=op, conditions=children)

		# 3. Leaf Condition Node
		if "left" in node:
			left_data = node.get("left")
			if left_data is None:
				raise ValueError("Leaf condition node requires a non-null 'left' operand")

			left_op = self._build_operand(left_data, allowed_scopes=allowed_scopes)

			op_raw = node.get("op", "==")
			if not isinstance(op_raw, str):
				raise ValueError("Comparison operator must be a string")

			op = op_raw.lower()
			if op_raw not in SUPPORTED_LEAF_OPERATORS and op not in SUPPORTED_LEAF_OPERATORS:
				raise ValueError(f"Unsupported condition comparison operator: '{op_raw}'")

			right_op = None
			if "right" in node:
				right_op = self._build_operand(node.get("right"), allowed_scopes=allowed_scopes)

			return LeafPlanNode(left=left_op, op=op_raw, right=right_op)

		raise ValueError(f"Malformed or unrecognized condition node payload: {node}")

	def _build_operand(self, operand_data: Any, allowed_scopes: set[str]) -> OperandResolver:
		if not isinstance(operand_data, dict):
			return LiteralOperand(value=operand_data)

		if "ref" in operand_data:
			ref_path = str(operand_data["ref"] or "").strip()
			if not ref_path:
				raise ValueError("Reference operand contains an empty 'ref' path")

			parts = ref_path.split(".", 1)
			scope = parts[0]
			subpath = parts[1] if len(parts) > 1 else ""

			if scope not in allowed_scopes:
				raise ValueError(
					f"Invalid operand scope: '{scope}'. Allowed scopes: {sorted(allowed_scopes)}"
				)

			return RefOperand(scope=scope, subpath=subpath)

		if "value" in operand_data:
			return LiteralOperand(value=operand_data["value"])

		return LiteralOperand(value=None)


# --- Candidate Adapter ---
class ApproachBCandidate(BaseConditionCandidate):
	"""Approach B: Prebuilt normalized execution plan evaluated via typed plan evaluator.

	Prepares and validates the condition plan before the timing loop.
	Runtime execution evaluates the prebuilt plan directly against document context.
	"""

	candidate_name = "Approach B (Normalized Execution Plan)"

	def __init__(self):
		self.builder = ExecutionPlanBuilder()

	def prepare(self, condition_payload: Any, metadata_context: dict | None = None) -> PreparedCondition:
		start_time = time.perf_counter()
		plan = self.builder.build_plan(condition_payload)
		prep_time = time.perf_counter() - start_time

		return PreparedCondition(
			candidate_name=self.candidate_name,
			prepared_object=plan,
			preparation_time_seconds=prep_time,
			metadata={"plan_node_type": type(plan.root_node).__name__ if plan.root_node else "None"},
		)

	def evaluate(
		self,
		prepared_condition: PreparedCondition,
		document_context: Any,
		execution_context: dict | None = None,
	) -> EvaluationResult:
		plan: ConditionExecutionPlan = prepared_condition.prepared_object
		if not plan or not plan.root_node:
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
			res = plan.root_node.evaluate(doc, row, execution_context)
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
