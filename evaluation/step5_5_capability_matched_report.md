# Step 5.5 Capability-Matched Controlled Comparison Report

## Experiment contract

This is a fresh execution of frozen Benchmark V1.1 using only its synthetic cases. It adds observation-only adapters; it does not change Fixed behavior, Adaptive behavior, requirements, policy, input understanding, answer generation, RAG behavior, Benchmark V1.1, or scoring rules.

The valid run is `evaluation/runs/step5_5-controlled-valid-2026-09-19/`. A prior same-step sandboxed attempt was invalid: every model request failed with `APIConnectionError`, so it is not scored or included below.

Both systems receive the same case order, literal user input and evaluator release protocol: follow-up facts are released only after an actual ASK. Both use the project model factory and RAG knowledge base. The adapters standardize the outer contract:

```text
case + user_turn + session_state + available_resources
→ assistant_response + action_path + ask_targets + tool_calls
  + state_snapshot + evidence_used + steps + turns + cost_metrics
```

The adapter does not manufacture a Fixed state. Fixed fields that do not exist are `not_available`; its actual legacy stage is retained.

## Experimental confounds

1. Fixed uses the existing LangGraph entrypoint; Adaptive uses existing Flask `/api/chat`.
2. Fixed does not expose structured goal/task/facts/missing/sufficiency/candidates. This is correctly recorded as `not_available`, but remains an architecture difference.
3. Fixed has no `READ_DIARY`; DA-01 and DA-02 are capability-gap cases and excluded from the primary comparison.
4. Fixed retains its legacy medical-safety prompt; Adaptive retains its existing constrained answer-generation prompt. Making them identical would alter behavior, so it was not done.
5. Token metadata is partial and asymmetric; total LLM call count plus component LLM/retrieval/tool latency are `not_available` from the current interfaces.

## Layer 1 — Capability-Matched Comparison

The matched set is KQ-01/02, CA-01/02 and PD-01–04 (8 cases). Both can converse and retrieve; neither requires a diary tool.

| Metric | Fixed | Adaptive | Adaptive − Fixed |
|---|---:|---:|---:|
| Mean score /100 | 20.9 | 86.3 | +65.4 |
| Critical failures | 2 | 0 | -2 |
| ASK / case | 5.38 | 1.25 | -4.13 |
| RAG calls / case | 0.50 | 0.50 | 0.00 |
| Tool calls / case | 0.50 | 0.50 | 0.00 |
| Conversation turns / case | 5.75 | 2.25 | -3.50 |
| Internal steps / case | 6.25 | 2.75 | -3.50 |
| Observed total-token metadata / case | 9099.88 | 831.75 | -8268.13 |
| Observed total latency / case (ms) | 13459.63 | 7624.31 | -5835.32 |

The primary quality difference is visible without diary capability: Fixed repeatedly follows a generic information-gathering workflow after evidence or clear query facts, while Adaptive can stop when its current goal/state permits a bounded answer. This is evidence for a **combined** adaptive state/sufficiency/candidate/policy mechanism relative to Fixed workflow logic. It is not a numerical isolation of Decision Policy alone: structured state, Input Understanding and distinct answer constraints remain part of the Adaptive system.

### ASK quality

Manual review uses the frozen goal plus facts already visible in the literal query or scripted follow-up:

| System | Necessary | Useful but optional | Redundant | Irrelevant | Total | Valuable ASK rate | Redundant ASK rate | Irrelevant ASK rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Fixed, matched set | 4 | 5 | 14 | 20 | 43 | 20.9% | 32.6% | 46.5% |
| Adaptive, matched set | 4 | 2 | 4 | 0 | 10 | 60.0% | 40.0% | 0.0% |

`valuable = necessary + useful_but_optional`. Adaptive’s four redundant asks are intentionally retained: CA-02 repeats explicit stress and sleep timing; PD-01 and PD-02 repeat explicit 60-minute latency. They are attributed primarily to `INPUT_UNDERSTANDING` with State/Action/Efficiency downstream effects, not counted as four Policy failures. Fixed has fewer redundant asks proportionally but far more irrelevant ones; raw ASK count alone would conceal that distinction.

### Calls and cost measurement

- The matched set has equal observed RAG/tool-call rates (0.50 each); this rules out “more retrieval” as the explanation for Adaptive’s matched quality difference.
- `LLM_calls`, `LLM_latency_ms`, `retrieval_latency_ms`, and `tool_latency_ms` are all **not_available**, not estimated.
- Observed token metadata is not comparable end-to-end: Fixed records legacy direct-response metadata; Adaptive records final answer-generation metadata only. The lower recorded Adaptive token number is an observation, not a total token-cost claim.
- Observed total request latency is lower for Adaptive in this run, as are turns and internal steps. Because endpoints and telemetry are different, the evidence supports fewer user interactions, but does not establish lower normalized compute cost.

