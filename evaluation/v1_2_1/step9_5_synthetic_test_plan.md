# Step 9.5 — Synthetic Test Plan (Design Only)

No scenario in this plan was executed. These are non-Benchmark tests; they
must not reuse Benchmark V2/V3 IDs, fixtures, or scoring.

| ID | Setup | Expected assertions |
| --- | --- | --- |
| S1 | General knowledge goal; deliberately wrong `PERSONALIZED_DECISION` task signal; evidence initially empty | Semantic provenance forms EVIDENCE REQUIRED → RETRIEVE. After evidence update, dependency is SATISFIED, incompatible personalized decision fields are suppressed from *effective* decision fields, and no stale ASK follows. |
| S2 | Directional personalized goal with missing wake time and no usable diary | Goal semantics and state form VALIDITY_CRITICAL_STATE; effective requirements retain wake time; ASK remains available. Synchronization must not under-ask. |
| S3 | General knowledge goal; user supplies bedtime and wake time voluntarily | Facts and provenance remain in State; EVIDENCE remains the relevant dependency; supplied sleep facts cause neither a new ASK nor irrelevant deletion. |
| S4 | Existing personalized session receives an explicit new knowledge goal | New `goal_id`, base/effective requirement provenance and dependencies replace incompatible prior-goal requirements. Old facts may remain only as non-mandatory history/relevant context. |
| S5 | Existing knowledge session receives an explicit new directional personalized goal | New effective decision fields are formed; evidence history may remain available, but valid current state requirements are calculated for the new goal. |
| S6 | Evidence dependency required, then RETRIEVE succeeds | REQUIRED dependency, forced precondition/candidate/action/tool/update lineage, then SATISFIED dependency with `supersedes_dependency_id`; no duplicate retrieve or stale evidence-driven ASK. |
| S7 | Diary-analysis wording with deliberately wrong non-DA task signal; authorised, available, unread diary | Goal semantics forms RESOURCE dependency; READ_DIARY lineage is forced before optional ASK; after valid projection it is SATISFIED. |
| S8 | Optional detail missing under a goal answerable without it | Field may be `secondary_missing` but not a hard dependency; value/cost can reject it; bounded ANSWER remains possible. |
| S9 | Same missing field in two goals: educational vs directional decision | Educational goal creates no validity dependency; directional goal may create one with concrete semantic provenance. Demonstrates goal-dependent, not field-fixed, criticality. |
| S10 | Mandatory EVIDENCE/RESOURCE plus high acquisition-cost label or several prior ASKs | Mandatory candidate retains forced lineage and is not rejected by cost/diminishing/ordinary stop. |
| S11 | Optional MEDIUM/LOW missing information with existing facts and prior ASKs | It remains optional, carries an optional candidate ID and rejection reason; no artificial dependency/precondition is created. |
| S12 | Diary invalid/unavailable after a forced resource action | Tool result and projection update link to the resource dependency; it becomes INVALID/UNAVAILABLE; no diary facts are written and ANSWER’s limitation identifies the dependency state. |

## Assertions common to every scenario

* `base_requirements`, `effective_requirements`, semantic adjustments and
  suppressed fields are visible in the same state revision.
* No final action is compared by field order. ASK eligibility remains governed
  by relevance, knownness, Information Value, cost, diminishing return and
  duplicate protection unless a validity precondition applies.
* IDs pass the lineage integrity invariants in
  `step9_5_trace_lineage_design.md`.
* No fact, evidence, diary entry, source count, date, provenance, or
  counterfactual result is invented merely to make a trace complete.

## Regression focus

The implementation gate must retain targeted coverage for Step 8 Information
Value, Step 8.8 validity semantics, Step 9.3 dependency resolution/Diary
Contract V2, bounded answers, resource alternatives, new-goal reset and
follow-up fact merge. `tests.test_model_configuration` is explicitly excluded
from this design: its status remains NOT_VERIFIED until a separately authorized
environment investigation.
