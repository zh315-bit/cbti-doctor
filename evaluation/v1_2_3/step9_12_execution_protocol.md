# Step 9.12 — Local Execution Protocol

## Preconditions

The new evaluation identity is `clean-evaluation-v1_2_3-20260922-01`, with historical parent `STEP9_8_FAILED_EVALUATION`. It is independent of Step 9.8: no Step 9.8 authorization, attempt ID, ledger or manifest may be reused.

Before a formal run, execute the read-only preflight:

```bash
.venv/bin/python -m scripts.preflight_step9_12_local
```

It must report a matching frozen identity, credential present, DNS/HTTPS ready, a successful real model probe, synthetic production smoke `PASS`, and trace lineage ready. It never creates a formal attempt or runs Benchmark V2.

## Authorization format

Use a new, non-secret ID beginning with `clean-evaluation-v1_2_3-20260922-01-`. The authorization metadata must match `step9_12_authorization_template.json`. It is not valid to reuse any Step 9.8 identifier.

## One-shot rule

The runner checks the frozen Agent/harness/Benchmark/scoring closure before any case and again immediately before case 1. On a real run it appends `PREPARED` before work and `STARTED` before the first case. A partial failure or completion blocks automatic reruns; no code changes or result selection are permitted.

## Formal command

No formal command is issued in this preflight because `credential_present=false` and the model probe/smoke were consequently not run. Once all preconditions are independently rechecked as PASS and a human supplies a new authorization ID, the only permitted command form is:

```bash
.venv/bin/python -m scripts.run_step9_12_frozen_evaluation --authorization-id <NEW_CLEAN_EVALUATION_AUTHORIZATION_ID>
```

Do not execute it until explicit authorization is recorded.
