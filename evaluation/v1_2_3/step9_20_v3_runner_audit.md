# Step 9.20 — V3 Authorization and Runner Audit

## Scope and outcome

This is authorization preparation only. No Benchmark V3 path was opened, listed, hashed, counted, or read. No V3 case was called. No model call or benchmark execution occurred.

The Step 9.19 candidate manifest and locked artifacts were re-hashed in the current workspace. Agent, accepted harness, scoring aggregate, metric registry, one-shot rules, protocol, and final candidate manifest all match their Step 9.19 values. The production-source leakage scan was restricted to `adaptive_agent/` and `configs/requirements.yaml`; the recorded candidate audit remains `case_specific_logic_present=false`.

## Current preflight evidence

The only readable `LOCAL_REAL_PREFLIGHT` is from 2026-09-22 and binds `clean-evaluation-v1_2_3-20260922-01`, the Step 9.11 Agent aggregate, and the prior V2 authorization infrastructure. It does not bind this new V3 evaluation or the Step 9.19 Agent aggregate, so it cannot satisfy the current authorization gate.

In this execution environment, `DEEPSEEK_API_KEY` is absent. Therefore the credential gate fails, and a current real-model probe and production smoke were not run. `MODEL_ENDPOINT_READY` is consequently `NO / NOT VERIFIED`, not a claim that the provider endpoint itself is down.

## Existing runner audit

`scripts/run_step9_12_frozen_evaluation.py` is not a V3 runner. It hard-binds the Step 9.12 Evaluation ID, Step 9.11 manifest, V2 benchmark path, V2 case-count check, and V2 execution ledger. Reusing or retargeting it would violate both its one-shot semantics and the Step 9.19 locked harness identity.

No V3-specific runner was added. A new runner is a material part of the execution harness; adding it without a separately reviewed/frozen runner identity would make the actual execution harness differ from the frozen identity that this step is required to match. This audit therefore fails closed rather than silently expanding the harness freeze. The runner also cannot be certified for the frozen scoring workflow while the current environment lacks the required production preflight.

## Authorization decision

`authorization_id` and `attempt_id` remain null and no formal authorization was issued. The evaluation identity is reserved as `heldout-v3-step9_20-20260923-01`; it is not authorization to execute. The command artifact says `NOT ISSUED` and contains no executable benchmark command.

The blockers are:

1. Current environment has no DeepSeek credential. The historical local preflight artifact is stale for both evaluation ID and Agent identity.
2. No Step 9.20 V3 runner identity has been separately audited and frozen; the existing one-shot runner is V2-only.

No Agent, Benchmark, scoring, metrics, or frozen protocol was modified. No Benchmark V2 rerun or Benchmark V3 access occurred.