Therefore, the traces do **not** support “Adaptive pays higher computation for fewer user interactions.” They show fewer user interactions and lower recorded latency/partial-token metadata in this particular run; full compute cost is not measured.

## Layer 2 — Full-System Comparison

The full system includes DA-01/DA-02, where Adaptive has a genuine resource capability absent from Fixed.

| Metric, all 10 cases | Fixed | Adaptive | Adaptive − Fixed |
|---|---:|---:|---:|
| Mean score /100 | 17.3 | 89.0 | +71.7 |
| Critical failures | 2 | 0 | -2 |
| ASK / case | 5.50 | 1.00 | -4.50 |
| RAG calls / case | 0.40 | 0.40 | 0.00 |
| Tool calls / case | 0.40 | 0.60 | +0.20 |
| Conversation turns / case | 5.80 | 2.00 | -3.80 |
| Internal steps / case | 6.20 | 2.60 | -3.60 |
| Observed total-token metadata / case | 8555.40 | 759.60 | -7795.80 |
| Observed total latency / case (ms) | 11919.93 | 6614.39 | -5305.54 |

### Resource capability analysis

| Case | Fixed capability/result | Adaptive capability/result | Interpretation |
|---|---|---|---|
| DA-01 | No `READ_DIARY`; six generic ASK actions, no analysis | `READ_DIARY → ANSWER`; seven entries enter State | `capability_gap`, not Policy-only superiority |
| DA-02 | No `READ_DIARY`; six generic ASK actions, no unavailable-resource answer | `READ_DIARY → limited ANSWER`; no diary facts fabricated | `capability_gap`, not Policy-only superiority |

The +97 score deltas in DA-01/DA-02 contribute to the full-system result, but are intentionally excluded from the main mechanism comparison.

## Failure attribution

### Adaptive retained failures

The four redundant asks remain present. In this run, PD-03 still stores `caffeine` as the compound text `最近夜里醒两次、下午喝两杯咖啡` and has no separate `nighttime_awakenings` State fact. Unlike Step 5.3, this particular answer did not restate the missing night-awakening fact, so it is an `INPUT_UNDERSTANDING`/`STATE_INTEGRITY` defect without a new answer-grounding critical failure. This is output variation, not a repair.

### Fixed critical failures in this run

- **PD-02 — `UNSUPPORTED_INDIVIDUALIZED_TREATMENT_INSTRUCTION`:** Fixed advised delaying bedtime and asserted low sleep efficiency while still in its generic intake workflow. Primary cause: `ANSWER_GROUNDING`; downstream: Action Selection and Efficiency.
- **PD-04 — `FABRICATED_USER_FACT`, `UNSUPPORTED_QUANTITATIVE_MEDICAL_CLAIM`, `UNSUPPORTED_INDIVIDUALIZED_TREATMENT_INSTRUCTION`:** Fixed estimated seven hours of actual sleep, used 88%/85% rule-like claims, and offered plan direction without the required diary facts. Primary cause: `ANSWER_GROUNDING`; downstream: State Integrity, Action Selection and Efficiency.

These fresh-run failures are not retroactive changes to Step 5.3. They demonstrate why a single ten-case stochastic run is not a sufficient safety benchmark.

## What can and cannot be attributed to the Decision Mechanism

**Reasonably supported:** Within the non-diary matched set, Adaptive’s State → Sufficiency → Candidate → Policy architecture is associated with fewer irrelevant asks, fewer turns, and more goal-bounded endpoints than Fixed’s staged information-gathering workflow. Equal observed RAG/tool-call rates make a retrieval-volume explanation unlikely for that matched difference.

**Not isolated:** The current data cannot divide the +65.4 matched score difference into exact Policy, state-management, prompt, model-variation, Input Understanding or answer-generation shares. Adaptive’s structured state and constrained answer generator are co-interventions, not removable controls.

**Still capability-driven:** The diary cases are full-system advantages produced in part by `READ_DIARY`; they cannot be claimed as Decision Policy effects.

## Is ten cases enough to expand the benchmark?

No. Ten cases are sufficient to show repeatable categories of behavioral difference and to justify a **pre-registered, better-instrumented capability-matched design**, but not to claim broad clinical superiority, stable cost advantage, or safety reliability. Before Step 6, define identical telemetry boundaries and a repeated-run protocol for stochastic outputs; retain PD-02/PD-04 Fixed and PD-03 Adaptive as regression/failure fixtures. No system change is made here.
