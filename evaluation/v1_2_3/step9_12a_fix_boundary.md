# Step 9.12a — Minimal Trace Fix Boundary (Design Only)

## Purpose

This is a design boundary, not an implementation authorization. It addresses only the Step 9.12 preflight's lineage observation query. It must not change an Agent action, state transition, dependency, policy, model call, benchmark input, or score.

## Minimal approved-scope design for a later step

Modify only the synthetic-smoke observability logic in `scripts/preflight_step9_12_local.py`:

1. Attach an in-memory capture recorder to the synthetic service and retain the returned `LoopResult`/`state_history`; do not write a formal Benchmark trace or attempt.
2. Evaluate lineage per action/revision rather than from final State alone.
3. Obtain the candidate relationship from `DECISION.chosen_action.candidate_id` and the corresponding action's `selected_candidate_id`.
4. Require `source_precondition_id` only where the selected candidate origin is `HARD_PRECONDITION`.
5. Validate tool events by linking `source_action_id` to the following tool-result and state-update event.
6. Treat a later ANSWER without a precondition as valid when its dependency is SATISFIED, UNAVAILABLE with a bounded path, or otherwise has no hard-precondition origin.

The resulting observer should report action-specific lineage shapes rather than a single `all(ids.values())` condition.

## Explicit non-goals

- Do not create synthetic precondition or candidate IDs merely to satisfy the checker.
- Do not retain obsolete preconditions in State after a dependency is satisfied.
- Do not change `DependencyResolver`, `preconditions.py`, candidate generation, policy, information value/cost, Answer Generation, diary handling, or State semantics.
- Do not add Benchmark case IDs, prompts, or case-specific branches.
- Do not run Benchmark V2, access Benchmark V3, or issue a real-model request as part of the repair.

## Required verification if implementation is later authorized

- A forced RETRIEVE/READ_DIARY action must show dependency → precondition → candidate → action → tool result → state update.
- A later ANSWER must be accepted without a stale precondition, while preserving its action/candidate relationship.
- Repeated smoke inspection must not mutate State or append benchmark artifacts.
- Existing synthetic, integration, guard, and non-external-model regressions must pass.
- The Step 9.11 frozen files and original Step 9.8 history must remain immutable.

## Identity consequence

This would be a Harness/observability-only change. It would require a new explicit Harness freeze/reconciliation before any authorized evaluation can proceed. It does **not** authorize a run and does **not** alter the frozen Agent, Benchmark V2, or scoring identities.
