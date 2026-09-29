# Step 9.8f — Frozen Run Guard Implementation Report

## Outcome

The frozen-run guard now distinguishes immutable frozen-input preparation from
actual case execution. It uses an append-only execution-attempt ledger and a
read-only preflight. No Benchmark V2 case, model request, or Benchmark V3
access occurred during this implementation.

## Modified files

| File | Change |
| --- | --- |
| `scripts/frozen_run_guard.py` | New isolated ledger, frozen-hash validation, eligibility state machine, and durable append helpers. |
| `scripts/run_step9_8_frozen_evaluation.py` | Uses the guard; adds `--preflight` and requires an explicit `--authorization-id` for a real invocation. |
| `scripts/run_step8_9_v1_2_1.py` | Adds optional runner callbacks and an optional trace path so Step 9.8 can record attempt transitions without overwriting historical zero-byte trace containers. Default historical behavior is unchanged. |
| `evaluation/v1_2_2/step9_8_execution_attempts.jsonl` | New append-only ledger containing historical reconciliation entries. |
| `tests/test_step9_8f_frozen_run_guard.py` | 13 focused infrastructure tests. |

## Guard state machine

```text
immutable frozen manifest
        ↓ (hashes rechecked)
PREPARED
        ↓ (durable entry immediately before first real case)
STARTED
        ├─ no returned case result after a started case → FAILED_AFTER_PARTIAL_EXECUTION
        ├─ each returned case → append STARTED progress entry
        └─ 40 returned cases + trace → COMPLETED

failure before the first case begins → FAILED_BEFORE_FIRST_CASE
```

`STARTED`, `FAILED_AFTER_PARTIAL_EXECUTION`, and `COMPLETED` block automatic
runs. `FAILED_BEFORE_FIRST_CASE` is preserved but can become eligible only
under a new explicit human authorization and matching frozen hashes. Invalid or
unknown ledger state fails closed as `AMBIGUOUS`.

## Ledger schema and historical reconciliation

Each JSONL record has an `attempt_id`, `timestamp`, benchmark/scoring hashes,
status, `cases_started`, `cases_completed`, `model_calls_started`, first/last
case identifiers, and sanitized failure metadata. No environment variables or
API keys are read into the ledger.

The first three append-only reconciliation entries preserve, rather than edit,
prior history:

| Attempt | Migrated status | Cases started/completed | Valid results |
| --- | --- | --- | --- |
| historical Step 9.8 | `FAILED_BEFORE_FIRST_CASE` | 0 / 0 | false |
| historical Step 9.8b | `FAILED_BEFORE_FIRST_CASE` | 0 / 0 | false |
| reported local manifest-guard block | `FAILED_BEFORE_FIRST_CASE` | 0 / 0 | false |

Unrecoverable fields are `unknown`; the local block records
`model_calls_started=0`. Existing manifests, reports, and the zero-byte trace
container were not deleted, overwritten, renamed, or altered.

## Frozen integrity and read-only preflight

The preflight command performed no model invocation and reported:

```text
FROZEN_INPUTS = MATCH
RUN_STATE = PREPARED
PREVIOUS_VALID_RESULTS = NONE
EXECUTION_ELIGIBLE = YES
AUTHORIZATION_REQUIRED = YES
```

Verified hashes:

```text
Benchmark V2 = dfa9b9e5a12b0017fa68d344d01b313ebc29e583b933fbe1e93c125f55ecafd2
Scoring rubric = a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899
```

`PREPARED → STARTED` repeats the same two hash checks directly before the
runner enters the first real case. A mismatch aborts before that case and is
recorded as a before-first-case failure by the runner.

Run the preflight locally with:

```bash
.venv/bin/python -m scripts.run_step9_8_frozen_evaluation --preflight
```

It is read-only: it does not create an attempt, call a model, or run a case.

## Test results

| Check | Result |
| --- | --- |
| Step 9.8f focused guard tests | 13 passed / 0 failed |
| Step 9.6 S1–S12 | 12 passed / 0 failed |
| Step 9.7 I1–I8 non-writing integration invocation | 8 / 8 passed; lineage PASS |
| Non-external-model regression | 146 passed / 0 failed / 0 skipped |
| `tests.test_model_configuration` | NOT_VERIFIED; intentionally not run in this step |

Focused coverage includes manifest-only eligibility, both hash mismatches,
blocking STARTED/partial/COMPLETED states, renewed authorization after a
before-first-case failure, ambiguous-state fail-closed behavior, durable
pre-case `STARTED`, append-only writes, secret exclusion, and read-only
preflight.

## Scope declarations

```text
Agent behavior changed: NO
Benchmark changed: NO
Scoring changed: NO
Decision Policy changed: NO
Benchmark V2 run: NO
Benchmark V3 accessed: NO
```

## Readiness

```text
READY_FOR_LOCAL_PREFLIGHT = YES
READY_FOR_ONE_AUTHORIZED_FROZEN_RUN = YES
```

The second value means the infrastructure is eligible, not that a run is
automatically authorized. A real invocation still requires a new explicit
authorization identifier, working local external-model connectivity, and must
not be retried automatically after a started or partial execution.

