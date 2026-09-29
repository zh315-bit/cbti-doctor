# Step 8.2 Regression Report

Date: 2026-09-20

## Modified Modules

- `adaptive_agent/information_value.py`: structured ordinal value/cost
  estimates, counterfactual test, resource alternative, and diminishing-return
  threshold.
- `adaptive_agent/state.py`: information estimates, considered/rejected
  candidate records, and stop reason.
- `adaptive_agent/candidates.py`: value/cost-aware ASK eligibility and
  observability records; READ_DIARY alternative preservation.
- `adaptive_agent/runner.py` and `evaluation/recorder.py`: trace persistence.
- `tests/test_v1_2_information_value.py`: generic Step 8.2 tests.

## Mechanism Changes

Missing and relevant are no longer sufficient by themselves for an ASK. A
candidate must pass the counterfactual value test, cost threshold, redundancy
check, and resource-alternative check. The threshold rises after successive
ASKs; high-value decision-changing questions remain eligible. Low-value or
none-value gaps can coexist with ANSWER and a bounded stop reason.

## Tests

```bash
python3 -m unittest discover -s tests -p 'test*.py'
```

Result: **98 tests passed, 4 skipped, 0 failed**.

Benchmark V2 was not run. Benchmark V3 was not created or inspected.

## Known Limitations

Value levels are ordinal heuristics, not calibrated expected utility. Rejected
candidate telemetry is now available for future traces, but historical frozen
traces remain non-observable for rejected candidates. The implementation does
not yet learn value estimates from outcomes.
