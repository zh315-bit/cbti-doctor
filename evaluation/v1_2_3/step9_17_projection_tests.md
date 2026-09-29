# Step 9.17 — Synthetic Projection Test Matrix

Tests are deterministic unit-level synthetic fixtures. No Benchmark case, external model, network, or Benchmark V3 was used.

| # | Scenario | Expected | Test |
|---:|---|---|---|
| 1 | Consecutive multi-day entries | preserve entries/count/dates/provenance; derive exact supported aggregates | `test_01_consecutive_multiday_entries_project_with_counts_dates_and_lineage` |
| 2 | Non-consecutive dates | preserve only provided dates; do not fill gaps | `test_02_nonconsecutive_dates_preserved_without_filling_gaps` |
| 3 | Multiple entries on one date | preserve source cardinality; count unique diary days separately | `test_03_multiple_entries_same_day_preserve_cardinality_and_unique_day_count` |
| 4 | Missing measurement | preserve null; average only over explicitly numeric available values | `test_04_missing_measurements_are_preserved_and_not_guessed` |
| 5 | Range/approximate clock | preserve uncertainty; omit exact variation derivation | `test_05_range_and_approximate_clocks_are_not_collapsed_to_exact` |
| 6 | Valid entry-shaped payload | accept only with matching count, dates, coverage, provenance | `test_06_entry_shaped_projection_records_provenance` |
| 7 | Complete summary-shaped payload | accept as `diary_summary`, not entries | `test_07_valid_summary_remains_summary_shaped` |
| 8 | Summary missing source cardinality | invalid; no State facts | `test_08_summary_missing_source_cardinality_is_invalid` |
| 9 | Summary missing date coverage | invalid; no State facts | `test_09_summary_missing_date_coverage_is_invalid` |
| 10 | Summary missing provenance | invalid; no State facts | `test_10_summary_missing_provenance_is_invalid` |
| 11 | Unavailable diary | `unavailable`, no facts | `test_11_unavailable_is_distinct_and_writes_no_facts` |
| 12 | Source/projected count mismatch | invalid, no facts | `test_12_cardinality_mismatch_is_invalid_and_writes_no_facts` |
| 13 | Invalid diary source in answer context | exclude diary-derived data and quantities | `test_13_invalid_diary_source_is_filtered_from_answer_context` |
| 14 | Valid projection derivation | average, clock variation, efficiency are deterministic and carry lineage | `test_14_valid_projection_allows_deterministic_claims_with_traceable_source` |
| 15 | Malformed date | invalid, no facts | `test_15_malformed_date_fails_closed` |
| 16 | Date/provenance coverage mismatch | invalid | `test_16_date_provenance_mismatch_fails_closed` |
| 17 | Empty but available diary | valid known empty projection; zero days, no fabricated entry | `test_17_empty_available_diary_is_valid_empty_not_fabricated` |
| 18 | Invalid new read after prior valid diary | clear stale diary-sourced State values | `test_18_invalid_new_read_cannot_leave_stale_diary_facts` |
| 19 | Generic retrieval projection envelope | record result/update IDs, payload shape, counts, provenance | `test_19_shared_projection_envelope_covers_retrieval` |
| 20 | Retrieved answer claim lineage | answer evidence claim points to retrieval result and State update | `test_20_retrieval_answer_claim_links_to_tool_and_state_update` |

Result: **20/20 passed** in the focused synthetic test module. Additional existing Diary Contract, Information Value, dependency, lineage, integration, and answer-grounding tests are reported in `step9_17_regression_report.md`.
