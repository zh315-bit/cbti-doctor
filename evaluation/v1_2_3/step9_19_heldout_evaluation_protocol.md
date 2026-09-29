# Step 9.19 — Held-Out Evaluation Protocol (Pre-registered)

## Research question

Can goal-directed sufficiency and information-value gating reduce low-value information acquisition while preserving task quality and safety on unseen tasks?

CBT-I is the application domain. The evaluation concerns goal-aligned information acquisition, sufficiency, and adaptive action selection. V2 remains a development/regression set; its historical result and future V3 held-out result are separate datasets, not a paired before/after experiment. Any score difference cannot be attributed to Steps 9.16–9.18 from these different case sets alone.

## Frozen candidate and metric registry

The sole current candidate is `post-step9_18-candidate-20260923-01`, Agent aggregate `0dfdbac361d68dfeb577433107395b50f4c2fa8ca59f3e1d226fbd9271a839a7`. The current accepted Harness freeze is `8bc271bebc1c5da5351d517e2bb4a0d1a99fda3de1b713a6197b12f81fad70c7`; scoring aggregate is `f742a8f8af7c8747818dadad81621c15d12d74f50538019913dfe18ab53bf59b`. Full component hashes are in `step9_19_final_candidate_manifest.json`. Metrics and definitions are locked in `step9_19_metric_registry.json` before any V3 access.

## Reporting and interpretation lock

Report three result families separately:

1. **Quality:** frozen five-dimension score and per-task-type scores, completion, answer validity.
2. **Acquisition efficiency:** action counts/rates, ask quality, turns, steps and tool calls.
3. **Safety:** critical/harmful failures and each behavior/safety rate.

No single overall-score threshold determines success. Efficiency reduction is favorable only as a descriptive trade-off and must be read alongside quality and safety. A lower acquisition count cannot compensate for a critical/harmful failure or invalid answer. Show case-level traces and task strata, publish denominators, and mark unmeasured telemetry rather than estimating it.

V2 comparison is historical/development context only. Do not report V2→V3 score deltas as a paired effect or causal impact of repairs. Do not claim universal superiority, statistical significance, clinical effectiveness, or generalization beyond the observed held-out sample.

## Scoring procedure

Apply the frozen rubric at the same dimension weights (20/20/20/25/15), preserve dimension-level scores and rationale, and separately record critical failure types and supporting trace. The rubric has no numeric anchor table; disclose single-reviewer judgment and do not imply calibrated/inter-rater-stable scores. The frozen V2 scorer's case-specific score table is not used for V3. No scoring rule may be revised after V3 is opened; an identified scoring defect invalidates the affected analysis and requires human review, not silent post-hoc change.

## One-shot boundary

The first official completed run under the frozen identity is permanently the **Primary Held-Out Result**. V3 is not yet accessed in Step 9.19. At first authorized access, log UTC timestamp, evaluator, evaluation ID, source identity/hash if supplied by the authorized runner, and access purpose before inspecting case content. A new unique evaluation ID, authorization ID, and attempt ID are required for the formal run; no historical V2/Step 9.8 identity may be reused.

Before execution and after completion, verify Agent, harness, scoring, and configuration hashes. Persist append-only start/finalization ledger, raw trace and per-case result before proceeding to the next case. Preserve the first attempt and every partial artifact. No code/config/rubric change is allowed during execution; no case-specific branches or rerun after reviewing a failure case.

## Failure classification and rerun rule

- `MODEL_API_FAILURE`: provider/network/auth/rate/server/connectivity failure. Record whether a request was attempted/completed; never classify as Agent failure solely from provider errors.
- `HARNESS_FAILURE`: runner, trace, serialization, or persistence failure outside production Agent behavior.
- `AGENT_FAILURE`: production Agent exception, invalid state/action, broken dependency/action semantics, or unsafe behavior. It is an observed system outcome, not grounds for retry.
- `ENVIRONMENT_FAILURE`: interpreter, filesystem, or dependency setup failure before production execution.
- `SCORING_FAILURE`: scoring/adjudication/metric computation failure; do not rerun Agent to repair it.

Automatic retries are prohibited. A new full attempt may be considered only when a documented non-Agent infrastructure/environment failure is proven to have occurred **before any case entered the Agent Loop, before any provider request began, and before any case result/raw case trace was emitted**. Keep the failed attempt immutable, fix only infrastructure, pass focused equivalence/regression, obtain fresh explicit human authorization, and create new attempt identity. Any failure after a case entered the Agent Loop or a provider request began consumes that attempt; do not restart as the same official run. A later recovery requires separate human review/authorization, a new evaluation/attempt identity, and explicit disclosure that the held-out set has been exposed; it cannot replace or delete the original attempt. Scoring failure never triggers an Agent rerun.

No V3 cases, counts, hashes, or outcomes are included in this protocol document.
