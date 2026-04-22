# 2. Flow Builder Core Concepts

Salesforce Flow Builder is a visual interface that uses a node-based graph structure to model business logic. 

---

## 2.1 Nodes (Elements)
**Description:**
Nodes are the building blocks of a Flow. They perform specific actions like querying data, evaluating logic, or presenting screens.

**Example:**
A "Get Records" node fetching a Contact, followed by a "Decision" node checking if the Contact has an email.

**How this maps to Flexirule:**
Nodes map directly to Flexirule's Vue Flow nodes (`Rule Action`, `Condition`, `Trigger`, etc.). Both systems rely on a directed graph of operations.
**What needs to be implemented or improved:**
- Shift to an extensible, non-hardcoded Node System where "Action" is a category, not a distinct type.
- Fetch all available node specifications (contracts) from the Frappe backend dynamically to populate the left sidebar.
- Implement auto-layout (top-down) using `dagre` in Vue Flow.

---

## 2.2 Connectors
**Description:**
Lines that connect nodes, determining the path and sequence of execution. They define which node executes next.

**Example:**
A connector pointing from a "Trigger" node to an "Assignment" node.

**How this maps to Flexirule:**
Connectors map to Vue Flow edges and the backend `next_action_id` relationships between actions.
**What needs to be implemented or improved:**
- Improve connection validation on activation to prevent unconnected branches or cyclic loops.
- Support clean branching logic (Decision paths).
- Enhance the canvas UX to allow inserting a node between an existing edge using a "+" button.

---

## 2.3 Execution Model
**Description:**
Flows execute sequentially from the Trigger/Start node, following connectors. Data state is carried through "variables" and "flow context".

**Example:**
A flow starts, assigns a variable `var_X = 10`, then proceeds to an action that uses `var_X`.

**How this maps to Flexirule:**
Flexirule's execution engine sequentially parses the defined rule logic, keeping track of context state dictionary `rule_context`.
**What needs to be implemented or improved:**
- Introduce a standardized Rule Lifecycle model (Draft -> Active -> Archived).
- Improve the shared Validation & Testing Layer: The Frappe Validation logic must mirror the Vue Builder testing logic to ensure graph execution consistency. 
