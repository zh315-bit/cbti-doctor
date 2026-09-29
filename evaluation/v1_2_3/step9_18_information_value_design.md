# Step 9.18 — Information Value Gate Design

## Purpose

Place one observable, goal-aware acquisition gate between optional Candidate Generation and Decision Policy. This is a deterministic ordinal heuristic; labels are not learned rewards, calibrated probabilities, or expected clinical outcomes.

## Flow and precedence

```text
Goal + State + Dependency Set
  → Hard Preconditions (mandatory dependencies remain non-overridable)
  → Candidate Generation
  → Information Value / Acquisition Gate
  → Decision Policy
  → Action
```

An active mandatory dependency continues through the existing Hard Precondition path. The gate annotates it as accepted with reason `mandatory_dependency_precondition_cannot_be_overridden`; acquisition cost, diminishing returns, and bounded-answer fallback cannot reject it. Optional acquisitions are evaluated using goal relevance, expected information gain, decision/answer-scope impact, missing-field criticality, redundancy, actual dependency status, and action cost.

## Ordinal decision rules

- ASK: retain only goal-scoped decision-relevant candidates (or an explicit required user-fact dependency); reject already-known/already-asked information; then apply the existing diminishing-return threshold to ordinal `HIGH / MEDIUM / LOW / NONE` value and interaction cost.
- RETRIEVE: optional retrieval is retained only for an active unsatisfied external-evidence dependency and rejected when evidence already satisfies it. Required evidence is produced earlier by Hard Preconditions.
- READ_DIARY: retained only for an active unsatisfied diary dependency; loaded, unavailable, invalid, or unauthorized resources are not retried. Required authorized available diaries are produced earlier by Hard Preconditions.
- If every acquisition candidate is rejected, emit a bounded ANSWER candidate and set `stop_reason=no_worthwhile_information_after_acquisition_gate`.
- When sufficiency already provides ANSWER and there is no unresolved hard dependency, the existing policy's ANSWER preference remains intact.

`acquisition_value` is a qualitative component summary, not arithmetic utility. Trace explicitly marks `heuristic_not_calibrated_probability=true`; no probability-like float is produced.

## Trace contract

For each generated acquisition candidate, `AdaptiveAgentState.acquisition_decisions` records candidate/action/target, expected information gain, goal relevance, decision impact, criticality category, redundancy, matching dependency (if any), estimated cost, acquisition value, accept/reject result, and reason. Runner state-history snapshots include this record so downstream evaluation can audit the choice.

## Inputs / outputs

Input: current `AdaptiveAgentState`, effective `RequirementSet`, and generated `ActionCandidate[]`.

Output: policy-ready candidate list. Candidates retain their real IDs and dependency/precondition lineage; no synthetic lineage is created. If all optional acquisitions are rejected, output contains the bounded ANSWER candidate.

## Boundary

This gate does not lower or alter sufficiency thresholds, rewrite dependency semantics, modify Decision Policy ranking, or bypass Answer Grounding. It governs optional acquisition only; hard validity/evidence/resource dependencies keep precedence.
