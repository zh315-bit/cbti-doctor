# Step 9.59a — r4 Parent Authorization Identity Binding Repair

**Status: PASS_INFRASTRUCTURE_REPAIR_AND_NON_CONSUMING_PRECLEARANCE**

Root cause was confirmed in the V3 adapter's call path: it invoked the frozen Step 9.35a parent `validate_authorization()` without passing the V3/r4 frozen bindings. The parent consequently used its default historical binding context, whose treatment-agent check failed and whose runner identity represented the parent runner rather than the authoritative V3 adapter. The Step 9.59 failure remains immutable and fail-closed; its candidate authorization and attempt IDs are burned and unusable.

The adapter now validates the current r5 runner freeze and passes that same recomputed binding map explicitly to the parent's existing strict validator. Exact hash equality remains enforced; no alternate runner identity is accepted. The adapter binds to the r5 freeze at `evaluation/v1_2_3/step9_59a_v3_runner_freeze_r5.json` (runner SHA-256 `7e75a80ad529c3df67a775287ca0aa9ada4f5ae7b18d1a0b85e593006362fe12`). The r4 freeze remains preserved as historical evidence. Agent, benchmark, evaluation semantics, scoring, metrics, and one-shot behavior were not modified.

The read-only r5 preclearance passes the Agent, all frozen evaluation identities, validator binding, case count/order, connectivity recovery evidence, exact-once, and namespace isolation checks. Focused offline regression: **60 passed, 0 failures, 0 errors**. Historical integrity checks rehashed 26 pinned files/outputs with zero mismatches; the Step 9.58 provenance gap remains `PRESENT_AND_DOCUMENTED`, and the Step 9.59 failed authorization audit remains unchanged.

No authorization or attempt was issued/created/consumed. No V4 case, model/Agent/RAG evaluation, adjudication, aggregation, comparison, or V5 access occurred. `READY_FOR_FRESH_V3_AUTHORIZATION=YES` is preclearance only; it is not authorization. Stop here; do not retry Step 9.59 or run Step 9.60.

See the JSON audit, regression test report, r5 freeze, and r5 preclearance for exact bindings and results.
