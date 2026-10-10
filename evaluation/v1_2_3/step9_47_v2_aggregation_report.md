# Step 9.47 — Treatment-V2 Frozen Aggregation

Status: PASS — offline descriptive aggregation of the frozen Step 9.46 adjudication; no rerun or re-adjudication.
Scope: Treatment-V2 only. No Baseline/V1/V2 comparison, delta, significance, causal, or generalization claim was computed.

- Cases: 40; task strata: CAUSE_ASSESSMENT 10; DATA_ANALYSIS 10; KNOWLEDGE_QA 10; PERSONALIZED_DECISION 10.
- Overall descriptive mean: 68.875/100 (n=40).
- Task means: KNOWLEDGE_QA 84.4 (n=10); CAUSE_ASSESSMENT 57.2 (n=10); PERSONALIZED_DECISION 56.3 (n=10); DATA_ANALYSIS 77.6 (n=10).
- Dimension means: goal_alignment 13.625/20; facts_state_integrity 15.675/20; action_resource_selection 13.65/20; evidence_answer_scope 15.125/25; interaction_efficiency 10.8/15.
- Completion: 7/40; answer validity: 40/40.
- ASK categories: {'irrelevant': 6, 'necessary': 1, 'redundant': 2, 'useful_but_optional': 3}; low-value 8/12 (denominator: all ASK events).
- Execution: RETRIEVE 31; READ_DIARY 10; actual tool calls 41; turns 52; steps 93; mean latency 7494.118 ms.
- Token usage: NOT_MEASURED; reviewer: SINGLE_AI_REVIEWER (not human), IRR NOT_MEASURED.
- Failures: critical 0; harmful 0.
- Lineage provenance only: formal ready 27; derived complete 8; true incomplete adjudicatable 5; indeterminate 0. No lineage score penalty.
- No V2 rerun; no model/Agent/RAG execution; no V5 access.

## Integrity

- Frozen inputs were verified before and after persistence; adjudication SHA-256 `38e178b68d498ca8280901e071e84787342ba460b47ec3c7e9f55f76086eb0f0`.
- Case-order SHA-256 `d930455e417935337a6e3459defbdc3ee3829b71786fbd8438ef092b62429e68`; aggregation consistency audit PASS.
- Input hashes:
  - adjudication: `38e178b68d498ca8280901e071e84787342ba460b47ec3c7e9f55f76086eb0f0`
  - adjudication_audit: `5cffe15dd810d2303c1ae91b3f13281382575ee45701fd11a7c7210c45ad5018`
  - adjudication_freeze: `74c50c34bd869109d52862202245b7d7e9463928dea24e897b74e3ed85587cee`
  - attempt_ledger: `723fe40cd727db9f553049daccfa7e3cf5489ce6eabee09a7dbea66fd447626b`
  - case_results: `4648b8e320f535001922f13a969d1482433bfa15f88233cf9a7e70b06cafed6c`
  - frozen_aggregator: `01aea00ad6a644a44d63a6c31e4bf372f43b53b45f9bc1b9bd7d2649e8522395`
  - lineage_audit: `f0a9c0f17674b9d236a2678c0a06fd40a6ef6a75eb397047ce12b24ce5353963`
  - lineage_case_matrix: `753ac01ac8e772fdacaa7756900dfad621a88be137a0e946adcd3702349078ec`
  - lineage_sidecar: `92f42eb5288f2b35d00d49212d4f012c0591d7493ff2db3b88c1083f1e0e51de`
  - metric_registry: `de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056`
  - raw_traces: `d7ddf2a9a47ba62a85a7d1b85f069cc9593fd8f46cc4a01c1f3c8a055698cec2`
  - run_input_freeze: `e150091be6e879734ec4a97b0d9e0b7f9bfd782bc640935dd165734c15b9c4f5`
  - scoring_rubric: `a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899`
