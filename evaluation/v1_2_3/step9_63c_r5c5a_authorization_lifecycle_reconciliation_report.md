# Step 9.63c-r5c5a — Authorization Lifecycle Reconciliation

**Status: `PASS_READ_ONLY_LIFECYCLE_ROOT_CAUSE_IDENTIFIED`**

## Finding

The two steps referred to different authorization identities. Step 9.63c-r5c4 retired the r8 authorization `auth-step9_63c_r4-4b2749ce10014634ac6de155d37ec6a9`; it did not retire the r7 authorization that r5c5's scan listed, `auth-step9_63a_r3-d53bbaa35b1e4522bc4a5f57d42c8ef7`.

The r5c4 retirement event is present and valid in the sole lifecycle JSONL ledger at `evaluation/v1_2_3/authorization_lifecycle_events.jsonl`, bytes 2,385–3,856 (1-based inclusive). Its unique event id is `retire-c1184275045745ce86c084f0106b4632`, and it binds the unchanged r8 manifest SHA-256 `f02cec713ce0a8aebc109ff898450f0365cf4f8b91b5330e08fae556cc83cc2a`. The pinned retirement determination identifies `SUPERSEDED_RUNNER_FREEZE`. The frozen 1,161-byte prefix remains intact. This is not a missing-event or wrong-ledger write.

The target r7 manifest still reads `ISSUED_NOT_CONSUMED`, but that is immutable issuance evidence, not current execution state. Its transaction journal at `evaluation/v4_runs/.execution_transactions/auth-step9_63a_r3-d53bbaa35b1e4522bc4a5f57d42c8f7.jsonl` (SHA-256 `76afd557e4559c50090e9e4939a2e52746cbaefff1d4d6bd886206798b2e96fa`) contains durable `PREPARED → COMMITTING → COMMITTED`; the final event says `commit_point=true` and `authorization_irreversibly_burned=true`. The matching derived namespace marker exists. There is no attempt-ledger `AUTHORIZATION_CONSUMED` projection, `ATTEMPT_CLAIMED`, or `CASE_STARTED`; the namespace contains only the reservation marker, with zero case outputs/traces. The transaction protocol and the earlier Step 9.63c-r1 forensic audit classify this as `COMMITTED_BUT_EXECUTION_NOT_STARTED`, burned and non-reusable. Its transaction helper returns `COMMITTED_READY_FOR_EXECUTION`, while the frozen r2 incident disposition forbids auto-resume; that wording/projection mismatch requires explicit lifecycle handling, not execution.

## Why r5c5 reported one active authorization

r5c5's scan uses `scripts/preflight_step9_62b_mac_local.py:active_authorizations`. It selects manifests whose immutable fields say `ISSUED_NOT_CONSUMED` and `consumed=false`, then checks attempt-ledger consumption and the lifecycle retirement JSONL. It does not inspect `.execution_transactions`. Thus it reports the target r7 identity as active even though the authoritative transaction journal has already irreversibly burned it. This is a false positive for current r9 executability, not evidence that the r5c4 retirement event failed.

The lifecycle state is currently distributed across different evidence types: manifests establish issuance identity; `authorization_lifecycle_events.jsonl` records retirement; the transaction journal is the frozen durable commit/burn authority; attempt ledgers project consumption; namespace markers prove reservation. Only one retirement ledger exists, but there is no unified event reducer. The formal execution path does check transaction and retirement guards; its read-only audit and the old issuer also call the incomplete active-manifest enumerator. Therefore `SINGLE_AUTHORITATIVE_LIFECYCLE_SOURCE = NO` as a single-file/reducer property, and `LIFECYCLE_SOURCE_DIVERGENCE = YES`.

Across 15 authorization-named manifest artifacts, 12 contain issued identity records; three are explicitly not-issued/identityless. The inventory is in `step9_63c_r5c5a_authorization_inventory.json`. Under the current r9 binding there are zero reusable/executable issued authorizations, but one committed, irreversibly burned pre-case transaction remains pending manual no-resume disposition. The r5c5 legacy enumerator's raw count is 1. These values are not interchangeable.

All 55 historical pins match; the 1,161-byte frozen lifecycle prefix SHA-256 remains `ca168f6939c4697a7a7bccc0b365b414d9a0e632f40de4242eb0a47e2d985285`. Step 9.58 provenance remains `PRESENT_AND_DOCUMENTED`. No lifecycle or historical bytes were modified. No authorization, attempt or namespace was created; no preflight, model/Agent/RAG/HTTP or V4 case ran.

## Safe next path

Do not append a retirement event for the target: the existing committed transaction already makes the identity non-reusable, and a duplicate retirement would misstate the transition. A separately authorized repair should implement a fail-closed reducer over manifests, retirement events, committed transaction journals, attempt-consumption ledgers and namespace markers; make the issuer/preflight/audit all consume that same reducer; and classify the target as burned/committed-pre-case with no auto-resume. Preserve the old manifest, transaction journal, namespace marker and retirement history. Then rerun only the fresh-authorization eligibility audit. No such repair was performed here.

`READY_TO_RETRY_R5C5 = NO`.
