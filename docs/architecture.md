# FlexiRule Architecture

FlexiRule enables deterministic, unified workflow logic through a node-based architecture stored directly in the database.

## System Layers
1. **Frontend Rule Builder**: A Vue 3 application built over `VueFlow` inside the Frappe desk, allowing users to map out Nodes (`Rule Action`) sequentially.
2. **Database Schema**: 
    - `Rule`: Holds metadata (Trigger Type, Priority, Versioning, Sub-rule configurations) and `trigger_condition` (raw JSON).
    - `Rule Action` (Child Table): Connected nodes holding `action_type`, `next_step_if_true`, `next_step_if_false`, `config` (JSON Blob), and compilation outputs.
3. **Execution Engine**: Reads the Rule Graph array. Traverses nodes safely preventing cyclical infinities. Defers logic to the `HandlerRegistry`.
4. **Compile-Time Optimization**: Validates dependencies and generates pure Python syntax from JSON representation for 10x evaluation speed dynamically using safe `frappe.safe_eval`.

## Frappe Design Philosophy
- Operations are backed natively by Frappe DocTypes.
- Sub-rules mirror the function-abstraction design in coding, but visibly.
- Access restrictions enforce role governance (e.g. `permissions` child table for executing Callable Rules).
