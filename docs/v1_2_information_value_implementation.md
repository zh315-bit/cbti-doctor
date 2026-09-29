# Adaptive Agent V1.2: Information Value Implementation

## Scope

Step 8.2 implements the frozen Step 8.1 information-value design without
running Benchmark V2. Input understanding, RAG, Benchmark V2, scoring rules,
and Benchmark V3 remain unchanged.

## InformationValueEstimate

`adaptive_agent/information_value.py` defines an interpretable structured
estimate with target, `HIGH/MEDIUM/LOW/NONE` value, counterfactual impact,
uncertainty, answer-scope impact, ordinal acquisition cost,
resource-alternative flag, redundancy, and rationale. It emits no calibrated
probabilities or expected-utility numbers.

## Rules and Cost

Timing fields and explicitly goal-named factors default to HIGH when plausible
values could change the next action. Remaining contextual fields generally
change answer scope and are MEDIUM; detail-only secondary facts are LOW;
known, semantically repeated, or irrelevant facts are NONE. Approximate/range
facts remain known. ASK cost rises from LOW to MEDIUM to HIGH with prior ASK
count and broad cognitive burden. READ_DIARY records a low-cost resource
alternative when an authorized diary is available.

## Diminishing Return and Stop Rule

Before the first ASK, LOW value can pass; after one ASK, MEDIUM is required;
after two or more, HIGH is required. This is a rising ordinal threshold, not a
fixed maximum ASK count. If no candidate clears value/cost or a resource
alternative dominates, candidate generation records a stop reason and permits
bounded ANSWER while missing fields remain.

## Observability

State and evaluation snapshots now persist `information_estimates`,
`considered_information`, `rejected_information`, and `stop_reason`. Each
considered item records value, cost, counterfactual impact, resource
alternative, accepted/rejected status, and rejection reason.

## Tests and Limitations

`tests/test_v1_2_information_value.py` covers NONE/LOW/HIGH classification,
uncertainty preservation, resource alternatives, diminishing returns,
genuine high-value ASK survival, and rejected-candidate observability. The
heuristic does not estimate calibrated probabilities, and final policy quality
still depends on upstream extraction and goal interpretation.
