# V1.2.2 Diary Tool Contract — Design

## Contract variants

The projection layer must not assume every successful diary result is a list of
individual entries.

| Kind | Required data | State eligibility |
| --- | --- | --- |
| `ENTRY_SHAPED` | `entries`, `source_entry_count`, dates/coverage, provenance | project only after count/date/provenance validation |
| `SUMMARY_SHAPED` | explicit `summary`, source cardinality, date coverage, aggregation method, provenance | write summary facts only; never reinterpret summary items as entries/days |
| `UNAVAILABLE` | availability reason and provenance | no diary-derived facts; dependency fallback |
| `INVALID` | validation errors and raw-safe metadata | fail closed; no diary-derived facts |

## Proposed result schema

```python
@dataclass(frozen=True)
class DiaryResultV2:
    kind: Literal['ENTRY_SHAPED', 'SUMMARY_SHAPED', 'UNAVAILABLE', 'INVALID']
    availability: bool
    authorization: Literal['authorized', 'unauthorized', 'unknown']
    entries: list[DiaryEntry] | None
    summary: DiarySummary | None
    source_entry_count: int | None
    date_coverage: DateCoverage | None
    aggregation_method: str | None
    provenance: DiaryProvenance | None
    warnings: list[str]
    validation_errors: list[str]
```

`SUMMARY_SHAPED` is valid only if `source_entry_count`, date coverage and
provenance demonstrate what the summary represents. A text such as
`"14 entries: latency ranges 20–90"` is not an entry list and cannot be safely
converted to “one diary day.”

## Projection rules

```text
ENTRY_SHAPED + valid invariants   → entry facts + deterministic derivations
SUMMARY_SHAPED + source truth     → summary facts with summary provenance only
SUMMARY_SHAPED - source truth     → INVALID / fail closed
UNAVAILABLE                       → no facts; bounded unavailable path
INVALID                           → no facts; bounded invalid-data path
```

The projection must retain `input_kind`, source/projected cardinality, source/
projected date coverage, aggregation method, provenance, status and warnings.
Derived claims must reference either entries or a declared summary aggregation;
they must never convert a range to an exact value, fill a missing night, or
infer diary entry count from a list of summaries.

## Step 9.1 applicability

DA-03, DA-04, DA-05 and DA-08 supplied summary-shaped strings without source
cardinality/date/provenance metadata. Their correct V2 contract outcome is
`INVALID`, not `ENTRY_SHAPED valid`. This is a future Tool → State integrity
repair; it is not a Decision Policy rule.
