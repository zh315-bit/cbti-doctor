# Step 9.16 Dependency Formation Repair Report

## Modified modules

- `adaptive_agent/dependency_resolver.py`
  - Added canonical source classes `USER_FACTS`, `EXTERNAL_EVIDENCE`, and `DIARY_DATA`.
  - Added generic goal-semantic formation for mixed and single-source goals.
  - Added dependency metadata aliases and requiredness/satisfaction lineage.
  - Kept legacy `EVIDENCE` and `RESOURCE` values for compatibility.
- `adaptive_agent/candidates.py`
  - Propagates dependency IDs to diary, retrieval, and user-fact candidates.
- `tests/test_step9_16_dependency_formation.py`
  - Added eight synthetic dependency scenarios.

No Benchmark case ID, Benchmark wording, RAG fixture, diary fixture, or scoring rule was added to production logic.

## Mechanism changes

Dependency formation now precedes effective requirements and candidate generation. Goal semantics can form multiple source dependencies, and task type contributes only a prior. Knowledge goals do not wait for optional personal facts before evidence retrieval. Diary-analysis goals own acquisition through `DIARY_DATA`; personal facts are not redundantly requested when the diary resource can satisfy the goal.

## Safety and regression boundaries

The repair does not force all Knowledge QA to retrieve, all Data Analysis to read a diary, or all Personalized Decision goals to ask. Existing hard validity and unavailable-resource fallbacks remain intact. Unknown semantics fail closed to bounded ANSWER.

## Status

`DEPENDENCY_FORMATION_REPAIRED = YES`

`CASE_SPECIFIC_LOGIC_ADDED = NO`

`AGENT_BEHAVIOR_CHANGED = YES`

`BENCHMARK_V2_RERUN = NO`

`BENCHMARK_V3_ACCESSED = NO`

Verification detail: 34 focused dependency/lineage tests and 64 curated existing Agent regression tests passed. Full discovery was attempted but four modules could not import because `flask`/`yaml` are absent in the environment; this did not produce a behavior failure in the exercised scope.
