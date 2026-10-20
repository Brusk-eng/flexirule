# FlexiRule — Condition Backend Comparison Benchmark Report

**Date:** 2026-10-20
**Repository:** [Sendipad/flexirule](https://github.com/Sendipad/flexirule)
**Branch:** `feat/condition-benchmark`
**Report Location:** `/app/reports/condition-backend-comparison-benchmark.md`
**Raw Results Data:** `reports/condition_benchmark_results.json`

---

## Executive Summary

This report documents the architectural investigation, empirical runtime probe, correctness test suite, and high-precision performance benchmarks comparing two architectural candidates for evaluating visual JSON rule conditions in FlexiRule:

- **Approach A — Precompiled Python Expression (`Approach A (frappe.safe_eval)`):** Evaluating a Python expression string generated from a condition tree using installed Frappe v15 restricted evaluation (`frappe.safe_eval`). Includes an isolated experimental diagnostic (`Approach A (Experimental Restricted Code Object)`) for evaluating precompiled RestrictedPython code objects.
- **Approach B — Prebuilt Normalized Execution Plan (`Approach B (Normalized Execution Plan)`):** Evaluating a typed, validated execution plan using a pure evaluator and comparator without Python compilation or AST parsing during execution.

### Summary Statistics and Findings

1. **`frappe.safe_eval` Overhead:** Installed Frappe v15 `frappe.safe_eval` performs `unicodedata.normalize()`, `ast.parse()`, AST node walking (`_validate_safe_eval_syntax`), and RestrictedPython AST transformation / compilation on **every single invocation**. It implements **no caching** of compiled bytecode objects.
2. **Semantic Correctness Gate Status:** **PASSED (100% Correctness Parity)**. Total Fixtures Tested: 11, Agreed: 11.
3. **Evaluations Completed:** **1,650,000** total error-free evaluations were completed during this benchmark run.

---

## 1. Environment and Reproducibility

| Key | Value |
|---|---|
| Python Version | 3.12.13 |
| Platform | Linux-6.8.0-x86_64-with-glibc2.39 |
| Frappe Framework | 15.123.1 |
| FlexiRule Version | 1.0.0-beta.3 |
| Benchmark Execution UTC | 2026-10-20T16:53:03Z |
| Benchmark Command | `PYTHONPATH=. /home/jules/frappe-bench/env/bin/python -m flexirule.ruleflow.tests.condition_benchmark.benchmark_runner` |

---

## 2. Correctness Test Suite Results

The correctness gate evaluates every candidate against matching and non-matching document contexts and verifies that all candidates agree with each other AND match the fixture's explicit expected results.

| Fixture ID | Complexity Tier | Status | Matching Check | Non-Matching Check | Errors |
|---|---|---|---|---|---|
| `tier1_simple_equality` | Tier 1 — Simple | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False}` | `None` |
| `tier2_typical_business_rule` | Tier 2 — Typical Business Rule | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False}` | `None` |
| `tier3_nested_and_or_groups` | Tier 3 — Nested Groups | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False}` | `None` |
| `tier4_deep_nested_complex` | Tier 4 — Deep Nested Complex | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False}` | `None` |
| `tier5_collection_child_records` | Tier 5 — Collection / Child Records | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False}` | `None` |
| `edge_case_is_set_null_empty` | Edge Case — Null / Empty | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False}` | `None` |
| `edge_case_link_tuple` | Edge Case — Link Tuple | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False}` | `None` |
| `edge_case_membership_in_not_in` | Edge Case — Membership | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False}` | `None` |
| `edge_case_contains_not_contains` | Edge Case — Substring | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False}` | `None` |
| `edge_case_collection_all_and_none` | Edge Case — Collection All/None | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False}` | `None` |
| `edge_case_length_gt_eq` | Edge Case — Length | **PASSED** | `{'Approach A (frappe.safe_eval)': True, 'Approach A (Experimental Restricted Code Object)': True, 'Approach B (Normalized Execution Plan)': True}` | `{'Approach A (frappe.safe_eval)': False, 'Approach A (Experimental Restricted Code Object)': False, 'Approach B (Normalized Execution Plan)': False}` | `None` |

