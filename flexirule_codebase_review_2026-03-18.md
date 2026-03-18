# FlexiRule Codebase Review (2026-03-18)

## Scope
Code-only review of FlexiRule backend (Python/Frappe) and frontend (Vue/Frappe Desk JS), with focus on architecture, contracts, security, scaling, and developer/user experience.

## Executive Verdict
FlexiRule has strong ambition and substantial coverage (compiler, coordinator, adapters, tests), but the architecture currently relies on duplicated contracts, runtime dynamic execution, and mixed API shapes that create avoidable fragility.

The core issue: **the frontend-builder contract, process metadata contract, and backend execution contract are not governed from a single typed source of truth**. This is the root of multiple bugs and maintainability pain.

> **Beta context:** The app is not production-ready yet, so the right strategy is to prioritize correctness and contract stability over backward compatibility and feature breadth during this phase.

## Priority Issues

### P0 — Contract drift & shape mismatch between backend API and consumers
- `get_process_operations` returns raw `Process Operation` rows (dicts), while form logic in `rule.js` treats response as list of strings (`ops.join("\n")`). This is a direct mismatch and a likely UI bug in classic form editing.
- Action-type contract exists in both Python and JS as duplicated static maps (`core/contracts.py` and `public/js/.../contracts.js`) with no generation/checksum/version enforcement.

**Impact**
- Broken or inconsistent operation dropdowns depending on entry surface (Rule Form vs Rule Builder).
- Silent divergence risk whenever one side adds/modifies action semantics.

### P0 — Security boundary is inconsistent across whitelisted APIs
- Sensitive APIs call `_require_api_access`, but utility endpoints like `get_doctype_fields`, `get_operator_config`, `get_schema_field_options`, and `get_process_operations` do not.
- `get_script` is whitelisted and exposes process JS source dynamically; `load_process_adapter` evaluates returned script with `new Function(...)`.

**Impact**
- Wider-than-necessary metadata/script exposure.
- Hard-to-reason threat model and larger attack surface in multitenant environments.

### P1 — Runtime code loading/execution pattern is too permissive
- Process adapters are loaded dynamically and executed in browser with `new Function(response.message.script)()`.
- Backend process execution dispatches by dotted path from module + process name.

**Impact**
- Debugging and security hardening are harder.
- Change safety depends on conventions instead of explicit compile-time contracts.

### P1 — Rule orchestration has good structure but heavy per-request potential at scale
- Global `doc_events` hook on `*` for many events is broad; there is early exit via rule map, but entry overhead still exists for every doctypes/event pair.
- Rule map invalidation is coarse (full map clear/rebuild).

**Impact**
- Overhead in high-write sites and queue-heavy installs.
- Cache churn across workers when many rule edits happen.

### P1 — Validation and execution semantics are spread across too many layers
- Rule validity is split between doctype validation, graph validator, contracts, process metadata, runtime handler checks, and builder-side checks.
- Some compiler fallbacks silently emit `''` for invalid refs/scopes, which can mask authoring mistakes instead of failing fast.

**Impact**
- Users can save logically wrong rules that only fail at runtime.
- Harder troubleshooting due to deferred failures.

### P2 — Developer experience is backend-test heavy but frontend-contract light
- Strong Python test surface exists.
- No equivalent contract snapshot tests ensuring Python contracts/process metadata remain in sync with frontend expectations.

**Impact**
- Regressions surface in UI behavior late.

## Frontend ↔ Backend Gaps (Concrete)

1) **Operation options shape mismatch (Form UI)**
- Backend API returns operation objects.
- `rule.js` treats them like strings and does `ops.join("\n")`.

2) **Parallel contract definitions (action types)**
- Python and JS both define action type requirements and flags.
- No CI guard proving they are equal.

3) **Multiple field metadata strategies**
- Builder store computes field metadata via `frappe.get_meta` directly.
- Other parts use API-driven `get_doctype_fields` utilities.
- Field naming/labeling conventions differ by path (`doc.field`, child prefixes, system fields).

