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
from flexirule.ruleflow.tests.condition_benchmark.comparison_api import (
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

		self.candidate_a = ApproachACandidate()
		self.candidate_a_exp = ApproachAExperimentalCodeObjectCandidate()
		self.candidate_b = ApproachBCandidate()

		self.candidates = [self.candidate_a, self.candidate_a_exp, self.candidate_b]
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
				fix.condition_payload, fix.matching_doc
			)
			check_non_match = self.harness.check_semantic_agreement(
				fix.condition_payload, fix.non_matching_doc
			)

			case_agrees = check_match["agrees"] and check_non_match["agrees"]
			if case_agrees:
				agreed_cases += 1

			correctness_results.append(
				{
					"fixture_id": fix.fixture_id,
					"tier": fix.tier,
					"agrees": case_agrees,
					"matching_doc_check": check_match["candidate_results"],
					"non_matching_doc_check": check_non_match["candidate_results"],
					"disagreements": check_match["disagreements"] + check_non_match["disagreements"],
					"errors": {**check_match["errors"], **check_non_match["errors"]},
				}
			)

		return {
			"total_cases": total_cases,
			"agreed_cases": agreed_cases,
			"all_agreed": agreed_cases == total_cases,
			"results": correctness_results,
		}

	def run_primary_benchmarks(self) -> dict:
		"""Execute prepared-execution-only hot timing loops."""
		fixtures = get_all_fixtures()
		fixture_benchmark_results = []

		for fix in fixtures:
			# Step 1: Prepare conditions outside timed region
			prepared_map = self.harness.prepare_all(fix.condition_payload)

			candidate_metrics = {}

			for candidate in self.candidates:
				c_name = candidate.candidate_name
				prep = prepared_map[c_name]
				doc = fix.matching_doc

				# Warm-up loop
				for _ in range(self.warmup_iterations):
					candidate.evaluate(prep, doc)

				# Timed batches loop
				batch_durations = []
				for _ in range(self.num_batches):
					start_time = time.perf_counter()
					for _ in range(self.iterations_per_batch):
						res = candidate.evaluate(prep, doc)
						if res.error:
							break
					elapsed = time.perf_counter() - start_time
					batch_durations.append(elapsed)

				# Compute per-execution time stats
				per_exec_times_us = [
					(d / self.iterations_per_batch) * 1e6 for d in batch_durations
				]
				sorted_times = sorted(per_exec_times_us)

				median_us = statistics.median(sorted_times)
				mean_us = statistics.mean(sorted_times)
				min_us = min(sorted_times)
				max_us = max(sorted_times)
				# p95 index for 5 batches is index 4 (max)
				p95_us = sorted_times[int(0.95 * len(sorted_times))] if len(sorted_times) >= 5 else max_us

				prep_time_ms = prep.preparation_time_seconds * 1000.0

				candidate_metrics[c_name] = {
					"preparation_time_ms": round(prep_time_ms, 4),
					"iterations_per_batch": self.iterations_per_batch,
					"num_batches": self.num_batches,
					"median_us_per_exec": round(median_us, 3),
					"mean_us_per_exec": round(mean_us, 3),
					"min_us_per_exec": round(min_us, 3),
					"max_us_per_exec": round(max_us, 3),
					"p95_us_per_exec": round(p95_us, 3),
					"total_batch_time_seconds": [round(d, 4) for d in batch_durations],
				}

			# Calculate speedup ratios
			a_time = candidate_metrics[self.candidate_a.candidate_name]["median_us_per_exec"]
			a_exp_time = candidate_metrics[self.candidate_a_exp.candidate_name]["median_us_per_exec"]
			b_time = candidate_metrics[self.candidate_b.candidate_name]["median_us_per_exec"]

			speedup_b_vs_a = round(a_time / b_time, 2) if b_time > 0 else 0.0
			speedup_b_vs_a_exp = round(a_exp_time / b_time, 2) if b_time > 0 else 0.0

			fixture_benchmark_results.append(
				{
					"fixture_id": fix.fixture_id,
					"tier": fix.tier,
					"description": fix.description,
					"leaf_count": fix.leaf_count,
					"nesting_depth": fix.nesting_depth,
					"speedup_ratio_b_vs_primary_a": speedup_b_vs_a,
					"speedup_ratio_b_vs_experimental_a": speedup_b_vs_a_exp,
					"candidate_metrics": candidate_metrics,
				}
			)

		return {"fixtures": fixture_benchmark_results}

	def run_amortized_benchmarks(
		self, execution_counts: list[int] | None = None
	) -> dict:
		"""Secondary benchmark calculating total amortized cost (Prep + N * Exec)."""
		if execution_counts is None:
			execution_counts = [1, 10, 100, 1000]

		fixtures = get_all_fixtures()
		amortized_results = []

		for fix in fixtures:
			prepared_map = self.harness.prepare_all(fix.condition_payload)
			fix_amortized = {
				"fixture_id": fix.fixture_id,
				"tier": fix.tier,
				"counts": {},
			}

			for N in execution_counts:
				count_metrics = {}
				for candidate in self.candidates:
					c_name = candidate.candidate_name
					prep = prepared_map[c_name]
					doc = fix.matching_doc

					prep_time_s = prep.preparation_time_seconds

					# Single execution measurement and total loop for N evaluations
					start_loop = time.perf_counter()
					for _ in range(N):
						candidate.evaluate(prep, doc)
					n_exec_s = time.perf_counter() - start_loop

					total_amortized_ms = (prep_time_s + n_exec_s) * 1000.0

					count_metrics[c_name] = {
						"prep_time_ms": round(prep_time_s * 1000.0, 4),
						"n_exec_time_ms": round(n_exec_s * 1000.0, 4),
						"total_amortized_cost_ms": round(total_amortized_ms, 4),
						"cost_per_eval_us": round((total_amortized_ms / N) * 1000.0, 3),
					}

				fix_amortized["counts"][str(N)] = count_metrics

			amortized_results.append(fix_amortized)

		return {"amortized": amortized_results}

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
			"environment": env_info,
			"correctness_suite": correctness,
			"primary_benchmark": primary,
			"amortized_benchmark": amortized,
		}

		os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
		with open(output_filepath, "w", encoding="utf-8") as f:
			json.dump(full_payload, f, indent=2)

		return full_payload


def run_benchmark():
	runner = BenchmarkRunner(iterations_per_batch=10000, num_batches=5)
	results = runner.run_full_suite_and_export()
	print("Benchmark run complete. Results saved to reports/condition_benchmark_results.json")
	return results


if __name__ == "__main__":
	sites_path = "/home/jules/frappe-bench/sites" if os.path.exists("/home/jules/frappe-bench/sites") else "sites"
	frappe.init(site="test_site", sites_path=sites_path)
	runner = BenchmarkRunner(iterations_per_batch=10000, num_batches=5)
	output_file = os.path.join(os.path.dirname(__file__), "../../../../reports/condition_benchmark_results.json")
	output_file = os.path.abspath(output_file)
	runner.run_full_suite_and_export(output_file)
	print(f"Benchmark run complete. Results saved to {output_file}")
