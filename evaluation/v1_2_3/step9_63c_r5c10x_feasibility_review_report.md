# Step 9.63c-r5c10x — Remaining import-blocker minimal feasibility review

**Status: PASS_READ_ONLY_ONE_COLLECTION_ONLY_CANDIDATE.** No code was changed and no pytest/unittest collection or execution was run. The nine modules in [the dependency matrix](step9_63c_r5c10x_remaining_9_dependency_matrix.json) were independently re-read against current source and file SHA-256 values; their 148 static `test_` method definitions are not current collected or passed counts.

## Finding

There is **one primary shared import-time cause**, not nine proven independent defects. Five modules directly import the frozen adapter, one imports the frozen issuer which imports that adapter, and three import the non-frozen transport which imports the issuer/adapter. `scripts/run_step9_53_v3_identity_adapter.py:25` immediately calls `load_identity_config(ROOT)`; `scripts/v3_runner_identity.py:27-40` requires the exact r11 pointer. The formal r11 pointer and freeze remain absent, so this is a deliberate fail-closed identity boundary. No current import-error count was measured. [Root-cause analysis](step9_63c_r5c10x_shared_root_cause_analysis.json).

The nine modules must not be placed into one unconditional “test-only repair” bucket. `tests/test_step9_63b_mac_local_preflight.py` has a bounded one-file collection-timing candidate. `tests/test_step9_63a_r3_authorization_issuance.py` crosses a frozen issuer boundary and requires a separate contract review before any issuer change. The other seven have module-level adapter-derived values/helpers, live `setUp` bindings, multiple imports, old r7/r8 expectations, or transaction/parent-run/preflight side effects; a safe minimal patch is not yet proven. No production or frozen code change is presently proven **necessary**, and no method execution is authorized merely by moving an import. The complete per-file evidence is in the matrix.

## One candidate, collection only

Recommend at most one later patch: defer the existing top-level transport import in `tests/test_step9_63b_mac_local_preflight.py` into its eight methods. This changes only a non-frozen test file's import timing; it does not require production changes and is expected to expose that file's eight static tests for collection. This is a prediction, **not a collected result**. Every method still needs the transport at runtime, so all eight remain blocked by the real absent r11 identity until a later approved identity/side-effect review. Some methods reach connectivity or `run_preflight()`; do not run them now. The [candidate recommendation](step9_63c_r5c10x_single_file_candidate_recommendation.md) and [collection/execution boundary](step9_63c_r5c10x_collection_execution_safety_boundary.json) specify a future one-file, syntax-plus-collection-only acceptance gate.

## Historical and frozen protection

The r10 historical freeze manifest still hashes to `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693`. The affected historical Trace files still hash to `e09321c89b75a4330799e4a4c286652cee82ed0e0d4fa1b8478c970dd7f6d8e5` and `5518eb4b0b7e8880c5f84e59ba0264013bed99e25edb8da93dca558304d4f084`, respectively. These are forward non-change observations, **not trusted original-content baselines**; `CONTENT_INTEGRITY_UNPROVEN` remains. No r11 pointer/freeze, authorization, preflight, transaction, or V4 execution was created or invoked.

```makefile
STEP9_63C_R5C10X_STATUS = PASS_READ_ONLY_ONE_COLLECTION_ONLY_CANDIDATE
REMAINING_MODULES_REVIEWED = 9
SHARED_ROOT_CAUSES_IDENTIFIED = 1_PRIMARY_IMPORT_TIME_R11_POINTER_DEPENDENCY
SAFE_SINGLE_FILE_CANDIDATE = tests/test_step9_63b_mac_local_preflight.py
CANDIDATE_PATCH_SCOPE = DEFER_EXISTING_TRANSPORT_IMPORT_WITHIN_THIS_NONFROZEN_TEST_FILE_COLLECTION_ONLY
TEST_EXECUTION_ALLOWED = NO
FROZEN_MEMBER_CHANGED = NO
HISTORICAL_TRACE_MODIFIED = NO
NEW_R11_FREEZE_CREATED = NO
NEW_AUTHORIZATION_ISSUED = NO
FORMAL_V4_CASE_EXECUTED = 0
READY_FOR_NEXT_MINIMAL_PATCH_APPROVAL = YES_COLLECTION_ONLY_SEPARATE_HUMAN_APPROVAL_REQUIRED
```
