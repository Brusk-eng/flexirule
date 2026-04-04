# FlexiRule Execution Model

> **Ground Truth**: Detailed step-by-step execution flow based on `flexirule/ruleflow/core/engine.py` and `flexirule/ruleflow/core/coordinator.py`.

---

## 1. Execution Entry Points

### 1.1 Document Event Trigger

Triggered via `hooks.py` when a document is saved:

```python
# hooks.py
def execute_rules(doc, event_name):
    """Called by Frappe doc_events hook"""
    RuleCoordinator.execute_rules(doc, event_name)
```

### 1.2 API Execution

Called programmatically via API:

```python
# coordinator.py
RuleCoordinator.execute_rule(rule_name, context={"doc": doc})

# Or via engine directly
engine = RuleEngine(rule_doc, execution_context=context)
result = engine.execute(doc)
```

### 1.3 Scheduler Execution

Triggered by `scheduler.py` for time-based rules:

```python
# scheduler.py
def process_scheduled_rules():
    due_schedulers = frappe.get_all("Rule Scheduler", ...)
    for scheduler in due_schedulers:
        RuleCoordinator.execute_rule(scheduler.rule, ...)
```

### 1.4 Background Execution

Async rules are queued:

```python
# coordinator.py:314-336
if rule_doc.execution_mode == "Asynchronous":
    frappe.enqueue(
        "flexirule.ruleflow.core.coordinator.RuleCoordinator.run_rule_background",
        rule_name=rule_doc.name,
        doc_doctype=doc.doctype,
        doc_name=doc.name,
        queue="default",
        timeout=rule_doc.max_execution_time or 300
    )
```

---

## 2. Execution Flow (Step by Step)

### 2.1 Rule Selection

```
1. RuleCoordinator.execute_rules(doc, event_name)
   ↓
2. RuleCoordinator.execute_rules_from_event(doc, event_name)
   ↓
3. RuleCoordinator.has_active_rules(doctype, event_name)
   └─ Checks cache for any rules for doctype/event
   ↓
4. RuleCoordinator.get_applicable_rules(doctype, event_name)
   └─ Returns list of Rule docs from cache
```

### 2.2 Eligibility Check

For each applicable rule, `check_eligibility()` is called:

```python
# coordinator.py:224-288
def check_eligibility(rule_doc, doc, event_name, old_doc=None) -> tuple[bool, str]:
    # 1. Active check
    if not rule_doc.is_active:
        return False, "Rule is not active"

    # 2. Event check
    if rule_doc.trigger_event != event_name:
        return False, f"Event mismatch"

    # 3. Trigger condition check (compiled_expression)
    if rule_doc.compiled_expression:
        result = frappe.safe_eval(
            rule_doc.compiled_expression,
            None,  # globals
            {
                "doc": doc,
                "old_doc": old_doc,
                "frappe": SafeFrappeAPI(),
                "resolve": FieldResolver.resolve,
                "check_link_match": check_link_match,
                "True": True,
                "False": False,
                "None": None
            }
        )
        if not result:
            return False, "Trigger Conditions failed"

    return True, "Eligible"
```

### 2.3 Execution Start

```python
# coordinator.py:314-347
def execute_single_rule(doc, rule_doc, old_doc=None, event_name=None):
    # 1. Check async mode
    if rule_doc.execution_mode == "Asynchronous":
        if not doc.get("__islocal"):
            frappe.enqueue(...)  # Queue for background
            return

    # 2. Prepare execution context
    execution_context = {"old_doc": old_doc}
    if frappe.flags.in_test:
        execution_context["test_mode"] = True

    # 3. Create and execute engine
    engine = RuleEngine(rule_doc, execution_context=execution_context)
    engine.execute(doc, event_name=event_name)
```

### 2.4 Engine Initialization

