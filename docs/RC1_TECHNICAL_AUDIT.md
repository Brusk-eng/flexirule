# FlexiRule Framework-Aware Re-Analysis (Frappe-Aligned)

## 0) Study Scope and Constraint Note

I attempted to complete Phase 0 by cloning the official Frappe repository, but this environment blocks outbound GitHub/PyPI access (HTTP 403 via proxy). Because of this, the Frappe-core study below is based on established Frappe runtime behavior and API semantics, then validated against FlexiRule code paths in this repository.

Commands attempted:
- `git clone --depth 1 https://github.com/frappe/frappe.git`
- `python -m pip install ...` (network blocked)

---

## 1) Frappe Core Summary (What was applied in this audit)

### 1.1 DocType lifecycle model applied

Framework order used for analysis:
- `before_insert` (new docs)
- `validate` / `before_save`
- DB write
- `after_insert` (new) / `on_update` (existing)
- submit/cancel flows (`before_submit`, `on_submit`, `before_cancel`, `on_cancel`)
- delete flow (`on_trash`)

Important interpretation used:
- `validate` and `before_save` are pre-write mutation points.
- post-write events (`after_insert`, `after_save`, `on_submit`, `on_update_after_submit`, `on_change`) are generally unsafe for mutating submitted business docs unless explicitly allowed by schema rules.

### 1.2 Permission enforcement layers applied

- `frappe.get_doc` enforces read permissions in normal flow.
- `frappe.get_list` applies permission filters.
- `frappe.get_all` bypasses user permission filtering by design; acceptable only when endpoint itself is strongly permission-gated.
- `ignore_permissions=True` is privileged bypass and should be migration/system-context only.
- `frappe.only_for` provides explicit role gate on endpoint entry.

### 1.3 Whitelisted method behavior applied

- `@frappe.whitelist()` exposes callable endpoint to authenticated users by default.
- `allow_guest=True` would expose to guests (not used here).
- Return values are JSON-serialized; returning raw exceptions (`str(e)`) leaks internals.
- CSRF/session controls exist at framework layer, but business authorization remains app responsibility.

### 1.4 Transaction boundaries applied

- Web requests: generally single transaction with commit/rollback at request boundary.
- Background jobs: transaction is per job; explicit commits create partial durability points.
- Savepoints are valid for partial rollback, but only useful if created before risky steps.

### 1.5 Scheduler/background model applied

- `frappe.enqueue` executes async in workers.
- Retry/requeue behavior means jobs must be idempotent or deduplicated.
- Mid-loop commits in workers convert failures into partial-completion semantics.

### 1.6 Cache model applied

- request-local cache (`frappe.local_cache`) has request scope.
- redis/global cache (`frappe.cache`) must be invalidated explicitly.

---

## 2) Lifecycle Compliance Findings

### L1 — Broad lifecycle injection is framework-allowed but high-risk
- `doc_events` hooks all doctypes (`"*"`) and many phases into rule execution.
- Classification: **Risky but allowed**.
- Evidence: global registration of nearly every lifecycle event.【F:flexirule/hooks.py†L16-L37】
- Impact: increases cross-app side effects and makes lifecycle predictability harder.

### L2 — Post-write phases still execute rule engine
- Rules run in `after_insert`, `after_save`, `on_submit`, `on_update_after_submit`, `on_change`.
- Classification: **Risky but allowed**; correctness depends on rule-level safeguards.
- Evidence: mapped events in global hook config.【F:flexirule/hooks.py†L22-L30】

### L3 — Active guardrails exist for Set Value in submitted contexts
- Rule validation blocks some post-submit edits if target field is not `allow_on_submit`.
- Classification: **Safe and framework-aligned**.
- Evidence: explicit validation for `On Submit` / `On Update After Submit` target field checks.【F:flexirule/ruleflow/doctype/rule/rule.py†L503-L537】

### L4 — Runtime mutation of Rule doc during doc event execution
- Coordinator catches runtime errors and saves `Rule` with `ignore_validate` + `ignore_permissions`.
- Classification: **Risky but allowed** (not a framework violation, but fragile during concurrent execution).
- Evidence.【F:flexirule/ruleflow/core/coordinator.py†L196-L200】

---

## 3) Permission System Findings

