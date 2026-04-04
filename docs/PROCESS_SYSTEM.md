# FlexiRule Process System

> **Ground Truth**: Documented based on actual implementation in `flexirule/ruleflow/core/action_handlers/process.py` and `flexirule/ruleflow/core/process_sync.py`.

---

## 1. Core Concepts

### 1.1 Process Definition

A **Process** is a modular, reusable unit of business logic composed of **Operations**. It serves as a container that ties together multiple atomic operations that can be executed as part of a `Process` action in a Rule.

**Key characteristics:**

- Processes can be file-backed (defined in JSON + Python) or database-only
- Each Process contains multiple Operations (child table)
- Processes are synced from code during `bench migrate`

### 1.2 Process Operation

An **Operation** is an atomic task within a Process. It defines:

- The function to call (Python function name)
- Configuration schema (UI inputs)
- Output schema (return value validation)
- Contract metadata (reads_vars, writes_to, etc.)

### 1.3 Process Action

In a Rule, the `Process` action type executes a specific operation from a Process:

```
Rule Action → Process (action type)
           → process_name = "My Process"
           → operation = "validate_email"
           → config = {...}
```

---

## 2. Process Architecture

### 2.1 Directory Structure

```
flexirule/
├── ruleflow/
│   ├── doctype/
│   │   ├── process/
│   │   │   ├── process.json          # DocType definition
│   │   │   └── process.py            # DocType controller
│   │   └── process_operation/
│   │       ├── process_operation.json
│   │       └── process_operation.py
│   └── process/
│       ├── batch/
│       │   ├── batch.py              # Process adapter
│       │   └── batch.json           # Process definition + operations
│       ├── enrichment/
│       ├── validation/
│       ├── deduplication/
│       ├── normalization/
│       └── mdm/
└── apps/
    └── my_custom_app/
        └── my_custom_app/
            └── process/
                └── my_process/
                    ├── my_process.py  # Custom process adapter
                    └── my_process.json  # Process definition
```

### 2.2 Process DocType Fields

| Field                 | Type              | Description                   |
| --------------------- | ----------------- | ----------------------------- |
| `process_name`        | Data (unique)     | Unique identifier             |
| `is_standard`         | Select (Yes/No)   | "Yes" = file-backed           |
| `module`              | Link (Module Def) | Associated module             |
| `reference_column`    | Column Break      | -                             |
| `default_ref_doctype` | Link (DocType)    | Default reference             |
| `description`         | Data              | Description                   |
| `operations_section`  | Section Break     | -                             |
| `operations`          | Table             | Process Operation child table |

### 2.3 Process Operation Fields

| Field                | Type   | Description                       |
| -------------------- | ------ | --------------------------------- |
| `func_name`          | Data   | Python function name              |
| `label`              | Data   | Display name                      |
| `enabled`            | Check  | Operation availability            |
| `visible_in_builder` | Check  | Show in UI                        |
| `icon`               | Data   | Icon class                        |
| `color`              | Data   | Color hex                         |
| `requires_doc`       | Check  | Needs context.doc                 |
| `can_stop_save`      | Check  | Can halt document save            |
| `is_terminal`        | Check  | Terminates flow                   |
| `writes_to`          | Select | Document/Context/None/Database    |
| `allows_async`       | Check  | Supports async execution          |
| `transactional`      | Check  | Supports savepoint rollback       |
| `reads_vars`         | Code   | JSON array of input vars          |
| `writes_vars`        | Code   | JSON array of output vars         |
| `config_schema`      | Code   | JSON Schema for config UI         |
| `output_schema`      | Code   | JSON Schema for return validation |

---

## 3. Process JSON Definition Format

File-backed processes use this JSON structure:

```json
{
	"process_name": "Deduplication",
	"module": "Ruleflow",
	"description": "Find and merge duplicate records",
	"operations": [
		{
			"func_name": "find_duplicates",
			"label": "Find Duplicates",
			"enabled": 1,
			"visible_in_builder": 1,
			"requires_doc": 1,
			"writes_to": "Context",
			"transactional": 1,
			"reads_vars": ["customer_name", "email"],
			"writes_vars": ["duplicates", "match_score"],
			"config_schema": [
				{
					"fieldname": "threshold",
					"fieldtype": "Float",
					"label": "Match Threshold",
					"default": 0.8,
					"description": "Minimum similarity score (0-1)"
				},
				{
					"fieldname": "match_fields",
					"fieldtype": "Table MultiSelect",
					"label": "Fields to Match",
					"options": "DocField"
				}
			],
			"output_schema": {
				"type": "object",
				"properties": {
					"duplicates": {
						"type": "array",
						"items": { "type": "object" }
					},
					"match_score": {
						"type": "number"
					}
				},
				"required": ["duplicates"]
			}
		},
		{
			"func_name": "merge_records",
			"label": "Merge Records",
			"enabled": 1,
			"writes_to": "Document",
			"transactional": 1
		}
	]
}
```

---

## 4. Process Adapter

### 4.1 Adapter Structure

The process adapter is a Python file with an `execute()` entry point:

```python
# ruleflow/process/deduplication/deduplication.py

import frappe
from frappe import _

def execute(context, func=None, config=None):
    """
    Entry point called by Process.execute()

    Args:
        context: Execution context dict
        func: Operation function name
        config: Operation configuration

    Returns:
        Result dict conforming to output_schema
    """
    operations = {
        "find_duplicates": find_duplicates,
        "merge_records": merge_records,
        "score_record": score_record,
    }

    if func and func in operations:
        return operations[func](context, config)

    frappe.throw(_("Operation {0} not found").format(func))


def find_duplicates(context, config):
    """
    Find duplicate records based on configuration.

    Args:
        context: Contains doc, vars, frappe (SafeFrappeAPI)
        config: Operation configuration from action

    Returns:
        dict with duplicates list and match_score
    """
    doc = context.get("doc")

    # Read configuration
    threshold = config.get("threshold", 0.8)
    match_fields = config.get("match_fields", [])

    # Read from context vars
    customer_name = context.get("vars", {}).get("customer_name")

    # Business logic
    duplicates = []
    match_score = 0.0

    # ... matching logic ...

    return {
        "duplicates": duplicates,
        "match_score": match_score,
        "searched_fields": match_fields
    }


def merge_records(context, config):
    """
    Merge duplicate records.
    """
    doc = context.get("doc")
    vars = context.get("vars", {})

    # Get duplicates from context
    duplicates = vars.get("duplicates", [])

    if not duplicates:
        return {"merged": False, "reason": "No duplicates found"}

    # Merge logic
    primary = doc
    for duplicate in duplicates[1:]:
        # Transfer data, delete duplicate
        pass

    return {"merged": True, "count": len(duplicates)}


def score_record(context, config):
    """
    Score a record for duplicate detection.
    """
    # Import scoring module
    from flexirule.ruleflow.process.deduplication.scoring import calculate_similarity

    doc = context.get("doc")

    reference_name = config.get("reference_name")
    reference_doc = frappe.get_doc(doc.doctype, reference_name)

    score = calculate_similarity(doc, reference_doc)

    return {"score": score, "above_threshold": score >= config.get("threshold", 0.8)}
```

### 4.2 Operation Contract

Each operation function must:

1. Accept `(context, config)` parameters
2. Return a `dict` conforming to `output_schema`
3. Use `SafeFrappeAPI` for read operations in conditions
4. Handle errors gracefully

### 4.3 Context Access Patterns

```python
def my_operation(context, config):
    # Access document
    doc = context.get("doc")
    if not doc:
        frappe.throw("Operation requires a document")

    # Access old document (before save)
    old_doc = context.get("old_doc")

    # Access execution variables
    vars = context.get("vars", {})
    my_var = vars.get("my_variable")

    # Access safe Frappe API
    frappe_safe = context.get("frappe")
    value = frappe_safe.get_value("Customer", {"name": "Acme"}, "customer_name")

    # Access metadata
    meta = context.get("meta", {})
    rule_name = meta.get("rule")
    user = meta.get("user")

    return {"result": "success"}
```