```python
# engine.py:237-258
def __init__(self, rule_doc, execution_context=None):
    # 1. Load rule
    if isinstance(rule_doc, str):
        rule_doc = frappe.get_doc("Rule", rule_doc)
    self.rule = rule_doc

    # 2. Filter enabled actions
    self.actions = [a for a in rule_doc.actions if a.is_enabled]

    # 3. Initialize context
    self.context = execution_context or {}
    if frappe.flags.in_test and "test_mode" not in self.context:
        self.context["test_mode"] = True

    # 4. Initialize execution log
    self.execution_log = []
    self.cache = {}

    # 5. Build action lookup maps
    self.action_map_by_id = {a.action_id: a for a in self.actions if a.action_id}
    self.action_map_by_label = {a.action_label: a for a in self.actions}
    self.action_map_by_name = {a.name: a for a in self.actions}
```

### 2.5 Execute Method

```python
# engine.py:271-365
def execute(self, doc, event_name=None, **kwargs):
    start_time = time.time()
    status = "Success"
    error_detail = None
    self.path_trace = []

    try:
        # 1. Pre-execution validation
        self._validate_execution()

        # 2. Role-based skip check
        skip_for_roles_docs = self.rule.get("skip_for_roles")
        if skip_for_roles_docs:
            user_roles = frappe.get_roles()
            skip_roles = [row.get("role") for row in skip_for_roles_docs]
            if any(role in user_roles for role in skip_roles):
                return self.context  # Skip execution

        # 3. Initialize context
        context = self._initialize_context(doc, **kwargs)

        # 4. Expose execution log to frappe.local
        frappe.local.execution_log = self.execution_log

        # 5. Set timeout
        timeout = self.rule.max_execution_time or 30
        context["_timeout"] = timeout
        context["_start_time"] = start_time

        # 6. Execute graph
        if self.context.get("test_mode"):
            result = self._execute_graph(context)  # No timeout in test
        else:
            with time_limit(timeout):
                result = self._execute_graph(context)

        return result

    except frappe.PermissionError as e:
        status = "Skipped"
        return self.context

    except (TimeoutException, FuturesTimeoutError, BoltonTimeoutError):
        status = "Failed"
        raise BoltonTimeoutError("timeout message")

    except Exception as e:
        status = "Failed"
        raise

    finally:
        # 7. Save execution log
        self._save_execution_log(status, duration, error_detail)

        # 8. Update rule last_error
        if not self.context.get("dry_run") and not self.context.get("test_mode"):
            self._update_last_error(error_detail if status == "Failed" else None)
```

### 2.6 Validation

```python
# engine.py:370-398
def _validate_execution(self):
    # 1. Check is_active
    if not self.rule.is_active:
        raise RuleDisabledError("Rule is disabled")

    # 2. Check has actions
    if not self.actions:
        raise EmptyRuleError("Rule has no enabled actions")

    # 3. Check release-disabled actions
    disabled_actions = [a.action_label for a in self.actions
                        if is_release_disabled_action(a.action_type)]
    if disabled_actions:
        raise frappe.ValidationError(
            f"Rule contains disabled action types: {disabled_actions}"
        )

    # 4. Check permissions (if defined)
    rule_permissions = self.rule.get("permissions")
    if rule_permissions:
        user_roles = set(frappe.get_roles())
        if "System Manager" not in user_roles:
            can_exec = any(p.can_execute and p.role in user_roles
                          for p in rule_permissions)
            if not can_exec:
                raise frappe.PermissionError("No execute permission")
```

### 2.7 Context Initialization

```python
# engine.py:400-416
def _initialize_context(self, doc, **kwargs):
    return {
        **self.context,
        "doc": doc,
        "frappe": self._get_safe_frappe_api(),
        "vars": {},
        "meta": {
            "rule": self.rule.name,
            "rule_version": self.rule.version,
            "engine_version": "1.0",
            "user": frappe.session.user,
            "timestamp": frappe.utils.now(),
            "test_mode": self.context.get("test_mode", False),
        },
        "stop": False,
        **kwargs,
    }
```

---

## 3. Graph Execution Loop

### 3.1 Main Loop (`_execute_graph`)

