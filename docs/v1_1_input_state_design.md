# Adaptive Agent V1.1: Input Understanding and State Integrity

## Scope

Step 7.1 hardens only input understanding, fact normalization, provenance,
state merging, and deterministic derived facts. Sufficiency policy, candidate
ranking, Decision Policy, RAG, answer generation, Benchmark V2, and V1 baseline
artifacts are unchanged.

## Modified Modules

- `adaptive_agent/input_understanding.py`: deterministic extraction after LLM
  output, Chinese/English duration and clock forms, compound fact splitting,
  range/approximate values, and conflict-aware merge.
- `adaptive_agent/state.py` and `adaptive_agent/runner.py`: turn index for
  provenance and state snapshots.
- `adaptive_agent/state_update.py`: diary values carry provenance and cannot
  overwrite a newer explicit user fact.
- `adaptive_agent/facts.py`: reusable deterministic clock/duration derivation.

## State Representation

Exact values retain the V1 representation (`"23:00"`, `60`, `False`). Ambiguous
values use a minimal tagged mapping, for example:

```json
{"uncertainty": "range", "low": "07:00", "high": "08:00"}
{"uncertainty": "approximate", "value": "00:00"}
```

Supported uncertainty labels are `exact`, `range`, `approximate`, and the
absence of a fact remains unknown. Range/approximate clocks are never used to
produce a fabricated unique duration.

## Provenance

`AdaptiveAgentState.fact_sources[field]` now records `kind`, `source_type`,
`source_turn`, `text`, `raw_value`, `normalized_value`, `certainty`, and (for
derived values) `source_fields`. Explicit user facts use `user_explicit`;
deterministic values use `user_derived`; diary projections use `diary`.
Model-only structured output remains in `Understanding.raw_facts` and cannot
enter State without textual grounding.

## Integrity and Derivation Rules

Each field is captured independently from a compound utterance. A newer
explicit fact corrects/refines an older value for the same field, while other
facts persist. Derived or diary values do not overwrite an explicit user fact.
Clock differences use modulo 24 hours (`23:30 → 07:00 = 450`); derivation is
skipped when a range or approximation prevents a unique result.

## Tests

`tests/test_v1_1_input_state.py` adds generic Chinese/English, colloquial,
compound, multi-turn correction, uncertainty, provenance, unknown-fact, and
cross-midnight regression coverage. Existing tests remain unchanged.
