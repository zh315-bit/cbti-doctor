# Step 9.33a — Full Regression Failure Triage

**Disposition: regression recovered; full effective regression passes.** This step did not run V4, invoke a benchmark model/Agent/RAG path, score any case, or access/create V5.

## Baseline comparison

The Step 9.32 baseline snapshot was extracted to an isolated temporary directory; the 101-file snapshot was verified against the frozen baseline inventory before running the exact failed test nodes. All 21 originally failing test nodes and the Step 9.30a.2 historical sidecar test class passed on that baseline (28/28, 0 failures, 0 errors). The source tree used for baseline comparison was separate from the treatment workspace. Baseline Agent aggregate remains `4e2bffea0d7eaa9299074a960df84a1806b3ae9d4930662929abc58ca5b2ae79`.

The original treatment suite had 288 tests, 21 failures and one setup error. The complete exact failure inventory and per-item classification/resolution is in `step9_33a_regression_failure_matrix.jsonl`.

## Triage and repair

Thirteen findings were actual treatment regressions: accepted, counterfactually material ASK candidates or a valid diary alternative could be displaced by an independent RETRIEVE. The policy now orders a diary that can satisfy missing facts first, then accepted ASK, then required RETRIEVE. Because the value gate removes immaterial/irrelevant ASK candidates first, this does not make low-value questions block evidence acquisition; evidence retrieval remains eligible immediately after no accepted material ASK is pending. The diary gate now recognizes a `VALIDITY_STATE` dependency that explicitly lists `READ_DIARY` as a satisfier. These changes are limited to `adaptive_agent/policy.py`, `adaptive_agent/acquisition_gate.py`, and `adaptive_agent/candidates.py`; safety/execution hard preconditions are unchanged.

One prior assertion expected a bounded ANSWER after a duplicate/unanswered question even though independent required evidence remained unsatisfied. Under the frozen Step 9.32 R1 contract, that dependency must remain actionable, so this is an `EXPECTED_SEMANTIC_CHANGE`; the replacement assertion checks accepted RETRIEVE. Historical hash-bound tests were updated to preserve their frozen-artifact integrity assertions while checking the correct treatment mismatch/fail-closed semantics. Two runner guard tests now provide an isolated matched-freeze fixture so they exercise their intended unissued-auth/prior-ledger guards. The historical Step 9.30a.2 tests read and validate the immutable saved sidecar/manifest/audit rather than rebuilding an artifact tied to the prior Agent identity.

Legacy assertions and replacements are retained in the matrix and the code comments. No Agent branch maps a case ID, fixture, expected action, or benchmark-specific policy. No benchmark, harness, scoring, metrics, adjudication, one-shot rule, or historical frozen artifact was modified.

## Verification

- Focused behavior and guard regression after repair: 102 tests passed (the final full suite below supersedes this earlier focused run).
- Full non-benchmark `python -m unittest discover -s tests`: **296 tests, 0 failures, 0 errors; exit 0** (83.634 seconds).
- Full suite's CLI usage text is expected output from tests that assert argument-validation failures; it is not a test failure.
- Exact Step 9.32 baseline comparison: 28/28 relevant nodes passed.
- Frozen Step 9.32 design/preregistration/baseline artifacts remain unchanged. No formal evaluation or V4 case was executed; no model/Agent/RAG was called for evaluation.

## Identity

After the final passing suite, a treatment freeze is recorded in `step9_33a_treatment_freeze.json`. It uses the existing 26-entry candidate inventory domain and current non-secret/runtime and corpus fingerprints; it does not claim the old Step 9.26/9.28/9.30a Agent freeze still matches. This freeze is only the development treatment identity required for future paired-evaluation precheck, not an authorization to evaluate.

## Stop conditions

`V4_RERUN=NO`, `MODEL_CALLED=NO`, `AGENT_CALLED_FOR_EVALUATION=NO`, `RAG_CALLED_FOR_EVALUATION=NO`, `V4_CASE_EXECUTED=0`, `V4_SCORE_GENERATED=NO`, `V5_CREATED_OR_ACCESSED=NO`. This step does not begin Step 9.34 or a paired evaluation.
