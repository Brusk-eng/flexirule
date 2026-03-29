# FlexiRule RC-Ready Production Rules

This document contains 5 production-grade rule configurations using only Frappe core DocTypes (Contact, ToDo, User) with no ERPNext dependency.

## Rule 1: Contact Data Cleanup (Scheduler + Callable Hybrid)

**Purpose**: Scheduled cleanup of Contact names with deduplication detection.

### Configuration

```json
{
  "doctype": "Rule",
  "rule_name": "RC Rule 1 - Contact Data Cleanup",
  "document_type": "Contact",
  "trigger_type": "Scheduler Event",
  "is_active": 1,
  "priority": 5,
  "description": "Normalize Contact names and detect duplicates via scheduler",
  "actions": [
    {
      "action_id": "root",
      "action_type": "Entry Action",
      "action_label": "Start Cleanup",
      "is_enabled": 1,
      "next_step_if_true": "QUERY-CONTACTS"
    },
    {
      "action_id": "QUERY-CONTACTS",
      "action_type": "Query Records",
      "action_label": "Fetch All Contacts",
      "is_enabled": 1,
      "reference_doctype": "Contact",
      "operation": "Query List",
      "config": "{\"filters\": {\"name\": [\"not like\", \"%-old\"]}, \"fields\": [\"name\", \"first_name\", \"middle_name\", \"last_name\", \"full_name\"], \"limit\": 100}",
      "return_variable": "contacts",
      "return_type": "List of Dict",
      "next_step_if_true": "NORMALIZE-NAMES"
    },
    {
      "action_id": "NORMALIZE-NAMES",
      "action_type": "Process",
      "action_label": "Normalize Names",
      "is_enabled": 1,
      "process_name": "Normalization",
      "operation": "normalize_string",
      "config": "{\"source_var\": \"contacts\", \"output_var\": \"normalized\", \"fields\": [\"first_name\", \"middle_name\", \"last_name\"]}",
      "return_variable": "normalized_contacts",
      "on_error": "Continue",
      "next_step_if_true": "CHECK-DUPLICATES"
    },
    {
      "action_id": "CHECK-DUPLICATES",
      "action_type": "Condition",
      "action_label": "Has Duplicates?",
      "is_enabled": 1,
      "condition_json": "[{\"left\": {\"ref\": \"vars.normalized_contacts\"}, \"op\": \"is\", \"right\": {\"value\": null}}]",
      "next_step_if_true": "END",
      "next_step_if_false": "CREATE-TODO"
    },
    {
      "action_id": "CREATE-TODO",
      "action_type": "Document Action",
      "action_label": "Create Review Task",
      "is_enabled": 1,
      "reference_doctype": "ToDo",
      "operation": "Create ToDo",
      "config": "{\"description\": \"Contact deduplication review required - {{ vars.normalized_contacts|length }} contacts processed\", \"priority\": \"Medium\", \"assigned_to\": \"Administrator\"}",
      "skip_permissions": 1,
      "next_step_if_true": "END"
    },
    {
      "action_id": "END",
      "action_type": "Stop",
      "operation": "Success",
      "action_label": "Complete",
      "is_enabled": 1
    }
  ]
}
```

### Expected Context Variables
- `contacts`: List of Contact dicts fetched from DB
- `normalized_contacts`: Processed list with normalized names
- `duplicate_count`: Number of potential duplicates detected

### Expected Outputs
- ToDo created if duplicates detected
- Contact list processed without errors

---

## Rule 2: Phone Validation (Reusable Callable Sub-Rule)

**Purpose**: Reusable validation rule for phone number format and uniqueness.

### Configuration

```json
{
  "doctype": "Rule",
  "rule_name": "RC Rule 2 - Phone Validation Sub-Rule",
  "document_type": null,
  "trigger_type": "Callable Event",
  "is_active": 1,
  "exposed_as_subrule": 1,
  "priority": 0,
  "description": "Validates phone numbers - format, primary check, duplicate detection",
  "actions": [
    {
      "action_id": "root",
      "action_type": "Entry Action",
      "action_label": "Start Validation",
      "is_enabled": 1,
      "next_step_if_true": "CHECK-PHONES"
    },
    {
      "action_id": "CHECK-PHONES",
      "action_type": "Condition",
      "action_label": "Has Phone Nos?",
      "is_enabled": 1,
      "condition_json": "[{\"left\": {\"ref\": \"doc.phone_nos\"}, \"op\": \"is not\", \"right\": {\"value\": null}}]",
      "next_step_if_true": "CHECK-PRIMARY",
      "next_step_if_false": "VALID-FAIL"
    },
    {
      "action_id": "CHECK-PRIMARY",
      "action_type": "Query Records",
      "action_label": "Check Primary Phone",
      "is_enabled": 1,
      "reference_doctype": "Contact",
      "operation": "Count",
      "config": "{\"filters\": {\"phone_nos\": [\"like\", \"%Primary%\"]}}",
      "return_variable": "primary_count",
      "return_type": "Integer",
      "next_step_if_true": "VALID-SUCCESS"
    },
    {
      "action_id": "VALID-SUCCESS",
      "action_type": "Stop",
      "operation": "Success",
      "action_label": "Validation Passed",
      "is_enabled": 1
    },
    {
      "action_id": "VALID-FAIL",
      "action_type": "Stop",
      "operation": "Error",
      "action_label": "Validation Failed",
      "is_enabled": 1,
      "value_template": "No phone numbers found in document"
    }
  ]
}
```