```python
# engine.py:422-596
def _execute_graph(self, context):
    # 1. Initialize loop tracking
    node_visits: dict[str, int] = {}  # Count visits per node
    max_visits_per_node = 100
    max_iterations = 1000

    execution_path = []
    current = self._get_start_node()

    # 2. Main loop
    for _iteration in range(max_iterations):
        # 2.1 Timeout check
        if "_timeout" in context and "_start_time" in context:
            if time.time() - context["_start_time"] > context["_timeout"]:
                raise BoltonTimeoutError("timeout exceeded")

        # 2.2 Stop flag check
        if context.get("stop"):
            self._log("INFO", "Flow stopped by action")
            break

        # 2.3 No current action = end
        if not current:
            break

        # 2.4 Get action ID for tracking
        node_id = current.action_id or current.name

        # 2.5 Track visit count
        visits = node_visits.get(node_id, 0) + 1
        node_visits[node_id] = visits

        # 2.6 Cycle detection
        if visits > max_visits_per_node:
            raise CycleDetectedError(
                f"Infinite loop: {current.action_label} visited {visits} times"
            )

        # 2.7 Record path
        execution_path.append(current.action_label)
        self.path_trace.append({
            "action": current.action_label,
            "action_id": node_id,
            "type": current.action_type,
            "timestamp": time.time()
        })

        # 2.8 Log execution
        self._log("INFO", f"Executing action: {current.action_label}")

        try:
            # 2.9 Get handler
            handler = HandlerRegistry.get(normalize_action_type(current.action_type))

            if not handler:
                self._log("WARNING", f"Unknown action type: {current.action_type}")
                result = None
                next_id = current.next_step_if_true
            else:
                # 2.10 Execute handler
                result, next_id = handler.execute(current, context, self)

            # 2.11 Store result in path trace
            self.path_trace[-1]["result"] = result

            # 2.12 Special handling for Process actions
            if current.action_type == "Process":
                self.path_trace[-1]["output"] = json.dumps(result, default=str)
                self.path_trace[-1]["input"] = self._get_action_config(current)

            # 2.13 Post-processing (mapping, mutation)
            self._post_process_action_result(current, result, context)

            # 2.14 Move to next action
            current = self._get_action_by_id(next_id)

        except Exception as e:
            # 2.15 Error handling
            if hasattr(current, "on_error"):
                if current.on_error == "Continue":
                    self._log("WARNING", f"Error, continuing: {e}")
                    current = self._get_action_by_id(current.next_step_if_true)
                    continue

                elif current.on_error == "Retry":
                    # Retry logic with exponential backoff
                    ...

                elif current.on_error == "Rollback":
                    # Savepoint rollback
                    frappe.db.rollback(save_point=f"flexirule_action_{current.name}")
                    raise

                elif current.on_error == "Escalate":
                    raise

            # Default: re-raise
            raise

    # 3. Check iteration limit
    if _iteration >= max_iterations - 1:
        raise CycleDetectedError("Max total iterations exceeded")

    # 4. Log execution path
    self._log("INFO", f"Execution path: {' → '.join(execution_path)}")

    return context
```

### 3.2 Start Node Detection

```python
# engine.py:598-644
def _get_start_node(self):
    # 1. Look for explicit root
    for action in self.actions:
        if action.action_id == "root" or action.action_type == "Entry Action":
            return action

    # 2. Fallback: Find action with no incoming edges
    has_incoming = set()
    for action in self.actions:
        for other in self.actions:
            if other.next_step_if_true == action.action_id:
                has_incoming.add(action.action_id)
            if other.next_step_if_false == action.action_id:
                has_incoming.add(action.action_id)

    for action in self.actions:
        action_id = action.action_id or action.name
        if action_id not in has_incoming:
            return action

    # 3. Last resort: First action
    return self.actions[0] if self.actions else None
```

---

## 4. Action Handler Execution

### 4.1 Handler Pattern

All handlers return `(result, next_action_id)`:

```python
class ActionHandler(ABC):
    @abstractmethod
    def execute(self, action, context: dict, engine: "RuleEngine") -> tuple[Any, str | None]:
        """Execute the action. Returns (result, next_action_id)"""
        pass
```

### 4.2 Standard Execution Flow

