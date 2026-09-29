# Step 9.8g — Frozen Run Recursion Failure Audit

## Audit scope

This is read-only. No code, ledger, manifest, Agent, Benchmark, scoring file, or
trace artifact was changed. No Benchmark case was rerun, no model was called by
this audit, and Benchmark V3 was not accessed.

## Authorized attempt and ledger evidence

Authorization reference: `step9_8_local_frozen_20260921_auth01`

| Field | Audited value |
| --- | --- |
| `attempt_id` | `attempt_9915d68189f343f8996fc412d4efec53` |
| terminal `status` | `FAILED_AFTER_PARTIAL_EXECUTION` |
| `cases_started` | `1` |
| `cases_completed` | `0` |
| `model_calls_started` | `unknown` |
| `first_case_id` | `V2-KQ-01` |
| `last_completed_case_id` | `unknown` |
| `failure_stage` | `during_or_after_case_execution` |
| `failure_type` | `RecursionError` |
| `STARTED` record | YES, appended before the first case |
| failure/finalization record | YES, terminal failure record appended |

The ledger is decisive for run-state classification: the attempt is not a
before-first-case failure because its durable `STARTED` record has
`cases_started=1`. Its final record is already an existing legal frozen-run
state; this audit did not append or change it.

## Raw trace and result audit

| Artifact / event | Evidence-based status |
| --- | --- |
| Attempt raw trace file | Exists: `step9_8_attempt_attempt_9915d68189f343f8996fc412d4efec53_raw_traces.jsonl` |
| Raw trace records | 0 lines / 0 bytes |
| Case trace | none |
| Persisted model response | none |
| Persisted state transition | none |
| Score / metrics / ASK quality / lineage result | none |
| Valid case result | NO |

The terminal observation `Loading weights: 100%` is not a persisted model-call
record. It establishes neither an external model request nor a returned model
response. With the ledger's `model_calls_started=unknown` and no trace/result
artifact, the following claims are not determinable from the required evidence:

```text
MODEL_CALL_STARTED = UNKNOWN
MODEL_CALL_COMPLETED = NOT_VERIFIABLE
CASE_COMPLETED = NO
```

## Frozen-run consumption decision

```text
ATTEMPT_STATUS = FAILED_AFTER_PARTIAL_EXECUTION
CASES_STARTED = 1
CASES_COMPLETED = 0
MODEL_CALLS_STARTED = UNKNOWN
VALID_CASE_RESULTS = NO
FROZEN_RUN_CONSUMED = YES
```

This is not protocol ambiguity. Step 9.8f defines `STARTED` and
`FAILED_AFTER_PARTIAL_EXECUTION` as states that block automatic reruns. Because
the durable `STARTED` record predates the failure and says `cases_started=1`, the
attempt has entered consumed execution history even though it produced no valid
case result.

## Root cause localization

`FAILURE_CLASS = EVALUATION_HARNESS_FAILURE`

First divergence: `scripts/run_step9_8_frozen_evaluation.py` assigns
`base.state_view = state_view` before calling `base.main()`.

```text
target module state_view(state)
→ base.state_view(state)
→ target module state_view(state)     # because base.state_view was overwritten
→ … recursion until RecursionError
```

The concrete bindings are:

1. `scripts/run_step9_8_frozen_evaluation.py:22` defines the wrapper
   `state_view()` and reads `base.state_view(state)`.
2. `scripts/run_step9_8_frozen_evaluation.py:78` replaces that exact
   `base.state_view` binding with the wrapper.
3. `scripts/run_step8_9_v1_2_1.py:163` invokes `state_view(state)` while
   assembling the first turn trace. At that point its global resolves to the
   wrapper, which calls itself through `base`.

This occurs in evaluation trace construction, after the runner has registered
the first case as started, not in the production Adaptive Agent's Goal,
DependencyResolver, Policy, tools, or Answer Generation. It is therefore not
an Agent behavior failure and supplies no valid benchmark observation.

## Why prior tests did not catch it

The Step 9.8f tests validated the ledger/guard state machine in isolation. The
Step 9.7 integration scenarios exercise the production route directly and do
not install the Step 9.8 runner's `base.state_view = state_view` monkey patch.
No test executed the combined wrapper-binding plus first-case trace path, so the
self-reference was not observed before the authorized local run.

## Frozen integrity

| Check | Result |
| --- | --- |
| Benchmark V2 SHA-256 | `dfa9b9e5a12b0017fa68d344d01b313ebc29e583b933fbe1e93c125f55ecafd2` — MATCH |
| Scoring rubric SHA-256 | `a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899` — MATCH |
| Agent source files listed by the frozen manifest | MATCH current hashes |
| Agent modified after authorization | NO |
| Benchmark modified | NO |
| Scoring modified | NO |

## Final declarations

```text
FROZEN_INPUTS = MATCH
FAILURE_CLASS = EVALUATION_HARNESS_FAILURE
ROOT_CAUSE = state_view wrapper self-recursion caused by monkey-patching base.state_view
```

No remediation is proposed or implemented here, and no subsequent Benchmark
run is authorized by this audit.

