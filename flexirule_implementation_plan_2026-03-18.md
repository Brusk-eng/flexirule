# FlexiRule Implementation Plan (Post-Architecture Review)

Date: 2026-03-18
Scope: Convert architecture findings into executable engineering work.

## Beta delivery posture

Because FlexiRule is still in beta (not production-ready), this plan favors:
- fast convergence on one contract/API behavior,
- explicit breaking changes where they reduce long-term risk,
- strict CI guards early,
- reduced emphasis on long-tail backward compatibility.

## Outcomes (What “done” means)

1. Frontend + backend use one contract source (or generated artifacts) for rule action semantics.
2. Builder-facing APIs return stable, versioned DTOs.
3. Whitelisted endpoints follow explicit access policy tiers.
4. Dynamic process adapter execution risk is reduced with controlled loading.
5. CI enforces contract/API consistency and blocks drift.

## Beta-ready exit gate (before wider rollout)

1. No known frontend/backend operation-shape mismatches.
2. Contract parity check is mandatory in CI and passing.
3. All sensitive whitelisted endpoints have explicit permission policy tests.
4. Dynamic adapter loading path is constrained (or guarded with strict fallback + visibility).
5. Critical builder flows pass smoke tests (Rule Form + Rule Builder parity).

---

## Phase 0 — Baseline & Guardrails (2–3 days)

### Work
- Add architecture decision record (ADR) for:
  - contract source-of-truth,
  - API DTO versioning,
  - endpoint access tiers,
  - adapter loading hardening.
- Create tracking board with epics:
  - Contract unification,
  - API normalization,
  - Security hardening,
  - Runtime/scale improvements,
  - CI quality gates.

### Deliverables
- `docs/adr/ADR-00x-rule-contract-governance.md`
- implementation tracker with owners and target dates.

### Exit criteria
- Team agrees on canonical schema strategy and migration order.

---

## Phase 1 — Fix Critical Contract Breaks First (1 week)

### 1.1 Normalize `get_process_operations`
- Change backend response to explicit DTO shape:
  - `[{ value: func_name, label, enabled, visible_in_builder, meta: {...} }]`
- Add backward compatibility (temporary):
  - if caller expects old shape, adapt in frontend parser.
- Update:
  - `ruleflow/doctype/rule/rule.js`
  - rule builder store/composables to consume the same parser utility.

### 1.2 Introduce one frontend operation parser
- Add `normalizeOperationOptions(raw)` helper.
- Use in both:
  - classic Rule form,
  - Vue Rule Builder.

### 1.3 Add regression tests for this mismatch
- Python API test for DTO fields.
- JS unit test for parser behavior (object list + legacy list fallback).

### Deliverables
- API DTO for operations.
- Shared frontend parser.
- Tests proving no surface-specific mismatch.

### Exit criteria
- Operation dropdown works identically on Rule form and Rule Builder.
- Any intentional breaking API shape change is documented in `CHANGELOG` under a beta-breaking section.

---

## Phase 2 — Contract Unification (1–2 weeks)

### 2.1 Create canonical contract artifact
- Define `rule_contract.schema.json` (or equivalent typed model).
- Include:
  - action types,
  - required fields,
  - branching capabilities,
  - terminal behavior,
  - mutation constraints,
  - per-action config schema hooks.

### 2.2 Generate backend/frontend artifacts
- Python: generated module for validation constants.
- JS: generated contract module for builder UI.
- Keep generated files committed and deterministic.

### 2.3 CI parity gate
- Add check that generated outputs are up-to-date.
- Fail CI when manual edits drift from canonical source.

### Deliverables
- Canonical schema + generator scripts.
- Generated Python/JS contracts.
- CI enforcement job.

### Exit criteria
- Remove hand-maintained duplicate contract maps.

---

## Phase 3 — API Boundary Hardening (1 week)

### 3.1 Endpoint access policy matrix
- Classify whitelisted endpoints by tier:
  - Tier A (public metadata, minimal scope),
  - Tier B (builder/editor),
  - Tier C (test/debug/administrative).

