# Adaptive Agent V1 Baseline Freeze

## Baseline identity

- **Baseline name:** `adaptive-agent-v1-baseline`
- **Frozen on:** 2026-09-19 (America/New_York)
- **Purpose:** the immutable comparison point for subsequent Adaptive V1.x/V2 work.
- **Git revision:** `not_available` — this working tree is a Git repository but has no `HEAD` commit. No tag or commit was created in this freeze.
- **Suggested future tag, only after a user-approved commit exists:** `adaptive-agent-v1-baseline`

This document freezes metadata and artifact references. It does not claim that the snapshot is a release, alter version history, or overwrite any prior evaluation run.

## Architecture snapshot

| Concern | Frozen implementation |
|---|---|
| Architecture | `AdaptiveChatService` persists an `AdaptiveAgentState` per session and delegates a single-action-at-a-time `AdaptiveAgentLoop` through Flask `/api/chat`. |
| Requirements | `configs/requirements.yaml`, loaded/resolved by `adaptive_agent/requirements.py`; task type informs requirements, not direct actions. |
| State schema | `adaptive_agent/state.py`: goal, task type, facts/provenance, missing information, evidence, sufficiency, resource status, candidates and action history. |
| Input Understanding | `adaptive_agent/input_understanding.py`: structured LLM goal/task extraction followed by deterministic validation/normalization and provenance-bearing fact merge. |
| Sufficiency estimator | `adaptive_agent/sufficiency.py`: separate user/evidence sufficiency, goal-specific decision missing fields and resource readiness. |
| Candidate generation | `adaptive_agent/candidates.py`: concrete ASK/RETRIEVE/READ_DIARY/ANSWER candidates with qualitative relevance, impact, redundancy and cost. |
| Decision policy | `adaptive_agent/policy.py`: heuristic choice among candidates; it does not implement learned policy or fixed task-type-to-action mapping. |
| Tool interfaces | `adaptive_agent/tools.py`: `RETRIEVE(query) → RetrievalResult` and `READ_DIARY(requirements) → DiaryResult`; unavailable diary facts remain unavailable. |
| State update / loop | `adaptive_agent/state_update.py` and `adaptive_agent/runner.py`: tool results merge into State, then requirements/sufficiency/candidates are recalculated before next action. |
| Answer generation | `adaptive_agent/answer_generation.py`: prompts only with goal, State facts, relevant evidence, data-derived claims and answer scope; post-processing removes unsupported quantitative claims. |
| Session/API integration | `adaptive_agent/service.py` and `main_flask.py`: `/api/chat` persists ASK state and records evaluation data. |

## Frozen evaluation specification

- **Benchmark:** `evaluation/benchmark_v1_1.yaml`, `benchmark_version: 1.1`, frozen design.
- **Scoring:** `evaluation/benchmark_v1_1_scoring.md`; five dimensions totaling 100, with independent critical-failure records and primary/downstream attribution.
- **Primary runner/adapter:** `scripts/run_step5_5_capability_matched.py`.
- **Primary baseline run:** `evaluation/runs/step5_5-controlled-valid-2026-09-19/`.

## Capability-matched baseline metrics

These are the official V1 baseline metrics for the requested primary subset, not claims about general clinical performance.

```text
n = 8 capability-matched cases
Score                 86.3 / 100
ASK / case             1.25
RAG / case             0.50
Tool calls / case      0.50
Turns / case           2.25
Steps / case           2.75
Critical Failures         0
```

Source: `evaluation/runs/step5_5-controlled-valid-2026-09-19/matched_paired_results.jsonl` and `cost_metrics.json`.

### Full-system resource result (reported separately)

DA-01 and DA-02 are not included above because Fixed lacks `READ_DIARY`. Adaptive completed both as `READ_DIARY → ANSWER`: DA-01 loaded seven diary entries and produced a bounded analysis; DA-02 retained unavailable status without fabricating diary facts. These are Full-System capability observations, not Decision Policy-only baseline metrics.

## File manifest

The lack of a Git `HEAD` is compensated only for reproducibility of this local snapshot by the following SHA-256 manifest. A future comparison must either use the same hashes or disclose changes as confounds.

```text
d502f1311ffd176ff1570f8a4eb56605db1de94a8188cf5cc59305f85b7ea5a1  adaptive_agent/state.py
56533b3098a60c642176aa3edc909c94cc895bc6f58e1f9120270df3e6da3711  adaptive_agent/requirements.py
cbaca3b8db02bfcd6cca2734500716de2d018ba6b5d0a6dedcd37ec68e534436  adaptive_agent/input_understanding.py
aacbd61fab9c1b72c411124291614c537bf8b67b7e329c0173f6e1c601c598b9  adaptive_agent/sufficiency.py
c3a557b94b1ffc35fd513abb2a11acd96a232442b9f216a69433c908b11d97eb  adaptive_agent/candidates.py
a86fe826cb5309e3c8ddd2152b75679dac1da3adaf105dd1cc5d63e4f14a3c34  adaptive_agent/policy.py
6abde508254e722e19f77715dd2d38b4f943e75f444ffa5b900b9341f4fa389e  adaptive_agent/tools.py
03167082b22151b79f37800997a7cd53a4da4844e249b6e3ba18780c6a5bfdff  adaptive_agent/answer_generation.py
420f116f2e149e4ed09ad40f23afc7628d15b81016871392fae8a27edd58e70d  adaptive_agent/runner.py
3c8df23e976769f6f2c647e1bd562c10bdc334a751940837551465f99481521f  adaptive_agent/state_update.py
07e2819af3ca6bfab511a7f5e5efa2634537ea5468cf92bbc253f94f543031ff  adaptive_agent/service.py
f61d5055114c7186373cb8a079b73ecdbe1d7e37217d12c97a4e6e56539bb40b  configs/requirements.yaml
ff62ab60a3af655a24471d55faaf69426583fe649e8c022668253a7e119fc6e2  evaluation/benchmark_v1_1.yaml
a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899  evaluation/benchmark_v1_1_scoring.md
d521a72c8263808d743cd904c8130ae8ce9a761c63dd12609215af970977b5f1  scripts/run_step5_5_capability_matched.py
```

## Measurement limitations carried forward

The current interfaces do not fully measure token use, exact LLM calls, LLM latency, retrieval latency or tool latency. Existing values are partial telemetry only:

- Fixed token metadata covers legacy direct response messages.
- Adaptive token metadata covers final answer-generation responses.
- Full internal LLM/RAG calls and component timing are `not_available`.

No future comparison may estimate these missing values and label the result as measured cost.
