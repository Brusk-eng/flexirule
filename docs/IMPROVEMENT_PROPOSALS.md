# FlexiRule Improvement Proposals

Based on the deep code analysis, here are concrete improvements addressing real gaps discovered in the system.

---

## Priority 1: Critical Fixes

### 1. Sub-Rule Context Isolation

**Gap Identified**: Sub-Rule handler shares and modifies parent `vars` dict directly (sub_rule.py:156). No scope isolation.

**Risk**: Variable shadowing, unexpected side effects, debugging difficulty.

**Current Behavior**:

```python
# sub_rule.py - Line 156
context["vars"].update(result_context.get("vars", {}))
# Parent vars are directly mutated
```

**Proposed Solution**:
Implement proper scope isolation with scoped vars:

```python
# Proposed: Sub-Rule creates isolated scope
def execute(self, action, context, engine):
    # Create isolated scope
    isolated_vars = context.get("vars", {}).copy()
    sub_context = context.copy()
    sub_context["vars"] = isolated_vars  # Isolated copy

    # Execute sub-rule
    sub_engine = RuleEngine(sub_rule_doc, execution_context=sub_context)
    result_context = sub_engine.execute(context.get("doc"))

    # Selective merge: Only specified return variables
    allowed_returns = self._get_allowed_returns(action)
    for var_name in allowed_returns:
        if var_name in result_context.get("vars", {}):
            context["vars"][var_name] = result_context["vars"][var_name]
```

**Implementation Effort**: Medium
**Impact**: High - Improves reliability and debuggability

---

### 2. Release-Disabled Actions Visibility

**Gap Identified**: `Loop` and `Switch` are marked as `RELEASE_DISABLED_ACTION_TYPES` in contracts.py:160 but this isn't clearly communicated in the UI.

**Risk**: Users may try to use unavailable action types.

**Current Behavior**:

```python
# contracts.py:160
RELEASE_DISABLED_ACTION_TYPES = {"Loop", "Switch"}
```

Only logged as warning in engine.

**Proposed Solution**:

1. Frontend should filter out disabled action types from the palette
2. Clear messaging when attempting to use disabled types

```javascript
// In rule_builder store.js
const AVAILABLE_ACTION_TYPES = [
	"Entry Action",
	"Condition",
	"Process",
	"Stop",
	"Wait",
	"Sub-Rule",
	"Set Value",
	"Raise Error",
	"Notify",
	"Query Records",
	"Document Action",
	// 'Loop' and 'Switch' excluded - release disabled
];
```

**Implementation Effort**: Low
**Impact**: Medium - Improves UX

---

## Priority 2: Security Enhancements

### 3. Expression Validation Hardening

**Gap Identified**: `validate_safe_eval` in permissions.py only checks syntax, not semantic safety. Actual safety relies on `SafeFrappeAPI` and `frappe.safe_eval`.

**Current Behavior**:

```python
# permissions.py:222-237
def validate_safe_eval(expression):
    try:
        compile(expression, "<string>", "eval")
    except SyntaxError as e:
        frappe.throw(...)
    return True  # Only checks syntax!
```

**Proposed Solution**:
Enhance validation with AST analysis:

```python
import ast

def validate_safe_eval(expression):
    # 1. Syntax check
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as e:
        frappe.throw(...)

    # 2. AST-based security check
    unsafe_patterns = [
        ast.Attribute,  # Method calls
        ast.Call,        # Function calls
        ast.Subscript,   # Complex indexing
    ]

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            # Check for dangerous attributes
            if node.attr in ['__globals__', '__code__', '__closure__']:
                frappe.throw("Forbidden pattern in expression")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id in ['eval', 'exec', 'compile', 'open']:
                    frappe.throw("Forbidden function in expression")

    return True
```

**Implementation Effort**: Medium
**Impact**: High - Security hardening

---

### 4. skip_permissions Audit Logging

**Gap Identified**: `can_skip_permissions` logs to frappe.logger but doesn't persist audit trail to database.

**Current Behavior**:

```python
# permissions.py:170-176
frappe.logger("flexirule.security").warning(
    "skip_permissions override by user=%s action=%s...",
    user, ...
)
# Only logs to file, not persistent
```

**Proposed Solution**:
Add `RulePermissionAuditLog` DocType and persist:

