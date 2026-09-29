# Step 9.10a — Evaluation Harness Fix Boundary (Design Only)

## Allowed

- Repair the `state_view` wrapper binding so it calls a captured original
  serializer rather than a module attribute that may be monkey-patched.
- Add harness-only tests for callback binding, trace construction, ledger
  callbacks, and non-recursive serialization.
- Add runner instrumentation needed to preserve independent recovery attempt
  identity and trace lineage.

## Prohibited

- Any Adaptive Agent, State, requirements, DependencyResolver, policy,
  information-value, tool, RAG, diary-contract, input-understanding, or
  answer-generation behavior change.
- Benchmark V2, rubric, fixture, scoring, model/provider, or case-specific
  modification.
- Rewriting, deleting, or reclassifying the consumed Step 9.8 history.

## Equivalence evidence required in Step 9.10b

1. Same `/api/chat` production components and session path.
2. Same case inputs, follow-up release, diary visibility, and tool interface.
3. Same final response/state for deterministic synthetic fixtures before and
   after the harness repair.
4. Wrapper records additional trace fields only; it does not mutate the state
   it serializes.
5. A direct first-case trace-construction test proves the original serializer is
   called exactly once and no recursive module binding remains.

This boundary is a proposed future implementation scope. It authorizes no code
change and no evaluation run.
