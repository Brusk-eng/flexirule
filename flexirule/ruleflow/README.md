# FlexiRule (beta 2)

A visual rule builder and execution engine for Frappe/ERPNext.

## Features

-   **Visual Rule Builder** - Drag-and-drop interface for building rules
-   **Processes** - Extensible file-backed processes and operations
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

## Process Architecture

FlexiRule uses file-backed **Processes** which contain multiple **Operations**.

### Standard Processes

-   `Normalization` - Clean and standardize field data
-   `Validation` - Complex multi-field validation
-   `Enrichment` - Auto-populate fields from multiple sources
-   `Deduplication` - Detect and prevent duplicates using various algorithms

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

### Custom Processes

1. Create a new `Process` document in Frappe.
2. If `is_standard` is checked, boilerplate files (`.py` and `.js`) will be created in your app.
3. Add `Process Operation` rows to define your methods.
4. Implement the logic in the generated controller.

## License

MIT
