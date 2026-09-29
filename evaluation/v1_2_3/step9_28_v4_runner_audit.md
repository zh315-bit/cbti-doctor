# Step 9.28 — V4 runner audit

## Bound identities

- Final Agent freeze, harness, scoring, metric registry, one-shot rules, V4 manifest, V4 dataset SHA-256, and runner freeze all match.
- V4 dataset status remains `SEALED_NOT_EVALUATED`; generic schema compatibility passed.
- Static seal audit reports no case-specific Agent logic and no expected-action lookup.

## Runner boundary

`scripts/run_step9_28_v4_heldout.py` uses the production `AdaptiveChatService` and `/api/chat` only in its formal run path. Its preflight is separate, case-inert with respect to Agent execution, and does not issue authorization. The formal path records and fsyncs immutable lifecycle events, raw traces, and unscored results; it refuses a prior ledger.

## Local preflight result

Credential and imports were present. DNS resolution for the configured model host failed, so HTTPS, model endpoint probe, and synthetic production smoke were not run. This is fail-closed: `READY_FOR_V4_FINAL_AUTHORIZATION = NO`. No V4 case was executed, scored, or sent to the Agent.
