# FlexiRule Production Evolution Plan

## Executive Summary

FlexiRule has a solid foundation but needs targeted improvements to become production-ready for ERP workloads. Key findings:

1. **Architecture is sound** - Handler strategy pattern, context isolation, safe evaluation
2. **Sub-Rule design is functional but limited** - needs formal input/output contracts
3. **Process system is underutilized** - Operations contract exists but schema validation is weak
4. **Missing critical primitives** - Bulk operations, transaction boundaries, observability
5. **Builder UX needs refinement** - Translation gaps, naming inconsistencies

---

## 1. Architecture Review

### Findings

**Strengths:**

- Handler Strategy Pattern (`core/action_handlers/`) provides clean extensibility
- `SafeFrappeAPI` enforces security boundary in conditions
- Context isolation with `vars` namespace prevents scope pollution
- Cycle detection via visit counting (100 per node max)
- Execution log persistence with enqueue pattern avoids transaction issues

**Structural Limitations:**

| Issue                                 | Location                         | Impact                               | Decision                                                           |
| ------------------------------------- | -------------------------------- | ------------------------------------ | ------------------------------------------------------------------ |
| `return_type` is select, not enforced | `rule_action.json:288`           | No runtime type checking             | Add validation in `_post_process_action_result`                    |
| `config` is raw JSON with no schema   | `rule_action.json:160`           | Process configs can be malformed     | Add `config_schema` to Process Operation, validate at execute time |
| `operation` field is Autocomplete     | `rule_action.json:151`           | No static typing, no discoverability | Add `operation` to `ProcessOperation` and populate via API         |
| Action chaining relies on string IDs  | `rule_action.json:259-269`       | Fragile, no compile-time validation  | Keep string IDs, add validation in Rule.validate()                 |
| No explicit `entry_action_id` field   | Inferred from `action_id='root'` | Implicit contract                    | Keep root convention, document clearly                             |

### Action Type Contract Assessment

Current contract in `contracts.py`:

```
Entry Action: no required fields, has_next_true
Condition: required_fields=[condition_json], branching
Process: required_fields=[process_name, operation]
Stop: required_fields=[operation] (Terminal Mode)
Notify: required_fields=[value_template, operation]
Query Records: required_fields=[reference_doctype, operation]
Document Action: required_fields=[reference_doctype, operation]
```

**Missing from contracts.py:**

- `Loop` and `Switch` are disabled (RELEASE_DISABLED_ACTION_TYPES) - correct for v0.1
- No explicit validation that `return_variable` is set when `return_type` is set (already enforced in `rule.py:_validate_return_variable_requirement`)

**Recommended Changes to contracts.py:**

```python
# Add to ACTION_TYPE_CONTRACT for Process
"Process": {
    "required_fields": ["process_name", "operation"],
    "has_next_true": True,
    "has_next_false": False,
    "terminal": False,
    "css": {"icon": "fa fa-cog", "color": "#8b5cf6"},
    "dynamic_fields": True,
    "requires_return_variable": True,  # NEW: when writes_to != None
}
```

### Execution Model Evaluation

| Aspect           | Current                                            | Assessment                                       |
| ---------------- | -------------------------------------------------- | ------------------------------------------------ |
| Sync/Async       | Both via `is_async` field                          | OK - background jobs use enqueue                 |
| Timeout          | Via `max_execution_time` on Rule                   | OK - time_limit context manager + internal check |
| Retry            | `retry_count` + exponential backoff                | OK - implemented in engine                       |
| Error Handling   | `on_error` (Stop/Continue/Retry/Rollback/Escalate) | OK - comprehensive                               |
| Cycle Detection  | Visit counting (100 per node)                      | OK - sufficient for loops                        |
| Context Mutation | Via `mutation_mode` + `return_variable`            | OK - but needs documentation                     |

---

## 2. Reusability & Sub-Rule Design

### Current State

Sub-Rule is a first-class abstraction with:

- `exposed_as_subrule` flag on Rule
- `trigger_type="Callable Event"` requirement
- Cycle detection via `execution_stack` in context
- Depth limiting via `MAX_SUB_RULE_DEPTH=2` (hardcoded in two places: `engine.py:48` and `sub_rule.py:20`)

### Issues

