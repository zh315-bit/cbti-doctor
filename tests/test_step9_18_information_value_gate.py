"""Synthetic counterfactual validation for the V1.2.3 acquisition gate."""
import unittest

from adaptive_agent.acquisition_gate import gate_acquisition_candidates
from adaptive_agent.candidates import generate_candidates
from adaptive_agent.dependency_resolver import DependencyResolver
from adaptive_agent.information_value import estimate_information_value
from adaptive_agent.requirements import RequirementSet, synchronize_requirements
from adaptive_agent.state import ActionCandidate, AdaptiveAgentState, TaskType
from adaptive_agent.sufficiency import SufficiencyEstimator


class InformationValueGateTests(unittest.TestCase):
    def prepare(self, state, req):
        SufficiencyEstimator().update(state, req)
        dependencies = DependencyResolver().resolve(state, req)
        state.dependencies_considered = [item.to_dict() for item in dependencies]
        req = synchronize_requirements(req, state, dependencies)
        SufficiencyEstimator().update(state, req)
        raw = generate_candidates(state, req)
        state.candidate_actions = gate_acquisition_candidates(state, req, raw)
        return state.candidate_actions

    def test_critical_decision_missing_fact_survives_as_ask(self):
        req = RequirementSet((), (), False, decision_fields=("caffeine",))
        state = AdaptiveAgentState(goal="咖啡影响下我该怎么调整睡前作息", task_type=TaskType.PERSONALIZED_DECISION)
        actions = self.prepare(state, req)
        self.assertEqual(actions[0].action, "ASK")
        self.assertEqual(actions[0].target, "caffeine")
        self.assertEqual(actions[0].gate_decision, "ACCEPT")

    def test_secondary_missing_with_sufficient_answer_does_not_ask(self):
        req = RequirementSet((), ("caffeine",), False)
        state = AdaptiveAgentState(goal="概括我提供的作息情况", task_type=TaskType.PERSONALIZED_DECISION)
        actions = self.prepare(state, req)
        self.assertEqual([item.action for item in actions], ["ANSWER"])
        self.assertEqual(state.user_info_sufficiency, "HIGH")

    def test_exact_known_fact_does_not_duplicate_ask(self):
        req = RequirementSet((), (), False, decision_fields=("caffeine",))
        state = AdaptiveAgentState(goal="咖啡影响下怎么调整", task_type=TaskType.PERSONALIZED_DECISION,
                                   facts={"caffeine": False})
        self.assertNotIn("ASK", [item.action for item in self.prepare(state, req)])

    def test_semantically_equivalent_sleep_time_satisfies_latency_target(self):
        req = RequirementSet((), (), False, decision_fields=("sleep_time_or_sleep_onset_latency",))
        state = AdaptiveAgentState(goal="睡着时间影响睡前调整", task_type=TaskType.PERSONALIZED_DECISION,
                                   facts={"sleep_time": "23:40"})
        self.assertNotIn("ASK", [item.action for item in self.prepare(state, req)])

    def test_goal_unrelated_missing_field_does_not_ask(self):
        req = RequirementSet((), ("caffeine",), False, decision_fields=())
        state = AdaptiveAgentState(goal="解释睡眠日记的用途", task_type=TaskType.KNOWLEDGE_QA)
        self.assertNotIn("ASK", [item.action for item in self.prepare(state, req)])

    def test_unresolved_evidence_dependency_forces_retrieve(self):
        req = RequirementSet((), (), True)
        state = AdaptiveAgentState(goal="什么是刺激控制？", task_type=TaskType.KNOWLEDGE_QA)
        action = self.prepare(state, req)[0]
        self.assertEqual(action.action, "RETRIEVE")
        self.assertEqual(action.origin, "HARD_PRECONDITION")
        self.assertEqual(action.gate_decision, "ACCEPT")
        self.assertIn("mandatory_dependency", action.gate_reason)

    def test_no_evidence_dependency_means_no_retrieve(self):
        req = RequirementSet((), (), False)
        state = AdaptiveAgentState(goal="用已知信息做简短描述", task_type=TaskType.PERSONALIZED_DECISION,
                                   user_info_sufficiency="HIGH", evidence_sufficiency="LOW")
        actions = self.prepare(state, req)
        self.assertNotIn("RETRIEVE", [item.action for item in actions])

    def test_required_diary_dependency_forces_read(self):
        req = RequirementSet((), (), False, resources=("sleep_diary",))
        state = AdaptiveAgentState(goal="分析最近的睡眠日记", task_type=TaskType.DATA_ANALYSIS,
                                   available_diary=True, diary_authorized=True, diary_available=True)
        action = self.prepare(state, req)[0]
        self.assertEqual(action.action, "READ_DIARY")
        self.assertEqual(action.origin, "HARD_PRECONDITION")

    def test_optional_diary_without_dependency_is_rejected(self):
        req = RequirementSet((), (), False, decision_fields=("caffeine",))
        state = AdaptiveAgentState(goal="咖啡影响下我该如何调整", task_type=TaskType.PERSONALIZED_DECISION,
                                   available_diary=True)
        actions = self.prepare(state, req)
        self.assertNotIn("READ_DIARY", [item.action for item in actions])
        rejected = next(item for item in state.acquisition_decisions if item["action"] == "READ_DIARY")
        self.assertEqual(rejected["reason"], "no_active_diary_dependency")

    def test_loaded_diary_does_not_repeat_tool_call(self):
        req = RequirementSet((), (), False, resources=("sleep_diary",))
        state = AdaptiveAgentState(goal="分析睡眠日记", task_type=TaskType.DATA_ANALYSIS,
                                   resource_status={"sleep_diary": "loaded"})
        actions = self.prepare(state, req)
        self.assertNotIn("READ_DIARY", [item.action for item in actions])

    def test_low_value_high_interaction_cost_optional_ask_is_rejected(self):
        req = RequirementSet((), ("caffeine",), False)
        state = AdaptiveAgentState(goal="回答作息问题", task_type=TaskType.PERSONALIZED_DECISION,
                                   action_history=[{"action": "ASK", "target": "nap"}] * 3)
        optional_ask = ActionCandidate("ASK", target="caffeine", question="咖啡？",
                                       expected_benefit="LOW", cost="HIGH")
        actions = gate_acquisition_candidates(state, req, [optional_ask])
        self.assertEqual(actions[0].action, "ANSWER")
        self.assertEqual(state.acquisition_decisions[0]["gate_decision"], "REJECT")

    def test_answer_scope_changing_information_can_be_acquired(self):
        req = RequirementSet((), (), False, decision_fields=("caffeine",))
        state = AdaptiveAgentState(goal="咖啡是否影响我的睡眠安排", task_type=TaskType.PERSONALIZED_DECISION)
        action = self.prepare(state, req)[0]
        self.assertEqual(action.action, "ASK")
        self.assertEqual(action.expected_information_gain, "MEDIUM")

    def test_validity_critical_personalized_fact_cannot_be_suppressed(self):
        req = RequirementSet((), (), False, decision_fields=("wake_time",))
        state = AdaptiveAgentState(goal="判断是否应提前上床", task_type=TaskType.PERSONALIZED_DECISION,
                                   facts={"bedtime": "23:00", "sleep_onset_latency": 60})
        action = self.prepare(state, req)[0]
        self.assertEqual((action.action, action.target), ("ASK", "wake_time"))
        self.assertEqual(action.origin, "OPTIONAL_ACQUISITION")
        self.assertEqual(action.gate_decision, "ACCEPT")
        self.assertIn("plausible values can change the direction", action.gate_reason)

    def test_evidence_dependency_for_quantitative_medical_claim_is_not_suppressed(self):
        req = RequirementSet((), (), True)
        state = AdaptiveAgentState(goal="CBT-I睡眠效率的临床量化阈值是什么？", task_type=TaskType.KNOWLEDGE_QA)
        action = self.prepare(state, req)[0]
        self.assertEqual(action.action, "RETRIEVE")
        self.assertEqual(action.origin, "HARD_PRECONDITION")

    def test_unavailable_diary_is_not_retried(self):
        req = RequirementSet((), (), False, resources=("sleep_diary",))
        state = AdaptiveAgentState(goal="分析睡眠日记", task_type=TaskType.DATA_ANALYSIS,
                                   resource_status={"sleep_diary": "unavailable"},
                                   diary_available=False, diary_authorized=True)
        actions = self.prepare(state, req)
        self.assertNotIn("READ_DIARY", [item.action for item in actions])

    def test_same_information_value_changes_with_goal_context(self):
        req = RequirementSet((), (), False, decision_fields=("caffeine",))
        relevant = AdaptiveAgentState(goal="咖啡因是否改变我的方案", task_type=TaskType.PERSONALIZED_DECISION)
        unrelated = AdaptiveAgentState(goal="确定一个通用睡眠时间概念", task_type=TaskType.PERSONALIZED_DECISION)
        self.prepare(relevant, req)
        relevant_dependencies = DependencyResolver().resolve(relevant, req)
        relevant_req = synchronize_requirements(req, relevant, relevant_dependencies)
        SufficiencyEstimator().update(relevant, relevant_req)
        unrelated_req = RequirementSet((), ("caffeine",), False, decision_fields=())
        self.prepare(unrelated, unrelated_req)
        unrelated_dependencies = DependencyResolver().resolve(unrelated, unrelated_req)
        unrelated_req = synchronize_requirements(unrelated_req, unrelated, unrelated_dependencies)
        SufficiencyEstimator().update(unrelated, unrelated_req)
        relevant_estimate = estimate_information_value(relevant, "caffeine", relevant_req)
        unrelated_estimate = estimate_information_value(unrelated, "caffeine", unrelated_req)
        self.assertNotEqual(relevant_estimate.value_level, unrelated_estimate.value_level)

    def test_trace_exposes_gate_components_and_non_calibration(self):
        req = RequirementSet((), (), False, decision_fields=("caffeine",))
        state = AdaptiveAgentState(goal="咖啡是否影响安排", task_type=TaskType.PERSONALIZED_DECISION)
        self.prepare(state, req)
        trace = state.acquisition_decisions[0]
        self.assertTrue({"expected_information_gain", "goal_relevance", "decision_impact",
                         "missing_criticality", "redundancy", "estimated_cost",
                         "acquisition_value", "gate_decision", "reason"}.issubset(trace))
        self.assertTrue(trace["heuristic_not_calibrated_probability"])
        self.assertFalse(any(isinstance(v, float) for v in trace.values()))


if __name__ == "__main__":
    unittest.main()
