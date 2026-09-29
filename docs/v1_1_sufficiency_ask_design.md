# Adaptive Agent V1.1: Sufficiency and Redundant ASK Control

## Scope

Step 7.2 changes only sufficiency metadata, decision-relevant missing facts,
ASK eligibility, redundancy prevention, resource-vs-ASK choice, and stopping
conditions. Input extraction, RAG, diary implementation, answer grounding,
Benchmark V2, baseline artifacts, and scoring remain unchanged.

## State and Sufficiency

The State now distinguishes:

- `required_missing`: all theoretical critical and secondary requirements;
- `decision_relevant_missing`: unresolved fields in the current goal's
  `decision_fields`;
- `secondary_missing`: useful context that must not block a bounded answer.

`critical_missing` remains as a backward-compatible alias for critical
requirements. Range and approximate fact values pass the existing known-value
check; they are not automatically refined.

## ASK Eligibility

An ASK candidate is emitted only when the target is unknown, appears in
`decision_relevant_missing`, has plausible impact on the next decision or
answer scope, and has not already been asked under an equivalent normalized
target. `sleep_time`, `sleep_onset_latency`, and
`sleep_time_or_sleep_onset_latency` share one normalized target. This is a
qualitative ordinal heuristic, not a calibrated probability.

## Information Value and Stop Conditions

Candidates encode goal relevance, decision impact, interaction cost, and
redundancy. Explicit goal factors and small remaining decision gaps receive
higher impact. Secondary gaps do not generate ASK candidates. When no eligible
ASK remains, the agent can answer with a bounded limitation; if evidence is
missing it may retrieve evidence first. A required resource is considered
before asking the user, and an unavailable resource produces a bounded answer
without retry loops.

## Tests

`tests/test_v1_1_sufficiency_ask.py` covers missing-category separation,
explicit/range/approximate availability, secondary-only answers, genuine
critical gaps, equivalent ASK blocking, resource precedence, unavailable
resource stopping, bounded answers, and negative premature-answer protection.
