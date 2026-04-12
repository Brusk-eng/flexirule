# FlexiRule Enterprise Redesign Blueprint

## Scope
This blueprint redesigns FlexiRule to be enterprise-grade (Salesforce Flow style) while staying Frappe-first and config-driven.

Constraints used:
- No production migration constraints.
- Local test site: `insight.test`.
- Backend is single source of truth.
- No hardcoded Rule/Rule Action/Rule Permission fields in builder logic.

---

## 0. Current Baseline (Observed in Code)

### Strengths already present
- Backend validation service exists: `ruleflow/core/validation_service.py`.
- Contract DTO exists and is exposed: `ruleflow/core/contracts.py`, `ruleflow/api.py`.
- Builder already split into domain stores (`useRuleStore`, `useGraphStore`, etc.).
- Fuzzy search service exists and already supports RapidFuzz fallback.
- Lifecycle service exists (`core/lifecycle_service.py`), but not fully normalized with Rule fields.
- Backend default graph initialization exists (`core/graph_service.ensure_default_graph`) and Rule model also initializes defaults.

### Main gaps to close
- Duplicate logic paths: graph/layout/search exist in multiple implementations (`useRuleGraph` vs `useAutoLayout`, UI fuzzy vs backend fuzzy).
- Lifecycle inconsistency: code uses both `status` and `lifecycle_state`.
- Node rendering still partially hardcoded in `App.vue`.
- Dynamic schema support exists but is not the only path yet.
- Contract consumption is mixed between static fallbacks and runtime metadata.

---

## 1. Vue 3 Refactor (Composition API, Reuse, Store Cleanliness)

### Target folder structure
```text
flexirule/public/js/flexirule/rule_builder/
  app/
    AppShell.vue
    CanvasView.vue
    ConfigPanelView.vue
    BuilderToolbar.vue
  components/
    nodes/
      BaseNode.vue
      NodeBadgeRow.vue
      renderers/
        TriggerNodeRenderer.vue
        DecisionNodeRenderer.vue
        ActionNodeRenderer.vue
        EndNodeRenderer.vue
    config/
      DynamicConfigForm.vue
      FieldRendererMap.vue
    lifecycle/
      LifecycleActions.vue
  composables/
    useBuilderBootstrap.js
    useCanvasInteractions.js
    useConnectionPolicy.js
    useNodeFactory.js
    useNodeCatalog.js
    useNodeStatus.js
    useFlowLayout.js
    useLifecycle.js
  stores/
    useBuilderStore.js
    modules/
      rule.js
      graph.js
      catalog.js
      meta.js
      lifecycle.js
      ui.js
      history.js
  services/
    apiClient.js
    contractClient.js
    metadataClient.js
    lifecycleClient.js
    simulationClient.js
  adapters/
    ruleDtoAdapter.js
    graphDtoAdapter.js
```

### Key composables
- `useBuilderBootstrap`: load settings + contracts + metadata + rule payload in one transaction.
- `useNodeFactory`: create node data only from backend node contract.
- `useConnectionPolicy`: validate connect attempts client-side using backend policy DTO.
- `useNodeStatus`: computes `valid/configured/tested/executable` badges.
- `useFlowLayout`: single layout engine (replace both `useRuleGraph` and `useAutoLayout`).
- `useLifecycle`: transition actions and UI lock rules from lifecycle contract.

### Refactor strategy
1. Keep `store.js` as compatibility facade temporarily.
2. Move all feature logic to module stores and composables.
3. Delete duplicate utilities once consumers are switched.
4. Enforce one serialization boundary in adapter layer (`graphDtoAdapter`).

---

## 2. Shared Validation + Testing Layer (JS for Form + Builder)

### New shared package
```text
flexirule/public/js/flexirule/shared/rulekit/
  index.js
  contracts.js
  metadata.js
  graphValidation.js
  lifecycleRules.js
  simulator.js
  testHarness.js
```

### Responsibilities
- `graphValidation.js`: structural checks (entry/end, unreachable nodes, branch completeness, cycle hints).
- `contracts.js`: normalized contract loading from backend DTO with version hash cache.
- `metadata.js`: DocType field/meta fetch + cache helpers.
- `simulator.js`: API wrapper for simulation/preview.
- `testHarness.js`: deterministic rule test runner payload format.

### Example API surface
```js
import { buildRuleKit } from "flexirule/shared/rulekit";

const kit = await buildRuleKit({ frappe, site: "insight.test" });

const result = kit.validateGraph(rulePayload, { mode: "draft" });
const preview = await kit.previewExecution({ ruleName, docname });
const sim = await kit.simulate({ ruleName, docname, dryRun: true });
```