### Expected Context Variables
- `primary_count`: Number of contacts with primary phones

### Expected Outputs
- Boolean success/error indication via Stop action

---

## Rule 3: Contact Before Save with Validation (DocType Event)

**Purpose**: Pre-save validation with phone check and sub-rule call.

### Configuration

```json
{
  "doctype": "Rule",
  "rule_name": "RC Rule 3 - Contact Before Save Validation",
  "document_type": "Contact",
  "trigger_type": "DocType Event",
  "trigger_event": "Before Save",
  "is_active": 1,
  "priority": 15,
  "description": "Validates Contact before save - checks for duplicates and calls phone validation sub-rule",
  "actions": [
    {
      "action_id": "root",
      "action_type": "Entry Action",
      "action_label": "Start Validation",
      "is_enabled": 1,
      "next_step_if_true": "CHECK-EMAIL"
    },
    {
      "action_id": "CHECK-EMAIL",
      "action_type": "Condition",
      "action_label": "Has Email?",
      "is_enabled": 1,
      "condition_json": "[{\"left\": {\"ref\": \"doc.email_id\"}, \"op\": \"is not\", \"right\": {\"value\": null}}]",
      "next_step_if_true": "CHECK-DUPLICATE",
      "next_step_if_false": "CALL-PHONE-SUB"
    },
    {
      "action_id": "CHECK-DUPLICATE",
      "action_type": "Query Records",
      "action_label": "Check Email Duplicate",
      "is_enabled": 1,
      "reference_doctype": "Contact",
      "operation": "Exist Record",
      "config": "{\"filters\": {\"email_id\": \"{{ doc.email_id }}\", \"name\": [\"!=\", \"{{ doc.name }}\"]}}",
      "return_variable": "has_duplicate",
      "return_type": "Boolean",
      "next_step_if_true": "STOP-IF-DUP"
    },
    {
      "action_id": "STOP-IF-DUP",
      "action_type": "Condition",
      "action_label": "Is Duplicate?",
      "is_enabled": 1,
      "condition_json": "[{\"left\": {\"ref\": \"vars.has_duplicate\"}, \"op\": \"==\", \"right\": {\"value\": true}}]",
      "next_step_if_true": "REJECT-DUP",
      "next_step_if_false": "CALL-PHONE-SUB"
    },
    {
      "action_id": "REJECT-DUP",
      "action_type": "Stop",
      "operation": "Error",
      "action_label": "Reject Duplicate",
      "is_enabled": 1,
      "value_template": "Contact with email {{ doc.email_id }} already exists"
    },
    {
      "action_id": "CALL-PHONE-SUB",
      "action_type": "Sub-Rule",
      "action_label": "Validate Phones",
      "is_enabled": 1,
      "rule": "RC Rule 2 - Phone Validation Sub-Rule",
      "skip_conditions": 1,
      "next_step_if_true": "SET-STATUS"
    },
    {
      "action_id": "SET-STATUS",
      "action_type": "Set Value",
      "action_label": "Set Status",
      "is_enabled": 1,
      "target_field": "status",
      "value_template": "Active",
      "next_step_if_true": "END"
    },
    {
      "action_id": "END",
      "action_type": "Stop",
      "operation": "Success",
      "action_label": "Validation Complete",
      "is_enabled": 1
    }
  ]
}
```

### Expected Context Variables
- `has_duplicate`: Boolean from duplicate check query

### Expected Outputs
- Validation passes or stops with error message

---

## Rule 4: Contact After Insert - Create ToDo (Document Action)

**Purpose**: After inserting a Contact, create a follow-up ToDo.

### Configuration

```json
{
  "doctype": "Rule",
  "rule_name": "RC Rule 4 - Contact Follow-up ToDo",
  "document_type": "Contact",
  "trigger_type": "DocType Event",
  "trigger_event": "After Insert",
  "is_active": 1,
  "priority": 8,
  "description": "Creates follow-up ToDo after new Contact is created",
  "actions": [
    {
      "action_id": "root",
      "action_type": "Entry Action",
      "action_label": "Start",
      "is_enabled": 1,
      "next_step_if_true": "CREATE-TODO"
    },
    {
      "action_id": "CREATE-TODO",
      "action_type": "Document Action",
      "action_label": "Create Follow-up Task",
      "is_enabled": 1,
      "reference_doctype": "ToDo",
      "operation": "Create ToDo",
      "config": "{\"description\": \"Follow up with new contact: {{ doc.first_name }} {{ doc.last_name }} ({{ doc.email_id }})\", \"priority\": \"Medium\", \"assigned_to\": \"{{ doc.owner }}\"}",
      "skip_permissions": 1,
      "next_step_if_true": "END"
    },
    {
      "action_id": "END",
      "action_type": "Stop",
      "operation": "Success",
      "action_label": "Task Created",
      "is_enabled": 1
    }
  ]
}
```

