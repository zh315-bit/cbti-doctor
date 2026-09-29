# Step 7.4 Paired Evaluation Report

Date: 2026-09-20

## Protocol

The frozen Benchmark V2 manifest was used unchanged: 40 cases, SHA-256 `dfa9b9e5a12b0017fa68d344d01b313ebc29e583b933fbe1e93c125f55ecafd2`. The V1 historical score/trace artifacts were reused; V1 was not rerun. V1.1 was run once with the same runner, fixtures, six-turn limit, and rubric. The raw result is permanently stored in `v1_1_v2_raw_traces.jsonl`.

## Observed Results

| Metric | Frozen V1 | V1.1 first run |
|---|---:|---:|
| Overall score | 63.85 | 65.03 |
| ASK / case | 2.775 | 2.800 |
| Turns / case | 3.45 | 3.525 |
| Steps / case | 3.95 | 4.050 |
| RETRIEVE / case | 0.325 | 0.325 |
| READ_DIARY / case | 0.175 | 0.200 |
| Six-ASK-limit cases | 13 | 11 |
| Critical failures | 2 | 0 (offline review) |

V1.1 ASK quality: necessary 21, useful-but-optional 9, redundant 39, irrelevant 43 out of 112; rates are 18.8%, 8.0%, 34.8%, and 38.4%. Token and exact LLM-call telemetry remain `not_available`.

The V1.1 first-pass frozen-rubric score is a trace-only adjudication, not a new scoring rule. Paired case classifications are in `v1_vs_v1_1_paired_results.jsonl`; 11 improved, 17 unchanged, and 12 regressed under that adjudication.

## Guardrails and Attribution

ASK reduction was not treated as success by itself. V1.1 still has 11 six-ASK-limit cases and a high ASK burden, so the run does not show a clean efficiency improvement. No observed critical premature-answer, unavailable-diary, or unsupported-user-fact failure was recorded in the offline review. Improvements/deteriorations are marked `combined_effect` when extraction, sufficiency, and grounding jointly determine the path.

## Interpretation Boundaries

**Supported interpretation:** this first stochastic V1.1 run shows that the frozen protocol can expose persistent ASK/state failures and allows auditable case-level comparison; it does not support a broad superiority claim.

**Not yet supported:** statistical significance, real-world clinical effectiveness, real-user generalization, or superiority over other systems. The V1.1 run is one synthetic 40-case sample and its trace-only score adjudication has reviewer uncertainty.

## Core Metrics

`V1 → V1.1`: overall 63.85 → 65.03; ASK/case 2.775 → 2.800; six-ASK cases 13 → 11; critical failures 2 → 0 observed. No post-run repair or rerun was performed.
