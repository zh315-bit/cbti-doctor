# Step 9.18 — Low-Value Information Acquisition Repair Report

## Implemented

Added a unified optional-acquisition gate between candidate generation and the policy in the production `AdaptiveAgentLoop`. It evaluates ASK, RETRIEVE and READ_DIARY candidates against current goal/state, relevant dependency state, redundancy, decision impact and cost. The gate writes a machine-readable decision record into State and every runner snapshot. Values remain interpretable ordinals, not calibrated probabilities.

Mandatory Hard Precondition actions are marked `HARD_PRECONDITION` and survive the gate. Optional retrieval and diary reads require a matching unsatisfied dependency; evidence already present or a diary already loaded/unavailable/invalid prevents duplicate tool calls. ASK is not retained merely because a field is missing: generation remains scoped to decision-relevant missing fields, known/equivalent/already-asked facts are rejected, and remaining candidates pass the current qualitative value/cost threshold. If nothing worthwhile remains, the loop can select bounded ANSWER with an explicit stop reason. Sufficiency thresholds were not changed.

## Files changed / added

- `adaptive_agent/acquisition_gate.py` — shared value/cost/dependency gate and trace records.
- `adaptive_agent/candidates.py` — separates raw generation from policy-ready gated `build_candidates` compatibility entry point; ASK values are evaluated by the gate.
- `adaptive_agent/runner.py` — invokes the gate after generation and snapshots acquisition decisions.
- `adaptive_agent/state.py` — adds candidate gate metadata and state acquisition-decision trace.
- `tests/test_step9_18_information_value_gate.py` — 17 controlled synthetic/counterfactual tests.
- `evaluation/v1_2_3/step9_13a_authorization_infrastructure` test assertions were updated to recognize the new candidate freeze while retaining both historical identities and fail-closed old-runner checks.
- `evaluation/v1_2_3/step9_18_candidate_freeze.json` — new post-Step-9.18 development identity; no prior freeze was overwritten.
- Four Step 9.18 design/test/regression/report documents and `record.md`.

## Gate inputs and outputs

Input is `(state, effective_requirements, generated_candidates)`. Output is a policy-ready candidate list with preserved candidate/dependency/precondition IDs. Each acquisition decision contains `expected_information_gain`, `goal_relevance`, `decision_impact`, `missing_criticality`, `redundancy`, `resource_dependency`, `estimated_cost`, `acquisition_value`, `gate_decision`, and `reason`. Rejected candidates are kept in trace; if every acquisition is rejected, the gate returns a bounded ANSWER candidate and `no_worthwhile_information_after_acquisition_gate` stop reason.

## Test and safety result

- Gate mechanism: **17/17 PASS**.
- Combined relevant focused regression: **115 passed**.
- Full non-Benchmark suite: **217 passed / 0 failed / 0 skipped**.
- `Missing Information ≠ Must Ask`: preserved; secondary-only missing data with a sufficient answer does not trigger ASK.
- Under-acquisition guard: high-value/validity-critical ASK and mandatory evidence/resource retrieval survive.
- No case IDs, Benchmark-specific keywords or expected paths added.
- No Benchmark V2 rerun, no V3 access, no live model call.

## Freeze chain

Step 9.11 historical freeze → authorized Step 9.16 dependency formation → authorized Step 9.17 projection repair → Step 9.18 acquisition gate. Step 9.11 and Step 9.17a candidate files remain unchanged. The new candidate freeze is not a benchmark authorization and makes no performance claim.

## Limitations

The gate is ordinal and rule-based; its value levels are not calibrated against outcomes. Existing candidate generation only proposes user-fact questions from the current decision-relevant field set; this repair does not add new requirement discovery or alter requirements/sufficiency. Trace completeness was validated through runner snapshots and tests, not a fresh live API smoke test.
