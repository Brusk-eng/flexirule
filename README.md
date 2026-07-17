<div align="center">
  <img width="180" alt="flexiRule" src="flexirule/public/icons/flexirule.svg" />

  <h1>FlexiRule</h1>

[![CI](https://github.com/Sendipad/flexirule/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/Sendipad/flexirule/actions/workflows/ci.yml?query=branch%3Adevelop)
![Beta Release](https://img.shields.io/badge/release-beta-orange)
![Frappe](https://img.shields.io/badge/built%20for-Frappe%20v15%2B-blue)

  <p><strong>Declarative Business Automation & Visual Orchestration Platform for Frappe and ERPNext</strong></p>

</div>

<div align="center">
  <img width="1307" height="751" alt="rule_builder" src="https://github.com/user-attachments/assets/8ff096b5-09b9-467a-925b-42530542c73d" />
  <p>
    <em>The visual, graph-based canvas serves as the single source of truth for your business workflows.</em>
  </p>
</div>

---

## 🚀 Overview

In enterprise systems built on **Frappe** and **ERPNext**, business logic frequently turns into a fragmented web of Python hooks scattered across multiple custom apps. This unstructured approach introduces several challenges:

* **Implicit Ordering**: It is difficult to determine which hook executes first, leading to unpredictable side effects.
* **Lack of Observability**: Debugging execution paths and tracing runtime failures is complex.
* **High Upgrade Risk**: Heavy dependency on internal API paths increases maintenance overhead.
* **Silent Failure States**: Uncaught errors can leave database transactions in an inconsistent state.

**FlexiRule** changes the paradigm by providing a **visual, graph-based orchestration layer**. Rather than spreading hidden code across your system, you design, validate, and execute declarative business logic with full control, complete observability, and built-in transaction safety.

---

## 💎 Why FlexiRule?

FlexiRule provides a modern, structured alternative to scattered Server Scripts and custom hook code:

* **Centralized Logic**: Consolidate your business rules into a single, auditable dashboard instead of maintaining custom hooks across multiple repositories.
* **Deterministic Orchestration**: Define clear execution paths using direct visual connections, resolving hook execution ordering issues.
* **Safe Sandboxed Evaluation**: Evaluates condition checks in a read-only environment using a sandboxed API, preventing accidental state changes during criteria checks.
* **Schema-Driven UI**: Forms and configuration panels are auto-generated from dynamic schemas, providing developers with structured inputs and validations.
* **Enterprise Governance**: Includes built-in execution safeguards, including savepoint-based transaction rollbacks, role-based execution bypasses, and permission audit logs.

---

## 🖼️ Visual Tour

<details>
<summary><strong>View Visual Walkthrough</strong></summary>

<br/>
<div align="center">
  <img width="1280" height="583" alt="Rule List Overview" src="https://github.com/user-attachments/assets/212b96bf-9259-426b-90c1-dd55efce0bd7" />
  <p><em>Centralized Rule Management Interface for filtering and managing active flows.</em></p>

  <img src="https://github.com/user-attachments/assets/41ac7963-f334-4fb2-bf0a-49409956c4a3" alt="Declarative condition tree builder" width="900" style="border-radius:14px;" />
  <p><em>Declarative condition tree builder with nested AND/OR evaluation.</em></p>

  <img width="1294" height="648" alt="Rule Builder Interface" src="https://github.com/user-attachments/assets/b5e00fd1-c171-48bf-abc6-93c4de93f6a1" />
  <p><em>VueFlow Rule Builder with drag-and-drop node configurations and topological routing.</em></p>

  <img width="1331" height="627" alt="Debugger Path Tracing" src="https://github.com/user-attachments/assets/e1e7bf85-7f27-4be1-9999-f9dcdd511603" />
  <p><em>Real-Time execution path tracing and state tracing directly on the canvas.</em></p>

  <img width="1029" height="722" alt="Query Records Configuration" src="https://github.com/user-attachments/assets/2bc38417-092e-4623-8324-dc736629213f" />
  <p><em>Query node configuration for introspecting fields, mapping inputs, and filtering database records.</em></p>

  <img width="1029" height="722" alt="Custom Field Assignment" src="https://github.com/user-attachments/assets/1e9201fc-b8fc-4308-86b5-2b80cc6ac25a" />
  <p><em>Batch assignment step supporting multi-operator mutations on document fields and context variables.</em></p>

  <img width="1029" height="722" alt="Notification Designer" src="https://github.com/user-attachments/assets/fedaf6aa-63d8-418d-9e32-30c422fe93cf" />
  <p><em>Flexible notifications supporting toasts, system alerts, or standard emails.</em></p>

  <img src="https://github.com/user-attachments/assets/97c23be2-f939-4190-ad34-c1318bd2dece" alt="Process Operation configuration" width="900" style="border-radius:14px;" />
  <p><em>Process Operations for running file-backed custom code with schema-driven inputs.</em></p>
</div>

</details>

---

## 🧠 Core Concepts

FlexiRule separates trigger criteria, execution paths, and business logic into structured components:

* **Rule**: The entry point that defines *when* execution should trigger, binding to DocType database hooks, background scheduler intervals, or manual callable events.
* **Action Type**: Reusable visual action definitions declaring layout styles, required parameters, and outcome capabilities.
* **Rule Action**: A specific step (node) in the execution graph that processes input configurations and routes control to successor nodes based on execution outcomes.
* **Process**: A file-backed Python module that acts as a secure, performance-optimized container for custom code.
* **Operation**: An individual function within a Process that exposes its parameters through a declarative JSON Schema.
* **Runtime Context**: An isolated execution namespace carrying the root document, context variables, and metadata.
* **Execution Graph**: The topologically ordered sequence of steps representing your business workflow.

---

## 🏗️ Architecture Overview

FlexiRule decouples event-driven triggers from execution mechanics and business logic processing:

```mermaid
graph TD
    Trigger[Rule Trigger: Hook, CRON, or Callable] --> Coordinator[Rule Coordinator: Filters & Prunes]
    Coordinator --> Registry[Runtime Registry: Cache Layer]
    Registry --> Engine[Rule Engine: Node Traversal Manager]
    Engine --> ActionRegistry[Action Registry: Strategy Handlers]
    ActionRegistry --> ProcessRuntime[Process Runtime: Dynamic Schema-Validated Code]
    ProcessRuntime --> Logging[Execution Logging: Non-blocking Background Queue]
```

### Component Responsibilities

* **Rule Trigger**: Binds database lifecycle events, scheduler intervals, or programmatic calls to start execution.
* **Rule Coordinator**: Resolves active rules and performs early eligibility pruning using pre-compiled conditions.
* **Runtime Registry**: A distributed cache layer that holds active rule maps to prevent database lookups during event hooks.
* **Rule Engine**: Traverses the execution graph topologically, manages context state, and handles retry and transaction boundaries.
* **Action Registry**: Maps individual execution steps to their respective strategy implementations (e.g., Conditions, Assignments, Loops).
* **Process Runtime**: Orchestrates custom processes, maps context variables, and validates configurations against JSON schemas.
* **Execution Logging**: Persists detailed execution traces asynchronously to keep user transactions fast and lightweight.

---

## 🔄 Execution Lifecycle

FlexiRule executes workflows through a deterministic path, utilizing database savepoints and background queues for safe, fast operations:

```mermaid
flowchart TD
    A([Trigger Event]) --> B[Rule Discovery]
    B --> C{Watched Fields Change?}
    C -- No --> Skip[Skip Execution]
    C -- Yes --> D[Load Rule from Registry Cache]
    D --> E{Eligible: Evaluate Pre-compiled Conditions}
    E -- No --> LogSkip[Log Early Skip & Exit]
    E -- Yes --> F[Initialize Isolated Runtime Context]
    F --> G{Traverse Nodes Topologically}
    G --> H[Resolve Input Mappings]
    H --> I[Execute Pluggable Action Handler]
    I --> J{Execution Success?}

    J -- No --> K{On Error Policy?}
    K -- Retry --> Retry[Apply Exponential Backoff]
    Retry --> H
    K -- Continue --> L[Advance to True Node]
    L --> G
    K -- Rollback --> Roll[Rollback to Savepoint]
    Roll --> Fail[Throw ValidationError]
    K -- Stop/Escalate --> Fail

    J -- Yes --> M[Map Result to Context Variables]
    M --> N{Has Next Node?}
    N -- Yes --> G
    N -- No --> O[Enqueue Execution Log Asynchronously]
    O --> P([Complete Transaction])
```

The execution flow begins with **Rule Discovery** and optimizes database performance via **Watched Fields**. If checked fields have changed, the pre-compiled criteria are evaluated in a read-only sandboxed environment. Upon passing, an isolated **Runtime Context** is initialized, and nodes are executed topologically. Errors are caught and handled according to the node's configured policy (`Retry`, `Continue`, `Rollback` to savepoint, or `Stop`). Once the path is completed, audit logs are pushed to an asynchronous background worker before the transaction commits.

---

## 🛠️ Key Features

* **Visual VueFlow Canvas**: Edit workflows, set outcomes, and visual transitions within an interactive graph.
* **Sandboxed Safe Execution**: Criteria evaluations are restricted to read-only database queries, preventing accidental data writes.
* **Topological Traversal**: Node routing resolves execution sequence, preventing infinite recursion loops.
* **Robust Error Handling**: Out-of-the-box support for `Retry` (with exponential backoff), `Continue`, `Rollback` (via db savepoints), and `Escalate` behaviors.
* **Cache-First Dispatch**: Minimizes database overhead by storing compiled rules inside a distributed registry.
* **Watched Fields Optimization**: Automatically prunes rules early if the modified fields do not overlap with fields analyzed in the rule's active criteria.
* **Variable Isolation**: Isolate context variables during sub-rule execution to prevent namespace collisions.
* **Audit & Compliance Controls**: Explicitly restrict workflows by user roles, bypass permissions with mandatory audit reasons, and persist detailed execution path traces.

---

## 🔌 Extensibility Model

Developers can extend FlexiRule at multiple layers to integrate custom business logic:

* **Action Types**: Custom execution blocks can be registered to provide reusable, platform-wide capabilities (e.g., custom integrations or formatters).
* **Processes & Operations**: Package custom logic into file-backed Python classes. FlexiRule automatically discovers these methods, letting you expose inputs through standard JSON schemas that automatically render as validated forms in the UI.
* **Dynamic Config Schemas**: Define dynamic layout fields, allowing the builder UI to generate user-friendly configuration panels on the fly.
* **Custom UI Controls**: Wire custom controls directly into action properties, supporting advanced data selectors and interactive widgets.

---

## 📬 API Capabilities

FlexiRule provides a robust suite of whitelisted endpoints to programmatically manage, test, and execute rules:

* **Manual Execution**: Run rules programmatically on specific records.
* **Sandboxed Simulation**: Perform a dry-run execution that rolls back database changes and returns the exact execution path trace.
* **State & Lifecycle Management**: Transition rules between `Draft` and `Active` states.
* **Path Prediction**: Inspect criteria and predict node traversal based on current field values.
* **Schema Introspection**: Retrieve active schemas, dynamic form structures, and active variable contexts at specific steps of the execution graph.

---

## 📦 Installation

```bash
# Get the app from the repository
bench get-app flexirule https://github.com/Sendipad/flexirule.git

# Install to your target site
bench --site [your-site] install-app flexirule
```

---

## 🤝 Contributing

Contributions are welcome! If you are interested in improving FlexiRule, please consider:

* Opening a **Bug Report** or submitting a **Feature Request** on GitHub.
* Improving documentation or writing custom Process Operations.
* Submitting a **Pull Request** with bug fixes or optimizations, ensuring you follow [Frappe Coding Guidelines](https://frappeframework.com/docs/v15/user/en/guidelines/coding-standards) and confirm that all tests pass.

---

<div align="center">
  <img width="100" alt="flexiRule" src="https://github.com/user-attachments/assets/e3724231-fccc-4f92-89af-6dd7b93c640f" />
  <p><strong>FlexiRule</strong> — Declarative, Visual, and Safe Business Logic for Frappe.</p>
  <p>Built with ❤️ by the community. Distributed under the MIT License.</p>
</div>
