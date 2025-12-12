# Bolton Rule Engine - Example JSON Schemas

## 1. Validation Rule Example

### Rule: Customer Validation

```json
{
  "rule_name": "Customer Email Required",
  "rule_type": "Validation",
  "is_active": 1,
  "priority": 100,
  "document_type": "Customer",
  "trigger_event": "validate",
  "conditions_json": "[{\"left\": {\"type\": \"field\", \"value\": \"customer_type\"}, \"operator\": \"==\", \"right\": {\"type\": \"literal\", \"value\": \"Company\"}}]",
  "actions_json": "[{\"type\": \"set_field\", \"field\": \"email_required\", \"value\": {\"type\": \"literal\", \"value\": 1}}]"
}
```

### Detailed Conditions Example

```json
[
  {
    "left": {"type": "field", "value": "total_qty"},
    "operator": ">",
    "right": {"type": "literal", "value": 100},
    "logical_operator": "AND"
  },
  {
    "left": {"type": "field", "value": "discount_percentage"},
    "operator": ">",
    "right": {"type": "literal", "value": 10},
    "logical_operator": "AND"
  },
  {
    "left": {"type": "field", "value": "approval_status"},
    "operator": "!=",
    "right": {"type": "literal", "value": "Approved"}
  }
]
```

### Detailed Actions Example

```json
[
  {
    "type": "raise_error",
    "message": "Discounts over 10% for orders > 100 items require approval"
  },
  {
    "type": "log_issue",
    "severity": "High",
    "message": "High value order with unapproved discount"
  }
]
```

---

## 2. Transformation Rule Example

### Rule: Auto-calculate Totals

```json
{
  "rule_name": "Calculate Order Totals",
  "rule_type": "Transformation",
  "is_active": 1,
  "priority": 90,
  "document_type": "Sales Order",
  "trigger_event": "before_save",
  "conditions_json": "[]",
  "actions_json": "[{\"type\": \"call_method\", \"method\": \"flexirule.ruleflow.utils.calculations.calculate_totals\", \"args\": {}}]"
}
```

---

## 3. Deduplication Rule Example

### Rule: Duplicate Customer Detection

```json
{
  "rule_name": "Detect Duplicate Customers",
  "rule_type": "Deduplication",
  "is_active": 1,
  "priority": 100,
  "document_type": "Customer",
  "trigger_event": "before_insert",
  "conditions_json": "[]",
  "actions_json": "[{\"type\": \"call_method\", \"method\": \"flexirule.ruleflow.core.scoring.check_duplicates\", \"args\": {\"threshold\": 85}}]",
  "options_json": "{\"match_threshold\": 85, \"blocking_fields\": [\"customer_name\", \"country\"], \"scoring_fields\": [{\"field\": \"customer_name\", \"weight\": 0.6, \"scorer\": \"fuzzy\"}, {\"field\": \"email_id\", \"weight\": 0.4, \"scorer\": \"exact\"}]}"
}
```

### Options JSON for Deduplication

```json
{
  "match_threshold": 85,
  "blocking_fields": ["customer_name", "country"],
  "scoring_fields": [
    {
      "field": "customer_name",
      "weight": 0.6,
      "scorer": "fuzzy"
    },
    {
      "field": "email_id",
      "weight": 0.3,
      "scorer": "exact"
    },
    {
      "field": "phone",
      "weight": 0.1,
      "scorer": "fuzzy"
    }
  ]
}
```

---

## 4. Enrichment Rule Example

### Rule: Fetch Tax ID

```json
{
  "rule_name": "Enrich Customer Tax ID",
  "rule_type": "Enrichment",
  "is_active": 1,
  "priority": 80,
  "document_type": "Customer",
  "trigger_event": "after_insert",
  "conditions_json": "[{\"left\": {\"type\": \"field\", \"value\": \"tax_id\"}, \"operator\": \"is_not_set\"}]",
  "actions_json": "[{\"type\": \"call_method\", \"method\": \"flexirule.ruleflow.utils.enrichment.fetch_tax_id\", \"args\": {}}]"
}
```

