# Step 9.46 — Treatment-V2 Frozen Adjudication

Status: **PASS — per-case adjudication frozen; not aggregated**.

- Evaluation: `heldout-v4-step9_43-treatment-v2-20260928-01`
- Attempt: `attempt-step9_44r1-cb362342ae31449aaffba8092c346864` (the already-completed formal attempt; this step created no attempt)
- Reviewer: `SINGLE_AI_REVIEWER`; human adjudication: **NO**; inter-rater reliability: **NOT_MEASURED**.
- Cases adjudicated: **40**, all four task strata have 10 cases.
- Rubric: `a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899`; schema: `21367c176f6b070d875a203ff779cfd44e2cb86a4e8956e1f93870fd054834c8`; metric registry: `de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056`.
- Adjudication JSONL SHA-256: `38e178b68d498ca8280901e071e84787342ba460b47ec3c7e9f55f76086eb0f0`.

The adjudication file contains the canonical Step 9.30b reviewer fields, with the Step 9.37 treatment protocol: five rubric dimensions (20/20/20/25/15), task completion, validity, ASK classifications, tool appropriateness, critical/harmful signals, attribution, rationale, and source-row hashes. Lineage sidecar was used only as provenance. Formal incomplete lineage cases remain `INCOMPLETE_FORMAL`; no semantic roots were synthesized and no score penalty was applied solely for lineage incompleteness.

Consistency checks: required reviewer fields complete; score ranges valid; failure and critical labels populated; ASK classifications match every observed ASK; task distribution matches the frozen 10-per-stratum design. Full per-case decisions and evidence are in the adjudication JSONL. This report intentionally does not calculate completion/validity rates, task means, critical/harmful totals, Overall, or comparisons.

Critical-failure case IDs: `NONE`.

Harmful-failure case IDs: `NONE`.

Source formal results, raw traces, attempt ledger, lineage sidecar, rubric, metric registry, and schema were hash-pinned and unchanged. No rerun, model/Agent/RAG execution, aggregation, baseline/V1/V2 comparison, or V5 access occurred.

The per-case adjudication artifact is ready to be supplied to Step 9.47. Step 9.47 must still independently apply its own frozen input-integrity and aggregation eligibility gates; no aggregation has been run here.
