# Step 9.63c-r3 — Parent Namespace / Transaction Boundary Repair

Status: `PASS_IMPLEMENTATION_OFFLINE_VALIDATION_ONLY`. This step did not issue an authorization or execute V4.

The r2 Option A design is implemented. The transaction journal and namespace allocator continue to define the one attempt-scoped execution root. The adapter passes that root explicitly to the parent; the parent verifies it equals `RUN_ROOT / derive_namespace_id(evaluation_id, authorization_id, attempt_id)` and that the reservation marker binds the same evaluation, authorization, attempt, namespace and transaction. Both parent authorization checks and the exclusive output-directory write use that exact root. The historical global evaluation directory no longer creates a false collision, while an already occupied current attempt output still fails closed.

The journal's `COMMITTED` event still means the execution identity is permanently claimed and the authorization irreversibly burned—not formal evaluation completion. The parent still claims the attempt once, exclusively creates the inner directory/ledger/results/traces, and gates each production case call with a durable `CASE_STARTED` event. No commit ordering, scoring, case content, model/tool/RAG configuration or Agent behavior changed.

The new future-authorization runner revision is `r8`, frozen at `step9_63c_r3_runner_freeze.json` (SHA-256 `86be96061d8c1cfbf769e21aac388cf2a308f53f6380f67c401d4c64b0bf4e6b`). It supersedes r7 only for a separately authorized future execution. The old r7 freeze, committed failed transaction, reservation marker, authorization and attempt remain untouched and non-reusable.

Offline verification: 13 new synthetic tests, including an actual parent-validator reproduction of the original collision and a stubbed production case-call sentinel reached after durable synthetic `CASE_STARTED`, and 217 total focused tests passed with zero failures/errors. `py_compile` passed. Read-only V3 identity preflight reports all frozen checks true. The static/dynamic entrypoint audit found zero unguarded formal V3 case paths. Fifty-five historical pins match; the Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`. The prior failed journal and marker hashes remain `76afd557e4559c50090e9e4939a2e52746cbaefff1d4d6bd886206798b2e96fa` and `37179292afafb149971961f5d50c82bf2ff42f1bfac9f7db56e5701e3017c7e9`.

`READY_FOR_FRESH_AUTHORIZATION_LIFECYCLE = YES` means infrastructure eligibility only. No new authorization, attempt, real namespace, model/Agent/RAG evaluation, or formal V4 case was created or executed here.
