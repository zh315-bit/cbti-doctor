# Step 9.20a — V3 One-Shot Runner Preparation Audit

## Identity and scope

The new `scripts/run_step9_20_v3_heldout.py` is a separate execution wrapper around the existing production `/api/chat` factory, AdaptiveChatService, Agent Loop and tool adapters. The Step 9.19 parent Harness files remain unchanged. The wrapper has its own SHA-256 in `step9_20a_v3_runner_freeze.json`, bound to the Step 9.19 final-candidate manifest and accepted parent Harness aggregate. No Agent, scoring or metric file was changed.

Import, frozen-identity verification, and `--local-preflight` do not inspect V3. The preflight checks the frozen Agent/Harness/Scoring/Metric/Rules hashes, credential presence, DNS/HTTPS, a minimal model probe and a synthetic `/api/chat` smoke. This step did not invoke the preflight's real-model path. Its command is saved separately for the user's local environment.

## Formal execution contract

Formal execution requires matching `--evaluation-id`, `--authorization-id`, `--attempt-id`, and an authorization file with `ISSUED_NOT_EXECUTED` status. The file must bind all frozen hashes, the separately frozen runner hash and a successful local real-preflight artifact. The supplied template has null IDs and `TEMPLATE_NOT_ISSUED`, so it cannot execute. An existing attempt ledger blocks another attempt under the same evaluation identity.

After an authorized invocation, the runner creates an append-only, exclusive ledger and initializes the production service. It writes `V3_FIRST_ACCESS` with UTC time, evaluator, purpose and source identity **before** reading V3 bytes. It records the source hash after reading. Each case enters `STARTED` before `/api/chat`; raw state histories, action paths, lineage, responses, latency and per-case result records are fsynced before moving to the next case. Tool data reaches the Agent only through the existing tool interface; follow-up facts are released only after the corresponding ASK. There are no case-ID branches.

Provider token usage is recorded as `NOT_MEASURED` because the current production stack does not expose a reliable complete per-case total. Dimension scores, critical failures and failure classification are marked `PENDING_FROZEN_RUBRIC_REVIEW` / `PENDING_REVIEW` for later single-reviewer adjudication under the locked rubric; the runner does not manufacture numeric scores. Model, harness, Agent and environment exceptions are recorded in the append-only ledger with failure stage and type. The runner does not retry.

## Constraints and verification

The V3 benchmark schema and contents remain sealed. The runner accepts the frozen V2-style fixture contract generically (`case_id`, `user_query`, `task_type`, `diary_facts`, `follow_up_facts`, optional `initial_session_facts`); if the sealed V3 schema differs, it fails closed and preserves the attempt. No Benchmark V2 or V3 case was executed during preparation.

The runner's freeze is a distinct child of Step 9.19 Harness freeze. It does not rewrite that historical freeze or itself authorize a run. The local preflight must be executed in an environment with the real credential; no authorization ID has been issued.

Offline synthetic checks passed: the locked domains and runner hash match; the unsigned template is rejected; a synthetic fixture is read only after the durable first-access event; the raw trace and case result are persisted; a second attempt under the same evaluation ID is refused. A synthetic case exception is preserved as `FAILED_AFTER_PARTIAL_EXECUTION` and cannot be retried. The focused guard/lineage/authorization suite passed **34/34**. The first test invocation used a slow dependency import; the focused test was adjusted to isolate that import and the completed rerun passed. Neither invocation called a real model or opened V3.
