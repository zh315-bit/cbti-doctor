# Step 5.3 Fixed vs Adaptive Controlled Comparison Report

## Scope and reproducibility

This is the first rerun on frozen Benchmark V1.1. It compares the existing Fixed Workflow (A) and Adaptive Agent V1 (B) on the same ten cases, case inputs, scripted follow-up facts, model factory, RAG knowledge base, and evaluator-owned diary fixtures. No Agent, RAG, requirements, answer-generation, or benchmark-specification file was modified. The definitive raw artifacts are in `evaluation/runs/step5_3-controlled-final-2026-09-19/`.

The earlier same-date non-final directory is discarded because concurrent processes produced incomplete/corrupted output. It is not included in any score or conclusion.

## Experimental confounds

1. Fixed uses its existing LangGraph entrypoint because it has no legacy `/api/chat` route; Adaptive uses the production Flask chat route.
2. Fixed exposes message history, not `AdaptiveAgentState`; therefore its raw trace has no structured task type/facts/state. The benchmark task type is used only by the evaluator for paired scoring.
3. Fixed has no `READ_DIARY` interface. The fixture was deliberately not prompt-injected, so it remains unavailable to Fixed.
4. Adaptive token usage is answer-generator metadata; Fixed token usage is response metadata when available. Both are retained as observed raw fields, but are not comparable end-to-end token totals.

These confounds favor neither a hidden-state injection nor a diary shortcut. They do limit causal claims about token/latency differences.

## Case-level paired result

| Case | Task | Fixed | Adaptive | Delta | Fixed path | Adaptive path |
|---|---|---:|---:|---:|---|---|
| KQ-01 | KNOWLEDGE_QA | 35 | 100 | +65 | RETRIEVE → ASK×5 → ANSWER | RETRIEVE → ANSWER |
| KQ-02 | KNOWLEDGE_QA | 34 | 100 | +66 | RETRIEVE → ASK×4 → ANSWER | RETRIEVE → ANSWER |
| CA-01 | CAUSE_ASSESSMENT | 25 | 98 | +73 | ASK×5 → ANSWER | RETRIEVE → ANSWER |
| CA-02 | CAUSE_ASSESSMENT | 19 | 74 | +55 | ASK×6 (stops ASK) | ASK×4 → ANSWER |
| PD-01 | PERSONALIZED_DECISION | 15 ⚠ | 78 | +63 | ASK×5 → RETRIEVE → ASK | ASK×2 → ANSWER |
| PD-02 | PERSONALIZED_DECISION | 20 | 76 | +56 | ASK×6 (stops ASK) | ASK → ANSWER |
| PD-03 | PERSONALIZED_DECISION | 28 | 72 ⚠ | +44 | ASK → RETRIEVE → ASK×3 → ANSWER | RETRIEVE → ANSWER |
| PD-04 | PERSONALIZED_DECISION | 20 | 85 | +65 | ASK×6 (stops ASK) | ASK×3 → ANSWER |
| DA-01 | DATA_ANALYSIS | 3 | 100 | +97 | ASK×6 (stops ASK) | READ_DIARY → ANSWER |
| DA-02 | DATA_ANALYSIS | 3 | 100 | +97 | ASK×6 (stops ASK) | READ_DIARY → ANSWER |

`⚠` marks a V1.1 critical failure, not a score reset. The full goal, state/facts, final answer, tool data, latency, token metadata and per-turn path remain in the system-specific JSONL traces. The paired JSONL adds dimension scores, attribution, and critical-failure records.

## Scores

| Metric | Fixed | Adaptive | Adaptive − Fixed |
|---|---:|---:|---:|
| Mean score /100 | 20.2 | 88.3 | +68.1 |
| Goal Alignment /20 | 5.5 | 19.6 | +14.1 |
| Facts / State Integrity /20 | 10.3 | 17.4 | +7.1 |
| Action / Resource Selection /20 | 0.4 | 17.4 | +17.0 |
| Evidence & Answer Scope /25 | 4.0 | 20.9 | +16.9 |
| Interaction Efficiency /15 | 0.0 | 13.0 | +13.0 |
| Critical failures | 1 | 1 | 0 |

