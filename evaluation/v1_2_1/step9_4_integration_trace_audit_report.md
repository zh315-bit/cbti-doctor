# Step 9.4 — Dependency Integration & Trace Audit

## Scope and regression result

This audit used synthetic, non-Benchmark calls through the actual
`AdaptiveAgentLoop` and tool interfaces. Benchmark V2 was not run; Benchmark V3
was not created, viewed, or used; no Agent behavior was changed as part of this
audit.

| Suite | Result |
| --- | --- |
| Step 9.4 runtime/trace audit + Step 9.3 mechanisms | 14 passed, 0 failed |
| Non-model full regression suite | 121 passed, 0 failed, 0 skipped |
| `tests.test_model_configuration` | **NOT_VERIFIED** — aggregate command did not return within this execution environment's 30-second window; it must not be counted as passed |

## Runtime call chain

```text
main_flask.py /api/chat
→ AdaptiveChatService.chat (service.py)
→ AdaptiveAgentLoop.run_turn (runner.py)
→ SufficiencyEstimator.update
→ build_candidates (candidates.py)
→ evaluate_preconditions (preconditions.py)
→ DependencyResolver.resolve (dependency_resolver.py)
→ mandatory candidate or optional IV/Cost/Return/Stop candidates
→ HeuristicDecisionPolicy.choose
→ RETRIEVE / READ_DIARY / ASK / ANSWER
→ state_update.py
→ _refresh: dependency re-resolution
→ answer generator
```

The resolver is therefore not test-only or parallel: `build_candidates` consumes
its output during every `runner._refresh`, and runner snapshots persist the
result before/after tool calls.

## Lifecycle audit

| Synthetic scenario | Observed lifecycle | Result |
| --- | --- | --- |
| Knowledge semantics + wrong task signal + no evidence | EVIDENCE REQUIRED → RETRIEVE → SATISFIED | PASS |
| Diary-analysis semantics + wrong task signal + authorized diary | RESOURCE AVAILABLE → READ_DIARY → SATISFIED | PASS |
| Diary goal + unavailable resource | RESOURCE UNAVAILABLE → ANSWER limitation, no tool call | PASS |
| General knowledge + existing evidence | EVIDENCE SATISFIED, no duplicate RETRIEVE; no RESOURCE | PASS |
| Invalid summary result | READ_DIARY → INVALID projection → no diary fact written | PASS |

No recorded mandatory precondition was suppressed by Information Value, cost,
diminishing return, or ordinary bounded stop.

## Diary Contract integration and fail-closed verification

`ENTRY_SHAPED` with count/date/provenance enters State after validation.
`SUMMARY_SHAPED` with complete metadata enters as a summary only. Summary missing
cardinality, date coverage or provenance; entry cardinality/date mismatch; and
UNAVAILABLE all result in `projection_status=invalid` or unavailable State,
with no diary-derived fact. The audit's invalid-summary loop confirmed the final
State and answer context have no `recent_sleep_pattern` fact.

## Trace completeness matrix

| Trace question/field | ASK | RETRIEVE | READ_DIARY | ANSWER | Audit |
| --- | --- | --- | --- | --- | --- |
| goal, task type, facts | present | present | present | present | PASS |
| dependency type/status/reason/source | present | present | present | present | PASS |
| satisfiers considered / selected satisfier | present in precondition | present | present | present/fallback | PASS |
| information value/cost/rejection | present for optional candidates | bypassed when mandatory | bypassed when mandatory | present if optional | PASS |
| tool result and State update | n/a | present | present | n/a | PASS |
| dependency after action | n/a | present in post-tool refresh | present in post-tool refresh | present | PASS |
| explicit goal-semantic parse | ambiguous: `dependency_source` records `goal_semantics`, but no structured matched-semantic object | same | same | same | DEFECT |
| dependency-to-candidate identifier | ambiguous: causality is carried by precondition fields, not a stable dependency id | same | same | same | DEFECT |

## Integration defects found (recorded, not fixed)

1. **Requirements remain task-type-derived after goal-semantic dependency repair.**
   In the wrong-task knowledge synthetic path, EVIDENCE correctly became
   SATISFIED after RETRIEVE, but the inherited personalized Requirements could
   still produce a later ASK. This is a Requirements/goal-semantics integration
   gap, not a DependencyResolver wiring failure.
2. **Goal semantics trace is label-level rather than structured.** The trace can
   show that goal semantics participated, but cannot show which semantic rule or
   span matched.
3. **No stable dependency id joins dependency, precondition and candidate.** The
   causal chain is reconstructable by type/target but not relationally explicit.

## Recommendation

Do **not** claim readiness for Benchmark V2 rerun solely from this audit. The
mandatory lifecycle and Diary Contract V2 wiring are integrated and fail closed,
but the two observability issues and the task-derived Requirements follow-up
ASK should be reviewed as a separate, bounded design decision. A Step 9.5
design/fix proposal is reasonable after human approval; no Policy tuning is
indicated by this audit.
