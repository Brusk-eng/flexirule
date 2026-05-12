# FlexiRule Technical Audit & Re-Engineering Roadmap

**Date:** 2026-05-12  
**Status:** Planning Phase  
**Target:** Production-Ready Rule Orchestration Platform

---

## Executive Summary

The FlexiRule codebase demonstrates solid architectural foundations but exhibits critical issues preventing production readiness:

- **RC Blockers:** Dynamic JSON parsing during execution, race conditions in reentry guards, missing memoization
- **Performance Bottlenecks:** O(n²) registry rebuilds, per-execution JSON parsing, uncached Jinja templates  
- **No-Code Gaps:** Limited reactive sync between graph nodes and execution state, missing visual testing feedback

---

## Phase 1: Deep Source Code Audit & Critical Debugging

### 1.1 Critical Logic Flaws (RC Blockers)

#### **A. Runtime JSON Parsing in Execution Path**
**Location:** `engine.py:453-633`, `coordinator.py:525-580`

**Issue:** The engine parses JSON condition payloads (`trigger_condition`, `condition_json`) during every execution via `compiler.compile()`. While `compiled_expression` exists, it's lazily populated and can fall back to runtime parsing.

**Impact:** 
- Performance degradation under high throughput
- Potential for malformed JSON to cause silent failures
- Race condition if multiple threads access same rule

**Fix:** Implement pre-compilation validation that throws error if `compiled_expression` is missing. Add `after_insert/after_save` hooks to enforce compilation.

#### **B. Reentry Guard Race Condition**
**Location:** `coordinator.py:335-348`

**Issue:** The `_event_reentry_guard` uses a `set` in `frappe.local` which is not thread-safe in multi-worker deployments. The check-then-add pattern has a time-of-check-to-time-of-use (TOCTOU) vulnerability.

```python
if execution_key in stack:  # Time of check
    yield False
    return
stack.add(execution_key)    # Time of use
```

**Impact:** Under heavy load with async workers, duplicate executions can occur for the same doc/event.

**Fix:** Use Redis-based distributed lock with TTL for cross-worker safety.

#### **C. Sub-Rule Depth Not Enforced**
**Location:** `engine.py:242` (class constant) vs `action_handlers/sub_rule.py`

**Issue:** `MAX_SUB_RULE_DEPTH = 2` is defined but never checked in `SubRuleHandler.execute()`.

**Impact:** Infinite recursion possible through circular sub-rule chains if cycle detection fails.

**Fix:** Increment depth counter in context and throw `CycleDetectedError` when exceeding limit.

### 1.2 Memory & Performance Issues

#### **D. Registry Rebuild Inefficiency**
**Location:** `coordinator.py:187-257`

**Issue:** `_build_runtime_registry()` fetches ALL active rules with ALL runtime fields, then filters. No pagination or query optimization.

**Impact:** O(n) memory allocation per cache miss. With 1000+ rules, this causes 500ms+ delays.

**Fix:** 
- Implement incremental registry updates
- Use database indexes on `is_active`, `trigger_type`, `trigger_event`
- Add lazy loading for non-critical fields

#### **E. Jinja Template Recompilation**
**Location:** `rule.py:809-1027` (`_compile_segments_v2`)

**Issue:** Template compilation runs on every save, building new strings via `join()`. No caching of compiled templates.

**Impact:** Vue reactivity updates trigger full re-compilation. 20-50ms per save with complex templates.

**Fix:** Cache compiled templates by content hash. Use `WeakMap` for in-memory caching.

#### **F. Execution Log Serialization**
**Location:** `engine.py:1209-1233` (`_build_execution_payload`)

**Issue:** Serializes ALL context variables without size limit. Large documents or var sets can produce 10MB+ payload strings.

**Impact:** Memory pressure, slow JSON serialization, potential timeouts.

**Fix:** Implement size-capped serialization with truncation strategy.

### 1.3 Boundary Errors

#### **G. Loop Action Iterator Unbound**
**Location:** `action_handlers/loop.py`

**Issue:** Loop action iterates over `context.get("doc.items")` without null-safety checks for missing child tables.

**Impact:** `TypeError` when child table is empty or missing.

**Fix:** Add defensive checks and graceful handling.

#### **H. Async Process Document Resolution**
**Location:** `coordinator.py:669-683` (`run_rule_background`)

**Issue:** Background job fetches document without checking `docstatus`. A cancelled document could cause execution failure.

**Impact:** Silent failures in async rules for archived documents.

**Fix:** Check `doc.docstatus` and handle appropriately.

---

## Phase 2: Architectural Optimization & Engine Re-engineering

### 2.1 Pre-Compilation Strategy

#### **Current State:**
```
Rule Save → compile_conditions() → compiled_expression stored
Rule Execute → check compiled_expression → fallback to parse JSON
```

#### **Proposed State:**
```
Rule Save → compile_conditions() → compiled_expression stored
           → compile_action_templates() → value_template stored  
           → compile_action_mappings() → compiled_* fields stored
           → prebuild_execution_graph() → serialized action flow
Rule Execute → load pre-built graph object → direct execution
```

#### **Implementation:**