The critical failures differ materially: Fixed PD-01 issued an unsupported individualized instruction to delay bedtime; Adaptive PD-03 stated a user-specific night-awakening fact absent from its current State.

## Raw efficiency metrics

| Mean per case | Fixed | Adaptive |
|---|---:|---:|
| ASK | 5.4 | 1.0 |
| RETRIEVE | 0.4 | 0.4 |
| READ_DIARY | 0.0 | 0.2 |
| Tool calls | 0.4 | 0.6 |
| Steps | 6.2 | 2.6 |
| Conversation turns | 5.8 | 2.0 |
| Observed token usage | 8784.3 | 764.7 |
| Latency (ms) | 9374.19 | 10046.75 |

Adaptive uses 0.2 more tool calls because it correctly reads the diary in the two data-analysis cases. It nevertheless takes 3.6 fewer steps and 3.8 fewer user-facing turns per case. Mean observed latency is 672.56 ms higher for Adaptive, driven particularly by KQ-01; this is not a reliable performance comparison given the endpoint and token-accounting confounds.

## By task type

| Task type | Fixed mean | Adaptive mean | Interpretation |
|---|---:|---:|---|
| KNOWLEDGE_QA | 34.5 | 100.0 | Fixed retrieves but then gathers irrelevant personal data; Adaptive retrieves once and answers. |
| CAUSE_ASSESSMENT | 22.0 | 86.0 | Adaptive is goal-directed, though CA-02 exposes an Input Understanding omission. |
| PERSONALIZED_DECISION | 20.75 | 77.75 | Adaptive substantially reduces unnecessary ASK, but PD-01/02 still show upstream fact-extraction effects and PD-03 is a grounding critical failure. |
| DATA_ANALYSIS | 3.0 | 100.0 | Adaptive honors the resource contract in both available and unavailable routes; Fixed cannot read or report the diary resource. |

## Failure analysis and trade-offs

- **Unnecessary ASK:** Fixed makes irrelevant or repeated ASK actions in every case, including Knowledge QA and diary cases. Adaptive's ASK actions are limited to CA/PD follow-ups; PD-04’s three targets are expressly acceptable in V1.1, though its path is longer than the strongest alternative.
- **Unnecessary RETRIEVE:** Both average 0.4 retrievals per case. Adaptive uses retrieval only in knowledge/cause/goal-support cases; Fixed retrieves in some relevant cases but fails to convert it into a goal-specific answer.
- **Resource dependency:** Adaptive has 1.0 READ_DIARY per data-analysis case and correctly yields a limited answer on the unavailable path. Fixed's 0.0 reflects the documented missing interface, not a hidden-fixture advantage for Adaptive.
- **Adaptive cost/benefit:** The higher task score is accompanied by 0.2 additional tool calls per case and slightly higher observed mean latency, while requiring far fewer steps, turns, and observed tokens. Simple cases do not show a Fixed efficiency advantage in completed goal-directed interaction: Fixed is faster in several raw runs, but often ends in ASK or a generic stage transition rather than a usable answer.
- **Failure preservation:** No failure was repaired to improve the comparison. Adaptive PD-03 and Fixed PD-01 remain critical failures for later analysis.

## Artifact inventory

- `fixed-traces.jsonl`: raw ten-case Fixed traces.
- `adaptive-traces.jsonl`: raw ten-case Adaptive traces.
- `paired-results.jsonl`: frozen-rubric dimension scores, attribution, critical records, and case deltas.
- `comparison-summary.json`: aggregate and task-type metrics.
- `experimental-confounds.json`: the four material confounds above.

The Step 5.1 V1 Pilot result (**83.8**, **1 critical failure**) remains historical and is not used as an Adaptive V1.1 result.

## Conclusion

On the frozen ten-case V1.1 specification, Adaptive is substantially more goal-aligned and resource-aware than the existing Fixed Workflow, while retaining one answer-grounding critical failure. This supports moving to a separate, explicitly authorized failure-analysis or benchmark-expansion decision; it does not authorize a Step 6 run or a behavior change by itself.
