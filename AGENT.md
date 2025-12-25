# AGENT.md — FlexiRule (Gemini & Claude Edition)

This document defines **how AI agents (specifically Google Gemini and Anthropic Claude)** should analyze, modify, and extend the FlexiRule codebase.

Agents must follow this guidance strictly.

---

## Project Summary

**FlexiRule** is a Frappe framework v15+ and the goal is to provide an advanced Rule engine with a **Vue 3 visual rule builder**.

Goals:

* Build rules using Frappe DocType metadata
* Mirror native Frappe filter semantics
* Support extensible rule execution, logging, and actions
* Provide a first-class visual authoring experience

FlexiRule must always feel **native to Frappe**, not external.

---

## Tech Stack

### Backend

* Frappe Framework v15+
* Python <3.10
* Rule Engine

  - Core evaluation engine for rules and actions
  - **Compiled Expression Engine**: Use `frappe.safe_eval` on pre-compiled Python expressions (`_expression` fields).
  - Condition compiler transforms JSON canonical representation into Python expressions stored in Rule / Rule Action DocTypes at save time.

* Decorator-Based Process Methods

  - Registered at migration time to the Process Method DocType

  - Extensible and reusable

* DocTypes
  - Rule
  - Rule Action
  - Process Method
  - Data Review Task
  - Data Review Related Document

* Extensible Process Methods
  - Designed for reuse across multiple rules and scenarios
  - Supports metadata-driven configuration and dynamic execution
### Frontend

* Vue 3
* Pinia
* VueFlow
* Metadata-driven UI and dynamic schema driven UI
* Drag & Drop Action Type builder.
* Multi-Custom Controls for special cases forexample: field Picker.
* Dynamic Configrator Dialog build based on schema fetch from Process Method.
* Custom field & operator renderers
* Condition Builder provide nesting condition builder.

---

## Agent-Specific Behavior Rules

### 🟦 Gemini Agents

Gemini is expected to:

* Perform **broad structural analysis** first
* Identify patterns, inconsistencies, and architectural risks
* Suggest **high-level improvements** before code changes
* Be explicit about assumptions

Gemini **MUST**:

* Explain reasoning step-by-step
* Map frontend ↔ backend behavior clearly
* Validate alignment with Frappe APIs (`get_meta`, DocField, filters)
* Highlight performance or scalability concerns

Gemini **MUST NOT**:

* Skip architectural context
* Propose framework-agnostic abstractions
* Introduce non-Frappe conventions

Expected Output Style:

* Sections with headings
* Clear rationale before implementation
* Optional diagrams (described, not drawn)

---

### 🟪 Claude Agents

Claude is expected to:

* Be **code-precise and implementation-oriented**
* Respect existing patterns and minimal diffs
* Focus on correctness and maintainability

Claude **MUST**:

* Propose concrete file-level changes
* Output clean, readable code
* Follow existing naming conventions
* Keep changes small and composable

Claude **MUST NOT**:

* Refactor unrelated code
* Introduce speculative features
* Change behavior without explanation

Expected Output Style:

* File-by-file changes
* Inline code snippets
* Explicit before/after behavior

---

## Core Domain Rules (Mandatory for All Agents)

### 1. Metadata-Driven Everything

All rule fields, operators, and inputs must derive from:

* `frappe.get_meta`
* `DocField` definitions
* System fields (`docstatus`, `owner`, etc.)

Hardcoding is forbidden.

---

### 2. Frappe DocType–Aligned Configuration Schema (MANDATORY)

All configuration schemas used by the **Configuration Builder** MUST be
strictly representable as valid **Frappe DocType / DocField definitions**.

If a configuration cannot be expressed as a DocType (including Custom Fields),
it is INVALID and MUST be rejected or refactored.

Rules:

- Every entry in `fields` MUST map 1:1 to a valid **DocField**
- Only DocField-compatible keys are allowed  
  (e.g. `fieldtype`, `label`, `fieldname`, `options`, `reqd`, `default`,
  `precision`, `depends_on`, `read_only`, `hidden`, `description`)
- Arbitrary UI-only or framework-specific keys are **FORBIDDEN**
- `Table` fields MUST reference a valid **child DocType** via `options`
- Child table schemas MUST themselves comply with DocField rules
- Any field whose value references a DocType or fieldname MUST resolve dynamically  
  (e.g. `options: parent.document_type` or another schema field)
- Custom or extended fieldtypes are allowed ONLY if they can be
  losslessly converted to DocField-compatible structures

