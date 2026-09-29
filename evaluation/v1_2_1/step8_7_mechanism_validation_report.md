# Step 8.7 — V1.2.1 Preconditions & State Integrity Mechanism Validation

## Result

**19 scenarios; 18 passed; 1 failed.** No Agent was modified, no Benchmark V2
was run, and no Benchmark V3 was created or viewed.

| Area | Result |
| --- | --- |
| Evidence preconditions | PASS: absent evidence produces RETRIEVE; existing/optional evidence does not. |
| Resource preconditions | PASS: authorized+available unread diary produces READ_DIARY; unavailable/unauthorized does not. |
| Cost/diminishing/stop precedence | PASS: evidence/resource required action survives five ASK and cannot fall through to ANSWER. |
| Projection integrity | PASS: normal, missing-value, non-consecutive, range and distinct same-date entries preserve count/dates/provenance. |
| Fail-closed projection | PASS: cardinality/date mismatch is invalid and writes no diary facts. |
| Information Value regression | PASS: 15 existing V1.2/V1.2.1 mechanism tests pass. |
| Observability | PASS for EVIDENCE/RESOURCE and IV fields; see Critical State gap below. |

## Failure

`H_critical_state` failed. A genuinely decision-changing missing `wake_time`
correctly selected `ASK`, but `preconditions_considered` was empty: it travelled
through the existing Information Value candidate path instead of an explicit
`CRITICAL_STATE` precondition. This is not an acquisition outcome failure, but
it fails the requested two-layer trace semantics. No code was changed here.

## Boundary result

The evidence/diary pair demonstrates that Hard Preconditions are distinct from
HIGH Information Value: they return a sole required action before value/cost.
Optional diary and detail-only state do not automatically create a precondition.
The remaining ambiguity is whether CRITICAL_STATE should be a true hard
precondition or remain a narrow, IV-governed decision-relevant ASK; current code
and documentation are inconsistent on this point and need an explicit design
decision before implementation.

All trace records are in `step8_7_mechanism_traces.jsonl`; the sole failed
scenario is retained rather than normalized away.
