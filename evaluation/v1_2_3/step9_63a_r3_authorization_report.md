# Step 9.63a-r3 — Fresh r7 authorization issuance only

Status: `PASS_FRESH_R7_AUTHORIZATION_ISSUED_NOT_CONSUMED`.

Exactly one new executable authorization was issued: `auth-step9_63a_r3-d53bbaa35b1e4522bc4a5f57d42c8ef7`. Its manifest SHA-256 is `1514438d0afe23a39de2a696e9ea5bd97faac4dd546a88cdbd7b91f450046345`. It binds only the r7 runner, the frozen V3 Agent and evaluation identities, the frozen 40-case set/order (10 cases per task type), the lifecycle contract, and the production transaction commit-point contract. Status is `ISSUED_NOT_CONSUMED`, with consumption count `0`.

The prebound attempt `attempt-step9_63a_r3-3b66e84b7b1f4f538e87156c85b0e7dd` and namespace `heldout-v4-treatment-v3-run-2b23978e98ac414ca26e` are identities only. Neither was created or reserved. The old r6 authorization `auth-step9_62-e796755748e14418b9da641f5d6c15e2` remains terminally `RETIRED_UNCONSUMED_NON_REUSABLE`; it is not executable or reusable. Active executable authorization count changed from `0` to exactly `1`.

Before the successful issue, an AppleDouble `._` sidecar caused a conservative historical-artifact scan to fail closed before manifest creation. The scan was restricted to real JSON artifacts, covered by a synthetic test, and the successful issuance occurred once. No real duplicate-issuance command was invoked; synthetic duplicate and binding-mismatch tests passed. The new issuer reuses the canonical lifecycle lock and fresh-identity guard, then exclusive-creates and fsyncs the manifest. It does not change the frozen r7 runner or evaluation semantics.

Offline focused regression: **170 passed, 0 failures, 0 errors**; compilation passed. All 55 historical pins matched using the frozen prefix for the append-only lifecycle ledger. The ledger's full SHA remains the authorized Step 9.63a-r2 value `f573185bc39c26e14306ff1ac7c1a3e3a64e9940cb1e6f089a08942b96cb044d`; the Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`.

No connectivity probe, DeepSeek request, model inference, Agent/RAG evaluation, transaction commit, V4 case, adjudication, aggregation, or comparison occurred. `READY_FOR_STEP9_63B_FINAL_PRECLEARANCE = YES` means only that a separate non-consuming preclearance may now be requested; it does not authorize execution in this step.
