# Process Adapter Standards

This document defines the standard structure and requirements for FlexiRule Process Adapters. Following these standards ensures compatibility with the Rule Builder's `ConfigurableAction` runtime.

## File Location
Process adapters should be placed in `apps/flexirule/flexirule/ruleflow/process/[process_name]/[process_name].js`.

## Example Structure

```javascript
frappe.provide('flexirule.processes');

flexirule.processes["ProcessName"] = {
    meta: {
        version: '1.0',
        title: __('Process Title')
    },

    /**
     * Required: Returns the configuration schema for a specific operation.
     */
    get_schema(operation_name, context) {
        const operation = this.get_operation(operation_name);
        if (!operation) return null;

        return {
            title: operation.label || operation_name,
            size: 'extra-large', // Options: 'small', 'medium', 'large'
            fields: typeof operation.get_config_fields === 'function'
                ? operation.get_config_fields(context)
                : []
        };
    },

    /**
     * Optional: Returns the output fields that this operation contributes to the rules context.
     */
    get_output_schema(operation_name, config, context) {
        // ... return list of {label, value, type}
        return [];
    },

    /**
     * Optional: Logic to run when the configuration dialog is opened.
     */
    onload(operation_name, context) {
        // ... initialization
    },

    operations: [
        {
            func_name: "operation_method",
            label: __("Operation Label"),
            description: __("Brief description of what this does"),
            icon: "edit",
            color: "#3b82f6",
            
            /**
             * Returns the raw Frappe field definitions for the UI.
             */
            get_config_fields: (ctx) => {
                return [
                    {
                        fieldname: "source_field",
                        label: __("Source Field"),
                        fieldtype: "DocField", // Standard: Maps to Autocomplete with rich options
                        options: ctx.document_type,
                        reqd: 1
                    },
                    // ... other fields
                ];
            }
        }
    ],

    // Utility Helpers
    get_operation(name) {
        return this.operations.find(op => op.func_name === name);
    }
};
```

## Best Practices

1.  **Use `DocField` for Field Selection**: Always use `fieldtype: "DocField"` for fields that select from the document. The runtime automatically resolves these to high-performance, cached `Autocomplete` fields with system field support.
2.  **Use `MultiDocField` for Multiple Fields**: Similarly, use `MultiDocField` for multiple field selection; it maps to `MultiSelectList`.
3.  **Strict Context**: Never mutate the global state. All updates should happen via the `ctx` (context) provided to hooks like `onchange`.
4.  **Async Friendly**: Hooks like `get_options` or `onchange` should be `async` if they perform metadata lookups.
5.  **Standard Labels**: Use `__()` for all user-facing labels to support translation.
6.  **Rich Fields**: Prefer `options: ctx.document_type` for field selectors to ensure they are scoped correctly.

## Common Utilities
The runtime provide several utilities at `flexirule.utils`:
- `flexirule.utils.get_doctype_fields(doctype)`: Returns cached fields for any DocType.
- `flexirule.utils.get_combined_fields(doctype, variables)`: Combines DocType fields with action variables.