---

## 3. Primary Prepared-Execution Benchmark Results

**Methodology:** Preparation (compilation / plan building) was performed **outside** the timed loop. The timed loop measured prepared execution over 5 batches of 10,000 iterations each (10,000 iterations x 5 batches).

| Fixture ID | Tier | Leaf / Depth | Approach A (`safe_eval`) | Approach A Exp (`code_obj`) | Approach B (`plan`) | Speedup B vs Primary A | Speedup B vs Exp A |
|---|---|---|---|---|---|---|---|
| `tier1_simple_equality` | Tier 1 — Simple | 1 / 1 | 173.45 µs/op | 9.232 µs/op | **3.699 µs/op** | **46.89x** | **2.5x** |
| `tier2_typical_business_rule` | Tier 2 — Typical Business Rule | 3 / 1 | 405.938 µs/op | 12.346 µs/op | **6.865 µs/op** | **59.13x** | **1.8x** |
| `tier3_nested_and_or_groups` | Tier 3 — Nested Groups | 4 / 2 | 540.835 µs/op | 12.717 µs/op | **7.671 µs/op** | **70.5x** | **1.66x** |
| `tier4_deep_nested_complex` | Tier 4 — Deep Nested Complex | 8 / 3 | 1145.937 µs/op | 18.631 µs/op | **12.845 µs/op** | **89.21x** | **1.45x** |
| `tier5_collection_child_records` | Tier 5 — Collection / Child Records | 3 / 2 | 731.873 µs/op | 17.716 µs/op | **11.129 µs/op** | **65.76x** | **1.59x** |
| `edge_case_is_set_null_empty` | Edge Case — Null / Empty | 1 / 1 | 306.192 µs/op | 10.781 µs/op | **3.287 µs/op** | **93.15x** | **3.28x** |
| `edge_case_link_tuple` | Edge Case — Link Tuple | 1 / 1 | 241.864 µs/op | 11.304 µs/op | **5.187 µs/op** | **46.63x** | **2.18x** |
| `edge_case_membership_in_not_in` | Edge Case — Membership | 2 / 1 | 374.049 µs/op | 10.9 µs/op | **5.981 µs/op** | **62.54x** | **1.82x** |
| `edge_case_contains_not_contains` | Edge Case — Substring | 2 / 1 | 576.268 µs/op | 14.365 µs/op | **5.7 µs/op** | **101.1x** | **2.52x** |
| `edge_case_collection_all_and_none` | Edge Case — Collection All/None | 1 / 2 | 488.591 µs/op | 13.27 µs/op | **6.933 µs/op** | **70.47x** | **1.91x** |
| `edge_case_length_gt_eq` | Edge Case — Length | 1 / 1 | 213.947 µs/op | 17.014 µs/op | **8.965 µs/op** | **23.86x** | **1.9x** |

---

## 4. Preparation Timings

Preparation time measured separately outside the execution loop:

| Fixture ID | Approach A Preparation Time (ms) | Approach B Preparation Time (ms) |
|---|---|---|
| `tier1_simple_equality` | 0.0972 ms | **0.0153 ms** |
| `tier2_typical_business_rule` | 0.2648 ms | **0.0288 ms** |
| `tier3_nested_and_or_groups` | 0.2814 ms | **0.0354 ms** |
| `tier4_deep_nested_complex` | 0.6333 ms | **0.0963 ms** |
| `tier5_collection_child_records` | 0.3262 ms | **0.0353 ms** |
| `edge_case_is_set_null_empty` | 0.1589 ms | **0.0231 ms** |
| `edge_case_link_tuple` | 0.1404 ms | **0.02 ms** |
| `edge_case_membership_in_not_in` | 0.2683 ms | **0.0225 ms** |
| `edge_case_contains_not_contains` | 0.2987 ms | **0.023 ms** |
| `edge_case_collection_all_and_none` | 0.2018 ms | **0.0238 ms** |
| `edge_case_length_gt_eq` | 0.1288 ms | **0.0168 ms** |

