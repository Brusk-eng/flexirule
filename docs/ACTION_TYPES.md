# FlexiRule Action Types Reference

> **Ground Truth**: Documented based on actual handler implementations in `flexirule/ruleflow/core/action_handlers/`.

---

## Action Type Contracts

Each action type follows a contract defined in `ruleflow/core/contracts.py`:

```python
ACTION_TYPE_CONTRACT = {
    "ActionType": {
        "required_fields": [...],      # Fields that MUST be set
        "has_next_true": bool,          # Supports next_step_if_true
        "has_next_false": bool,        # Supports next_step_if_false
        "terminal": bool,              # Ends execution (no next steps)
        "css": {"icon": "...", "color": "..."},
        "allowed_mutations": [...],     # Valid mutation modes
        "mandatory_fields": {...},     # Fields required for specific operations
    }
}
```

---

## 1. Entry Action

**Purpose**: The designated start node of the rule graph.

**Handler**: `simple_actions.py` → `EntryActionHandler`

### Fields

| Field               | Required | Description              |
| ------------------- | -------- | ------------------------ |
| `action_id`         | Yes      | Must be `"root"`         |
| `action_type`       | Yes      | Must be `"Entry Action"` |
| `action_label`      | Yes      | Display name             |
| `next_step_if_true` | No       | First action to execute  |
| `is_enabled`        | Yes      | Default: 1               |

### Execution Logic

```python
class EntryActionHandler(ActionHandler):
    action_type = "Entry Action"

    def execute(self, action, context, engine):
        return None, action.next_step_if_true
```

Simply passes through to the next action.

### Usage Notes

- Auto-created by `Rule.ensure_start_node()` if missing
- Always positioned first in the actions list
- Cannot be deleted while other actions exist

---

## 2. Condition

**Purpose**: Branch the flow based on a logical evaluation.

**Handler**: `condition.py` → `ConditionHandler`

### Fields

| Field                  | Required | Description                              |
| ---------------------- | -------- | ---------------------------------------- |
| `condition_json`       | Yes      | JSON AST from UI condition builder       |
| `condition_expression` | Auto     | Compiled Python expression (set on save) |
| `next_step_if_true`    | No       | Next action if condition is True         |
| `next_step_if_false`   | No       | Next action if condition is False        |

### Execution Logic

```python
def execute(self, action, context, engine):
    if not action.condition_expression:
        if action.condition_json:
            raise ValueError("Action has condition_json but no compiled condition_expression")
        result = True  # Empty condition passes
    else:
        result = engine._evaluate_python_condition(action.condition_expression, context)

    next_id = action.next_step_if_true if result else action.next_step_if_false
    return result, next_id
```

### Condition JSON Format

```json
{
	"op": "and",
	"conditions": [
		{ "left": { "ref": "doc.status" }, "op": "==", "right": { "value": "Draft" } },
		{ "left": { "ref": "doc.amount" }, "op": ">=", "right": { "value": 1000 } }
	]
}
```

### Supported Operators

| Operator     | Description          | Example                             |
| ------------ | -------------------- | ----------------------------------- |
| `==`         | Equals               | `doc.status == "Draft"`             |
| `!=`         | Not equals           | `doc.status != "Cancelled"`         |
| `>`          | Greater than         | `doc.amount > 1000`                 |
| `<`          | Less than            | `doc.priority < 5`                  |
| `>=`         | Greater or equal     | `doc.qty >= 10`                     |
| `<=`         | Less or equal        | `doc.qty <= 100`                    |
| `in`         | In list              | `doc.status in ["Draft", "Submit"]` |
| `not in`     | Not in list          | `doc.type not in ["A", "B"]`        |
| `like`       | Contains (substring) | `doc.name like "INV%"`              |
| `not like`   | Does not contain     | `doc.name not like "%test%"`        |
| `is_set`     | Has value            | `doc.email is_set`                  |
| `is_not_set` | Empty/null           | `doc.remarks is_not_set`            |

### Collection Conditions

```json
{
	"op": "any",
	"collection": "doc.items",
	"alias": "item",
	"where": {
		"op": "and",
		"conditions": [{ "left": { "ref": "item.qty" }, "op": ">", "right": { "value": 10 } }]
	}
}
```

