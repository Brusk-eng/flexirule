# Architecture Analysis

This document provides a deep-dive into the FlexiRule architectural components, implemented optimizations, and identified concerns.

## Core Components

### 1. Rule Engine (`RuleEngine`)
- **Responsibility**: Orchestrates the execution of a single rule graph.
- **Action Traversal**: Sequential node processing with support for loops and branches.
- **Sandbox**: Implements `SafeFrappeAPI` and `ReadOnlyDocument` to ensure safety during condition evaluation.

### 2. Execution Coordinator (`RuleCoordinator`)
- **Responsibility**: Discovery and dispatch. Maps DocType events to active rules.
- **Registry**: Manages the `flexirule_runtime_registry_v2` in Redis for high-performance rule lookup.

### 3. Process Engine (`ProcessOperationExecutor`)
- **Responsibility**: Executes "Process" actions using the Declarative Contract v2.
- **Adapters**: Uses `OperationAdapterRegistry` to resolve execution logic for different operation types (validate, transform, etc.).

### 4. Registry System
- **HandlerRegistry**: Strategy pattern for Action Types. Handlers are stateless singletons.
- **AssignmentOperatorRegistry**: Custom operators for field assignments (set, add, clear).

---

## Implemented Optimizations

### 1. Rule Execution Change Filtering
- **Feature**: `watched_fields` filtering in `RuleCoordinator`.
- **Optimization**: Rules are only executed if fields they depend on (detected via `compiled_expression`) have changed in the current transaction. This prevents redundant runs on heavy DocTypes.

### 2. Action Plan Caching
- **Feature**: Two-layer cache (Local + Redis) for compiled execution plans.
- **Optimization**: Pre-resolves JSON configurations and template discovery. Reduces CPU overhead by avoiding repetitive `json.loads` calls during runtime, especially within `Loop` actions.

### 3. Bulk Sub-rule Cycle Detection
- **Feature**: Bulk adjacency building in `Rule.validate_no_sub_rule_cycles`.
- **Optimization**: Uses a single SQL query to fetch all sub-rule links and runs DFS in-memory. Eliminates the N+1 query problem during rule saving.

---

## Architectural Concerns & RC Blockers

### 1. Low Recursion Limit (RC Blocker)
- **Severity**: High
- **Description**: `MAX_SUB_RULE_DEPTH` is hardcoded to `2` in `engine.py`.
- **Impact**: Blocks valid complex business processes that require deep rule nesting.
- **Recommendation**: Increase to `5` or make it a configurable setting in `RuleFlow Settings`.

### 2. Validation Duplication
- **Severity**: Medium
- **Description**: Overlap between `Rule.validate()`, `validation_service.py`, and `ActionHandler.validate()`.
- **Impact**: Risk of "Partial Save" states where a rule is valid for a Draft but fails Activation due to inconsistent logic.

### 3. Savepoint Management
- **Severity**: Medium
- **Description**: Use of savepoints for rollback logic (`flexirule_action_`) in `engine.py`.
- **Impact**: If an exception occurs outside the `try/finally` block or within the rollback call itself, savepoints might leak, potentially leading to database connection exhaustion or transaction issues.

### 4. Safe Eval Depth
- **Severity**: Low
- **Description**: `validate_safe_eval` in `permissions.py` only validates syntax.
- **Impact**: Does not prevent complex logic or slow attribute lookups that could impact performance. Relying solely on `frappe.safe_eval` for runtime security.

---

## Extension Guide

### How to add a new Action Type
1. Create a new handler in `flexirule/ruleflow/core/action_handlers/`.
2. Inherit from `ActionHandler`.
3. Implement `execute(self, action, context, engine)`.
4. Register the handler in `HandlerRegistry.register()`.
5. Update `ACTION_TYPE_CONTRACT` in `contracts.py` to define its UI behavior.
