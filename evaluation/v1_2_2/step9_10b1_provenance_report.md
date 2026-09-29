# Step 9.10b.1 — Frozen Agent Provenance Reconstruction

## Method and boundary

This was a read-only forensic reconstruction. The original Step 9.8 manifest remains unchanged. Current hashes are present-day observations only; they were not used to backfill a historical manifest. Passing tests were not treated as proof of historical equivalence.

The actual recovery execution path was traced from `/api/chat` through `adaptive_agent.flask_app`, `service`, `runner`, the state/requirements/dependency/precondition/candidate/policy chain, tools and State Update, answer generation, lazy RAG, and the recorder. The file-level result is in `step9_10b1_production_dependency_inventory.json`.

## Evidence reconstruction

The Step 9.8 manifest gives strong, exact SHA-256 evidence for 13 active Agent/model files; all 13 current files match. This is meaningful but limited: it omits the Flask/service boundary, DependencyResolver, facts utility, recorder, requirements configuration, and RAG implementation/artifacts.

The Step 5.6 source manifest gives matching earlier hashes for `service.py` and `configs/requirements.yaml`; an immutable Git tree dated 2026-09-16 gives matching earlier content for `rag_client.py` and `local_embeddings.py`. Neither provides a freeze-time identity for 2026-09-21. A Git tree dated 2026-09-22 is post-event and therefore unusable for reconstructing the frozen state. Reports and `record.md` explain intended changes but are prose, so they remain weak evidence.

## Result

| Evidence class | Files |
| --- | ---: |
| Strong — Step 9.8 exact hash | 13 |
| Medium — earlier immutable/prior manifest with time gap | 4 |
| Weak — prose/existence only | 6 |
| Behavior-affecting files with `UNKNOWN` equivalence | 10 |

The ten unresolved dependencies are `flask_app.py`, `service.py`, `dependency_resolver.py`, `facts.py`, `evaluation/recorder.py`, `configs/requirements.yaml`, `rag_client.py`, `local_embeddings.py`, the RAG index, and the RAG source corpus. This is not evidence that any changed; it is evidence that their Step 9.8 contents cannot be proven from the available artifacts.

`flask_app.py` requires particular care. Step 9.8a documentation says the import-light factory was extracted as infrastructure after the original initialization failure, but that statement has no contemporaneous immutable file identity. It cannot be upgraded to a frozen-state match.

## Determination

```text
AGENT_EQUIVALENCE_STATUS = INSUFFICIENT_PROVENANCE
RECOVERY_EXPERIMENT_STATUS = NOT_STRICTLY_RECOVERABLE
MISSING_BEHAVIOR_AFFECTING_FILES = 10
STRONG_EVIDENCE_FILES = 13
MEDIUM_EVIDENCE_FILES = 4
WEAK_EVIDENCE_FILES = 6
UNKNOWN_FILES = 10
READY_TO_REASSESS_STEP9_10B = NO
```

The outcome is deliberately not `PROVEN_DIFFERENT`: no actual behavior-code change was established. It is also not recoverable with merely a documented non-behavioral limitation, because the unresolved dependencies can affect model construction, dependency formation, tool/state handling, RAG evidence, or API request completion.

No Benchmark V2 case was executed, no real model was called, and Benchmark V3 was not accessed. The Agent, Benchmark, scoring rubric, and original Step 9.8 manifest were not modified.