Collection operators: `any`, `all`, `none`

---

## 3. Process

**Purpose**: Execute a Process operation with configuration.

**Handler**: `process.py` → `ProcessHandler`

### Fields

| Field             | Required    | Description                                           |
| ----------------- | ----------- | ----------------------------------------------------- |
| `process_name`    | Yes         | Name of Process DocType                               |
| `operation`       | Yes         | Operation function name                               |
| `config`          | No          | JSON configuration                                    |
| `input_mapping`   | No          | Map context vars to config                            |
| `output_mapping`  | No          | Map result to context vars                            |
| `return_variable` | Conditional | Required if output_mapping or writes_to=Context       |
| `return_type`     | No          | Expected return type                                  |
| `mutation_mode`   | No          | How to apply result                                   |
| `retry_count`     | No          | Number of retries (default: 0)                        |
| `timeout`         | No          | Max execution seconds (default: 30)                   |
| `on_error`        | No          | Error handling: Stop/Continue/Retry/Rollback/Escalate |
| `is_async`        | No          | Execute in background (cannot use output_mapping)     |

### Execution Logic

```python
def execute(self, action, context, engine):
    process_name = action.process_name
    operation = action.operation

    config = engine._get_action_config(action)

    # Apply input mapping
    if action_config.get("input_mapping"):
        config = apply_input_mapping(context, input_mapping, config)

    # Execute with retry
    result = engine._call_process_with_retry(
        process_doc, operation, config, context,
        retry_count=action.retry_count or 0,
        timeout=action.timeout or 30
    )

    return result, action.next_step_if_true
```

### Runtime Contract Enforcement

The engine enforces these contracts at execution time:

1. **requires_doc**: Fails if `context.doc` is None
2. **writes_to == "Document"**: Warning logged for "After" events
3. **transactional**: Wrapped in savepoint for rollback
4. **output_schema**: Validation warning (non-fatal)

### Config Structure

```json
{
	"input_mapping": [
		{ "source": "vars.customer_id", "target": "customer" },
		{ "source": "doc.amount", "target": "amount" }
	],
	"output_mapping": [
		{ "source": "result.is_valid", "target": "vars.is_valid" },
		{ "source": "result.score", "target": "vars.match_score" }
	],
	"my_field": "my_value"
}
```

---

## 4. Loop

**Purpose**: Iterate over a collection (child table or list).

**Handler**: `loop.py` → `LoopHandler`

**Status**: Release-disabled (see `contracts.py:160`)

### Fields

| Field                | Required | Description                             |
| -------------------- | -------- | --------------------------------------- |
| `config`             | Yes      | Must contain `iterator` or `collection` |
| `next_step_if_true`  | Yes      | Loop body actions                       |
| `next_step_if_false` | No       | Exit path                               |

### Config Structure

```json
{
	"iterator": "doc.items", // Expression resolving to list
	"alias": "item", // Variable name for current item
	"max_iterations": 10000 // Safety limit
}
```

### Execution Logic

```python
def execute(self, action, context, engine):
    # Initialize loop state
    if "_loops" not in context["vars"]:
        context["vars"]["_loops"] = {}

    loop_state = context["vars"]["_loops"].get(action.action_id, {"index": 0})

    config = engine._get_action_config(action)
    iterator_name = config.get("iterator")
    item_alias = config.get("alias", "item")

    items = engine._evaluate_python_condition(iterator_name, context)

    current_index = loop_state["index"]

    if current_index < len(items):
        # Set current item
        context["vars"][item_alias] = items[current_index]
        context["vars"]["loop"] = {
            "index": current_index,
            "first": current_index == 0,
            "last": current_index == len(items) - 1,
            "length": len(items),
        }

        loop_state["index"] += 1
        context["vars"]["_loops"][action.action_id] = loop_state

        return True, action.next_step_if_true  # Continue to body
    else:
        # Loop complete - cleanup
        del context["vars"]["_loops"][action.action_id]
        return False, action.next_step_if_false  # Exit
```

### Usage Pattern

```
[Loop Node] ──body──> [Action to repeat] ──back to── [Loop Node]
                         │
                         └──exit──> [Next Action after loop]
```

---

## 5. Switch

**Purpose**: Multi-case branching based on a value.