### Consumption model
- Frappe Desk form (`rule.js`) uses same `rulekit` for pre-save validation and lifecycle button availability.
- Vue Rule Builder uses same `rulekit` for canvas checks and testing UX.
- Backend consumes same rules as canonical Python services (`validation_service`, `lifecycle_service`, `engine`).
  - JS is shared for clients.
  - Backend remains canonical enforcer.

---

## 3. Rule Lifecycle Standardization

## Canonical fields
- `Rule.lifecycle_state` is canonical state.
- `Rule.is_active` is derived (`1` only when `lifecycle_state == "Active"`).
- Deprecate direct business use of `status` for lifecycle decisions.

### State machine
- `Draft -> Active` (requires full validation, optionally approval).
- `Draft -> Inactive` (parked draft, not executable).
- `Inactive -> Draft` (resume editing).
- `Active -> Inactive` (deactivate execution).
- `Active -> Archived` (immutable historical).
- `Inactive -> Archived`.
- `Archived -> Draft` (must create new version).

### Version enforcement
- Active rules are immutable.
- Edit behavior from settings:
  - If `allow_editing_active = 1`: allow controlled updates (not recommended).
  - Else: force `amend_rule()` to create next draft version.
- Single open draft per lineage.

### Optional approval workflow
- In `RuleFlow Settings`:
  - `require_approval_for_active` flag.
  - Transition hooks list per state change.
  - Optional approver role map.

### Backend implementation
- `core/lifecycle_service.py`:
  - switch to `lifecycle_state` everywhere.
  - resolve transitions from settings contract, not hardcoded dict.
  - emit transition events for hooks.
- `doctype/rule/rule.py`:
  - normalize/derive `is_active`.
  - reject illegal state mutations outside lifecycle service.

### Frontend behavior rules
- Builder editability controlled by lifecycle contract + permissions.
- Transition buttons fetched from `get_allowed_transitions`.
- Show reasoned lock messages (state + permission + required action).

---

## 4. Backend Alignment (Frappe-First, Single Truth)

### Target backend layers
```text
ruleflow/
  api/
    builder_api.py
    lifecycle_api.py
    test_api.py
    metadata_api.py
  core/
    coordinator.py
    engine.py
    lifecycle_service.py
    validation_service.py
    graph_service.py
    contract_service.py
    node_catalog_service.py
    search_service.py
  repositories/
    rule_repo.py
    settings_repo.py
    execution_log_repo.py
```

### Hook model
- Keep `doc_events` entrypoint in `ruleflow/hooks.py`.
- Keep coordinator as orchestration only.
- Keep engine as the only execution and terminal log writer.

### Frontend-facing API contracts
- `GET flexirule.ruleflow.api.get_builder_bootstrap(rule_name)`
  - returns: rule DTO, contracts DTO, lifecycle contract, node catalog, settings profile, metadata hashes.
- `POST flexirule.ruleflow.api.validate_rule_document(doc, mode)`
- `POST flexirule.ruleflow.api.transition_rule(rule_name, target_state, comment)`
- `POST flexirule.ruleflow.api.search_actions_v2(query, filters, limit)`
- `GET flexirule.ruleflow.api.get_node_config_schema(action_type, operation, process_name)`
- `POST flexirule.ruleflow.api.simulate_rule(...)`
- `POST flexirule.ruleflow.api.get_execution_preview(...)`

---

## 5. Canvas (Vue Flow) Enterprise Enhancements

## 5.1 RuleFlow Settings-driven UI

### Extend `RuleFlow Settings` with child tables
- `Rule Lifecycle State`:
  - `state_key`, `label`, `is_terminal`, `is_editable`, `is_executable`.
- `Rule Lifecycle Transition`:
  - `from_state`, `to_state`, `requires_approval`, `hook_method`, `allowed_roles`.
- `Rule Node UI Profile`:
  - `node_type`, `config_mode` (`Sidebar|Modal|Inline`), `icon`, `color`, `priority`.
- `Rule Builder Behavior`:
  - `action_creation_mode` (`Fuzzy|Manual|Hybrid`), `active_edit_mode` (`Allow|Version`).

### Runtime behavior
- Builder does not hardcode state transitions.
- Node config placement (sidebar/modal/inline) driven by settings profile.

## 5.2 Fuzzy search API (RapidFuzz)

### Endpoint
`POST /api/method/flexirule.ruleflow.api.search_actions_v2`

### Request
```json
{
  "query": "create invoice",
  "filters": {
    "trigger_type": "DocType Event",
    "trigger_event": "Before Save",
    "target_doctype": "Sales Invoice"
  },
  "limit": 20
}
```

### Response
```json
{
  "items": [
    {
      "id": "process:erpnext_billing:create_invoice",
      "kind": "process_operation",
      "action_type": "Process",
      "process_name": "ERPNext Billing",
      "operation": "create_invoice",
      "label": "Create Invoice",
      "description": "Create invoice from source doc",
      "category": "Data Operations",
      "score": 92.4,
      "icon": "fa fa-file-text-o",
      "color": "#0f766e"
    }
  ],
  "meta": {
    "query_time_ms": 11,
    "index_version": "2026-04-11T00:00:00Z"
  }
}
```