```python
def can_skip_permissions(action, context=None, throw=True):
    # ... existing validation ...

    # Log to database
    try:
        frappe.get_doc({
            "doctype": "Rule Permission Audit Log",
            "rule": getattr(action, "parent", None),
            "action_id": getattr(action, "action_id", None),
            "user": user,
            "roles": list(user_roles),
            "reason": audit_reason,
            "timestamp": frappe.utils.now()
        }).insert(ignore_permissions=True)
    except Exception:
        pass  # Don't fail on audit log error

    return True
```

**Implementation Effort**: Medium
**Impact**: Medium - Compliance and audit

---

## Priority 3: Architectural Improvements

### 5. Formal Graph Model

**Gap Identified**: FlexiRule uses implicit graph via `next_step` fields. No explicit Edge table or graph structure.

**Risk**: Difficult to analyze graph properties (cycles, reachability) at design time.

**Proposed Solution**:
Add optional explicit graph representation:

```python
# New DocType: Rule Graph Edge
class RuleGraphEdge(Document):
    rule = Link("Rule")
    source_action = Link("Rule Action")
    target_action = Link("Rule Action")
    edge_type = Select(["true", "false", "default"])

# Alternative: Store computed graph in Rule
class Rule(Document):
    # New field
    computed_graph = Code(JSON)  # Computed on save

    def compute_graph(self):
        """Compute and store graph representation"""
        nodes = {a.action_id: a for a in self.actions}
        edges = []

        for action in self.actions:
            if action.next_step_if_true:
                edges.append({
                    "source": action.action_id,
                    "target": action.next_step_if_true,
                    "type": "true"
                })
            if action.next_step_if_false:
                edges.append({
                    "source": action.action_id,
                    "target": action.next_step_if_false,
                    "type": "false"
                })

        self.computed_graph = json.dumps({
            "nodes": list(nodes.keys()),
            "edges": edges,
            "entry": self._get_start_node_id()
        })
```

**Use Cases**:

- Visual path highlighting
- Reachability analysis
- Cycle detection (more robust than visit counting)
- Execution path prediction

**Implementation Effort**: High
**Impact**: Medium - Tooling improvement

---

### 6. Typed Schemas for Config and Output

**Gap Identified**: Operations define `config_schema` and `output_schema` as JSON but there's no runtime enforcement.

**Current Behavior**:

```python
# config_schema is stored as raw JSON string
# engine.py:821-823 only logs warning on schema mismatch
if op_def and op_def.output_schema:
    self._validate_output_against_schema(result, op_def.output_schema, operation)
    # Non-fatal - just warning
```

**Proposed Solution**:
Add optional strict validation:

```python
from pydantic import BaseModel, ValidationError

def _validate_output_against_schema_strict(result, output_schema, operation_name):
    """Validate with Pydantic if schema is well-formed"""
    try:
        schema = json.loads(output_schema)
        if not schema.get("properties"):
            return  # Skip if not proper schema

        # Generate Pydantic model from schema
        props = schema.get("properties", {})
        required = schema.get("required", [])

        model_fields = {}
        for name, spec in props.items():
            field_type = spec.get("type", "string")
            py_type = {
                "string": str,
                "number": float,
                "integer": int,
                "boolean": bool,
                "array": list,
                "object": dict,
                "null": type(None)
            }.get(field_type, str)

            model_fields[name] = (py_type, ...)

        # Create dynamic model
        DynamicModel = type("DynamicModel", (BaseModel,), model_fields)

        # Validate
        DynamicModel(**result)

    except (json.JSONDecodeError, TypeError, ValidationError) as e:
        frappe.logger().warning(
            f"Output schema validation failed for {operation_name}: {e}"
        )
```

**Implementation Effort**: Medium
**Impact**: Medium - Data integrity

---

### 7. Static Validation Layer

**Gap Identified**: `validation_service.py` provides good validation but lacks static analysis for graph properties.

**Current Gaps**:

- No detection of unreachable nodes after conditional branches
- No dead code detection (actions that can never be reached)
- No path coverage analysis

**Proposed Solution**:
Add static graph analysis:

```python
# validation_service.py additions

def validate_graph_static(rule_doc) -> dict:
    """Static analysis of rule graph"""
    errors = []
    warnings = []

    actions = {a.action_id: a for a in rule_doc.actions}

    # 1. Compute all reachable nodes
    reachable = compute_reachable(actions, start_id)

    # 2. Detect unreachable nodes
    for action in rule_doc.actions:
        if action.action_id not in reachable:
            warnings.append(
                f"Action '{action.action_label}' is unreachable from start"
            )

    # 3. Detect potential infinite paths (no terminal)
    infinite_paths = find_non_terminating_paths(actions)
    if infinite_paths:
        warnings.append(
            f"Potential infinite execution paths detected: {infinite_paths}"
        )

    # 4. Check variable scope coverage
    variable_coverage = analyze_variable_usage(actions)
    for var_name, usages in variable_coverage.items():
        if not usages.get("defined"):
            errors.append(f"Variable 'vars.{var_name}' used but never defined")

    return {"errors": errors, "warnings": warnings}


def compute_reachable(actions, start_id):
    """BFS to compute reachable nodes"""
    reachable = set()
    queue = [start_id]

    while queue:
        node_id = queue.pop(0)
        if node_id in reachable:
            continue
        reachable.add(node_id)

        action = actions.get(node_id)
        if not action:
            continue

        if action.next_step_if_true:
            queue.append(action.next_step_if_true)
        if action.next_step_if_false:
            queue.append(action.next_step_if_false)

    return reachable


def find_non_terminating_paths(actions):
    """Find paths that don't end in terminal nodes"""
    # Use DFS to find all paths
    # Check if each path ends in terminal or infinite loop
    pass
```

**Implementation Effort**: Medium
**Impact**: High - Prevent invalid rules

---

## Priority 4: Performance Optimizations

### 8. Condition Compilation Caching

**Gap Identified**: Conditions are compiled on Rule save and stored in `condition_expression`. However, the compiled expression is stored per-action, not cached globally.

**Current Behavior**:

```python
# rule.py:309-345 - compile_conditions()
for action in self.actions:
    if action.action_type == "Condition" and action.condition_json:
        action.condition_expression = compiler.compile(action.condition_json)
# Re-compiled on every save
```

**Proposed Solution**:
Add compilation cache:

```python
# Add to engine.py or create new caching module

COMPILATION_CACHE = {}  # Simple in-memory cache
MAX_CACHE_SIZE = 1000

def get_compiled_condition(condition_json, rule_name):
    """Get or compile condition with caching"""
    cache_key = hashlib.md5(f"{rule_name}:{condition_json}".encode()).hexdigest()

    if cache_key in COMPILATION_CACHE:
        return COMPILATION_CACHE[cache_key]

    # Compile
    compiler = ConditionCompiler()
    expression = compiler.compile(condition_json)

    # Cache
    if len(COMPILATION_CACHE) >= MAX_CACHE_SIZE:
        # LRU eviction
        oldest = list(COMPILATION_CACHE.keys())[0]
        del COMPILATION_CACHE[oldest]

    COMPILATION_CACHE[cache_key] = expression
    return expression
```

**Implementation Effort**: Low
**Impact**: Medium - Performance for large rule sets

---

### 9. Lazy Action Handler Loading

**Gap Identified**: `HandlerRegistry._ensure_initialized()` imports all handlers on first access. This adds startup overhead.

**Current Behavior**:

```python
# action_handlers/__init__.py:227-248
@classmethod
def _ensure_initialized(cls) -> None:
    if cls._initialized:
        return
    # Import ALL handlers on first use
    from flexirule.ruleflow.core.action_handlers import (
        condition, create_doc, loop, process,
        query_records, simple_actions, sub_rule, switch
    )
    cls._initialized = True
```

**Proposed Solution**:
Lazy loading per handler:

```python
@classmethod
def get(cls, action_type: str) -> ActionHandler | None:
    # Check cache first
    if action_type in cls._handlers:
        return cls._handlers[action_type]

    # Lazy load specific handler
    handler_map = {
        "Condition": "condition",
        "Process": "process",
        "Loop": "loop",
        # ... etc
    }

    if action_type in handler_map:
        module_name = handler_map[action_type]
        module = __import__(
            f"flexirule.ruleflow.core.action_handlers.{module_name}",
            fromlist=["HandlerRegistry"]
        )
        # Handler registers itself on import

    return cls._handlers.get(action_type)
```

