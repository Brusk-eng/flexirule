# Runtime Usage Verification Report

This report documents the verification of components within the FlexiRule architecture, distinguishing between those actively exercised by production execution paths and those that are unused, experimental, or legacy.

## Summary of Runtime Usage

| Component | Status | Category | Evidence / Trace Path |
| :--- | :--- | :--- | :--- |
| **RuleCoordinator** | **Active** | Core Orchestration | `hooks.py` → `coordinator.py`. |
| **RuleEngine** | **Active** | Core Execution | `coordinator.py` → `engine.py`. |
| **ProcessRegistry** | **Active** | Metadata | `ProcessHandler` → `ProcessOperationExecutor` → `ProcessRegistry`. |
| **ProcessOperationExecutor** | **Active** | Execution | `ProcessHandler` → `ProcessOperationExecutor` (Contract V2). |
| **ActionHandlers** | **Active** | Execution | `RuleEngine` → `HandlerRegistry` → `*Handler`. |
| **Runtime Registry Cache** | **Active** | Performance | `RuleCoordinator.get_runtime_registry`. |
| **Action Plan Cache** | **Active** | Performance | `RuleEngine` → `action_plan_cache.py`. |
| **Rule Scheduler** | **Active** | Trigger | `hooks.py` → `scheduler.py` → `RuleScheduler`. |
| **Data Review Task** | **Unused** | Experimental | Exists in `doctype/` but no references in `core/` or `action_handlers/`. |
| **`_call_process_with_retry`** | **Legacy** | Execution | Exists in `engine.py` but current `ProcessHandler` uses `ProcessOperationExecutor`. |
| **Switch Action** | **Partial** | Feature | Defined in contracts but marked as `RELEASE_DISABLED` in `contracts.js`. |

---

## Detailed Component Verification

### 1. Core Execution Stack (Verified Active)
The primary execution path for document events is fully implemented and actively used.
*   **Trace**: `frappe.model.doc_events` → `flexirule.ruleflow.hooks.execute_rules` → `RuleCoordinator.execute_rules_from_event` → `RuleEngine.execute`.
*   **Status**: **Fully Implemented**.

### 2. Process Architecture (Verified Active)
The extensible process model is the primary way for executing custom business logic.
*   **Trace**: `ProcessHandler.execute` → `ProcessOperationExecutor.execute` → `OperationAdapterRegistry.execute` → `_execute_python_process_operation` → `frappe.get_attr`.
*   **Status**: **Fully Implemented**.

### 3. Cache Architecture (Verified Active)
Multi-layered caching is used to optimize performance.
*   **Trace**: `RuleCoordinator.get_runtime_registry` (Redis) and `RuleEngine` usage of `get_rule_action_plan` (Action Plan Cache).
*   **Status**: **Fully Implemented**.

### 4. Data Review Task (Verified Unused)
The `Data Review Task` and its related child tables exist in the repository but are not currently integrated into the rule execution flow.
*   **Investigation**: Grepping the codebase for "Data Review Task" or "data_review_task" shows no invocations from `RuleEngine`, `ActionHandlers`, or `Processes`.
*   **Status**: **Experimental / Work-in-Progress**.

### 5. Legacy Code & Technical Debt
*   **`RuleEngine._call_process_with_retry`**: This method in `engine.py` appears to be the "V1" way of calling processes. The current `ProcessHandler` (V2) uses `ProcessOperationExecutor` instead. It remains in the codebase as legacy/dead code.
*   **`ConditionCompiler.OPERATOR_MAP['has_changed']`**: This operator is explicitly marked as deprecated in `compiler.py` and returns `True` as a fallback.

### 6. Registry registrations
*   **Action Types**: All types defined in `contracts.js` (except `Switch`) are actively registered and handled in `flexirule/ruleflow/core/action_handlers/`.
*   **Process Adapters**: `validate`, `transform`, `lookup`, `dedupe`, and `batch` are all registered in `OperationAdapterRegistry` but all currently point to the same Python executor.

---

## Verification Findings by Entry Point

| Entry Point | Verified? | Usage Status |
| :--- | :---: | :--- |
| **Rule Builder Save** | Yes | **Active** - Calls `validate_rule_document` and `frappe.client.save`. |
| **Doc Event Execution** | Yes | **Active** - Main rule execution path via hooks. |
| **Scheduler Execution** | Yes | **Active** - Runs via background jobs every minute. |
| **Manual / API Execution** | Yes | **Active** - Used by Rule Builder "Test" button. |
| **Sub-rule Execution** | Yes | **Active** - Handled by `SubRuleHandler`. |
| **Registry Rebuild** | Yes | **Active** - Triggered on Rule save/update. |
| **Metadata Loading** | Yes | **Active** - Used by Rule Builder via `get_contract_dto`. |

## Final Conclusion
The core architectural pillars (Registry, Engine, Handlers, Processes, Cache) are **active and verified**. The most significant "unverified" or "unused" component is the `Data Review Task` system, which exists in metadata but not in the runtime flow.
