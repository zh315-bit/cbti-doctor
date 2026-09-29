# Step 9.5 — Goal / Requirement Synchronization Design

## Scope and evidence

This is a design-only analysis of the Step 9.4 audit and current source. No
Agent, Policy, scoring specification, or Benchmark was changed or run. Model
configuration remains **NOT_VERIFIED** and is outside this design.

The concrete observed defect is not that `DependencyResolver` fails to resolve
an EVIDENCE dependency. It does resolve and satisfy it. The mismatch is that
`AdaptiveAgentLoop.run_turn()` resolves a `RequirementSet` from the initial
`state.task_type` once, then passes the same object to every later `_refresh()`.
Consequently, a task-type-derived personalized requirement can still populate
`decision_missing` and emit an optional ASK after goal-semantic EVIDENCE has
been satisfied.

## Current authority and dual sources of truth

```text
user input
  → InputUnderstander: goal + task_type + facts
  → runner: task_type → base RequirementSet → resolve_requirements(base, goal)
  → Sufficiency: required_missing / decision_relevant_missing / scope
  → DependencyResolver: goal semantics + current state + RequirementSet
  → Preconditions: dependency → mandatory candidate
  → Candidates: RequirementSet missing → optional ASK/RETRIEVE/READ_DIARY/ANSWER
  → Policy: select one candidate
```

There are two valid but currently unsynchronised interpretations:

| Source | Present authority | Correct role | Failure risk |
| --- | --- | --- | --- |
| User utterance / `goal` | Primary statement of requested outcome | Defines answer intent and semantic dependencies | May be lexical/ambiguous; must not by itself erase useful facts |
| `task_type` | Input-understanding classification signal | Chooses a conservative baseline requirement family | May be wrong or stale after a goal change |
| `RequirementSet` | Current source for missing fields/sufficiency | Describes potentially useful information and answer scope | Must not silently become a mandatory action source |
| `DependencyResolver` | Current source for hard preconditions | Defines conditions needed for a valid answer | Must not be used to delete all optional information |
| State / tool results | Source of observed facts/evidence/resource status | Determines knownness and dependency status | Must never be overridden by a label |

### Recommended authority hierarchy

There is no universal rule that goal semantics always wins. The proposed order
for each claim is:

1. **Observed State / validated tool truth** owns whether a fact, evidence, or
   resource is known, available, valid, or loaded.
2. **Goal semantics** owns goal-specific validity dependencies and the semantic
   applicability of a requirement family.
3. **Task type** selects `base_requirements` only when it is compatible with
   the current goal semantics; it is an auxiliary prior, not a direct action
   authority.
4. **Requirements** own optional information categories, bounded answer scope,
   and information-value input after synchronization.
5. **Dependency status** owns mandatory precondition status. A Policy cannot
   demote a REQUIRED dependency based on cost or an ordinary stop rule.

This preserves a useful task-type prior where goal wording is genuinely
underspecified while preventing it from continuing to impose an incompatible
decision-field set after semantic resolution.

## Requirement versus Dependency boundary

| State concept | Definition | May cause ASK alone? | Lifecycle |
| --- | --- | --- | --- |
| `required_missing` | All unknown fields in the effective critical and secondary requirement set | No | Recomputed on every refresh |
| `decision_relevant_missing` | Unknown fields potentially able to change the current decision or answer scope | No; must pass Information Value / cost / de-duplication | Recomputed on every refresh |
| `secondary_missing` | Unknown fields that only improve detail | No | Recomputed on every refresh |
| `Dependency` | Condition that must be satisfied before a valid answer for this goal | Not directly; it creates a precondition candidate | Re-resolved after each state-changing event |

`required_missing` remains an observability and completeness signal. It is not
a list of mandatory questions. Once an EVIDENCE dependency is `SATISFIED`, an
incompatible legacy personalized decision field has no authority to generate
an ASK. Compatible optional information remains visible and may improve the
answer if the user has already supplied it.

## Options considered

| Option | Semantic correctness | Regression risk | Complexity | Traceability | Decision |
| --- | --- | --- | --- | --- | --- |
| A. Goal semantics overrides all task-type requirements | Over-broad: could discard a valid baseline when wording is vague | High | Low | Medium | Reject |
| B. Dependency filters Requirements | Can suppress stale fields, but lacks an explicit source of resulting requirements | Medium | Medium | Low | Do not use alone |
| C. Re-derive Requirements after Dependency Resolution | Correct refresh timing, but needs a stable representation of base vs semantic inputs | Medium | Medium | High | Include in lifecycle |
| D. Introduce `effective_requirements` | Explicit, compatible with existing `RequirementSet`, preserves optional fields | Lowest bounded change | Medium | High | **Recommend** |

