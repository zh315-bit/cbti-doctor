# Step 9.58a-r1 — V3 Output Namespace Remediation

**Status:** `PASS_NAMESPACE_REMEDIATION_ONLY`  
**Created:** 2026-10-01 19:23:16 UTC

## Result

The Step 9.58b post-hoc attestation and its inventory/report/audit hashes verify. The post-hoc evidence is accepted for this infrastructure remediation only. The original Step 9.58 manifest, audit, report, and freeze remain absent; `ORIGINAL_STEP9_58_ARTIFACT_SET_COMPLETE=NO` and `STEP9_58_PROVENANCE_GAP=PRESENT_AND_DOCUMENTED` remain unchanged. No historical claim is relabeled as complete artifact integrity.

The Step 9.57 occupied output directory remains untouched and permanently non-reusable. Its ledger SHA-256 remains `10d3577bd59f886e5b5b79f23c8e911e117bfc52004eb234034f9314c2c5728e`; the empty result and raw-trace files retain SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

## Namespace allocation repair

The old runner used the frozen logical `evaluation_id` as its sole physical directory name. The new allocator derives a separate physical namespace key from the exact logical evaluation, authorization, and attempt IDs, then lays out output as:

`evaluation/v4_runs/<derived-namespace-id>/<frozen-evaluation-id>/`

The derivation uses the first 20 hex characters of SHA-256 over the three identities separated by NUL bytes. Before reserving, the allocator takes an exclusive filesystem lock and recursively scans historical ledgers and reservation markers for identity reuse. It then creates a reservation directory and marker exclusively, fsyncs the marker and relevant directories, and delegates exclusive attempt-directory/ledger creation to the unchanged parent runner. A collision, interrupted reservation, or repeated identity fails closed; there is no resume or automatic retry. The legacy occupied and Step 9.57 failed namespaces are explicitly forbidden. No case-specific runner or namespace logic was found.

The adapter is infrastructure-only and is frozen as runner revision r4 (`5c64ad7918703e9f2364d832963f39fbcd8bd45a7519a1771515b5d62bca4c87`); allocator SHA-256 is `e9ec6e25cf9d8f4899176ae7795445911e4b77c42048f8eb3ed515189a7b1288`. Historical ledger and reservation scans are recursive, so nested ledgers remain protected even if a reservation marker is absent. The r4 freeze explicitly supersedes the preserved r3 freeze for future authorization only. The Agent, benchmark, harness, scoring implementation/rubric, metric registry, one-shot rules, model/tool/RAG configuration, case set/order, and evaluation semantics are unchanged.

## Validation and boundary

The r4 read-only identity preflight passes all frozen identity checks. Twenty-one focused synthetic lifecycle/allocator tests pass with zero failures and zero errors, including pre-attempt absence, post-create/pre-first-case callback ordering and exact identity validation, occupied/failed namespace rejection, exact-identity non-reuse, nested historical ledger reuse rejection even without a marker, corrupted marker fail-closed behavior, and parallel duplicate allocation with exactly one winner. Test fixtures use temporary directories; no formal evaluation namespace was created or touched.

No authorization was issued or consumed; no attempt was created; no V4 case was executed; no model, Agent, or RAG case execution occurred. No adjudication, aggregation, comparison, or V5 activity occurred. `READY_FOR_FRESH_V3_AUTHORIZATION=YES` means only that the repaired runner is eligible for a separate authorization audit. It is not authorization or permission to run an evaluation.

Artifacts: `step9_58a_r1_v3_identity_contract.json`, `step9_58a_r1_v3_runner_freeze_r4.json`, `step9_58a_r1_v3_runner_preclearance.json`, `step9_58a_r1_v3_namespace_allocation_audit.json`, `step9_58a_r1_v3_namespace_lifecycle_test_report.json`, and `step9_58a_r1_v3_integrity_audit.json`.
