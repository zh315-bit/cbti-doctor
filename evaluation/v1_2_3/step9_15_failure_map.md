# Step 9.15 Failure Map

## Scope

This is a trace-only analysis of the completed Step 9.14 run `clean-evaluation-v1_2_3-20260922-01`. No Agent code, Benchmark V2, scoring rubric, or Benchmark V3 was changed or accessed.

Observed: 40/40 completed, overall 68.275, 55 ASK (1.375/case), PD ASK 2.500/case, 0 critical failures, 3 harmful failures, and 26/55 ASK redundant or irrelevant (47.27%).

## A. Dependency Formation Failure

KQ-02 and KQ-05 first diverge when a knowledge/education request is represented as `PERSONALIZED_DECISION`. DA-07 first diverges when a diary-comparison request is represented without a `RESOURCE(sleep_diary)` dependency. In all three, `dependencies_considered` is empty, so no evidence or diary-resource candidate can be formed. The later ASK sequence is therefore downstream, not an independent ranking defect. KQ-04/KQ-10 show the related inverse error: an education goal receives an unavailable diary dependency.

This is an architecture-level Goal Semantics -> Dependency Formation defect. It affects safety, completion, and interaction cost simultaneously.

## B. Tool -> State Projection Failure

DA-01/02/03/04/05/08 all execute `READ_DIARY`, but the summary-shaped result fails the canonical diary contract before State projection. Source counts are known from the fixture (7, 7, 14, 7, 14, and 11 entries respectively), yet the runtime projection records null counts, empty dates, no provenance, and no State facts. DA-08 also has a 14-day window with known missing indices 4, 9, and 12; the invalid payload prevents preserving that partial coverage.

The validator's fail-closed result is safe: no diary value is fabricated. The failure is nevertheless architectural because the same projection contract breaks six cases before analysis and answer construction.

## C. Low-Value Information Acquisition

The frozen review classifies 8 ASK as necessary, 21 useful-but-optional, 14 redundant, and 12 irrelevant. Ten irrelevant ASK are directly explained by A (three KQ/DA primary cases). The remaining 16 low-value ASK occur in broader CA/PD flows and reflect a mixed chain:

1. effective requirements expose broad generic sleep fields even when the goal needs a narrower set;
2. missing-information detection treats absent State facts as unknown without enough provenance-aware recovery;
3. 18 of 26 low-value ASK still carry HIGH information-value/decision-impact metadata;
4. candidate ranking and policy select candidates that the human goal review does not consider necessary.

Therefore “Policy failure” is not a sufficient diagnosis. The first repair boundary should be requirement/dependency semantics and state availability; only then should value thresholds or ranking be tuned.

## Cross-class map

`Goal` -> **A: Goal Semantics / Dependency** -> `Requirements` -> **C: Missing detection / value estimation** -> `Candidate / Policy` -> `Answer`.

`READ_DIARY` -> **B: Tool/Fixture Contract** -> `State Projection` -> `Analysis` -> `Answer`.

The first path explains the three harmful cases and much of the ASK burden. The second explains safe but incomplete diary analysis. They are related by state and dependency contracts, but should not be collapsed into one bug.

## What not to repair now

- Do not optimize ASK/case toward zero or weaken hard preconditions.
- Do not loosen diary validation without preserving cardinality, date coverage, and provenance checks.
- Do not tune ranking or policy before fixing upstream goal/dependency formation.
- Defer retrieval-support mismatch (KQ-03/08/09) until evidence-to-claim binding is isolated.