**Handler**: `switch.py` → `SwitchHandler`

**Status**: Release-disabled (see `contracts.py:160`)

### Fields

| Field               | Required | Description                           |
| ------------------- | -------- | ------------------------------------- |
| `config`            | Yes      | Must contain `expression` and `cases` |
| `next_step_if_true` | No       | Default case (when no match)          |

### Config Structure

```json
{
	"expression": "doc.status",
	"cases": {
		"Draft": "action_id_1",
		"Pending": "action_id_2",
		"Approved": "action_id_3"
	}
}
```

### Execution Logic

```python
def execute(self, action, context, engine):
    config = engine._get_action_config(action)

    expression = config.get("expression")
    cases = config.get("cases", {})

    # Evaluate expression
    val = engine._evaluate_python_condition(expression, context)

    # Match case (try original value then string conversion)
    next_id = cases.get(val) or cases.get(str(val)) or action.next_step_if_true

    return val, next_id
```

---

## 6. Stop

**Purpose**: Terminate execution normally.

**Handler**: `simple_actions.py` → `StopHandler`

### Fields

| Field            | Required    | Description                    |
| ---------------- | ----------- | ------------------------------ |
| `operation`      | No          | "Success" (default) or "Error" |
| `value_template` | Conditional | Required if operation="Error"  |

### Execution Logic

```python
def execute(self, action, context, engine):
    mode = getattr(action, "operation", None) or "Success"

    if mode == "Error":
        value_template = getattr(action, "value_template", "") or "Rule execution stopped"
        template_context = {
            "doc": context.get("doc"),
            "vars": context.get("vars", {}),
            "frappe": SafeFrappeAPI(),
            "utils": frappe.utils,
        }
        message = frappe.render_template(value_template, template_context)
        frappe.throw(message)  # Raises ValidationError

    return None, None  # Clean termination - no next action
```

### Usage

- Place at end of branches where no further action is needed
- Use "Error" mode to halt with validation message

---

## 7. Wait

**Purpose**: Pause execution for a duration.

**Handler**: `simple_actions.py` → `WaitHandler`

### Fields

| Field     | Required | Description                       |
| --------- | -------- | --------------------------------- |
| `config`  | No       | May contain `duration` in seconds |
| `timeout` | No       | Alternative to config.duration    |

### Execution Logic

```python
def execute(self, action, context, engine):
    config = engine._get_action_config(action)

    duration = config.get("duration", 0)
    if not duration and action.timeout:
        duration = action.timeout

    if duration > 0:
        time.sleep(duration)

    return None, action.next_step_if_true
```

---

## 8. Set Value

**Purpose**: Update a document field using Jinja template.

**Handler**: `simple_actions.py` → `SetValueHandler`

### Fields

| Field             | Required | Description                   |
| ----------------- | -------- | ----------------------------- |
| `target_field`    | Yes      | Field name to update          |
| `value_template`  | Yes      | Jinja template for value      |
| `return_variable` | No       | Store result in this variable |

### Execution Logic

```python
def execute(self, action, context, engine):
    target_field = getattr(action, "target_field", None)
    value_template = getattr(action, "value_template", "") or ""

    template_context = {
        "doc": context.get("doc"),
        "vars": context.get("vars", {}),
        "frappe": SafeFrappeAPI(),
        "utils": frappe.utils,
    }

    rendered_value = frappe.render_template(value_template, template_context)

    doc = context.get("doc")
    if doc and hasattr(doc, "set"):
        doc.set(target_field, rendered_value)

    return rendered_value, action.next_step_if_true
```

### Template Variables

Available in Jinja templates:

- `doc` - Current document
- `vars` - Execution variables
- `frappe` - SafeFrappeAPI (read-only)
- `utils` - frappe.utils

### Validation

`Rule._validate_set_value_editable()` checks:

- Field exists on DocType
- Field is editable for current trigger event
- For "On Submit" events, field must have `allow_on_submit` enabled

---

## 9. Raise Error

**Purpose**: Terminate with ValidationError.

**Handler**: `simple_actions.py` → `RaiseErrorHandler`

### Fields

| Field            | Required | Description                    |
| ---------------- | -------- | ------------------------------ |
| `value_template` | Yes      | Error message (Jinja template) |

