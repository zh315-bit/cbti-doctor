# Step 5.4 Comparison Validity & Failure Analysis Report

## Scope, data and arithmetic

This report is a **read-only analysis** of `step5_3-controlled-final-2026-09-19`. It did not rerun either system and did not change Fixed, Adaptive, Benchmark V1.1, or the scoring rubric.

The saved V1.1 means are Fixed **20.2** and Adaptive **88.3**. Their arithmetic difference is **+68.1**, rather than +67.9. All counts below are recomputed only from the saved ten-case JSONL traces and paired scores.

## Validity boundary

The experiment supports a comparison of observed behavior on these ten artificial V1.1 cases. It is not an architecture-neutral performance test, because Fixed uses a legacy LangGraph entrypoint and message history, while Adaptive uses `/api/chat` and structured state. Fixed also lacks `READ_DIARY`; the two diary cases are therefore a capability gap, not evidence that the Adaptive Decision Policy alone is superior. Token telemetry also uses different scopes and cannot establish end-to-end token-cost superiority.

## Case-level source of the score gap

“Primary driver” means the most direct trace-supported explanation, not a claim that a single component caused every point of the rubric difference.

| Case | Delta | Primary trace-supported driver | Additional observed contributors | Valid conclusion |
|---|---:|---|---|---|
| KQ-01 | +65 | workflow architecture / action selection | Fixed RETRIEVE was followed by five irrelevant personal ASK actions | Both could retrieve; Adaptive stopped at a goal-aligned answer. |
| KQ-02 | +66 | workflow architecture / action selection | Fixed asked four personal questions after retrieval | Same capability class; this supports less redundant Adaptive action sequencing. |
| CA-01 | +73 | state management + workflow architecture | Fixed did not turn query facts into a bounded answer path; Adaptive retrieved and answered | Supports better use of known facts, not policy-only causation. |
| CA-02 | +55 | workflow architecture / action selection | Adaptive also missed explicit facts, leading to two redundant asks | Adaptive still ended safely; its advantage cannot be wholly assigned to Policy. |
| PD-01 | +63 | workflow architecture + answer grounding | Fixed gathered four low-value fields after the one useful wake-time question, then made an unsupported individualized recommendation; Adaptive had one extraction-caused redundant ask | Supports a combined action-boundary/answer-boundary advantage, not a pure policy claim. |
| PD-02 | +56 | workflow architecture / action selection | Fixed continued six asks despite explicit timing facts; Adaptive redundantly asked latency due to extraction omission | Same capability class; supports large interaction-efficiency difference with an Adaptive upstream weakness. |
| PD-03 | +44 | workflow architecture / action selection | Adaptive has its own answer-grounding critical failure | Adaptive score lead is not a safety win in this case. |
| PD-04 | +65 | action selection / workflow architecture | Adaptive’s three asks are V1.1-acceptable; Fixed asked six fields but did not obtain the defined decision fields or answer | Supports goal-specific candidate selection advantage. |
| DA-01 | +97 | **capability_gap** | Fixed has no `READ_DIARY`; Adaptive reads available diary then answers | Do not attribute this gap to Adaptive Policy superiority alone. |
| DA-02 | +97 | **capability_gap** | Fixed cannot inspect/report unavailable diary resource; Adaptive reads unavailable result and limits answer | Do not attribute this gap to Adaptive Policy superiority alone. |

## Capability-matched subset

The eight non-DA cases are capability-matched at the action-interface level: both systems can converse and retrieve; neither needs a diary tool. This does **not** eliminate endpoint/state-architecture confounds, but removes the explicit `READ_DIARY` asymmetry.

| Existing-trace aggregation, 8 cases | Fixed | Adaptive | Delta |
|---|---:|---:|---:|
| Mean score | 24.5 | 85.4 | +60.9 |
| ASK / case | 5.25 | 1.25 | -4.00 |
| Tool calls / case | 0.50 | 0.50 | 0.00 |
| Turns / case | 5.75 | 2.25 | -3.50 |
| Steps / case | 6.25 | 2.75 | -3.50 |
| Critical failures | 1 | 1 | 0 |

