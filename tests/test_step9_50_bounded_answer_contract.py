"""Synthetic-only coverage for the frozen Step 9.50 bounded-answer contract."""
import unittest

from adaptive_agent.answer_generation import (
    authorize_final_answer, build_answer_context, validate_bounded_response,
)
from adaptive_agent.input_understanding import Understanding
from adaptive_agent.requirements import RequirementSet
from adaptive_agent.runner import AdaptiveAgentLoop
from adaptive_agent.state import ActionCandidate, AdaptiveAgentState, TaskType


def fixture_state(*, evidence=True, facts=True, missing_status="UNKNOWN", hard=False):
    state = AdaptiveAgentState(
        goal="synthetic question about 规律作息与睡眠机制", task_type=TaskType.PERSONALIZED_DECISION,
        answer_scope="仅在有依据的范围内回答；保留已知约束。",
        facts={"known_constraint": "synthetic fixed morning obligation"} if facts else {},
        fact_sources={"known_constraint": {"source_type": "user_explicit", "certainty": "exact"}} if facts else {},
        fact_status={"choice_factor": missing_status},
        target_status={"choice_factor": {"status": missing_status}},
        decision_missing=["choice_factor"], decision_relevant_missing=["choice_factor"],
        information_estimates={"choice_factor": {"decision_impact": "decision_changing"}},
    )
    state.dependencies_considered = [{
        "dependency_id": "dep_synthetic_choice", "dependency_type": "USER_FACTS",
        "target": "choice_factor", "status": missing_status, "requiredness": "required",
        "fallback": "bounded general information",
    }]
    if evidence:
        state.evidence = ["合成证据说明规律作息与一般睡眠机制之间的关联。"]
        state.evidence_sources = [{"evidence": state.evidence[0], "source_type": "RAG",
                                  "goal_id": state.goal_id, "retrieval_query": state.goal,
                                  "projection_status": "valid"}]
        state.dependencies_considered.append({
            "dependency_id": "dep_synthetic_evidence", "dependency_type": "EVIDENCE",
            "target": "external_evidence", "status": "SATISFIED", "requiredness": "required",
        })
    if hard:
        state.preconditions_considered = [{
            "precondition_id": "pre_synthetic_hard", "type": "VALIDITY_STATE",
            "target": "choice_factor", "status": "invalid",
        }]
    return state


def requirements(*, fields=("choice_factor",), scope="仅在有依据的范围内回答；保留已知约束。"):
    return RequirementSet((), (), False, decision_fields=tuple(fields), answer_scope=scope,
                          precondition_classes={})


def authorize(state=None, **kwargs):
    state = state or fixture_state(**kwargs)
    return state, authorize_final_answer(state, requirements())


