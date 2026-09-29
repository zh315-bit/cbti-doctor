# V1.2.2 Dependency Resolver — Architecture Design

## Purpose and boundary

`Requirement` expresses information that may improve, refine, or constrain an
answer. `Dependency` expresses a condition that must be satisfied before the
current goal can be validly answered. They are deliberately different:

```text
missing Requirement  ≠ mandatory ASK
missing Dependency   ≠ optional acquisition
```

Information Value applies only after mandatory dependencies have been resolved
or a valid bounded fallback has been selected. It must not reject a mandatory
RETRIEVE/READ_DIARY merely because its acquisition cost is high.

## Proposed resolver interface

```python
class DependencyResolver:
    def resolve(
        self,
        *,
        goal: str,
        task_type: TaskType | None,
        facts: Mapping[str, object],
        evidence: Sequence[Evidence],
        resources: ResourceState,
        answer_scope: str,
        requirements: RequirementSet,
        conversation_context: ConversationContext,
    ) -> list[Dependency]: ...
```

`task_type` is a signal, not a dependency rule. Goal semantics, explicit user
language, answer scope, State and resource provenance have priority. For
example, a goal that asks to define or explain a CBT-I principle yields an
evidence dependency even if upstream task classification says
`PERSONALIZED_DECISION`; a goal requesting analysis of historical diary patterns
yields a diary resource dependency even if classification is wrong.

```python
@dataclass(frozen=True)
class Dependency:
    dependency_id: str
    dependency_type: Literal['EVIDENCE', 'RESOURCE', 'VALIDITY_STATE']
    target: str                         # e.g. external_cbt_i_evidence, sleep_diary, wake_time
    status: DependencyStatus
    required_for_goal: str
    reason: str
    source: list[DependencySource]      # goal_semantics, answer_scope, requirement, context
    satisfiable_by: list[Satisfier]     # actions/sources, not a selected action
    fallback: Fallback | None           # bounded limitation or unavailable explanation
    provenance: dict[str, object]

class DependencyStatus(str, Enum):
    REQUIRED = 'REQUIRED'
    AVAILABLE = 'AVAILABLE'
    SATISFIED = 'SATISFIED'
    UNAVAILABLE = 'UNAVAILABLE'
    INVALID = 'INVALID'
    DEFERRED = 'DEFERRED'
```

`AVAILABLE` means at least one satisfier is authorized and usable, not that the
dependency is satisfied. `DEFERRED` means the dependency remains visible but no
new identical user acquisition is justified (for example, an unanswered
equivalent ASK); it must retain its limitation provenance. The existing six
states are sufficient for V1.2.2; no additional status is proposed.

## Resolution semantics

| Dependency | Goal-semantic trigger | Satisfied by | Unavailable/invalid fallback |
| --- | --- | --- | --- |
| `EVIDENCE` | General CBT-I definition, explanation, comparison, rule, or external clinical claim in answer scope | relevant retrieved evidence | explain evidence limitation; do not invent a knowledge claim |
| `RESOURCE(sleep_diary)` | Goal explicitly asks to analyse, compare, summarize, or trend historical diary data | valid, authorized, loaded diary payload | explain diary unavailable/invalid; do not fabricate analysis |
| `VALIDITY_STATE` | Current personalized goal cannot support even a bounded directional answer without the state fact | known fact, or authorized resource alternative, or ASK | limited non-directional response only when no new satisfier exists |

No new dependency type is supported by Step 9.1 traces. `PROVENANCE` is a
cross-cutting validity property of RESOURCE/EVIDENCE satisfiers, not a fourth
goal dependency type.

## Lifecycle → hard preconditions

```text
REQUIRED + satisfiable source  → select a mandatory satisfier
REQUIRED + no usable source    → bounded unavailable fallback
AVAILABLE                      → select one satisfier; dependency remains unresolved
SATISFIED                      → pass to optional candidates
INVALID                        → fail closed; bounded invalid-data fallback
DEFERRED                       → do not repeat the equivalent acquisition; preserve limitation
```

The resolver produces a dependency, not an action. The hard-precondition layer
selects a satisfier:

```text
EVIDENCE                 → RETRIEVE(query)
RESOURCE(sleep_diary)    → READ_DIARY
VALIDITY_STATE           → preferred valid resource satisfier, otherwise ASK
```

This permits a future dependency to have multiple satisfiers without encoding
`dependency_type == action`. A resource alternative for `recent_sleep_pattern`,
for instance, should appear on the dependency as an authorized diary satisfier;
the action layer selects it before direct user ASK.

## Full decision boundary

```text
Goal + validated State + answer scope
  → Dependency Resolver
  → mandatory Hard Preconditions / satisfier selection
  → optional Candidate Generation
  → Information Value
  → Acquisition Cost
  → Diminishing Return
  → Bounded Answer
  → Decision Policy
```

Mandatory actions bypass Information Value, Cost, Diminishing Return and the
ordinary bounded-answer stop. Optional fields use all four. A bounded fallback
is legal only for a dependency with `UNAVAILABLE`, `INVALID`, or `DEFERRED`
status and must name the resulting answer limit.

## ASK pipeline

```text
Goal semantics
→ dependencies and satisfiers
→ validated State facts/provenance
→ resource alternatives
→ decision-relevant optional missing fields
→ Information Value
→ ASK
```

This explicitly excludes the invalid shortcut `requirements → missing → ASK`.
It addresses the Step 9.1 clusters: dependency misformation (11 irrelevant
ASK), stale/omitted query facts (21 redundant ASK), and a remaining 12
unresolved irrelevant ASK that require future candidate-level counterfactual
observability before attribution.

## Required observability

Each trace must retain:

```text
dependencies_considered
dependencies_required
dependencies_satisfied
dependencies_unavailable
dependency_source
dependency_reason
dependency_satisfiers
selected_satisfier
rejected_satisfiers
```

For every selected satisfier, record why RETRIEVE was mandatory, why the diary
was required, why ASK was preferred to a resource, or why a dependency was
treated as satisfied. This is an observability contract, not telemetry that may
change Policy.
