# Step 8.9 Failure Analysis

Known failure review: KQ-02 and KQ-05 still route through misclassified personalized state and never create EVIDENCE; DA-07 still lacks the diary RESOURCE state and never creates READ_DIARY. DA-03/04/05/08 read the diary but their summary-shaped fixtures have no entry cardinality/date metadata, so projection stays `valid` without source truth and the final answer calls one/two summary items days. These are Tool→State projection integrity failures, not Information Value or Preconditions failures.

[
  {
    "case_id": "V2-KQ-02",
    "critical_failure": false,
    "failure_type": "required_dependency_or_premature_answer",
    "supporting_trace": "raw trace / state_transitions"
  },
  {
    "case_id": "V2-KQ-05",
    "critical_failure": false,
    "failure_type": "required_dependency_or_premature_answer",
    "supporting_trace": "raw trace / state_transitions"
  },
  {
    "case_id": "V2-DA-03",
    "critical_failure": true,
    "failure_type": "answer_contradicts_diary_fixture",
    "supporting_trace": "raw trace / state_transitions"
  },
  {
    "case_id": "V2-DA-04",
    "critical_failure": true,
    "failure_type": "answer_contradicts_diary_fixture",
    "supporting_trace": "raw trace / state_transitions"
  },
  {
    "case_id": "V2-DA-05",
    "critical_failure": true,
    "failure_type": "answer_contradicts_diary_fixture",
    "supporting_trace": "raw trace / state_transitions"
  },
  {
    "case_id": "V2-DA-07",
    "critical_failure": false,
    "failure_type": "required_dependency_or_premature_answer",
    "supporting_trace": "raw trace / state_transitions"
  },
  {
    "case_id": "V2-DA-08",
    "critical_failure": true,
    "failure_type": "answer_contradicts_diary_fixture",
    "supporting_trace": "raw trace / state_transitions"
  }
]
