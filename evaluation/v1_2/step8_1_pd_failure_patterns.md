# PD Failure Patterns from Frozen V1.1 Traces

This analysis uses only the 9 PD six-ASK-limit traces in the frozen Step 7.4
raw artifacts. It does not introduce case-specific rules.

## Pattern 1: Requirements Completeness Masquerades as Decision Value

The agent keeps requesting total sleep, awakenings, and recent pattern after a
bounded directional answer is already possible. These fields can be useful for
a full prescription, but are not automatically worth another user turn for a
narrow direction question. Their default value is LOW or MEDIUM, not HIGH.

## Pattern 2: Extraction Failure Expands the Remaining Set

When explicit facts do not enter State, every downstream field appears missing.
The information-value layer cannot rescue a missing fact that was never
represented; it only sees a falsely large uncertainty set. This is a combined
Step 7.1 plus sufficiency failure.

## Pattern 3: No Diminishing-Return Threshold

The sixth ASK can pass the same eligibility shape as the first because the
current policy has no increasing acquisition threshold. V1.2 should require
progressively stronger counterfactual impact as prior ASK count and cognitive
burden rise; it should not use a fixed maximum-ASK rule.

## Pattern 4: Resource/Answer Alternatives Are Not Compared at Value Level

A diary or bounded answer can sometimes dominate another ASK. The decision must
compare READ_DIARY, RETRIEVE, ASK, and ANSWER using value, cost, and answer-risk,
not only whether a requirement remains missing.

## Pattern 5: Detail Improvement Is Treated as Personalization Necessity

Some follow-up facts enrich an answer without changing its direction or safety
scope. These should be LOW value and omitted once the bounded answer is adequate.
