# Step 9.19 — One-Shot Held-Out Rules

1. V3 remains sealed until a separate explicit run authorization. Step 9.19 reads no case content and records no V3 hash.
2. On first authorized V3 access, append an access record with UTC time, evaluator, purpose, evaluation identity and available source-manifest identity before opening cases.
3. Before first case, verify the Step 9.19 final-candidate Agent aggregate, accepted Harness freeze, Scoring aggregate, model/runtime configuration and required preflight. Any mismatch is a fail-closed abort; do not refresh this manifest silently.
4. One formal run uses a new evaluation ID, authorization ID and attempt ID bound to all frozen hashes. Exactly one case order/fixture protocol is used; no case selection, expected-path branching, or result cherry-picking.
5. Recheck Agent, Harness, Scoring and configuration hashes after the run. Any mismatch invalidates the run pending review.
6. Persist append-only `PREPARED → STARTED → COMPLETED / FAILED_*` lifecycle, per-case traces and results. The STARTED event is durable before the first real Agent Loop call. Persist failures and partial output; never delete or overwrite attempts.
7. No Agent, prompt, tool, model configuration, harness, case, or scoring edits during the run. No automatic retry and no rerun after inspecting a failed case.
8. Classify interruptions as `MODEL_API_FAILURE`, `HARNESS_FAILURE`, `AGENT_FAILURE`, `ENVIRONMENT_FAILURE`, or `SCORING_FAILURE` using trace/exception evidence. Provider/harness exceptions are not Agent failures absent evidence of a production-path contract violation.
9. Only a proven non-Agent environment/harness failure before Agent Loop entry, provider request start, and case-result/trace emission may be considered for a new explicitly authorized attempt. Preserve the original attempt and create a new attempt ID. Any later recovery is a separate disclosed evaluation after human review and cannot supersede historical artifacts.
10. The first completed official run under the locked identity is the immutable Primary Held-Out Result. V2 is reported separately as historical development evidence, never as a paired control.
11. The frozen rubric weights are 20/20/20/25/15. Report score, acquisition efficiency and safety separately; no single success threshold. Critical/harmful failures are not offset by a better score or fewer actions.
12. Missing token/latency/model-call telemetry is `NOT_MEASURED` / `NOT_AVAILABLE`, never estimated.