---

## 5. Nested Condition Groups Example

### Complex Validation with AND/OR Logic

```json
[
  {
    "conditions": [
      {
        "left": {"type": "field", "value": "docstatus"},
        "operator": "==",
        "right": {"type": "literal", "value": 1}
      },
      {
        "left": {"type": "field", "value": "workflow_state"},
        "operator": "==",
        "right": {"type": "literal", "value": "Approved"}
      }
    ],
    "logical_operator": "OR"
  },
  {
    "left": {"type": "field", "value": "grand_total"},
    "operator": "<",
    "right": {"type": "literal", "value": 1000}
  }
]
```

This evaluates as: `(docstatus == 1 AND workflow_state == "Approved") OR grand_total < 1000`

---

## 6. Normalization Profile Example

### Profile: Clean Customer Names

```json
{
  "profile_name": "Customer Name Cleanup",
  "target_doctype": "Customer",
  "is_active": 1,
  "normalize_fields_json": "[{\"fieldname\": \"customer_name\", \"transformations\": [\"trim\", \"lowercase\", \"remove_punctuation\"]}, {\"fieldname\": \"email_id\", \"transformations\": [\"trim\", \"lowercase\"]}]"
}
```

### Normalize Fields JSON

```json
[
  {
    "fieldname": "customer_name",
    "transformations": ["trim", "lowercase", "remove_punctuation"]
  },
  {
    "fieldname": "email_id",
    "transformations": ["trim", "lowercase"]
  },
  {
    "fieldname": "phone",
    "transformations": ["remove_non_numeric", "format_phone"]
  }
]
```

---

## 7. Complete Rule Example with All Features

```json
{
  "rule_name": "Comprehensive Order Validation",
  "rule_type": "Validation",
  "is_active": 1,
  "priority": 100,
  "document_type": "Sales Order",
  "trigger_event": "validate",
  "debug_mode": 1,
  "conditions_json": "[{\"conditions\": [{\"left\": {\"type\": \"field\", \"value\": \"customer_group\"}, \"operator\": \"==\", \"right\": {\"type\": \"literal\", \"value\": \"Corporate\"}}, {\"left\": {\"type\": \"field\", \"value\": \"grand_total\"}, \"operator\": \">\", \"right\": {\"type\": \"literal\", \"value\": 50000}}], \"logical_operator\": \"AND\"}, {\"left\": {\"type\": \"field\", \"value\": \"approval_status\"}, \"operator\": \"!=\", \"right\": {\"type\": \"literal\", \"value\": \"Approved\"}}]",
  "actions_json": "[{\"type\": \"raise_warning\", \"message\": \"High value corporate order requires approval\"}, {\"type\": \"set_field\", \"field\": \"requires_approval\", \"value\": {\"type\": \"literal\", \"value\": 1}}, {\"type\": \"log_issue\", \"severity\": \"Medium\", \"message\": \"Unapproved high-value corporate order\"}]",
  "options_json": "{\"notify_roles\": [\"Sales Manager\", \"Accounts Manager\"]}"
}
```

---

## Usage Examples

### Creating a Rule via API

```python
import frappe

rule = frappe.get_doc({
    "doctype": "Rule",
    "rule_name": "My Custom Rule",
    "rule_type": "Validation",
    "is_active": 1,
    "priority": 100,
    "document_type": "Sales Invoice",
    "trigger_event": "validate",
    "conditions_json": '[{"left": {"type": "field", "value": "outstanding_amount"}, "operator": ">", "right": {"type": "literal", "value": 0}}]',
    "actions_json": '[{"type": "raise_warning", "message": "Invoice has outstanding amount"}]'
})
rule.insert()
```

### Testing a Rule

```python
# Get a document
doc = frappe.get_doc("Customer", "CUST-0001")

# Execute rules manually (normally happens automatically)
from flexirule.ruleflow.core.coordinator import RuleCoordinator
RuleCoordinator.execute_rules(doc, "validate") - 

```
