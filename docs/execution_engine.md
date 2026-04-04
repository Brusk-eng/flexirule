# Execution Engine

The core `RuleEngine` orchestrates individual rules via an advanced `execute_graph()` traversal.

## Traversal Safety 
The engine mitigates infinite cyclical loops inherently. `node_visits` counts executions per node; traversing past `100` visits results in an explosive `CycleDetectedError` avoiding background worker lockups.
Long running rules are guarded by a `time_limit` context block throwing `TimeoutError`.

## Execution Status & Logic Output
Actions resolve in to `{result, next_id}` dynamically via the injected Handlers (located inside `flexirule.ruleflow.core.action_handlers`).

In the core Engine error block: 
- Error Handling settings (`Continue`, `Retry`, `Rollback`, `Escalate`) on the Action level decide what happens during a `Exception`. Retries implement exponential backoffs. Rollbacks utilize Frappe database Savepoints (`frappe.db.savepoint()`) rather than full un-handled commits.

## RuleCoordinator Entry Point
A document triggers `frappe.doc_events` (a hook execution logic pattern). The `RuleCoordinator` fetches mapped rules actively listening via `frappe.cache`. It handles `Dry Run` rollbacks and dispatching `Async` rules into Frappe enqueued queues properly.
