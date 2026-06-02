# Rule Execution Lifecycle

This document traces the runtime execution path of FlexiRule across different trigger types, including action handler details and implemented optimizations.

## A. Document Event Triggers

Document events are triggered by Frappe's standard document lifecycle hooks (e.g., Before Save, After Save).

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Frappe as Frappe Framework
    participant Hooks as flexirule.ruleflow.hooks
    participant Coord as RuleCoordinator
    participant Engine as RuleEngine
    participant Handler as ActionHandler
    participant DB as Database

    Frappe->>Hooks: execute_rules(doc, method)
    Hooks->>Coord: execute_rules_from_event(doc, event)
    Coord->>Coord: Get Active Rules (from Registry)
    Coord->>Coord: check_eligibility(rule, doc, event)
    Note over Coord: Evaluates compiled_expression
    loop For each Eligible Rule
        Coord->>Engine: execute(doc, event)
        Engine->>Engine: _execute_graph(context)
        loop For each Action
            Engine->>Handler: execute(action, context, engine)
            Handler-->>Engine: (result, next_action_id)
            Engine->>Engine: _post_process_action_result
            Note over Engine: Applies Mutation Mode (Doc/Vars)
        end
        Engine->>DB: _save_execution_log
    end
```

### 1. Registration & Hook Discovery
- **Hook Definition**: `flexirule/hooks.py` registers `flexirule.ruleflow.hooks.execute_rules` for almost all DocType events (`*`).
- **Exclusion List**: `get_excluded_doctypes()` in `hooks.py` prevents execution on system DocTypes (Email Queue, Version, etc.) and internal FlexiRule DocTypes to avoid recursion.

### 2. Rule Lookup & Filtering (Optimized)
- **Runtime Registry**: `RuleCoordinator.get_runtime_registry()` uses a Redis-backed index (`flexirule_runtime_registry_v2`) for O(1) lookup of active rules.
- **Change Filtering**: `_passes_watched_field_filter()` skips rules if `watched_fields` are defined and none of them changed in the current transaction. This prevents redundant rule execution on unrelated field updates.
- **Eligibility**: `check_eligibility()` evaluates the `compiled_expression` (trigger condition) using `frappe.safe_eval`.

### 3. Execution Context
- **Context Creation**: `RuleEngine._initialize_context()` creates a sandbox containing:
    - `doc`: The current document.
    - `old_doc`: State before save (if available).
    - `vars`: Execution-local variables.
    - `frappe`: `SafeFrappeAPI` (restricted read-only access).
    - `rule`: Metadata about the running rule.

### 4. Action Handler Execution
The `RuleEngine` dispatches action execution to specialized handlers using the Strategy Pattern.

#### Strategy Pattern implementation
- **Registry**: `HandlerRegistry` manages all available action handlers.
- **Statelessness**: All handlers (e.g., `AssignmentHandler`, `ProcessHandler`) are stateless singletons. They receive the mutable `context` and `engine` instance for each execution.
- **Execution Tuple**: Every handler's `execute` method returns a `(result, next_action_id)` tuple.
    - `result`: The value produced by the action (e.g., doc list, calculation result).
    - `next_action_id`: The ID of the next node to traverse in the graph. This enables conditional branching and loops.

#### Action Plan Caching (Optimization)
- **Source**: `flexirule/ruleflow/core/action_plan_cache.py`
- **Behavior**: The engine uses a compiled execution plan for each action. This plan contains pre-resolved schemas, Jinja templates, and configuration paths.
- **Benefit**: Eliminates the overhead of repetitive JSON parsing (`json.loads`) and template discovery during the execution of a single rule, especially within loops.

---

## B. Scheduled Event Triggers

Scheduled rules run on document batches at specific intervals.

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Cron as Frappe Scheduler (all)
    participant Sched as scheduler.py
    participant Doc as RuleScheduler (DocType)
    participant Coord as RuleCoordinator
    participant Engine as RuleEngine

    Cron->>Sched: check_scheduled_rules()
    Sched->>Doc: enqueue()
    Doc->>Frappe: frappe.enqueue(run_scheduled_rule)
    Frappe->>Sched: run_scheduled_rule(name)
    Sched->>Doc: execute()
    Doc->>Doc: _get_documents() (Apply Filters)
    loop For each Document in Batch
        Doc->>Coord: execute_rule(rule, context)
        Coord->>Engine: execute(doc)
    end
```

### 1. Scheduler Registration
- **Frappe Hook**: `scheduler_events['all']` calls `check_scheduled_rules` every minute.
- **Due Check**: `RuleScheduler.is_event_due()` uses `croniter` to determine if the next execution time has passed.

### 2. Execution Flow
- **Background Queue**: Jobs are enqueued via `frappe.enqueue` with a unique `job_id` (`rule_scheduler::{name}`) to prevent overlapping runs.
- **Batching**: `RuleScheduler.execute()` fetches document names using `filter_json` and processes them in batches (default 100).

---

## C. Callable Event Triggers

Callable rules are executed on-demand, either as subrules or via API.

### Mode 1: Subrule Execution
**Rule A → Action: Sub-Rule → Rule B**

- **Discovery**: `SubRuleHandler` fetches Rule B by name.
- **Context Inheritance**: Rule B receives the same `doc` and `vars` from Rule A.
- **Recursion Protection**: `validate_no_sub_rule_cycles()` (at save time via bulk query optimization) and `MAX_SUB_RULE_DEPTH = 2` (at runtime) prevent infinite loops.

### Mode 2: API/User Execution
**frappe.call() → api.py → Rule Engine**

- **Endpoints**: `flexirule.ruleflow.api.execute_rule` or `test_rule`.
- **Permission Check**: `_require_api_access()` ensures only authorized users trigger rules manually.

---

## Source Trace Summary

### Document Event Flow
**File** → **Class** → **Method** → **Next Call**

1. `frappe/model/document.py` → `Document` → `run_hooks` → `flexirule.ruleflow.hooks.execute_rules`
2. `flexirule/ruleflow/hooks.py` → `N/A` → `execute_rules` → `RuleCoordinator.execute_rules_from_event`
3. `flexirule/ruleflow/core/coordinator.py` → `RuleCoordinator` → `execute_rules_from_event` → `RuleEngine.execute`
4. `flexirule/ruleflow/core/engine.py` → `RuleEngine` → `execute` → `_execute_graph`
5. `flexirule/ruleflow/core/engine.py` → `RuleEngine` → `_execute_graph` → `HandlerRegistry.get`
6. `flexirule/ruleflow/core/action_handlers/process.py` → `ProcessHandler` → `execute` → `ProcessOperationExecutor.execute`
7. `flexirule/ruleflow/core/process_runtime_v2.py` → `ProcessOperationExecutor` → `execute` → `OperationAdapterRegistry.execute`
8. `flexirule/ruleflow/core/process_runtime_v2.py` → `OperationAdapterRegistry` → `execute` → `_execute_python_process_operation`
9. `flexirule/ruleflow/core/process_runtime_v2.py` → `N/A` → `_execute_python_process_operation` → `Process.execute` (via module lookup)