The subset retains a large score difference without the diary capability gap. The traces support interpreting much of that remaining gap as different workflow/action sequencing and structured-state use. They do not isolate a numeric causal contribution from Decision Policy, Input Understanding, state management, or answer generation.

## Task-type analysis

| Task type | Fixed | Adaptive | Difference | Main reading |
|---|---:|---:|---:|---|
| KNOWLEDGE_QA | 34.5 | 100.0 | +65.5 | Capability-matched. Fixed retrieves but continues personal intake; Adaptive retrieves once then answers. |
| CAUSE_ASSESSMENT | 22.0 | 86.0 | +64.0 | Adaptive’s bounded re-evaluation helps, but CA-02 shows explicit-fact extraction still matters. |
| PERSONALIZED_DECISION | 20.75 | 77.75 | +57.0 | Smallest score gap. Adaptive asks fewer, more goal-related questions, but has extraction-caused redundant asks and one grounding critical failure. |
| DATA_ANALYSIS | 3.0 | 100.0 | +97.0 | Largest gap, primarily the documented `READ_DIARY` capability difference. |

- The smallest observed difference is **PERSONALIZED_DECISION (+57.0)**, not because Fixed performs well, but because Adaptive has two remaining upstream extraction failures and one grounding critical failure in this category.
- The clearest dynamic Action Selection evidence is KQ-01/KQ-02 and PD-04: the same broad interaction/retrieval capabilities exist, but Adaptive does not expand into generic intake after its goal is answerable.
- The only Adaptive-exclusive tool capability in this run is `READ_DIARY`; it explains the DA advantage materially and must stay separate from a policy conclusion.
- Fixed ASK volume is highest in DATA_ANALYSIS (**6.0/case**), then CAUSE_ASSESSMENT and PERSONALIZED_DECISION (**5.5/case** each), then KNOWLEDGE_QA (**4.5/case**).

## ASK quality analysis

### Classification rule

Each actual ASK is manually classified against the frozen case goal and the facts already visible in the user query or prior scripted follow-up:

- **necessary**: directly needed to complete the permitted current answer scope;
- **useful_but_optional**: goal-related, but a bounded answer could proceed without it;
- **redundant**: repeats a visible/provided fact or a question already answered/declined;
- **irrelevant**: does not have material information value for the current frozen goal.

`useful_ask_rate = (necessary + useful_but_optional) / all_asks`. This is a trace-review measure, not a clinical truth label.

| System | Necessary | Useful but optional | Redundant | Irrelevant | Total ASK | Redundant ASK rate | Useful ASK rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fixed | 4 | 5 | 15 | 30 | 54 | 27.8% | 16.7% |
| Adaptive | 4 | 2 | 4 | 0 | 10 | 40.0% | 60.0% |

This is why raw ASK count alone is insufficient. Adaptive has a higher redundant-ASK *rate* because its four redundant asks are concentrated in CA-02, PD-01, and PD-02, where explicit facts did not reach State. It nevertheless produces six goal-useful asks in total and no irrelevant asks, versus Fixed’s nine goal-useful asks spread across 54 asks and 30 irrelevant asks.

| Case group | Fixed classification sequence | Adaptive classification sequence |
|---|---|---|
| KQ-01 / KQ-02 | irrelevant×5 / irrelevant×4 | none / none |
| CA-01 | redundant×3, optional×2 | none |
| CA-02 | necessary×2, redundant×2, optional×2 | redundant, necessary, redundant, necessary |
| PD-01 | necessary, optional, irrelevant×4 | redundant, necessary |
| PD-02 | redundant×6 | redundant |
| PD-03 | redundant×4 | none |
| PD-04 | necessary, irrelevant×5 | necessary, optional×2 |
| DA-01 / DA-02 | irrelevant×6 / irrelevant×6 | none / none |

## Critical failure root-cause analysis

### Fixed PD-01: unsupported individualized recommendation