1. **No input/output contracts** - Sub-Rule accepts any `doc` of matching DocType, returns nothing explicit
2. **Depth limit inconsistency** - Engine uses 2, sub_rule handler uses 2, but hardcoded separately
3. **Context leaking** - `context["vars"].update()` merges all vars back (no namespace isolation)
4. **Trigger conditions are optional** - `skip_conditions` defaults to 1 (skip)

### Decision: Enhance Sub-Rule, Don't Replace

Sub-Rule is the right abstraction. Improvements needed:

**1. Add Input/Output Contract to Rule DocType:**

```json
// New fields on Rule
{
    "fieldname": "input_schema",
    "fieldtype": "Code",
    "label": "Input Schema",
    "options": "JSON",
    "description": "[{\"fieldname\": \"var_name\", \"fieldtype\": \"Data\", \"label\": \"Description\"}]"
},
{
    "fieldname": "output_schema",
    "fieldtype": "Code",
    "label": "Output Schema",
    "options": "JSON",
    "description": "Expected vars keys and types returned by this rule"
}
```

**2. Add Sub-Rule Parameter Passing:**

In `Sub-Rule` action, add ability to pass parameters:

```json
// New field on RuleAction
{
	"fieldname": "sub_rule_params",
	"fieldtype": "Code",
	"label": "Sub-Rule Parameters",
	"options": "JSON",
	"description": "{\"param_name\": \"{{ vars.source_var }}\"}"
}
```

**3. Add Namespace Isolation:**

Modify `sub_rule.py` to namespace vars:

```python
# Instead of context["vars"].update(result_context.get("vars", {}))
# Use:
namespace = getattr(action, 'return_variable', None) or sub_rule_name.replace(" ", "_").lower()
context["vars"][namespace] = result_context.get("vars", {})
```

**4. Consolidate Depth Limit:**

```python
# In engine.py, read from sub_rule.py
MAX_SUB_RULE_DEPTH = MAX_SUB_RULE_DEPTH  # Import from sub_rule module
```

---

## 3. Process System Evaluation

### Current Architecture

```
Process (Doctype)
  └── ProcessOperation (Child Table)
        ├── func_name (Python function in process module)
        ├── config_schema (JSON Schema for operation config)
        ├── output_schema (JSON Schema for return)
        ├── writes_to (None/Context/Document/Database)
        ├── reads_vars / writes_vars
        └── transactional flag
```

Process modules in `ruleflow/process/`:

- `validation/` - field validation operations
- `normalization/` - string transformations
- `deduplication/` - fuzzy matching/scoring
- `batch/` - batch processing
- `enrichment/` - data enrichment
- `mdm/` - master data management

### Issues

| Issue                                         | Impact                            | Decision                                           |
| --------------------------------------------- | --------------------------------- | -------------------------------------------------- |
| No centralized operation registry             | Discoverability poor              | Add `get_available_operations()` API               |
| `config_schema` not enforced at runtime       | Malformed configs fail silently   | Add validation in `_call_process_with_retry`       |
| `output_schema` validation logs warnings only | Type mismatches not caught        | Make it a warning (current behavior is acceptable) |
| Process modules are file-backed               | No versioning, no UI management   | Keep file-backed, improve sync mechanism           |
| No bulk processing operation                  | Scheduler batch_size not utilized | Add `bulk_query` operation type                    |

### Process Adapter Improvements

**1. Standardize Operation Interface:**

All operations should follow this contract:

```python
def operation_name(context: dict, config: dict) -> dict:
    """
    Returns dict with:
    - result: the operation output
    - metadata: {operation: str, duration_ms: float, records_processed: int}
    """
    # Implementation
    return {"result": output_value, "metadata": {...}}
```

**2. Add Bulk Operation Support:**

```python
# New process: batch_operations
OPERATIONS = {
    "bulk_transform": bulk_transform,
    "bulk_validate": bulk_validate,
    "bulk_normalize": bulk_normalize,
}

def bulk_transform(context, config):
    """
    Config:
    {
        "records": "{{ vars.contact_records }}",  # List of dicts
        "field_transformations": [
            {"field": "phone", "transform": "numeric_only"}
        ],
        "output_field": "normalized_records"
    }
    """
```

**3. Enforce Config Schema:**

```python
# In engine.py _call_process_with_retry
if op_def and op_def.config_schema:
    schema = json.loads(op_def.config_schema)
    validate(config, schema)  # From jsonschema
```

---

## 4. Real Use Case Rules (Frappe Core DocTypes Only)

### Rule 1: Scheduler Data Pipeline (Contact Normalization)

