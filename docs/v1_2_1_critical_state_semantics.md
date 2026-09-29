# V1.2.1 Critical State Semantics

## Purpose

V1.2.1 distinguishes whether missing state merely improves an answer from
whether it prevents a valid answer to the **current goal**.  This is a
goal-and-context classification, never a direct conversion of a requirement's
`critical` label.

| Missing category | Meaning | Decision route |
| --- | --- | --- |
| `secondary_missing` | Can improve detail only. | Usually bounded answer; it may be considered by Information Value. |
| `decision_relevant_missing` | Plausible values may change direction or answer scope, but a bounded answer can still be valid. | Information Value → Acquisition Cost → Diminishing Return → ASK/resource/ANSWER. |
| `validity_critical_missing` | Without the fact, the requested answer cannot validly determine its requested direction; no already-satisfied state source exists. | `VALIDITY_CRITICAL_STATE` hard precondition. |

## Validity-Critical State

A state dependency is validity-critical only when the counterfactual question is
answered **no**:

> If this fact remains unknown, can the agent still give a valid bounded answer
> for this goal?

The current supported instance is a personalized, directional timing decision
(for example, whether to move bedtime earlier or later).  The agent requires
the relevant sleep-onset/sleep-time context and wake-time boundary before it
can determine that direction.  In contrast, `wake_time` is not a hard
precondition for “why is a regular wake time important?”; that educational goal
can be answered with grounded evidence without a personal wake time.

This is deliberately narrower than `RequirementSet.critical`.  Caffeine,
nighttime awakenings, recent pattern, and other critical-ranked fields remain
optional or decision-relevant unless the current answer is invalid without
them.  They therefore stay in the V1.2 Information Value mechanism rather than
being collected automatically.

## Hard-Precondition Boundary

The ordered decision boundary is:

```text
EVIDENCE / RESOURCE / VALIDITY_CRITICAL_STATE
    → Information Value
    → Acquisition Cost
    → Diminishing Return
    → Bounded Answer
```

For `VALIDITY_CRITICAL_STATE`, the agent first checks an authorized, available,
unread diary that can supply the needed information.  It selects `READ_DIARY`
when that lower-burden source exists; otherwise it selects one `ASK`.  This is
resource substitution, not a blanket preference for diaries.

An unavailable or unauthorized required diary is never treated as satisfied.
The agent returns a limited/unavailable path rather than inventing diary facts.
Diary Tool → State projection separately validates cardinality, dates, and
provenance; an invalid projection writes no diary-derived facts.

## Repeated Questions and Bounded Answers

Hard preconditions are not permission to ask the same semantic question again
without new information.  If the equivalent question has already been issued
and no resource alternative exists, the trace records:

```text
status: deferred
satisfaction_source: previous_unanswered_ask
```

The dependency remains visible, but no repeat ASK candidate is emitted.  The
ordinary bounded-answer path can state the limitation.  This preserves the
V1.1 rule `Missing Information ≠ Must Ask` and prevents an internal repeated-
ASK loop.

## Trace Contract

Every state precondition records `type`, `target`, `required_for`, `status`,
`satisfaction_source`, `required_action`, and `reason`.  A validity-critical
entry additionally records `validity_reason` and `resource_alternative`.
Snapshots and evaluation records also retain `validity_critical_missing`, so a
reviewer can distinguish “required for validity” from “optional but valuable.”
