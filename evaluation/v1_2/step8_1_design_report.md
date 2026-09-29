# Step 8.1 Information Value Design Report

Date: 2026-09-20

## Scope

Design and offline analysis only. No Agent behavior, Benchmark V2, rubric, or
historical result was modified. No Agent or Benchmark V2 rerun was performed.

## Proposed Ordinal Information Value

Each remaining fact receives `HIGH`, `MEDIUM`, `LOW`, or `NONE` from six
interpretable dimensions: decision impact, current uncertainty, answer-scope
impact, acquisition cost, resource alternatives, and redundancy.

The core counterfactual test is: *if a plausible value of this fact were known,
could the next action or bounded answer scope change?* Decision-changing facts
default to HIGH; answer-scope-changing facts to MEDIUM/HIGH; detail-only facts
to LOW; redundant or irrelevant facts to NONE. Approximate/range values lower
uncertainty but do not automatically create a refinement ASK.

Retrospective classification of the 112 V1.1 ASK actions:

| Prior label | Proposed value | Count |
|---|---:|---:|
| necessary | HIGH | 21 |
| useful-but-optional | MEDIUM | 9 |
| redundant | NONE | 39 |
| irrelevant | NONE | 43 |

No action was classified LOW in the coarse retrospective because the frozen
trace labels do not preserve enough semantic detail to distinguish every
detail-improving ASK from an irrelevant one. V1.2 should add that distinction
before implementation.

## Proposed Acquisition Cost

`ASK` starts at MEDIUM and rises with previous ASK count, repeated target,
cognitive burden, and unresolved prior answers. `RETRIEVE` is MEDIUM for tool
and latency cost. `READ_DIARY` is LOW when available/relevant and unavailable
otherwise. `ANSWER` has non-zero risk cost: uncertainty, grounding, and
personalization risk increase when the answer is more specific.

The decision is not “minimize ASK”; it is to compare information value against
acquisition cost and answer risk. A later ASK must clear a higher ordinal
threshold than an earlier ASK, without hard-coding a fixed maximum count.

## Stop Rule

Stop gathering when no remaining fact has HIGH value, or when MEDIUM value does
not change answer scope enough to justify its cost and answer risk. Missing
information may remain while ANSWER is selected with a bounded limitation.

## Frozen V1.1 Evidence

V1.1 had 112 ASK (2.800/case), 34.8% redundant and 38.4%
irrelevant under Step 7.5's trace-only labels. PD remained the bottleneck at
5.333 ASK/case and 9 six-ASK-limit cases. This supports designing an
information-value layer, but does not prove that the proposed model improves
behavior.

## Candidate V1.2 Flow

```text
Goal → State → Sufficiency → Remaining Information
     → Information Value (HIGH/MEDIUM/LOW/NONE)
     → Cost and answer-risk comparison
     → ASK / RETRIEVE / READ_DIARY / ANSWER
```

V1.1 primarily asks whether a field is missing and decision-relevant. V1.2
would add counterfactual value, explicit acquisition cost, resource alternatives,
diminishing returns, and a stop rule before candidate generation/selection.
This is a design proposal only.

## Relationship to Calibrate-Then-Act

The design is conceptually inspired by Calibrate-Then-Act: estimate whether
additional information is worth acquiring before acting, and account for
uncertainty and action cost. CBTI-Doctor currently implements interpretable
heuristics, State/provenance, sufficiency, and bounded answers. It does not
implement CTA, calibrated expected utility, learned probabilities, or a
validated calibration procedure. The proposed ordinal values remain heuristic.

## V1.2 Evaluation Plan

Benchmark V2 is now a development/regression set, not final independent
evidence. After V1.2 development is frozen, create and freeze a held-out
Benchmark V3, or preregister a leakage-resistant protocol. Compare V1.1 vs V1.2
on task score, ASK/case, redundant/irrelevant/necessary/useful ASK rates,
six-ASK-limit cases, critical failures, premature-answer rate, and resource use.
Do not create V3 in Step 8.1.

## Limitations

The retrospective labels are coarse and inherited from Step 7.5. The frozen
trace does not expose rejected ASK candidates, so gate-blocking and marginal
value cannot be measured directly. No causal claim, calibration claim, or
general superiority claim is supported.
