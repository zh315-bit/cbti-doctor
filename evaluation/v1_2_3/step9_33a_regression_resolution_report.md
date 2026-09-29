# Step 9.33a — Regression Resolution Report

## Effective changes

1. **Necessary acquisition order:** after the acquisition gate, a relevant available diary that explicitly satisfies a validity dependency precedes personal ASK; otherwise an accepted ASK whose plausible outcomes change direction/scope precedes independent retrieval. Nonaccepted/low-value ASK candidates cannot delay required evidence. Required evidence remains available after relevant fact acquisition.
2. **Diary satisfier lineage:** `READ_DIARY` can be accepted from a `VALIDITY_STATE` dependency only when its `satisfiable_by` explicitly includes `READ_DIARY`. It is not generalized to unrelated diary access.
3. **Test-contract reconciliation:** changed expectations are limited to R1-required retrieval after an unanswered/duplicate ASK, soft validity trace/action origin, and old freeze mismatch. Original and replacement semantics are documented in the failure matrix. Historical artifacts are not rewritten.
4. **Freeze-bound historical sidecar checks:** retained assertions against the persisted Step 9.30a.2 sidecar, manifest and audit. They are no longer rebuilt under a different treatment identity.

## Regression outcome

The Step 9.32 baseline passed all 28 exact targeted checks. After triage, focused regression passed and the effective complete suite passed: **296 run, 0 failures, 0 errors**. No unresolved `INDETERMINATE` failure remains. The individual 22 failure/error items are classified and resolved in `step9_33a_regression_failure_matrix.jsonl`.

## Preserved invariants

- Safety- and execution-critical preconditions remain hard and fail closed.
- ASK requires unknown, decision-relevant information with material counterfactual impact and complete lineage; already-known/unavailable/asked targets remain suppressed.
- Independent evidence and diary dependencies are not satisfied by personal facts or one another; unavailable resources are not fabricated or automatically retried.
- Agent has no case-specific or expected-action branch.
- Step 9.32 frozen design, paired preregistration, synthetic plan and baseline freeze remain unchanged.
- No V4 case, paired evaluation, evaluation model/Agent/RAG path, score, or V5 was executed/created/accessed.

## Next-step gate

The Step 9.33a treatment identity is frozen solely because complete regression passed. Step 9.34 remains a separate, preregistered paired-evaluation precheck and must revalidate environment and identities; this report does not start or authorize it.
