# Step 9.33 — R1/R2/R3 Architecture Repair Implementation

Status: mechanisms implemented in scoped Agent modules; focused contracts pass; full regression blocks treatment freeze and Step 9.34 readiness.

## Baseline and treatment candidate

Pre-change Agent aggregate was verified against Step 9.32 baseline: `4e2bffea0d7eaa9299074a960df84a1806b3ae9d4930662929abc58ca5b2ae79` (MATCH). The post-change diagnostic aggregate is `710860b0af6c313b5cf49939f41446144641d3076afdd47000c7d1e612817ebb`. It is explicitly **not frozen** because the required complete regression pass did not occur.

## Implemented repairs

- R1: Evidence need no longer depends on personal-decision completeness. Required diary resource is resolved first, then required evidence; after tool projection the production loop refreshes requirements/dependencies. Unavailable resources/evidence become terminal availability state for the current goal and cannot create fabricated facts/evidence or automatic loops.
- R2: Explicit safety/execution classes remain hard fail-closed preconditions. Generic decision-validity dependencies are soft, leave a trace and proceed to the information-value gate. Candidate counterfactual value drives ASK versus bounded answer; direct material decisions remain eligible for necessary ASK.
- R3: `fact_status`, `target_status`, and `fact_conflicts` carry ASSERTED/DERIVED/RETRIEVED/UNKNOWN/UNAVAILABLE/NOT_APPLICABLE/INVALID semantics. Explicit unavailability after an ASK persists; semantically equivalent target aliases are normalized for duplicate suppression; divergent assertions are retained as INVALID conflict, while explicit correction language retains existing correction semantics. Status and conflict provenance reach snapshots and Answer Context.

No Agent behavior was added for a benchmark case, ID, fixture, expected action or expected path.

## Changed files (11)

Production modules: `adaptive_agent/answer_generation.py`, `candidates.py`, `dependency_resolver.py`, `information_value.py`, `input_understanding.py`, `preconditions.py`, `requirements.py`, `runner.py`, `state.py`, `state_update.py`. Added tests: `tests/test_step9_33_r1_r2_r3_repairs.py`.

## Regression blockers

Full non-benchmark suite: 288 run, 21 failures, 1 error. Failing assertions cluster around legacy ASK-before-independent-RETRIEVE expectations, legacy generic validity-as-hard behavior, and source hash checks anchored to the pre-repair freeze. Exact failing test IDs:

```text
test_adaptive_foundations.AdaptiveFoundationTests.test_question_is_ranked_by_goal_value_not_requirement_order
test_adaptive_loop.AdaptiveLoopTests.test_ask_stops_the_current_turn_without_running_tools
test_adaptive_service.AdaptiveServiceTests.test_two_ask_turns_preserve_goal_facts_and_action_history
test_policy_refinement.PolicyRefinementTests.test_direction_goal_stops_asking_while_critical_fields_still_missing
test_policy_refinement.PolicyRefinementTests.test_exact_prescription_does_not_use_directional_shortcut
test_policy_refinement.PolicyRefinementTests.test_explicit_goal_factor_remains_valuable_after_schedule_is_known
test_policy_refinement.PolicyRefinementTests.test_known_alternative_and_unanswered_question_not_repeated
test_policy_refinement.PolicyRefinementTests.test_more_questions_are_allowed_when_goal_has_more_dependencies
test_policy_refinement.PolicyRefinementTests.test_question_order_independent_of_requirements_permutation
test_step9_13a_authorization_infrastructure.AuthorizationInfrastructureTests.test_step9_24_candidate_freeze_matches_authorized_inventory
test_step9_18_information_value_gate.InformationValueGateTests.test_validity_critical_personalized_fact_cannot_be_suppressed
test_step9_28_v4_runner.V4RunnerPreparationTests.test_frozen_identities_match_before_any_formal_attempt
test_step9_28_v4_runner.V4RunnerPreparationTests.test_prior_ledger_blocks_any_automatic_rerun
test_step9_28_v4_runner.V4RunnerPreparationTests.test_unissued_template_cannot_create_a_ledger_or_read_a_case
test_v1_1_sufficiency_ask.SufficiencyAskControlTests.test_one_decision_relevant_fact_missing_still_asks
test_v1_2_1_preconditions.HardPreconditionTests.test_optional_state_stays_optional_but_genuine_critical_state_asks
test_v1_2_1_preconditions.HardPreconditionTests.test_unanswered_validity_question_is_deferred_not_repeated
test_v1_2_1_preconditions.HardPreconditionTests.test_validity_critical_trace_and_semantic_boundary
test_v1_2_1_preconditions.HardPreconditionTests.test_validity_criticality_is_goal_dependent_and_diary_precedes_ask
test_v1_2_2_dependency_contract.DependencyContractTests.test_validity_state_is_goal_dependent_and_uses_ask
test_v1_2_information_value.InformationValueTests.test_decision_changing_missing_is_high_and_asks
ERROR setUpClass: test_step9_30a2_lineage_sidecar.Step930a2LineageSidecarTests (frozen identity mismatch; fail closed)
```

This means `TREATMENT_FREEZE_CREATED=NO` and `READY_FOR_STEP9_34_PAIRED_EVALUATION_PRECHECK=NO`; the diagnostic hash must not be treated as a frozen treatment identity.

## Preregistration and prohibited activity

Step 9.32 repair design, paired protocol, synthetic plan and baseline freeze hashes remain unchanged. No benchmark/scoring/adjudication artifacts were modified. No V4 rerun, V5 creation/access, paired evaluation, or benchmark model/Agent/RAG call occurred.