```python
# For most actions:
result, next_id = handler.execute(current, context, self)

# For Condition:
if result:
    next_id = current.next_step_if_true
else:
    next_id = current.next_step_if_false

# For Loop:
if result:  # result = True means "continue iteration"
    next_id = current.next_step_if_true  # body
else:  # result = False means "exit loop"
    next_id = current.next_step_if_false  # exit path

# For Stop (terminal):
return None, None  # No next action

# For Set Value:
doc.set(target_field, rendered_value)
return rendered_value, current.next_step_if_true
```

### 4.3 Post-Processing

After each handler executes, `_post_process_action_result` is called:

```python
# engine.py:684-749
def _post_process_action_result(self, action, result, context):
    cm = ContextManager(context)

    # 1. Output Mapping (Result -> Context vars)
    action_config = frappe.parse_json(getattr(action, "config", "{}") or "{}")
    output_mapping = action_config.get("output_mapping")
    if output_mapping:
        apply_output_mapping(result, output_mapping, context)

    # 2. Return Variable Storage
    return_variable = getattr(action, "return_variable", None)
    return_type = getattr(action, "return_type", None)

    if return_variable and result is not None:
        cm.set_variable(return_variable, result, return_type)

        # Optional schema validation
        expected_keys = self._parse_output_schema(action.resolved_output_schema)
        if expected_keys:
            cm.validate_return_keys(result, expected_keys, return_variable)

    # 3. Mutation Mode (Result -> Doc/Context/DB)
    mutation_mode = getattr(action, "mutation_mode", None)
    if mutation_mode:
        contract = get_contract(action.action_type)
        allowed = contract.get("allowed_mutations", [])

        if mutation_mode not in allowed:
            raise MethodExecutionError(f"Mutation mode not allowed")

        if not return_variable:
            raise MethodExecutionError(f"Mutation mode requires return_variable")

        cm.apply_mutation(mutation_mode, return_variable, result, context)
```

---

## 5. Error Handling

### 5.1 Error Strategy Selection

Each action has an `on_error` field:

| on_error         | Behavior                                             |
| ---------------- | ---------------------------------------------------- |
| `Stop` (default) | Re-raise exception, terminate flow                   |
| `Continue`       | Log warning, continue to `next_step_if_true`         |
| `Retry`          | Exponential backoff, retry up to `retry_count` times |
| `Rollback`       | Rollback to savepoint, re-raise                      |
| `Escalate`       | Re-raise same exception                              |

### 5.2 Retry Implementation

```python
# engine.py:529-562
elif current.on_error == "Retry":
    retry_count = getattr(current, "retry_count", 3) or 3
    retry_key = f"_retry_{current.action_id or current.name}"
    current_attempt = context.get("vars", {}).get(retry_key, 0)

    if current_attempt < retry_count:
        # Increment counter
        context.setdefault("vars", {})[retry_key] = current_attempt + 1

        # Calculate backoff
        wait_time = 2 ** current_attempt  # 1s, 2s, 4s...

        # Cannot retry in sync hook
        if context.get("_in_sync_hook"):
            raise frappe.ValidationError(
                f"Cannot retry action inside synchronous hook"
            )

        # Wait and retry
        time.sleep(wait_time)
        continue  # Retry same action

    # Max retries exceeded
    raise
```

### 5.3 Rollback Implementation

```python
# engine.py:563-577
elif current.on_error == "Rollback":
    savepoint_name = f"flexirule_action_{current.action_id or current.name}"
    self._log("ERROR", f"Rolling back to savepoint: {savepoint_name}")
    try:
        frappe.db.rollback(save_point=savepoint_name)
    except Exception:
        self._log("WARNING", "Savepoint rollback failed")
    raise
```

---

## 6. Timeout Behavior

### 6.1 Timeout Sources

1. **Rule-level**: `max_execution_time` field (default: 30s)
2. **Action-level**: `timeout` field for Process actions
3. **Test mode**: Disabled (`test_mode: True` in context)

### 6.2 Timeout Implementation

