# Salesforce Flow to FlexiRule Reference: Data Handling and Variables

## Variables in Salesforce Flow

Salesforce Flow heavily utilizes user-defined variables to pass information back and forth between elements.

### Variable Types
1. **Record Variables (`$Record`, `$Record__Prior`):** Automatically injected in Record-Triggered flows. Represent the current and old state of the record.
2. **Primitive Variables:** Text, Number, Boolean, Date.
3. **Record Collections:** Arrays of multiple records.
4. **Formulas:** Dynamically calculated values based on logic and other variables at runtime.

## FlexiRule Approach

### Context Engine
In FlexiRule (and Frappe generally), execution revolves around a `context` dictionary.
- `$Record` maps exactly to `doc` in Frappe hooks.
- `$Record__Prior` maps to `doc.get_doc_before_save()` caching behavior.
- FlexiRule Rule Engine typically injects standard variables into the evaluation sandbox: `frappe`, `doc`, `nowdate`, etc.

### Formulating Expressions
Salesforce provides a dedicated Formula Builder. FlexiRule relies heavily on Python evaluation contexts (`frappe.safe_eval`). When building the Rule Builder, any variable parameter should theoretically support either Static Values, Variable Lookups, or Python Expressions (Formulas).

## Suggested Alignment
In the Visual Canvas, when a user sets an Action Node property, they should specify dynamic values using standard Frappe templating limits, e.g., `{{ doc.name }}` or explicit `Evaluate` flags.