## 5.3 Node system (fully extensible)

### Node schema contract (backend -> frontend)
```json
{
  "node_type": "Condition",
  "category": "Logic",
  "label": "Decision",
  "icon": "fa fa-code-fork",
  "color": "#2563eb",
  "handles": {
    "outgoing": ["true", "false"],
    "incoming": ["default"]
  },
  "required_fields": ["condition_json"],
  "badges": ["valid", "configured", "tested", "executable"],
  "ui": {
    "config_mode": "Sidebar",
    "schema_provider": "get_node_config_schema"
  }
}
```

### Categories
- Core: Trigger, Condition, Action, End.
- Data: Query, Create, Update, Delete, Upsert.
- Logic: Assignment, Loop, Break, Continue, Wait.
- Integration: API Call, Webhook, Background Job, Script (sandboxed).
- Modularity: SubRule, Process.
- Optional: Screen, Approval Step, Notification.

`Action` is category only, never a single concrete node type.

### Node status badges
- `valid`: passes contract + backend validation.
- `configured`: required params present.
- `tested`: successful simulation or node test exists.
- `executable`: reachable and allowed by lifecycle/policy.

## 5.4 Layout algorithm
- Single Dagre/ELK top-down engine in `useFlowLayout`.
- Insert-between flow:
  - user clicks `+` on edge.
  - edge split into `source -> new -> target`.
  - downstream nodes shift by rank.
- Overlap prevention:
  - rank spacing + collision pass.
  - branch balancing for condition/switch nodes.

## 5.5 Styling and edges
- Central theme tokens by node category (CSS vars).
- Use Frappe icons and semantic colors.
- Strong edge contrast, arrowheads, branch labels (`True`, `False`, case labels).
- Hover/selected/focus states with accessibility contrast.

## 5.6 Connection validation
- Validate on connect (client) using policy contract.
- Re-validate on save/activate (backend).
- Reject illegal arcs (terminal outgoing, invalid branch handles, cross-state restrictions).

## 5.7 Dynamic configuration
- All forms generated from `get_node_config_schema`.
- No field list hardcoding in node components.
- Action/operation-specific policy merged server-side and shipped as schema.

---

## 6. Dynamic Alignment with Frappe Metadata (No Hardcoding)

### Metadata service layer
- Use APIs:
  - `frappe.desk.form.load.getdoctype` / `frappe.get_meta` (backend mediated).
  - `flexirule.ruleflow.api.get_node_config_schema`.
  - `flexirule.ruleflow.api.get_doctype_fields`.
- Client cache key:
  - `doctype + modified + contract_version_hash`.

### Dynamic form generator design
- Step 1: load Rule/Rule Action/Rule Permission meta.
- Step 2: apply contract overrides (`reqd`, `hidden`, operation policies).
- Step 3: evaluate `depends_on` with current model.
- Step 4: render via field renderer map.

No builder component may assume specific fieldnames as mandatory constants beyond metadata/contract output.

---

## 7. Default Rule Initialization

### Backend (canonical)
- Keep `ensure_default_graph(rule_doc)` as canonical initializer:
  - create Trigger root node.
  - create End node.
  - auto-connect root -> end.
- Call on:
  - new Rule creation.
  - explicit initialize API endpoint.
  - save validation guard when graph empty.

### Frontend
- On load, if backend says `initialized = true`, render as-is.
- No manual setup wizard for first two nodes.

---

## 8. Suggested Implementation Order (Fast, Safe, Incremental)

1. Normalize lifecycle (`lifecycle_state` canonical) + API contract cleanup.
2. Introduce `get_builder_bootstrap` API and shared `rulekit` package.
3. Remove duplicated layout/search implementations, switch to single services.
4. Migrate node rendering to backend-driven node catalog + schema.
5. Extend RuleFlow Settings with lifecycle + UI behavior child tables.
6. Add enterprise UX polish (badges, edge labels, `+` insertion, branch spacing).
7. Add full integration tests (save, activate, simulate, preview) on `insight.test`.

---

## 9. Test Matrix (insight.test)

Use:
- `bench --site insight.test run-tests --app flexirule`
- targeted tests for lifecycle, graph validation, and APIs.

Must-pass scenarios:
- create rule -> auto Trigger/End exists.
- draft save with partial config (allowed).
- activate with invalid graph (blocked with structured errors).
- active edit behavior respects settings (`allow_editing_active`).
- fuzzy search respects trigger filters.
- dynamic schema rendering works without hardcoded Rule Action fields.
- simulate/preview return consistent path and node badge updates.