**Trigger:** Scheduler Event (Daily)
**Purpose:** Normalize Contact names, detect duplicates

```
Actions:
1. Entry Action (root)
   └── next: ACT-QUERY

2. Query Records (ACT-QUERY)
   - operation: Query List
   - reference_doctype: Contact
   - filter_doctype: Contact
   - filters: {"exposed_name": ["is", "not set"]}  # Or custom condition
   - mutation_mode: Set Context Variable
   - return_variable: contact_batch
   - return_type: List of Dict
   - next: ACT-NORMALIZE

3. Process (ACT-NORMALIZE) - Normalization
   - process_name: Normalization
   - operation: normalize_multiple_fields
   - config: {
       "field_config": [
         {"fieldname": "first_name", "transformations": ["trim", "casefold"]},
         {"fieldname": "last_name", "transformations": ["trim", "casefold"]}
       ],
       "store_in_context": true
     }
   - return_variable: normalized_batch
   - return_type: Dict
   - next: ACT-DEDUP

4. Process (ACT-DEDUP) - Deduplication
   - process_name: Deduplication
   - operation: fuzzy_match
   - config: {
       "source_records": "{{ vars.normalized_batch }}",
       "match_fields": ["first_name", "last_name"],
       "threshold": 0.85
     }
   - return_variable: duplicate_groups
   - return_type: List
   - next: ACT-DECIDE

5. Condition (ACT-DECIDE)
   - condition_json: [{"left": {"ref": "vars.duplicate_groups"}, "op": "==", "right": {"value": null}}]
   - next_step_if_true: ACT-END  # No duplicates
   - next_step_if_false: ACT-CREATE-TODO

6. Document Action (ACT-CREATE-TODO) - Create Review Task
   - operation: Create ToDo
   - reference_doctype: ToDo
   - config: {
       "description": "Review {{ vars.duplicate_groups | length }} duplicate contact groups"
     }
   - next: ACT-END

7. Stop (ACT-END)
   - operation: Success
```

### Rule 2: Reusable Sub-Rule (Phone Validation)

**Trigger:** Callable Event (for Contact DocType)
**Exposed As Sub-Rule:** Yes

```
Input Contract:
- doc: Contact (required)
- vars.validate_phones_strict: bool (optional)

Actions:
1. Entry Action (root)
   └── next: ACT-GET-PHONES

2. Process (ACT-GET-PHONES) - Read child table
   - process_name: Validation
   - operation: child_table_rows (custom)
   - config: {
       "child_table": "phone_numbers",
       "validations": [...]
     }
   - return_variable: phone_rows
   - next: ACT-CHECK-PRIMARY

3. Condition (ACT-CHECK-PRIMARY)
   - condition_json: [{"left": {"ref": "vars.phone_rows"}, "op": "length >", "right": {"value": 0}}]
   - next_step_if_false: ACT-ERROR-NO-PHONES
   - next_step_if_true: ACT-DEDUP-CHECK

4. Condition (ACT-DEDUP-CHECK) - Detect duplicate in same doc
   - condition_json: [{"left": {"ref": "vars.phone_rows"}, "op": "has_duplicates", "right": {"field": "phone"}}}
   - next_step_if_false: ACT-RETURN
   - next_step_if_true: ACT-ERROR-DUPLICATE

5. Stop (ACT-ERROR-NO-PHONES) - Error
   - value_template: "At least one phone number is required"

6. Stop (ACT-ERROR-DUPLICATE) - Error
   - value_template: "Duplicate phone numbers found in document"

7. Stop (ACT-RETURN) - Success
   - operation: Success
```

### Rule 3: DocType Event Rule (before_save Contact)

**Trigger:** DocType Event, Contact, Before Save

