# FlexiRule Rule Authoring Guide

> **Ground Truth**: Based on actual behavior of the rule engine and validation service.

---

## 1. Rule Structure

### 1.1 Rule Components

A Rule consists of:

- **Trigger**: When to execute (trigger_type + trigger_event)
- **Conditions**: Optional gate that must pass (compiled_expression)
- **Actions**: Graph of actions to execute

```python
Rule
├── trigger_type: DocType Event | Scheduler Event | Callable Event
├── trigger_event: Before Save | Validate | After Submit | etc.
├── trigger_condition: JSON AST for optional gate
├── compiled_expression: Compiled Python (set on save)
├── document_type: Target DocType
├── priority: 0-20 (higher = first)
├── execution_mode: Synchronous | Asynchronous
├── max_execution_time: 30 (default)
├── actions: [RuleAction child table]
└── permissions: [RulePermission child table]
```

### 1.2 Trigger Types

| Trigger Type        | Use Case                  | Configuration                   |
| ------------------- | ------------------------- | ------------------------------- |
| **DocType Event**   | Document lifecycle events | document_type + trigger_event   |
| **Scheduler Event** | Periodic execution        | document_type (optional filter) |
| **Callable Event**  | Sub-rule execution        | Must be callable (no event)     |

### 1.3 Trigger Events (DocType Event)

| Event                    | Description           | Document Access     |
| ------------------------ | --------------------- | ------------------- |
| `Before Naming`          | Before auto-naming    | Read-only           |
| `Before Insert`          | Before first save     | Full access         |
| `Before Save`            | Before each save      | Full access         |
| `Validate`               | During validation     | Full access         |
| `Before Submit`          | Before submission     | Read-only           |
| `After Insert`           | After first save      | Limited (saved doc) |
| `After Save`             | After each save       | Limited             |
| `On Submit`              | After submission      | Limited             |
| `Before Cancel`          | Before cancellation   | Limited             |
| `On Cancel`              | After cancellation    | Limited             |
| `On Trash`               | Before deletion       | Read-only           |
| `On Update After Submit` | After submit edits    | Limited             |
| `On Change`              | On field value change | Depends on field    |
| `Before Rename`          | Before rename         | Read-only           |
| `After Rename`           | After rename          | Limited             |
| `Before Print`           | Before printing       | Read-only           |

---

## 2. Designing Rules

### 2.1 Rule Design Principles

1. **Single Responsibility**: Each rule should do one thing well
2. **Clear Purpose**: Rules should have a descriptive name and purpose
3. **Minimal Complexity**: Prefer multiple simple rules over one complex rule
4. **Idempotent Where Possible**: Rules should be safe to re-run
5. **Order Matters**: Use priority to control execution order

### 2.2 Action Graph Design

The rule is a directed graph of actions:

```
[Entry Action] → [Action 1] → [Action 2] → ...
                    ↓ (if condition)
                [Action 2a] → [Action 3]
                    ↓ (else)
                [Action 2b] → [Action 3]
```

### 2.3 Start Node

Every rule must have exactly one Entry Action (start node):

- Auto-created if missing (`Rule.ensure_start_node()`)
- Must have `action_id = "root"` or `action_type = "Entry Action"`
- Positioned first in actions list

### 2.4 Flow Control Patterns

#### Sequential Flow

```
[Entry] → [A] → [B] → [C] → [Stop]
```

Simple linear execution.

#### Conditional Branch

```
[Entry] → [Condition]
            ↓ true     ↓ false
          [Action A]  [Action B]
              ↓           ↓
            [Continue]  [Continue]
```

Use `next_step_if_true` and `next_step_if_false`.

#### Multi-Branch (Switch)

```
[Entry] → [Switch: doc.status]
            Draft → [Draft Handler]
            Submit → [Submit Handler]
            Cancel → [Cancel Handler]
            (default) → [Unknown Handler]
```

Use Switch action with config.cases.

#### Loop

```
[Entry] → [Loop: doc.items]
            ↓ body
          [Process Item]
            ↓
          [Loop] ← (goes back if more items)
            ↓ exit
          [After Loop]
```

Loop iterates over collection, executing body for each item.

---

## 3. Common Rule Patterns

### 3.1 Field Validation Rule

Purpose: Validate document fields before save.

