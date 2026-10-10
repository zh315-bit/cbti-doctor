# Step 9.63c-r5c5b — Unified Fail-Closed Lifecycle Reducer Repair

**Status: `PASS_LIFECYCLE_REDUCER_REPAIR_OFFLINE_VALIDATED`**

The legacy active scanner treated issuance-time manifest status as current state and omitted the authoritative transaction journal. A single reducer now combines the immutable issuance manifest, retirement ledger, transaction journal, attempt-consumption ledger, and namespace reservation marker. Contradictory or malformed evidence reduces to `INCONSISTENT_FAIL_CLOSED`; it is never executable. The reducer does not reconcile or resume a transaction.

The r7 target now derives to `COMMITTED_BURNED_PRE_CASE_NON_REUSABLE` because its valid journal ends at `COMMITTED` with `authorization_irreversibly_burned=true`, and its exact marker binds the same transaction. There is no attempt claim or case start. The r8 target derives to `RETIRED_UNCONSUMED_NON_REUSABLE` from its valid retirement event. Both are excluded from active authorization. Active executable count is 0.

The manifest and transaction journal were not modified; their SHA-256 values remain `1514438d0afe23a39de2a696e9ea5bd97faac4dd546a88cdbd7b91f450046345` and `76afd557e4559c50090e9e4939a2e52746cbaefff1d4d6bd886206798b2e96fa` respectively. Retirement ledger history was not appended or rewritten. Historical pin count is 55 with 0 mismatches under the frozen 1,161-byte prefix model. Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`.

The lifecycle reducer and all executable consumers are included in new r10 freeze `step9_63c_r5c5b_runner_freeze_r10.json` (SHA-256 `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693`, 20 members). r9 remains byte-preserved but is superseded for new authorization. Current pointer resolves to r10 and all freeze members match.

Offline validation passed: 21 new synthetic reducer tests plus 47 focused issuer/preflight/formal-entry tests (68 total), 0 failures, 0 errors. Python compilation passed. V3 Agent, V4 benchmark, scoring, metrics, and evaluation semantics were not modified.

No authorization was issued; no attempt or namespace was created/reserved; no preflight, HTTP, model, Agent, RAG, V4 case, adjudication, aggregation, comparison, or V5 access occurred. The committed r7 transaction remains preserved and must not be resumed. This step stops here; any fresh authorization requires a separate authorized step.

Full audit: `step9_63c_r5c5b_lifecycle_reducer_repair_audit.json`. Synthetic test matrix: `step9_63c_r5c5b_lifecycle_reducer_test_matrix.json`.
