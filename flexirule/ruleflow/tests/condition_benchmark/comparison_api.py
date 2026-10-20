# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PreparedCondition:
	"""Encapsulates a condition prepared by a candidate evaluator."""

	candidate_name: str
	prepared_object: Any
	preparation_time_seconds: float
	metadata: dict = field(default_factory=dict)


@dataclass
class EvaluationResult:
	"""Result of executing a prepared condition against document context."""

	candidate_name: str
	result: bool | None
	execution_time_seconds: float
	error: str | None = None


class BaseConditionCandidate(ABC):
	"""Base interface for condition evaluator candidates."""

	candidate_name: str

	@abstractmethod
	def prepare(
		self, condition_payload: Any, metadata_context: dict | None = None
	) -> PreparedCondition:
		"""Prepare a condition payload for execution.

		Measures preparation time separately from execution time.
		"""
		pass

	@abstractmethod
	def evaluate(
		self,
		prepared_condition: PreparedCondition,
		document_context: Any,
		execution_context: dict | None = None,
	) -> EvaluationResult:
		"""Evaluate an already-prepared condition against document/execution context."""
		pass


class ConditionComparisonHarness:
	"""Internal test harness for comparing condition candidates."""

	def __init__(self, candidates: list[BaseConditionCandidate]):
		self.candidates = {c.candidate_name: c for c in candidates}

	def prepare_all(
		self, condition_payload: Any, metadata_context: dict | None = None
	) -> dict[str, PreparedCondition]:
		"""Prepare the condition using all registered candidates."""
		prepared = {}
		for name, candidate in self.candidates.items():
			prepared[name] = candidate.prepare(condition_payload, metadata_context)
		return prepared

	def evaluate_all(
		self,
		prepared_conditions: dict[str, PreparedCondition],
		document_context: Any,
		execution_context: dict | None = None,
	) -> dict[str, EvaluationResult]:
		"""Evaluate all prepared conditions against document context."""
		results = {}
		for name, candidate in self.candidates.items():
			prep = prepared_conditions.get(name)
			if prep is None:
				continue
			results[name] = candidate.evaluate(prep, document_context, execution_context)
		return results

	def check_semantic_agreement(
		self,
		condition_payload: Any,
		document_context: Any,
		metadata_context: dict | None = None,
		execution_context: dict | None = None,
	) -> dict:
		"""Compare results across candidates and report semantic disagreements."""
		prepared = self.prepare_all(condition_payload, metadata_context)
		eval_results = self.evaluate_all(prepared, document_context, execution_context)

		candidate_outputs = {name: res.result for name, res in eval_results.items() if res.error is None}
		unique_results = set(candidate_outputs.values())

		agrees = len(unique_results) <= 1
		disagreements = []

		if not agrees:
			disagreements.append(
				f"Semantic disagreement detected across candidates: {candidate_outputs}"
			)

		errors = {name: res.error for name, res in eval_results.items() if res.error is not None}

		return {
			"agrees": agrees,
			"candidate_results": candidate_outputs,
			"disagreements": disagreements,
			"errors": errors,
			"prepared": prepared,
			"evaluations": eval_results,
		}
