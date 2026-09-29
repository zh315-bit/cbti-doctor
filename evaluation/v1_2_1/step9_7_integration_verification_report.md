# Step 9.7 — End-to-End Integration & Lineage Verification

## Scope

No Agent behavior, Decision Policy, Information Value/Cost, Answer Generation,
Diary Contract V2, Benchmark, or scoring rule was changed. Benchmark V2 was
not run; Benchmark V3 was not accessed.

I1–I8 execute the production `create_app()` `/api/chat` route definition from
`main_flask.py` with injected real `AdaptiveChatService`, session persistence,
`AdaptiveAgentLoop`, State, requirements, DependencyResolver, preconditions,
candidates, policy, and State updates. Understanding, tools, and answer output
are deterministic synthetic fixtures; no external model or health data is sent.

The complete `main_flask` module import did not return within this environment's
30-second window, likely before factory construction because of legacy module
initialization. Live WSGI/full-module import is therefore **NOT_VERIFIED**. The
executed route function is parsed from the production source; this limitation
does not mean the tested route/service/loop path was replaced by a parallel
workflow.

## I1–I8 results

| ID | Result | Verified behavior |
| --- | --- | --- |
| I1 | PASS | Wrong personalized signal + knowledge goal: EVIDENCE → RETRIEVE → SATISFIED → ANSWER, no stale ASK. |
| I2 | PASS | Directional personalized goal with missing wake time: VALIDITY_STATE → ASK. |
| I3 | PASS | Follow-up merges State, resynchronizes requirements, does not repeat wake-time ASK. |
| I4 | PASS | EVIDENCE lifecycle has no duplicate RETRIEVE on later API turn. |
| I5 | PASS | RESOURCE → READ_DIARY → valid State projection → SATISFIED. |
| I6 | PASS | Known unavailable diary → UNAVAILABLE bounded answer; no retry or fabricated fact. |
| I7 | PASS | Goal change resets old effective requirements/dependencies. |
| I8 | PASS | Supplied useful optional facts reach State/answer; absence does not cause automatic ASK. |

**Integration scenarios: 8 / 8 PASS.** Full route responses, tool counts, final
State and State histories are in `step9_7_integration_scenarios.json` and
`step9_7_integration_traces.jsonl`.

## Lifecycle results

* **Dependency lifecycle: PASS.** I1/I4 prove EVIDENCE required→satisfied and
  no duplicate retrieval; I5 proves valid diary RESOURCE→satisfied; I6 proves
  unavailable resource does not enter data State; I2 retains VALIDITY_STATE.
* **Effective Requirements lifecycle: PASS.** I3 proves follow-up resync, I7
  proves new-goal reset, and I8 proves optional facts are retained without
  mandatory acquisition.

## Lineage / observability audit

The audit checked every captured route-turn snapshot for:

```text
goal_id → semantic_id → dependency_id → precondition_id → candidate_id
→ action_id → tool_result_id → state_update_id
```

It checks dependency/semantic, precondition/dependency, candidate/action and
tool/state-update joins, as well as precondition counterfactual observability.
Mandatory candidates report `precondition_forced_action`; uncomputed
counterfactual values remain `not_available`.

**Lineage audit: PASS. Observability gaps: 0.** Each final action is explainable
from its goal semantics, dependency/precondition or optional candidate origin,
selection ID, and State/tool update lineage.

## Regression

| Suite | Result |
| --- | --- |
| I1–I8 route integration runner | 8 / 8 passed |
| S1–S12 + Step 9.3 dependency/Diary Contract + Step 8.x focused mechanisms | 40 passed / 0 failed / 0 skipped |
| Non-external-model regression | 133 passed / 0 failed / 0 skipped |
| `tests.test_model_configuration` | **NOT_VERIFIED** — no result within 30 seconds |

## Defects and required declarations

**Agent integration bug: NO.** No scenario or lineage assertion failed.

The whole-module/live-process limitation is an independent **NOT_VERIFIED**
environment/startup issue. Its blocked layer is legacy module initialization;
it is not a Dependency, effective-requirement, Policy, or lineage divergence.
It must not be reported as a pass.

* Agent modified: **NO**
* Benchmark V2 run: **NO**
* Benchmark V3 accessed: **NO**
* Decision Policy optimized: **NO**
* Information Value / Cost optimized: **NO**
* Answer Generation modified: **NO**