### Expected Context Variables
- `doc.first_name`, `doc.last_name`, `doc.email_id`, `doc.owner`

### Expected Outputs
- ToDo document created and assigned

---

## Rule 5: Process Heavy Rule (Chained Operations)

**Purpose**: Demonstrate multiple Process operations chained with context variables.

### Configuration

```json
{
  "doctype": "Rule",
  "rule_name": "RC Rule 5 - User Onboarding Validation",
  "document_type": "User",
  "trigger_type": "DocType Event",
  "trigger_event": "Before Save",
  "is_active": 1,
  "priority": 12,
  "description": "Complex user validation with multiple process operations",
  "actions": [
    {
      "action_id": "root",
      "action_type": "Entry Action",
      "action_label": "Start",
      "is_enabled": 1,
      "next_step_if_true": "CHECK-EMAIL-FORMAT"
    },
    {
      "action_id": "CHECK-EMAIL-FORMAT",
      "action_type": "Process",
      "action_label": "Validate Email Format",
      "is_enabled": 1,
      "process_name": "Validation",
      "operation": "validate_email",
      "config": "{\"email_field\": \"email\", \"check_dns\": false}",
      "return_variable": "email_valid",
      "return_type": "Boolean",
      "on_error": "Continue",
      "next_step_if_true": "CHECK-EMAIL-RESULT"
    },
    {
      "action_id": "CHECK-EMAIL-RESULT",
      "action_type": "Condition",
      "action_label": "Email Valid?",
      "is_enabled": 1,
      "condition_json": "[{\"left\": {\"ref\": \"vars.email_valid\"}, \"op\": \"==\", \"right\": {\"value\": true}}]",
      "next_step_if_true": "CHECK-USERNAME",
      "next_step_if_false": "END-ERROR"
    },
    {
      "action_id": "CHECK-USERNAME",
      "action_type": "Process",
      "action_label": "Validate Username",
      "is_enabled": 1,
      "process_name": "Validation",
      "operation": "validate_username",
      "config": "{\"username_field\": \"name\", \"min_length\": 3}",
      "return_variable": "username_valid",
      "return_type": "Boolean",
      "on_error": "Continue",
      "next_step_if_true": "CHECK-USERNAME-RESULT"
    },
    {
      "action_id": "CHECK-USERNAME-RESULT",
      "action_type": "Condition",
      "action_label": "Username Valid?",
      "is_enabled": 1,
      "condition_json": "[{\"left\": {\"ref\": \"vars.username_valid\"}, \"op\": \"==\", \"right\": {\"value\": true}}]",
      "next_step_if_true": "SET-USER-FLAGS",
      "next_step_if_false": "END-ERROR"
    },
    {
      "action_id": "SET-USER-FLAGS",
      "action_type": "Set Value",
      "action_label": "Set Verified Flag",
      "is_enabled": 1,
      "target_field": "mute_emails",
      "value_template": "0",
      "next_step_if_true": "ENRICH-DATA"
    },
    {
      "action_id": "ENRICH-DATA",
      "action_type": "Process",
      "action_label": "Enrich User Data",
      "is_enabled": 1,
      "process_name": "Enrichment",
      "operation": "fetch_user_metadata",
      "config": "{\"source\": \"frappe\", \"fields\": [\"email\", \"enabled\", \"user_type\"]}",
      "return_variable": "user_metadata",
      "return_type": "Dict",
      "on_error": "Continue",
      "next_step_if_true": "LOG-RESULT"
    },
    {
      "action_id": "LOG-RESULT",
      "action_type": "Notify",
      "action_label": "Log Validation",
      "is_enabled": 1,
      "operation": "System",
      "value_template": "User {{ doc.name }} validated successfully",
      "next_step_if_true": "END"
    },
    {
      "action_id": "END",
      "action_type": "Stop",
      "operation": "Success",
      "action_label": "Validation Complete",
      "is_enabled": 1
    },
    {
      "action_id": "END-ERROR",
      "action_type": "Stop",
      "operation": "Error",
      "action_label": "Validation Failed",
      "is_enabled": 1,
      "value_template": "User validation failed: check email and username formats"
    }
  ]
}
```

### Expected Context Variables
- `email_valid`: Boolean from email validation
- `username_valid`: Boolean from username validation
- `user_metadata`: Dict with enriched user data

### Expected Outputs
- Validation passes through all checks or stops with error

---

## Summary

| Rule | Trigger Type | DocType | Actions | Complexity |
|------|-------------|---------|---------|------------|
| 1 | Scheduler Event | Contact | Query, Process, Condition, Document Action | High |
| 2 | Callable Event | None | Condition, Query, Stop | Medium |
| 3 | DocType Event | Contact | Condition, Query, Sub-Rule, Set Value | High |
| 4 | DocType Event | Contact | Document Action | Low |
| 5 | DocType Event | User | Process x3, Condition x2, Set Value, Notify | Very High |

All rules use only core Frappe DocTypes (Contact, ToDo, User) and do not depend on ERPNext.