### P1 — Several whitelisted APIs have no explicit entry authorization
- Methods like `execute_rule`, `test_rule`, `clone_rule`, `get_process_list` do not call `frappe.only_for` or explicit `frappe.has_permission`.
- Classification: **Risky but allowed** (framework exposes endpoint; app must gate business privilege).
- Evidence.【F:flexirule/ruleflow/api.py†L176-L250】【F:flexirule/ruleflow/api.py†L408-L458】【F:flexirule/ruleflow/doctype/process/process.py†L231-L281】

### P2 — `get_all` used inside whitelisted methods
- `get_process_list`, `get_process_js_paths`, `get_process_operations` use `get_all`.
- Classification: **Risky but allowed**; can bypass per-user list filtering.
- Evidence.【F:flexirule/ruleflow/doctype/process/process.py†L215-L220】【F:flexirule/ruleflow/doctype/process/process.py†L237-L267】【F:flexirule/ruleflow/api.py†L416-L423】

### P3 — Explicit role gate exists only for scheduler manual execute endpoint
- `execute_now` correctly uses `frappe.only_for("System Manager")`.
- Classification: **Safe**.
- Evidence.【F:flexirule/ruleflow/doctype/rule_scheduler/rule_scheduler.py†L207-L214】

### P4 — Privileged bypass in migration sync is context-appropriate
- `process_sync` sets `ignore_permissions=True` while syncing system metadata after migration.
- Classification: **Safe** in migration context.
- Evidence.【F:flexirule/ruleflow/core/process_sync.py†L192-L203】

---

## 4) Transaction & Concurrency Findings

### T1 — Scheduler commits mid-loop (partial durability)
- RuleScheduler commits every batch and at end.
- Classification: **Risky but allowed**.
- Risk: retries/failures can duplicate side effects unless operations are idempotent.
- Evidence.【F:flexirule/ruleflow/doctype/rule_scheduler/rule_scheduler.py†L156-L171】

### T2 — Batch process module has same mid-loop commit behavior
- Batch process commits per batch and final.
- Classification: **Risky but allowed**.
- Evidence.【F:flexirule/ruleflow/process/batch/batch.py†L58-L63】

### T3 — Dedicated log persistence commits independently
- `persist_execution_log` commits log row in its own transaction.
- Classification: **Safe pattern** for audit survivability, with tradeoff that logs can outlive rolled-back business transaction.
- Evidence.【F:flexirule/ruleflow/utils/logging.py†L14-L25】

### T4 — Savepoint rollback path may not have matching savepoint creation in action error branch
- Error branch references `rollback(save_point=flexirule_action_...)`; savepoint setup in same branch is not evident.
- Classification: **Risky but allowed** (logic fragility).
- Evidence rollback path.【F:flexirule/ruleflow/core/engine.py†L534-L552】

### T5 — Dry-run API uses savepoint then rollback correctly
- Classification: **Safe and framework-aligned**.
- Evidence.【F:flexirule/ruleflow/core/coordinator.py†L69-L75】

---

## 5) Hook System Risks

### H1 — Cross-app interference risk from `doc_events["*"]`
- In Frappe, hooks from all apps merge; global wildcard handlers run very often and ordering can be difficult across apps.
- Classification: **Risky but allowed**.
- Evidence of wildcard strategy.【F:flexirule/hooks.py†L16-L31】

### H2 — Short-circuiting is present and reduces overhead
- Hook layer checks excluded doctypes + local cached map before importing coordinator.
- Classification: **Good mitigation**.
- Evidence.【F:flexirule/ruleflow/hooks.py†L61-L73】

### Frappe-aligned recommendation
- Keep wildcard hook only if required, but add configurable doctype allowlist and event subset per rule family to reduce merged-hook blast radius.

---

## 6) ORM & Query Findings

### O1 — `get_all` in exposed APIs where permission-aware listing is expected
- `get_process_list`, `get_process_js_paths`, `get_process_operations`.
- Classification: **Risky but allowed**.
- Evidence.【F:flexirule/ruleflow/doctype/process/process.py†L215-L220】【F:flexirule/ruleflow/doctype/process/process.py†L237-L267】【F:flexirule/ruleflow/api.py†L416-L423】

### O2 — Concrete bug: `default_doctype` typo in Process API fallback
- Type block defines `default_ref_doctype`; API uses `default_doctype`.
- Classification: **Framework-agnostic bug (Major)**.
- Evidence mismatch.【F:flexirule/ruleflow/doctype/process/process.py†L27-L40】【F:flexirule/ruleflow/doctype/process/process.py†L174-L177】

