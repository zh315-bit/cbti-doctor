import unittest

from adaptive_agent.candidates import build_candidates
from adaptive_agent.dependency_resolver import DependencyResolver
from adaptive_agent.information_value import acquisition_threshold_met, estimate_information_value
from adaptive_agent.policy import HeuristicDecisionPolicy
from adaptive_agent.requirements import RequirementSet, load_requirements, synchronize_requirements
from adaptive_agent.state import AdaptiveAgentState, TaskType
from adaptive_agent.sufficiency import SufficiencyEstimator


class InformationValueTests(unittest.TestCase):
    def prepare(self, state, req=None):
        req = req or load_requirements()[state.task_type]
        SufficiencyEstimator().update(state, req)
        dependencies = DependencyResolver().resolve(state, req)
        state.dependencies_considered = [item.to_dict() for item in dependencies]
        req = synchronize_requirements(req, state, dependencies)
        SufficiencyEstimator().update(state, req)
        state.candidate_actions = build_candidates(state, req)
        return req

    def test_decision_changing_missing_is_high_and_asks(self):
        state = AdaptiveAgentState(goal="咖啡摄入会改变我是否应该调整睡前安排吗", task_type=TaskType.PERSONALIZED_DECISION)
        req = self.prepare(state)
        estimate = estimate_information_value(state, "caffeine", req)
        self.assertEqual(estimate.value_level, "HIGH")
        self.assertEqual(HeuristicDecisionPolicy().choose(state).action, "ASK")

    def test_irrelevant_missing_is_none_and_not_ask(self):
        req = RequirementSet((), ("caffeine",), False, decision_fields=())
        state = AdaptiveAgentState(goal="解释刺激控制", task_type=TaskType.KNOWLEDGE_QA)
        self.prepare(state, req)
        estimate = estimate_information_value(state, "caffeine", req)
        self.assertEqual(estimate.value_level, "NONE")
        self.assertFalse(any(item.action == "ASK" for item in state.candidate_actions))

    def test_approximate_fact_is_known_and_not_refined(self):
        state = AdaptiveAgentState(goal="是否应该早点上床", task_type=TaskType.PERSONALIZED_DECISION,
                                   facts={"bedtime": "23:00", "sleep_onset_latency": {"uncertainty": "approximate", "value": 60}, "wake_time": "07:00"})
        req = self.prepare(state)
        estimate = estimate_information_value(state, "sleep_onset_latency", req)
        self.assertEqual(estimate.value_level, "NONE")
        self.assertNotIn("sleep_onset_latency", [x.target for x in state.candidate_actions if x.action == "ASK"])

    def test_diary_resource_is_recorded_as_alternative(self):
        req = RequirementSet(("wake_time",), (), False, resources=("sleep_diary",))
        state = AdaptiveAgentState(goal="读取日记", task_type=TaskType.DATA_ANALYSIS, available_diary=True)
        self.prepare(state, req)
        self.assertEqual(HeuristicDecisionPolicy().choose(state).action, "READ_DIARY")
        self.assertTrue(any(x.get("candidate_action") == "READ_DIARY" for x in state.considered_information))

    def test_later_ask_requires_high_value(self):
        state = AdaptiveAgentState(goal="比较最近睡眠规律", task_type=TaskType.PERSONALIZED_DECISION,
                                   action_history=[{"action": "ASK", "target": "caffeine"}, {"action": "ASK", "target": "nap"}],
                                   decision_relevant_missing=["recent_sleep_pattern"])
        req = RequirementSet(("recent_sleep_pattern",), (), False)
        SufficiencyEstimator().update(state, req)
        dependencies = DependencyResolver().resolve(state, req)
        state.dependencies_considered = [item.to_dict() for item in dependencies]
        req = synchronize_requirements(req, state, dependencies)
        SufficiencyEstimator().update(state, req)
        estimate = estimate_information_value(state, "recent_sleep_pattern", req)
        allowed, reason = acquisition_threshold_met(estimate, 2)
        self.assertFalse(allowed)
        self.assertEqual(reason, "value_below_threshold_high")

    def test_rejected_candidates_are_observable_and_stop_reason_is_set(self):
        req = RequirementSet((), ("caffeine",), False, decision_fields=("caffeine",))
        state = AdaptiveAgentState(goal="比较作息", task_type=TaskType.PERSONALIZED_DECISION,
                                   action_history=[{"action": "ASK", "target": "nap"}, {"action": "ASK", "target": "exercise"}])
        self.prepare(state, req)
        self.assertTrue(state.rejected_information)
        self.assertEqual(state.rejected_information[0]["accepted"], False)
        self.assertTrue(state.stop_reason)
        self.assertEqual(HeuristicDecisionPolicy().choose(state).action, "ANSWER")

    def test_genuine_high_value_survives_diminishing_return(self):
        state = AdaptiveAgentState(goal="判断是否调整起床时间", task_type=TaskType.PERSONALIZED_DECISION,
                                   action_history=[{"action": "ASK", "target": "caffeine"}, {"action": "ASK", "target": "nap"}],
                                   decision_relevant_missing=["wake_time"])
        req = RequirementSet(("wake_time",), (), False)
        SufficiencyEstimator().update(state, req)
        dependencies = DependencyResolver().resolve(state, req)
        state.dependencies_considered = [item.to_dict() for item in dependencies]
        req = synchronize_requirements(req, state, dependencies)
        SufficiencyEstimator().update(state, req)
        estimate = estimate_information_value(state, "wake_time", req)
        allowed, _ = acquisition_threshold_met(estimate, 2)
        self.assertTrue(allowed)


if __name__ == "__main__":
    unittest.main()
