# Step 7.1 Regression Report

Date: 2026-09-20

## Scope and Modified Modules

Implemented input understanding, state integrity, fact normalization,
provenance, and deterministic derivation changes in:

- `adaptive_agent/input_understanding.py`
- `adaptive_agent/state.py`
- `adaptive_agent/runner.py`
- `adaptive_agent/state_update.py`
- `adaptive_agent/facts.py`
- `tests/test_v1_1_input_state.py`

No sufficiency logic, candidate ranking, Decision Policy, RAG, answer
generation policy, Benchmark V2, baseline artifacts, or scoring rubric was
modified.

## Mechanism Changes

- Explicit facts are parsed independently from Chinese and English utterances;
  LLM omissions do not erase grounded facts.
- Clock ranges and approximate times preserve uncertainty instead of selecting
  an endpoint.
- New explicit facts replace/refine same-field prior facts; unrelated facts
  persist across turns.
- Provenance includes source type, turn, raw text/value, normalized value,
  certainty, and derivation source fields.
- Deterministic duration helpers handle midnight crossing and refuse unique
  output for non-exact ranges.

## Tests Passed

Command:

```bash
python3 -m unittest discover -s tests -p 'test*.py'
```

Result: **75 tests passed, 4 skipped, 0 failed**.

The frozen `evaluation/failures/adaptive_v1_failure_set.yaml` remains
unchanged and is used as the regression reference. Benchmark V2 was not run.

## Known Limitations

The normalizer intentionally covers supported sleep requirement fields rather
than unrestricted clinical language. Source turns are available for loop
turns; direct unit-level calls without a loop have no turn context. Ambiguous
contradictions that are not explicit user corrections remain conservative and
require later clarification.
