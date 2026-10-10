# Step 9.63c-r5c10ab — Test infrastructure recovery and r11 Freeze blocker review

Status: `PASS_GUARDED_FULL_REGRESSION_MEASURED_C1_FIXED_R11_FREEZE_NOT_READY`

Date: 2026-10-09. Interpreter: project `.venv/bin/python` (Python 3.12.14). Framework: stdlib `unittest`
only; pytest was neither required nor installed. No dependency, lock file or global environment change.

## 1. Current Repository State Report

| Item | Historical report | Current, measured here |
|---|---|---|
| Test files | — | 66 `tests/test_*.py`, 0 syntax errors (AST) |
| Collected methods | 603 | 648 before fix, **650** after (+2 new negative tests) |
| Passed | 577 | 594 before fix (608 excluding 14 guard false positives), **628** after |
| Failed | 20 | **4** |
| Runtime errors | 6 (18 incl. placeholders) | **18** |
| Import blockers | 12 | **8** |
| r10 freeze manifest SHA | `d24244…2693` | unchanged |
| r10 members | 17 match, 3 approved r11 deltas | identical: 17 match; scanner, resolver, formal consumer differ (approved r5c10c/r5c10j) |
| Historical traces | `e09321…d8e5`, `5518eb…4f084` | unchanged SHA and mtime; content integrity still `CONTENT_INTEGRITY_UNPROVEN` |
| r11 pointer / freeze / registry | absent | absent |

Reconciliation: 603 + 43 methods made collectable by the r5c10r/t/v/y import isolations (9+13+13+8) + 2
negative tests from r5c10o = 648. Then 648 + 2 new C1 negatives = 650.

Differences from the handoff:
- The handoff listed 3 previously modified test files. Six non-frozen test files had actually been modified
  in r5c10o/r/t/v/y. All six match their recorded post-patch SHA-256 values.
- The three handoff files are **Git-untracked**, so `git diff` has no baseline for them. Their integrity was
  verified only against SHAs recorded in `record.md`.
- `scripts/run_step9_35a_matched_treatment.py` shows `M` versus Git HEAD, but its bytes equal the r10-frozen
  SHA (`b79bc78a…`). It is a frozen member and was not touched.
- The r5c10y item (collection of `test_step9_63b_mac_local_preflight.py`) is now verified with native
  unittest: 8 collected, 0 import errors, no side effects. pytest was not needed.
- New finding: `unittest.TestLoader.loadTestsFromName` converts only `ImportError` into a placeholder. The
  adapter's `RuntimeError` propagates and aborts the whole load. The repository's CI loop
  (`.github/workflows/tests.yml`) uses `loadTestsFromName`, so CI crashes at the first blocked module instead
  of reporting results. CI was **not** modified; see Remaining Blockers.

## 2. Root Cause Matrix

| ID | Items now | Mechanism | Fix class | Status |
|---|---|---|---|---|
| C1 | 0 (was 18) | Frozen parent runner calls `assert_executable_authorization()` without a manifest. The reducer globs the *real* `evaluation/v1_2_3` manifests and ledger, so a synthetic test ID is always `INCONSISTENT_FAIL_CLOSED` before the targeted assertions run. Production guard correct. | Test fixture only | **FIXED** |
| C2 | 8 import-blocked modules | Frozen adapter `scripts/run_step9_53_v3_identity_adapter.py:25` calls `load_identity_config(ROOT)` at import. The strict r11 resolver rejects the absent pointer. Chains: direct, via the frozen issuer, or via non-frozen transport. | Frozen member, or wait for r11 | BLOCKED (expected fail-closed) |
| C2R | 14 runtime errors | Same root as C2, reached at method execution after earlier collection-only import isolation. | Wait for r11 | BLOCKED (expected fail-closed) |
| C3 | 3 | r9/r8 bootstrap tests assert old resolver behaviour; the resolver is now r11-only by design. | Test contract decision | NEEDS DECISION |
| C4 | 3 | Archival r10 snapshot tests expect live r10 executability, which the r11-only resolver forbids. | Test contract decision (retire or archive) | NEEDS DECISION |
| C5 | 1 | V2 identity check rejects current parent runner bytes against the archived V2 parent SHA. The module is already listed as artifact-bound in CI. | Needs trusted archived bytes | NEEDS DECISION |
| C6 | 1 | Step 9.51a pinned test-inventory manifest does not list test modules added later. | Historical contract decision | NEEDS DECISION |

Answers to the analysis questions:

- **A.** The adapter binds module constants (`V3_RUNNER_FREEZE_PATH`, `RUNNER_FREEZE_REVISION`) from the
  current pointer at import time. Since r5c10j the resolver accepts only r11, and the r11 pointer is
  intentionally absent.
