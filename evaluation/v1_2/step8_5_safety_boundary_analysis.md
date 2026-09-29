# Step 8.5 Safety Boundary Analysis

The frozen traces support a separation between **hard preconditions** and
cost-aware optional acquisition. KQ-02/KQ-05 show that a knowledge claim whose
requirements include evidence cannot safely fall through to a bounded stop just
because personalized fields were exhausted. DA-07 shows that a diary-based goal
with an authorized, available required diary cannot treat `READ_DIARY` as an
optional ASK alternative. These failures arise before a valid Information Value
comparison: the required dependency never reached candidate generation.

Recommended V1.2.1 design (not implemented):

```text
Layer 1  Hard Preconditions: valid task/goal requirements; mandatory evidence/resource readiness
Layer 2  Information Value: rank optional missing information only
Layer 3  Acquisition Cost: compare eligible optional paths
Layer 4  Diminishing Return: raise threshold only for optional acquisition
Layer 5  Bounded Answer: permitted only after hard preconditions are met, or with an explicit unavailable-precondition limitation
```

Diary projection is independent: preserve an entry-level Tool → State contract,
provenance and cardinality before deterministic diary derivation or answer
generation. A policy rule must not mask this data-integrity defect.