---

## 5. Amortized Total Cost Measurements

Calculates total cost for 1 preparation followed by N evaluations:

$$\text{Total Amortized Cost} = \text{Preparation Time} + (N \times \text{Execution Time})$$

| Fixture ID | N Evaluations | Approach A Total Cost (ms) | Approach B Total Cost (ms) | Approach A Cost/Eval (µs) | Approach B Cost/Eval (µs) |
|---|---|---|---|---|---|
| `tier1_simple_equality` | N = 1 | 1.2224 ms | **0.0776 ms** | 1222.423 µs | **77.555 µs** |
| `tier1_simple_equality` | N = 10 | 5.7308 ms | **0.0749 ms** | 573.082 µs | **7.495 µs** |
| `tier1_simple_equality` | N = 100 | 44.634 ms | **0.523 ms** | 446.34 µs | **5.23 µs** |
| `tier1_simple_equality` | N = 1000 | 397.5173 ms | **6.8128 ms** | 397.517 µs | **6.813 µs** |
| `tier2_typical_business_rule` | N = 1 | 2.2931 ms | **0.0801 ms** | 2293.096 µs | **80.056 µs** |
| `tier2_typical_business_rule` | N = 10 | 9.3714 ms | **0.3297 ms** | 937.137 µs | **32.973 µs** |
| `tier2_typical_business_rule` | N = 100 | 82.8289 ms | **1.5685 ms** | 828.289 µs | **15.685 µs** |
| `tier2_typical_business_rule` | N = 1000 | 919.8958 ms | **10.998 ms** | 919.896 µs | **10.998 µs** |
| `tier3_nested_and_or_groups` | N = 1 | 2.4547 ms | **0.2062 ms** | 2454.662 µs | **206.168 µs** |
| `tier3_nested_and_or_groups` | N = 10 | 13.514 ms | **0.421 ms** | 1351.403 µs | **42.096 µs** |
| `tier3_nested_and_or_groups` | N = 100 | 105.2959 ms | **2.0472 ms** | 1052.959 µs | **20.472 µs** |
| `tier3_nested_and_or_groups` | N = 1000 | 1331.1772 ms | **20.6619 ms** | 1331.177 µs | **20.662 µs** |
| `tier4_deep_nested_complex` | N = 1 | 5.2645 ms | **0.1003 ms** | 5264.476 µs | **100.31 µs** |
| `tier4_deep_nested_complex` | N = 10 | 31.395 ms | **0.2507 ms** | 3139.499 µs | **25.071 µs** |
| `tier4_deep_nested_complex` | N = 100 | 300.5577 ms | **3.8638 ms** | 3005.577 µs | **38.638 µs** |
| `tier4_deep_nested_complex` | N = 1000 | 2352.6365 ms | **25.9883 ms** | 2352.637 µs | **25.988 µs** |
| `tier5_collection_child_records` | N = 1 | 1.9469 ms | **0.1864 ms** | 1946.866 µs | **186.42 µs** |
| `tier5_collection_child_records` | N = 10 | 15.3813 ms | **0.3596 ms** | 1538.13 µs | **35.963 µs** |
| `tier5_collection_child_records` | N = 100 | 98.4159 ms | **1.1898 ms** | 984.159 µs | **11.898 µs** |
| `tier5_collection_child_records` | N = 1000 | 896.4217 ms | **26.0428 ms** | 896.422 µs | **26.043 µs** |
| `edge_case_is_set_null_empty` | N = 1 | 1.3715 ms | **0.0637 ms** | 1371.469 µs | **63.715 µs** |
| `edge_case_is_set_null_empty` | N = 10 | 8.1131 ms | **0.1058 ms** | 811.315 µs | **10.583 µs** |
| `edge_case_is_set_null_empty` | N = 100 | 65.1067 ms | **0.3658 ms** | 651.067 µs | **3.658 µs** |
| `edge_case_is_set_null_empty` | N = 1000 | 387.6812 ms | **2.9511 ms** | 387.681 µs | **2.951 µs** |
| `edge_case_link_tuple` | N = 1 | 0.5372 ms | **0.0404 ms** | 537.237 µs | **40.428 µs** |
| `edge_case_link_tuple` | N = 10 | 2.718 ms | **0.1256 ms** | 271.803 µs | **12.562 µs** |
| `edge_case_link_tuple` | N = 100 | 23.8533 ms | **0.5657 ms** | 238.533 µs | **5.657 µs** |
| `edge_case_link_tuple` | N = 1000 | 243.8263 ms | **5.273 ms** | 243.826 µs | **5.273 µs** |
| `edge_case_membership_in_not_in` | N = 1 | 0.8526 ms | **0.052 ms** | 852.554 µs | **52.014 µs** |
| `edge_case_membership_in_not_in` | N = 10 | 4.1661 ms | **0.1469 ms** | 416.607 µs | **14.689 µs** |
| `edge_case_membership_in_not_in` | N = 100 | 41.2248 ms | **0.8258 ms** | 412.248 µs | **8.258 µs** |
| `edge_case_membership_in_not_in` | N = 1000 | 413.476 ms | **5.9035 ms** | 413.476 µs | **5.904 µs** |
| `edge_case_contains_not_contains` | N = 1 | 1.0207 ms | **0.0487 ms** | 1020.748 µs | **48.734 µs** |
| `edge_case_contains_not_contains` | N = 10 | 6.2665 ms | **0.0982 ms** | 626.653 µs | **9.821 µs** |
| `edge_case_contains_not_contains` | N = 100 | 57.5712 ms | **0.6101 ms** | 575.712 µs | **6.101 µs** |
| `edge_case_contains_not_contains` | N = 1000 | 581.1719 ms | **5.5712 ms** | 581.172 µs | **5.571 µs** |
| `edge_case_collection_all_and_none` | N = 1 | 0.9138 ms | **0.0531 ms** | 913.816 µs | **53.086 µs** |
| `edge_case_collection_all_and_none` | N = 10 | 5.0222 ms | **0.1198 ms** | 502.22 µs | **11.981 µs** |
| `edge_case_collection_all_and_none` | N = 100 | 46.7737 ms | **0.7223 ms** | 467.737 µs | **7.223 µs** |
| `edge_case_collection_all_and_none` | N = 1000 | 464.7835 ms | **7.2194 ms** | 464.783 µs | **7.219 µs** |
| `edge_case_length_gt_eq` | N = 1 | 0.5199 ms | **0.0396 ms** | 519.942 µs | **39.598 µs** |
| `edge_case_length_gt_eq` | N = 10 | 2.4773 ms | **0.075 ms** | 247.732 µs | **7.502 µs** |
| `edge_case_length_gt_eq` | N = 100 | 21.9656 ms | **0.5276 ms** | 219.656 µs | **5.276 µs** |
| `edge_case_length_gt_eq` | N = 1000 | 210.3314 ms | **3.9174 ms** | 210.331 µs | **3.917 µs** |

---

## 6. Architectural Analysis & Diagnostic Note

1. **Approach A Experimental Code-Object Diagnostic:** Evaluating precompiled RestrictedPython code objects via `eval(code_obj)` eliminates string parsing and AST compilation overhead. However, it is labeled strictly as a **lower-level diagnostic**, NOT as the primary production `frappe.safe_eval` result, because standard Frappe APIs do not expose code object caching.
2. **Coverage Scope:** While all 11 fixtures passed 100% semantic correctness tests, a finite fixture suite does not constitute formal mathematical proof of universal equivalence for all possible condition expressions. Edge cases or untested custom operators must be verified before production migration.
3. **Production Isolation Confirmation:** **No production code, evaluators, controllers, persistence contracts, or DocTypes were modified.** All candidate evaluators and test harnesses reside isolated in `flexirule/ruleflow/tests/condition_benchmark/`.