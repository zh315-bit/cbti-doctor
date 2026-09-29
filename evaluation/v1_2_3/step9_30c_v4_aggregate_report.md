# Step 9.30c — V4 Frozen Adjudication Aggregation

**Status: BLOCKED_FAIL_CLOSED_ADJUDICATION_PIN_MISMATCH.** No aggregate was generated.

The request pins adjudication SHA-256 `85d436955fe2b7ea244b8ce94fcb4443d7004140c5b0c4090283f7a0907cd645`. The computed hash of the Step 9.30b adjudication file and the hash recorded in its freeze are both `85d436955fe2b7ea2448bce94fcb4443d7004140c5b0c4090283f7a0907cd645`. These identities differ. The historical freeze and adjudication were left unchanged; no substitution was made.

Because the requested Step 9.30b identity gate failed, the formal aggregate-generation path was not allowed to proceed. Focused unit tests did exercise the pure aggregation function in memory against the frozen adjudication rows to verify determinism, but no official metrics artifact or case-level summary was emitted. Consequently this report contains no score, task mean, metric, or case-level result. The separate audit records the mismatch.

No V4 case was rerun. No model, Agent, or RAG was called. No adjudication, run result, raw trace, attempts ledger, rubric, metric registry, or lineage sidecar was modified. No aggregate metrics or case-level summary file was created.

To resume, reconcile the expected adjudication digest through an explicitly authorized, append-only identity correction step; do not edit or overwrite the existing Step 9.30b freeze or adjudication artifacts.


## Step 9.30c-r1 retry aggregate report

# Step 9.30c — V4 Frozen Adjudication Aggregate

Status: **DESCRIPTIVE_SINGLE_AI_REVIEWER_AGGREGATE**. This is deterministic aggregation of the frozen 40-case Step 9.30b adjudication; no case was rescored.

## Observed result

- Overall descriptive mean: **70.5/100** (2820/40; arithmetic mean of case totals).
- Task means: KNOWLEDGE_QA 82.2 (n=10); CAUSE_ASSESSMENT 59.1 (n=10); PERSONALIZED_DECISION 62.6 (n=10); DATA_ANALYSIS 78.1 (n=10).
- Dimension means (point scale, per frozen rubric): goal_alignment 13.675/20; facts_state_integrity 16.1/20; action_resource_selection 13.9/20; evidence_answer_scope 15.5/25; interaction_efficiency 11.325/15.
- Completion: 16/40 = 0.4; validity: 37/40 = 0.925. Per-task strata are in the metrics JSON.
- ASK events: 9; necessary 0, useful optional 0, redundant 1, irrelevant 8; low-value rate 1.0 (9/9). Necessary-target preservation 0.25 (1/4).
- Tools/actions: RETRIEVE 13 (0.325/case), READ_DIARY 10 (0.25/case), ASK 9, actual tool calls 23 (0.575/case). Tool counts are not quality scores; appropriateness counts are separate.
- Efficiency means: turns 1.225/case; steps 1.8/case; tool calls 0.575/case. Latency mean/median/p90 nearest-rank: 6453.3615/3251.395/11380.62 ms. Token usage: **NOT_MEASURED**.
- Critical failures: 0 []; harmful failures: 16 ['V4-CA-01', 'V4-CA-02', 'V4-CA-03', 'V4-CA-05', 'V4-CA-06', 'V4-CA-07', 'V4-CA-09', 'V4-CA-10', 'V4-PD-01', 'V4-PD-03', 'V4-PD-05', 'V4-PD-06', 'V4-PD-07', 'V4-PD-08', 'V4-PD-09', 'V4-PD-10'].
- Lineage (provenance only, not score penalties): formal ready 28; derived complete 7; incomplete formal but adjudicatable 5.

## Supported interpretation

These are descriptive results from one AI reviewer. Completion comes from the frozen completion judgment, not `final_status=ANSWER`. Failure causes and first-divergence layers are reported from frozen per-case labels; no labels were changed.

## Not yet supported

Reviewer type is a single AI reviewer, not human adjudication; inter-rater reliability was not measured. Deterministic consistency checks passed, but scores remain single-reviewer descriptive judgments. Historical comparison is NOT_COMPARABLE for this report; historical scores were not loaded. No overall pass threshold is defined, and no pass/fail conclusion is made.

## Integrity

No Agent/model/RAG call or V4 rerun occurred. Frozen source files were hash-verified before and after aggregation and were not modified:


Audit artifact: `evaluation/v1_2_3/step9_30c_v4_aggregate_report.md`; aggregation audit JSON records output hashes and no-modification flags.

## Step 9.30c-r1 addendum — preregistered acquisition metric and integrity hashes

- Total acquisition actions per case (ASK + RETRIEVE + READ_DIARY): **32/40 = 0.8**. Contributing case IDs: V4-CA-02, V4-CA-04, V4-CA-08; V4-DA-01 through V4-DA-10; V4-KQ-01 through V4-KQ-10; V4-PD-03, V4-PD-04, V4-PD-05, V4-PD-06, V4-PD-10.
- Frozen input SHA-256: adjudication `85d436955fe2b7ea2448bce94fcb4443d7004140c5b0c4090283f7a0907cd645`; case results `77042ae9f5a5a75f7f7efd068e3c182e5725fa709e4f68ae63e58f0bbad0d2ea`; raw traces `e1aac03f4dbedf567c625694e084fa23155c8bfc2db1d43c4dffbce158734189`; attempts ledger `5fe1b11cbe0c28ccdfd056e3141862748897dc3b419ff6f05eb3ad8cb847b59f`; rubric `a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899`; metric registry `de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056`; lineage sidecar `a7b39f70b8f2591982f19ae2ea6d66918b4bd4bba0e588300317ec14f0cfd447`.
- Post-aggregation integrity: all seven frozen inputs remained unchanged; original Step 9.30c failure audit was preserved. V4 rerun/model/Agent/RAG calls: NO. Token usage: NOT_MEASURED. Overall pass threshold: NOT_DEFINED. Historical comparison: NOT_COMPARABLE.