```
Actions:
1. Entry Action (root)
   └── next: ACT-CHECK-PHONES

2. Condition (ACT-CHECK-PHONES)
   - condition_json: [{"left": {"ref": "doc.phone_numbers"}, "op": "==", "right": {"value": null}}]
   - next_step_if_false: ACT-QUERY-EXISTING
   - next_step_if_true: ACT-ERROR

3. Stop (ACT-ERROR) - Error
   - operation: Error
   - value_template: "Phone numbers child table cannot be empty"

4. Query Records (ACT-QUERY-EXISTING)
   - operation: Exist Record
   - reference_doctype: Contact
   - filters: [
       {"field": "phone_numbers.phone", "operator": "=", "value": "{{ doc.phone_numbers[0].phone }}"},
       {"field": "name", "operator": "!=", "value": "{{ doc.name }}"}
     ]
   - mutation_mode: Set Context Variable
   - return_variable: phone_exists
   - return_type: Boolean
   - next: ACT-CHECK-RESULT

5. Condition (ACT-CHECK-RESULT)
   - condition_json: [{"left": {"ref": "vars.phone_exists"}, "op": "==", "right": {"value": true}}]
   - next_step_if_false: ACT-VALIDATE-SUBRULE
   - next_step_if_true: ACT-ERROR-DUPLICATE

6. Sub-Rule (ACT-VALIDATE-SUBRULE) - Call phone validation sub-rule
   - rule: Phone Validation Sub-Rule
   - skip_conditions: 1
   - next: ACT-END

7. Stop (ACT-ERROR-DUPLICATE) - Error
   - operation: Error
   - value_template: "Contact with same phone number already exists"

8. Stop (ACT-END) - Success
   - operation: Success
```

### Rule 4: Async Rule with Retry (Email Campaign)

**Trigger:** Scheduler Event (Hourly)

```
Actions:
1. Entry Action (root)
   └── next: ACT-QUERY

2. Query Records (ACT-QUERY)
   - operation: Query List
   - reference_doctype: Email Campaign
   - filters: {"status": "Pending", "scheduled_date": "<=", "{{ frappe.utils.now() }}"}
   - mutation_mode: Set Context Variable
   - return_variable: campaigns
   - return_type: List of Dict
   - next: ACT-PROCESS

3. Process (ACT-PROCESS) - Batch email
   - process_name: Batch
   - operation: process_batch
   - config: {
       "items": "{{ vars.campaigns }}",
       "batch_size": 50,
       "operation": "send_email"
     }
   - on_error: Retry
   - retry_count: 3
   - is_async: 1
   - return_variable: results
   - return_type: Dict
   - next: ACT-LOG

4. Document Action (ACT-LOG) - Update status
   - operation: Update Existing
   - reference_doctype: Email Campaign
   - mutation_mode: Set Doc Field
   - config: {
       "status": "Processed",
       "processed_at": "{{ frappe.utils.now() }}"
     }
   - next: ACT-END

5. Stop (ACT-END) - Success
   - operation: Success
```

### Rule 5: Process-Chain Rule (Lead Scoring)

**Trigger:** DocType Event, Lead, After Save

```
Actions:
1. Entry Action (root)
   └── next: ACT-EXTRACT

2. Process (ACT-EXTRACT) - Enrichment: Extract features
   - process_name: Enrichment
   - operation: extract_lead_features
   - config: {
       "source_fields": ["company", "industry", "source"],
       "output_var": "lead_features"
     }
   - return_variable: features
   - return_type: Dict
   - next: ACT-SCORE

3. Process (ACT-SCORE) - Deduplication: Score lead
   - process_name: Deduplication
   - operation: calculate_score
   - config: {
       "features": "{{ vars.features }}",
       "weights": {"company": 0.3, "industry": 0.4, "source": 0.3}
     }
   - return_variable: score
   - return_type: Dict
   - next: ACT-MAP

4. Process (ACT-MAP) - Transform: Map score to tier
   - process_name: Normalization
   - operation: normalize_field_to_context
   - config: {
       "source_field": "vars.score.total",
       "transformations": ["map_ranges"],
       "context_key": "lead_tier"
     }
   - return_variable: tier
   - return_type: String
   - next: ACT-SET

5. Set Value (ACT-SET) - Update lead tier
   - target_field: lead_owner
   - value_template: "{% if vars.tier == 'A' %}sales_team_a{% elif vars.tier == 'B' %}sales_team_b{% else %}sales_team_c{% endif %}"
   - next: ACT-END

6. Stop (ACT-END) - Success
   - operation: Success
```

---

## 5. Unit Testing Strategy

### Framework: FrappeTestCase (already in use)

### Test Coverage Matrix

| Category       | Test File                      | Coverage                  |
| -------------- | ------------------------------ | ------------------------- |
| Engine Core    | `test_engine_comprehensive.py` | 959 lines - comprehensive |
| Coordinator    | `test_coordinator.py`          | Hook integration          |
| API            | `test_api.py`                  | Whitelisted endpoints     |
| Advanced Flows | `test_advanced_rule_flows.py`  | Real-world scenarios      |

### Missing Tests

