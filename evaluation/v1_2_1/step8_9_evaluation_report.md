# Step 8.9 — V1.2.1 Development/Regression Evaluation

## Observed Results

{
  "benchmark_interpretation": "development_regression_set_not_held_out",
  "cases": 40,
  "overall_score": 67.5,
  "dimension_means": {
    "goal_alignment": 18.2,
    "facts_state_integrity": 13.75,
    "action_resource_selection": 13.7,
    "evidence_answer_scope": 12.82,
    "interaction_efficiency": 9.03
  },
  "task_scores": {
    "KNOWLEDGE_QA": 83.5,
    "CAUSE_ASSESSMENT": 72.5,
    "PERSONALIZED_DECISION": 52.08,
    "DATA_ANALYSIS": 64.38
  },
  "ASK_per_case": 1.65,
  "PD_ASK_per_case": 2.917,
  "RETRIEVE_per_case": 0.275,
  "READ_DIARY_per_case": 0.225,
  "turns_per_case": 2.65,
  "steps_per_case": 3.15,
  "total_latency_ms_per_case": 7478.7,
  "six_ASK_limit_cases": 0,
  "critical_failures": 4,
  "harmful_failures": 7,
  "token_usage": "not_available",
  "exact_LLM_calls": "not_available",
  "LLM_latency": "not_available",
  "retrieval_latency": "not_available",
  "tool_latency": "not_available"
}

## Supported Interpretation

The 40-case frozen V2 development/regression run completed once. Hard preconditions work when they are present in State; they cannot repair upstream task/state failures that prevent their creation.

## Not Yet Supported

This is not held-out evaluation, generalization evidence, real-world superiority, or calibrated optimal-policy evidence.