## Recommended minimal synchronization mechanism

Introduce a pure `RequirementSynchronizer` (or equivalently a pure function in
the requirements domain) that produces an immutable `EffectiveRequirements`
record. It does not select actions and does not call tools.

```text
base_requirements (from task_type)
  + goal semantic assessment
  + resolved dependencies
  + validated State facts/resources
  → effective_requirements
  → Sufficiency / optional candidate generation
```

Suggested fields:

```text
base_requirement_source: task type and configuration version
semantic_adjustments: [{rule_id, disposition, reason}]
active_critical / active_secondary / active_decision_fields
suppressed_fields: [{field, reason, source_requirement}]
answer_scope
dependency_ids_considered
```

The synchronization rule is a compatibility filter, not a blanket deletion:

* A mandatory dependency is represented by the dependency/precondition layer,
  never duplicated as a mandatory optional requirement.
* A task-type decision field incompatible with goal semantics is suppressed
  from `active_decision_fields`; it remains only as historical base provenance.
* A compatible optional field remains in `active_secondary` or
  `active_decision_fields`, but can only result in ASK through normal
  Information Value, acquisition cost, diminishing return, and de-duplication.
* Facts already supplied by the user are never discarded because a field is
  suppressed. The answer generator may use them when relevant and within
  answer scope.

For the Step 9.4 knowledge-goal situation, semantic classification establishes
EVIDENCE. After retrieval, effective decision fields for an incompatible
PERSONALIZED_DECISION base set are empty/suppressed rather than producing a
follow-up sleep-schedule ASK. This is a general semantic compatibility rule,
not a KQ-specific branch.

## Recommended lifecycle

The current order calculates sufficiency before dependency resolution. The
recommended dependency-aware refresh uses a bounded two-phase calculation:

```text
Input Understanding / new-goal detection
→ resolve base requirements from task type
→ derive goal semantics with provenance
→ preliminary State missing calculation
→ resolve dependencies
→ synchronize effective requirements
→ recompute missing + sufficiency from effective requirements
→ re-resolve dependencies against the synchronized State view
→ preconditions → candidates → Information Value/Cost/Stop → Policy
```

The second dependency resolution is not a loop: it validates the dependency
statuses after synchronized fields have been calculated. It must be run again
after every state-changing boundary:

| Event | Required refresh behavior |
| --- | --- |
| New goal | Replace base/effective requirement provenance; do not inherit incompatible prior-goal fields |
| Follow-up fact merge | Recompute knownness, effective missing and dependencies |
| RETRIEVE | Update evidence; dependency becomes SATISFIED and effective requirements are recomputed |
| READ_DIARY | Validate/project resource result, then recompute resource status, facts and dependencies |
| ASK response merge | Same as follow-up fact merge |
| Dependency re-resolution | Replace, never append to, current dependency/effective-requirement snapshots |

This makes stale requirements observable and prevents them from surviving a
goal change or tool action.

## Explicit non-goals and regression protection

The synchronizer must not change `information_value.py`, the policy ranking,
acquisition cost, diminishing return, bounded answer logic, diary tool
contract, or answer grounding. It must retain:

* `Missing Information ≠ Must Ask`;
* VALIDITY_CRITICAL_STATE only where the current goal cannot be validly
  answered without that state;
* resource alternatives before an ASK where a valid authorised resource exists;
* one-action-per-turn and existing ASK de-duplication;
* new-goal reset and follow-up fact merge behavior.

## Recommended Step 9.6 implementation boundary

Modify only the requirement-resolution / refresh boundary and serializable
trace schema:

1. `adaptive_agent/requirements.py`: add pure effective-requirement data and
   synchronization function.
2. `adaptive_agent/runner.py`: re-create effective requirements at every
   refresh, including tool re-evaluation and new goal boundary.
3. `adaptive_agent/sufficiency.py` and `adaptive_agent/candidates.py`: consume
   the effective object rather than independently re-resolving base
   requirements.
4. `adaptive_agent/dependency_resolver.py` and `preconditions.py`: accept and
   emit lineage/provenance data, without changing dependency semantics.
5. `adaptive_agent/state.py`, recorder/snapshots and focused synthetic tests:
   persist the effective requirements and lineage.

Do **not** modify Input Understanding, the Heuristic Decision Policy,
Information Value/Cost/Return, Answer Generation, Diary Contract V2, Benchmark
V2/V3, or scoring. No implementation is performed by this Step 9.5 document.