### O3 — Direct SQL usage in scheduled cleanup
- Current SQL is parameterized and bounded by static table.
- Classification: **Safe** from SQLi standpoint; stylistically ORM alternative exists.
- Evidence.【F:flexirule/tasks.py†L14-L20】

### O4 — Missing explicit patch entries for index hardening
- `patches.txt` has section headers only.
- Classification: **Risky but allowed** (scale concern, not framework violation).
- Evidence.【F:flexirule/patches.txt†L1-L5】

---

## 7) Security Boundary Review

### S1 — No guest exposure found in whitelisted methods
- No `allow_guest=True` declarations observed.
- Classification: **Safe baseline**.
- Evidence includes standard whitelist usage only.【F:flexirule/ruleflow/api.py†L176-L176】【F:flexirule/ruleflow/doctype/process/process.py†L170-L170】

### S2 — Internal error strings are returned to API callers
- `{"error": str(e)}` patterns present.
- Classification: **Risky but allowed**; leaks internals and weakens API contract.
- Evidence.【F:flexirule/ruleflow/api.py†L219-L220】【F:flexirule/ruleflow/api.py†L249-L250】

### S3 — Endpoint-level privilege escalation paths
- Because multiple admin-like APIs are ungated and some use `get_all`, authenticated non-admin users may retrieve metadata beyond intended scope depending on site role config.
- Classification: **Risky but allowed** (authorization design issue).
- Evidence.【F:flexirule/ruleflow/doctype/process/process.py†L237-L267】【F:flexirule/ruleflow/api.py†L408-L423】

---

## 8) Differences From Previous Audit

### 8.1 Findings that remain valid
- Global wildcard hook risk remains valid.
- Permission hardening gaps in whitelisted APIs remain valid.
- Scheduler partial-commit/idempotency risk remains valid.
- Process field typo bug remains valid.

### 8.2 Findings corrected/refined in this framework-aware pass
- Prior wording implied `get_doc` itself was a permission gap in APIs; refined view: the bigger issue is missing **endpoint-level authorization + `get_all` usage**, because `get_doc` does enforce read permission in normal flow.
- Direct SQL in cleanup is not itself a framework violation; it is acceptable if parameterized and intentional.

### 8.3 New/clearer findings from framework lens
- `persist_execution_log` intentionally commits independently: this is a deliberate audit-durability pattern, not automatically a bug.
- Migration-time `ignore_permissions` in process sync is acceptable system-context usage.
- True risk is not “framework violation everywhere” but **risky-but-allowed** patterns around authorization design and transaction semantics.

---

## 9) Revised RC Readiness Score (0–100)

### **72 / 100**

Reasoning:
- + improved confidence in lifecycle guardrails and savepoint usage in some paths.
- - meaningful authorization and transaction-idempotency hardening still required.
- - missing DB patch/index plan remains a release-readiness gap.

---

## 10) Final Go / No-Go Recommendation

## **NO-GO for RC1 today**

### Mandatory fixes (framework-critical/risk material)
1. Add explicit authorization gates (`frappe.only_for` or `frappe.has_permission`) for every admin-impacting whitelisted method.
2. Replace permission-bypassing `get_all` with `get_list` in user-facing endpoints (or role-gate endpoints to admins only).
3. Fix `default_doctype` → `default_ref_doctype` bug in Process API fallback.
4. Add idempotency guardrails for scheduler/batch execution with partial commits.

### Strongly recommended fixes
1. Add index patches for dominant filters and log lookups.
2. Normalize API error responses (no raw internal exception text).
3. Add concurrency tests for scheduler retries and duplicate side-effect prevention.
4. Reduce wildcard `doc_events` surface (doctype allowlist and event subset).

### Optional improvements
1. Split API into admin/runtime modules.
2. Introduce settings doctype for retention, batch size, and operational defaults.
3. Expand audit metadata on manual rule executions.

---

## 11) Deep Scheduler/Idempotency Review (Current Design)

### 11.1 What exists today

Current scheduler execution path:
1. periodic hook scans active schedulers (`check_scheduled_rules`).
2. each scheduler doc can enqueue a job with `job_id = rule_scheduler::{name}`.
3. worker loads matching documents and iterates.
4. commits happen every `batch_size`, then at end.

Evidence:
- scheduler scan and enqueue entrypoint.【F:flexirule/ruleflow/scheduler.py†L13-L20】
- dedupe by RQ job id on enqueue.【F:flexirule/ruleflow/doctype/rule_scheduler/rule_scheduler.py†L73-L96】
- batch loop with partial commits.【F:flexirule/ruleflow/doctype/rule_scheduler/rule_scheduler.py†L135-L171】

