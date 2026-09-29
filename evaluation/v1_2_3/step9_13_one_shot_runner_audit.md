# Step 9.13 — One-Shot Runner Audit

Audited file: `scripts/run_step9_12_frozen_evaluation.py`. No runner was executed.

| Requirement | Result | Evidence |
| --- | --- | --- |
| Explicit authorization ID | PASS | `--authorization-id` is required and prefix-validated. |
| Evaluation identity binding | PARTIAL | Static `EVALUATION_ID` and authorization prefix bind identity, but no `--evaluation-id` argument exists. |
| One-shot guard / append-only ledger | PASS | `PREPARED`, `STARTED`, terminal entries are appended to JSONL. |
| Hash check before first case | PASS for legacy identity | `before_case` calls `verify_frozen_identity()`. |
| Fail closed / no automatic retry | PASS | blocking terminal states prevent rerun; exceptions persist terminal failure. |
| Raw trace persistence | PASS | per-attempt JSONL trace path is passed to the base runner. |
| Per-case persistence | PASS | `after_case` appends completion state. |
| Interruption/failure persistence | PASS | exception path appends `FAILED_BEFORE_FIRST_CASE` or `FAILED_AFTER_PARTIAL_EXECUTION`. |
| Case-specific branching | PASS | no V2 case-ID lookup/branch was found. |
| Benchmark V3 access | PASS | no V3 path/import appears. |
| Step 9.12b Harness consumption | FAIL | runner checks the old Step 9.11 harness manifest and will reject current preflight script hash. |

## Frozen classification rules

These rules are fixed before execution:

- `COMPLETED`: all 40 cases complete and valid results persist.
- `PARTIAL_EXECUTION`: at least one case starts but fewer than 40 complete.
- `ENVIRONMENT_FAILURE`: failure before an Agent/model request caused by local runtime, DNS, credential, or dependency environment.
- `MODEL_FAILURE`: a configured provider/model request fails after invocation begins.
- `HARNESS_FAILURE`: runner, ledger, trace, adapter, or evaluation-only callback failure.
- `AGENT_FAILURE`: production Agent raises or violates a recorded execution contract.
- `SCORING_FAILURE`: completed case traces exist but scorer fails to produce valid case/aggregate scores.

These classifications are observational labels; they do not authorize a run or a retry.
