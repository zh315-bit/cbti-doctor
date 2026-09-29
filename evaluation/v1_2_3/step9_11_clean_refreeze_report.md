# Step 9.11 — Clean Evaluation Re-Freeze

## New identity and historical boundary

`clean-evaluation-v1_2_3-20260922-01` is a new evaluation identity created from
the current Agent. It is not a Step 9.8 rerun or recovery. Its historical parent
is `STEP9_8_FAILED_EVALUATION`; that historical result remains closed as an
evaluation-harness failure with zero completed cases.

The new identity is frozen but not authorized to execute:

```text
evaluation_state = FROZEN
execution_state  = NOT_AUTHORIZED
```

## Complete dependency closure

The closure begins at production `/api/chat` and includes the Flask factory,
service/session layer, loop, input understanding, fact derivation, requirements
and YAML, DependencyResolver, sufficiency, preconditions, candidates, policy,
information-value layer, state and State Update, tool interfaces, answer
generation, recorder, model configuration, lazy RAG code, local embeddings,
RAG index and PDF corpus. It also includes a redacted non-secret runtime model
configuration fingerprint. Credential material itself is not stored.

The closure contains 25 Agent-behavior entries and 3 evaluation-harness entries.
The exact file-level inventory is in `step9_11_dependency_inventory.json`.

## Frozen inputs and reproducibility

| Item | Result |
| --- | --- |
| Benchmark V2 cases | 40 |
| Benchmark V2 SHA-256 | MATCH (`dfa9…afd2`) |
| Scoring rubric SHA-256 | MATCH (`a7f…899`) |
| Agent aggregate reproducible | YES |
| Harness aggregate reproducible | YES |
| Benchmark aggregate reproducible | YES |
| Scoring aggregate reproducible | YES |

Domain aggregates are calculated from sorted `path<TAB>sha256` lines; the final
evaluation aggregate is calculated from the four named domain aggregates. This
rules out the incomplete hand-picked source list that blocked strict Step 9.8
recovery provenance.

## Leakage audit

Benchmark V2 is **not held out**: it remains a development/regression set.
The production Agent/configuration closure contains no V2 case-ID rule,
expected-action lookup, benchmark-specific prompt, requirement, or answer rule.
Historical case-level reviewer mappings in the scoring implementation remain
separate, frozen scoring behavior and are not imported by the Agent.

## Deterministic validation

Focused deterministic modules: **59 passed, 0 failed**. Full non-external-model
unittest discovery: **152 passed, 0 failed**. `tests.test_model_configuration`
was deliberately not run because it is model/environment dependent; it is not
counted as a pass.

No Benchmark case, Flask/model request, or external model was run. The Agent,
Benchmark V2 and scoring rubric were not modified.

```text
READY_FOR_STEP9_12 = YES
```
