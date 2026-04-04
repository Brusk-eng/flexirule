# The Condition System

To guarantee extremely performant runtime speeds without sacrificing visual builder capacities, FlexiRule divides the Condition concept into two formats.

## Display Schema: `condition_json`
- An abstract Syntax Tree (AST) representing the user decisions visually.
- Managed by `public/js/flexirule/rule_builder/components/condition_builder/ConditionBuilder.vue`
- Uses `logical_operator` nodes (`and/or`), scalar value `left/right` operators (`==`, `in`, `contains`), and array logic (`collection` scopes looking at child tables).

## Runtime Form: `compiled_expression`
- A raw, Python-executable string evaluated using `frappe.safe_eval()`. 
- Generated internally from `condition_json` exactly when a user hits "Save" via the `ConditionCompiler`.
- Uses `flexirule.ruleflow.utils.field_resolver.FieldResolver` safely attached to the `frappe.safe_eval` global space to lookup cross-document contexts.
- Runtime Engine directly skips interpreting `condition_json` and runs `compiled_expression`. If `compiled_expression` is empty, evaluation halts and fails the node.
