# Salesforce Flow to FlexiRule Reference: Decision and Loop Logic

## 1. Decision Nodes (Branching)

### Concept
A Salesforce Decision element evaluates multiple condition groups. By default, it processes outcomes sequentially (top-down) and executes the branch for the first Outcome that evaluates to `true`. If no criteria are met, it falls back to a "Default Outcome".

### FlexiRule Mapping
- **Condition Node:** Acts as an `If/Else` block determining logic branching.
- **Switch Node:** Should perform identical logic to SF Decision Elements. It evaluates conditions and routes execution down a specific Edge on the canvas.
- **Frontend Recommendation:** The Vue Builder must visibly distinguish output paths from Condition nodes. There must always be a logical guarantee of execution path (i.e. default edges).

## 2. Loop Nodes (Iteration)

### Concept
A Salesforce Loop element takes a Variable Collection and iterates through items. For each item, it executes "For Each" actions. After all items are iterated, it traverses the "After Last" branch.

### FlexiRule Mapping
- **Loop Node:** Should receive a string indicating the List property inside the runtime Context.
- The Engine sets the current iteration item in the context explicitly (`context['item'] = list_object`).
- The graph edges out of a Loop node must explicitly delineate `[Loop Iteration Path]` vs `[Loop Completed Path]`. 
- **Recommendation:** Avoid deeply nested loops without tight governance controls to avoid recursive explosions inside Frappe server limits.