**Implementation Effort**: Low
**Impact**: Low - Startup optimization

---

## Priority 5: Developer Experience

### 10. Rule Testing API

**Gap Identified**: No structured API for testing rules in development.

**Current Options**:

- Manual execution via UI
- Ad-hoc Python scripting

**Proposed Solution**:
Add test rule API:

```python
# api.py additions

@frappe.whitelist()
def test_rule(rule_name, test_cases=None):
    """
    Test a rule with multiple test cases

    Args:
        rule_name: Rule to test
        test_cases: List of test case dicts:
            [{
                "name": "Basic validation",
                "doc": {"doctype": "Sales Invoice", ...},
                "expected": {
                    "status": "Success",
                    "vars": {"result": True},
                    "path": ["Entry Action", "Condition", "Process"]
                }
            }]

    Returns:
        Test results with pass/fail per case
    """
    results = []

    for case in test_cases:
        try:
            # Execute rule
            result = RuleCoordinator.execute_rule(
                rule_name,
                context={"doc": case["doc"], "test_mode": True}
            )

            # Compare results
            passed = True
            failures = []

            if case.get("expected", {}).get("status"):
                # Check status
                pass

            if case.get("expected", {}).get("vars"):
                # Check vars
                for key, expected_val in case["expected"]["vars"].items():
                    actual = result.get("vars", {}).get(key)
                    if actual != expected_val:
                        passed = False
                        failures.append(f"var.{key}: expected {expected_val}, got {actual}")

            results.append({
                "name": case["name"],
                "passed": passed,
                "failures": failures,
                "path_trace": result.get("path_trace", [])
            })

        except Exception as e:
            results.append({
                "name": case["name"],
                "passed": False,
                "error": str(e)
            })

    return results
```

**Implementation Effort**: Medium
**Impact**: High - Developer productivity

---

### 11. Execution Path Visualization

**Gap Identified**: No way to visualize actual execution path vs designed path.

**Current Behavior**:

- Execution logs contain path_trace
- No visual comparison with designed graph

**Proposed Solution**:
Add path visualization to builder:

```javascript
// In rule_builder store.js

async function visualizeExecution(ruleName, docName) {
	// Execute rule and get path
	const result = await frappe.call({
		method: "flexirule.ruleflow.api.execute_rule",
		args: { rule_name: ruleName, doc_name: docName },
	});

	// Highlight execution path
	const pathTrace = result.path_trace || [];

	// Update node styles to show execution
	pathTrace.forEach((step, index) => {
		const node = nodes.value.find((n) => n.id === step.action_id);
		if (node) {
			node.style = {
				...node.style,
				border: "2px solid #22c55e", // Green
				backgroundColor: index === 0 ? "#dcfce7" : "#f0fdf4",
			};
		}
	});

	// Animate path
	for (let i = 0; i < pathTrace.length; i++) {
		await new Promise((resolve) => setTimeout(resolve, 500));
		highlightEdge(pathTrace[i], pathTrace[i + 1]);
	}
}
```

**Implementation Effort**: Medium
**Impact**: Medium - Debugging experience

---

## Summary of Recommendations

| Priority | Improvement                         | Effort | Impact |
| -------- | ----------------------------------- | ------ | ------ |
| 1        | Sub-Rule Context Isolation          | Medium | High   |
| 1        | Release-Disabled Actions Visibility | Low    | Medium |
| 2        | Expression Validation Hardening     | Medium | High   |
| 2        | skip_permissions Audit Logging      | Medium | Medium |
| 3        | Formal Graph Model                  | High   | Medium |
| 3        | Typed Schemas for Config/Output     | Medium | Medium |
| 3        | Static Validation Layer             | Medium | High   |
| 4        | Condition Compilation Caching       | Low    | Medium |
| 4        | Lazy Action Handler Loading         | Low    | Low    |
| 5        | Rule Testing API                    | Medium | High   |
| 5        | Execution Path Visualization        | Medium | Medium |

**Recommended First Steps**:

1. Sub-Rule Context Isolation (fixes dangerous behavior)
2. Static Validation Layer (prevents invalid rules)
3. Expression Validation Hardening (security)
4. Rule Testing API (developer experience)

---

_Document Version: 1.0_
_Based on FlexiRule v1.0 architecture analysis_