4) **Operation source ambiguity**
- Some paths rely on DB `Process Operation` rows.
- Others fallback to adapter JS operations.
- Eligibility filtering can diverge based on which source is used first.

## Recommended Architecture Changes

### 1) Introduce a single canonical “Rule Contract Spec” artifact
Create one machine-readable schema (JSON/TS/Pydantic) for:
- action types,
- required fields,
- branching capabilities,
- mutation/return constraints,
- per-action config schema,
- API payload schemas.

Generate both Python and JS bindings from it; reject mismatched generated files in CI.

### 2) Normalize all builder-facing APIs to versioned DTOs
- Add `/api/v1/ruleflow/...` typed response DTOs.
- Example: `get_process_operations` should **always** return `[{value,label,meta...}]` and never raw DB row shape.
- Add response version markers to prevent hidden breaking changes.

### 3) Lock down API exposure by capability tiers
- Public metadata endpoints: minimal fields, read-only, explicit permission checks.
- Builder/editor endpoints: require `Rule Builder` or `System Manager`.
- Debug/test endpoints: stricter role + site config flag.

### 4) Replace dynamic adapter execution with signed/static asset loading where possible
- Prefer static bundled adapters (or server-rendered manifests) over arbitrary `new Function` evaluation.
- If dynamic script is mandatory, enforce strict signature/hash allowlist and CSP-safe loading path.

### 5) Add compile-time fail-fast validation
- Invalid scope/ref in condition compiler should hard-fail with actionable error, not silently coerce to empty string expression.

## Consistency Enforcement Strategy

1. **Schema-first**
   - Author contracts as JSON Schema (or Pydantic models exported to JSON Schema).
2. **Codegen**
   - Generate Python validators + TS types + runtime validators (zod/ajv).
3. **CI gates**
   - Contract parity test (backend vs frontend generated hashes).
   - API snapshot tests for DTO shape.
4. **Runtime guardrails**
   - Validate request/response payloads at API boundary.
   - Reject unknown fields in strict mode.

## Performance & Scaling Suggestions

- Cache rule map per doctype+event shard (not single monolith key).
- Incremental cache invalidation when one rule changes.
- Add bounded execution metrics tags (doctype/event/rule) and p95/p99 logging.
- Guard `test_action_query`/manual test endpoints with rate-limit + size limits for JSON payloads.
- Add lazy loading and virtualized lists in builder for very large process/rule graphs.

## Refactoring Roadmap

### Phase 1 (Stabilize contracts, 1–2 weeks)
- Fix `get_process_operations` contract mismatch.
- Add typed DTO normalizers in backend APIs.
- Add one CI test asserting frontend/backend action contract parity.
- Keep migration lightweight and intentionally opinionated (breaking early in beta is cheaper than accumulating silent drift).

### Phase 2 (Security hardening, 1–2 weeks)
- Apply `_require_api_access` (or explicit permission checks) consistently.
- Restrict script loading path and remove raw `new Function` where feasible.
- Add allowlist-based endpoint policy doc + tests.
- In beta, allow temporary developer overrides only behind explicit site config flags (default OFF).

### Phase 3 (Architecture cleanup, 2–4 weeks)
- Introduce canonical contract spec + generated bindings.
- Consolidate field metadata retrieval into one service path.
- Refactor builder and classic form to use the same operation DTO parser.

### Phase 4 (Scale & observability, ongoing)
- Incremental cache invalidation.
- Rule execution telemetry dashboards.
- Load-test suite for heavy-doc-event environments.

## Opinionated Bottom Line
FlexiRule is close to being a strong framework-level rule engine, but it needs **contract governance and API discipline** more than new features. Until the contract duplication and dynamic execution model are tightened, every feature addition will increase hidden coupling and regression risk.