---

## 5. Process Execution

### 5.1 Execution Flow

```
Process Action (Rule)
  → ProcessHandler.execute()
    → engine._call_process_with_retry()
      → Process DocType record lookup
        → process.execute(context, func=operation, config=...)
          → Process adapter's execute() function
            → Specific operation function
      → Runtime contract enforcement
      → Savepoint management (if transactional)
      → Output schema validation
```

### 5.2 Runtime Contract Enforcement

In `engine.py:755-856`, the engine enforces:

**1. requires_doc**

```python
if op_def and op_def.requires_doc:
    if not context.get("doc"):
        raise MethodExecutionError(
            f"Operation {operation} requires a document but context.doc is not set"
        )
```

**2. writes_to == "Document" in After events (Warning)**

```python
if op_def and op_def.writes_to == "Document":
    event_name = context.get("event_name")
    after_events = ["After Insert", "After Save", "On Submit", ...]
    if event_name in after_events:
        self._log("WARNING", "Operation writes to Document in 'After' event...")
```

**3. has_side_effect (Info log)**

```python
if op_def and op_def.has_side_effect:
    self._log("INFO", "Executing operation with side effects")
```

**4. transactional (Savepoint)**

```python
if op_def and op_def.transactional:
    frappe.db.savepoint(savepoint_name)
    try:
        result = process_doc.execute(context, func=operation, config=config)
        frappe.db.release_savepoint(savepoint_name)
    except Exception:
        frappe.db.rollback(save_point=savepoint_name)
        raise
```

**5. output_schema (Warning on failure)**

```python
if op_def and op_def.output_schema:
    self._validate_output_against_schema(result, op_def.output_schema, operation)
```

### 5.3 Config Schema for UI

The `config_schema` field defines what configuration fields appear in the UI:

```json
[
	{
		"fieldname": "email_field",
		"fieldtype": "Link",
		"label": "Email Field",
		"options": "DocField",
		"description": "Select the field containing email addresses"
	},
	{
		"fieldname": "check_dns",
		"fieldtype": "Check",
		"label": "Verify DNS Records",
		"default": 0
	},
	{
		"fieldname": "validation_type",
		"fieldtype": "Select",
		"label": "Validation Type",
		"options": "Strict\nLoose\nCustom",
		"depends_on": "eval:doc.check_dns==1",
		"reqd": 1
	}
]
```

---

## 6. Process Sync

### 6.1 Sync Process

Processes are synced from file to database during `bench migrate`:

```
after_migrate hook
  → sync_all_processes()
    → For each installed app
      → sync_processes_for_app(app_name)
        → For each module in app
          → Find {module}/process/{name}/{name}.json
            → import_process_from_file(json_path, module_name)
              → Create or update Process DocType
              → Sync operations from JSON
```

### 6.2 Sync Logic (`process_sync.py`)

```python
def import_process_from_file(json_path, module_name):
    with open(json_path) as f:
        data = json.load(f)

    process_name = data["process_name"]

    if frappe.db.exists("Process", process_name):
        # Update existing
        doc = frappe.get_doc("Process", process_name)
        # Sync operations (add/update/remove)
        doc.save()
    else:
        # Create new
        doc = frappe.new_doc("Process")
        doc.process_name = process_name
        doc.module = module_name
        # Add operations
        doc.insert()
```

### 6.3 Pruning

Processes that no longer have a file backing are removed:

```python
def _prune_missing_standard_processes(module_names, expected_process_names):
    existing = frappe.get_all("Process", filters={
        "module": ["in", module_names],
        "is_standard": "Yes"
    })

    for process in existing:
        if process.name not in expected_process_names:
            frappe.delete_doc("Process", process.name, force=True)
```

---

## 7. Built-in Processes

### 7.1 Deduplication Process

**Location**: `flexirule/ruleflow/process/deduplication/`

