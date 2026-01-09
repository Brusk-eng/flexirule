# Bolton Rule Engine

A visual rule builder and execution engine for Frappe/ERPNext.

## Features

-   **Visual Rule Builder** - Drag-and-drop interface for building rules
-   **Process Methods** - Extensible library of validation, enrichment, and notification methods
-   **Graph-Based Execution** - Complex rule flows with conditions and branching
-   **Event Integration** - Trigger rules on document events (save, submit, etc.)

## Quick Start

### 1. Create a Rule

```python
rule = frappe.get_doc({
    "doctype": "Rule",
    "rule_name": "Validate Customer Email",
    "document_type": "Customer",
    "trigger_event": "Validate",
    "is_active": 1
})
rule.insert()
```

### 2. Open Rule Builder

Navigate to `/app/rule-builder/{rule_name}` to open the visual builder.

### 3. Add Actions

Add Process nodes and configure them using the sidebar.

## Process Methods

### Validation

-   `Validate Required Fields` - Check required fields have values
-   `Validate Field Pattern` - Regex validation
-   `Validate Value in Range` - Numeric range validation
-   `Validate Unique Field` - Prevent duplicates

### Enrichment

-   `Set Default Value` - Set field defaults
-   `Calculate Field Value` - Formula-based calculation
-   `Autocomplete from Linked Doc` - Copy from linked documents

### Deduplication

-   `Find Duplicates` - Find exact matches
-   `Find Similar Records` - Fuzzy matching
-   `Prevent Duplicate Save` - Block duplicate saves

### Notification

-   `Send Email Notification` - Email alerts
-   `Create TODO` - Task assignment
-   `Create Notification` - In-app notifications

## API

### Test a Rule

```javascript
frappe.call({
	method: "flexirule.ruleflow.api.test_rule",
	args: { rule_name: "My Rule", doctype: "Customer", docname: "CUST-001" },
});
```

### Clear Cache

```javascript
frappe.call({
	method: "flexirule.ruleflow.api.clear_cache",
	args: { doctype: "Customer" },
});
```

## Extending

### Custom Process Method

1. Create Python function:

```python
def my_custom_method(doc, context, param1, param2, **kwargs):
    # Your logic here
    return result
```

2. Register in Process Method doctype with config_schema.

## License

MIT
