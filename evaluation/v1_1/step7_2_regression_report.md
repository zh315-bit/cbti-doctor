# Step 7.2 Regression Report

Date: 2026-09-20

## Modified Modules

- `adaptive_agent/state.py`: added `required_missing` and
  `decision_relevant_missing` metadata.
- `adaptive_agent/sufficiency.py`: computes the three missing-information
  categories while preserving existing `critical_missing` behavior.
- `adaptive_agent/candidates.py`: adds ASK eligibility, normalized ASK target
  history, ordinal information-value signals, and resource-aware stopping.
- `adaptive_agent/runner.py` and `evaluation/recorder.py`: persist the new
  sufficiency metadata.
- `tests/test_v1_1_sufficiency_ask.py`: generic Step 7.2 regression coverage.

## Mechanism Changes

ASK now requires an unknown, decision-relevant, materially useful target that
has not already been answered by an equivalent question. Approximate and range
facts count as available unless the current goal explicitly requires precision.
Secondary missing facts no longer block ANSWER. Resource candidates remain
available when a diary can supply a missing fact; unavailable resources do not
retry indefinitely.

## Regression Results

Command:

```bash
python3 -m unittest discover -s tests -p 'test*.py'
```

Result: **84 tests passed, 4 skipped, 0 failed**.

The frozen `evaluation/failures/adaptive_v1_failure_set.yaml` remains
unchanged. Benchmark V2 was not run.

## Known Limitations

The information-value heuristic is ordinal and intentionally not calibrated.
Precision-sensitive refinement is not introduced without an explicit goal
signal. ASK semantic equivalence currently uses normalized requirement names,
not embeddings or a general language similarity model.
