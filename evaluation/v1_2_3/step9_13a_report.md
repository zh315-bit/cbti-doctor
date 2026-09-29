# Step 9.13a — Final Authorization Blocker Resolution

## Result

The two infrastructure changes are implemented. The local real-model preflight still needs to be captured by the user on their Mac. No authorization ID has been issued and no formal evaluation has started.

## Changes

| File | Change | Input → output |
| --- | --- | --- |
| `scripts/preflight_step9_12_local.py` | Added `--capture` and exclusive, uniquely named JSON persistence. The existing readiness expression, model probe, production smoke, and lineage observer were not changed. | Actual local preflight result → timestamped `LOCAL_REAL_PREFLIGHT` JSON and printed artifact path. |
| `scripts/run_step9_12_frozen_evaluation.py` | Requires exact `--evaluation-id`, verifies the new Harness freeze and its Step 9.12b parent, and checks all frozen domains before an attempt and again before case 1. Preserves the append-only ledger, per-case trace, and failure path. | Evaluation ID + authorization ID + frozen files + ledger → eligibility or fail-closed refusal; no run was requested. |
| `evaluation/v1_2_3/step9_13a_harness_freeze.json` | New independent Harness identity for the two changed scripts. Step 9.11 and Step 9.12b freeze files remain intact. | Frozen file hashes → current Harness aggregate. |
| `tests/test_step9_13a_authorization_infrastructure.py` | Offline capture, secret exclusion, identity, freeze mismatch, and one-shot guard checks. | Synthetic test inputs → assertions only; no model or case execution. |

These changes sit outside the Adaptive Agent Loop. They neither alter the loop's input nor its selected actions.

## Captured artifact contract

The user command is:

```bash
.venv/bin/python -m scripts.preflight_step9_12_local --capture
```

The command runs the existing local real-model probe and synthetic production smoke, then writes a unique JSON file under `evaluation/v1_2_3/`. It records `preflight_type=LOCAL_REAL_PREFLIGHT`, UTC timestamp, evaluation ID, Agent/Harness/Benchmark/Scoring hashes, the requested gate fields, and whether V2/V3 were accessed. It contains only the boolean `credential_present`, never the key. Failed preflights are persisted as failures rather than upgraded to PASS. The earlier Step 9.12 FAIL artifact is not overwritten.

No local real-model preflight was run during Step 9.13a, so no new genuine PASS artifact exists yet.

## Frozen identity

| Domain | SHA-256 | Result |
| --- | --- | --- |
| Agent aggregate | `ee914db7b8b5538c5607fdff34cff9083f6d069d50cf342964ae91c8a6446927` | MATCH |
| Benchmark V2 file | `dfa9b9e5a12b0017fa68d344d01b313ebc29e583b933fbe1e93c125f55ecafd2` | MATCH; 40 cases |
| Scoring aggregate | `f742a8f8af7c8747818dadad81621c15d12d74f50538019913dfe18ab53bf59b` | MATCH |
| Current Harness aggregate | `8bc271bebc1c5da5351d517e2bb4a0d1a99fda3de1b713a6197b12f81fad70c7` | MATCH |

The runner checks the new Harness freeze, its parent file SHA-256, the Step 9.11 Agent/Benchmark/Scoring aggregates, and the current on-disk files. It requires `--evaluation-id clean-evaluation-v1_2_3-20260922-01`. The `STARTED` ledger entry still precedes the first case. A previously used authorization ID is rejected; ambiguous or unreadable attempt history fails closed.

## Offline verification

- Step 9.13a focused tests: **8 passed**.
- Step 9.12b observer tests: **8 passed**.
- Entire non-external-model regression excluding `tests.test_model_configuration`: **168 passed, 0 failed, 0 skipped**.
- `tests.test_model_configuration`: **NOT_VERIFIED**, not counted as passed.
- Direct read-only frozen identity check: Agent, Harness, Benchmark, Scoring, and combined identity **MATCH**.
- Formal attempt ledger: absent. Valid case traces/results: none.

During the initial focused-test draft, one synthetic authorization string did not match its mocked prior ledger entry and entered runner initialization. It was interrupted during dependency import, before a case or model call. The only resulting trace was empty; test-created capture files and the empty trace were removed. The test now explicitly asserts that the base runner is never called. No valid Benchmark result or attempt ledger entry was produced.

## Current gate

```text
PREFLIGHT_ARTIFACT_SUPPORT_READY = YES
RUNNER_EVALUATION_ID_BINDING = PASS
CURRENT_HARNESS_FREEZE_BINDING = PASS
AGENT_BEHAVIOR_CHANGED = NO
BENCHMARK_CHANGED = NO
SCORING_CHANGED = NO
READY_FOR_LOCAL_PREFLIGHT_CAPTURE = YES
READY_FOR_AUTHORIZED_RUN = NO
```

The user must execute the local capture command and return its generated artifact for review before a formal authorization can be considered.
