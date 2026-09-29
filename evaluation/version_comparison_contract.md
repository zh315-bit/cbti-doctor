# Adaptive Version Comparison Contract

## Purpose

This contract governs every Adaptive V1.x/V2 comparison against `adaptive-agent-v1-baseline`. It prevents improvements from overwriting the baseline, changing the task while scoring it, or converting capability differences into Policy claims.

## Required constants

Unless explicitly listed as an experimental confound, a comparison must retain:

1. Frozen `evaluation/benchmark_v1_1.yaml` and `evaluation/benchmark_v1_1_scoring.md`.
2. The same ten synthetic cases, literal user inputs, fixture visibility and follow-up release protocol.
3. The same RAG corpus/index, retrieval interface and diary fixtures.
4. The same model identifier, parameters and prompt-level safety boundary when feasible.
5. The same experiment adapter interface and output schema from `scripts/run_step5_5_capability_matched.py`.
6. The same manual score dimensions, critical-failure contract and primary/downstream attribution rules.
7. Isolated session per case, a unique run tag, and append-only raw traces.

## Required two-layer reporting

Every report must produce both:

- **Capability-Matched Comparison:** exclude cases for which one system lacks a required capability. For the V1 baseline, this is the eight non-DA cases.
- **Full-System Comparison:** retain all ten cases, including DA-01/DA-02, and label diary outcomes as resource-capability effects rather than Policy-only effects.

## Artifact requirements

At minimum, save:

```text
<system>-matched-traces.jsonl
matched-paired-results.jsonl
cost_metrics.json
experimental_confounds.json
comparison report
```

Each trace must record raw input, assistant response, action path, ASK targets, tool calls, state snapshot or `not_available`, evidence used or `not_available`, turns, steps, token usage scope, latency and final status.

## Measurement rules

- Record `not_available` for exact LLM calls, token totals or component latency when they cannot be directly observed.
- Never infer internal calls from turns, or estimate a missing component latency.
- Retain telemetry scope alongside every token number.
- Report repeated-run variability when a model is stochastic; do not treat one non-reproduction as a failure repair.

## Confound disclosure

If any of the following changes, the report must list it as an `experimental_confounds` entry and explain expected direction of impact where known:

- model/provider/parameters;
- prompt or medical safety constraints;
- RAG corpus/index/retriever;
- tool capability/interface;
- benchmark, fixtures, follow-up protocol or scoring;
- adapter/endpoints or telemetry scope;
- source hashes when no Git commit is available.

## Baseline protection

- Do not overwrite Step 5.1–5.5 artifacts, historical scores or known failure records.
- Keep deterministic and stochastic failures in `adaptive_v1_failure_set.yaml` even after a later run does not reproduce them.
- A proposed Agent change requires a new version identifier, new run directory and paired comparison to this baseline. It may not be presented as an improvement solely because one benchmark case passes.
