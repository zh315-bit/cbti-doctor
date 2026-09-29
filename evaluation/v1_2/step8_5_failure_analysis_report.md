# Step 8.5 — Failure Decomposition & Safety Boundary Analysis

## Reconciliation

There are **4 Critical Failures**, exactly DA-03, DA-04, DA-05 and DA-08. They
are `answer_contradicts_diary_fixture`. KQ-02, KQ-05 and DA-07 are serious,
harmful observed failures, but are not automatically Critical Failures under the
frozen rubric.

## Pipeline findings

KQ-02/KQ-05 first fail at Input Understanding/State: their traces hold broad
personalized-decision missing fields rather than a knowledge-evidence state.
Evidence remains LOW, RETRIEVE is never generated, and bounded stopping is a
downstream premature-stop/evidence-dependency failure—not a demonstrated
Information Value false negative. DA-07 first fails similarly: despite the
authorized fixture, State never represents the diary resource, so no READ_DIARY
candidate exists. Its later stop is downstream.

DA-03/04/05/08 correctly select and load `READ_DIARY`; their first error is
Tool → State projection. Grouped/summary fixture strings are counted as list
items and reach answer generation as false diary cardinality. They are not
Decision Policy failures.

## Information Value false negatives

Strict trace-visible false negatives: **0**. The necessary RETRIEVE/READ_DIARY
actions in the three harmful cases were absent, not rejected by an observed
value/cost comparison. This is important: fixing an IV threshold would not cure
the upstream dependency omission. Correct low-value-rejection rate is
not_measurable with the frozen trace denominator.

## Trade-off interpretation

**Observed:** on this V2 development set, ASK/case fell from 2.800 to 1.775
(36.6%), PD ASK/case from 5.333 to 3.000, and six-ASK cases from 11 to 0, while
four critical diary failures appeared.

**Supported:** the V1.2 stop mechanism changes acquisition burden, but hard
evidence/resource dependencies need a distinct boundary before optional
cost-aware selection.

**Not yet supported:** generalization, real-user benefit, clinical safety,
calibrated value estimates, or superiority. V2 is a single stochastic
development/regression run.

## V1.2.1 minimal plan (not implemented)

1. Add a hard-precondition gate for correctly classified evidence-required and
resource-required goals; only optional fields enter IV/cost/diminishing return.
2. Repair diary Tool → State projection with entry cardinality and provenance.
3. Add regression cases for KQ evidence dependency, DA authorized-resource
dependency and compressed diary cardinality, then rerun only under separately
authorized protocol.
