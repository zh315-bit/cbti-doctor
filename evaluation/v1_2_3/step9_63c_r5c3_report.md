# Step 9.63c-r5c3 — Runner Freeze / Authorization Lifecycle Bootstrap Dependency Repair Design

Status: `PASS_DESIGN_ONLY_BOOTSTRAP_DEPENDENCIES_IDENTIFIED` (2026-10-06 UTC). This step performed read-only inspection and authored design artifacts only; it did not implement code or execute tests.

## Finding

The bootstrap incompatibility is real, but the exact cycle is narrower than the r5c2 summary implied. The formal entry and identity adapter hard-code r8, while the formal-entry bytes have changed from their r8 frozen hash. The available r5 Mac preflight is tied to the old r8 authorization and cannot prove readiness for r9. Separately, `historical_pins_match()` checks both an append-only prefix and the complete current ledger length/hash; a legitimate retirement append therefore breaks the helper's full-file equality. These are the confirmed blockers to a coherent r9 transition.

The retirement implementation itself does **not** require the current runner to match the historical authorization. It checks the frozen lifecycle contract, a pinned non-reuse determination, exact unconsumed manifest shape, absence of transaction/attempt/reservation/namespace, and appends a terminal event under the shared lifecycle lock with file and directory fsync. Therefore it can be the independent lifecycle authority if the design strengthens/records the proof that the old manifest was issued against its exact historical r8 freeze. Retirement remains non-consumption: consumed stays false and the count stays zero.

No dedicated r8/r9 freeze-builder function or active-authorization-count gate in a freeze builder was found in the inspected code. The current preflight/authorization eligibility gates do inspect active executable authorization state, but that is a fresh-authorization concern, not evidence that passive freeze creation itself is gated. Any later builder should remain non-executing and should not inherit an unnecessary active-auth gate.

## Recommended design

Use Option C: an independent lifecycle authority verifies immutable historical issuance binding and current terminal eligibility, but does not compare the old authorization to current runner bytes. Create/freeze r9 first as a passive identity record; then retire the r8 authorization against its historical manifest and freeze; verify the append-compatible ledger prefix; only in a distinct later step issue a new r9 authorization. Never migrate r8 authority to r9.

Replace whole-ledger pin equality with a prefix-length + prefix-SHA proof (`current_length >= historical_length` and `SHA256(current[:historical_length]) == pinned_prefix_sha`). Validate every appended event and keep the existing lock, fsync, terminal-state, collision, and exactly-once controls. Preserve the single namespace authority `TRANSACTION_RESOLVED_EXECUTION_NAMESPACE` and existing transaction identity fields.

The minimal implementation candidates and risks are specified in `step9_63c_r5c3_bootstrap_repair_design.json`; the 20 future synthetic tests are designed, not run, in `step9_63c_r5c3_synthetic_test_plan.json`.

## State and boundary

- Old authorization remains `ISSUED_NOT_CONSUMED`, consumed `NO`, count `0`; no retirement event appended.
- No r9 freeze or new authorization; no attempt or namespace.
- V3 Agent, V4 benchmark, scoring, metrics, one-shot rules, and evaluation semantics were not changed.
- No test, model, Agent, RAG, HTTP, preflight, or formal V4 execution occurred.
- The old r5 preflight artifact provenance remains `E_STILL_UNPROVEN`; it remains unacceptable for formal execution.

Artifacts: `step9_63c_r5c3_bootstrap_dependency_analysis.json`, `step9_63c_r5c3_bootstrap_repair_design.json`, and `step9_63c_r5c3_synthetic_test_plan.json`.
