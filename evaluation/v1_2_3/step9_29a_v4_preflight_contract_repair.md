# Step 9.29a — V4 preflight contract reconciliation

## Proven data flow

The Step 9.28 runner preflight writes canonical `ready_for_final_authorization` from its aggregate preflight gate and canonical `benchmark_v4_accessed_by_agent: false` because it never sends a V4 case to the Agent. The recovery producer computed the same readiness gate and had no V4 evaluation path, but called its fields `ready_for_v4_final_authorization` and `benchmark_v4_accessed_for_evaluation`.

Thus the mismatch was naming-only: neither form signals authorization issuance, and both access fields assert the same local-preflight safety invariant. The reconciled recovery producer emits both forms from the same two booleans. The runner consumer accepts either complete spelling, but rejects missing, non-boolean, readiness-false, access-true, or conflicting simultaneous values.

## Freeze lineage

The runner changed, so `step9_28_v4_runner_freeze.json` is retained as superseded and no longer claims to match the runner. `step9_29a_v4_runner_freeze.json` binds the new runner hash, and `step9_29a_v4_evaluation_infrastructure_identity.json` records the limited infrastructure identity change. No Agent, V4 benchmark, scoring, metrics, or evaluation semantics changed.

## Next permitted action

The new recovery-preflight command is recorded in the JSON audit but was not run in this step. It must create a fresh artifact before any later authorization audit. This step issued no authorization and created no attempt, ledger, V4 answer, or score.
