# Step 8.8 — Critical State Semantics & Hard Precondition Boundary

## Scope and result

Only the minimal state-semantics and trace change was made.  Benchmark V2 was
not run; Benchmark V3 was neither created nor viewed.

| Validation | Before | After |
| --- | ---: | ---: |
| Step 8.7 controlled mechanisms | 18 / 19 | **19 / 19** |
| Regression suite | — | **111 passed, 0 failed, 0 skipped** |

The Step 8.7 trace file contains all 19 passing scenarios.  In particular,
`H_critical_state` now records `VALIDITY_CRITICAL_STATE`, `wake_time`, the
current goal, a validity reason, no resource alternative, and selected `ASK`.

## Minimal implementation

1. Added `validity_critical_missing` to `AdaptiveAgentState`, the loop snapshot,
   and evaluation serialization.
2. Defined a narrow counterfactual classifier in `preconditions.py`: only a
   personalized directional timing decision is upgraded from decision-relevant
   missing state to `VALIDITY_CRITICAL_STATE`.
3. Checked an authorized unread diary before emitting a state `ASK`; it produces
   `READ_DIARY` when it can satisfy the state dependency.
4. Made precondition observability explicit with `validity_reason` and
   `resource_alternative`.
5. Added semantic-boundary tests and a repeat-ASK guard.  An already-issued,
   unanswered equivalent question is recorded as `deferred`, then falls to the
   constrained bounded-answer path instead of asking again.

## Controlled paired checks

| Same missing information | Directional personalized goal | Educational/detail goal | Result |
| --- | --- | --- | --- |
| `wake_time` | `VALIDITY_CRITICAL_STATE` → ASK, or diary read | No state hard precondition | Goal-dependent PASS |
| sleep-onset / sleep-time context | Can be validity-critical | Definition/explanation remains answerable | Goal-dependent PASS |
| caffeine / nighttime awakenings / recent pattern | Not promoted by requirement rank alone | Not promoted | Optional/IV boundary PASS |
| diary-derived recent pattern | Authorized unread diary can substitute for direct ASK | Optional diary does not create a hard precondition | Resource-first PASS |

## Answers to the required boundary questions

1. **When is missing state a hard precondition?** Only if its absence makes a
   valid bounded answer impossible for the exact current goal.  A requirement
   field being “critical” is insufficient.
2. **When does it enter Information Value only?** When it changes detail,
   answer scope, or possibly direction but a bounded answer remains valid.
3. **How does resource alternative precede ASK?** A validity-critical dependency
   checks an authorized, available unread diary first.  That route returns
   `READ_DIARY`; only absent alternatives yield `ASK`.
4. **Was over-asking reintroduced?** No.  The regression suite includes both
   secondary-only bounded answers and an unanswered-equivalent-ASK case.  The
   latter becomes `deferred`, not a second ASK.

## Files to review

- `adaptive_agent/preconditions.py`: narrow classification, diary-before-ASK,
  and repeated-question deferral.
- `adaptive_agent/sufficiency.py`: separate missing-state categories.
- `adaptive_agent/runner.py` and `evaluation/recorder.py`: trace persistence.
- `tests/test_v1_2_1_preconditions.py`: paired semantic and no-over-asking tests.
- `evaluation/v1_2_1/step8_7_mechanism_traces.jsonl`: machine-readable 19/19
  validation evidence.
