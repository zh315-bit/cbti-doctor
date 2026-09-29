# Step 9.6 — Effective Requirements Implementation

## Scope

Implemented the Step 9.5 minimal design boundary. Benchmark V2 was not run;
Benchmark V3 was not created, viewed, or used. No scoring specification,
Decision Policy, Information Value/Cost algorithm, Answer Generation, or Diary
Contract V2 semantics were changed.

## Implementation

### Effective requirements

`RequirementSet` now carries serializable requirement identifiers,
classifications, semantic adjustments, and an `is_effective` marker.
`synchronize_requirements(base, state, dependencies)` is a pure requirements
layer function:

```text
base task-type requirements
+ deterministic goal semantic provenance
+ resolved dependency set
→ effective requirements
```

It classifies fields as `mandatory`, `useful_optional`, or `irrelevant`.
Mandatory meaning remains owned by a dependency/precondition; no missing field
is converted into an ASK merely by its classification. General knowledge
semantics suppress incompatible personal information acquisition while
preserving already supplied facts in State. Diary semantics make diary resource
acquisition authoritative rather than carrying an incompatible task-type
evidence flag into the optional candidate path.

### Lifecycle integration

`AdaptiveAgentLoop._refresh()` now:

```text
base requirements
→ preliminary sufficiency / missing state
→ DependencyResolver
→ synchronize effective requirements
→ final sufficiency / missing state
→ candidates and preconditions
```

It repeats on the initial turn and after RETRIEVE/READ_DIARY state updates. The
runner recreates base requirements from the current `state.task_type` and goal
on each refresh, rather than retaining a prior effective object. New-goal reset
creates a new `goal_id`; user facts remain subject to existing merge rules.

The preliminary sufficiency pass is intentionally retained because the existing
VALIDITY_STATE resolver needs `decision_missing` to decide whether a directional
state dependency exists. The second pass makes the values consumed by
candidates come only from effective requirements.

### Candidate boundary

ASK candidates record `candidate_id`, `source_requirement_id`,
`source_dependency_id`, `source_precondition_id`, and `origin`. Mandatory
dependencies still produce a precondition candidate before Information Value,
Cost, diminishing return, and bounded stop. Optional candidates remain subject
to the unchanged V1.2 Information Value gates.

## Files modified

* `adaptive_agent/requirements.py`
* `adaptive_agent/runner.py`
* `adaptive_agent/candidates.py`
* `adaptive_agent/dependency_resolver.py`
* `adaptive_agent/preconditions.py`
* `adaptive_agent/state.py`
* `adaptive_agent/state_update.py`
* `evaluation/recorder.py`
* `tests/test_step9_6_effective_requirements_lineage.py`

`sufficiency.py` was not changed: it consumes the effective `RequirementSet`
provided by the runner, so its existing missing/sufficiency algorithm remains
unchanged.

## Synthetic result

S1–S12: **12 / 12 passed**. See
`step9_6_synthetic_test_results.json` for the assertion-level record.

## New architecture failure

None was observed in S1–S12. The synchronization rule deliberately has a
bounded lexical semantic surface inherited from `DependencyResolver`; broader
language coverage remains an Input/goal-semantic validation topic, not a claim
that all natural-language goals are now perfectly classified.
