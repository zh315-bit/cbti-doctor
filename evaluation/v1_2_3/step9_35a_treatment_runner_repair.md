# Step 9.35a — Treatment Runner Compatibility Repair

Decision: `TREATMENT_RUNNER_READY=YES`; matched treatment authorization precheck passes. No authorization was issued and no treatment execution occurred.

## Environment

Project interpreter: `/Volumes/Elements/cbti-doctor-main/.venv/bin/python`. PyYAML 6.0.3 is already installed there. pytest is not installed and is not listed as a project dependency; no package/environment changes were made. The focused and regression suites ran with the project interpreter's `unittest` runner.

## Runner and boundary

Added `scripts/run_step9_35a_matched_treatment.py` and froze it at SHA-256 `920486b1d7984fae6ee77b5ac51af0d0a98caf42e445d1abcf7ff75b46038505`. This new treatment-only adapter explicitly requires evaluation, authorization, and attempt IDs; authorization file; and the treatment Agent, benchmark, Harness, scoring, registry, One-shot Rules, and matched-protocol hashes. It checks the frozen `POST_HOC_MATCHED_FROZEN_BASELINE` class, treatment-vs-baseline Agent distinction, issued/unconsumed authorization, unique IDs, exact output namespace, all current frozen identities, 40-case order fingerprint, and absence of a prior attempt. It does not require the obsolete randomized-paired protocol.

Execution delegates only the existing generic production case helper `scripts/run_step9_28_v4_heldout.py::_case_result` (source SHA-256 `fddaa09803dd1df27da81f3793929d15a3f6d5d29c1060842ecbf138a76b1d06`), which sends requests through the production `/api/chat` route. The adapter adds treatment identity binding and persistence guards, not case-specific policy or scoring. The original Step 9.28/9.29a baseline runner and freeze remain byte-for-byte unchanged; the new freeze supersedes them for treatment execution only.

One-shot behavior: exclusive new namespace and ledger; authorization consumption and `FIRST_EVALUATION_ACCESS` are fsynced before reading benchmark bytes; actual case order/schema are checked before model/service execution; attempt and per-case `STARTED` are persisted before Agent calls; traces/results are exclusive-created, directory entries synced, and records fsynced; interruption leaves the attempt in place and prevents rerun. Importing the adapter does not access benchmark bytes; identity validation hashes the sealed file without parsing it; formal case parsing occurs only after the durable first-access marker.

## Verification

All 21 new synthetic-contract tests passed, including valid matched contract, wrong identity pins, baseline Agent rejection, class mismatch, set/order mismatch, duplicate authorization/attempt, namespace collision, missing/unissued/consumed authorization, and acceptance without a randomized-preregistration flag. Fourteen existing one-shot/runner authorization regressions also passed (`35/35` total). Tests did not execute cases or call Agent/model/RAG.

Recomputed frozen hashes all match. Treatment inventory matches its 9.33a freeze, with no Agent edits. The exact current dataset case-ID order matches the completed baseline's locked fingerprint; no case contents were emitted. Baseline ledger/results/traces/adjudication/aggregate remain immutable and hash-matched (40 completed cases). Non-Agent configuration, tools, RAG, dependencies, and execution limits match; adjudication remains configured for the locked single-AI-reviewer class and procedure.

The treatment runner freeze is `evaluation/v1_2_3/step9_35a_treatment_runner_freeze.json`, with status `FROZEN_NOT_AUTHORIZED`. `READY_FOR_MATCHED_TREATMENT_AUTHORIZATION=YES` means the precheck gates pass; it does not issue permission. Authorization/attempt IDs remain null, no command was generated, the treatment namespace is absent, and no V4 case, score, baseline rerun, or V5 activity occurred.
