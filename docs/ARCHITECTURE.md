# FlexiRule Architecture Documentation

> **Ground Truth**: This document reflects ACTUAL code behavior, not idealized design. All claims are verified against the source code at `flexirule/ruleflow/core/`.

---

## 1. Execution Model

### 1.1 Entry Point Chain

```
Doc Event (hooks.py)
  → RuleCoordinator.execute_rules(doc, event_name)
    → RuleCoordinator.execute_rules_from_event(doc, event_name)
      → get_applicable_rules(doctype, event_name) [uses cache]
        → check_eligibility(rule_doc, doc, event_name, old_doc)
          → execute_single_rule(doc, rule_doc, old_doc, event_name)
            → RuleEngine(rule_doc, execution_context).execute(doc, event_name)
              → _execute_graph(context) [main loop]
```

### 1.2 Graph Execution Loop (`_execute_graph`)

The core loop in `engine.py:422-596` follows this flow:

```python
# 1. START: Find root node
current = _get_start_node()  # Entry Action (action_id='root') or first action

# 2. MAIN LOOP: Iterate up to 1000 times
for _iteration in range(max_iterations):
    # 2.1 Timeout check
    if time.time() - context['_start_time'] > context['_timeout']:
        raise BoltonTimeoutError()

    # 2.2 Stop flag check
    if context.get('stop'):
        break  # Clean exit

    # 2.3 Cycle detection (100 visits per node max)
    visits = node_visits[node_id]
    if visits > 100:
        raise CycleDetectedError()

    # 2.4 Execute action via HandlerRegistry
    handler = HandlerRegistry.get(normalize_action_type(current.action_type))
    result, next_id = handler.execute(current, context, self)

    # 2.5 Post-processing (output mapping, return variable, mutation)
    _post_process_action_result(current, result, context)

    # 2.6 Move to next action
    current = _get_action_by_id(next_id)

# 3. END: Return context
return context
```

### 1.3 Error Handling Strategy

Each action has an `on_error` field with options:

- **Stop** (default): Re-raise, terminates flow
- **Continue**: Log warning, continue to next_step_if_true
- **Retry**: Exponential backoff (1s, 2s, 4s...), up to `retry_count` attempts
- **Rollback**: Rollback to savepoint, then re-raise
- **Escalate**: Re-raise same exception

```python
# From engine.py:519-590
if hasattr(current, "on_error"):
    if current.on_error == "Continue":
        current = self._get_action_by_id(current.next_step_if_true)
        continue
    elif current.on_error == "Retry":
        # Exponential backoff: 1s, 2s, 4s...
        wait_time = 2 ** current_attempt
        time.sleep(wait_time)
        continue  # Retry same action
```

### 1.4 Retry Logic Details

- **Retry key**: Stored in `context['vars'][f'_retry_{action_id}']`
- **Backoff**: Exponential (2^attempt seconds)
- **Sync context restriction**: Cannot retry inside synchronous hooks (raises ValidationError)

---

## 2. Context System

### 2.1 Context Structure

```python
context = {
    "doc": <Frappe Document>,           # The document being processed
    "old_doc": <Frappe Document>,      # Document state before save
    "vars": {},                         # Execution variables (scope for mapping)
    "frappe": <SafeFrappeAPI>,          # Read-only Frappe API proxy
    "meta": {
        "rule": "Rule Name",
        "rule_version": 1,
        "engine_version": "1.0",
        "user": "user@example.com",
        "timestamp": "2025-01-01 12:00:00",
        "test_mode": False,
        # Sub-Rule metadata:
        "parent_rule": "Parent Rule Name",     # Set by SubRuleHandler
        "execution_stack": ["RuleA", "RuleB"], # Cross-rule cycle detection
        "call_depth": 1,                        # Sub-Rule nesting depth
    },
    "stop": False,                     # Can be set by Stop action
    "event_name": "Before Save",       # Trigger event
    "_timeout": 30,                     # Execution timeout in seconds
    "_start_time": 1704067200.0,       # Unix timestamp
    "_in_sync_hook": False,             # Set by hooks.py for sync context
}
```

### 2.2 Context Manager (`context_manager.py`)

The `ContextManager` class provides:

- `set_variable(name, value, return_type)` - Set with optional type validation
- `get_variable(name, default)` - Get variable
- `apply_mutation(mutation_mode, var_name, value)` - Apply mutation modes:
    - `Set Doc Field` - `doc.set(var_name, value)`
    - `Update Doc Field` - `doc.set(k, v)` for all keys in dict
    - `Set Context Variable` - `vars[var_name] = value`
    - `Update Context Variable` - `vars[var_name].update(value)`
    - `Append to Context Variable` - `vars[var_name].append(value)`
    - `Batch Database Set` - `frappe.db.set_value(doctype, name, value)`

