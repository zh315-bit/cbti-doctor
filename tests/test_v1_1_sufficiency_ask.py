import unittest

from adaptive_agent.candidates import build_candidates
from adaptive_agent.dependency_resolver import DependencyResolver
from adaptive_agent.policy import HeuristicDecisionPolicy
from adaptive_agent.requirements import RequirementSet, load_requirements, synchronize_requirements
from adaptive_agent.state import AdaptiveAgentState, ActionCandidate, TaskType
from adaptive_agent.sufficiency import SufficiencyEstimator
from adaptive_agent.state_update import apply_diary_result
from adaptive_agent.tools import DiaryResult


class SufficiencyAskControlTests(unittest.TestCase):
    def decide(self, state, req=None):
        req = req or load_requirements()[state.task_type]
        SufficiencyEstimator().update(state, req)
        dependencies = DependencyResolver().resolve(state, req)
        state.dependencies_considered = [item.to_dict() for item in dependencies]
        req = synchronize_requirements(req, state, dependencies)
        SufficiencyEstimator().update(state, req)
        state.candidate_actions = build_candidates(state, req)
        return HeuristicDecisionPolicy().choose(state)

    def test_missing_categories_are_distinct(self):
        state = AdaptiveAgentState(goal="是否应该早点上床", task_type=TaskType.PERSONALIZED_DECISION,
                                   facts={"bedtime": "23:00"})
        self.decide(state)
        self.assertIn("wake_time", state.required_missing)
        self.assertIn("wake_time", state.decision_relevant_missing)
        self.assertIn("total_sleep_time", state.required_missing)
        self.assertNotIn("total_sleep_time", state.decision_relevant_missing)

    def test_approximate_and_range_are_available_for_bounded_directional_goal(self):
        state = AdaptiveAgentState(goal="是否应该早点上床", task_type=TaskType.PERSONALIZED_DECISION,
                                   facts={"bedtime": {"uncertainty": "approximate", "value": "00:00"},
                                          "sleep_onset_latency": {"uncertainty": "approximate", "value": 60},
                                          "wake_time": {"uncertainty": "range", "low": "07:00", "high": "08:00"}})
        selected = self.decide(state)
        self.assertEqual(selected.action, "RETRIEVE")
        self.assertEqual(state.decision_relevant_missing, [])

    def test_secondary_only_missing_allows_answer(self):
        state = AdaptiveAgentState(goal="是否应该早点上床", task_type=TaskType.PERSONALIZED_DECISION,
                                   facts={"bedtime": "23:00", "sleep_onset_latency": 60, "wake_time": "07:00"},
                                   evidence=["evidence"])
        self.assertEqual(self.decide(state).action, "ANSWER")
        self.assertEqual(state.decision_relevant_missing, [])

    def test_one_decision_relevant_fact_missing_still_asks(self):
        state = AdaptiveAgentState(goal="是否应该早点上床", task_type=TaskType.PERSONALIZED_DECISION,
                                   facts={"bedtime": "23:00", "sleep_onset_latency": 60})
        selected = self.decide(state)
        self.assertEqual((selected.action, selected.target), ("ASK", "wake_time"))

    def test_explicit_fact_and_equivalent_ask_are_blocked(self):
        state = AdaptiveAgentState(goal="是否应该早点上床", task_type=TaskType.PERSONALIZED_DECISION,
                                   facts={"bedtime": "23:00", "sleep_onset_latency": 60, "wake_time": "07:00"})
        self.assertEqual(self.decide(state).action, "RETRIEVE")
        state.action_history.append({"action": "ASK", "target": "sleep_time"})
        self.assertNotIn("sleep_onset_latency", [c.target for c in build_candidates(state, load_requirements()[state.task_type])])

    def test_resource_candidate_precedes_user_ask(self):
        req = RequirementSet(("wake_time",), (), False, resources=("sleep_diary",))
        state = AdaptiveAgentState(goal="读取日记中的起床时间", task_type=TaskType.DATA_ANALYSIS,
                                   available_diary=True)
        selected = self.decide(state, req)
        self.assertEqual(selected.action, "READ_DIARY")

    def test_unavailable_resource_does_not_retry(self):
        req = RequirementSet((), (), False, resources=("sleep_diary",))
        state = AdaptiveAgentState(goal="分析日记", task_type=TaskType.DATA_ANALYSIS,
                                   resource_status={"sleep_diary": "unavailable"})
        selected = self.decide(state, req)
        self.assertEqual(selected.action, "ANSWER")
        self.assertFalse(any(c.action == "READ_DIARY" for c in state.candidate_actions))

    def test_bounded_answer_stops_secondary_collection(self):
        req = RequirementSet(("bedtime", "wake_time"), ("caffeine",), True)
        state = AdaptiveAgentState(goal="比较作息", task_type=TaskType.PERSONALIZED_DECISION,
                                   facts={"bedtime": "23:00", "wake_time": "07:00"}, evidence=["evidence"])
        self.assertEqual(self.decide(state, req).action, "ANSWER")

    def test_genuinely_insufficient_state_does_not_answer_early(self):
        req = RequirementSet(("bedtime", "wake_time"), (), False)
        state = AdaptiveAgentState(goal="比较作息", task_type=TaskType.PERSONALIZED_DECISION,
                                   facts={"bedtime": "23:00"})
        self.assertEqual(self.decide(state, req).action, "ASK")


if __name__ == "__main__":
    unittest.main()
