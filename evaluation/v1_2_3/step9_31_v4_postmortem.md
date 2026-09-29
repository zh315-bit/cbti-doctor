# Step 9.31 — V4 Postmortem & Architecture-Level Failure Taxonomy

Status: **READ_ONLY_POSTMORTEM**. This analysis consumes frozen Step 9.30c-r1 metrics, Step 9.30b adjudication, formal case results/raw traces, rubric, Metric Registry, and lineage sidecar. No Agent/model/RAG call, V4 rerun, or rescoring occurred. Input paths and SHA-256 digests are embedded in `step9_31_v4_postmortem.json`.

## Result in brief

- 40 cases; descriptive overall 70.5. By task: KQ 82.2, CA 59.1, PD 62.6, DA 78.1.
- Validity 37/40 (92.5%); completion 16/40 (40.0%). Cross-tab: 16 valid+complete, 21 valid but incomplete, 3 invalid and incomplete, 0 invalid but complete.
- All 9 ASK events were low-value per the frozen reviewer: 8 irrelevant and 1 redundant. Event-level root cause counts: {'HARD_PRECONDITION_OVERRIDES_INFORMATION_VALUE': 5, 'INPUT_FACT_NOT_PROJECTED_TO_STATE': 1, 'INPUT_FACT_AND_UNANSWERABLE_TARGET_STATE_NOT_REPRESENTED': 3}. First divergence: {'DEPENDENCY_FORMATION': 5, 'INPUT_UNDERSTANDING_STATE': 4}.
- Harmful failures: 16; frozen cause counts: {'REQUIRED_INFORMATION_ACQUISITION_OMISSION': 1, 'REQUIRED_RESOURCE_OMISSION': 13, 'REQUIRED_INFORMATION_AND_RESOURCE_OMISSION': 1, 'REPEATED_IRRELEVANT_ACQUISITION': 1}. Critical failures: 0.

## ASK mechanism and controlled-test discrepancy

Five ASK events (V4-CA-02, V4-CA-04, V4-PD-03, V4-PD-04, V4-PD-06) arose from a generic validity-state dependency/forced precondition: the hard gate forced an ASK despite a bounded fallback or an unhelpful target. Four events were tied to state projection/input-understanding issues: one question repeated facts already stated (PD-05), and three asks in PD-10 followed explicit adequate/stable facts missing from state plus no persistent “unknown/unavailable/asked” target state. The full event-level evidence and raw-line digests are in `step9_31_ask_failure_matrix.jsonl`.

Step 9.25’s mechanism tests passed local structured scenarios, but the low-value optional-ASK denominator was 3 candidates that entered that gate (0 low-value among those), not all production-path ASK events. It did not cover end-to-end natural-language fact extraction, state projection, multi-turn unknown handling, or production evidence selection. V4’s 9/9 denominator covers observed ASK events across the held-out traces. These results therefore concern different populations and different pipeline layers; they are not logically contradictory. The controlled test is narrower evidence, not a generalization proof.

## Harmful failures and task weakness

CA’s 8/10 harmful outcomes mostly share omitted user information and/or external evidence before bounded answers; PD’s 8/10 harmful outcomes include omitted information/resources, wrong forced acquisition, known-fact loss, and a repeated-ASK loop. The traces show no actual RETRIEVE in the harmful CA/PD cases. This is consistent with an upstream dependency/candidate-policy interaction: incomplete user facts can make the system stop at a bounded answer rather than independently retrieving general evidence. This remains an architecture-level inference from traces, not a new frozen reviewer label.

KQ is strongest (8 complete; 2 evidence-coverage partial) and all ten cases retrieve; DA is 5/10 complete, with diary reads present in all ten, but four harmful task-execution omissions occurred after diary data projection. Thus CA/PD weakness is not simply “the model cannot answer”: their trace bottleneck is acquisition planning and fact/dependency handling; DA’s separate weakness is task completion after tool results; KQ’s residual weakness is evidence coverage/synthesis. Task × frozen cause and inferred architecture mappings are in `step9_31_architecture_failure_map.json`.

## Validity vs completion

Validity (37/40) measures bounded/defensible behavior; completion (16/40) requires doing the requested acquisition, evidence retrieval, or analysis. Twenty-one cases are valid but incomplete: safe limitations were often stated, but a requested action/result was omitted. Three DA cases were both invalid and incomplete. Completion root labels are preserved as adjudicated: {'REQUIRED_INFORMATION_ACQUISITION_OMISSION': 1, 'REQUIRED_RESOURCE_OMISSION': 13, 'ACTION_SELECTION': 1, 'TASK_EXECUTION_OMISSION': 4, 'CONDITIONAL_EVIDENCE_NOT_RETRIEVED': 1, 'EVIDENCE_COVERAGE_LIMITATION': 2, 'REQUIRED_INFORMATION_AND_RESOURCE_OMISSION': 1, 'REPEATED_IRRELEVANT_ACQUISITION': 1}. `final_status=ANSWER` was not used as a completion proxy.

## Ranked architecture repair candidates

1. **R1_EVIDENCE_PATH_INDEPENDENT_OF_PERSONAL_FACT_COMPLETENESS** — decouple external evidence needs from personal-fact completeness. Addresses an estimated 15 omission cases (all harmful in this postmortem grouping); main risk is irrelevant retrieval/overreach.
2. **R2_VALUE_GATED_PRECONDITION_AND_SAFE_FALLBACK** — require information-value and safe-fallback checks before hard-precondition ASK; preserve truly necessary clarification. Addresses 5 ASK events and 4 harmful cases; main risk is suppressing necessary ASK.
3. **R3_ASSERTED_FACT_AND_UNAVAILABLE_TARGET_STATE** — project asserted facts and retain unknown/unavailable target state. Addresses 4 ASK events and 2 harmful cases in two cases; main risk is erroneous extraction or overbroad target equivalence.

R4, answer-task contract after tool projection, is retained as a fourth candidate (six completion cases including two non-harmful evidence-coverage cases) but is outside the top three under the requested CA/PD/harmful/ASK common-upstream prioritization. See repair JSON for test plans and risks. These counts are hypotheses about addressable cases, not guaranteed treatment effects.

## Paired hypotheses and contamination boundary

Preregistered directional hypotheses (no numeric targets): reduce low-value ASK rate, improve completion and reduce harmful failures, preserve necessary ASK and critical-failure safety, increase independent evidence retrieval/grounding when personal facts are incomplete, improve explicit-fact retention and stop repeated asks after unknown/unavailable responses, and improve requested diary task completion without unsupported calculations. Exact denominators and frozen adjudication protocol must be held constant in later paired evaluation.

From this point, V4 is **DEVELOPMENT / POSTMORTEM EVIDENCE**. Any Agent changes informed by Step 9.31 make V4 non-unseen for that Agent. V4 may support regression or paired mechanism analysis; a new sealed V5 is required for a new Agent’s held-out generalization claim.

## Limitations and integrity

Step 9.30b was a single AI reviewer; IIR was not measured. Layer attribution is an analyst inference, not independently adjudicated. No pass threshold is defined and historical comparability is NOT_COMPARABLE. Frozen inputs were only read; all Step 9.31 output artifacts are additive. Agent, benchmark, adjudication, scoring, and metric registry were not modified; V4 was not rerun; no model, Agent, or RAG was called.
