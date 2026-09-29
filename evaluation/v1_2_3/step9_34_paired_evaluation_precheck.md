# Step 9.34 — Paired Evaluation Precheck and Protocol Freeze

**Status: BLOCKED_FAIL_CLOSED_PROTOCOL_DESIGN_CONFLICT.** This is a read-only identity and integrity precheck. No benchmark execution, model call, treatment attempt, paired result, or V5 activity occurred. No authorization is issued.

## Verified identities and baseline records

- Baseline Agent aggregate: `4e2bffea0d7eaa9299074a960df84a1806b3ae9d4930662929abc58ca5b2ae79` (matches Step 9.32 baseline freeze and Step 9.29b authorization/run records).
- Treatment Agent aggregate: `e5e4841b51ecc6bced0f342a261a356756d07b39764670d774b910b86b8625a7` (current inventory recomputed against the Step 9.33a freeze; match). Its intended changes are the preregistered R1/R2/R3 implementation; no case-ID or expected-action branch was found.
- Baseline evaluation/attempt/authorization: `heldout-v4-step9_28-20260925-01` / `heldout-v4-step9_28-20260925-01-attempt-step9_29b-5370d36a64d84a3da4f2585e9b57055a` / `heldout-v4-step9_28-20260925-01-auth-step9_29b-7c9d4ba6c7b649e69a64f9b9e68175db`. Ledger ends `COMPLETED`, 40 started and 40 completed. Step 9.30a frozen input manifest matches all referenced input hashes and sizes.
- Case results and raw traces each contain 40 unique records; both ordered case-ID sequences match each other and the sealed V4 dataset. Their order fingerprint is `d930455e417935337a6e3459defbdc3ee3829b71786fbd8438ef092b62429e68`; distribution remains 10 per task.
- Sealed V4 SHA-256: `8b8c72092fcd7544e69d5d2ecd13610c7bb4c14210fca330698b3e5ab3f01d7f`. Runner source/freeze, harness, rubric/scoring, Metric Registry and one-shot hashes match the baseline authorization and run ledger. Adjudication SHA `85d436955fe2b7ea2448bce94fcb4443d7004140c5b0c4090283f7a0907cd645` matches its Step 9.30b freeze; aggregate audit is `PASS_DETERMINISTIC_AGGREGATION`, with 40 adjudicated cases. Reviewer type is `SINGLE_AI_REVIEWER`, not human; inter-rater reliability remains `NOT_MEASURED`.
- The treatment inventory has the same 26 paths as the baseline inventory. Every non-Agent entry (including model/config, RAG, runtime fingerprint, tools, and dependency lock) matches. Differences are confined to the intended Agent implementation paths.

See `step9_34_baseline_treatment_identity.json` for exact paths, hashes, counts, fingerprints and checks.

## Fail-closed blockers

1. **Existing baseline conflicts with the frozen design.** Step 9.32 preregistration `eae334625468d9a844273a3771767a2a733e240ba2eecc9abe19df30f6100e99` requires a fresh baseline arm reconstructed from the immutable Step 9.32 snapshot and explicitly says the prior official one-shot result must not be the only baseline arm. This request prohibits rerunning baseline V4 and directs reuse of that existing one-shot result. Both cannot be honored simultaneously. The protocol also predeclares randomized case/arm order; the already-completed baseline was run in fixed dataset order, so the pair cannot be randomized retroactively. Replacing the preregistered plan now would be a post-hoc protocol change.
2. **No treatment-compatible paired runner is frozen.** The current frozen runner `scripts/run_step9_28_v4_heldout.py` is bound to the baseline final candidate identity. Its authorization validator fails closed against the treatment identity. Step 9.32 also requires the same paired runner version/hash across both arms; preparing a new treatment-capable runner now would not make the already-completed baseline arm have used that runner.
3. **Reviewer blinding/order cannot be reproduced.** The existing baseline has already been adjudicated by a single AI reviewer. The preregistered paired process requires the same reviewer identity/type and blinded randomized A/B order. A later treatment-only adjudication cannot retroactively create that paired blinded order. No attempt was made to re-adjudicate or alter labels.

Consequently, the preregistered metric definitions and claim policy are preserved unchanged, but **no executable paired protocol is frozen**. `step9_34_paired_protocol.json` records the conflict and is explicitly non-executable. The paired metric registry is only a faithful projection of the Step 9.32 preregistration and frozen Step 9.26 registry; it does not cure or amend the study design. The authorization template is disabled and contains no IDs.

## Frozen metric and claim semantics

M1–M5 formulas, numerators/denominators, directionality, case-level pairing fields, secondary metrics, lineage treatment, reviewer type, and descriptive claim policy are carried forward exactly as specified in Step 9.32 and the frozen registry. No significance test or post-hoc metric is introduced. V2/V3 remain `NOT_COMPARABLE`. Five `INCOMPLETE_FORMAL` lineage cases remain adjudicatable under the existing frozen Step 9.30a.2/9.30b procedure; lineage is provenance only and earns no extra score.

## Integrity and stop

`BASELINE_V4_RERUN=NO`; `TREATMENT_V4_EXECUTED=NO`; `V5_CREATED=NO`; `V5_ACCESSED=NO`. Benchmark, scoring rubric, Metric Registry, Step 9.32 paired protocol/hypotheses, and all baseline run/adjudication/aggregate artifacts remain unchanged. `READY_FOR_STEP9_35_TREATMENT_AUTHORIZATION=NO` until the preregistration/design conflict and compatible paired-runner/reviewer constraints are resolved through an explicitly authorized protocol path. Stop here; no treatment command or authorization was generated.
