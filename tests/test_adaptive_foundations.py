import unittest

from adaptive_agent.requirements import calculate_missing, load_requirements, synchronize_requirements
from adaptive_agent.candidates import build_candidates
from adaptive_agent.dependency_resolver import DependencyResolver
from adaptive_agent.policy import HeuristicDecisionPolicy
from adaptive_agent.state import AdaptiveAgentState, TaskType
from adaptive_agent.sufficiency import SufficiencyEstimator


def make_personalized_state(**facts):
    return AdaptiveAgentState(
        goal="判断我是否应该更早上床",
        task_type=TaskType.PERSONALIZED_DECISION,
        facts=facts,
    )


class AdaptiveFoundationTests(unittest.TestCase):
    def test_secondary_gaps_do_not_lower_sufficient_personalized_goal(self):
        requirements = load_requirements()[TaskType.PERSONALIZED_DECISION]
        state = make_personalized_state(
            bedtime="23:00", sleep_onset_latency=60, wake_time="07:00",
            total_sleep_time=420, nighttime_awakenings=1, recent_sleep_pattern="持续两周",
        )

        SufficiencyEstimator().update(state, requirements)

        self.assertEqual(state.secondary_missing, ["perceived_stress", "nap", "caffeine"])
        self.assertEqual(state.user_info_sufficiency, "HIGH")

    def test_missing_calculation_keeps_zero_as_known_fact(self):
        requirements = load_requirements()[TaskType.PERSONALIZED_DECISION]
        critical, _ = calculate_missing(requirements, {
            "bedtime": "23:00", "sleep_onset_latency": 0, "wake_time": "07:00",
            "total_sleep_time": 420, "nighttime_awakenings": 0,
            "recent_sleep_pattern": "稳定",
        })
        self.assertEqual(critical, [])

    def test_knowledge_goal_needs_evidence_not_personal_sleep_facts(self):
        requirements = load_requirements()[TaskType.KNOWLEDGE_QA]
        state = AdaptiveAgentState(goal="什么是刺激控制？", task_type=TaskType.KNOWLEDGE_QA)

        SufficiencyEstimator().update(state, requirements)

        self.assertEqual(state.user_info_sufficiency, "HIGH")
        self.assertEqual(state.evidence_sufficiency, "LOW")

    def test_question_is_ranked_by_goal_value_not_requirement_order(self):
        requirements = load_requirements()[TaskType.PERSONALIZED_DECISION]
        state = make_personalized_state(
            bedtime="23:00", sleep_onset_latency=30, wake_time="07:00",
            total_sleep_time=420,
        )
        # YAML orders nighttime awakenings before recent pattern. This goal makes
        # the pattern question more valuable, so it should be selected first.
        state.goal = "我想了解最近一周的睡眠趋势是否有问题"
        SufficiencyEstimator().update(state, requirements)
        dependencies = DependencyResolver().resolve(state, requirements)
        state.dependencies_considered = [item.to_dict() for item in dependencies]
        requirements = synchronize_requirements(requirements, state, dependencies)
        SufficiencyEstimator().update(state, requirements)
        state.candidate_actions = build_candidates(state, requirements)

        selected = HeuristicDecisionPolicy().choose(state)

        self.assertEqual(selected.action, "ASK")
        self.assertEqual(selected.target, "recent_sleep_pattern")

    def test_policy_answers_when_only_secondary_information_is_missing(self):
        requirements = load_requirements()[TaskType.PERSONALIZED_DECISION]
        state = make_personalized_state(
            bedtime="23:00", sleep_onset_latency=60, wake_time="07:00",
            total_sleep_time=420, nighttime_awakenings=1, recent_sleep_pattern="持续两周",
        )
        state.evidence.append("已检索到与目标相关的 CBT-I 证据")
        SufficiencyEstimator().update(state, requirements)
        dependencies = DependencyResolver().resolve(state, requirements)
        state.dependencies_considered = [item.to_dict() for item in dependencies]
        requirements = synchronize_requirements(requirements, state, dependencies)
        SufficiencyEstimator().update(state, requirements)
        state.candidate_actions = build_candidates(state, requirements)

        self.assertEqual(HeuristicDecisionPolicy().choose(state).action, "ANSWER")


if __name__ == "__main__":
    unittest.main()
