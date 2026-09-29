"""Counterfactual, goal-conditioned tests for the Step 9.24 acquisition gate."""
import unittest

from adaptive_agent.acquisition_gate import gate_acquisition_candidates
from adaptive_agent.candidates import generate_candidates
from adaptive_agent.dependency_resolver import DependencyResolver
from adaptive_agent.information_value import estimate_information_value
from adaptive_agent.requirements import RequirementSet, synchronize_requirements
from adaptive_agent.state import ActionCandidate, AdaptiveAgentState, TaskType
from adaptive_agent.sufficiency import SufficiencyEstimator


class Step924InformationValueTests(unittest.TestCase):
    def setup_state(self, goal, *, fields=("caffeine",), facts=None, history=None,
                    task_type=TaskType.PERSONALIZED_DECISION, req=None):
        req = req or RequirementSet((), (), False, decision_fields=fields)
        state = AdaptiveAgentState(goal=goal, task_type=task_type, facts=facts or {},
                                   action_history=history or [])
        SufficiencyEstimator().update(state, req)
        dependencies = DependencyResolver().resolve(state, req)
        state.dependencies_considered = [item.to_dict() for item in dependencies]
        req = synchronize_requirements(req, state, dependencies)
        SufficiencyEstimator().update(state, req)
        raw = generate_candidates(state, req)
        state.candidate_actions = gate_acquisition_candidates(state, req, raw)
        return state, req

    def test_a_missing_irrelevant_fact_is_not_asked(self):
        req = RequirementSet((), ("caffeine",), False, decision_fields=())
        state, _ = self.setup_state("解释一个通用的睡眠概念", fields=(), req=req,
                                    task_type=TaskType.KNOWLEDGE_QA)
        estimate = estimate_information_value(state, "caffeine", req)
        self.assertEqual(estimate.value_level, "NONE")
        self.assertNotIn("ASK", [item.action for item in state.candidate_actions])

    def test_b_detail_only_candidate_is_rejected_by_counterfactual_gate(self):
        req = RequirementSet((), ("caffeine",), False, decision_fields=("caffeine",))
        state, req = self.setup_state("简要描述我已提供的睡眠情况", fields=("caffeine",), req=req)
        candidate = ActionCandidate("ASK", target="caffeine", question="咖啡？")
        actions = gate_acquisition_candidates(state, req, [candidate])
        self.assertEqual([item.action for item in actions], ["ANSWER"])
        self.assertEqual(state.acquisition_decisions[0]["decision_impact"], "LOW")
        self.assertIn("counterfactual_values_do_not_change", state.acquisition_decisions[0]["reason"])

    def test_c_comparison_scope_change_can_be_medium_and_asked(self):
        goal = "比较咖啡摄入与睡眠安排的关系"
        state, req = self.setup_state(goal)
        estimate = estimate_information_value(state, "caffeine", req)
        self.assertEqual(estimate.value_level, "MEDIUM")
        self.assertEqual(estimate.decision_impact, "answer_scope_changing")
        self.assertEqual(state.candidate_actions[0].action, "ASK")

    def test_d_explicit_decision_changing_fact_is_high(self):
        goal = "咖啡摄入会改变我应该怎样调整睡前安排吗？"
        state, req = self.setup_state(goal)
        estimate = estimate_information_value(state, "caffeine", req)
        self.assertEqual(estimate.value_level, "HIGH")
        self.assertEqual(estimate.decision_impact, "decision_changing")
        self.assertEqual(state.candidate_actions[0].action, "ASK")

    def test_e_approximate_fact_does_not_trigger_precision_ask(self):
        req = RequirementSet((), (), False, decision_fields=("caffeine",))
        state, _ = self.setup_state("咖啡摄入会改变我应该怎样调整睡前安排吗？", facts={
            "caffeine": {"value": "下午约一杯", "uncertainty": "approximate"}
        }, req=req)
        self.assertNotIn("ASK", [item.action for item in state.candidate_actions])

    def test_f_range_fact_does_not_trigger_exact_value_ask(self):
        req = RequirementSet((), (), False, decision_fields=("caffeine",))
        state, _ = self.setup_state("咖啡摄入会改变我应该怎样调整睡前安排吗？", facts={
            "caffeine": {"value": "每周约2到3次", "uncertainty": "range"}
        }, req=req)
        self.assertNotIn("ASK", [item.action for item in state.candidate_actions])

    def test_g_known_or_semantically_asked_information_is_not_reacquired(self):
        req = RequirementSet((), (), False, decision_fields=("caffeine",))
        state, _ = self.setup_state("咖啡摄入会改变我应该怎样调整睡前安排吗？",
                                    facts={"caffeine": "下午喝茶"}, req=req)
        self.assertNotIn("ASK", [item.action for item in state.candidate_actions])
        repeated, _ = self.setup_state("咖啡摄入会改变我应该怎样调整睡前安排吗？",
                                       history=[{"action": "ASK", "target": "caffeine"}], req=req)
        self.assertNotIn("ASK", [item.action for item in repeated.candidate_actions])

    def test_h_same_fact_has_different_value_under_different_goals(self):
        low_goal = "概括我目前提供的睡眠情况"
        high_goal = "咖啡摄入会改变我应该怎样调整睡前安排吗？"
        req = RequirementSet((), (), False, decision_fields=("caffeine",))
        low, low_req = self.setup_state(low_goal, req=req)
        high, high_req = self.setup_state(high_goal, req=req)
        self.assertLess({"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}[estimate_information_value(low, "caffeine", low_req).value_level],
                        {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}[estimate_information_value(high, "caffeine", high_req).value_level])

    def test_i_counterfactual_trace_explains_unchanged_action(self):
        req = RequirementSet((), (), False, decision_fields=("perceived_stress",))
        state, effective_req = self.setup_state("简要概括最近睡眠情况", fields=("perceived_stress",), req=req)
        estimate = estimate_information_value(state, "perceived_stress", effective_req)
        self.assertEqual(estimate.decision_impact, "detail_improving")
        record = next(item for item in state.rejected_information if item["action"] == "ASK")
        self.assertIn("next action remain unchanged", record["counterfactual_candidate"]["if_unknown"])

    def test_j_hard_precondition_survives_low_value_cost_and_diminishing_return(self):
        req = RequirementSet((), (), False, decision_fields=("caffeine",))
        state = AdaptiveAgentState(goal="一个与咖啡无关的通用问题", task_type=TaskType.PERSONALIZED_DECISION,
                                   action_history=[{"action": "ASK", "target": f"field_{i}"} for i in range(6)])
        hard = ActionCandidate("ASK", target="caffeine", expected_benefit="LOW", cost="HIGH",
                               origin="HARD_PRECONDITION", source_precondition_id="real-precondition")
        actions = gate_acquisition_candidates(state, req, [hard])
        self.assertEqual(actions[0].action, "ASK")
        self.assertEqual(actions[0].gate_decision, "ACCEPT")
        self.assertIn("cannot_be_overridden", actions[0].gate_reason)

    def test_estimate_exposes_ordinal_counterfactual_not_probability(self):
        state, req = self.setup_state("咖啡摄入会改变我应该怎样调整睡前安排吗？")
        estimate = estimate_information_value(state, "caffeine", req)
        self.assertTrue(estimate.lineage_complete)
        self.assertTrue(estimate.dependency_id)
        self.assertEqual(len(estimate.counterfactual_outcomes), 2)
        self.assertFalse(any(isinstance(value, float) for value in estimate.to_dict().values()))


if __name__ == "__main__":
    unittest.main()
