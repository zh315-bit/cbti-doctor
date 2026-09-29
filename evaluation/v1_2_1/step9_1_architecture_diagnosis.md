# Step 9.1 — Dependency Formation & Projection Failure Localization

## Result

This is read-only analysis of the frozen Step 8.9 traces. No Agent, Benchmark
V2, scoring rule, or Benchmark V3 was changed or run.

| Mechanism-level first divergence | Cases | Count |
| --- | --- | ---: |
| Evidence dependency fails to form after KQ task misrepresentation | KQ-02, KQ-05 | 2 |
| Resource dependency fails to form after DA task/state misrepresentation | DA-07 | 1 |
| Summary-shaped diary contract lacks source truth before projection | DA-03/04/05/08 | 4 |

Thus **3/7** harmful failures are Dependency Formation failures and **4/7** are
Tool → State Projection failures. None first diverges in the Decision Policy.

## Failure chains

- **KQ-02 / KQ-05:** input is a general knowledge question → Input
  Understanding emits a personal decision goal/task → personalized Requirements
  populate decision missing fields → `evidence_required` never becomes the
  knowledge dependency → no EVIDENCE precondition or RETRIEVE candidate → ASK
  loop and bounded answer.
- **DA-07:** input says the diary is in the account and requests data comparison
  → Input Understanding emits PERSONALIZED_DECISION and no diary state → DATA
  ANALYSIS resource requirement is unavailable → no RESOURCE precondition or
  READ_DIARY candidate → irrelevant ASK loop and bounded answer.
- **DA-03/04/05/08:** DATA_ANALYSIS correctly forms RESOURCE → READ_DIARY runs
  → output is a summary string/list without source entry count or dates →
  projection accepts `valid` because its entry invariants have no source truth
  to check → a summary item is described as one/two days in the answer.

## Requirements versus Dependencies

They are partially conflated. Requirements correctly express fields that may
matter after a task is represented, but they cannot establish the evidence or
diary dependency when that representation is wrong. The candidate future
boundary is therefore:

```text
Goal
→ Dependency Resolver
→ Evidence / Resource / Validity-State dependencies
→ Hard Preconditions
→ Information Value and optional acquisition
```

This is a design diagnosis only. It does not implement a resolver.

## ASK connection

Of 66 ASK, 44 were redundant or irrelevant. Eleven irrelevant ASK are directly
caused by the three harmful task/dependency failures. Twenty-one redundant ASK
are trace-linked to known query facts failing to survive Input Understanding →
State. The remaining 12 irrelevant ASK need stronger counterfactual candidate
instrumentation before attributing them to Information Value, Candidate
Generation, or Policy.

## Minimal future repair boundary

Do not alter Information Value, cost, diminishing return, or bounded stopping to
mask these failures. The smallest coherent repair surface is:

1. make a goal-aware Dependency Resolver receive a validated task/goal;
2. make the diary tool contract discriminate entry-shaped versus summary-shaped
   payloads and require source cardinality/date/provenance for the latter;
3. fail closed when that required summary provenance is absent.

The artifact JSON files retain each case-level chain and the underlying
taxonomy. This report makes no performance or generalization claim.