```
[Entry] → [Condition: required fields]
            ↓ true           ↓ false
          [Continue]      [Raise Error: missing fields]
```

```python
# Trigger: DocType Event - Before Save
# Condition:
{
    "op": "and",
    "conditions": [
        {"left": {"ref": "doc.customer"}, "op": "is_set"},
        {"left": {"ref": "doc.items"}, "op": "is_set"}
    ]
}
# Actions:
# 1. Entry Action
# 2. Condition (check required fields)
# 3. Set Value (normalize data) - if valid
# 4. Stop (Error) - if invalid
```

### 3.2 Auto-Assignment Rule

Purpose: Assign records based on rules.

```
[Entry] → [Query: find available agent] → [Set Value: assigned_to] → [Notify: agent]
```

### 3.3 Status Transition Rule

Purpose: Enforce valid status transitions.

```
[Entry] → [Condition: current_status == "Draft"]
            ↓ true     ↓ false
          [Switch: target_status]
            Draft → [Stop: Success]
            Pending → [Process: validate pending]
            Approved → [Process: send approval email]
            (default) → [Stop: Error: invalid transition]
```

### 3.4 Data Enrichment Rule

Purpose: Enrich document with external data.

```
[Entry] → [Process: enrich_customer_data]
            ↓
          [Condition: vars.enrichment_score > 0.8]
            ↓ true           ↓ false
          [Set Value: auto_match=1]  [Set Value: auto_match=0]
            ↓                           ↓
          [Continue]               [Notify: review needed]
```

### 3.5 Batch Processing Rule

Purpose: Process multiple records.

```
[Entry] → [Process: fetch_pending_records]
            ↓
          [Loop: vars.pending_records]
            ↓ body
          [Process: process_single]
            ↓
          [Loop] ←
            ↓ exit
          [Notify: batch complete]
```

---

## 4. Action Configuration

### 4.1 Setting Return Variables

When an action produces output, store it for downstream use:

1. **Set Return Variable Name**: Name the output
2. **Set Return Type**: Expected type (Boolean, Dict, List, etc.)
3. **Set Mutation Mode**: How to apply the result

```python
# Example: Query Records with output
Action: Query Records
  operation: "Query List"
  reference_doctype: "Contact"
  return_variable: "contacts"
  return_type: "List of Dict"
  mutation_mode: "Set Context Variable"
```

### 4.2 Using Variables Downstream

```python
# Condition using vars
{
    "op": "and",
    "conditions": [
        {"left": {"ref": "vars.contacts"}, "op": "is_set"},
        {"left": {"ref": "vars.contacts.length"}, "op": ">", "right": {"value": 0}}
    ]
}
```

### 4.3 Input/Output Mapping

**Input Mapping**: Map context variables to operation config

```json
{
	"input_mapping": [
		{ "source": "doc.customer", "target": "customer" },
		{ "source": "vars.search_term", "target": "query" }
	]
}
```

**Output Mapping**: Map operation result to context variables

```json
{
	"output_mapping": [
		{ "source": "result.is_valid", "target": "vars.is_valid" },
		{ "source": "result.score", "target": "vars.match_score" }
	]
}
```

---

## 5. Sub-Rule Design

### 5.1 Sub-Rule Purpose

Sub-Rules enable:

- **Code reuse**: Shared logic across rules
- **Modularity**: Break complex rules into smaller pieces
- **Team collaboration**: Different teams own different sub-rules

### 5.2 Creating a Sub-Rule

1. Create a new Rule with:

    - `trigger_type`: "Callable Event"
    - `exposed_as_subrule`: Checked
    - `is_active`: Yes

2. Design the sub-rule actions

3. Reference from parent rule using Sub-Rule action

### 5.3 Sub-Rule Configuration

```python
Action: Sub-Rule
  rule: "My Sub-Rule"
  skip_conditions: 1  # Skip sub-rule's trigger conditions
  skip_permissions: 0  # Keep permission checks
```

### 5.4 Context Sharing

**WARNING**: Current sub-rule implementation shares `vars` directly. Variables set in sub-rule are visible to parent.

```python
# Parent Rule
vars = {"parent_var": "value"}

# Sub-Rule
vars["sub_var"] = "new_value"  # Also visible in parent

# After Sub-Rule returns
vars = {"parent_var": "value", "sub_var": "new_value"}
```

### 5.5 Sub-Rule Limitations