### 11.2 Determinism gaps in current model

#### D-GAP-1: `job_id` deduplicates only queued/running job, not execution window
- once job finishes/fails, same scheduler can re-enqueue before/after boundary ambiguities.
- no persisted run identity (`scheduled_for`) to guarantee exactly one run per schedule window.

#### D-GAP-2: document-level idempotency key is absent
- if worker crashes after side effects but before updating execution markers, retry can replay same doc.
- especially risky with external side effects (email/todo/notifications/process methods).

#### D-GAP-3: partial commit semantics without checkpoint ledger
- commits every batch are fine operationally, but replay behavior is nondeterministic without durable per-doc status table.

#### D-GAP-4: no lease/fencing token on scheduler ownership
- two workers can contend around timing edges (queue retry/manual force + normal schedule).
- RQ job ID helps at queue submission, but not as durable distributed lease.

---

## 12) Proposed Deterministic Execution Model

### 12.1 Design target

Adopt **at-least-once delivery + exactly-once effect per (scheduler, slot, doc, rule version)** using explicit idempotency ledger and run-state machine.

This matches Frappe worker realities (retries, crashes, partial commits) while still delivering deterministic outcomes.

### 12.2 New persistence entities (minimal)

### A) `Rule Scheduler Run` (parent)
Fields:
- `name` (autoname)
- `scheduler` (Link Rule Scheduler)
- `slot_ts` (Datetime, normalized schedule boundary)
- `status` (`Queued`,`Running`,`Completed`,`Failed`,`Aborted`)
- `lease_owner` (worker id)
- `lease_until` (Datetime)
- `attempt`
- `started_at`,`finished_at`
- `total_docs`,`processed_docs`,`success_docs`,`failed_docs`
- `error_summary`

Unique constraint/index:
- unique `(scheduler, slot_ts)`

### B) `Rule Scheduler Run Item` (child/standalone)
Fields:
- `run` (Link Run)
- `doc_doctype`,`doc_name`
- `idempotency_key` (Data, unique)
- `status` (`Pending`,`Processing`,`Succeeded`,`Failed`,`Skipped`)
- `attempt_count`
- `last_error`
- `result_hash` (optional)
- `processed_at`

Unique constraint/index:
- unique `idempotency_key`
- index `(run, status)`

### C) `Rule Effect Journal` (optional but recommended for external side effects)
Fields:
- `idempotency_key`
- `effect_type` (`email`,`todo`,`notification`,`custom`)
- `effect_target`
- `status`
- `payload_hash`
- `created_at`

Unique constraint:
- `(idempotency_key, effect_type, effect_target)`

### 12.3 Canonical idempotency key

For each document execution:

`sha256(f"{scheduler}|{slot_ts_iso}|{rule_name}|{rule_modified}|{doc_doctype}|{doc_name}")`

Why include `rule_modified`:
- prevents accidental suppression across rule revisions.
- keeps retries for same run deterministic.

### 12.4 Scheduler run state machine

`Queued -> Running -> (Completed | Failed | Aborted)`

Rules:
1. create/get run by `(scheduler, slot_ts)` under transaction.
2. only one owner can transition `Queued/Running` with valid lease.
3. lease must be renewed periodically (heartbeat).
4. if lease expired, next worker may fence old owner and continue.

### 12.5 Deterministic algorithm (worker)

1. **Acquire run**
   - `INSERT ... ON DUPLICATE` (or get existing) for `(scheduler, slot_ts)`.
   - if existing `Completed`, exit (already done).
   - acquire lease via conditional update where `lease_until < now` or same owner.

2. **Materialize item set**
   - fetch document list (stable ordering by `name asc`).
   - upsert `Run Item` rows with idempotency keys.

3. **Process loop by item status**
   - select `Pending/Failed(retriable)` items ordered by `doc_name`.
   - transition item to `Processing` with compare-and-set.
   - execute rule inside per-item savepoint.
   - on success -> `Succeeded`; on error -> `Failed` with attempts.
   - commit each item (or small chunk) safely.

4. **Finalize run**
   - if all terminal and no failed -> `Completed`.
   - else `Failed` (with summary), eligible for controlled retry policy.

### 12.6 External side effects policy

