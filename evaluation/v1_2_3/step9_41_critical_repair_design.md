# Step 9.41 — Critical Regression Repair Design

Status: design only. No Agent code, benchmark, rubric, metric, adjudication, claim policy, V4, or V5 was changed or executed/accessed.

## Canonical invariant

Resource/evidence sufficiency and answer authorization are separate checks. Completing a retrieval can satisfy only its matching evidence dependency; it cannot authorize an individualized recommendation whose personal-state dependency is still unresolved. An information-value gate may suppress optional/detail acquisition, but it may not demote a dependency required to keep a selected individualized action safe, valid, correctly scoped, or executable.

The final answer authorization gate runs after state updates, tool/resource projection, evidence availability, and dependency re-evaluation, but before personalized answer-context finalization and generation. It consumes goal/task type, effective requirements, dependency targets/status/provenance, personalization materiality, safety/execution preconditions, resource/evidence status, answer scope, candidate answer action, and previous acquisition attempts. It returns exactly one of:

- `AUTHORIZED_FULL`: all dependencies material to the proposed personalized action are satisfied by valid target-matched state, required evidence is resolved, and safety/validity/execution gates pass.
- `AUTHORIZED_BOUNDED`: a safe general/non-personalized scope is available. Narrow scope, preserve limitations, and exclude actions that depend on unresolved personal facts. Missing optional detail is not blocking.
- `BLOCKED_NEEDS_INFORMATION`: no safe bounded response satisfies the requested decision, but a material dependency has a valid remaining acquisition path. Route one ASK/READ_DIARY and preserve attempt history.
- `BLOCKED_UNSAFE_OR_INVALID`: relevant state is invalid/conflicted/prohibited, or neither safe bounded fallback nor valid acquisition route exists. Do not generate the unsafe answer.

These are the concrete outcomes for conceptual `ANSWER_AUTHORIZED`, `ANSWER_BOUNDED`, and `ANSWER_BLOCKED` respectively. Blocked outcomes are distinct: one routes information acquisition; the other refuses/stops the unsafe scope.

## Keeping R1/R2/R3

R1 remains intact because this gate does not run before retrieval. Independent required evidence/resource acquisition remains actionable while unrelated personal facts are missing. Only after acquisition does the gate decide what answer scope the available state supports; satisfying evidence never satisfies a personal-state dependency.

R2 remains intact because “personalization-related” is not enough to make a field hard. A dependency blocks full scope only when plausible values materially change safety, validity, individualized recommendation scope, or execution correctness, and no safe bounded fallback covers that action. Presentation preferences and other detail-only unknowns remain optional and can still be suppressed by information value.

R3 remains intact: `ASSERTED` satisfies only an exact dependency when provenance/scope/freshness validate; `DERIVED` requires permitted derivation and valid inputs; `RETRIEVED` ordinarily satisfies only its matching resource/evidence dependency (a typed user-linked record may satisfy personal state only if explicitly allowed and validated); `UNKNOWN`, `DEFERRED`, and `UNAVAILABLE` are not satisfied; `NOT_APPLICABLE` counts only when the dependency contract permits and validates it; `INVALID` never satisfies. Unknown/deferred/unavailable may support an explicitly safe bounded non-personalized scope, not the individualized action they fail to establish.

## Transition and placement

If a previously full answer loses a required personal dependency, transition `FULL → BOUNDED` when safe general guidance remains; otherwise transition `ANSWER → ASK` only when the fact is material, resolvable, and not already exhausted. If neither route is safe/available, block. The information-value gate runs before this authorization decision: it optimizes optional acquisition, while the final gate protects the validity of the proposed answer.

Four existing modules are the proposed implementation surface; no new module is required by this design:

| File | Function/class | Responsibility |
|---|---|---|
| `adaptive_agent/dependency_resolver.py` | `DependencyResolver.resolve`, `validity_critical_fields` | Form typed, target-specific personalization dependencies only when material; preserve independent evidence/resource dependencies and provenance. |
| `adaptive_agent/preconditions.py` | `evaluate_preconditions` | Preserve hard safety/execution authority; surface a necessary acquisition candidate without making all personal facts hard or suppressing independent retrieval. |
| `adaptive_agent/runner.py` | `AdaptiveAgentLoop.run_turn`, `_refresh` | Re-evaluate after each tool/state update; gate every ANSWER immediately before generation; route bounded answer, one acquisition action, or fail-closed stop; trace the enum/reasons. |
| `adaptive_agent/answer_generation.py` | `build_answer_context`, `LLMAnswerGenerator.answer` | Enforce the authorized scope at the State→Answer boundary and prevent unresolved personal fields or evidence from implying unsupported personalization. |

The exact signatures/field contract and responsibilities are in `step9_41_critical_repair_design.json`. Placement remains conceptual; Step 9.42 must verify signatures against current code before implementation.

## Tests and future gates

The independent fixtures T1–T6 and preservation assertions are in `step9_41_synthetic_test_plan.json`. Future implementation must pass all Step 9.33/9.33a tests plus the new tests, necessary-ASK preservation, low-value-ASK suppression, independent resource acquisition, no fabricated personalization, and no infinite ASK/retrieve loops.

After implementation, create and freeze a new treatment-v2 identity without overwriting the baseline, treatment-v1, or Step 9.39 results. A V4 regression-only confirmation would require a separate protocol and authorization; V4 remains development evidence and reuse is not automatic. A sealed unseen V5 is a distinct later stage after repair/regression/freeze and separate authorization.

`RESUME_DESCRIPTIVE_MATCHED_COMPARATIVE_CLAIM_ELIGIBLE = NO` remains unchanged until treatment-v2 shows critical failures no greater than baseline and does not materially destroy prior primary gains. Existing claim policy is untouched.

SAFETY_INVARIANT_DESIGNED = YES  
FINAL_ANSWER_AUTHORIZATION_GATE_DESIGNED = YES  
R1_PRESERVED_BY_DESIGN = YES  
R2_PRESERVED_BY_DESIGN = YES  
R3_PRESERVED_BY_DESIGN = YES  
FULL_ANSWER_AUTHORIZATION_RULE = all material dependencies and safety/validity/execution preconditions for proposed individualized action are satisfied by validated target-matched state  
BOUNDED_ANSWER_RULE = safe general scope exists; unresolved dependent individualized actions are excluded and limitations retained  
BLOCK_RULE = no safe bounded scope; route one valid unexhausted material acquisition, otherwise block unsafe/invalid generation  
IMPLEMENTATION_FILE_COUNT = 4  
IMPLEMENTATION_FILES = adaptive_agent/dependency_resolver.py, adaptive_agent/preconditions.py, adaptive_agent/runner.py, adaptive_agent/answer_generation.py  
NEW_SYNTHETIC_TEST_COUNT = 6  
V4_ROLE = regression-only confirmation after separate protocol/authorization; development evidence, not unseen evaluation  
V5_ROLE = separately authorized sealed unseen held-out for future generalization claims  
RESUME_DESCRIPTIVE_MATCHED_COMPARATIVE_CLAIM_ELIGIBLE = NO  
AGENT_MODIFIED = NO  
V4_RERUN = NO  
V5_CREATED = NO  
V5_ACCESSED = NO  
READY_FOR_STEP9_42_CRITICAL_REPAIR_IMPLEMENTATION = YES
