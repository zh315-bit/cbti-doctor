# Step 9.6 — Trace Lineage Implementation

## Implemented lineage

The runtime now emits deterministic identifiers retained in loop snapshots and
the evaluation recorder:

```text
goal_id
→ semantic_id
→ dependency_id
→ precondition_id
→ candidate_id
→ action_id
→ tool_result_id
→ state_update_id
```

`goal_id` begins at the turn establishing a goal; `state_revision` increments
after input and after tool-driven State updates. A re-resolved dependency uses a
new revision ID and records `supersedes_dependency_id` when it represents the
same target from the preceding revision.

## Semantic provenance

`DependencyResolver` records deterministic semantic assessments with:

* `semantic_id`
* `semantic_rule_id`
* `matched_text`
* `semantic_reason`
* qualitative `certainty` (`HIGH`, `MEDIUM`, or `LOW` only)
* `match_method=deterministic_rule`

There is no numerical confidence or calibrated probability.

## Causal links

* Dependency records include `dependency_id`, `semantic_ids`, status, source,
  and potential supersession.
* Precondition records include `precondition_id`, `source_dependency_id`,
  `semantic_ids`, selected satisfier, and forced-action marker.
* Candidates include their own ID and source requirement/dependency/precondition
  IDs. Optional candidates have no precondition source.
* `record_action()` records `action_id` and `selected_candidate_id`.
* Tool-to-State updates append `lineage_events` containing `tool_result_id`,
  `source_action_id`, `state_update_id`, and `source_tool_result_id`.

Counterfactual fields are observability only. A forced precondition records
`precondition_forced_action`; unavailable counterfactual execution is written
as `not_available`, never fabricated.

## Scope limitation

This is lineage instrumentation, not a second policy execution. It does not
calculate a counterfactual action path and it does not alter selection behavior
outside effective-requirement synchronization.