class Step950BoundedAnswerContractTests(unittest.TestCase):
    def test_t01_required_sleep_state_is_not_used_for_personal_priority(self):
        state, auth = authorize()
        self.assertEqual(auth["status"], "AUTHORIZED_BOUNDED")
        self.assertIn("individualized_action:choice_factor", auth["bounded_excluded_actions"])

    def test_t02_known_morning_constraint_is_retained(self):
        state, auth = authorize()
        context = build_answer_context(state)
        self.assertEqual(context["user_facts"]["known_constraint"]["value"], "synthetic fixed morning obligation")
        self.assertTrue(auth["bounded_supported_content_basis"])

    def test_t03_general_mechanism_is_grounded_not_personal_causation(self):
        state, auth = authorize()
        answer = "一般睡眠机制与规律作息有关。"
        self.assertEqual(auth["status"], "AUTHORIZED_BOUNDED")
        self.assertIsNotNone(validate_bounded_response(answer, state, auth))

    def test_t04_hypothesis_language_does_not_claim_proven_individual_cause(self):
        state, auth = authorize()
        answer = "规律作息可能与一般睡眠机制有关。"
        self.assertIsNotNone(validate_bounded_response(answer, state, auth))

    def test_t05_supported_general_cycle_remains_answerable(self):
        state, auth = authorize()
        answer = "一般睡眠机制可能受到规律作息影响。"
        self.assertIsNotNone(validate_bounded_response(answer, state, auth))

    def test_t06_positive_user_fact_is_preserved_as_basis(self):
        state, auth = authorize()
        self.assertIn("fact:known_constraint", auth["bounded_supported_content_basis"])
        self.assertIn("synthetic fixed morning obligation", build_answer_context(state)["user_facts"]["known_constraint"]["value"])

    def test_t07_exhausted_acquisition_history_does_not_change_epistemic_status(self):
        state, auth = authorize()
        state.action_history.append({"action": "ASK", "target": "choice_factor"})
        self.assertEqual(state.fact_status["choice_factor"], "UNKNOWN")
        self.assertEqual(auth["status"], "AUTHORIZED_BOUNDED")

    def test_t08_optional_missing_detail_does_not_block_supported_answer(self):
        state, auth = authorize()
        state.information_estimates["optional_detail"] = {"decision_impact": "detail_improving"}
        result = authorize_final_answer(state, requirements())
        self.assertEqual(result["status"], "AUTHORIZED_BOUNDED")

    def test_t09_unknown_date_field_is_not_invented(self):
        state, auth = authorize()
        state.fact_status["daily_total"] = "UNKNOWN"
        self.assertEqual(state.fact_status["daily_total"], "UNKNOWN")
        self.assertNotIn("daily_total", build_answer_context(state)["relevant_facts"])

    def test_t10_supported_observation_can_be_reported_without_new_threshold(self):
        state, auth = authorize()
        state.evidence.append("The synthetic observed range is 55 minutes; no stability threshold is given.")
        state.evidence_sources.append({"evidence": state.evidence[-1], "source_type": "RAG",
                                       "goal_id": state.goal_id, "retrieval_query": state.goal,
                                       "projection_status": "valid"})
        self.assertTrue(authorize_final_answer(state, requirements())["bounded_supported_content_basis"])

    def test_t11_answer_addresses_the_synthetic_request_topic(self):
        state, auth = authorize()
        self.assertIsNotNone(validate_bounded_response("规律作息是一般睡眠机制的一部分。", state, auth))

    def test_t12_missing_mechanism_evidence_stays_explicitly_bounded(self):
        state, auth = authorize()
        self.assertEqual(auth["answer_authorization_mode"], "AUTHORIZED_BOUNDED")
        self.assertTrue(auth["bounded_excluded_actions"])

    def test_t13_supported_facts_can_be_used_without_procedural_invention(self):
        state, auth = authorize()
        self.assertIn("fact:known_constraint", auth["bounded_supported_content_basis"])
        self.assertEqual(state.fact_status["choice_factor"], "UNKNOWN")

    def test_t14_bounded_limit_does_not_expand_procedure_scope(self):
        state, auth = authorize()
        self.assertEqual(auth["answer_scope"], state.answer_scope)
        self.assertIn("individualized_action:choice_factor", auth["bounded_excluded_actions"])

    def test_t15_full_and_bounded_scopes_remain_distinct(self):
        state, bounded = authorize()
        self.assertNotEqual(bounded["answer_authorization_mode"], "AUTHORIZED_FULL")
        full_state = fixture_state()
        full_state.fact_status.clear()
        full_state.target_status.clear()
        full_state.decision_missing.clear()
        full_state.decision_relevant_missing.clear()
        full = authorize_final_answer(full_state, requirements(fields=()))
        self.assertEqual(full["answer_authorization_mode"], "AUTHORIZED_FULL")

    def test_t16_optional_dependency_does_not_remove_supported_bounded_answer(self):
        state, auth = authorize()
        state.dependencies_considered.append({"dependency_id": "dep_optional", "dependency_type": "USER_FACTS",
            "target": "optional_preference", "status": "UNKNOWN", "requiredness": "optional", "fallback": None})
        self.assertEqual(authorize_final_answer(state, requirements())["status"], "AUTHORIZED_BOUNDED")

    def test_t17_required_dependency_without_fallback_requests_information(self):
        state = fixture_state(evidence=False, facts=False)
        state.dependencies_considered[0]["fallback"] = None
        state.candidate_actions.append(ActionCandidate(action="ASK", target="choice_factor"))
        auth = authorize_final_answer(state, requirements(scope=""))
        self.assertEqual(auth["status"], "BLOCKED_NEEDS_INFORMATION")

    def test_t18_hard_precondition_is_not_bounded_away(self):
        state = fixture_state(hard=True)
        auth = authorize_final_answer(state, requirements())
        self.assertEqual(auth["status"], "BLOCKED_UNSAFE_OR_INVALID")
        self.assertIn("pre_synthetic_hard", auth["blocked_precondition_ids"])

    def test_t19_deferred_and_unknown_remain_unsatisfied(self):
        for value in ("DEFERRED", "UNKNOWN"):
            with self.subTest(value=value):
                state = fixture_state(missing_status=value)
                self.assertEqual(state.target_status["choice_factor"]["status"], value)
                self.assertEqual(authorize_final_answer(state, requirements())["status"], "AUTHORIZED_BOUNDED")

    def test_t20_full_answer_is_authorized_when_required_state_is_present(self):
        state = fixture_state()
        state.fact_status["choice_factor"] = "ASSERTED"
        state.target_status["choice_factor"] = {"status": "ASSERTED"}
        state.fact_sources["choice_factor"] = {"source_type": "user_explicit"}
        state.facts["choice_factor"] = "synthetic stated choice"
        self.assertEqual(authorize_final_answer(state, requirements())["status"], "AUTHORIZED_FULL")

    def test_t21_unknown_is_not_promoted_by_retrieved_evidence(self):
        state, auth = authorize()
        state.facts["choice_factor"] = "placeholder from unknown state"
        self.assertEqual(state.fact_status["choice_factor"], "UNKNOWN")
        self.assertEqual(state.dependencies_considered[0]["status"], "UNKNOWN")
        self.assertNotIn("choice_factor", build_answer_context(state)["relevant_facts"])
        self.assertEqual(auth["status"], "AUTHORIZED_BOUNDED")

    def test_t22_deferred_fact_is_not_promoted_by_evidence(self):
        state = fixture_state(missing_status="DEFERRED")
        state.facts["choice_factor"] = "placeholder from deferred state"
        auth = authorize_final_answer(state, requirements())
        self.assertEqual(state.fact_status["choice_factor"], "DEFERRED")
        self.assertNotIn("choice_factor", build_answer_context(state)["relevant_facts"])
        self.assertNotEqual(auth["status"], "AUTHORIZED_FULL")

    def test_t23_unavailable_fact_is_not_promoted_by_fallback(self):
        state = fixture_state(missing_status="UNAVAILABLE")
        state.facts["choice_factor"] = "placeholder from unavailable state"
        auth = authorize_final_answer(state, requirements())
        self.assertEqual(state.fact_status["choice_factor"], "UNAVAILABLE")
        self.assertNotIn("choice_factor", build_answer_context(state)["relevant_facts"])
        self.assertNotEqual(auth["status"], "AUTHORIZED_FULL")

    def test_t24_required_dependency_excludes_only_unsupported_action_scope(self):
        state, auth = authorize()
        self.assertIn("dep_synthetic_choice", auth["blocked_dependency_ids"])
        self.assertIn("individualized_action:choice_factor", auth["bounded_excluded_actions"])
        self.assertTrue(auth["bounded_supported_content_basis"])

    def test_t25_hard_precondition_without_acquisition_is_complete_block(self):
        state = fixture_state(hard=True)
        state.candidate_actions.clear()
        auth = authorize_final_answer(state, requirements())
        self.assertEqual(auth["answer_authorization_mode"], "BLOCKED_UNSAFE_OR_INVALID")

    def test_t26_unsupported_directive_is_rejected(self):
        state, auth = authorize()
        self.assertIsNone(validate_bounded_response("你应该调整作息。", state, auth))

    def test_t27_bounded_answer_has_fact_and_evidence_basis(self):
        state, auth = authorize()
        self.assertIn("fact:known_constraint", auth["bounded_supported_content_basis"])
        self.assertIn("evidence:0", auth["bounded_supported_content_basis"])

    def test_t28_useful_bounded_answer_is_responsive_and_not_boilerplate(self):
        state, auth = authorize()
        answer = "规律作息与一般睡眠机制有关。"
        validated = validate_bounded_response(answer, state, auth)
        self.assertEqual(validated, answer)

        class Understander:
            def understand(self, user_input, prior_state=None):
                return Understanding("synthetic question about 规律作息与睡眠机制",
                                     TaskType.PERSONALIZED_DECISION, {})

        class Retrieval:
            def retrieve(self, query):
                raise AssertionError("bounded synthetic path must not retrieve")

        class Diary:
            def read(self, requirements):
                raise AssertionError("bounded synthetic path must not read diary")

        class Policy:
            def choose(self, current_state):
                return ActionCandidate(action="ANSWER", rationale="synthetic answer")

        class SyntheticLoop(AdaptiveAgentLoop):
            def _refresh(self, current_state, current_requirements):
                current_state.fact_status["choice_factor"] = "UNKNOWN"
                current_state.target_status["choice_factor"] = {"status": "UNKNOWN"}
                current_state.decision_missing = ["choice_factor"]
                current_state.information_estimates["choice_factor"] = {"decision_impact": "decision_changing"}
                current_state.dependencies_considered = [{
                    "dependency_id": "dep_synthetic_choice", "dependency_type": "USER_FACTS",
                    "target": "choice_factor", "status": "DEFERRED", "requiredness": "optional",
                    "fallback": "bounded answer using persisted evidence and known facts",
                }]
                return current_requirements

        class Generator:
            def __init__(self):
                self.limitation = None

            def answer(self, current_state, limitation=None):
                self.limitation = limitation
                return answer

        loop_state = AdaptiveAgentState(
            facts={"known_constraint": "synthetic fixed morning obligation"},
            fact_sources={"known_constraint": {"source_type": "user_explicit"}},
            fact_status={"sleep_onset_latency": "UNKNOWN"},
            target_status={"sleep_onset_latency": {"status": "UNKNOWN"}},
            decision_missing=["sleep_onset_latency"],
            information_estimates={"sleep_onset_latency": {"decision_impact": "decision_changing"}},
            evidence=["合成证据说明规律作息与一般睡眠机制之间的关联。"],
        )
        generator = Generator()
        req = RequirementSet((), (), False, decision_fields=("choice_factor",),
                             answer_scope="仅在已知事实和证据范围内回答。")
        loop = SyntheticLoop(Understander(), Retrieval(), Diary(), answer_generator=generator,
            requirements={TaskType.PERSONALIZED_DECISION: req}, policy=Policy(), max_steps=1)
        result = loop.run_turn("synthetic question", loop_state)
        decision = next(item["answer_authorization"] for item in result.state_history
                        if item["event"] == "DECISION" and "answer_authorization" in item)
        terminal = result.state_history[-1]
        self.assertEqual(result.status, "ANSWER")
        self.assertEqual(decision["answer_authorization_mode"], "AUTHORIZED_BOUNDED")
        self.assertTrue(generator.limitation and "AUTHORIZED_BOUNDED" in generator.limitation)
        self.assertEqual(terminal["answer_authorization"], decision)
        self.assertEqual(result.state.answer_context_audit["final_answer_authorization"], decision)

    def test_t29_all_valid_requirements_allow_full_mode(self):
        state = fixture_state()
        state.facts["choice_factor"] = "synthetic stated choice"
        state.fact_sources["choice_factor"] = {"source_type": "user_explicit"}
        state.fact_status["choice_factor"] = "ASSERTED"
        state.target_status["choice_factor"] = {"status": "ASSERTED"}
        self.assertEqual(authorize_final_answer(state, requirements())["answer_authorization_mode"], "AUTHORIZED_FULL")

    def test_t30_invalid_state_with_no_safe_basis_is_blocked(self):
        state = fixture_state(evidence=False, facts=False, missing_status="INVALID")
        state.fact_conflicts["choice_factor"] = [{"source": "synthetic conflict"}]
        state.dependencies_considered[0]["fallback"] = None
        auth = authorize_final_answer(state, requirements())
        self.assertEqual(auth["status"], "BLOCKED_UNSAFE_OR_INVALID")


if __name__ == "__main__":
    unittest.main()