```python
# engine.py:106-126
@contextmanager
def time_limit(seconds):
    """Thread-based timeout using timer"""
    if seconds <= 0:
        yield
        return

    timeout_event = threading.Event()
    timer = threading.Timer(seconds, timeout_event.set)
    timer.start()
    try:
        yield timeout_event
    finally:
        timer.cancel()


# engine.py:325-326
if self.context.get("test_mode"):
    result = self._execute_graph(context)
else:
    with time_limit(timeout):
        result = self._execute_graph(context)
```

### 6.3 Internal Timeout Check

```python
# engine.py:434-439
if "_timeout" in context and "_start_time" in context:
    if time.time() - context["_start_time"] > context["_timeout"]:
        raise BoltonTimeoutError("timeout exceeded")
```

---

## 7. Logging and Trace

### 7.1 Execution Log

```python
# engine.py:911-918
def _log(self, level, message):
    entry = {
        "timestamp": frappe.utils.now(),
        "level": level,
        "message": message
    }
    self.execution_log.append(entry)

    if self.rule.debug_mode or self.context.get("test_mode"):
        frappe.logger().info(f"[{self.rule.name}] [{level}] {message}")
```

### 7.2 Path Trace

```python
# engine.py:463-471
self.path_trace.append({
    "action": current.action_label,
    "action_id": node_id,
    "type": current.action_type,
    "timestamp": time.time(),
})

# After handler execution:
try:
    self.path_trace[-1]["result"] = result
except Exception:
    pass
```

### 7.3 Execution Log Persistence

```python
# engine.py:959-1056
log_doc = {
    "doctype": "Rule Execution Log",
    "rule": self.rule.name,
    "status": status,
    "duration": duration,
    "trigger_source": self._build_trigger_source(context),
    "reference_doctype": doc.doctype,
    "reference_docname": doc.name,
    "executed_by": frappe.session.user,
    "execution_path": json.dumps(self.path_trace),
    "context_snapshot": json.dumps(context_snapshot),
    "error_trace": error_trace
}

# All logs use enqueue to avoid transaction issues
frappe.enqueue("flexirule.ruleflow.utils.logging.persist_execution_log",
               queue="short", log_data=log_data)
```

---

## 8. Context Lifecycle

### 8.1 Context Creation

```python
context = {
    "doc": doc,                    # Set by caller
    "old_doc": old_doc,            # Set by coordinator
    "vars": {},                   # Created fresh
    "frappe": SafeFrappeAPI(),    # Read-only proxy
    "meta": {
        "rule": rule_name,
        "user": user,
        "timestamp": now(),
        "test_mode": False
    },
    "stop": False,                # Can be set by actions
    "_timeout": 30,               # Set by engine
    "_start_time": time.time()   # Set by engine
}
```

### 8.2 Context Mutations

Variables are added/modified by:

1. **Return Variables**: `context["vars"]["name"] = value`
2. **Mutation Modes**: Via `ContextManager.apply_mutation()`
3. **Sub-Rule Merge**: `context["vars"].update(sub_result["vars"])`

### 8.3 Context Access Patterns

```python
# Read document
doc = context.get("doc")

# Read variable
my_var = context.get("vars", {}).get("my_var")

# Write variable
context.setdefault("vars", {})["my_var"] = "value"

# Access safe Frappe API
frappe_safe = context.get("frappe")
value = frappe_safe.get_value("Customer", filters, "name")

# Read metadata
rule_name = context.get("meta", {}).get("rule")
```

---

## 9. Constants and Limits

| Constant              | Value | Location        | Purpose                   |
| --------------------- | ----- | --------------- | ------------------------- |
| `MAX_SUB_RULE_DEPTH`  | 2     | `engine.py:48`  | Sub-Rule nesting limit    |
| `max_visits_per_node` | 100   | `engine.py:427` | Infinite loop detection   |
| `max_iterations`      | 1000  | `engine.py:431` | Total loop iterations     |
| `DEFAULT_TIMEOUT`     | 30    | `engine.py:317` | Default execution timeout |
| `DEFAULT_RETRY_COUNT` | 3     | `engine.py:531` | Default retry attempts    |

---

_Document Version: 1.0_
_Generated from FlexiRule v1.0 source analysis_
