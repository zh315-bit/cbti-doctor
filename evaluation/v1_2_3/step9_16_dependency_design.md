# Step 9.16 Dependency Formation Design

## Scope

Step 9.16 repairs the architecture-level dependency formation boundary only. The implementation does not inspect benchmark case IDs, does not map task type directly to an action, and does not change ranking, Decision Policy, diary projection, RAG implementation, scoring, Benchmark V2, or Benchmark V3.

The enforced order is:

`User Input -> Goal Semantics -> Dependency Formation -> Effective Requirements -> Missing Information -> Candidate Actions -> Information Value -> Decision Policy`

## Canonical dependency classes

The resolver now records a canonical `dependency_class` while retaining legacy wire values for compatibility:

| Canonical class | Legacy type | Meaning | Typical satisfiers |
|---|---|---|---|
| `USER_FACTS` | `USER_FACTS` | Personal facts required or useful for the bounded decision | `ASK`, `READ_DIARY` |
| `EXTERNAL_EVIDENCE` | `EVIDENCE` | CBT-I knowledge, rules, guidelines, or RAG evidence | `RETRIEVE` |
| `DIARY_DATA` | `RESOURCE` | Historical sleep-diary data requested by the goal | `READ_DIARY` |
| `VALIDITY_STATE` | `VALIDITY_STATE` | A goal-specific state needed to determine direction safely | `ASK`, `READ_DIARY` |

`USER_FACTS` is intentionally candidate-level and optional by default. It supplies provenance for user-fact ASK candidates without becoming an unconditional hard precondition. `EXTERNAL_EVIDENCE`, `DIARY_DATA`, and `VALIDITY_STATE` retain their existing hard-precondition behavior when the goal semantics require them.

## Goal semantics

Goal semantics combine explicit goal signals with task type as a prior. Task type never directly selects an action. Generic advice and education shapes can form an evidence dependency even when an upstream classifier supplied a personalized task signal. Diary language and historical-analysis intent form the diary dependency. Mixed goals can form multiple dependencies, such as `USER_FACTS + EXTERNAL_EVIDENCE` or `DIARY_DATA + EXTERNAL_EVIDENCE`.

Optional user facts do not block evidence retrieval. Available diary data is represented as a diary dependency and is consumed through `READ_DIARY`, rather than being converted into equivalent ASK candidates.

## Lineage contract

Each dependency now exposes:

- `dependency_id`
- `dependency_type` (legacy-compatible)
- `dependency_class` (canonical source class)
- `dependency_source` / `source`
- `dependency_reason` / `reason`
- `requiredness`
- `status`
- `satisfied_by` / `satisfiable_by`
- `semantic_ids`

Candidates link through `source_dependency_id`; existing hard-precondition candidates additionally carry `source_precondition_id`. Selected actions retain `selected_candidate_id`, yielding:

`Goal -> Dependency -> Candidate -> Selected Action`

No synthetic lineage IDs are created outside the resolver's goal/revision namespace.

## Safe fallback

An unknown or unsupported goal produces no forced dependency and falls back to the existing bounded ANSWER path. It does not fabricate evidence, diary data, or personal facts. Hard validity dependencies remain protected from optional acquisition heuristics.