1. **Source input:** 23:00 bedtime and 60-minute sleep-onset latency; the only scripted follow-up that could materially refine the direction decision was wake time.
2. **Workflow architecture:** the legacy information-gathering stage continued after the wake-time question into night awakenings, subjective quality, screen use, exercise/caffeine and stress. Those fields did not have established information value for the narrow “should I go to bed earlier?” goal.
3. **Retrieval/answer path:** after the generic intake, Fixed invoked retrieval and surfaced a long generic sleep-restriction explanation, including detailed rule-like content. Its final answer converted that material into “do not go to bed earlier; you may need to delay bedtime” while still lacking a completed, scoped user state.
4. **Why not blocked:** Fixed has no visible structured `answer_scope` gate, state sufficiency gate, or answer-grounding boundary that can reject an individualized recommendation when the current intake is incomplete. The trace supports a primary `ANSWER_GROUNDING` failure with workflow/action-selection downstream effects.

### Adaptive PD-03: State-grounding failure propagation

```text
Literal source input
  “最近夜里醒两次、下午喝两杯咖啡”
        ↓
Input Understanding
  bedtime / latency / wake_time extracted;
  caffeine is stored as the combined string
  “最近夜里醒两次、下午喝两杯咖啡”;
  nighttime_awakenings is absent
        ↓
Current AgentState
  no nighttime_awakenings fact or fact source
        ↓
RETRIEVE → ANSWER
        ↓
Final answer
  says “下午两杯咖啡和夜里醒两次…可能有关”
        ↓
Unsupported user-specific claim under the State-only answer contract
```

The first defect is Input Understanding / State Integrity: a compound raw fact was not normalized into `nighttime_awakenings: 2`. The distinct critical defect is Answer Generation: it used the raw-language interpretation despite that fact being absent from current State. The decision path itself (`RETRIEVE → ANSWER`) does not show a Policy failure for this case. No repair is made in this phase.

## Cost analysis: observed, not normalized

| Measure per case, all 10 | Fixed | Adaptive | What can be concluded |
|---|---:|---:|---|
| Observed token usage | 8784.3 | 764.7 | Recorded, but **not comparable end-to-end** because telemetry scopes differ. |
| Observed latency (ms) | 9374.19 | 10046.75 | Recorded; no normalized latency conclusion because endpoints differ. |
| Tool calls | 0.4 | 0.6 | Adaptive’s extra 0.2 is the two necessary diary reads. |
| Turns | 5.8 | 2.0 | Directly observed interaction path difference. |
| Steps | 6.2 | 2.6 | Directly observed loop/workflow path difference. |

In the eight-case capability-matched subset, observed token metadata is Fixed **9349.25** vs Adaptive **837.13**, and observed latency is Fixed **10174.84 ms** vs Adaptive **11809.97 ms**. These remain telemetry/endpoint-confounded observations, not a cost-performance verdict.

## Three-level conclusion

### Observed Result

On these ten frozen V1.1 cases, Adaptive scored 88.3 and Fixed 20.2 (+68.1). On the eight capability-matched non-diary cases, the saved scores are 85.4 and 24.5 (+60.9). Fixed made 54 asks; Adaptive made 10. Each system had one critical failure.

### Supported Interpretation

The traces support that Adaptive more often selects a goal-bounded action path, avoids Fixed’s generic intake after retrieval, and uses explicit resource state to read/handle diary data. The non-DA subset supports that a large difference remains even after removing the `READ_DIARY` capability gap. The traces also support that Adaptive’s remaining unnecessary asks are primarily upstream State/Extraction failures, and that PD-03 is an independent answer-grounding failure.

### Not Yet Supported

This ten-case, single-run, endpoint-asymmetric experiment does not support a claim that Adaptive is universally superior to Fixed in real clinical use, that all +68.1 points come from Decision Policy, or that Adaptive is cheaper/faster end-to-end. It also does not quantify the independent causal effect of State, Policy, RAG, model variability, or answer-generation design.

## Recommended next step

Choose **C. Design a capability-matched comparison** before benchmark expansion or Agent modification: define a pre-registered comparison in which both systems share the same invocation surface and token/latency instrumentation, and clearly separate cases that require diary capability. Retain the two current critical failures as fixed failure-analysis fixtures. Option A (repair Adaptive) should be explicitly authorized separately and then followed by a fresh comparison; it should not be mixed into this validity analysis.