- **B.** Identity should be resolved in the functions that need it (`run`, validation), not at module load.
  Changing that requires editing a frozen member. It is not done here.
- **C.** C1 was fixed test-only. Collection-only deferral is possible for some C2 modules, but every such
  move turns into a C2R runtime error. Its value is visibility only.
- **D.** CI loader robustness (`loadTestsFromName` versus arbitrary import exceptions). Proposed, not done.
- **E.** All 8 C2 modules and 14 C2R methods require the formal r11 pointer. Their pass/fail outcome after
  r11 exists is **NOT_MEASURED** and may expose further r10/r7-era expectations.
- **F.** Yes. 30 of 38 historical items, plus all current C2/C2R items, share the adapter import-time read.
  C1 (18) was a separate shared fixture cause.
- **G.** Collection of all 66 modules produced 0 guard events and 0 file changes. The historical trace writers
  were already isolated in r5c10o and stayed clean. The full regression made 0 repository writes, 0 network
  resolutions or connections, and launched 2 allowed `python -c` subprocesses (r5c7d).

## 3. Modified Files and SHA Audit

| File | Frozen? | Before | After | Change |
|---|---|---|---|---|
| `tests/test_step9_35a_treatment_runner.py` | No (Git-tracked, already had uncommitted +2 lines) | `793070e74d79ed4156f8f017633a4d82f47edfdd4d2736114121dc2019980068` | `8934cbeee1e93555e56b8778fe1ece248840e366bd034395eb3f44c12c61f781` | +40 lines, 0 removed (see `step9_63c_r5c10ab_c1_fixture_fix.diff`) |
| `tests/._test_step9_35a_treatment_runner.py` | No (exFAT AppleDouble, untracked) | `b3f6f260…5cc574` | `d469bba1…a2c0a` | OS metadata side effect of the edit |
| `record.md` | No | `8dcb26804430a310d4637db05f60261ebb13ea03c7dd4a145260036f453f29d6` | see final record | appended entry |

C1 fix details:
- `setUp` creates a temporary lifecycle root holding one synthetic issued manifest, an empty lifecycle
  ledger path, and empty run/transaction roots.
- It patches `authorization_lifecycle.ROOT/EVENT_LEDGER_PATH` and `v3_execution_transaction.RUN_ROOT/TRANSACTION_ROOT`
  with `mock.patch.object`, restored through `addCleanup`.
- The real reducer still runs end to end. No assertion was changed, and there is no skip, xfail or
  exception swallowing.
- Two negatives were added: a missing issuance manifest must fail with `INCONSISTENT_FAIL_CLOSED`, and a
  retirement event must fail with `RETIRED_UNCONSUMED_NON_REUSABLE`.
- A read tracer confirmed 0 reads of real repository authorization or `v4_runs` files during the module.

New evidence files: this report, `step9_63c_r5c10ab_test_results_matrix.json`,
`step9_63c_r5c10ab_c1_fixture_fix.diff`, and `step9_63c_r5c10ab_test_harness/` (reference tooling, see §4).
No frozen member, historical trace, authorization artifact, ledger, registry or production module changed.

## 4. Test Collection and Regression Report

Side-effect guard (`step9_63c_r5c10ab_test_harness/guard/sitecustomize.py`):
- It is a Python audit hook loaded via `PYTHONPATH` and inherited by child interpreters.
- It blocks and logs: writes/creates/renames/deletes/metadata changes under the repository (including
  `dir_fd`-relative operations), non-loopback DNS and connections, and non-Python subprocesses.
- Self-tested on each block path. Two false-positive classes were found and fixed during this step:
  `rmtree` with `dir_fd` relative names, and repo→tmp `copyfile` reads.
- The independent backstop is a full-repository SHA/size/mtime snapshot of 2,333 files, excluding `.venv`,
  `.git`, `models` and `__pycache__`.

| Level | Command (from repo root) | Exit | Result |
|---|---|---|---|
| L1 syntax | `collect.py` AST pass | 0 | 66 files, 0 syntax errors |
| L2 collection | `PYTHONPATH=<harness>/guard … .venv/bin/python <harness>/collect.py OUT.json` | 0 | 648 collected, 8 import blockers, 0 guard events, 0 file changes |
| L3 safe unit | `run_module.py … test_step9_58a_r1_namespace_allocator` | 0 | 8 pass, 1 C2R error, 0 guard events after guard fix |
| L4 targeted | `run_module.py … test_step9_35a_treatment_runner` | 0 | 23/23 pass, 0 guard events, 0 real-ledger reads |
| L5 full | `<harness>/run_all.sh <OUT outside repo>` | 66 × 0 | **650 collected / 628 pass / 4 fail / 18 error / 8 import-blocked modules** (reproduced twice) |
| L6 | r11 prerequisite review (§6) | — | NOT READY |