| Limitation         | Value   | Notes                     |
| ------------------ | ------- | ------------------------- |
| MAX_SUB_RULE_DEPTH | 2       | Nested sub-rules limited  |
| Cycle Detection    | Yes     | Via execution_stack       |
| Context Isolation  | Partial | vars shared, not isolated |

---

## 6. Best Practices

### 6.1 Rule Naming

```
{Verb}_{Entity}_{Purpose}

Examples:
- Validate_Sales_Order_RequiredFields
- Assign_Support_Ticket_RoundRobin
- Calculate_Invoice_Discounts
- Notify_On_Order_Submit
```

### 6.2 Action Labeling

```
{ActionType}_{Purpose}

Examples:
- Condition_CheckStatus
- Process_EnrichCustomer
- SetValue_UpdateStatus
- Notify_SendConfirmation
```

### 6.3 Error Handling

Configure `on_error` for actions that may fail:

| Action Type   | Recommended on_error |
| ------------- | -------------------- |
| Process       | Retry (3 attempts)   |
| Query Records | Continue             |
| Sub-Rule      | Escalate             |
| Set Value     | Continue             |
| Notify        | Continue             |

### 6.4 Performance Considerations

1. **Avoid deep nesting**: Keep rule depth under 10 actions
2. **Use early exits**: Stop processing when condition fails
3. **Limit loops**: Use `max_iterations` config
4. **Cache expensive operations**: Store results in vars

### 6.5 Security

1. **Use SafeFrappeAPI**: Never use raw frappe in conditions
2. **Validate inputs**: Check vars exist before use
3. **Audit permission bypasses**: Document skip_permissions usage
4. **Limit async**: Async actions cannot use output mapping

---

## 7. Anti-Patterns

### 7.1 Circular References

```python
# DON'T: Rule A calls Rule B, Rule B calls Rule A
Rule A → Sub-Rule: Rule B
Rule B → Sub-Rule: Rule A  # CYCLE DETECTED!
```

Solution: Use cycle detection (raises CycleDetectedError)

### 7.2 Infinite Loops

```python
# DON'T: Action points to itself
[Action] → next_step_if_true = [Action]  # Infinite loop!
```

Solution: Loop detection (100 visits per node max)

### 7.3 Deep Nesting

```python
# DON'T: Too many levels of nesting
Rule → Sub-Rule → Sub-Rule → Sub-Rule → Sub-Rule
```

Solution: MAX_SUB_RULE_DEPTH = 2 limits nesting

### 7.4 Unreachable Actions

```python
# DON'T: Action with no incoming edges
[Entry] → [Action 1]
[Action 2]  # No one points to Action 2!
```

Solution: validation_service checks for unreachable actions

### 7.5 Missing Terminal Nodes

```python
# DON'T: Terminal action with next steps
[Stop] → next_step_if_true = [Action 2]  # Should be None!
```

Solution: validation_service validates terminal actions

### 7.6 Unvalidated Variables

```python
# DON'T: Use vars without checking existence
Condition: vars.missing_var == "value"  # Error if not set!
```

Solution: Use `is_set` operator first, or provide defaults

---

## 8. Debugging Rules

### 8.1 Enable Debug Mode

Set `debug_mode: 1` on the rule to enable verbose logging.

### 8.2 Check Execution Log

The Rule Execution Log records:

- Execution path (actions visited)
- Results from each action
- Context snapshot
- Error traces

### 8.3 Dry Run

Use `RuleCoordinator.execute_rule()` with `dry_run=True`:

```python
result = RuleCoordinator.execute_rule(
    "My Rule",
    context={"doc": doc, "dry_run": True}
)
```

### 8.4 Test Mode

Set `test_mode: True` in context to disable timeouts:

```python
engine = RuleEngine(rule_doc, execution_context={"test_mode": True})
```

---

## 9. Validation Checklist

Before activating a rule:

- [ ] Rule has one Entry Action
- [ ] All required fields are set for each action
- [ ] Conditions have compiled expressions
- [ ] No unreachable actions
- [ ] No circular references (Sub-Rules)
- [ ] Terminal actions have no next steps
- [ ] All variables used are defined earlier
- [ ] On Error handlers are configured appropriately
- [ ] Async actions don't use output mapping

---

_Document Version: 1.0_
_Generated from FlexiRule v1.0 source analysis_
