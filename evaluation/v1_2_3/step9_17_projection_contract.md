# Step 9.17 — Tool → State Projection Contract

## Purpose and boundary

Every tool adapter returns source data; it does not write directly into AgentState. A projection boundary validates the payload and records the exact State update. The contract is generic so future tools can use the same envelope, while this implementation tightens the current RAG evidence and sleep-diary projections only. Tool availability is not evidence of payload validity, and a payload's shape must never be inferred from its contents after the fact.

## Shared projection envelope

Each projection event records:

```text
tool_result_id
state_update_id
source_action_id
tool / source_type
payload_shape
source_entry_count
projected_entry_count
date_coverage (null for non-date data)
provenance
projection_status (valid | unavailable | invalid)
projection_warnings
```

`source_entry_count` means source records/items represented by the tool; `received_entry_count` is the row count physically present in an entry-shaped payload; `projected_entry_count` means raw entry rows actually admitted to State (not the number of values inside a summary). Thus an invalid result has `projected_entry_count=0` while retaining received counts/dates for diagnosis; a valid summary has zero projected raw entries and remains a summary. Tool-specific fields may extend this envelope. The shared status meanings are: `valid` = verified and projected; `unavailable` = source cannot provide data; `invalid` = source responded but its payload/metadata failed validation. Candidate/tool IDs link to the matching State update. No projection code may invent source records, dates, cardinality, provenance, or lineage IDs.

## Diary payload shapes

| Shape | Contract | State representation |
|---|---|---|
| `ENTRY_SHAPED` | `entries` or `recent_sleep_pattern` is a list of objects, each with a valid ISO date. Nonnegative source count equals received row count; `source_dates` preserves one date per row including same-day duplicates; `date_coverage` equals the unique valid dates; provenance is a non-empty structured mapping. Missing measurements are allowed and remain missing. | Preserve the validated entries at `facts.recent_sleep_pattern`; preserve `diary_projection` and fact-source metadata. Empty, known diary is valid with count 0 and empty date coverage. |
| `SUMMARY_SHAPED` | Must include a positive source cardinality, non-empty valid date coverage, non-empty structured provenance, and non-empty summary semantics. Summary payload must not be entry-shaped. | Store only at `facts.diary_summary`; never rewrite it as `recent_sleep_pattern` or claim its source count is its projected entry count. |
| `UNAVAILABLE` | Explicit unavailable response or unavailable flag. | No facts; projection status `unavailable`; resource status `unavailable`. |
| `INVALID` | Explicit invalid response, unsupported shape, malformed date, count/date/provenance mismatch, or insufficient summary metadata. | No facts; projection status `invalid`; resource status `invalid`; warnings retained. |

Serialized `projection_status` is lowercase for compatibility with the current AgentState contract. `DiaryResult.kind` uses the uppercase shape names above.

## Deterministic entry derivations

Only validated entry-shaped data can produce `diary_derived` fields. Current deterministic calculations are:

- `diary_day_count`: count of unique covered dates (not entry count; multiple same-day entries remain distinct source entries).
- `average_sleep_duration_minutes`: arithmetic mean of finite numeric `total_sleep_time` values, with the contributing entry count recorded.
- `bedtime_variation_minutes` / `wake_time_variation_minutes`: circular minimum-span clock variation over exact clock values only; range/approximate values are retained but excluded from exact calculation.
- `time_in_bed_by_day`: cross-midnight duration from exact bedtime/wake-time pairs.
- `sleep_efficiency_by_day`: numeric total sleep divided by exact time-in-bed only when both inputs exist and the result is physically bounded by time-in-bed.

Each derived State fact carries the source projection, counts, date coverage, provenance, and tool/state IDs. Incomplete inputs reduce the number of deterministic results; no missing value or date is imputed.

## Claim grounding and lineage

Answer context excludes diary-sourced facts unless their active source projection is `valid`. A new diary read clears the previous diary-sourced projection before applying the new result, preventing stale diary values from leaking through an invalid/unavailable read. Deterministic diary claims and validated summary claims carry `tool_result_id`, `state_update_id`, projection status, source count, date coverage, and provenance in `claim_provenance`. Evidence claims carry their retrieval tool and State-update IDs. Thus the auditable path is:

```text
dependency → action/source_action_id → tool_result_id
→ validated projection → state_update_id / sourced fact
→ claim_provenance → answer context
```

RAG uses the same envelope with `payload_shape=EVIDENCE_LIST`, evidence-item counts, and no date coverage. The envelope is designed for future tools; adding a new tool still requires its own explicit shape validator and derivation rules.

## Non-goals

This contract does not change dependency formation, candidate scoring, Decision Policy, answer medical strategy, Benchmark V2, scoring, or any benchmark fixture. It does not make summary semantics objectively true merely because the tool supplied a label; the metadata provides traceability, not independent source authenticity.