Per-item outcomes are in `step9_63c_r5c10ab_test_results_matrix.json`.

## 5. Remaining Blockers

1. **C2/C2R (8 modules, 14 methods):** these need the formal r11 pointer and freeze, or an approved change to
   the frozen adapter to resolve identity lazily. A fake pointer, r10 fallback or import-time mock is not
   acceptable.
2. **C3, C4, C5, C6 (8 methods):** these need human contract decisions: retire, re-scope to archival
   fixtures, or update pinned historical manifests. They must not be "fixed" by changing assertions.
3. **CI loader:** the workflow aborts on the first non-`ImportError` import failure. Proposed (not
   implemented): catch per-module import exceptions and record them as errors. This needs separate approval
   because it changes CI behaviour.
4. **Historical trace content integrity** stays `CONTENT_INTEGRITY_UNPROVEN` (no pre-r5c10l original exists).
5. **Untracked evidence:** many Step 9.5x–9.63c scripts, tests and evaluation artifacts are Git-untracked.
   Their integrity rests only on recorded SHAs, not on Git history.

## 6. r11 Freeze Readiness Assessment

| Prerequisite | Finding |
|---|---|
| 20 r11 members, consistent paths/SHA | 19/20 paths exist. The pointer is absent. r11 member SHAs are not finalized (matrix still says `NOT_IMPLEMENTED`/`NOT_CREATED`). |
| r10 history unchanged | YES. Manifest SHA unchanged; 17 unchanged members match; 3 approved deltas only. |
| Builder supports independent r11 identity | Yes: a versioned builder with exclusive-create publication that refuses an existing target. **Gap:** for changed resolver/consumer members it only checks "differs from r10" and does not pin reviewed SHAs (only the scanner is pinned). The freeze review must pin exact SHAs. |
| Builder dependency closure | **Gap:** `build_candidate()` imports `verify_frozen_inputs` from the r10 builder `scripts/build_step9_63c_r5c4_runner_freeze.py`. That file is replaced in r11 and therefore not an r11 member. It is currently unchanged (r10 SHA). |
| Resolver strict r11, no r10 fallback | YES. Static review plus passing `test_r11_pointer_missing_corrupt_and_r10_fallback_forbidden`. |
| Pointer creation mechanism | **MISSING.** No production writer or reviewed procedure for `step9_63c_r11_current_runner_identity.json` was found. |
| Producer/consumer provenance binding | YES (static + 12/12 r5c10j tests). Producer ID grammar `preflight-step9_63c_r5-r11-<hex32>` matches the consumer regex. The consumer verifies producer SHA, freeze SHA, registry claim and persistence before `adapter.run()`. |
| Registry uniqueness / non-replay | YES in synthetic tests (claim durability, concurrent single winner, failed ID non-reusable, tamper rejection). The production registry is not created, which is correct. |
| Authorization bound to exact r11 path+SHA | Consumer enforces `runner_freeze_path`/`runner_freeze_sha256`. **MISSING:** no r11 authorization issuer exists (the only issuer is hard-bound to r7). The old r10 authorization stays issued/unconsumed; retirement is pending separate approval. |
| Historical evidence integrity | Trace content `CONTENT_INTEGRITY_UNPROVEN`; Step 9.58 provenance gap remains documented. |
| Full regression green | NO: 22 non-pass and 8 import-blocked modules. |

**READY_FOR_R11_FREEZE_REVIEW = NO.** Minimum next steps, each needing separate approval:
1. A reviewed pointer-creation procedure.
2. Pin the exact SHAs for the resolver and consumer in the builder or review record.
3. Decide on the r5c4 builder dependency (make it a member or inline it).
4. Decide the C3–C6 test contracts.
5. A CI loader decision.

## 7. Rollback Plan

- Revert the C1 fix with `cp <backup> tests/test_step9_35a_treatment_runner.py`.
  - The backup is held in the session scratchpad with SHA `793070e7…0068`. Without it, reverse-apply
    `step9_63c_r5c10ab_c1_fixture_fix.diff` with `patch -R`.
  - Do **not** use `git checkout` on that file: it would also discard the earlier uncommitted +2-line fixture
    change.
- The new evidence files (`step9_63c_r5c10ab_*`) are additive. Delete them only with explicit approval.
- No frozen member, trace, authorization, ledger or registry needs rollback, because none changed.