**1. Sub-Rule Isolation Tests:**

```python
def test_sub_rule_vars_namespace(self):
    """Sub-Rule vars should be namespaced, not leak into parent"""
    # Setup
    sub_rule = self.create_test_rule("Test Sub NS", trigger_type="Callable Event", exposed_as_subrule=1)
    sub_rule.actions[1].return_variable = "sub_result"
    sub_rule.save()

    main_rule = self.create_test_rule("Test Main NS")
    # Add Sub-Rule action

    engine = RuleEngine(main_rule)
    result = engine.execute(doc)

    # Verify
    self.assertIn("sub_result", result["vars"])
    self.assertNotIn("other_var", result["vars"])

def test_sub_rule_input_contract(self):
    """Sub-Rule should validate input schema"""
    pass

def test_sub_rule_cycle_detection_cross_rule(self):
    """Cross-rule cycle detection via execution_stack"""
    pass
```

**2. Process Schema Validation Tests:**

```python
def test_process_config_schema_validation(self):
    """Config should be validated against config_schema"""
    # Create Process with config_schema
    # Pass invalid config
    # Expect ValidationError

def test_process_output_schema_validation(self):
    """Output should be validated against output_schema"""
    # Create operation with wrong output type
    # Expect warning logged
```

**3. Context Mutations Tests:**

```python
def test_mutation_mode_batch_database(self):
    """Batch Database Set mutation mode works correctly"""
    pass

def test_mutation_mode_append_to_context_variable(self):
    """Append to Context Variable accumulates"""
    pass
```

**4. Error Scenarios:**

```python
def test_retry_exponential_backoff(self):
    """Retry uses exponential backoff"""
    pass

def test_rollback_savepoint_restores(self):
    """Rollback restores to savepoint"""
    pass

def test_escalate_error_propagates(self):
    """Escalate propagates error up"""
    pass
```

### Test Data Strategy

- Use **ToDo** for simple document operations
- Use **Contact** + **Contact Phone** child table for complex scenarios
- Use **DocType** for testing schema/field operations
- Create test fixtures in `test_engine_comprehensive.py::setUp()`

---

## 6. Gaps & Missing Features

### Critical Gaps

| Gap                        | Current State            | Impact                          | Proposed Solution                                                    |
| -------------------------- | ------------------------ | ------------------------------- | -------------------------------------------------------------------- |
| **Bulk Operations**        | No dedicated action type | Scheduler batch_size unused     | Add `Bulk Process` action type or enhance `Process` with bulk config |
| **Transaction Boundaries** | Partial (savepoints)     | Partial rollback possible       | Add `Transaction` action type with commit/rollback                   |
| **Observability**          | Basic execution log      | Hard to debug production issues | Add structured tracing with trace_id correlation                     |
| **Loop Primitive**         | Disabled                 | Cannot iterate                  | Re-enable with proper guardrails                                     |

### Proposed Designs

**1. Transaction Action Type:**

```json
{
	"action_type": "Transaction",
	"required_fields": ["operation"],
	"operation_options": ["Begin", "Commit", "Rollback", "Savepoint"],
	"config": {
		"savepoint_name": "my_sp",
		"isolation_level": "READ COMMITTED"
	}
}
```

**2. Loop Re-enablement:**

- Add `max_iterations` to Loop config (default 1000)
- Add `break_on_condition` support
- Add iteration counter to context: `vars.__loop_index`

**3. Observability Enhancement:**

```python
# Add trace_id to context
context["meta"]["trace_id"] = frappe.utils.generate_uuid()

# Log with correlation
self._log("INFO", f"[{trace_id}] Action {action_id} executed", extra={"trace_id": trace_id})

# Store in execution log
log_doc.trace_id = trace_id
```

### Process System Improvements

**1. Add Operation Registry API:**

```python
@frappe.whitelist()
def get_process_operations(process_name):
    """Return available operations for a process with metadata"""
    process = frappe.get_cached_doc("Process", process_name)
    return [{
        "name": op.func_name,
        "label": op.label,
        "description": op.description,
        "writes_to": op.writes_to,
        "config_schema": op.config_schema,
        "output_schema": op.output_schema
    } for op in process.operations if op.enabled]
```

**2. Standardize Process Output:**

All operations should return:

```python
{
    "result": ...,        # Primary output
    "metadata": {         # Execution metadata
        "operation": "operation_name",
        "duration_ms": 45,
        "records_processed": 100
    }
}
```

