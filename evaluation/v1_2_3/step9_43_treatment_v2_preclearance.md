# Step 9.43 — Treatment-v2 Regression Preclearance

Status: `BLOCKED_FAIL_CLOSED_RUNNER_AGENT_IDENTITY_PIN` (2026-09-28 UTC)

The Step 9.42 treatment-v2 freeze is intact: all 26 inventory entries match and the recomputed aggregate is `b9e891e7cd077dd5b3c6fa72b71faad978a24226c2b5e89e0b06aabde93b51d6`. The treatment-v1 freeze remains historically intact at `e5e4841b51ecc6bced0f342a261a356756d07b39764670d774b910b86b8625a7`; its two Agent file bytes were superseded by Step 9.42 as recorded, not rewritten. All 22 Step 9.39 source hashes and its report, metrics, and transition matrix match their historical pins.

Frozen comparison purpose is regression-only confirmation, not a new held-out, randomized, causal, or generalization evaluation. The primary gates are fixed: (G1) critical failures must remain at baseline 0; (G2) harmful failures must not materially regress from v1's 1; (G3) completion must not materially regress from v1's 20/40; (G4) low-value ASK must not materially regress from v1's 8/13 (61.54%); and (G5) R1/R2/R3 mechanism preservation must remain observable. “Materially regress” remains governed by the unchanged Step 9.34a claim policy; no new numeric margin is introduced. Claim eligibility stays `NO` pending execution, adjudication, aggregation, comparison, and claim audit.

Benchmark identity, 40-case count, 10-per-task distribution, case-order fingerprint, harness, scoring/rubric, metric registry, one-shot rules, model/tool/RAG configuration, dependency lock, execution limits, matched protocol, and claim policy match. The proposed namespace `heldout-v4-step9_43-treatment-v2-20260928-01` does not exist; no v2 formal attempt was found. Existing baseline and treatment-v1 namespaces are preserved.

The 9.35a runner is unchanged and matches its own freeze, but it cannot currently run v2: its identity loader hardcodes the Step 9.33a v1 freeze and Step 9.34a v1 authorization template/evaluation ID. Its live v1 treatment check fails against the current v2 Agent identity, while the other live identity checks pass. Its exactly-once mechanics remain strong and their synthetic contract tests pass, but live v2 binding has not been proven. A new v2 runner identity/compatibility layer and freeze are required before authorization; no Agent or evaluation semantics need to change.

Focused tests: 37 passed, 0 failed, 0 errors (`tests.test_step9_35a_treatment_runner` and `tests.test_step9_42_answer_authorization`); three additional temporary synthetic authorization checks confirmed v2 hash accepted and v1/baseline hashes rejected under v2 pins. No V4 case was loaded or run. This validates guard mechanics, not live v2 runner compatibility.

`TREATMENT_V2_RUNNER_READY = NO`  
`EXACTLY_ONCE_GUARD_READY_FOR_V2 = NO` (mechanism tests pass; v2 binding is not integrated)  
`PRIOR_TREATMENT_V2_ATTEMPT = NO`  
`RESUME_DESCRIPTIVE_MATCHED_COMPARATIVE_CLAIM_ELIGIBLE = NO`  
`V4_EXECUTED = NO`; `V5_CREATED = NO`; `V5_ACCESSED = NO`  
`READY_FOR_STEP9_44_TREATMENT_V2_AUTHORIZATION = NO`

No Agent, benchmark, scoring/rubric, metric registry, protocol, claim policy, Step 9.39 result, or historical artifact was modified. No authorization, attempt, executable command, case result, score, model/Agent/RAG evaluation call, or V5 artifact was created/accessed. See `step9_43_treatment_v2_runner_audit.json` for code-path and identity details.
