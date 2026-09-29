# Step 9.9 — Post-Frozen-Run Recovery Protocol Design

## Immutable historical record

The original Step 9.8 experiment remains permanently distinct:

```text
FROZEN_RUN_CONSUMED
FAILED_AFTER_PARTIAL_EXECUTION
EVALUATION_HARNESS_FAILURE
CASES_STARTED = 1
CASES_COMPLETED = 0
VALID_CASE_RESULTS = NO
```

Its ledger records, manifests, zero-byte trace, and audit reports must not be
deleted, changed, renamed, or represented as a successful run. No later result
may be called a Step 9.8 rerun or attributed to the original frozen attempt.

## New experimental identity

After a separately reviewed harness repair, the next possible experiment is:

```text
Step 9.10 — Benchmark V2 Recovery Evaluation
```

It is a new, independently authorized evaluation—not a continuation of Step
9.8. Its immutable evaluation identity must include:

| Field | Requirement |
| --- | --- |
| `evaluation_id` | New unique recovery-evaluation identifier. |
| `authorization_id` | New explicit human authorization; never reuse Step 9.8's identifier. |
| `attempt_id` | New unique append-only attempt identifier. |
| `parent_failure_reference` | Step 9.8 attempt id, audit path, and `EVALUATION_HARNESS_FAILURE`. |
| `benchmark_sha256` | Frozen V2 hash. |
| `scoring_sha256` | Frozen rubric hash. |
| `agent_source_sha256` | Manifest for all relevant Agent files. |
| `harness_source_sha256` | Manifest for the repaired evaluation runner/harness files. |
| `ledger_path` | New recovery ledger; never append recovery entries to the consumed Step 9.8 ledger. |

The recovery ledger should be append-only and independent, while linking back to
the original failure through `parent_failure_reference`.

## Recovery eligibility gate

A recovery evaluation is eligible only when every item is independently
verified before the first case:

1. Step 9.8 has a completed audit classifying the failure as an evaluation
   harness failure.
2. Benchmark V2 SHA-256 matches the frozen value.
3. Scoring rubric SHA-256 matches the frozen value.
4. Relevant Agent behavior source hashes match the declared recovery baseline;
   any difference is a disclosed experimental confound, not a silent change.
5. The only intentional code changes are within the stated evaluation-harness
   boundary.
6. The harness fix passes targeted recursion/wiring tests and regression tests.
7. Equivalence checks show unchanged Agent input/output semantics, tools,
   sessions, fixtures, scoring, and case release rules.
8. No case-specific branch or workaround is present.
9. Benchmark V3 has not been accessed.
10. A new human authorization is recorded after all previous checks pass.

Any mismatch, unknown result, stale `STARTED` recovery attempt, partial result,
or absent authorization fails closed. It does not fall back to the Step 9.8
ledger and does not cause automatic retry.

## Minimal harness-fix boundary (design only)

The known defect is a wrapper self-reference:

```text
wrapper state_view()
→ base.state_view()
→ base.state_view has been replaced by wrapper
→ recursion
```

The permitted minimal repair is to capture the original callable before any
assignment and have the wrapper call that captured callable, never the patched
module attribute. This is a trace-serialization boundary repair only; it must
not alter Agent State contents, decision behavior, tool calls, answer text,
case inputs, or scoring.

Before implementation, audit each mutable hook using this checklist:

| Hook | Required audit question |
| --- | --- |
| `state_view` | Does the wrapper call an immutable original callable rather than a patched module attribute? |
| recorder hooks | Does a callback wrap only recording and avoid recursive recorder dispatch? |
| `before_case` | Is it invoked once before the real case and unable to alter case data or Agent State? |
| `after_case` | Does it observe a completed result without re-entering the runner? |
| trace callbacks | Are callbacks one-way serialization, with no callback-to-runner recursion? |
| ledger callbacks | Can they append status without invoking the Agent, runner loop, or model? |

## Scientific interpretation after recovery

The original Step 9.8 supplies no performance finding. A valid Step 9.10
recovery evaluation could be reported as a **post-failure controlled Benchmark
V2 evaluation** only if the eligibility gate passes. Every report must retain
the disclosure that the original frozen attempt was consumed by an evaluation
harness failure before valid results existed.

With identical Benchmark, rubric, fixtures, and evaluation definitions,
Step 8.9 V1.2.1 and Step 9.10 may be compared on:

```text
Overall; ASK/case; PD ASK/case; RETRIEVE/case; READ_DIARY/case;
turns/case; steps/case; critical/harmful failures; ASK-quality rates;
dependency failures; Tool → State projection failures; lineage completeness.
```

The comparison must separately manifest Agent version/architecture and harness
version. No metric is calculated by this design document.

## Development-set limitation

Benchmark V2 is a development/regression benchmark because it has already
informed multiple rounds of analysis. Neither a recovery result nor a comparison
with Step 8.9 establishes held-out generalization, clinical effectiveness, or
final system performance. Such claims require a separate held-out benchmark;
Benchmark V3 is only named here as a future boundary and is neither accessed nor
designed in this step.

## Required staged follow-up

```text
Step 9.10a  Evaluation Harness Minimal Fix
Step 9.10b  Harness Equivalence + Regression Validation
Step 9.10c  Local Preflight
Step 9.10d  One Authorized Recovery Evaluation
```

These are deliberately separate approvals. Passing one does not authorize the
next.

