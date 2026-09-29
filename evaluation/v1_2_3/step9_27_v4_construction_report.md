# Step 9.27 — V4 Construction Report

Status: `SEALED_NOT_EVALUATED`.

Created a 40-case dataset using the Step 9.26 frozen protocol and the generic runner fixture contract. Runtime-visible fields are limited to case ID, task type, user query, explicitly seeded initial session facts, follow-up fixtures, and diary availability/data. `evaluation` contains evaluator-only expectations and must not be passed into Agent runtime context.

## Static results

- Cases: 40; task distribution is KQ 10, CA 10, PD 10, DA 10.
- Difficulty: easy 3, medium 19, hard 18. Step 9.26 required task balance, not a difficulty quota.
- Language labels: English 14, colloquial Chinese 11, distributed Chinese 7, brief Chinese 5, mixed Chinese-English 3.
- Diary resources: available 9, unavailable 31. One personalized case explicitly seeds prior session facts; other user facts remain in the literal query or the tool fixture.
- Schema and typed fixture checks: pass. Dates are ISO dates; numeric sleep-duration values are minutes; missing values remain null/absent. Unavailable resources carry no facts.
- Coverage matrix includes direct bounded answers, necessary and optional ASK contrasts, evidence and diary dependencies, unavailable resource behavior, evidence grounding, semantic status, mixed missing information, and projection integrity.

## Frozen identity

Before sealing, all 26 Agent inventory entries matched Step 9.26; Harness, Scoring, Metric Registry, and One-shot Rules also matched. No Agent, Harness, Scoring, metric, rule, V2, or V3 files were changed. Production Agent/config search found no V4 ID, V4 dataset lookup, or expected-action lookup.

No Agent was executed, no model was called, no V4 evaluation or authorization was started. The V4 runner remains a separate future preparation task.

Dataset SHA-256 is `8b8c72092fcd7544e69d5d2ecd13610c7bb4c14210fca330698b3e5ab3f01d7f`; immutable seal is recorded in `evaluation/benchmarks/benchmark_v4_manifest.json`.
