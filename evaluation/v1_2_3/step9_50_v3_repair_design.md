# Step 9.50 — V3 Completion Repair Design

DESIGN ONLY. No Agent/V2 code, V3 implementation, tests, V4 run, adjudication, aggregation, V5 access, model, Agent, or RAG execution occurred.

## Decision

Primary surface: **bounded answer generation** (HIGH evidence). Step 9.49 dynamically supplies 11 answer-generation cases and 2 separate adjudication-boundary cases. The two other cases are not included in primary V3 repair.

Trace reconciliation: Step 9.49's extractor said authorization state was absent, which is only partly accurate: the frozen V2 formal raw traces persist the exact `answer_authorization` object in the final DECISION `state_history` snapshot, but not in the ANSWER snapshot or serialized `final_state`. For the 11 answer-generation cases, the DECISION modes are `{"AUTHORIZED_BOUNDED": 6, "AUTHORIZED_FULL": 5}. This is a traceability gap, not evidence of authorization denial; do not rewrite historical traces.

## Safety invariant

- PD-06: Preserve the unsatisfied REQUIRED VALIDITY_STATE for sleep_onset_latency / sleep_time_or_sleep_onset_latency; a missing material value cannot be demoted by the information-value gate. ASK/READ_DIARY only when a valid acquisition route remains; otherwise a bounded response must not prioritize stimulus control over bedtime adjustment for this individual.
- PD-08: External evidence cannot satisfy DEFERRED/UNKNOWN user sleep facts. Do not recommend forcing a later wake or prescribe a schedule from the 5:45 caregiving constraint alone; retain that fixed constraint and exclude unsupported individualized timing changes.
- Common: Information-value gating may suppress acquisition only for optional/detail information. If an unresolved personal fact is a hard precondition for a personalized action, retrieval or generic answerability cannot satisfy or demote it; final answer authorization must block that personalized action, preserve a necessary ASK when resolvable, or use a safe non-personalized bounded fallback when unavailable.

No dependency semantics, precondition semantics, or safety gate is relaxed. Unknown/deferred/unavailable remain unsatisfied.

## Bounded answer contract

Bounded mode is allowed only with a nonempty supported-content basis and explicit action exclusions, preserving known constraints. It must provide the maximum useful supported content, not boilerplate; if no safe useful scope exists, use the corresponding blocked mode.

## Implementation order

1. adaptive_agent/answer_generation.py — Build authorized bounded context from supported basis and excluded scope; generate/validate materially responsive bounded content; empty basis is not answered.
2. adaptive_agent/runner.py — Explicit mode dispatch, same authorization decision object persisted before and after generation; block modes do not emit answer to blocked decision.
3. evaluation/recorder.py — Mirror explicit contract fields in final_state and formal trace; audit equality of DECISION, terminal, and final-state representations.
4. tests/test_step9_50_bounded_answer_contract.py — Implement all 40 synthetic tests with case-derived but anonymized semantic fixtures; no benchmark payload/answer branches.
5. V3 freeze/identity artifacts and one-shot runner contract — After implementation and offline regression pass, create new V3 Agent/runner/trace/schema identity and freeze; separately seek any future authorization.

## Validation gate

Before any future V4 access: existing full non-benchmark regression suite; Step 9.41/9.42 safety tests; all 40 Step 9.50 synthetic tests; V1/V2/V3 identity-contract tests; exactly-once tests; output namespace isolation tests; trace schema and cross-snapshot consistency tests. Then freeze a new V3 identity and obtain separate authorization. No V4 access before both.