**Operations**:

- `find_duplicates` - Find duplicate records
- `merge_records` - Merge duplicates
- `score_record` - Score for duplicate detection

### 7.2 Enrichment Process

**Location**: `flexirule/ruleflow/process/enrichment/`

**Operations**:

- `enrich_from_external` - Enrich data from external sources
- `enrich_from_linked` - Enrich from linked documents

### 7.3 Validation Process

**Location**: `flexirule/ruleflow/process/validation/`

**Operations**:

- `validate_fields` - Validate document fields
- `validate_uniqueness` - Check for duplicate values

### 7.4 MDM Process

**Location**: `flexirule/ruleflow/process/mdm/`

**Operations**:

- `standardize_format` - Standardize data format
- `update_references` - Update cross-document references

### 7.5 Normalization Process

**Location**: `flexirule/ruleflow/process/normalization/`

**Operations**:

- `normalize_text` - Text normalization
- `normalize_numbers` - Number standardization

### 7.6 Batch Process

**Location**: `flexirule/ruleflow/process/batch/`

**Operations**:

- `process_batch` - Process documents in batch
- `schedule_batch` - Schedule batch processing

---

## 8. Best Practices

### 8.1 Operation Design

1. **Single Responsibility**: Each operation should do one thing
2. **Clear Output Schema**: Define and document return structure
3. **Error Handling**: Return error info in result, don't throw unless critical
4. **Idempotency**: Operations should be safe to retry

### 8.2 Configuration Schema

1. **Use Standard Fieldtypes**: All config fields must be valid Frappe fieldtypes
2. **Provide Defaults**: Every field should have a sensible default
3. **Document Dependencies**: Use `depends_on` for conditional fields

### 8.3 Transactional Operations

Operations that modify data should be `transactional: 1` to support rollback:

```python
{
    "func_name": "update_totals",
    "label": "Update Totals",
    "writes_to": "Document",
    "transactional": 1
}
```

### 8.4 Context Variables

Use `reads_vars` and `writes_vars` to document data dependencies:

```json
{
	"func_name": "calculate_commission",
	"reads_vars": ["sales_amount", "commission_rate"],
	"writes_vars": ["commission", "total_payable"]
}
```

---

## 9. Creating a Custom Process

### 9.1 Step 1: Create Process Adapter

```python
# my_app/my_app/process/my_process/my_process.py

def execute(context, func=None, config=None):
    operations = {
        "validate": validate_data,
        "transform": transform_data,
    }

    if func and func in operations:
        return operations[func](context, config)

    raise ValueError(f"Unknown operation: {func}")


def validate_data(context, config):
    doc = context.get("doc")
    rules = config.get("validation_rules", [])

    errors = []
    for rule in rules:
        if not _check_rule(doc, rule):
            errors.append(rule.get("message"))

    return {
        "is_valid": len(errors) == 0,
        "errors": errors
    }


def transform_data(context, config):
    doc = context.get("doc")

    # Transform logic
    transformed = {...}

    return {"result": transformed}
```

### 9.2 Step 2: Create Process JSON

```json
{
	"process_name": "My Process",
	"module": "My App",
	"description": "Custom data processing",
	"operations": [
		{
			"func_name": "validate",
			"label": "Validate Data",
			"enabled": 1,
			"writes_to": "None",
			"output_schema": {
				"type": "object",
				"properties": {
					"is_valid": { "type": "boolean" },
					"errors": { "type": "array", "items": { "type": "string" } }
				},
				"required": ["is_valid"]
			}
		},
		{
			"func_name": "transform",
			"label": "Transform Data",
			"enabled": 1,
			"writes_to": "Context"
		}
	]
}
```

### 9.3 Step 3: Run Migration

```bash
bench --site [site] migrate
```

### 9.4 Step 4: Create Rule

In the Rule Builder:

1. Add a `Process` action
2. Select your Process and Operation
3. Configure the operation using the schema UI

---

_Document Version: 1.0_
_Generated from FlexiRule v1.0 source analysis_
