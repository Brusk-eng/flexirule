# Runtime Architecture Overview

This document provides a top-level overview of the FlexiRule execution stack, highlighting the primary runtime paths and architectural boundaries.

## Complete Execution Stack

```mermaid
graph TD
    subgraph "Frappe Layer"
        Event[Frappe Doc Event / Scheduler] --> Hooks[flexirule.ruleflow.hooks]
    end

    subgraph "Orchestration Layer"
        Hooks --> Coord[RuleCoordinator]
        Coord --> Registry[(Runtime Registry Cache)]
        Coord --> Eligibility[Eligibility Check: safe_eval]
    end

    subgraph "Execution Layer"
        Eligibility -- Eligible --> Engine[RuleEngine]
        Engine --> PlanCache[(Action Plan Cache)]
        Engine --> HandlerRegistry[Handler Registry]

        subgraph "Action Handlers"
            HandlerRegistry --> Simple[SimpleHandlers: Notify, Stop, etc.]
            HandlerRegistry --> DocAction[DocumentActionHandler]
            HandlerRegistry --> Assignment[AssignmentHandler]
            HandlerRegistry --> SubRule[SubRuleHandler]
            HandlerRegistry --> Process[ProcessHandler]
        end
    end

    subgraph "Process Layer (Declarative Runtime V2)"
        Process --> ProcExec[ProcessOperationExecutor]
        ProcExec --> ProcRegistry[Process Registry]
        ProcExec --> AdapterRegistry[Adapter Registry]
        AdapterRegistry --> Adapter[Python Adapter]
        Adapter[Python Adapter] --> PythonMethod{{Python Method}}
    end

    subgraph "Persistence & Logging"
        Engine -.-> Log[Rule Execution Log]
        PythonMethod -.-> DB[(Database)]
        DocAction -.-> DB
    end

    %% Legend / Status
    classDef verified stroke:#22c55e,stroke-width:2px;
    classDef partial stroke:#f59e0b,stroke-width:2px;
    classDef unused stroke:#94a3b8,stroke-dasharray: 5 5;

    class Event,Hooks,Coord,Registry,Eligibility,Engine,PlanCache,HandlerRegistry,Simple,DocAction,Assignment,SubRule,Process,ProcExec,ProcRegistry,AdapterRegistry,Adapter,PythonMethod,Log,DB verified;
```

## Runtime Path Verification

### 1. Verified Runtime Paths (Green)
*   **Hook Entry**: `hooks.py` → `coordinator.py`.
*   **Engine Flow**: `coordinator.py` → `engine.py` → `action_handlers/`.
*   **Process Execution**: `ProcessHandler` → `ProcessOperationExecutor` → `Python Adapter`.
*   **Caching**: Redis and `frappe.local` layers for Registry and Action Plans.
*   **Logging**: Asynchronous enqueuing of `Rule Execution Log`.

### 2. Optional / Conditional Paths
*   **Async Execution**: Rules or Actions marked as `Asynchronous` are enqueued via `frappe.enqueue`.
*   **Sub-rules**: Triggered only when a `Sub-Rule` action is present in the flow.
*   **Error Rollback**: Triggered only if `on_error: Rollback` is configured and an action fails.

### 3. Partially Implemented Paths
*   **Switch Action**: Registered in the frontend contract but marked as disabled; handler exists but has minimal usage in production rules.

### 4. Unverified / Unused Paths
*   **Data Review System**: `Data Review Task` exists but is not currently reachable from the standard rule execution flow.

## Architectural Boundaries

1.  **Safety Boundary**: `SafeFrappeAPI` and `safe_eval` protect the system from arbitrary code execution during condition evaluation.
2.  **Performance Boundary**: The `Runtime Registry` ensures that the overhead of checking for rules on every document save is minimal.
3.  **Extensibility Boundary**: The `Process` system allows third-party apps to add business logic without modifying the core engine, using a strict JSON-schema-based contract.
