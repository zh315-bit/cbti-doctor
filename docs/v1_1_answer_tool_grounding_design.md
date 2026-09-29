# Adaptive Agent V1.1: Answer and Tool Data Grounding

## Scope

Step 7.3 hardens answer context construction, claim provenance, deterministic
data projection, diary summaries, uncertainty preservation, and final answer
validation. Input understanding, sufficiency, candidate ranking, Decision
Policy, RAG implementation, Benchmark V2, baseline artifacts, and scoring are
unchanged.

## Claim Taxonomy and Provenance

The answer context now distinguishes user-derived, diary-derived,
deterministically-derived, evidence-grounded, and unsupported claims.
`AdaptiveAgentState.claim_provenance` records claim text, claim type, source,
source field(s), derivation, and certainty. Explicit user facts reference their
Step 7.1 provenance; deterministic records reference State fields and named
calculations; retrieved evidence is indexed as `evidence:N`.

## Deterministic Projection

`deterministic_claim_records()` uses the shared cross-midnight duration helper.
It computes time in bed, sleep efficiency, diary entry count, diary average
total sleep, and date coverage only from available values. Ranges and
approximations do not produce a unique duration. Missing diary days are not
invented or filled with zeroes.

## Validation and Uncertainty

The final answer passes through deterministic numeric/evidence validation and
precision protection. Unsupported quantitative or medical-rule claims are
removed. Exact clock wording is weakened when State stores a range or
approximate value. Unavailable diary data never enters the answer context.

## Tests

`tests/test_v1_1_answer_tool_grounding.py` covers cross-midnight duration,
range/approximate preservation, diary counts/averages/date coverage,
unavailable data, user-fact grounding, unsupported claims, evidence-backed
thresholds, provenance records, and tool-to-State-to-answer consistency.
