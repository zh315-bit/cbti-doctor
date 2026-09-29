# Step 9.12b — Minimal Trace Observer Fix Report

## Change

Changed only `scripts/preflight_step9_12_local.py` and added its focused observer tests. The synthetic smoke still invokes the production Flask `/api/chat` service path. Its recorder is replaced only for that synthetic request with an in-memory capture recorder, so the observer can inspect the real `LoopResult.state_history` without producing a Benchmark record.

The observer now resolves a candidate-to-action link from the recorded `DECISION.chosen_action.candidate_id` and `action_history.selected_candidate_id`. It obtains a precondition only from that action's source candidate and requires it only where `origin=HARD_PRECONDITION`. Tool actions additionally require matching `tool_result_id` and `state_update_id` through `lineage_events.source_action_id`.

No identifier is generated or repaired. A missing real link remains null and appears in `missing_required_lineage`, causing a fail-closed smoke result.

## Conditional lineage semantics

`SATISFIED_ANSWER` and other policy-selected answers require a real candidate/action link but do not require a stale active precondition or a tool result. A hard-precondition tool action requires its precondition; a tool action requires its tool-result/state-update linkage. This changes only observer interpretation, not state retention or the Agent's action path.

## Focused validation

`tests/test_step9_12b_trace_observer.py`: **8 passed**.

- T1 recovers a real candidate from history after final State is refreshed.
- T2 accepts a satisfied ANSWER without an active precondition.
- T3–T5 enforce precondition/candidate/tool contracts conditionally.
- T6 proves no fake IDs are created.
- T7 fails closed for a genuinely missing link.
- T8 proves the observer does not mutate State/history or action path.

Additional offline checks: S1–S12 **12 passed**; I1–I8 integration scenarios **8/8 PASS** with lineage audit PASS (executed from a temporary output directory so historical artifacts remained untouched); integration trace audit tests **6 passed**; combined focused test modules **26 passed**; non-external-model suite (excluding `tests.test_model_configuration`) **160 passed, 0 failed, 0 skipped**. `tests.test_model_configuration` remains **NOT_VERIFIED** and is not counted as passed.

## Harness freeze

Step 9.11's Agent freeze was not changed. A separate Harness-only record, `step9_12b_harness_freeze.json`, records the old harness hash and the replacement aggregate. It changes only the preflight observer file. Agent, Benchmark V2, and scoring hashes must remain matched for a future local recheck.

## Safety and execution status

No DeepSeek/model request was made. Benchmark V2 was not executed and Benchmark V3 was not accessed. This change is observability-only; it does not authorize an evaluation run.