### 2.3 Mutation Safety

Mutation modes are validated against `contracts.py`:

```python
# Only allowed for action types that declare allowed_mutations
if mutation_mode not in contract.get("allowed_mutations", []):
    raise MethodExecutionError("Mutation mode not allowed")
```

---

## 3. Action Type System

### 3.1 Handler Registry Pattern

All actions use the Strategy Pattern via `HandlerRegistry`:

```python
# action_handlers/__init__.py
class HandlerRegistry:
    _handlers: ClassVar[dict] = {}

    @classmethod
    def get(cls, action_type: str) -> ActionHandler | None:
        cls._ensure_initialized()  # Lazy load all handlers
        return cls._handlers.get(action_type)

    @classmethod
    def _ensure_initialized(cls) -> None:
        # Imports all handlers, triggering registration
        from flexirule.ruleflow.core.action_handlers import (
            condition, create_doc, loop, process,
            query_records, simple_actions, sub_rule, switch
        )
```

### 3.2 Action Handler Contract

All handlers inherit from `ActionHandler`:

```python
class ActionHandler(ABC):
    action_type: str | None = None

    @abstractmethod
    def execute(self, action, context: dict, engine: "RuleEngine") -> tuple[Any, str | None]:
        """
        Returns: (result, next_action_id)
        - result: Any type, stored in path_trace
        - next_action_id: ID of next action or None to stop
        """
        pass

    def validate(self, action, context: dict) -> list:
        """Optional pre-execution validation. Returns list of error strings."""
        return []
```

### 3.3 Built-in Action Types

| Action Type     | Handler File        | Purpose                              |
| --------------- | ------------------- | ------------------------------------ |
| Entry Action    | `simple_actions.py` | Root node, passes through            |
| Condition       | `condition.py`      | Evaluates compiled Python expression |
| Process         | `process.py`        | Executes Process operation           |
| Loop            | `loop.py`           | Iterates over collections            |
| Switch          | `switch.py`         | Multi-case branching                 |
| Stop            | `simple_actions.py` | Terminates execution                 |
| Wait            | `simple_actions.py` | Sleeps for duration                  |
| Set Value       | `simple_actions.py` | Updates document field               |
| Raise Error     | `simple_actions.py` | Throws ValidationError               |
| Notify          | `simple_actions.py` | Sends notifications                  |
| Sub-Rule        | `sub_rule.py`       | Executes another rule                |
| Query Records   | `query_records.py`  | Database queries                     |
| Document Action | `create_doc.py`     | CRUD operations                      |

### 3.4 Condition Evaluation Flow

```
condition_json (JSON AST from UI)
  → Rule.validate() calls compile_conditions()
    → ConditionCompiler.compile(condition_json)
      → condition_expression (Python code string)
  → ConditionHandler.execute()
    → engine._evaluate_python_condition(expression, context)
      → frappe.safe_eval(expression, safe_locals)
```

**Key Security Points:**

- `_evaluate_python_condition` uses `SafeFrappeAPI` (read-only)
- `ConditionCompiler.validate()` checks for invalid patterns
- `method` value type is deprecated and returns None

---

## 4. Process System

### 4.1 Architecture

```
Process DocType (database)
  ├── process_name: Unique identifier
  ├── module: Associated module
  ├── is_standard: "Yes" = file-backed
  └── operations: [Process Operation child table]

Process JSON (file-backed)
  → Synced during migrate via process_sync.py
  → Creates/updates Process DocType records

Process Adapter (Python)
  → ruleflow/process/{name}/{name}.py
  → execute(context, func, config) entry point
```

### 4.2 Process Execution (`process.py` handler)

```python
# From action_handlers/process.py
def execute(self, action, context, engine):
    process_name = action.process_name
    operation = action.operation

    # Parse config and apply input mapping
    config = engine._get_action_config(action)
    if action_config.get("input_mapping"):
        config = apply_input_mapping(context, input_mapping, config)

    # Execute with retry and timeout
    result = engine._call_process_with_retry(
        process_doc, operation, config, context,
        retry_count=action.retry_count or 0,
        timeout=action.timeout or 30
    )
    return result, action.next_step_if_true
```

### 4.3 Runtime Contract Enforcement

