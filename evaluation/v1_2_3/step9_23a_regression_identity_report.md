# Step 9.23a — Regression Identity Report

## Identity semantics

The tests now check three separate properties:

1. Historical Step 9.11/9.17/9.18 artifacts retain their original bytes and parent hashes.
2. The current Agent matches the new Step 9.23 candidate inventory and aggregate.
3. The historical V3 runner remains bound to its original Agent and fails closed for the new candidate. The unissued authorization template is independently rejected once a matching freeze is supplied in the offline test.

No runner check or hash comparison was weakened. The V3 runner still rejects the new P1 Agent with `frozen identity mismatch`; its consumed V3 result is not a result for this candidate.

## Verification

- The three prior failing identity tests: **3/3 PASS** after separating historical identity from current candidate identity.
- Full non-Benchmark suite, excluding the external `tests.test_model_configuration`: **232 total / 232 passed / 0 failed / 0 skipped**.
- The suite includes the Step 9.23 synthetic tests and existing dependency, projection, lineage, information-value, and answer-grounding regression tests. Two argparse usage messages are expected output from negative CLI tests; the suite exit status is successful.
- `tests.test_model_configuration`: **NOT RUN**; it requires external provider configuration/model connectivity. No model API was called during this step.
- Benchmark V2 and V3 were not run. V3 results and scoring remain unchanged.

The Step 9.23 candidate freeze is a development identity, not benchmark authorization. P2 remains out of scope until this audit is accepted.
