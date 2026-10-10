# Step 9.63a-r1 — Production transaction integration

Status: `PASS_PRODUCTION_TRANSACTION_INTEGRATION_AND_FREEZE` (infrastructure only). No formal V4 execution was performed.

The actual V3 chain now runs `run_step9_63_v3_formal_execution.execute_formal` → V3 identity adapter → durable transaction `PREPARED` → `COMMITTING` → `COMMITTED` → exact namespace reservation → one-time `ATTEMPT_CLAIMED` → transaction-bound attempt ledger → transaction `CASE_STARTED` → production `/api/chat`. The V3 Agent, case set/order, scoring, model/tool/RAG configuration and evaluation semantics were not changed.

The `COMMITTED` journal line is authoritative and binds authorization, attempt, namespace, runner, Agent, evaluation identity and case-set fingerprint. It is written under the shared allocator/lifecycle lock with exclusive journal creation, file `fsync`, and parent-directory `fsync`. Namespace and attempt files are projections; a crash after commit does not make an authorization reusable. An additional durable `ATTEMPT_CLAIMED` event prevents automatic physical-attempt restart after a crash. Corrupt or ambiguous journal state fails closed for manual reconciliation. This is a process-crash recoverability guarantee on a filesystem honoring these primitives, **not** a proven power-loss atomicity guarantee.

The current executable runner identity is r7, SHA-256 `99ab870303e45497bf750b55f8382912089c2cf80e737b780922695d9906275c`. r6 is superseded for future authorization only; its freeze and historical artifacts remain unchanged. The Step 9.62 authorization is still r6-bound, issued and unconsumed, with count 0. Its attempt and physical namespace do not exist. It cannot be carried forward or used for r7 formal execution. A separate lifecycle/authorization decision is required before final preclearance.

Thirty-three new production-wiring synthetic tests plus 100 focused historical/offline tests passed; `py_compile` passed. The 55 historical pins matched before and after; the Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`. Static current-V3 entrypoint audit found zero unguarded paths. No model, Agent, RAG, case execution, authorization consumption, or real attempt/namespace creation occurred.

`READY_FOR_FRESH_AUTHORIZATION_LIFECYCLE_DECISION = YES`; `READY_FOR_STEP9_63B_FINAL_PRECLEARANCE = NO`.
