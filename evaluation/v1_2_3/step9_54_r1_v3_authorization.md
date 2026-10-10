# Step 9.54-r1 — Treatment-V3 Formal V4 One-Shot Authorization

Authorization-only audit passed. Authorization `auth-step9_54r1-b43c3282fd9344f6a7c3548e376ec6d1` is `ISSUED_NOT_CONSUMED` for evaluation `heldout-v4-step9_53-treatment-v3-20260930-01`, purpose `REGRESSION_ONLY_CONFIRMATION`, with claim scope `FROZEN_MATCHED_DEVELOPMENT_REGRESSION_ONLY`. The authoritative runner freeze is Step 9.53 r2 only.

The V3 Agent identity is `085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607`; Step 9.53 runner freeze r2 SHA-256 is `4c4749cde621ed989ec9c0dc77a194931079cdaee7f20dc6ba5668afee46eb43`; runner SHA-256 is `02e37b60469f0fb36979b883be45cf3231d3088fc4c48ce21dacdf6e3d0d9b6e`. Frozen V4 dataset, manifest, Harness, Scoring/rubric, Metric Registry, One-shot Rules, model/tool/RAG configuration, case set/order, and task distribution match. Claim scope excludes causal effect, statistical significance, unseen generalization, external validity, and V5 performance.

Historical integrity passed: Step 9.50 evaluation artifact pins 43/43; Step 9.51a recorded checks 183 pre-test and 40 post-test with zero mismatches; Step 9.48 frozen inputs/outputs 61/61; Baseline/V1/V2 formal run files 9/9; the separately frozen Step 9.37–9.39, 9.45a–9.47 artifacts/lineage rechecks 75/75. Step 9.51-r1, 9.52, and 9.53 r2 identity/audit pins also match. Step 9.51 V3 implementation source revisions are the declared treatment changes; historical result, trace, adjudication, aggregate, and comparison artifacts remain byte-identical.

The frozen parent runner requires `attempt_id` in the authorization manifest and requires the same ID at consumption. Therefore an attempt identity was preallocated (`attempt-step9_54r1-d2e272e499e24f5f82096a01b2bf9fe9`) as a protocol binding. This is not a formal attempt: no output namespace, execution ledger, case result, or raw trace was created.

The authorization has not been consumed. No V4 case was executed; no model/Agent/RAG case execution, score, adjudication, aggregation, or comparison occurred. V5 remains untouched. No Step 9.55 command was run; this authorization does not automatically trigger execution. Any run must separately consume this one-shot authorization under the frozen runner protocol.

See `step9_54_r1_v3_authorization_audit.json` and `step9_54_r1_v3_authorization_freeze.json` for the complete gate report and artifact hashes.
