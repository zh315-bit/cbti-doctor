# Step 9.63c-r5c10a — Post-failure transaction / authorization forensics

Status: `PASS_READ_ONLY_FORENSICS_FAILURE_BEFORE_PREPARED`. This report describes the single user-reported Mac Terminal formal invocation. It did not rerun the command or preflight, reconcile state, repair code, create a transaction/attempt, or call the model, Agent, RAG or network.

## Failure stage and root cause

The frozen path is `execute_formal → adapter.run → begin_and_commit → _find_identity → read_events → Path.read_text(encoding="utf-8")`. In `begin_and_commit`, `_find_identity` precedes `_append(PREPARED)`. The exact r5c6 transaction journal is absent, so this failure occurred **before PREPARED, COMMITTING, COMMITTED and the authoritative commit point**. The exception is `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb0 in position 37: invalid start byte`.

`_find_identity` enumerates `transaction_root.glob("*.jsonl")` and calls `read_events` on every match. That includes `evaluation/v4_runs/.execution_transactions/._auth-step9_63a_r3-d53bbaa35b1e4522bc4a5f57d42c8ef7.jsonl`, a 4,096-byte AppleDouble Macintosh metadata file, not a JSONL transaction event ledger. Its SHA-256 is `b3f6f26076673352c35b796cdea465d173ef353978b1e6d5ae1417ee2cc25574`, magic bytes are `00 05 16 07`, and the first UTF-8 failure is at offset 37. The corresponding ordinary prior journal is valid JSONL, SHA-256 `76afd557e4559c50090e9e4939a2e52746cbaefff1d4d6bd886206798b2e96fa`, with three events and state `COMMITTED` for a different authorization. The classification is `A_TRANSACTION_SCANNER_READS_NON_EVENT_BINARY_FILE`, confidence `HIGH`; event-file filtering is missing. No suspicious file was modified or removed.

## State after the failed invocation

The exact journal `evaluation/v4_runs/.execution_transactions/auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e.jsonl` does not exist. Transaction event count is 0; `PREPARED=0`, `COMMITTING=0`, `COMMITTED=0`, `ATTEMPT_CLAIMED=0`, `CASE_STARTED=0`; transaction state is `ABSENT` and authoritative commit point reached is `NO`.

The unified `reduce_authorization_lifecycle` reports authorization `auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e` as `ISSUED_EXECUTABLE`, consumed `NO`, consumption count `0`. The reducer's `reusable` field is `true` because there is no durable transaction/consumption evidence. **That is not authority to retry this formal command:** the frozen authorization binds a maximum of one formal attempt, forbids authorization reuse and automatic retry/resume, and the user reports the command was invoked once. Operational `AUTHORIZATION_REUSABLE = NO`; no retry authorization is given here.

Attempt `attempt-step9_63c_r5c6-3401b701486c4fdeb4019b461d024bd4` is prebound but has no attempt ledger (0 matching events across five ledgers). Namespace `heldout-v4-treatment-v3-run-8e4bd0fd803f31b9e0da` and its reservation marker are absent (0 matching events). There are no result/trace files or rows for this attempt. `CASES_STARTED=0`, `CASES_COMPLETED=0`, `FORMAL_V4_CASE_EXECUTED=0`. By the frozen call ordering, the failed identity scan precedes namespace reservation, parent case runner, service creation, and inference; model/Agent/RAG evaluation and HTTP inference were not reached by this invocation. This is scoped to this invocation, not an assertion about unrelated processes.

## Historical integrity and boundary

r10 freeze SHA-256 remains `d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693`; all 20 members match. V3 Agent SHA-256 remains `085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607`, and frozen evaluation identities match. All 55 historical pins match; the Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`. The fresh preflight artifact SHA-256 remains `fbb2f3dfe964bbe500459c4ba58e016f7318bd2ca61c439d902030fd3cb2f35a`; invocation registry SHA-256 remains `01de3e5f9bced87785e851c4071b9eb2f320b43d2a36b1fcf9390b7e9c0ab377`.

`SAFE_TO_RERUN_FORMAL_COMMAND = NO`. `READY_FOR_REPAIR_DESIGN = YES`. Repair, reconciliation, retirement, fresh authorization and any further execution require separate steps. This step produced only the new audit/report and an append-only record entry.