For side-effecting operations (`sendmail`, `create_todo`, notifications):
- before effect, check `Rule Effect Journal` by `(idempotency_key, effect signature)`.
- if exists succeeded -> skip effect.
- else perform effect + insert succeeded row atomically with item txn.

This makes retries safe and deterministic.

---

## 13) Concrete Framework-Aligned Implementation Plan

### 13.1 Immediate changes in existing scheduler code

1. Replace direct doc loop execution with run/item service layer.
2. Keep `frappe.enqueue` but set payload to explicit `run_name` not just scheduler name.
3. Persist `slot_ts` from due-check time (not worker start time).
4. Keep batch commits, but only after item status transition commit.

Target files to refactor first:
- `flexirule/ruleflow/scheduler.py`【F:flexirule/ruleflow/scheduler.py†L13-L30】
- `flexirule/ruleflow/doctype/rule_scheduler/rule_scheduler.py`【F:flexirule/ruleflow/doctype/rule_scheduler/rule_scheduler.py†L106-L204】
- `flexirule/ruleflow/process/batch/batch.py` (share same run-item engine).【F:flexirule/ruleflow/process/batch/batch.py†L42-L64】

### 13.2 Required DB patches

1. create `Rule Scheduler Run` doctype + unique index `(scheduler, slot_ts)`.
2. create `Rule Scheduler Run Item` + unique `idempotency_key`.
3. add index `Rule Execution Log(rule, reference_docname, creation)`.
4. add index for scheduler selection/status fields if high-volume.

Note: `patches.txt` currently has no active entries, so this must be introduced before RC1.【F:flexirule/patches.txt†L1-L5】

### 13.3 Transaction model recommendation

- **Per item transaction boundary** with savepoint around rule execution.
- item state writes (`Processing -> Succeeded/Failed`) and effect journal writes are committed together.
- run summary counters updated with atomic `db_set`/SQL increments.
- no global long transaction over all docs.

### 13.4 Retry policy (deterministic)

- retry only failed items with `attempt_count < max_attempts`.
- exponential backoff based on item attempts.
- preserve same idempotency key across retries in same run.
- new schedule slot creates new run + new keyspace.

### 13.5 Manual `execute_now` behavior

- manual trigger should create slot key with suffix `manual:{timestamp}` or explicit `manual_run_id` to avoid colliding with scheduled slot.
- still use run/item ledger for determinism.

---

## 14) Deterministic Test Matrix (must add before RC1)

1. **Crash-after-side-effect test**
   - simulate failure after email send but before item completion update.
   - assert replay does not send duplicate email (effect journal check).

2. **Concurrent worker acquisition test**
   - two workers attempt same `(scheduler, slot_ts)`.
   - assert only one lease holder processes items.

3. **Partial commit replay test**
   - fail halfway through N items.
   - rerun same slot and assert already-succeeded items are skipped deterministically.

4. **Rule revision isolation test**
   - same doc, same scheduler, different rule modified timestamp.
   - assert different idempotency keys and expected fresh execution.

5. **Manual vs scheduled collision test**
   - run `execute_now` near due slot boundary.
   - assert manual run and scheduled run are isolated and traceable.

6. **Batch process parity test**
   - batch module should reuse same run/item idempotency primitives.

---

## 15) Updated Conclusion on Scheduler Design

Current design is operational but not deterministic under retries/failures because idempotency is queue-level only (RQ job ID), not effect-level.

With the proposed run/item ledger + lease + canonical idempotency keys, FlexiRule can achieve deterministic, auditable, and replay-safe scheduler execution consistent with Frappe worker semantics.

---

## 16) Senior Architecture Review of Proposed Deterministic Model (Frappe + Distributed Systems)

### Pros

1. **You correctly moved idempotency from queue-level to data-level.**
   - Queue dedupe (`job_id`) is weak; DB uniqueness is the right place for determinism.
2. **Per-document transaction boundaries are cleaner than batch-wide mid-loop commits.**
   - This maps better to Frappe worker failure semantics.
3. **Explicit execution state introduces observability and replay control.**
   - This is mandatory for marketplace-grade auditability.
4. **Timeout recovery for stuck `Running` states is necessary and currently missing.**
5. **Deterministic ordering at scheduling time is directionally correct.**

### Cons

1. **“At-most-once execution” is overstated and technically false in your current wording.**
   - With distributed workers and crash/retry, you get **at-least-once delivery + idempotent effect**, not strict at-most-once.
   - If a worker performs side effects and dies before transaction finalization, replay still occurs unless every effect is idempotent.

