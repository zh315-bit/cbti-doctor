# Step 9.34a — Frozen-Baseline Matched Comparison Protocol

Status: `FROZEN_BEFORE_TREATMENT_EXECUTION`  
Comparison class: `POST_HOC_MATCHED_FROZEN_BASELINE`  
Protocol ID: `step9_34a-posthoc-frozen-baseline-matched-v4-v1`

## Design and preserved history

Step 9.32 remains `NOT_EXECUTABLE_WITH_EXISTING_FROZEN_BASELINE`; Step 9.34 remains `FAIL_CLOSED_PROTOCOL_INCOMPATIBILITY`. Their artifacts are unchanged. The fresh-baseline requirement, randomized arm order, and randomized reviewer order cannot be satisfied retrospectively. This protocol is an independent, explicitly post-hoc comparison plan; it does not amend or satisfy the original randomized preregistration.

The existing official V4 baseline is compared with one future frozen treatment run on the exact same 40 case IDs and the same case order. Case-set/order fingerprint: `d930455e417935337a6e3459defbdc3ee3829b71786fbd8438ef092b62429e68`. This is matched order, not randomized order. V4 is development/postmortem evidence for the repair-informed treatment, not unseen generalization evidence.

## Locked baseline and metrics

`step9_34a_baseline_metric_lock.json` binds the official Step 9.30c aggregate, case-level summary, adjudication, rubric, registry, and aggregation audit by path and SHA-256. It preserves the original labels and denominators; no baseline readjudication or rescoring occurred.

Primary metrics M1–M5 and their frozen-registry formulas, baseline numerators/denominators, treatment denominator rules, delta conventions, and improvement directions are in the metric lock. Important denominator distinctions are retained, especially M1's ASK-event denominator versus case-level rates, and M4's oracle-target denominator versus event-level ASK-class counts. M4 uses the frozen V4 necessary-target set and must report target- and case-level discordance.

Completion, harmful/critical failure, and ASK transition definitions are frozen in the JSON protocol. Pair only exact `case_id`; do not fuzzy-match. Report absolute counts/rates, treatment-minus-baseline deltas, and matched improvement/regression/unchanged transitions. Relative changes are applicable only for meaningful nonzero baseline values. No new significance test is authorized.

## Future treatment controls

Before any future authorization, independently recompute and match V4 bytes and manifest, exact case set/order, treatment Agent freeze, Harness, scoring/rubric, Metric Registry, One-shot Rules, model and runtime configuration, tools, RAG, dependency lock, execution limits, session isolation, and treatment-compatible runner. Any unprovable or mismatched item fails closed before first access. The existing runner identity is not presumed treatment-compatible; Step 9.35 must verify it and bind the exact executable runner.

Use one formal attempt only. The future runner must append durably to its ledger, persist first-access and per-case STARTED before execution, preserve per-case raw trace and result, and retain an interrupted attempt without retry or automatic resume. This step issued no authorization, generated no IDs, created no attempt, and generated no executable command. The authorization template is disabled and requires a separate future issuance step and explicit user action.

## Reviewer and claim limitations

Baseline reviewer type is `SINGLE_AI_REVIEWER`, not human; inter-rater reliability was not measured. The exact historical reviewer backend version is not recorded. A future reviewer configuration must be pinned and disclosed before adjudication; do not claim backend-version identity unless independently established. Preserve the five incomplete-formal-but-adjudicatable cases under the existing lineage/adjudication policy; lineage is provenance only and contributes no score.

Permitted future reporting is descriptive: frozen-baseline, case-matched, 40-case development/postmortem comparison, with explicit order and reviewer limitations. Prohibited: randomized-trial or randomized-preregistered claims, causal claims, statistical-significance claims, clinical-effectiveness claims, unseen-generalization claims, and universal superiority claims. A comparative claim is not eligible now; future eligibility requires treatment execution, adjudication, aggregation, and identity/integrity checks to pass. A randomized paired claim is permanently unavailable for this baseline/treatment comparison.

## Current execution state

- Baseline V4 rerun: `NO`
- Treatment V4 executed: `NO`
- V5 created/accessed: `NO` / `NO`
- Comparative results generated: `NO`
- Authorization issued: `NO`
- Formal attempt created: `NO`
