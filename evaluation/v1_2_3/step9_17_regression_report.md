# Step 9.17 — Regression Report

## Focused test groups

| Group | Result |
|---|---:|
| Step 9.17 synthetic Tool→State projection matrix | 20 passed / 0 failed |
| Combined Tool/State + Diary Contract + lineage + answer grounding + dependency + Agent Loop tests | 93 passed / 0 failed |
| Full non-Benchmark unittest discovery | 200 run: 198 passed / 2 failed / 0 skipped |

The 93-test focused command covered `test_step9_17_tool_projection`, `test_v1_2_2_dependency_contract`, `test_v1_2_1_preconditions`, `test_v1_2_1_mechanism_validation`, `test_answer_generation_grounding`, `test_v1_1_answer_tool_grounding`, `test_adaptive_loop`, `test_policy_refinement`, `test_step9_6_effective_requirements_lineage`, and `test_step9_4_integration_audit`.

## Full-suite failures

1. `test_step9_13a_authorization_infrastructure.AuthorizationInfrastructureTests.test_attempt_guard_blocks_started_and_reused_authorization`: expected historical runner preflight to remain eligible, but it is blocked because current Agent source no longer matches its old frozen identity.
2. `test_step9_13a_authorization_infrastructure.AuthorizationInfrastructureTests.test_current_harness_and_other_frozen_domains_match`: expected `agent_freeze_match=True`; current Agent source changed as authorized in Step 9.17, so the Step 9.11 historical Agent freeze correctly does not match the working tree.

Both failures concern historical freeze identity, not projection behavior. The old freeze records remain intact. No attempt was made to refresh/replace the baseline or to weaken these assertions.

`pytest` is not installed in this environment; repository tests were run with the project virtual environment's `unittest` runner. The full-suite run did not skip any tests. All focused projection and integration tests pass. Because the full suite has two failed assertions, overall `REGRESSION_STATUS=FAIL` pending a separately authorized decision about development-source versus historical-freeze test semantics.

## Scope verification

Benchmark V2 rerun: NO. Benchmark V3 accessed: NO. Agent policy, requirements, sufficiency, candidate generation, dependency formation, and answer medical strategy were not changed. Changes are limited to Tool result projection/State provenance, deterministic diary calculations, answer-context filtering for invalid diary projections, and tests/reports/learning record.
