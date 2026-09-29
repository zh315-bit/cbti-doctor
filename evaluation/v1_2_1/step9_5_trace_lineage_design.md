# Step 9.5 — Trace Lineage Design

## Objective

The current trace records type/target and a `goal_semantics` source label. It
can be read manually, but it cannot reliably join a dependency to the
precondition, candidate, selected action, tool result, and re-resolved
dependency. This design adds deterministic, per-turn lineage identifiers and
semantic provenance without claiming calibrated confidence.

## Identity model

IDs are generated in the loop, not derived solely from a type/target string.
They are stable inside one state revision and intentionally receive a new
revision on re-resolution.

```text
goal_id:        goal_t{turn}_r{state_revision}
semantic_id:    sem_t{turn}_r{state_revision}_{ordinal}
dependency_id:  dep_t{turn}_r{state_revision}_{ordinal}
precondition_id:pre_t{turn}_r{state_revision}_{ordinal}
candidate_id:   cand_t{turn}_r{state_revision}_{ordinal}
action_id:      act_t{turn}_r{state_revision}_{step}
tool_result_id: tool_t{turn}_r{state_revision}_{step}
state_update_id:upd_t{turn}_r{state_revision}_{step}
```

The exact string format is an implementation detail; uniqueness, referential
integrity, and snapshot retention are the contract. A new goal begins a new
`goal_id`; a tool or fact update increments `state_revision`.

## Goal-semantic provenance schema

Each goal assessment should emit a structured deterministic match object:

```json
{
  "semantic_id": "sem_t2_r4_1",
  "goal_id": "goal_t2_r4",
  "semantic_rule_id": "KNOWLEDGE_EVIDENCE_REQUIRED",
  "matched_text": "为什么规律起床时间重要",
  "semantic_reason": "goal requests general external CBT-I knowledge",
  "certainty": "HIGH",
  "match_method": "deterministic_rule"
}
```

`certainty` is a qualitative rule-match indication (`HIGH`, `MEDIUM`, `LOW`),
not a probability and not calibration. If a rule uses multiple spans, record
an array of exact matched text. If no rule matched, record an empty assessment
with `match_method: none`; do not invent provenance.

## Dependency, precondition and candidate schemas

```json
{
  "dependency_id": "dep_t2_r4_1",
  "goal_id": "goal_t2_r4",
  "semantic_ids": ["sem_t2_r4_1"],
  "dependency_type": "EVIDENCE",
  "target": "external_evidence",
  "status": "REQUIRED",
  "reason": "current answer scope includes external CBT-I knowledge",
  "satisfiers_considered": ["RETRIEVE"],
  "selected_satisfier": "RETRIEVE"
}
```

```json
{
  "precondition_id": "pre_t2_r4_1",
  "source_dependency_id": "dep_t2_r4_1",
  "status": "UNSATISFIED",
  "required_action": "RETRIEVE",
  "precondition_forced_action": true,
  "counterfactual_candidate": null,
  "counterfactual_action": "ANSWER",
  "counterfactual_stop_reason": "evidence dependency absent"
}
```

```json
{
  "candidate_id": "cand_t2_r4_1",
  "action": "RETRIEVE",
  "source_precondition_id": "pre_t2_r4_1",
  "source_dependency_id": "dep_t2_r4_1",
  "origin": "HARD_PRECONDITION",
  "accepted": true,
  "selection_or_rejection_reason": "mandatory dependency unsatisfied"
}
```

Optional candidates must have `origin: OPTIONAL_ACQUISITION` and a null
precondition ID. They retain `information_value`, `acquisition_cost`, decision
impact, accepted/rejected status, and rejection reason. This makes it explicit
whether the action happened because it was mandatory or because its value
covered cost.

## Action, tool and state-update links

```json
{
  "action_id": "act_t2_r4_1",
  "selected_candidate_id": "cand_t2_r4_1",
  "action": "RETRIEVE",
  "selection_reason": "mandatory dependency unsatisfied",
  "tool_result_id": "tool_t2_r4_1",
  "state_update_id": "upd_t2_r5_1"
}
```

The post-tool dependency objects carry `supersedes_dependency_id` and their
new status. For example, `dep_t2_r5_1` with `SATISFIED` supersedes
`dep_t2_r4_1`, rather than overwriting its history. An ASK has an `action_id`
but no tool-result ID; a user follow-up creates a state-update ID that links
the preceding ASK target to the merged fact if supplied.

## Trace requirements by action

| Action | Required lineage fields |
| --- | --- |
| ASK | candidate/action IDs, origin, value/cost (if optional), target, accept/reject rationale, current goal/revision |
| RETRIEVE | all mandatory or optional candidate links, query, tool result, evidence update, re-resolved dependency relation |
| READ_DIARY | all candidate links, tool payload kind, contract/projection record, state update, re-resolved resource dependency |
| ANSWER | selected candidate ID, answer scope, stop reason or satisfied dependency set, no hidden tool satisfaction |

## Counterfactual observability contract

Counterfactual fields are observational explanations, not a second execution
of the policy. For a forced hard precondition, the trace may record the
candidate/action/stop that was available before the force was applied. For an
optional candidate, `precondition_forced_action` is false and the
counterfactual fields are null. If the system cannot determine a counterfactual
without running a separate policy pass, it records `not_computed`; it must not
fabricate one.

## Integrity invariants for Step 9.6 tests

1. Every `source_dependency_id` resolves to a dependency in the same or an
   immediately preceding state revision.
2. Every selected action has exactly one `selected_candidate_id`.
3. Mandatory candidates have a precondition and dependency source; optional
   candidates do not claim a forced precondition.
4. Every SATISFIED/UNAVAILABLE/INVALID post-action dependency identifies its
   earlier dependency or records why no predecessor exists.
5. A new `goal_id` cannot reference an old-goal requirement/dependency without
   an explicit carry-forward record.
6. Goal-semantic provenance is concrete rule/span/reason data or absent; a
   bare `goal_semantics` label is insufficient.
