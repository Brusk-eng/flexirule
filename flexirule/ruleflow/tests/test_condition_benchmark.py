# Copyright (c) 2026, FlexiRule and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from flexirule.ruleflow.tests.condition_benchmark.benchmark_runner import BenchmarkRunner
from flexirule.ruleflow.tests.condition_benchmark.candidate_approach_a import (
	ApproachACandidate,
	ApproachAExperimentalCodeObjectCandidate,
)
from flexirule.ruleflow.tests.condition_benchmark.candidate_approach_b import ApproachBCandidate
from flexirule.ruleflow.tests.condition_benchmark.comparison_api import (
	ConditionComparisonHarness,
)
from flexirule.ruleflow.tests.condition_benchmark.fixtures import get_all_fixtures


class TestConditionBenchmark(FrappeTestCase):
	"""Unit tests for FlexiRule condition benchmark comparison API and candidates."""

	def setUp(self):
		super().setUp()
		self.candidate_a = ApproachACandidate()
		self.candidate_a_exp = ApproachAExperimentalCodeObjectCandidate()
		self.candidate_b = ApproachBCandidate()
		self.candidates = [self.candidate_a, self.candidate_a_exp, self.candidate_b]
		self.harness = ConditionComparisonHarness(self.candidates)

	def test_candidates_prepare_and_evaluate_simple_fixture(self):
		fixtures = get_all_fixtures()
		simple_fixture = fixtures[0]

		prepared = self.harness.prepare_all(simple_fixture.condition_payload)
		self.assertEqual(len(prepared), 3)

		# Evaluate matching doc
		match_results = self.harness.evaluate_all(prepared, simple_fixture.matching_doc)
		for name, res in match_results.items():
			self.assertIsNone(res.error, f"Candidate {name} failed with error: {res.error}")
			self.assertTrue(res.result, f"Candidate {name} expected True for matching doc")

		# Evaluate non-matching doc
		non_match_results = self.harness.evaluate_all(prepared, simple_fixture.non_matching_doc)
		for name, res in non_match_results.items():
			self.assertIsNone(res.error, f"Candidate {name} failed with error: {res.error}")
			self.assertFalse(res.result, f"Candidate {name} expected False for non-matching doc")

	def test_semantic_correctness_suite_agreement(self):
		runner = BenchmarkRunner(iterations_per_batch=10, num_batches=1, warmup_iterations=1)
		suite_results = runner.run_semantic_correctness_suite()
		self.assertTrue(
			suite_results["all_agreed"],
			f"Disagreements found across candidates: {suite_results['results']}",
		)

	def test_benchmark_runner_full_suite_export(self):
		runner = BenchmarkRunner(iterations_per_batch=10, num_batches=1, warmup_iterations=1)
		payload = runner.run_full_suite_and_export("reports/test_benchmark_results.json")

		self.assertIn("environment", payload)
		self.assertIn("correctness_suite", payload)
		self.assertIn("primary_benchmark", payload)
		self.assertIn("amortized_benchmark", payload)
