# Step 9.16 Regression Report

## Verification commands

Focused and existing non-Benchmark regression tests were run with Python's unittest runner. Benchmark V2 was not run and Benchmark V3 was not accessed.

## Results

Focused dependency and lineage/integration suite:

`34 passed, 0 failed`

Curated existing non-Benchmark Agent regression suite:

`64 passed, 0 failed`

Full unittest discovery attempted 158 tests but was environment-blocked before four modules could import because `flask` and `yaml` are unavailable; four existing tests were skipped. No dependency-formation behavior assertion failed.

This includes 8 new synthetic dependency tests and 26 existing dependency/effective-requirements/integration tests.

The passing suite confirms:

- single-source and mixed-source dependency formation;
- evidence retrieval is not blocked by optional user facts;
- available diary data remains a resource action rather than an ASK;
- wrong task-type signals do not erase goal semantics;
- hard preconditions and unavailable-resource fail-closed paths remain intact;
- candidate and selected-action lineage remains observable;
- unknown dependency semantics do not create fake lineage or fabricated data.

## Final status

`DEPENDENCY_FORMATION_REPAIRED = YES`

`CASE_SPECIFIC_LOGIC_ADDED = NO`

`AGENT_BEHAVIOR_CHANGED = YES`

`BENCHMARK_V2_RERUN = NO`

`BENCHMARK_V3_ACCESSED = NO`

`REGRESSION_STATUS = PASS`

Scope note: focused and curated suites passed; full discovery was environment-blocked for four modules lacking `flask`/`yaml`.

## Next phase gate

Step 9.17 may be entered for Tool -> State Projection Repair. It was not executed in this step.
