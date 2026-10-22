# Implementation Plan: Generic TreeBuilder Readable View and Leaf Editing

## Status and intent

**Status:** Plan only. Do not implement this file's plan as part of the planning change itself.

**Goal:** Extend Generic TreeBuilder so a consumer can render each leaf as either a readable summary or its existing form, with double-click and an explicit accessible action to switch between them. Preserve a form-only mode for consumers that need the current always-editable layout. Use Query Filter as the first concrete consumer so nested filters can read like ordinary language, while keeping the generic layer independent of Frappe, Query Records, Condition semantics, and value-resolver details.

This is a presentation and interaction enhancement. It must not change the canonical tree payload, validation contract, filter serialization, or rule execution behavior.

## 1. Verified current architecture

Relevant source files on the current develop branch:

- [TreeBuilder.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/TreeBuilder.vue) owns the root UI, exposes the generic read-only option, and currently forwards a leaf slot.
- [TreeBuilderNode.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/TreeBuilderNode.vue) recursively renders groups, collections, and leaves and forwards the existing leaf slot through nested nodes.
- [TreeBuilderLeaf.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/TreeBuilderLeaf.vue) currently renders one default leaf slot plus the generic remove action. It has no summary/editor switching behavior.
- [useTreeBuilder.js](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/useTreeBuilder.js) already keeps UI state outside the tree model and defines an editingNodeId ref plus setEditing(). These are not currently wired into the leaf presentation. Reuse this existing state rather than adding edit flags to persisted nodes.
- [TreeBuilder README](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/README.md) establishes the intended boundary: TreeBuilder owns hierarchy and mutations; the consumer owns leaf semantics.
- [GenericGrid.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/controls/GenericGrid.vue) already uses separate row-summary and row slots, double-click switching, and a row action event. It is a useful UX reference.
- [generic_grid_model.mjs](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/controls/generic_grid_model.mjs) centralizes the grid's summary toggle decision. However, GenericGrid currently uses a row property (default isEditing) for its edit state. **Do not copy that storage pattern into TreeBuilder:** an edit flag on a tree node risks leaking UI state into the canonical serialized rule configuration.
- [QueryFilterTree.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/rule_config/query_filters/QueryFilterTree.vue) is currently the first clear TreeBuilder consumer. It supplies FilterLeaf as the existing leaf slot and delegates model changes to TreeBuilder.
- [FilterLeaf.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/rule_config/query_filters/FilterLeaf.vue) owns field, operator, value/resolver editing, and validation. It already resolves field metadata and uses the existing control/value architecture; keep these responsibilities in the filter domain layer.
- [RuleFlow Settings](https://github.com/Sendipad/flexirule/blob/develop/flexirule/ruleflow/doctype/ruleflow_settings/ruleflow_settings.json) is a single site-wide DocType currently restricted to System Manager for writes. It is not the correct persistence store for a preference that each user can independently change.

## 2. User-visible behavior and terminology

Keep three concepts separate:

1. **Structural/read-only lock** (existing readOnly API): controls whether structural operations and domain editing are permitted. Do not redefine this prop to mean summary presentation.
2. **Presentation mode:** controls whether leaves initially show the form or a readable summary.
3. **Per-leaf edit state:** temporary UI state for the leaf currently opened in form mode.

Recommended public presentation values:

- **form:** always render the existing leaf form. This remains the Generic TreeBuilder default for backward compatibility and is the form-only view.
- **summary:** render a consumer-provided readable summary by default. Double-clicking the summary or activating an explicit Edit action opens the existing form for that leaf. An explicit Done/return-to-reading action switches back to the summary.

When readOnly is true, structural and domain mutations remain disallowed. In summary mode, do not offer a route into editing. In form mode, preserve existing consumer behavior: render the existing form and let the consumer render its controls disabled/read-only as it does today. This avoids making the current readOnly prop silently change meaning.

If a consumer selects summary but does not supply a summary slot, safely fall back to the existing form slot. Do not render a blank leaf or require every current consumer to migrate at once.

## 3. Recommended component contract

### Generic core

Add a TreeBuilder prop such as presentationMode, constrained to form or summary and defaulting to form. Keep this API generic; do not add filter-specific or condition-specific options to the core.

Preserve the existing leaf slot as the form/editor renderer. Add an optional leaf-summary slot for the readable renderer. Both slots receive a consistent, documented context including:

- node, context, index, and parent (existing leaf context);
- editing/effective display state;
- readOnly;
- explicit callbacks to request edit or return to summary, if a consumer needs custom controls.

The generic leaf shell should own the standard mode-switch interaction and action affordance. Consumers provide content, not a separate copy of the generic edit-state machine. The callbacks can still be exposed for consumers that need a custom interaction.

Use the existing editingNodeId / setEditing() API in useTreeBuilder. Keep presentation state outside the canonical tree. The initial implementation should allow at most one leaf to be in form-edit mode at a time, matching the existing single editingNodeId model; entering edit mode for another leaf should switch the active leaf rather than leave an accidental mixed set of editors.

### Slot forwarding

Forward the new summary slot through every recursive TreeBuilderNode path, including children of groups and collections. A root-only implementation is incomplete and would fail for nested filters.

Keep the existing leaf slot name and its slot props stable. Do not force all consumers to adopt the summary slot in the same change.

### Interaction details

- Double-click the summary surface to open the form. Avoid toggling when the event originates from an interactive element such as a link or button inside the summary.
- Provide a visible, keyboard-accessible Edit action; do not make double-click the only route into editing.
- In form mode, provide a clear Done/return-to-reading action when summary presentation is enabled.
- Use translated labels and accessible names/titles for mode actions; preserve keyboard focus sensibly when switching modes.
- Do not automatically close the form on blur. Current form controls update the canonical leaf through their normal update:modelValue path; make the transition explicit so a user does not lose an editing surface while interacting with controls.
- Clear or reconcile editingNodeId if the edited leaf is removed or no longer exists in a replaced tree. Clear stale UI edit state when necessary; never serialize it.
- Keep drag/drop, group operators, node IDs, tree normalization, and structural validation independent of the presentation mode.
- Ensure the presentation prop can react to parent changes. Avoid capturing a one-time primitive value in a composable if runtime changes are expected.

## 4. Query Filter as the first consumer

After the generic contract is in place, add a dedicated summary renderer for Query Filters, for example FilterLeafSummary.vue or a small pure formatter plus a renderer component. Do not put Query Filter knowledge into TreeBuilder.

The summary should communicate the filter in ordinary language, using available metadata and value information. Examples of the intended shape:

- **Status equals Open**
- **Posting Date is on or after 1 October**
- **Amount is between 100 and 500**
- **Customer is one of …**
- A variable/resolver value shown by a user-facing description rather than raw resolver JSON or an opaque configuration object.

These are illustrative examples; use the actual metadata, translations, and formatting available in the component's context.

Implementation guidance:

1. Reuse the field metadata and value display/formatting mechanisms already used by FlexiRule. Before adding a formatter, inspect whether the existing FlexValue/control architecture exposes a suitable display label or formatter; do not invent a parallel resolver-display schema.
2. Reuse field labels obtained by the current navigable-field/metadata code. Resolve dotted/navigated fields accurately and retain enough context for nested Link/Table fields.
3. Reuse the existing operator-label policy where possible. Preserve operator-specific wording such as date comparisons and special operators.
4. Handle Between as two displayed operands, and handle in / not in and multi-value forms without serializing implementation details.
5. For static values, display meaningful formatted values. For variable or resolver-driven values, display a concise human-readable token/description. Never evaluate a resolver only to paint the summary, and never expose private/runtime values just to create the display text.
6. For empty or malformed leaves, show a stable, translated incomplete/invalid state that lets the user open the form. Do not hide invalid configuration behind an empty label.
7. Render text through normal Vue interpolation; do not render user-configured summaries as raw HTML.
8. Keep summaries presentational. Leaf edits must continue to flow through FilterLeaf and TreeBuilder.replaceNode; summary formatting must not mutate or normalize the persisted payload.

The generic TreeBuilder default remains form. Once summaries cover supported cases, configure QueryFilterTree to use summary as its consumer-level default while retaining an override for integrations and tests. This yields the readability improvement for filters without changing every TreeBuilder consumer at once.

## 5. Condition Builder compatibility

Design the generic contract so a future condition leaf can use the same pattern: a domain-specific condition summary slot and the existing condition form/editor slot. The generic core must not parse conditions or format expressions.

The current condition-builder implementation has its own domain model and UI; this task must not silently migrate or rewrite it. Treat moving the existing Condition Builder onto Generic TreeBuilder and adding condition-language summaries as a separate task, following an audit of its canonical model, short-circuit semantics, validation, and save/load contract. That keeps this UX work from inadvertently changing condition compilation or runtime behavior.

## 6. Per-user preference: future persistence path

Keep the component preference injectable/overridable now, but do not embed storage logic inside TreeBuilder. The generic component should receive a resolved presentationMode; a higher layer decides where the preference comes from.

For the future Preferences UI:

1. Inspect current builder preference ownership and any existing FlexiRule user-setting keys before adding another key.
2. Use Frappe v15's native per-user settings mechanism (frappe.model.user_settings.save(doctype, key, value) and frappe.get_user_settings(doctype, key)) for cross-session, per-user preference persistence. Verify the exact load/update flow against the installed framework version during implementation.
3. Store a namespaced key for the preferred TreeBuilder presentation mode, with a validated value (form or summary). Fall back safely when the saved value is missing, invalid, or unavailable to Guest users.
4. Surface the control in the relevant Ruleflow/Rule Builder Preferences UI. If a site-wide administrator default is later required, it may be a global fallback, with a user's own preference taking precedence.
5. Do not add a user preference to the existing RuleFlow Settings singleton as though it were per-user. That DocType is site-wide, and a setting there would change the experience for all users.
6. Do not use localStorage as the long-term source of truth for a setting that should follow a user across browsers/devices. GenericGrid's current local preference pattern is only a UI reference, not the persistence architecture to copy for this feature.

Recommended precedence when the preference layer is added: explicit consumer prop > saved per-user preference > optional site-wide default > generic backward-compatible default (form).

Keep preference persistence as a follow-up implementation slice after the component behavior and summary renderer are stable, unless the project chooses to include the Preferences UI in the same release.

## 7. Suggested implementation slices

### Slice A — Generic summary/form mode

- Add presentationMode and the optional leaf-summary slot while preserving the current leaf slot.
- Wire the UI-only editingNodeId state through TreeBuilder, recursive TreeBuilderNode, and TreeBuilderLeaf.
- Implement double-click, accessible Edit/Done actions, hard-read-only gating, missing-summary fallback, and edit-state cleanup.
- Document the API in the TreeBuilder README.
- Add pure tests for mode resolution and edit-state cleanup where the project's current unit-test structure supports them.

### Slice B — Query Filter summaries

- Audit existing FlexValue/control display helpers and field metadata APIs.
- Implement the Query Filter summary renderer and tests for field/operator/value combinations.
- Integrate both slots in QueryFilterTree without changing its model ownership, replaceNode update flow, validation, or serializer.
- Make summary mode the QueryFilterTree-level default only when supported summaries and a usable fallback are in place.

### Slice C — Per-user preference (future)

- Add the preference control to the appropriate Preferences UI.
- Read/write through Frappe's user-scoped settings APIs using a namespaced key.
- Test missing, invalid, saved, and cross-session preference states, including Guest behavior.
- Keep the preference resolver outside Generic TreeBuilder so other consumers can supply another default.

### Slice D — Condition summaries (future, separate scope)

- Audit the current Condition Builder's canonical model and rendering flow.
- Adopt the generic slot/interaction contract only after proving a lossless mapping and preserving validation, serialization, and short-circuit semantics.
- Add readable summaries for the supported condition operators and operands.

## 8. Test plan

### Generic TreeBuilder unit/component tests

- Default form mode renders the existing leaf slot without changing current consumer behavior.
- Summary mode renders leaf-summary by default and returns to the form for the correct node when double-clicked.
- Explicit Edit/Done actions work by keyboard and expose correct accessible labels.
- Double-click on an interactive descendant of the summary does not accidentally toggle editing.
- Summary mode with no summary slot falls back to the existing form.
- Hard readOnly blocks edit transitions and structural operations; current form-only read-only behavior stays compatible.
- Editing one node switches away from the previously edited node as documented.
- Removing the edited leaf or replacing the tree so the node no longer exists clears stale edit state.
- The mode and edit state do not appear in getTree(), emitted update:modelValue, serialized filters, or persisted Rule Action config.
- The summary slot is correctly passed through nested groups and collections.
- Changing presentationMode at runtime updates rendering without requiring a full page reload.

### Query Filter summary tests

Cover at least: missing field/operator/value, normal text/number values, date operators, Between, in / not in, special Is values, nested field paths, static arrays, and variable/resolver-driven values. Assert human-readable output and absence of raw config dumps.

### Regression checks

- Run existing TreeBuilder mutation/validation and drag-model tests.
- Run existing filter operator and serializer tests.
- Verify loading, editing, validating, and saving filters produces the same canonical persisted payload as before.
- Run the frontend build/lint and the targeted UI tests available in the configured Frappe v15 bench.
- If Cypress coverage is added, keep it in its own PR unless that is explicitly in scope; do not make a new Cypress setup a prerequisite for accepting the component/API change.

## 9. Acceptance criteria

1. Existing consumers continue to render the form by default with no required slot migration.
2. TreeBuilder offers an opt-in summary presentation and a form-only presentation.
3. A summary leaf can switch to form by double-click and by an accessible explicit action, and can return to summary intentionally.
4. TreeBuilder owns generic presentation state; leaf consumers own domain summary text and form contents.
5. UI state remains outside the canonical serializable tree.
6. readOnly retains its current security/interaction meaning and is not overloaded as a display-mode flag.
7. The new summary slot works at arbitrary supported nesting depth.
8. Query Filter summaries improve readability without changing filter evaluation, values, validation, or serialization.
9. The generic TreeBuilder knows nothing about Frappe DocTypes, filter operators, conditions, or resolver internals.
10. Per-user persistence is kept out of the generic component and, when implemented, uses Frappe's native user-scoped settings API rather than the global RuleFlow Settings singleton.
11. The Condition Builder is prepared to reuse the contract later, but its model/compiler/runtime path is not silently changed by this task.
12. Tests verify the observable contracts above and existing tree/filter regressions remain green.

## 10. Source references

- FlexiRule TreeBuilder API and composition: [TreeBuilder.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/TreeBuilder.vue), [TreeBuilderNode.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/TreeBuilderNode.vue), [TreeBuilderLeaf.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/TreeBuilderLeaf.vue), [useTreeBuilder.js](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/useTreeBuilder.js), [TreeBuilder README](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/tree_builder/README.md).
- Grid interaction reference: [GenericGrid.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/controls/GenericGrid.vue) and [generic_grid_model.mjs](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/controls/generic_grid_model.mjs).
- First consumer: [QueryFilterTree.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/rule_config/query_filters/QueryFilterTree.vue), [FilterLeaf.vue](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/rule_config/query_filters/FilterLeaf.vue), and [query_filter_serializer.js](https://github.com/Sendipad/flexirule/blob/develop/flexirule/public/js/flexirule/rule_builder/components/rule_config/query_filters/query_filter_serializer.js).
- Current global settings: [RuleFlow Settings DocType](https://github.com/Sendipad/flexirule/blob/develop/flexirule/ruleflow/doctype/ruleflow_settings/ruleflow_settings.json).
- Framework user preferences: [Frappe v15 user_settings.js](https://github.com/frappe/frappe/blob/version-15/frappe/public/js/frappe/model/user_settings.js) and [Frappe v15 user_settings.py](https://github.com/frappe/frappe/blob/version-15/frappe/model/utils/user_settings.py).
