# Step 7.3 Regression Report

Date: 2026-09-20

## Modified Modules

- `adaptive_agent/answer_generation.py`: claim taxonomy records, deterministic
  diary/data summaries, uncertainty-aware validation, and evidence provenance.
- `adaptive_agent/state.py`: `claim_provenance` trace metadata.
- `adaptive_agent/state_update.py`: existing diary projection now feeds
  provenance-preserving State values into answer calculations.
- `adaptive_agent/runner.py` and `evaluation/recorder.py`: persist claim
  provenance in evaluation traces.
- `tests/test_v1_1_answer_tool_grounding.py`: generic grounding regressions.

## Mechanism Changes

Deterministic calculations now produce structured claim records with source
fields and derivation names. Diary lists are summarized from raw entries for
counts, averages, and date coverage; absent days remain absent. The answer
context contains facts, relevant evidence, deterministic claims, and claim
provenance. Final validation rejects unsupported numeric/medical claims and
weakens exact clock wording when State uncertainty is range or approximate.

## Regression Results

Command:

```bash
python3 -m unittest discover -s tests -p 'test*.py'
```

Result: **91 tests passed, 4 skipped, 0 failed**.

The frozen `evaluation/failures/adaptive_v1_failure_set.yaml` remains
unchanged. Benchmark V2 was not run.

## Known Limitations

Claim detection for non-quantitative unsupported prose remains conservative;
numeric and precision claims have the strongest deterministic checks. Evidence
provenance is indexed by current evidence-list position rather than a
long-lived document identifier. Diary missing-day analysis is intentionally
omitted unless a formal expected date window is available.
