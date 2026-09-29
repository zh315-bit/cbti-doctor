# Step 8.6 Regression Report

Implemented V1.2.1 hard preconditions and diary projection integrity without
running Benchmark V2.

Targeted regression: **23 passed, 0 failed** across the new hard-precondition
tests plus existing V1.2 Information Value and V1.1 sufficiency tests. The full
suite was started with the repository `unittest` discovery command; its extended
model/dependency portion did not complete within the interactive observation
window, so no full-suite pass count is claimed here.

New coverage verifies evidence retrieval preconditions, evidence reuse,
authorized/available diary reads, unavailable/unauthorized non-reads, optional
vs decision-relevant state, diary cardinality/date/provenance invariants, and
invalid projection rejection. Information Value tests continue to pass, showing
the optional mechanism remains active after hard-precondition evaluation.