2. **`trigger_hash = hash(rule.modified + doc.modified)` is weak and unstable.**
   - `doc.modified` can change for unrelated metadata updates.
   - hash implementations differ; you need stable canonical digest (e.g., SHA-256 over canonical JSON payload).
   - using timestamp fields alone misses semantic equivalence and can cause false positives/negatives.

3. **Atomic “insert Running then execute” is not a complete lock protocol.**
   - You still need lease/fencing to handle stale `Running` rows after worker death.
   - Duplicate key alone is not ownership semantics.

4. **“Logs inside same transaction only” conflicts with operational forensics goals.**
   - If transaction rolls back, logs disappear exactly when you need them.
   - You need two log classes: transactional business logs + out-of-band failure telemetry.

5. **Enqueue-per-document can crush queue infrastructure at 50k scale.**
   - Job fan-out creates high Redis/RQ pressure, scheduling overhead, and worker context-switch churn.

6. **FOR UPDATE in scheduler fetch is mostly a red herring here.**
   - You are not mutating those rows at schedule time; lock contention increases with little deterministic gain.

7. **Single-row `Rule Execution State` model is underspecified for retries.**
   - Reusing one row mutates history and destroys forensic timeline.
   - You need immutable attempts or separate attempt table.

### High-Risk Components

1. **Hard claim that model guarantees at-most-once.**
   - This will fail in real failure modes and create false confidence in compliance docs.
2. **Trigger hash definition based on `modified` fields.**
   - High risk of duplicate suppression bugs and missed executions.
3. **One-job-per-doc at high volume.**
   - High operational risk (queue storms, backlog growth, long tail latency).
4. **Stale `Running` recovery without fencing token.**
   - Split-brain execution risk when old worker resumes after timeout reassignment.

### Unnecessary Components

1. **Do NOT add `SELECT ... FOR UPDATE` to scheduler listing path by default.**
   - It increases lock contention and doesn't solve core idempotency.
2. **Do NOT force all logging into same transaction.**
   - Keep critical failure telemetry out-of-band.
3. **Do NOT treat unique key as a complete distributed lock system.**
   - You still need lease + owner token transitions.

### Recommended Modifications

#### A) Correct the guarantee language
- Replace “at-most-once execution” with:
  - **At-least-once dispatch**
  - **Exactly-once effect per deterministic execution identity** (only for actions proven idempotent)

#### B) Replace trigger hash construction
Use canonical digest over deterministic payload:
- `rule_name`
- `rule_version` (immutable int, not mutable timestamp)
- `trigger_event`
- `doc_doctype`, `doc_name`
- selected business fields used by conditions/actions (normalized JSON)

Then:
- `trigger_hash = sha256(canonical_json)`

#### C) Split execution state into run + attempt
- `Rule Execution State` (identity row, unique on execution key)
- `Rule Execution Attempt` (append-only per retry, with worker_id, started_at, ended_at, outcome)

This preserves history and avoids mutable forensic loss.

#### D) Use bounded fan-out, not pure one-job-per-doc
For 50k+ docs:
- scheduler creates **shards/pages** (e.g., 500 docs per shard job)
- shard worker processes with per-doc claim rows and per-doc commits
- this retains isolation while avoiding 50k immediate jobs

#### E) Introduce lease + fencing
On claim/start:
- set `lease_owner`, `lease_token`, `lease_until`
- updates require matching current token
- recovery can only steal when lease expired and token version advanced

#### F) Action-level idempotency policy matrix
- classify actions: `pure`, `doc_update`, `side_effect`
- side-effect actions require effect journal unique key `(execution_key, action_id, effect_signature)`
- retries must check journal before invoking external effect

#### G) Logging model (dual path)
- transactional log: business-visible execution log (rolls back with doc)
- durable telemetry log: failure/error channel outside transaction for incident triage

#### H) Cleanup and retention
- `Rule Execution State/Attempt` tables require retention policy and archiving job.
- without this, table growth will become your next production incident.

### Final Verdict

## **Adopt with Changes**

Your direction is correct, but the current proposal overclaims guarantees and under-specifies failure ownership, hashing semantics, and high-volume scheduling behavior.

If implemented exactly as written, it will still produce duplicate effects under crash/retry edges and may create queue-scale instability for large tenants.

Implement the modifications above or do not ship this as “deterministic” in RC messaging.
