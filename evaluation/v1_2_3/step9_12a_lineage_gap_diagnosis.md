# Step 9.12a — Production Trace Lineage Gap Diagnosis

## Scope and evidence

This is a read-only diagnosis of the real local Step 9.12 synthetic production smoke. No Agent, benchmark, scoring, model configuration, or execution artifact was modified. Benchmark V2 was not run and Benchmark V3 was not accessed.

The observed request completed normally: State was created, an action was recorded, and an answer was returned. The final mutable State exposed `goal_id`, `semantic_id`, `dependency_id`, `action_id`, `tool_result_id`, and `state_update_id`, while the preflight observer reported `precondition_id=null` and `candidate_id=null`.

## Exact production path

`/api/chat` enters `main_flask.create_app`, calls `AdaptiveChatService.chat`, restores/merges session State, and invokes `AdaptiveAgentLoop.run_turn`. The loop refreshes effective requirements and dependencies, evaluates hard preconditions, generates candidates, selects an action, records an action, invokes a tool when needed, updates State, and refreshes/re-evaluates before the final answer.

For the smoke's knowledge-answer path, the relevant event sequence is:

1. Goal semantics form an EVIDENCE dependency.
2. `evaluate_preconditions` creates a hard EVIDENCE precondition with `precondition_id` and a `RETRIEVE` `ActionCandidate` with `candidate_id` and `source_precondition_id`.
3. The runner records the selected candidate in the first `DECISION` snapshot and records `selected_candidate_id` on the RETRIEVE action.
4. Retrieval writes a `tool_result_id` and a `state_update_id`; a subsequent refresh marks evidence satisfied.
5. The final ANSWER is a later, policy-selected action. It has no active hard precondition by design.

The complete event-level provenance is preserved in `LoopResult.state_history` and is passed to the evaluation recorder. The final mutable State is a current-state view, not an append-only history: candidate generation resets `considered_information`, and precondition evaluation resets `preconditions_considered` on each refresh.

## Code evidence

- `adaptive_agent/preconditions.py` assigns IDs to both precondition records and mandatory `ActionCandidate`s.
- `adaptive_agent/candidates.py` resets per-revision candidate-observability lists. Its hard-precondition observability record intentionally omits the candidate ID even though the returned `ActionCandidate` has one.
- `adaptive_agent/runner.py` stores per-step `DECISION`/tool snapshots in `LoopResult.state_history`, then refreshes State after tool results.
- `adaptive_agent/state.py` stores the selected candidate on each action as `selected_candidate_id`.
- `adaptive_agent/state_update.py` emits tool-result/state-update lineage with the source action ID.
- `scripts/preflight_step9_12_local.py` instead inspected only the final State, searched final `preconditions_considered` and final `considered_information`, and required every ID to be non-null.
- `evaluation/v1_2_1/step9_7_integration_traces.jsonl` (I1) demonstrates the intended multi-revision chain: the RETRIEVE decision has a precondition and candidate ID; the later ANSWER is valid after the dependency is SATISFIED without an active precondition.

## Failure classification

| Field | Classification | Evidence-based conclusion |
| --- | --- | --- |
| `precondition_id` | F — valid action path has no active precondition | The final ANSWER follows a satisfied evidence dependency. Its preceding RETRIEVE precondition exists in the first decision snapshot, but should not remain active after satisfaction. |
| `candidate_id` | G — observer queried the wrong State representation | The `ActionCandidate` was created with an ID and its action records `selected_candidate_id`; the final `considered_information` list is revision-scoped/reset and is not its durable ID carrier. |

Primary root cause: **LINEAGE_SCHEMA_TOO_STRICT**. The Step 9.12 preflight assumed every final action must simultaneously expose every lineage-node type from every prior revision.

Secondary causes: **TEST_COVERAGE_GAP** for this real-preflight observer and a **TRACE_OBSERVABILITY_BUG** in the preflight consumer/query. There is no evidence of a production wiring bug, object-ID propagation bug, trace-recorder bug, or Agent behavior bug.

## Is a single full lineage shape valid?

Only partially. The architecture supports at least these valid shapes:

```text
DEPENDENCY_FORCED_TOOL
goal → semantic → dependency → precondition → candidate → action → tool_result → state_update

POLICY_SELECTED_ANSWER_AFTER_SATISFACTION
goal → semantic → dependency(SATISFIED) → candidate → action

OPTIONAL_POLICY_ACTION
goal → candidate → action
```

Therefore, a precondition is required only for an action whose origin is a hard precondition. It is not a mandatory field for every later answer. Event/revision lineage must be checked in the decision/tool snapshots, not inferred from fields that remain in the final mutable State.

## Frozen-identity impact

No frozen file was changed in this diagnosis. If approved later, an observer-only repair would change the Harness/observability domain, not Agent behavior, Benchmark V2, or scoring. It must receive an explicit Harness freeze revision; Step 9.11 must not be silently rewritten.

## Final status

```text
ROOT_CAUSE = LINEAGE_SCHEMA_TOO_STRICT
PRECONDITION_ID_FAILURE_CLASS = F
CANDIDATE_ID_FAILURE_CLASS = G
FULL_LINEAGE_ASSUMPTION_VALID = PARTIAL
AGENT_BEHAVIOR_BUG = NO
TRACE_OBSERVABILITY_BUG = YES (preflight observer only)
LINEAGE_SCHEMA_ISSUE = YES
MINIMAL_FIX_POSSIBLE_WITHOUT_BEHAVIOR_CHANGE = YES
BENCHMARK_V2_EXECUTED = NO
BENCHMARK_V3_ACCESSED = NO
AGENT_BEHAVIOR_MODIFIED = NO
BENCHMARK_MODIFIED = NO
SCORING_MODIFIED = NO
READY_FOR_AUTHORIZED_RUN = NO
```
