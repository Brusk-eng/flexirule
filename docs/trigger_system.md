# The Trigger System

FlexiRule can be sparked by three primary mechanisms: DocType Events, Schedulers, and Callables.

## 1. DocType Event
Attached to core Frappe Database hooks natively (triggered by `doc_events`).
Supported hooks:
- `Before Naming`, `Before Insert`, `Before Save`, `Validate`, `Before Submit`
- `After Insert`, `After Save`, `On Submit`
- `Before Cancel`, `On Cancel`, `On Trash`, `On Update After Submit`
- `Before Rename`, `After Rename`, `Before Print`

**Safety constraints:** Doc Modification is blocked outright in 'After' hooks. The `Rule.validate_trigger_alignment()` checks for `Set Value` nodes and Process `writes_to == "Document"` metadata.

## 2. Scheduler Event
TBD. Designed to be fired from Frappe background jobs periodically. Cannot mutate active context documents synchronously since they initiate their own scope.

## 3. Callable Event
Also known as Sub-Rules.
- These rules cannot listen to standard hooks.
- Required to have `Priority = 0`.
- Selected by checking `exposed_as_subrule`.
- Trigger conditions attached acts as an additional entry-guard against incompatible payloads before executing.