---

## 7. Builder (Vue3) Improvements

### UX Issues Identified

| Issue                                             | Location               | Impact           |
| ------------------------------------------------- | ---------------------- | ---------------- |
| Duplicate labels in return_type options           | `contracts.py:161`     | User confusion   |
| No translation for "Return Type" options          | `contracts.py:161`     | Not i18n ready   |
| "operation" label too generic                     | `rule_action.json:153` | Ambiguous        |
| "Configure" button text not translated            | `rule_action.json:323` | Not i18n ready   |
| Dynamic fields for Process not clearly documented | `contracts.py:43`      | Users don't know |

### Improvements

**1. Normalize Labels (contracts.py):**

```python
RETURN_TYPE_OPTIONS = [
    "Boolean (True/False)",
    "Dictionary (Single Object)",
    "List (Array of Items)",
    "List of Dictionaries (Table Data)",
    "Document as Dictionary"
]
```

**2. Add Translation Wrapper Function:**

```python
def get_contract_dto() -> dict:
    """Export a frontend-safe contract payload with translated strings"""
    return {
        ...
        "return_type_options": [window.__(opt) for opt in RETURN_TYPE_OPTIONS],
    }
```

**3. Rename Confusing Fields:**

In `contracts.py`, add `field_renames` to contract:

```python
ACTION_TYPE_CONTRACT["Process"]["field_renames"] = {
    "operation": "Operation / Method",
    "config": "Configuration (JSON)"
}
```

**4. Process Configuration UX:**

Add visual preview for Process config:

- Show operation signature (inputs/outputs)
- Show example config
- Validate against schema before save

**5. Improve Loop/Switch UI:**

Since these are disabled, show clear "Coming Soon" messaging in the builder with:

- Disabled state styling
- Link to documentation explaining when they'll be available

---

## 8. Implementation Priority

### Phase 1: Quick Wins (1-2 weeks)

1. Add translations to contract.py return_type_options
2. Consolidate MAX_SUB_RULE_DEPTH to single constant
3. Add operation metadata API
4. Fix duplicate labels in RETURN_TYPE_OPTIONS

### Phase 2: Core Improvements (2-4 weeks)

1. Sub-Rule input/output contracts (add fields to Rule)
2. Namespace isolation for sub-rule vars
3. Process config_schema validation at runtime
4. Add trace_id for observability

### Phase 3: Missing Primitives (4-8 weeks)

1. Re-enable Loop with proper guardrails
2. Add Transaction action type
3. Bulk operations for Process
4. Enhanced execution log with trace correlation

### Phase 4: Testing & Polish (ongoing)

1. Complete unit test coverage for missing scenarios
2. Integration tests for scheduler with batch processing
3. Builder UX improvements
4. Documentation

---

## 9. Decision Summary

| Decision                                 | Rationale                                   |
| ---------------------------------------- | ------------------------------------------- |
| Keep Sub-Rule as first-class abstraction | Works well, just needs contracts            |
| Consolidate depth limit                  | Currently in two places, risk of divergence |
| Keep file-backed Process modules         | Works well, no need for DB-backed           |
| Add transaction action type              | Critical for ERP workflows                  |
| Re-enable Loop with guardrails           | Frequently needed, just needs proper limits |
| Add trace_id observability               | Production debugging essential              |
| Standardize operation output             | Enables better chaining and debugging       |

---

## 10. Files to Modify

### High Priority

1. `flexirule/ruleflow/core/contracts.py` - Return type translations, field renames
2. `flexirule/ruleflow/core/action_handlers/sub_rule.py` - Namespace isolation, depth constant import
3. `flexirule/ruleflow/core/engine.py` - Trace ID, consolidated MAX_SUB_RULE_DEPTH
4. `flexirule/ruleflow/doctype/rule/rule.json` - Add input_schema, output_schema fields
5. `flexirule/ruleflow/doctype/rule/rule.py` - Validate new schema fields

### Medium Priority

6. `flexirule/ruleflow/doctype/process/process.py` - Add operation registry API
7. `flexirule/ruleflow/core/action_handlers/process.py` - Add config_schema validation
8. `flexirule/ruleflow/doctype/rule_action/rule_action.json` - Add sub_rule_params field

### Testing

9. `flexirule/ruleflow/tests/test_engine_comprehensive.py` - Add missing tests
10. Create new test files for sub-rule isolation, process schemas
