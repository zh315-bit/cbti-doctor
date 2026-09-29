# V1.2.1 Hard Preconditions & State Integrity

V1.2.1 separates validity requirements from optional information value.

1. **Hard Preconditions** are evaluated before candidate/value/cost comparison.
   - `EVIDENCE`: an evidence-required, otherwise answerable goal with no evidence
     requires `RETRIEVE`.
   - `RESOURCE`: a diary-derived goal requires `READ_DIARY` when the authorized,
     available diary is unread. Unavailable or unauthorized resources lead only
     to an explicit bounded/unavailable answer.
   - `CRITICAL_STATE`: remains intentionally narrow: only decision-relevant
     unknown fields can produce `ASK`; secondary detail does not become hard.
2. **Optional acquisition** then uses the existing Information Value, Cost, and
   Diminishing Return mechanisms unchanged.
3. **Bounded answers** cannot replace a satisfiable hard precondition because
   preconditions return the only candidate for that step.

Diary results now record source/projected entry counts, dates, projection status
and warnings. When an explicit entry projection is malformed, State marks it
`invalid`, stores no diary facts, and cannot silently derive an answer from it.
Provenance carries this projection record with every diary fact.

Known limitation: whether a free-text input is classified as a knowledge or
diary-derived goal remains an Input Understanding responsibility. Hard
preconditions protect dependencies that have entered State; they do not invent
a dependency from an incorrect upstream task classification.
