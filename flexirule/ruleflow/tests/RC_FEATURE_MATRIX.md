# FlexiRule RC-Ready Feature Matrix

## Overview

This document defines the supported, unsupported, and deferred features for FlexiRule Release Candidate (RC).

## Trigger Types

| Trigger Type    | Status                 | Notes                                             |
| --------------- | ---------------------- | ------------------------------------------------- |
| DocType Event   | ✅ **FULLY SUPPORTED** | All document events (Before Save, Validate, etc.) |
| Scheduler Event | ✅ **FULLY SUPPORTED** | With Rule Scheduler configuration                 |
| Callable Event  | ✅ **FULLY SUPPORTED** | For Sub-Rule invocation                           |

### Trigger Type Details

**DocType Event**

- document_type: Required
- trigger_event: Required (from predefined list)
- trigger_condition: Optional (compiled to Python expression)
- Scheduler Filter DocType: Optional

**Scheduler Event**

- document_type: Optional (if batch processing)
- Scheduler Frequency: Required (All/Hourly/Daily/Weekly/Monthly/Cron)
- Scheduler Filters: Optional

**Callable Event**

- document_type: Optional (allows generic reusable rules)
- Must be exposed_as_subrule=1 to be callable

## Action Types

| Action Type     | Status                 | Notes                                      |
| --------------- | ---------------------- | ------------------------------------------ |
| Entry Action    | ✅ **FULLY SUPPORTED** | Root node of rule graph                    |
| Condition       | ✅ **FULLY SUPPORTED** | JSON condition builder + Python expression |
| Process         | ✅ **FULLY SUPPORTED** | Via Process adapters                       |
| Set Value       | ✅ **FULLY SUPPORTED** | Jinja template support                     |
| Stop            | ✅ **FULLY SUPPORTED** | Success and Error modes                    |
| Notify          | ✅ **FULLY SUPPORTED** | Toast, System, Email, Provider             |
| Query Records   | ✅ **FULLY SUPPORTED** | All query modes                            |
| Document Action | ✅ **FULLY SUPPORTED** | Create/Update/Delete/ToDo/Comment          |
| Sub-Rule        | ✅ **FULLY SUPPORTED** | Callable rule invocation                   |
| Wait            | ✅ **FULLY SUPPORTED** | Duration-based delays                      |
| Loop            | 🚫 **NOT SUPPORTED**   | RC deferred                                |
| Switch          | 🚫 **NOT SUPPORTED**   | RC deferred                                |

## Supported Operations per Action

### Query Records Operations

- ✅ Query List
- ✅ Query Doc
- ✅ Exist Record
- ✅ Query Report
- ✅ Count, Sum, Average, Min, Max
- ✅ Group By

### Document Action Operations

- ✅ Create New
- ✅ Update Existing
- ✅ Delete Record
- ✅ Create ToDo
- ✅ Add Comment

### Notify Operations

- ✅ Toast
- ✅ System (frappe.log)
- ✅ Email
- ✅ System Notification
- ✅ Provider (custom)

## Mutation Modes

| Mutation Mode              | Status | Supported Actions              |
| -------------------------- | ------ | ------------------------------ |
| Set Doc Field              | ✅     | Document Action                |
| Update Doc Field           | ✅     | Document Action                |
| Set Context Variable       | ✅     | Query Records, Document Action |
| Update Context Variable    | ✅     | Query Records, Document Action |
| Append to Context Variable | ✅     | Query Records                  |
| Batch Database Set         | ✅     | Document Action                |

## Return Types

- ✅ Boolean
- ✅ Dict
- ✅ List
- ✅ List of Dict
- ✅ Doc as Dict

## Context Variables

All action types can produce context variables via `return_variable`.

### Standard Variable DTO

```json
{
	"name": "variable_name",
	"type": "string|boolean|list|dict",
	"declared_type": "Boolean|Dict|List|...",
	"value_preview": "...",
	"source_action_id": "action_123"
}
```

## Security Features

| Feature                              | Status                        |
| ------------------------------------ | ----------------------------- |
| SafeFrappeAPI in conditions          | ✅ Supported                  |
| Permission bypass (skip_permissions) | ✅ Supported with audit trail |
| Role-based skip (skip_for_roles)     | ✅ Supported                  |
| Rule permission table                | ✅ Supported                  |
| Dry-run mode                         | ✅ Supported                  |
| Timeout protection                   | ✅ Supported                  |

## Testing Features

| Feature                            | Status       |
| ---------------------------------- | ------------ |
| test_rule API (direct from engine) | ✅ Supported |
| save_log flag                      | ✅ Supported |
| Execution path trace               | ✅ Supported |
| Context snapshot                   | ✅ Supported |
| Execution log                      | ✅ Supported |

## Builder Features

| Feature                      | Status       |
| ---------------------------- | ------------ |
| VueFlow visual editor        | ✅ Supported |
| Drag-and-drop nodes          | ✅ Supported |
| Edge connections             | ✅ Supported |
| Condition builder (JSON)     | ✅ Supported |
| Config modal per action type | ✅ Supported |
| Undo/Redo                    | ✅ Supported |
| Dirty state tracking         | ✅ Supported |
| Backend pre-validation       | ✅ Supported |

## Limitation Summary

### RC Blockers Resolved

1. ✅ test_rule() no longer depends on DB log
2. ✅ Sub-rule document_type coupling relaxed
3. ✅ Context variable DTO standardized
4. ✅ Action contract normalization enforced

### Deferred to Post-RC

1. 🚫 Loop action type
2. 🚫 Switch action type
3. 🚫 Async output mapping (with Async enabled)
4. 🚫 Multi-document transaction support

### Breaking Changes for RC

1. **Sub-Rule document_type**: Callable rules without document_type are now allowed (previously required matching)
2. **test_rule API**: Now returns `execution_path` directly from engine instead of from DB log
3. **Action Type Normalization**: "Raise Error" → "Stop" (with operation="Error")
4. **mutation_mode field name**: Still current; to be renamed in future version
5. **"Manual" terminology removed**: Replaced with "Callable Event"

## Validation Checklist

Before RC release, ensure:

- [ ] All 5 production rules can be created and tested
- [ ] test_rule API returns correct execution path
- [ ] Sub-rule with null document_type works when called from parent rule
- [ ] All disabled action types (Loop, Switch) are hidden in UI
- [ ] All action types match backend contract
- [ ] No orphaned DB dependencies in test_mode
