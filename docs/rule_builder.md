# Rule Builder (Vue 3 Frontend)

Because FlexiRule offers 10+ distinct action nodes with deep variables, rendering static JS dialogues was inappropriate. FlexiRule features an organic interface driven dynamically by Backend Schemas.

## Core Flow Builder
`public/js/flexirule/rule_builder/App.vue` leverages `@vue-flow/core`. 
Dropping a node dispatches a `ProcessNode`, `ConditionNode`, or `ActionSelectorNode`. The true structure for saving is an array mapped directly into the Frappe Child Table (`Rule Action`).

## Dynamic `ControlFactory`
Editing a node opens `RuleConfigModal.vue`. The specific UI inputs (Dropdowns, Text Areas, Fields Selectors) are completely auto-generated inside `SchemaRenderer.vue`.
If selecting the 'Set Value' action, the UI knows exactly what inputs to build. Process Actions fetch their exact inputs directly from the assigned Process Operation record locally cached.

## Rule Data Integrity
`store.js` manages Undo/Redo queues, Dirty checking, and handles propagating updates up towards the Frappe Document layer. Vue acts purely as a presentation proxy.