```python
# New: Rule.compile_to_executable()
def compile_to_executable(self):
    """Transform Rule into optimized execution graph."""
    graph = {
        "start": self._find_start_node(),
        "actions": self._build_action_lookup(),
        "dependencies": self._extract_depencencies(),
        "memoized_conditions": self._precompute_condition_values(),
    }
    self.executable_graph = json.dumps(graph, cls=SafeJSONEncoder)
    self._cache_rule_actions()

# New: RuleEngine.execute_with_cache()
def execute_with_cache(self, doc, event_name=None):
    """Execute using pre-compiled executable graph."""
    graph = json.loads(self.rule.executable_graph)
    # Skip JSON parsing entirely
    return self._execute_compiled_graph(graph, context)
```

### 2.2 Memoization System

#### **Cache Layers:**
1. **Condition Result Cache** - Keyed by `(doc.doctype, doc.name, expression_hash)`
2. **Process Operation Cache** - Keyed by `(process_name, operation, config_hash)`  
3. **Template Cache** - Keyed by template content hash

```python
class ExecutionCache:
    def __init__(self):
        self._condition_cache = TTLCache(maxsize=1000, ttl=300)
        self._template_cache = LRUCache(maxsize=500)
        
    def get_condition_result(self, condition_hash, context_hash):
        key = f"{condition_hash}:{context_hash}"
        return self._condition_cache.get(key)
```

### 2.3 Tree Traversal Optimization

#### **Current:** Linear graph walking with per-node lookups
#### **Optimized:** Pre-compute reverse mappings, use adjacency lists

```python
# Pre-build during save
action_graph = {
    "action_id": {
        "type": "Process",
        "next_if_true": "ACT-002",
        "next_if_false": None,
        "compiled_handler": <handler_ref>,
    }
}
```

### 2.4 Asynchronous Execution Patterns

#### **Current:** Fire-and-forget with basic enqueue
#### **Enhanced:** Promise-based with cancellation tokens

```python
async def execute_async_with_cancellation(self, context, cancellation_token):
    try:
        async for action in self._stream_actions(context):
            if cancellation_token.is_cancelled():
                return {"status": "cancelled"}
            await action.execute_async(context)
    except Exception as e:
        return {"error": str(e)}
```

---

## Phase 3: No-Code Evolution & Reactive UX

### 3.1 Visual Execution Feedback

#### **Current Gap:** Test execution shows results but no step-by-step visualization

#### **Proposed Enhancement:**

```javascript
// Vue 3 Composition API - Real-time execution state
export const useExecutionVisualizer = () => {
  const activeNodeId = ref(null)
  const executedNodes = ref(new Set())
  const nodeResults = ref({})
  
  // Stream execution path in real-time
  const streamExecution = async (docname) => {
    const eventSource = new EventSource(`/api/method/flexirule.ruleflow.api.stream_execution?doc=${docname}`)
    eventSource.onmessage = (e) => {
      const data = JSON.parse(e.data)
      activeNodeId.value = data.nodeId
      executedNodes.value.add(data.nodeId)
      nodeResults.value[data.nodeId] = data.result
    }
  }
}
```

### 3.2 Reactive State Synchronization

#### **Current Issue:** Stores communicate via events, not reactive props

#### **Proposed Architecture:**

```javascript
// Unified reactive state composable
export const useRuleState = () => {
  const graph = reactive({
    nodes: [],
    edges: []
  })
  
  // Auto-sync to backend on change with debounce
  watch(graph, debounce(saveToServer, 500), { deep: true })
  
  return { graph }
}
```

### 3.3 Extensible Backend Schema

#### **New Process Definition Format:**

```json
{
  "name": "MyProcess",
  "operations": [
    {
      "func_name": "calculate_discount",
      "input_schema": {"order": "object", "customer": "string"},
      "output_schema": {"discount": "number", "reason": "string"},
      "contracts": {
        "requires_doc": true,
        "transactional": true,
        "has_side_effect": false,
        "writes_to": null
      }
    }
  ],
  "ui_schema": {
    "config_fields": [
      {
        "fieldname": "discount_percent",
        "fieldtype": "Float",
        "label": "Discount Percent",
        "default": 10
      }
    ]
  }
}
```

---

## Deliverables & Implementation Order

### Priority 1 (Critical - Must Fix Before RC)
1. [ ] Runtime JSON parsing elimination - enforce pre-compilation
2. [ ] Reentry guard thread-safety - Redis locks
3. [ ] Sub-rule depth enforcement
4. [ ] Execution log size limits

### Priority 2 (Performance - Before Production Scale)
5. [ ] Pre-compiled executable graph storage
6. [ ] Memoization cache layer
7. [ ] Registry incremental updates
8. [ ] Jinja template caching

### Priority 3 (No-Code Enhancement - Q2 Roadmap)
9. [ ] Real-time execution visualization
10. [ ] Reactive state composable refactoring
11. [ ] Streamable API endpoints
12. [ ] Process UI schema support

---

## File Changes Summary

| File | Changes | Reason |
|------|---------|--------|
| `core/engine.py` | Add pre-compiled graph execution, cache injection | Performance |
| `core/coordinator.py` | Redis reentry guards, incremental registry | Thread safety |
| `core/action_handlers/sub_rule.py` | Depth counter enforcement | Stability |
| `doctype/rule/rule.py` | Enforce compiled fields on save | Data integrity |
| `public/js/stores/*.js` | Reactive composables | UX |
| `docs/execution_engine.md` | Update for pre-compilation | Documentation |

---

## Next Steps

1. **Review this plan** with stakeholders for approval
2. **Create GitHub issues** for each priority item
3. **Begin Phase 1 implementation** starting with RC blockers
4. **Set up performance benchmarks** for before/after measurement