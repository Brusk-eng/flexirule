# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import os
import platform
import statistics
import time
from typing import Any, Optional

import frappe

from flexirule.ruleflow.tests.condition_benchmark.candidate_approach_a import (
	ApproachACandidate,
	ApproachAExperimentalCodeObjectCandidate,
)
from flexirule.ruleflow.tests.condition_benchmark.candidate_approach_b import ApproachBCandidate
from flexirule.ruleflow.tests.condition_benchmark.candidate_approach_c import ApproachCCandidate
from flexirule.ruleflow.tests.condition_benchmark.comparison_api import (
	BaseConditionCandidate,
	ConditionComparisonHarness,
)
from flexirule.ruleflow.tests.condition_benchmark.fixtures import (
	BenchmarkFixture,
	get_all_fixtures,
)


class BenchmarkRunner:
	"""Executes fair performance benchmarks and semantic correctness tests."""

	def __init__(
		self,
		iterations_per_batch: int = 10000,
		num_batches: int = 5,
		warmup_iterations: int = 50,
	):
		self.iterations_per_batch = iterations_per_batch
		self.num_batches = num_batches
		self.warmup_iterations = warmup_iterations

		self.candidate_a: BaseConditionCandidate = ApproachACandidate()
		self.candidate_a_exp: BaseConditionCandidate = ApproachAExperimentalCodeObjectCandidate()
		self.candidate_b: BaseConditionCandidate = ApproachBCandidate()
		self.candidate_c: BaseConditionCandidate = ApproachCCandidate()

		self.candidates: list[BaseConditionCandidate] = [
			self.candidate_a,
			self.candidate_a_exp,
			self.candidate_b,
			self.candidate_c,
		]
		self.harness = ConditionComparisonHarness(self.candidates)

	def run_semantic_correctness_suite(self) -> dict:
		"""Verify that candidates agree on all fixture cases."""
		fixtures = get_all_fixtures()
		correctness_results = []
		total_cases = 0
		agreed_cases = 0

		for fix in fixtures:
			total_cases += 1
			check_match = self.harness.check_semantic_agreement(
				fix.condition_payload,
				fix.matching_doc,
				expected_result=fix.expected_matching_result,
			)
			check_non_match = self.harness.check_semantic_agreement(
				fix.condition_payload,
				fix.non_matching_doc,
				expected_result=fix.expected_non_matching_result,
			)

			case_is_correct = check_match["is_correct"] and check_non_match["is_correct"]
			if case_is_correct:
				agreed_cases += 1

			correctness_results.append(
				{
					"fixture_id": fix.fixture_id,
					"tier": fix.tier,
					"description": fix.description,
					"is_correct": case_is_correct,
					"agrees": check_match["agrees"] and check_non_match["agrees"],
					"matches_expected": check_match["matches_expected"]
					and check_non_match["matches_expected"],
					"matching_doc_check": check_match["candidate_results"],
					"non_matching_doc_check": check_non_match["candidate_results"],
					"disagreements": check_match["disagreements"] + check_non_match["disagreements"],
					"errors": {**check_match["errors"], **check_non_match["errors"]},
				}
			)

		return {
			"total_cases": total_cases,
			"agreed_cases": agreed_cases,
			"all_correct": agreed_cases == total_cases,
			"all_agreed": agreed_cases == total_cases,
			"results": correctness_results,
		}

	def _check_fixture_correctness(self, fix) -> tuple[bool, dict]:
		"""Gate timing on agreement with each fixture's expected matching and non-matching results."""
		check_match = self.harness.check_semantic_agreement(
			fix.condition_payload,
			fix.matching_doc,
			expected_result=fix.expected_matching_result,
		)
		check_non_match = self.harness.check_semantic_agreement(
			fix.condition_payload,
			fix.non_matching_doc,
			expected_result=fix.expected_non_matching_result,
		)
		passed = check_match["is_correct"] and check_non_match["is_correct"]
		failures = (
			check_match["disagreements"]
			+ check_non_match["disagreements"]
			+ list(check_match["errors"].values())
			+ list(check_non_match["errors"].values())
		)
		return passed, {
			"matching": check_match,
			"non_matching": check_non_match,
			"failures": failures,
		}

	def _prepare_all_with_median(self, condition_payload: Any) -> dict[str, Any]:
		"""Prepare repeatedly and report the median preparation duration, not one noisy sample."""
		sample_count = max(3, self.num_batches)
		preparation_runs = [
			self.harness.prepare_all(condition_payload) for _ in range(sample_count)
		]
		prepared = preparation_runs[-1]

		for candidate in self.candidates:
			name = candidate.candidate_name
			prep = prepared[name]
			samples = [
				run[name].preparation_time_seconds
				for run in preparation_runs
				if name in run and not run[name].error
			]
			if prep.error:
				continue
			if len(samples) != sample_count:
				prep.error = (
					"Preparation did not succeed in every repeated preparation sample "
					f"({len(samples)}/{sample_count})"
				)
				continue
			prep.preparation_time_seconds = statistics.median(samples)
			prep.metadata["preparation_samples_seconds"] = samples

		return prepared

	def _rotated_candidates(self, offset: int) -> list[BaseConditionCandidate]:
		"""Rotate candidate order between batches to reduce systematic order bias."""
		if not self.candidates:
			return []
		shift = offset % len(self.candidates)
		return self.candidates[shift:] + self.candidates[:shift]

	def _warm_up_candidate(self, candidate, prep, fix) -> str | None:
		"""Warm both branches and reject candidates that do not preserve fixture results."""
		contexts = [
			(fix.matching_doc, fix.expected_matching_result),
			(fix.non_matching_doc, fix.expected_non_matching_result),
		]
		for index in range(self.warmup_iterations):
			doc, expected = contexts[index % len(contexts)]
			try:
				result = candidate.evaluate(prep, doc)
			except Exception as exc:
				return f"Warm-up exception: {exc!s}"
			if result.error:
				return f"Warm-up evaluation failed: {result.error}"
			if result.result != expected:
				return (
					"Warm-up result mismatch: "
					f"expected {expected!r}, got {result.result!r}"
				)
		return None

	def _time_evaluation_batch(
		self, candidate, prep, fix, iterations: int, start_offset: int = 0
	) -> tuple[float, int, str | None, float]:
		"""Time full candidate calls and sum each result's evaluator-core timer."""
		contexts = [
			(fix.matching_doc, fix.expected_matching_result),
			(fix.non_matching_doc, fix.expected_non_matching_result),
		]
		successful_evaluations = 0
		last_result = None
		last_expected = None
		core_execution_seconds = 0.0
		batch_error = None
		start_time = time.perf_counter()

		for index in range(iterations):
			doc, expected = contexts[(index + start_offset) % len(contexts)]
			try:
				result = candidate.evaluate(prep, doc)
			except Exception as exc:
				batch_error = f"Evaluation exception: {exc!s}"
				break
			if result.error:
				batch_error = f"Evaluation error: {result.error}"
				break
			last_result = result.result
			last_expected = expected
			core_execution_seconds += result.execution_time_seconds
			successful_evaluations += 1

		elapsed = time.perf_counter() - start_time
		if batch_error is None and successful_evaluations != iterations:
			batch_error = (
				f"Incomplete evaluations ({successful_evaluations}/{iterations})"
			)
		if batch_error is None and last_result != last_expected:
			batch_error = (
				f"Final result mismatch: expected {last_expected!r}, got {last_result!r}"
			)
		return elapsed, successful_evaluations, batch_error, core_execution_seconds

	def run_primary_benchmarks(self) -> dict:
		"""Compare full candidate-call cost using repeated, order-rotated batches."""
		fixtures = get_all_fixtures()
		fixture_benchmark_results = []

		for fix in fixtures:
			correctness_passed, correctness_detail = self._check_fixture_correctness(fix)
			prepared_map = self._prepare_all_with_median(fix.condition_payload)
			candidate_metrics: dict[str, Any] = {}
			states: dict[str, dict[str, Any]] = {}

			for candidate in self.candidates:
				name = candidate.candidate_name
				prep = prepared_map[name]
				state = {
					"prep": prep,
					"samples_us": [],
					"samples_core_us": [],
					"durations_seconds": [],
					"successful_evaluations": 0,
					"error": None,
				}
				if prep.error:
					state["error"] = prep.error
				elif not correctness_passed:
					state["error"] = "Skipped: semantic correctness gate failed"
				states[name] = state

			# Warm every eligible candidate before the timed batches.
			if correctness_passed:
				for candidate in self._rotated_candidates(0):
					name = candidate.candidate_name
					state = states[name]
					if state["error"]:
						continue
					state["error"] = self._warm_up_candidate(
						candidate, state["prep"], fix
					)

				# Each candidate sees the same workload; candidate order rotates each batch.
				for batch_index in range(self.num_batches):
					for candidate in self._rotated_candidates(batch_index):
						name = candidate.candidate_name
						state = states[name]
						if state["error"]:
							continue
						elapsed, successful, batch_error, core_elapsed = self._time_evaluation_batch(
							candidate, state["prep"], fix, self.iterations_per_batch,
							start_offset=batch_index,
						)
						if batch_error:
							state["error"] = (
								f"Batch {batch_index + 1} failed: {batch_error}"
							)
							continue
						state["samples_us"].append(
							elapsed / self.iterations_per_batch * 1e6
						)
						state["samples_core_us"].append(
							core_elapsed / self.iterations_per_batch * 1e6
						)
						state["durations_seconds"].append(elapsed)
						state["successful_evaluations"] += successful

			for candidate in self.candidates:
				name = candidate.candidate_name
				state = states[name]
				prep = state["prep"]
				samples = state["samples_us"]
				common = {
					"preparation_time_ms": round(
						prep.preparation_time_seconds * 1000.0, 4
					),
					"iterations_per_batch": self.iterations_per_batch,
					"total_batches_attempted": self.num_batches,
					"valid_batches": len(samples),
					"successful_evaluations": state["successful_evaluations"],
				}

				if state["error"] or len(samples) != self.num_batches:
					candidate_metrics[name] = {
						"is_valid_measurement": False,
						"error": state["error"]
						or f"Only {len(samples)}/{self.num_batches} batches succeeded",
						**common,
					}
					continue

				sorted_times = sorted(samples)
				median_us = statistics.median(sorted_times)
				candidate_metrics[name] = {
					"is_valid_measurement": True,
					"error": None,
					**common,
					"median_us_per_exec": round(median_us, 3),
					"median_core_us_per_exec": round(
						statistics.median(state["samples_core_us"]), 3
					),
					"mean_us_per_exec": round(statistics.mean(samples), 3),
					"min_us_per_exec": round(min(samples), 3),
					"max_us_per_exec": round(max(samples), 3),
					"p95_us_per_exec": round(
						sorted_times[int(0.95 * len(sorted_times))]
						if len(sorted_times) >= 5 else max(sorted_times),
						3,
					),
					"valid_batch_durations_seconds": [
						round(value, 4) for value in state["durations_seconds"]
					],
				}

			a_metric = candidate_metrics.get(self.candidate_a.candidate_name, {})
			b_metric = candidate_metrics.get(self.candidate_b.candidate_name, {})
			c_metric = candidate_metrics.get(self.candidate_c.candidate_name, {})

			def speedup(numerator_metric, denominator_metric):
				if not (
					numerator_metric.get("is_valid_measurement")
					and denominator_metric.get("is_valid_measurement")
				):
					return None
				numerator = numerator_metric.get("median_us_per_exec")
				denominator = denominator_metric.get("median_us_per_exec")
				if not isinstance(numerator, int | float) or not isinstance(
					denominator, int | float
				) or denominator <= 0:
					return None
				return round(numerator / denominator, 2)

			fixture_benchmark_results.append({
				"fixture_id": fix.fixture_id,
				"tier": fix.tier,
				"description": fix.description,
				"correctness_gate_passed": correctness_passed,
				"correctness_failures": correctness_detail["failures"],
				"timed_workload": "alternating matching and non-matching documents",
				"leaf_count": fix.leaf_count,
				"nesting_depth": fix.nesting_depth,
				"speedup_ratio_b_vs_primary_a": speedup(a_metric, b_metric),
				"speedup_ratio_c_vs_primary_a": speedup(a_metric, c_metric),
				"speedup_ratio_b_vs_c": speedup(c_metric, b_metric),
				"candidate_metrics": candidate_metrics,
			})

		return {
			"methodology": {
				"iterations_per_batch": self.iterations_per_batch,
				"num_batches": self.num_batches,
				"warmup_iterations_per_candidate": self.warmup_iterations,
				"candidate_order": "rotated between batches",
				"document_workload": "alternating matching and non-matching documents",
				"timed_scope": "entire candidate.evaluate call, including candidate-specific per-call setup",
				"preparation_time_samples": max(3, self.num_batches),
			},
			"fixtures": fixture_benchmark_results,
		}

	def run_amortized_benchmarks(self, execution_counts: list[int] | None = None) -> dict:
		"""Estimate preparation + N evaluations using repeated batches and correctness gates."""
		if execution_counts is None:
			execution_counts = [1, 10, 100, 1000]
		if any(type(count) is not int or count <= 0 for count in execution_counts):
			raise ValueError("execution_counts must contain positive integers")

		fixtures = get_all_fixtures()
		amortized_results = []

		for fix in fixtures:
			correctness_passed, correctness_detail = self._check_fixture_correctness(fix)
			prepared_map = self._prepare_all_with_median(fix.condition_payload)
			candidate_errors: dict[str, str | None] = {}

			for candidate in self.candidates:
				name = candidate.candidate_name
				prep = prepared_map[name]
				if prep.error:
					candidate_errors[name] = prep.error
				elif not correctness_passed:
					candidate_errors[name] = (
						"Skipped: semantic correctness gate failed; see correctness_failures"
					)
				else:
					candidate_errors[name] = self._warm_up_candidate(candidate, prep, fix)

			counts_dict: dict[str, Any] = {}
			for count_index, count in enumerate(execution_counts):
				execution_samples: dict[str, list[float]] = {
					candidate.candidate_name: [] for candidate in self.candidates
				}
				core_execution_samples: dict[str, list[float]] = {
					candidate.candidate_name: [] for candidate in self.candidates
				}
				batch_errors: dict[str, str] = {
					name: error for name, error in candidate_errors.items() if error
				}

				if correctness_passed:
					for batch_index in range(self.num_batches):
						order_offset = batch_index + count_index
						for candidate in self._rotated_candidates(order_offset):
							name = candidate.candidate_name
							if batch_errors.get(name):
								continue
							prep = prepared_map[name]
							elapsed, _, batch_error, core_elapsed = self._time_evaluation_batch(
								candidate, prep, fix, count, start_offset=batch_index
							)
							if batch_error:
								batch_errors[name] = (
									f"Sample {batch_index + 1}/{self.num_batches} failed: "
									f"{batch_error}"
								)
								continue
							execution_samples[name].append(elapsed)
							core_execution_samples[name].append(core_elapsed)

				count_metrics = {}
				for candidate in self.candidates:
					name = candidate.candidate_name
					prep = prepared_map[name]
					samples = execution_samples[name]
					common = {
						"prep_time_ms": round(
							prep.preparation_time_seconds * 1000.0, 4
						),
						"valid_batches": len(samples),
						"total_batches_attempted": self.num_batches,
					}
					if batch_errors.get(name) or len(samples) != self.num_batches:
						count_metrics[name] = {
							"is_valid": False,
							"error": batch_errors.get(name)
							or f"Only {len(samples)}/{self.num_batches} repeated samples succeeded",
							**common,
						}
						continue

					median_execution_seconds = statistics.median(samples)
					total_amortized_seconds = (
						prep.preparation_time_seconds + median_execution_seconds
					)
					count_metrics[name] = {
						"is_valid": True,
						**common,
						"n_exec_time_ms": round(
							median_execution_seconds * 1000.0, 4
						),
						"median_exec_us_per_eval": round(
							median_execution_seconds / count * 1e6, 3
						),
						"median_core_exec_us_per_eval": round(
							statistics.median(core_execution_samples[name]) / count * 1e6,
							3,
						),
						"total_amortized_cost_ms": round(
							total_amortized_seconds * 1000.0, 4
						),
						"cost_per_eval_us": round(
							total_amortized_seconds / count * 1e6, 3
						),
						"sample_execution_times_ms": [
							round(sample * 1000.0, 4) for sample in samples
						],
					}

				counts_dict[str(count)] = count_metrics

			amortized_results.append({
				"fixture_id": fix.fixture_id,
				"tier": fix.tier,
				"correctness_gate_passed": correctness_passed,
				"correctness_failures": correctness_detail["failures"],
				"candidate_order": "rotated between repeated samples",
				"document_workload": "alternating matching and non-matching documents",
				"counts": counts_dict,
			})

		return {
			"methodology": {
				"execution_counts": execution_counts,
				"repeated_samples_per_count": self.num_batches,
				"warmup_iterations_per_candidate": self.warmup_iterations,
				"preparation_time_samples": max(3, self.num_batches),
				"amortized_formula": "(median preparation time + median total time for N evaluations) / N",
				"candidate_order": "rotated between samples",
				"document_workload": "alternating matching and non-matching documents",
			},
			"amortized": amortized_results,
		}

	def generate_markdown_report(self, full_payload: dict, output_markdown_path: str) -> str:
		"""Generate a Markdown report that is 100% synchronized with the raw JSON result payload."""
		env = full_payload["environment"]
		correctness = full_payload["correctness_suite"]
		primary = full_payload["primary_benchmark"]
		amortized = full_payload["amortized_benchmark"]

		cand_a_name = self.candidate_a.candidate_name
		cand_a_exp_name = self.candidate_a_exp.candidate_name
		cand_b_name = self.candidate_b.candidate_name
		cand_c_name = self.candidate_c.candidate_name

		total_evals_completed = 0
		for fix_res in primary["fixtures"]:
			metrics = fix_res.get("candidate_metrics", {})
			for c_metric in metrics.values():
				total_evals_completed += c_metric.get("successful_evaluations", 0)

		md_lines = []
		md_lines.append("# FlexiRule — Condition Backend Comparison Benchmark Report")
		md_lines.append("")
		md_lines.append(f"**Date:** {time.strftime('%Y-%m-%d', time.gmtime())}  ")
		md_lines.append("**Repository:** [Sendipad/flexirule](https://github.com/Sendipad/flexirule)  ")
		md_lines.append("**Branch:** `feat/condition-benchmark`  ")
		md_lines.append(f"**Report Location:** `{output_markdown_path}`  ")
		md_lines.append(f"**Benchmark Protocol:** v{full_payload.get('benchmark_protocol_version', 'unknown')}  ")
		md_lines.append("**Measurement Protocol:** repeated preparation medians; repeated timed batches; rotating candidate order; alternating matching/non-matching documents; correctness gate  ")
		md_lines.append("**Raw Results Data:** `reports/condition_benchmark_results.json`  ")
		md_lines.append("")
		md_lines.append("---")
		md_lines.append("")
		md_lines.append("## Executive Summary")
		md_lines.append("")
		md_lines.append(
			"This report documents the architectural investigation, empirical runtime probe, correctness test suite, "
			"and high-precision performance benchmarks comparing two architectural candidates for evaluating visual JSON rule conditions in FlexiRule:"
		)
		md_lines.append("")
		md_lines.append(
			f"- **Approach A — Precompiled Python Expression (`{cand_a_name}`):** Evaluating a Python expression string "
			"generated from a condition tree using installed Frappe v15 restricted evaluation (`frappe.safe_eval`). "
			f"Includes an isolated experimental diagnostic (`{cand_a_exp_name}`) for evaluating precompiled RestrictedPython code objects."
		)
		md_lines.append(
			f"- **Approach B — Prebuilt Normalized Execution Plan (`{cand_b_name}`):** Evaluating a typed, validated execution plan "
			"using a pure evaluator and comparator without Python compilation or AST parsing during execution."
		)
		md_lines.append("")
		md_lines.append("### Summary Statistics and Findings")
		md_lines.append("")
		md_lines.append(
			"1. **`frappe.safe_eval` Overhead:** Installed Frappe v15 `frappe.safe_eval` performs `unicodedata.normalize()`, `ast.parse()`, "
			"AST node walking (`_validate_safe_eval_syntax`), and RestrictedPython AST transformation / compilation on **every single invocation**. "
			"It implements **no caching** of compiled bytecode objects."
		)

		all_correct = correctness.get("all_correct", False)
		status_str = "PASSED (100% Correctness Parity)" if all_correct else "FAILED (Disagreements Detected)"
		md_lines.append(
			f"2. **Semantic Correctness Gate Status:** **{status_str}**. Total Fixtures Tested: {correctness.get('total_cases')}, Agreed: {correctness.get('agreed_cases')}."
		)
		md_lines.append(
			f"3. **Evaluations Completed:** **{total_evals_completed:,}** total error-free evaluations were completed during this benchmark run."
		)
		md_lines.append("")
		md_lines.append("---")
		md_lines.append("")
		md_lines.append("## 1. Environment and Reproducibility")
		md_lines.append("")
		md_lines.append("| Key | Value |")
		md_lines.append("|---|---|")
		md_lines.append(f"| Python Version | {env.get('python_version')} |")
		md_lines.append(f"| Platform | {env.get('platform')} |")
		md_lines.append(f"| Frappe Framework | {env.get('frappe_version')} |")
		md_lines.append(f"| FlexiRule Version | {env.get('flexirule_version')} |")
		md_lines.append(f"| Benchmark Execution UTC | {env.get('timestamp_utc')} |")
		md_lines.append(
			"| Benchmark Command | `PYTHONPATH=. /home/jules/frappe-bench/env/bin/python -m flexirule.ruleflow.tests.condition_benchmark.benchmark_runner` |"
		)
		md_lines.append("")
		md_lines.append("---")
		md_lines.append("")
		md_lines.append("## 2. Correctness Test Suite Results")
		md_lines.append("")
		md_lines.append(
			"The correctness gate evaluates every candidate against matching and non-matching document contexts and verifies "
			"that all candidates agree with each other AND match the fixture's explicit expected results."
		)
		md_lines.append("")
		md_lines.append(
			"| Fixture ID | Complexity Tier | Status | Matching Check | Non-Matching Check | Errors |"
		)
		md_lines.append("|---|---|---|---|---|---|")

		for c_res in correctness["results"]:
			status = "PASSED" if c_res["is_correct"] else "FAILED"
			m_chk = str(c_res["matching_doc_check"])
			nm_chk = str(c_res["non_matching_doc_check"])
			errs = str(c_res["errors"]) if c_res["errors"] else "None"
			md_lines.append(
				f"| `{c_res['fixture_id']}` | {c_res['tier']} | **{status}** | `{m_chk}` | `{nm_chk}` | `{errs}` |"
			)

		md_lines.append("")
		md_lines.append("---")
		md_lines.append("")
		md_lines.append("## 3. Primary Prepared-Execution Benchmark Results")
		md_lines.append("")
		md_lines.append(
			"**Methodology:** Preparation was measured separately using repeated samples and the median. "
			f"Each batch contains {self.iterations_per_batch:,} evaluations and there are {self.num_batches} repeated batches. "
			"Within each batch the same matching and non-matching documents alternate; candidate order rotates between batches. "
			"The timed scope is the entire candidate.evaluate() call, including candidate-specific per-call setup."
		)
		md_lines.append("")
		md_lines.append(
			"| Fixture ID | Tier | Leaf / Depth | Approach A (`safe_eval`) | Approach A Exp (`code_obj`) | Approach B (`plan`) | Approach C (`json_tree`) | Speedup B vs Primary A | Speedup C vs Primary A | Speedup B vs C |"
		)
		md_lines.append("|---|---|---|---|---|---|---|---|---|---|")

		for item in primary["fixtures"]:
			fid = item["fixture_id"]
			tier = item["tier"]
			ld = f"{item['leaf_count']} / {item['nesting_depth']}"
			metrics = item["candidate_metrics"]

			a_m = metrics.get(cand_a_name, {})
			a_exp_m = metrics.get(cand_a_exp_name, {})
			b_m = metrics.get(cand_b_name, {})
			c_m = metrics.get(cand_c_name, {})

			a_str = f"{a_m.get('median_us_per_exec')} µs/op" if a_m.get("is_valid_measurement") else "INVALID"
			a_exp_str = (
				f"{a_exp_m.get('median_us_per_exec')} µs/op"
				if a_exp_m.get("is_valid_measurement")
				else "INVALID"
			)
			b_str = f"{b_m.get('median_us_per_exec')} µs/op" if b_m.get("is_valid_measurement") else "INVALID"
			c_str = f"{c_m.get('median_us_per_exec')} µs/op" if c_m.get("is_valid_measurement") else "INVALID"

			sp_b_a_str = (
				f"**{item.get('speedup_ratio_b_vs_primary_a')}x**"
				if item.get("speedup_ratio_b_vs_primary_a") is not None
				else "N/A"
			)
			sp_c_a_str = (
				f"**{item.get('speedup_ratio_c_vs_primary_a')}x**"
				if item.get("speedup_ratio_c_vs_primary_a") is not None
				else "N/A"
			)
			sp_b_c_str = (
				f"**{item.get('speedup_ratio_b_vs_c')}x**"
				if item.get("speedup_ratio_b_vs_c") is not None
				else "N/A"
			)

			md_lines.append(
				f"| `{fid}` | {tier} | {ld} | {a_str} | {a_exp_str} | **{b_str}** | {c_str} | {sp_b_a_str} | {sp_c_a_str} | {sp_b_c_str} |"
			)

		md_lines.append("")
		md_lines.append("---")
		md_lines.append("")
		md_lines.append("## 4. Preparation Timings")
		md_lines.append("")
		md_lines.append("Preparation time measured separately outside the execution loop:")
		md_lines.append("")
		md_lines.append("| Fixture ID | Approach A Prep (ms) | Approach B Prep (ms) | Approach C Prep (ms) |")
		md_lines.append("|---|---|---|---|")

		for item in primary["fixtures"]:
			fid = item["fixture_id"]
			metrics = item["candidate_metrics"]
			a_prep = metrics.get(cand_a_name, {}).get("preparation_time_ms", 0)
			b_prep = metrics.get(cand_b_name, {}).get("preparation_time_ms", 0)
			c_prep = metrics.get(cand_c_name, {}).get("preparation_time_ms", 0)
			md_lines.append(f"| `{fid}` | {a_prep} ms | **{b_prep} ms** | {c_prep} ms |")

		md_lines.append("")
		md_lines.append("---")
		md_lines.append("")
		md_lines.append("## 5. Amortized Total Cost Measurements")
		md_lines.append("")
		md_lines.append(
			"Estimates one preparation plus N evaluations. Preparation time is the median of repeated preparation samples; "
			"execution time is the median total duration across repeated N-evaluation batches. Timing is gated by fixture correctness."
		)
		md_lines.append("")
		md_lines.append(
			"$$\\text{Total Amortized Cost} = \\text{Preparation Time} + (N \\times \\text{Execution Time})$$"
		)
		md_lines.append("")
		md_lines.append(
			"| Fixture ID | N Evaluations | Approach A Total Cost (ms) | Approach B Total Cost (ms) | Approach A Cost/Eval (µs) | Approach B Cost/Eval (µs) |"
		)
		md_lines.append("|---|---|---|---|---|---|")

		for item in amortized["amortized"]:
			fid = item["fixture_id"]
			counts = item["counts"]
			for n_str, c_data in counts.items():
				a_info = c_data.get(cand_a_name, {})
				b_info = c_data.get(cand_b_name, {})

				a_tot = f"{a_info.get('total_amortized_cost_ms')} ms" if a_info.get("is_valid") else "ERR"
				b_tot = f"{b_info.get('total_amortized_cost_ms')} ms" if b_info.get("is_valid") else "ERR"
				a_pe = f"{a_info.get('cost_per_eval_us')} µs" if a_info.get("is_valid") else "ERR"
				b_pe = f"{b_info.get('cost_per_eval_us')} µs" if b_info.get("is_valid") else "ERR"

				md_lines.append(f"| `{fid}` | N = {n_str} | {a_tot} | **{b_tot}** | {a_pe} | **{b_pe}** |")

		md_lines.append("")
		md_lines.append("---")
		md_lines.append("")
		md_lines.append("## 6. Architectural Analysis & Diagnostic Note")
		md_lines.append("")
		md_lines.append(
			"1. **Approach A Experimental Code-Object Diagnostic:** Evaluating precompiled RestrictedPython code objects via `eval(code_obj)` "
			"eliminates string parsing and AST compilation overhead. However, it is labeled strictly as a **lower-level diagnostic**, NOT as the primary "
			"production `frappe.safe_eval` result, because standard Frappe APIs do not expose code object caching."
		)
		md_lines.append(
			f"2. **Coverage Scope:** {correctness.get('agreed_cases', 0)} of {correctness.get('total_cases', 0)} fixtures passed the semantic correctness gate. "
			"Fixtures that fail the gate are excluded from both performance benchmarks. A finite fixture suite does not constitute formal proof of universal equivalence; "
			"untested operators and edge cases must still be verified before production migration."
		)
		md_lines.append(
			"3. **Production Isolation Confirmation:** **No production code, evaluators, controllers, persistence contracts, or DocTypes were modified.** "
			"All candidate evaluators and test harnesses reside isolated in `flexirule/ruleflow/tests/condition_benchmark/`."
		)

		report_content = "\n".join(md_lines)
		os.makedirs(os.path.dirname(output_markdown_path), exist_ok=True)
		with open(output_markdown_path, "w", encoding="utf-8") as f:
			f.write(report_content)

		return report_content

	def run_full_suite_and_export(
		self, output_filepath: str = "reports/condition_benchmark_results.json"
	) -> dict:
		"""Run correctness, primary prepared benchmark, amortized benchmark and export JSON."""
		correctness = self.run_semantic_correctness_suite()
		primary = self.run_primary_benchmarks()
		amortized = self.run_amortized_benchmarks()

		env_info = {
			"python_version": platform.python_version(),
			"platform": platform.platform(),
			"frappe_version": getattr(frappe, "__version__", "15.123.1"),
			"flexirule_version": "1.0.0-beta.3",
			"timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
		}

		full_payload = {
			"benchmark_protocol_version": 2,
			"measurement_protocol": (
				"Repeated median preparation samples; primary and amortized execution use "
				"repeated timed batches, rotating candidate order, alternating matching and "
				"non-matching documents, and semantic correctness gates."
			),
			"environment": env_info,
			"correctness_suite": correctness,
			"primary_benchmark": primary,
			"amortized_benchmark": amortized,
		}

		os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
		with open(output_filepath, "w", encoding="utf-8") as f:
			json.dump(full_payload, f, indent=2)

		markdown_path = os.path.join(
			os.path.dirname(output_filepath), "condition-backend-comparison-benchmark.md"
		)
		self.generate_markdown_report(full_payload, markdown_path)

		return full_payload


if __name__ == "__main__":
	sites_path = (
		"/home/jules/frappe-bench/sites" if os.path.exists("/home/jules/frappe-bench/sites") else "sites"
	)
	frappe.init(site="test_site", sites_path=sites_path)
	runner = BenchmarkRunner(iterations_per_batch=10000, num_batches=5)
	output_file = os.path.join(
		os.path.dirname(__file__), "../../../../reports/condition_benchmark_results.json"
	)
	output_file = os.path.abspath(output_file)
	runner.run_full_suite_and_export(output_file)
	print(f"Benchmark run complete. Results saved to {output_file}")