In `engine.py:755-856`, `_call_process_with_retry` enforces:

1. **requires_doc**: Fails if context.doc is None
2. **writes_to == "Document"**: Warning logged for "After" events
3. **has_side_effect**: Info logged
4. **transactional**: Wrapped in savepoint for rollback
5. **output_schema**: Validation against schema (warning on failure)

### 4.4 Process Operation Fields

| Field           | Purpose                                      |
| --------------- | -------------------------------------------- |
| `func_name`     | Python function name to call                 |
| `label`         | Display name in UI                           |
| `enabled`       | Whether operation is available               |
| `requires_doc`  | Operation needs context.doc                  |
| `writes_to`     | "Document" / "Context" / "None" / "Database" |
| `transactional` | Supports savepoint rollback                  |
| `config_schema` | JSON Schema for operation config UI          |
| `output_schema` | JSON Schema for return validation            |

---

## 5. Sub-Rule System

### 5.1 Execution Flow

```python
# From sub_rule.py:28-159
def execute(self, action, context, engine):
    sub_rule_name = action.rule

    # Validation
    sub_rule = frappe.get_cached_doc("Rule", sub_rule_name)
    assert sub_rule.trigger_type == "Callable Event"
    assert sub_rule.is_exposed_as_subrule()
    assert sub_rule.document_type == engine.rule.document_type

    # Cycle detection
    execution_stack = context.get("meta", {}).get("execution_stack", [])
    if sub_rule_name in execution_stack:
        raise CycleDetectedError("Cross-rule cycle detected")

    # Prepare sub-context
    sub_context = context.copy()
    sub_context["meta"] = context["meta"].copy()
    sub_context["meta"]["execution_stack"] = [*execution_stack, engine.rule.name]
    sub_context["meta"]["call_depth"] = current_depth + 1

    # Check depth limit (MAX_SUB_RULE_DEPTH = 2)
    if current_depth >= 2:
        raise CycleDetectedError("Max sub-rule depth exceeded")

    # Execute sub-rule
    sub_engine = RuleEngine(sub_rule_doc, execution_context=sub_context)
    result_context = sub_engine.execute(context.get("doc"))

    # Merge vars back
    context["vars"].update(result_context.get("vars", {}))
```

### 5.2 Isolation Model

**Current limitation**: Context is NOT fully isolated. The sub-rule shares and modifies the parent's `vars` dict directly. This can cause:

- Variable shadowing
- Unexpected side effects
- Debugging difficulty

**Recommendation**: Implement proper scope isolation for production use.

---

## 6. Security Model

### 6.1 SafeFrappeAPI

Read-only proxy in `engine.py:129-225`:

```python
class SafeFrappeAPI:
    # Allowed operations:
    - get_value(doctype, filters, fieldname)
    - get_all(doctype, filters, fields, limit_page_length)
    - db_exists(doctype, name)
    - get_meta(doctype)
    - format_value(value, df, doc, currency)

    # Explicitly DENIED:
    - get_doc (use get_value instead)
    - new_doc
    - delete_doc
    - db_set_value
    - db.sql
    - db.commit / db.rollback
```

### 6.2 skip_permissions Guard

In `permissions.py:134-177`:

```python
def can_skip_permissions(action, context=None, throw=True):
    if not int(getattr(action, "skip_permissions", 0)):
        return False

    user_roles = set(frappe.get_roles(user))
    allowed_roles = set(frappe.get_hooks("flexirule_skip_permissions_roles") or
                       {"System Manager"})

    if user != "Administrator" and not user_roles.intersection(allowed_roles):
        raise PermissionError("skip_permissions requires specific roles")

    # Must have permission_audit_reason
    audit_reason = _extract_skip_permissions_audit_reason(action)
    if not audit_reason:
        raise ValidationError("skip_permissions requires audit reason")
```

### 6.3 Condition Compiler Security

The compiler validates expressions via `validate_safe_eval` in `permissions.py`:

```python
def validate_safe_eval(expression):
    try:
        compile(expression, "<string>", "eval")
    except SyntaxError:
        raise ValidationError("Invalid syntax in expression")
    return True
```

**Note**: This only checks syntax, not semantic safety. The actual safety comes from:

- `frappe.safe_eval` restrictions
- `SafeFrappeAPI` read-only proxy
- No arbitrary method calls in conditions

---

## 7. Graph Model

### 7.1 Implicit Graph Structure

FlexiRule uses an **implicit graph** defined by:

- `next_step_if_true` field on each action
- `next_step_if_false` field (Condition/Switch only)
- `config.cases` for Switch

