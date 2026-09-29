# Step 9.30a.1 — V4 Lineage Failure Forensics

Read-only forensic sidecar for `heldout-v4-step9_28-20260925-01`. Frozen formal inputs were re-hashed against the Step 9.30a input freeze before analysis. No benchmark file was loaded; no Agent, model, RAG, or V4 case was executed. Formal traces, case results, ledger, and benchmark were not modified.

## Findings

- Frozen `lineage_ready=false` count: **12/40**: V4-CA-02, V4-CA-04, V4-DA-01, V4-DA-03, V4-DA-06, V4-DA-09, V4-DA-10, V4-PD-03, V4-PD-04, V4-PD-05, V4-PD-06, V4-PD-10.
- Independent trace recomputation across all cases: **35 COMPLETE**, **5 INCOMPLETE**, **0 NOT_APPLICABLE**, **0 INDETERMINATE**.
- Among the 12 false cases: **7 COMPLETE with `CONTRACT_FALSE_NEGATIVE`**, **5 INCOMPLETE**.
- Root causes: **7 runner derivation false negatives** and **5 true execution-lineage omissions**; no persistence bug or not-applicable misclassification found.
- The 7 false negatives have earlier ASK action/candidate records in earlier turn snapshots and the cumulative serialized action history. The checker only receives the current loop result snapshot on later turns, so its per-turn validation cannot find earlier candidates. Trace evidence permits deterministic sidecar reconstruction.
- The 5 true omissions are diary cases whose READ_DIARY event, tool result, state update, source type, dependency and diary projection are persisted, but `semantic_provenance` is empty in every turn and final state. The required semantic root was never emitted; it cannot be recreated without inventing an ID. Their raw traces support answer/evidence adjudication but do not satisfy the frozen complete-lineage contract.
- Failures are not equivalent to “no tool used”: of the 12, **6** use no retrieval/diary tool, **1** uses RETRIEVE, and **5** use READ_DIARY. Every case has at least one action and a dependency; no case is NOT_APPLICABLE under the frozen root requirement.

## Contract and V3 comparison

`lineage_ready` is computed by `scripts/run_step9_28_v4_heldout.py::_case_result` as `all(turn.lineage.ready)`. `_lineage_validation` checks recorded action IDs, candidate-to-DECISION linkage, optional dependency link presence, precondition ID for HARD_PRECONDITION actions, tool-result and state-update IDs for RETRIEVE/READ_DIARY, plus goal, semantic, dependency roots and a nonempty action list. This is execution-trace completeness as observed by that helper, not an adjudication score or persistence-integrity check.

V4 and V3 call the same `_lineage_validation` helper from `scripts/preflight_step9_12_local.py`; the V3 runner applies the same accumulated-history/current-turn-snapshot pairing. This is a shared pre-existing derivation limitation, not a V3→V4 regression. V3 labels/scores were not used.

The seven false negatives can be represented in a derived sidecar without rerunning. The five diary traces have durable tool/evidence lineage but lack the frozen semantic root; do not mark them complete or repair their formal records. Protocol review is still required before any downstream adjudication treats them as complete.

## Status

- `TRUE_LINEAGE_FAILURE_COUNT = 5`
- `NOT_APPLICABLE_MISCLASSIFIED_COUNT = 0`
- `PERSISTENCE_BUG_COUNT = 0`
- `RUNNER_DERIVATION_BUG_COUNT = 7`
- `INDETERMINATE_COUNT = 0`
- `RAW_TRACE_SUFFICIENT_FOR_ADJUDICATION = YES (12/12)`
- `CASE_RESULT_SUFFICIENT = NO (12/12)`
- `LINEAGE_CAN_BE_RECONSTRUCTED_WITHOUT_RERUN = NO (5/12 strict-contract semantic roots absent)`
- `REMEDIATION_CLASS = DERIVED_SIDECAR_REPAIR_POSSIBLE`
- `READY_FOR_STEP9_30B_HUMAN_ADJUDICATION = NO`
- `V4_CASE_EXECUTED = 0`; `V4_SCORE_GENERATED = NO`; `AGGREGATE_GENERATED = NO`

Machine-readable details are in `step9_30a1_v4_lineage_forensics.json` and `step9_30a1_v4_lineage_case_matrix.jsonl`.
