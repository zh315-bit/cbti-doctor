# Step 9.2 Dependency Resolver Mechanism Test Plan (Design Only)

No scenarios in this plan were executed.

| ID | Setup | Expected dependency/action boundary |
| --- | --- | --- |
| M1 | Knowledge goal, wrong `task_type` | EVIDENCE REQUIRED from goal semantics; RETRIEVE mandatory |
| M2 | Same knowledge goal, relevant evidence present | EVIDENCE SATISFIED; no duplicate RETRIEVE |
| M3 | Diary-analysis goal, wrong `task_type` | RESOURCE(sleep_diary) REQUIRED from goal semantics |
| M4 | Required authorized available unread diary | RESOURCE AVAILABLE → READ_DIARY |
| M5 | Required diary unavailable | RESOURCE UNAVAILABLE → bounded resource fallback, no retry |
| M6 | Missing recent pattern and authorized diary satisfier | resource satisfier selected before ASK |
| M7 | Optional detail-only missing fact | no dependency; Information Value evaluates it |
| M8 | Validity-critical directional state with no resource | VALIDITY_STATE REQUIRED → ASK |
| M9 | Same missing field under educational vs directional goal | no dependency vs VALIDITY_STATE REQUIRED |
| M10 | Mandatory dependency with high acquisition cost | mandatory satisfier survives Cost |
| M11 | Mandatory dependency after several ASK | mandatory satisfier survives Diminishing Return |
| M12 | Mandatory dependency while bounded answer otherwise possible | ordinary stop cannot bypass it |

## Diary Contract scenarios

1. Valid seven-entry `ENTRY_SHAPED` result preserves count, dates and provenance.
2. Missing values remain missing; no derived exact values appear.
3. Non-consecutive dates preserve coverage gaps.
4. Duplicate-looking distinct entries preserve cardinality.
5. `SUMMARY_SHAPED` with count, coverage and aggregation method writes summary
   facts only; it does not create entries.
6. `SUMMARY_SHAPED` without any source truth becomes `INVALID` and writes no
   diary-derived facts.
7. Malformed date, cardinality mismatch or provenance mismatch becomes INVALID.
8. UNAVAILABLE and INVALID both avoid tool retry and diary-derived claims.

Each scenario must assert dependency lifecycle state, satisfiers considered,
selected/rejected satisfier, precondition action or fallback, and trace fields.