### 3.2 Enforce permission checks consistently
- Apply role/capability checks to utility endpoints where needed.
- Ensure all potentially sensitive metadata/script endpoints are gated.

### 3.3 Response minimization
- Remove unnecessary fields from utility API payloads.
- Add explicit `api_version` in response objects for critical endpoints.

### Deliverables
- `docs/security/api-access-matrix.md`
- endpoint permission tests.

### Exit criteria
- No whitelisted endpoint with sensitive behavior lacks explicit policy.

---

## Phase 4 — Dynamic Adapter Risk Reduction (1 week)

### 4.1 Restrict adapter loading
- Prefer static asset path or signed manifest over arbitrary script execution.
- If dynamic path remains, validate checksum/signature before evaluation.

### 4.2 Controlled fallback behavior
- If adapter load fails verification, disable operation configuration with actionable UI error.

### 4.3 Observability
- Log adapter load source, hash, and failure reason (without leaking payload).

### Deliverables
- Adapter loading policy + implementation.
- telemetry events for adapter loading.

### Exit criteria
- No uncontrolled dynamic script eval path in production mode.

---

## Phase 5 — Runtime Correctness & Scale (1–2 weeks)

### 5.1 Compiler strict mode
- Change invalid scope/reference fallback from silent empty expression to validation error.
- Add migration script/report for existing affected rules.

### 5.2 Rule map invalidation improvements
- Move from full global invalidation to targeted doctype/event key invalidation where feasible.

### 5.3 Execution observability
- Add p95/p99 execution telemetry by doctype/event/rule.
- Add skip/fail reason counters.

### Deliverables
- strict compiler validation mode.
- improved cache invalidation strategy.
- dashboard-ready metrics.

### Exit criteria
- measurable drop in ambiguous runtime failures and improved rule execution visibility.

---

## Testing & Quality Gates

## Backend
- API contract tests for each normalized endpoint.
- Permission tests for all whitelisted endpoints.
- Rule compile/validate tests for strict mode behavior.

## Frontend
- Unit tests for DTO parsers and contract consumers.
- E2E smoke tests:
  - create/edit process action in Rule form,
  - same action in Rule Builder,
  - save/validate/execute path.

## CI policy
- Lint + static checks must pass.
- Contract parity/generation check must pass.
- API snapshot diff requires explicit approval.

---

## Rollout Strategy

1. Ship Phase 1 behind compatibility adapter (no breaking UI changes).
2. Introduce Phase 2 generation in “warn-only” CI mode for one sprint.
3. Flip to strict CI enforcement once all call sites migrate.
4. Roll out endpoint hardening with feature flags per endpoint group.

### Beta acceleration option (recommended)

If internal consumers can absorb minor breaking changes, skip compatibility adapter and move directly to normalized DTOs + strict parser checks in one sprint. This reduces dual-path maintenance during beta.

---

## Risks & Mitigations

- **Risk:** Contract migration breaks existing customizations.
  - **Mitigation:** Provide compatibility parser + deprecation window.
- **Risk:** Permission tightening surprises existing roles.
  - **Mitigation:** publish access matrix + migration notes.
- **Risk:** Adapter hardening blocks legacy custom process scripts.
  - **Mitigation:** temporary allowlist + signed migration path.

---

## Suggested Owner Split

- **Backend lead:** DTOs, permissions, compiler strict mode, cache invalidation.
- **Frontend lead:** unified parser, generated contracts integration, UI fallback handling.
- **QA lead:** cross-surface rule authoring regression suite.
- **DevOps:** CI gates, contract-generation checks, telemetry wiring.

---

## First Sprint Backlog (Practical)

1. Normalize `get_process_operations` DTO.
2. Add shared JS parser and migrate Rule form + Builder to it.
3. Add API and UI regression tests for operations dropdown behavior.
4. Add ADR for contract source-of-truth decision.
5. Add initial CI check that backend/frontend operation shapes are validated.