Agents MUST NOT invent new schema concepts, DSLs, or abstractions that
do not exist in Frappe.


Canonical example:
```python
config_schema = {
    "fields": [...],
    "child_tables": {...}
}
```
### 3. Frappe Filter Semantics (MANDATORY)

The condition schema MUST align with native Frappe filter semantics
and be representable as a logical tree of groups and conditions.

This schema is NOT flexible and MUST be followed exactly.

---

#### 3.1 Condition Tree Structure

Rules are represented as a recursive tree:

- **Group node**
  - `op`: `"and"` | `"or"`
  - `conditions`: array of group or condition nodes

- **Condition node**
  - `left`
  - `op`
  - `right`

Empty groups are INVALID and MUST be rejected or pruned.

---

#### 3.2 Left-Hand Side (LHS)

- `left` MUST always be a reference to DocType metadata
- It MUST be expressed using `ref`
- The reference MUST be resolvable via `frappe.get_meta`

```json
"left": {
  "ref": "doc.party_type_group"
}
```
---

#### 3.9 Collection Quantifiers (Child Table Semantics)

The condition schema supports **quantified conditions** over child table
collections, aligned with Frappe child table filtering behavior.

These nodes are NOT logical groups and MUST NOT be treated as `and/or`.

---

##### Supported Quantifiers

- `any`  → at least one row matches
- `all`  → all rows must match
- `none` → no rows may match

---

##### Quantifier Node Structure (MANDATORY)

```json
{
  "id": "<uuid>",
  "op": "any | all | none",
  "collection": "doc.<child_table_fieldname>",
  "alias": "<row_alias>",
  "where": <condition_group>
}
```
## Process Methods & Actions

When working with process methods or actions:

* Follow decorator-based registration
* Keep logic deterministic
* Do not access request globals directly
* Failures must be logged via FlexiRule logs

---

## Logging & Audit Requirements

Every rule execution must:

* Capture input context
* Log execution duration
* Record success/failure status
* Preserve bypass or override flags

---
---
## Data Integrity & Compilation Standards

### 1. Source of Truth
- **Runtime Truth**: The `_expression` fields (e.g., `trigger_condition_expression`, `condition_expression`) are the **ONLY** source of truth for the execution engine.
- **Visual Truth**: The JSON fields (e.g., `trigger_condition`, `condition_json`) are the source for the UI.
- **Synchronization**: `Rule.validate()` MUST explicitly call the compiler to update `_expression` fields from JSON fields.

### 2. Development Standards
- Any new conditional logic added to the system MUST follow the **JSON Source -> Python Expression** pattern.
- **Runtime Interpretation of JSON is FORBIDDEN**.
- Compiler must handle `None` values safely (e.g., `doc.get('field')` vs `doc.field`).

---
## Reference Benchmarks (Inspiration)

Agents should analyze these Frappe features to ensure design and logic parity:

1. **Visual UI:** Reference the `frappe/public/js/frappe/form_builder` for how Frappe implements modern form builder in vue.
2. **Frappe Workflows:** For the state transition logic and action-trigger architecture.
## Output Contract (STRICT)

```
## Summary
## Reasoning
## Proposed Changes
## Files Impacted
## Code (if applicable)
## Risks & Notes
```

---

## Local Test Setup & Execution (MANDATORY)

AI agents must assume a **standard Frappe Bench environment**. erpnext@abdo-PowerEdge-T40:~/frappe-bench$  All testing must be done against a real site.



### Required Commands After Changes

Backend / DocType changes:

```bash
bench --site insight.test migrate
```

Frontend changes:

```bash
bench build --app flexirule
bench clear-cache
```

---


### 4. Tests (If Present)

```bash
bench --site insight.test run-tests --app flexirule
```

Agents must not invent or assume tests that do not exist.

---

### 5. Manual Validation Checklist

Agents must manually verify:

* Rule creation, save, and reload
* Nested condition/group behavior
* Operator validity per fieldtype
* `docstatus` semantics match Frappe
* `link_filters` applied to Link fields
* Rule execution logs created correctly
* No errors in Error Log, server logs, or browser console

---

### 6. Mandatory Disclosure in Responses

For every proposed change, agents **MUST explicitly state**:

* Whether `bench migrate` is required
* Whether `bench build` is required
* Which commands must be executed to test the change

---

## Final Instruction to Agents

You are not just writing code.
You are extending **Frappe-native behavior**.

Be conservative, explicit, and metadata-first.
