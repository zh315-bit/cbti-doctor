# Step 9.38 — Frozen Treatment Aggregation (Retry)

Status: PASS — deterministic offline aggregation of the frozen Step 9.37 treatment adjudication. No case was rerun or rescored.

- Treatment overall descriptive mean: 79.625/100 (n=40).
- Task means: KNOWLEDGE_QA 82.2 (n=10); CAUSE_ASSESSMENT 79.1 (n=10); PERSONALIZED_DECISION 74.4 (n=10); DATA_ANALYSIS 82.8 (n=10).
- Dimension means: goal_alignment 15.875/20; facts_state_integrity 17.325/20; action_resource_selection 18.475/20; evidence_answer_scope 16.575/25; interaction_efficiency 11.375/15.
- Completion: 20/40; validity: 38/40.
- ASK events: 13; low-value ASK rate 0.6154 (8/13; denominator is all ASK events).
- Execution means: retrieve 0.775/case; read diary 0.25/case; tool calls 1.025/case; turns 1.325/case; steps 2.35/case; mean latency 9658.0275 ms.
- Token usage: NOT_MEASURED. Critical failures: 2; harmful failures: 1.
- Lineage (provenance only, no score effect): formal ready 27; derived complete 8; incomplete formal but adjudicatable 5; denominator 40.
- Reviewer: single AI reviewer, not human; inter-rater reliability not measured.
- No baseline-treatment deltas, improvement percentages, significance claims, resume claims, or V5 access were generated.

## Integrity

Step 9.38a r4 is the append-only provenance bridge: compatibility is aggregation-compatible, not byte identity. Aggregation definitions came only from the Step 9.26 registry; Step 9.37 historical Step 9.19 provenance remains unchanged.
The Step 9.38 fail-closed audit remains preserved. No Agent, model, RAG, treatment rerun, or source artifact modification occurred.

Source identities:

- reconciliation: `06587be92e733543ad0ce8eb5074a365f8a161d2569b24f21fc140e0873d4b29`
- adjudication: `60b5c2847ffdb51c43e00351519cb910428a82eb981849dfebefb76112658047`
- adjudication_freeze: `fe84e4ca0853de680d199807252daa6a2555b1951aa37505924cb15fcc087df5`
- metric_registry: `de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056`
- case_results: `9c926a69f9a4dfd19c559be0cbe8a08abc0902d5728c6f0202ba048b9e67e561`
- raw_traces: `0a8483e4125577e860eb0a7c72c399651800eb94d45eeb9481e6b21795302fdf`
- attempt_ledger: `fc29a97cced81605dd0ec90b3ff8de80ca85e42b898ba5a5fb90f5db09d26d2a`
- lineage_sidecar: `62f3fc844bbabbf59df0e42122d1b570faa11fc16e74b41a0f682f15939f2c42`
- scoring_rubric: `a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899`
- frozen_aggregator: `01aea00ad6a644a44d63a6c31e4bf372f43b53b45f9bc1b9bd7d2649e8522395`
- prior_fail_closed_audit: `3c4f04c18d3c5d0bff07827703a38b971e60f7a19e2b8bdeb9114cdcf4d3694c`
