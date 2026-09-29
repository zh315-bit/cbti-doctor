# Step 9.16 Dependency Tests

The new suite is `tests/test_step9_16_dependency_formation.py`. It uses only synthetic goals and in-memory state; no Benchmark V2/V3 case data is imported.

Covered scenarios:

1. External-evidence-only goal forms `EXTERNAL_EVIDENCE` and selects `RETRIEVE`.
2. User-facts-only goal forms `USER_FACTS` and exposes the dependency on ASK candidates.
3. Diary-data-only goal forms `DIARY_DATA` and selects `READ_DIARY` when available.
4. User facts plus evidence forms both classes and retrieves evidence first.
5. Diary plus evidence forms both classes and preserves the diary resource path.
6. Optional user facts do not block an unsatisfied evidence dependency.
7. Available diary data is not converted into unnecessary ASK candidates.
8. Unknown dependency/goal semantics fails safely to bounded ANSWER without fake lineage.

Existing regression coverage remains active for:

- wrong task signal with knowledge semantics;
- wrong task signal with diary semantics;
- evidence and diary satisfied-state transitions;
- hard validity preconditions;
- effective-requirements lineage;
- unavailable/invalid diary fail-closed behavior;
- trace causal fields.