### Execution Logic

```python
def execute(self, action, context, engine):
    value_template = getattr(action, "value_template", "") or "Validation Error"

    template_context = {
        "doc": context.get("doc"),
        "vars": context.get("vars", {}),
        "frappe": SafeFrappeAPI(),
        "utils": frappe.utils,
    }

    message = frappe.render_template(value_template, template_context)
    frappe.throw(message)  # Raises ValidationError
```

---

## 10. Notify

**Purpose**: Send notifications to users.

**Handler**: `simple_actions.py` → `NotifyHandler`

### Fields

| Field            | Required | Description                                   |
| ---------------- | -------- | --------------------------------------------- |
| `operation`      | Yes      | Notification type                             |
| `value_template` | Yes      | Message content (Jinja template)              |
| `config`         | No       | Additional config (recipients, subject, etc.) |

### Notification Types

| Operation             | Description              | Config Requirements     |
| --------------------- | ------------------------ | ----------------------- |
| `Toast`               | Browser alert            | None                    |
| `System`              | Realtime publish to user | None                    |
| `Email`               | Send email               | `recipients`, `subject` |
| `System Notification` | Create Notification Log  | `subject`, `for_user`   |
| `Provider`            | Hook-registered provider | `provider`, `recipient` |

### Execution Logic

```python
def execute(self, action, context, engine):
    notification_type = self._normalize_mode(action.operation)
    value_template = action.value_template
    config = engine._get_action_config(action)

    message = self._render_template(value_template, context)

    if notification_type == "Toast":
        frappe.msgprint(message, alert=True)
    elif notification_type == "System":
        frappe.publish_realtime("msgprint", {"message": message, "alert": True}, user=frappe.session.user)
    elif notification_type == "Email":
        frappe.sendmail(recipients=..., subject=..., message=...)
    elif notification_type == "System Notification":
        notification = frappe.get_doc({"doctype": "Notification Log", ...})
        notification.insert(ignore_permissions=True)
    elif notification_type == "Provider":
        self._send_via_provider(config, context, message)
```

---

## 11. Sub-Rule

**Purpose**: Execute another rule as a nested sub-process.

**Handler**: `sub_rule.py` → `SubRuleHandler`

### Fields

| Field                     | Required    | Description                                   |
| ------------------------- | ----------- | --------------------------------------------- |
| `rule`                    | Yes         | Target Rule name                              |
| `skip_conditions`         | No          | Skip sub-rule trigger conditions (default: 1) |
| `skip_permissions`        | No          | Bypass permission checks                      |
| `permission_audit_reason` | Conditional | Required if skip_permissions=1                |

### Target Rule Requirements

- `trigger_type` must be "Callable Event"
- `exposed_as_subrule` must be checked
- Must be active
- Must have same `document_type` as parent rule

### Execution Logic

```python
def execute(self, action, context, engine):
    sub_rule_name = action.rule

    sub_rule = frappe.get_cached_doc("Rule", sub_rule_name)

    # Validation
    assert sub_rule.trigger_type == "Callable Event"
    assert sub_rule.is_exposed_as_subrule()
    assert sub_rule.document_type == engine.rule.document_type

    # Cycle detection
    execution_stack = context["meta"]["execution_stack"]
    if sub_rule_name in execution_stack:
        raise CycleDetectedError("Cross-rule cycle detected")

    # Depth limit (MAX_SUB_RULE_DEPTH = 2)
    if current_depth >= 2:
        raise CycleDetectedError("Max sub-rule depth exceeded")

    # Prepare sub-context
    sub_context = context.copy()
    sub_context["meta"]["execution_stack"] = [*execution_stack, engine.rule.name]

    # Execute
    sub_engine = RuleEngine(sub_rule_doc, execution_context=sub_context)
    result_context = sub_engine.execute(context.get("doc"))

    # Merge vars back to parent
    context["vars"].update(result_context.get("vars", {}))

    return None, action.next_step_if_true
```

### Isolation Limitations

**CURRENT BEHAVIOR**: Context is NOT fully isolated.

- `vars` dict is shared and modified directly
- Sub-rule can overwrite parent variables
- No scope protection

**This can cause debugging difficulty and unexpected side effects.**

---

## 12. Query Records

**Purpose**: Query database for records.

