# Test Coverage Audit — FlexiRule

## 1. Automated Test Suite Execution Results

### Current Fetch Records review-fix run — 2026-10-11

The server CI job ran the test suite on the Fetch Records review-fix branch:

- **Command**: bench --site test_site run-tests --app flexirule
- **Result**: 543 tests run, **1 error**, 0 assertion failures, 2 skipped.
- **Failing test**: test_fetch_records_delegates_native_qb_payload_and_permissions.
- **Observed exception**: KeyError: 0 in Frappe's virtual-DocType metadata lookup after the test unintentionally entered the permission-aware frappe.get_list fallback.

This run is **not green**. The production compatibility layer detected that the installed Frappe v15 Query Builder does not expose native ignore_permissions, and correctly selected the permission-aware fallback. The test was intended to characterize native Query Builder delegation but had not isolated that capability scenario.

A test-only correction has been pushed: the native-delegation test now stubs the capability descriptor to represent native support and explicitly checks the ignore_permissions=False argument. Dedicated compatibility tests remain responsible for exercising the Frappe v15 fallback. The updated run must pass before this item is considered verified.

### Earlier historical run

An earlier test-site run reported **414 tests**, 412 passed, and 2 skipped in 18.21 seconds. That result predates the current branch and must not be used as evidence that the current review-fix changes pass.

**Test suite location**: flexirule/ruleflow/tests/.

---

## 2. Regression Test Suite for Confirmed Findings

A dedicated regression test module `flexirule/ruleflow/tests/test_audit_reproductions.py` was implemented and permanently integrated into the test suite to verify fixes for the key findings:
1. **AST Validation & Sandbox Escape (FR-SEC-001)**: `test_FR_SEC_001_ast_validation_stub_sandbox_escape` verifies `validate_safe_eval` throws `ValidationError` when encountering dunder attribute traversal expressions (`__subclasses__`).
2. **Server-Side Template Injection (FR-SEC-002)**: `test_FR_SEC_002_ssti_in_document_action_rendering` verifies `DocumentActionHandler._render_scalar` does not evaluate raw `frappe` module database calls.
3. **SafeFrappeAPI Parameter Guard (FR-SEC-003)**: `test_FR_SEC_003_safe_frappe_api_format_value_dict_override` verifies `SafeFrappeAPI.format_value` blocks custom dictionary overrides as `df`.
4. **Sub-Rule Recursion Depth Limit Enforcement (FR-ENGINE-002)**: `test_FR_ENGINE_002_sub_rule_recursion_depth_propagated` verifies `SubRuleHandler` enforces `MAX_SUB_RULE_DEPTH = 2` when context depth exceeds the limit.


## 3. Follow-up Verification Status

- [x] Identify the CI failure and trace it to a version-dependent test setup.
- [x] Push a deterministic test-isolation fix to fix/fetch-records-review-findings.
- [ ] Confirm the rerun passes the complete server test suite.
- [ ] Confirm all linter and frontend CI jobs pass for the same branch head.

Do not convert the unchecked items to complete based only on the code change; the CI results for the new commit are the acceptance evidence.


## 4. Latest CI Rerun: Native Payload Assertion (2026-10-11)

The next server run still reports one failure among 543 tests (zero errors, one assertion failure, two skipped): `test_fetch_records_delegates_native_qb_payload_and_permissions`. The capability-isolation fix resolved the prior environment-dependent fallback path, exposing a stale expected payload in the same test. Fetch Records normalizes root-DocType filter leaves from four-item form `[doctype, field, operator, value]` to three-item form `[field, operator, value]` before delegation. The assertion expected the pre-normalized `User` prefix, while the actual delegated payload correctly omitted it. Updated the expected payload to match the handler's normalized contract. CI for this correction is pending; verification remains open until the complete server suite and other checks pass.