**No explicit edge table exists**. The graph is computed at runtime.

### 7.2 Start Node Detection

```python
# From engine.py:598-644
def _get_start_node(self):
    # 1. Look for explicit root (action_id='root' or type='Entry Action')
    for action in self.actions:
        if action.action_id == "root" or action.action_type == "Entry Action":
            return action

    # 2. Fallback: Find action with no incoming edges
    # (Computed by checking all next_step fields)
    has_incoming = set()
    for action in self.actions:
        for other in self.actions:
            if other.next_step_if_true == action.action_id:
                has_incoming.add(action.action_id)

    # Return first action with no incoming edges
```

### 7.3 Cycle Detection

Two mechanisms:

1. **Per-node visit limit**: 100 visits per action_id (`node_visits` dict)
2. **Total iteration limit**: 1000 iterations max
3. **Sub-Rule cycle detection**: Via `execution_stack` in context

---

## 8. Caching System

### 8.1 Rule Map Cache

```python
# From coordinator.py:91-124
CACHE_KEY = "flexirule_map"  # Redis key

def get_rule_map() -> dict:
    """Returns: {doctype: {event: [rule_names]}}"""

    # 1. Try frappe.local.flexirule_map["unified"]
    # 2. Try frappe.cache.get_value(CACHE_KEY)
    # 3. Fallback: _build_rule_map() from DB
    # 4. Store in cache and return
```

### 8.2 Cache Invalidation

```python
# From coordinator.py:367-387
def clear_cache(doctype: str | None = None):
    # Clear Redis cache
    frappe.cache.delete_value(CACHE_KEY)
    # Clear local caches
    if hasattr(frappe.local, "flexirule_map"):
        delattr(frappe.local, "flexirule_map")
    # Notify distributed workers
    frappe.publish_realtime("flexirule_cache_clear", {"doctype": doctype})
```

---

## 9. Execution Log System

### 9.1 Log Structure

```python
# From engine.py:959-1056
log_doc = {
    "doctype": "Rule Execution Log",
    "rule": rule_name,
    "rule_version": 1,
    "status": "Success" | "Failed" | "Stopped",
    "duration": 0.123,
    "trigger_source": "Doc: DOCTYPE/NAME [Before Save]",
    "reference_doctype": "Sales Invoice",
    "reference_docname": "SI-001",
    "executed_by": "user@example.com",
    "message": "Executed successfully",
    "execution_path": json.dumps(path_trace),  # [{action, timestamp, result}, ...]
    "context_snapshot": json.dumps(vars),     # Serialized vars
    "error_trace": None,
    # Batch/Scheduler fields
    "scheduler": "My Scheduler",
    "batch_id": "batch-123",
    "batch_index": 5,
    "batch_total": 100,
}
```

### 9.2 Persistence Strategy

```python
# Success and failure logs use enqueue to avoid transaction issues
if status in ("Failed", "Error"):
    frappe.enqueue("persist_execution_log", queue="short", log_data=log_data)
elif context.get("save_log"):
    frappe.enqueue("persist_execution_log", queue="short", log_data=log_data)
else:
    frappe.enqueue("persist_execution_log", queue="short", log_data=log_data)
```

**Note**: All logs are enqueued to avoid adding writes to the user's document save transaction.

---

## 10. Key Constants

| Constant            | Value      | Location        |
| ------------------- | ---------- | --------------- |
| MAX_SUB_RULE_DEPTH  | 2          | `engine.py:48`  |
| MAX_NODE_VISITS     | 100        | `engine.py:427` |
| MAX_ITERATIONS      | 1000       | `engine.py:431` |
| DEFAULT_TIMEOUT     | 30 seconds | `engine.py:317` |
| DEFAULT_RETRY_COUNT | 3          | `engine.py:531` |

---

## 11. Known Architectural Decisions

### 11.1 No Formal Graph Representation

The system uses implicit linking via `next_step` fields. There is no Edge table or explicit graph structure.

### 11.2 Context Mutation Safety

Sub-Rules share and modify parent context.vars directly. No isolation.

### 11.3 JSON AST Compilation

Conditions are compiled from JSON to Python at save time, not runtime. This is a security measure.

### 11.4 Release-Disabled Actions

`Loop` and `Switch` are intentionally disabled in the current release (see `contracts.py:160`).

### 11.5 Async Limitation

Async actions cannot use Output Mapping (enforced in validation_service.py).

---

_Document Version: 1.0_
_Generated from source code analysis of FlexiRule v1.0_