**Handler**: `query_records.py` → `QueryRecordsHandler`

### Fields

| Field               | Required | Description                 |
| ------------------- | -------- | --------------------------- |
| `operation`         | Yes      | Query mode                  |
| `reference_doctype` | Yes      | Target DocType              |
| `reference_docname` | No       | For Query Doc mode          |
| `config`            | No       | Mode-specific configuration |
| `return_variable`   | No       | Store result                |
| `mutation_mode`     | No       | How to apply result         |

### Query Modes

| Operation      | Description                      | Returns         |
| -------------- | -------------------------------- | --------------- |
| `Query List`   | `frappe.get_list()`              | List of dicts   |
| `Query Doc`    | `frappe.get_doc()`               | Dict (document) |
| `Exist Record` | `frappe.db.exists()`             | Boolean         |
| `Query Report` | `frappe.desk.query_report.run()` | Report data     |
| `Count`        | `frappe.db.count()`              | Integer         |
| `Sum`          | Aggregation                      | Number          |
| `Average`      | Aggregation                      | Number          |
| `Min`          | Aggregation                      | Number          |
| `Max`          | Aggregation                      | Number          |
| `Group By`     | Aggregation with group           | List of dicts   |

### Allowed Mutations

Only these mutation modes are allowed for Query Records:

- `Set Context Variable`
- `Update Context Variable`
- `Append to Context Variable`

---

## 13. Document Action

**Purpose**: Create, update, or delete documents.

**Handler**: `create_doc.py` → `DocumentActionHandler`

### Fields

| Field               | Required    | Description                 |
| ------------------- | ----------- | --------------------------- |
| `operation`         | Yes         | Action mode                 |
| `reference_doctype` | Yes         | Target DocType              |
| `reference_docname` | Conditional | For Update/Delete modes     |
| `config`            | No          | Mode-specific configuration |
| `return_variable`   | No          | Store result                |
| `mutation_mode`     | No          | How to apply result         |

### Document Modes

| Operation         | Description              |
| ----------------- | ------------------------ |
| `Create New`      | Insert new document      |
| `Update Existing` | Load and update document |
| `Delete Record`   | Delete document          |
| `Create ToDo`     | Create linked ToDo       |
| `Add Comment`     | Add timeline comment     |

### Config for Create New

```json
{
	"field_mappings": [
		{ "source": "doc.customer", "target": "customer" },
		{ "source": "vars.total", "target": "grand_total" }
	],
	"static_values": {
		"company": "My Company",
		"doctype": "Sales Invoice Item"
	}
}
```

### Config for Update Existing

```json
{
    "docname_expression": "doc.invoice_ref",
    "field_mappings": [...],
    "static_values": {...}
}
```

### Config for Create ToDo

```json
{
	"assigned_to": "{{ doc.owner }}",
	"description": "Task for {{ doc.name }}",
	"priority": "Medium"
}
```

### Config for Add Comment

```json
{
	"comment_text": "Status changed to {{ vars.new_status }}",
	"comment_type": "Comment"
}
```

---

## Mutation Modes Reference

| Mode                         | Applies To | Behavior                                    |
| ---------------------------- | ---------- | ------------------------------------------- |
| `Set Doc Field`              | All        | `doc.set(var_name, value)`                  |
| `Update Doc Field`           | All        | `doc.set(k, v)` for all keys                |
| `Set Context Variable`       | All        | `vars[var_name] = value`                    |
| `Update Context Variable`    | All        | `vars[var_name].update(value)`              |
| `Append to Context Variable` | All        | `vars[var_name].append(value)`              |
| `Batch Database Set`         | All        | `frappe.db.set_value(doctype, name, value)` |

---

## Error Handling Reference

| on_error         | Behavior                                               |
| ---------------- | ------------------------------------------------------ |
| `Stop` (default) | Re-raise exception, terminate flow                     |
| `Continue`       | Log warning, continue to next_step_if_true             |
| `Retry`          | Exponential backoff (1s, 2s, 4s...), up to retry_count |
| `Rollback`       | Rollback to savepoint, then re-raise                   |
| `Escalate`       | Re-raise same exception                                |

---

_Document Version: 1.0_
_Generated from FlexiRule v1.0 source analysis_
