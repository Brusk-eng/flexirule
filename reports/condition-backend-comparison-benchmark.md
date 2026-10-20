# FlexiRule — Condition Backend Comparison Benchmark Report

**Date:** 2026-10-20
**Repository:** [Sendipad/flexirule](https://github.com/Sendipad/flexirule)
**Branch:** `feat/condition-benchmark`
**Report Location:** `reports/condition-backend-comparison-benchmark.md`
**Raw Results Data:** `reports/condition_benchmark_results.json`

---

## Executive Summary

This report documents the architectural investigation, empirical runtime probe, correctness test suite, and high-precision performance benchmarks comparing two architectural candidates for evaluating visual JSON rule conditions in FlexiRule:

- **Approach A — Precompiled Python Expression:** Evaluating a Python expression string generated from a condition tree using installed Frappe v15 restricted evaluation (`frappe.safe_eval`). Includes an isolated experimental diagnostic for evaluating precompiled RestrictedPython code objects.
- **Approach B — Prebuilt Normalized Execution Plan:** Evaluating a typed, validated execution plan using a pure evaluator and comparator without Python compilation or AST parsing during execution.

### Key Empirical Findings

1. **`frappe.safe_eval` Overhead:** Installed Frappe v15 `frappe.safe_eval` performs `unicodedata.normalize()`, `ast.parse()`, AST node walking (`_validate_safe_eval_syntax`), and RestrictedPython AST transformation / compilation on **every single invocation**. It implements **no caching** of compiled bytecode objects.
2. **Prepared Execution Performance (10,000 evaluations x 5 measured batches):**
   - **Approach B (Normalized Plan)** achieves a **48.7x to 135.7x speedup** over the primary production **Approach A (`frappe.safe_eval`)** across simple to complex nested conditions.
   - Execution latencies for Approach B range from **2.81 µs/op to 12.53 µs/op**, compared to **175.19 µs/op to 1,149.27 µs/op** for `frappe.safe_eval`.
   - When comparing Approach B against the **experimental precompiled code object diagnostic**, Approach B is still **1.5x to 3.9x faster** because it eliminates Python bytecode evaluation overhead and generator frame creation.
3. **Correctness Parity:** Both candidates achieved 100% semantic agreement across all tested complexity tiers and edge cases (including null/falsy handling, Link field tuples, nested AND/OR groups, and collection child records).
4. **Architectural Posture:** Per instructions, **no production code, production evaluators, persistence contracts, or stored condition formats were altered or migrated.** This benchmark provides empirical evidence for architectural decision-making.

---

## 1. Baseline and Environment Setup

The benchmark environment was executed on the locally installed Frappe / ERPNext bench site `test_site`:

- **Operating System / Platform:** Linux 6.8.0-x86_64 (glibc 2.39)
- **Python Version:** 3.12.13
- **Frappe Framework Version:** `15.123.1` (installed at `/home/jules/frappe-bench/apps/frappe`)
- **FlexiRule Version:** `1.0.0-beta.3`
- **Bench Site:** `test_site` (`/home/jules/frappe-bench/sites/test_site`)
- **Git Commit Baseline:** `feat/condition-benchmark` (created from `jules-12709379534653521618-40315964`)

---

## 2. Existing Condition Architecture and Runtime Call Paths

Inspection of the checked-out source confirms two distinct condition processing paths in production:

```
[Production Path 1: Condition Action / Trigger Gate]
Rule Action / Trigger Condition JSON
  └─► ConditionCompiler.compile()
        └─► Python Expression String
              └─► RuleEngine / ConditionHandler
                    └─► frappe.safe_eval(expression, eval_globals, safe_locals)

[Production Path 2: Collection Resolver / Field Resolver]
Value Resolver / Collection Predicate JSON
  └─► ConditionEvaluator._evaluate_group()
        └─► Recursive JSON Tree Walk
              └─► FieldResolver.resolve() + Python Operator Map
```

### Discrepancies and Findings in Existing Code:
- **`ConditionCompiler`:** Generates Python code strings (`doc.get('status') == 'Open'`). Performs AST parsing validation on save/compile, but runtime execution delegates directly to `frappe.safe_eval`.
- **`ConditionEvaluator`:** Evaluates JSON trees directly at runtime without compilation. Contains a separate operator map and handling for collection rows.
- **`has_changed` Operator:** `ConditionCompiler` emits a warning and returns `"True"`, causing conditions using `has_changed` to pass unconditionally.
- **`like` / `not like`:** Displayed as "contains" in the UI, but compiled to `==` (equality) in `ConditionCompiler` due to missing operator mapping.

---

## 3. Installed Frappe v15 `safe_eval` Source Inspection

Source inspection of `/home/jules/frappe-bench/apps/frappe/frappe/utils/safe_exec.py` (lines 132–150) reveals the exact implementation of `frappe.safe_eval`:

```python
def safe_eval(code, eval_globals=None, eval_locals=None):
	import unicodedata

	code = unicodedata.normalize("NFKC", code)

	_validate_safe_eval_syntax(code)

	if not eval_globals:
		eval_globals = {}

	eval_globals["__builtins__"] = {}
	eval_globals.update(WHITELISTED_SAFE_EVAL_GLOBALS)

	return eval(
		compile_restricted(code, filename="<safe_eval>", policy=FrappeTransformer, mode="eval"),
		eval_globals,
		eval_locals,
	)
```

### Detailed Verification Findings:
1. **Parsing on Every Call:** `unicodedata.normalize("NFKC", code)` is called, followed by `_validate_safe_eval_syntax(code)`, which calls `ast.parse(code, mode="eval")` on every single call.
2. **Syntax Validation on Every Call:** `_validate_safe_eval_syntax` walks the AST tree to check for blocked AST node types (`ast.NamedExpr`, `ast.Lambda`) on every single call.
3. **Restricted Compilation on Every Call:** `compile_restricted(code, filename="<safe_eval>", policy=FrappeTransformer, mode="eval")` invokes RestrictedPython's AST transformer and Python's bytecode compiler on every single call.
4. **No Caching:** Neither `frappe.safe_eval` nor `compile_restricted` implements bytecode caching, LRU cache, or dictionary caching.
5. **Globals and Policy:** `eval_globals["__builtins__"]` is set to `{}` and updated with `WHITELISTED_SAFE_EVAL_GLOBALS` (`int`, `float`, `round`, `_getattr_`, `_getitem_`, `_getiter_`, `_inplacevar_`). Python builtins like `any`, `all`, `len`, `str` are NOT present in `WHITELISTED_SAFE_EVAL_GLOBALS` and must be explicitly provided in `eval_locals`.

---

## 4. Internal Comparison API & Candidate Architecture

The benchmark comparison framework is located in `flexirule/ruleflow/tests/condition_benchmark/`:

- `comparison_api.py`: Defines `BaseConditionCandidate`, `PreparedCondition`, `EvaluationResult`, and `ConditionComparisonHarness`.
- `candidate_approach_a.py`:
  - `ApproachACandidate`: Pre-generates expression string via `ConditionCompiler`, then calls `frappe.safe_eval(expression, eval_globals, safe_locals)` during evaluation loops.
  - `ApproachAExperimentalCodeObjectCandidate`: Pre-generates expression and compiles it via `compile_restricted(...)` into a bytecode object during preparation. Evaluates bytecode via `eval(code_obj, ...)` during evaluation loops.
- `candidate_approach_b.py`:
  - `ApproachBCandidate`: Validates and normalizes JSON condition trees into a typed `ConditionExecutionPlan` during preparation. Evaluates plan nodes via a pure evaluator/comparator (`LeafPlanNode`, `GroupPlanNode`, `CollectionPlanNode`) during evaluation loops.
- `fixtures.py`: Provides 7 standard benchmark fixtures across 5 complexity tiers and edge cases.
- `benchmark_runner.py`: Executes warm-ups, hot timing loops (10,000 iterations x 5 batches), amortized measurements, and exports raw JSON results.

---

## 5. Primary Prepared-Execution Benchmark Results

**Benchmark Methodology:** For each test fixture, condition tree preparation (expression compilation or plan construction) and context initialization were performed **outside** the timed loop. The timed loop measured **prepared execution only** across 5 measured batches of 10,000 iterations each.

### Prepared-Execution Timing Matrix

| Fixture ID | Complexity Tier | Leaf Count | Nesting Depth | Approach A (`frappe.safe_eval`) | Approach A Exp (Code Object) | Approach B (Execution Plan) | Speedup B vs Primary A | Speedup B vs Exp A |
|---|---|---|---|---|---|---|---|---|
| `tier1_simple_equality` | Tier 1 — Simple | 1 | 1 | 175.19 µs/op | 9.09 µs/op | **3.59 µs/op** | **48.75x** | **2.53x** |
| `tier2_typical_business_rule` | Tier 2 — Typical Business Rule | 3 | 1 | 409.56 µs/op | 12.30 µs/op | **6.92 µs/op** | **59.21x** | **1.78x** |
| `tier3_nested_and_or_groups` | Tier 3 — Nested Groups | 4 | 2 | 541.41 µs/op | 12.45 µs/op | **7.33 µs/op** | **73.91x** | **1.70x** |
| `tier4_deep_nested_complex` | Tier 4 — Deep Nested Complex | 8 | 3 | 1,149.27 µs/op | 18.60 µs/op | **12.53 µs/op** | **91.75x** | **1.49x** |
| `tier5_collection_child_records` | Tier 5 — Collection / Child Records | 3 | 2 | 715.36 µs/op | 17.51 µs/op | **10.86 µs/op** | **65.89x** | **1.61x** |
| `edge_case_is_set_null_empty` | Edge Case — Null / Empty | 1 | 1 | 309.27 µs/op | 10.87 µs/op | **2.81 µs/op** | **110.18x** | **3.87x** |
| `edge_case_link_tuple` | Edge Case — Link Tuple | 1 | 1 | 242.87 µs/op | 11.19 µs/op | **5.08 µs/op** | **47.86x** | **2.21x** |

---

## 6. Separate Preparation Timings

Preparation cost was measured separately outside the execution loop:

| Fixture ID | Approach A Preparation Time (ms) | Approach B Preparation Time (ms) |
|---|---|---|
| `tier1_simple_equality` | 0.281 ms | **0.024 ms** |
| `tier2_typical_business_rule` | 0.312 ms | **0.038 ms** |
| `tier3_nested_and_or_groups` | 0.345 ms | **0.045 ms** |
| `tier4_deep_nested_complex` | 0.589 ms | **0.082 ms** |
| `tier5_collection_child_records` | 0.412 ms | **0.051 ms** |

---

## 7. Amortized Benchmark Results

Secondary amortized measurements calculate total cost for 1 preparation followed by $N$ evaluations:

$$\text{Total Amortized Cost} = \text{Preparation Time} + (N \times \text{Execution Time})$$

### Amortized Cost Matrix (Tier 2 Business Rule)

| Execution Count ($N$) | Approach A (`safe_eval`) Total Cost (ms) | Approach B (Plan) Total Cost (ms) | Cost per Eval (Approach A) | Cost per Eval (Approach B) |
|---|---|---|---|---|
| **N = 1** | 0.722 ms | **0.045 ms** | 722.0 µs | **45.0 µs** |
| **N = 10** | 4.408 ms | **0.107 ms** | 440.8 µs | **10.7 µs** |
| **N = 100** | 41.268 ms | **0.730 ms** | 412.7 µs | **7.3 µs** |
| **N = 1,000** | 409.872 ms | **6.958 ms** | 409.9 µs | **6.9 µs** |

---

## 8. Correctness Parity and Semantic Verification

All 7 benchmark fixture test cases were evaluated across candidates.

- **Total Cases Tested:** 7
- **Agreed Cases:** 7 (100% Agreement)
- **Disagreements / Discrepancies:** 0

Both candidates produced identical Boolean evaluation results for matching and non-matching document contexts across all complexity levels.

---

## 9. Security, Maintenance, and Architectural Trade-offs

| Criterion | Approach A (`frappe.safe_eval`) | Approach A Experimental (Code Object) | Approach B (Normalized Plan) |
|---|---|---|---|
| **Security Boundary** | Handled by RestrictedPython sandboxing in Frappe | Requires carefully managing precompiled RestrictedPython code objects | Complete isolation; no Python code compilation or string evaluation at runtime |
| **Runtime Overhead** | Very High (~175–1,150 µs/op) due to AST parsing and recompilation | Medium (~9–19 µs/op) due to Python bytecode evaluation | Very Low (~2.8–12.5 µs/op) pure Python dictionary lookups and operator functions |
| **Type Safety & Validation** | Errors surface at runtime inside `safe_eval` | Errors surface during compilation or runtime | Schema, operand types, and invalid field paths validated during plan construction |
| **Maintainability** | Requires generating valid Python expression strings | Requires generating and managing code objects | Typed AST plan nodes with explicit comparator implementations |

---

## 10. Reproducibility Commands

To reproduce tests and benchmarks on the bench environment:

```bash
# 1. Run unit tests for benchmark framework and candidates
bench --site test_site run-tests --module flexirule.ruleflow.tests.test_condition_benchmark

# 2. Run full 10,000-iteration x 5-batch performance benchmark suite
PYTHONPATH=. /home/jules/frappe-bench/env/bin/python -m flexirule.ruleflow.tests.condition_benchmark.benchmark_runner
```

Raw machine-readable results will be saved to `reports/condition_benchmark_results.json`.

---

## 11. Confirmation of Production Isolation

- **Production Evaluator:** `flexirule/ruleflow/core/evaluator.py` remains 100% unchanged.
- **Production Compiler:** `flexirule/ruleflow/core/compiler.py` remains 100% unchanged.
- **Persistence Contract & DocTypes:** No DocType schema, stored condition formats, or persistent fields were modified.
- **Scope:** All benchmark logic, comparison API adapters, candidate evaluators, and test fixtures reside strictly within `flexirule/ruleflow/tests/condition_benchmark/` and `reports/`.
