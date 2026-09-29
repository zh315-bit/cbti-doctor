"""Step 9.16 synthetic dependency-formation tests; no Benchmark inputs."""
import unittest

from adaptive_agent.candidates import build_candidates
from adaptive_agent.dependency_resolver import DependencyResolver
from adaptive_agent.policy import HeuristicDecisionPolicy
from adaptive_agent.requirements import RequirementSet, synchronize_requirements
from adaptive_agent.state import AdaptiveAgentState, TaskType
from adaptive_agent.sufficiency import SufficiencyEstimator


def decide(state: AdaptiveAgentState, requirements: RequirementSet):
    SufficiencyEstimator().update(state, requirements)
    dependencies = DependencyResolver().resolve(state, requirements)
    state.dependencies_considered = [item.to_dict() for item in dependencies]
    requirements = synchronize_requirements(requirements, state, dependencies)
    SufficiencyEstimator().update(state, requirements)
    state.candidate_actions = build_candidates(state, requirements)
    return HeuristicDecisionPolicy().choose(state)


class DependencyFormationTests(unittest.TestCase):
    def test_external_evidence_only_goal(self):
        state = AdaptiveAgentState(goal="解释刺激控制的一般原则", task_type=TaskType.KNOWLEDGE_QA)
        action = decide(state, RequirementSet((), (), False))
        self.assertEqual(action.action, "RETRIEVE")
        self.assertEqual(state.dependencies_considered[0]["dependency_class"], "EXTERNAL_EVIDENCE")
        self.assertEqual(state.dependencies_considered[0]["dependency_type"], "EVIDENCE")
        self.assertFalse(any(d["dependency_class"] == "DIARY_DATA" for d in state.dependencies_considered))

    def test_user_facts_only_goal(self):
        state = AdaptiveAgentState(goal="根据我的作息判断是否需要调整", task_type=TaskType.PERSONALIZED_DECISION)
        req = RequirementSet(("bedtime", "wake_time"), (), False)
        action = decide(state, req)
        self.assertEqual(action.action, "ASK")
        dep = next(d for d in state.dependencies_considered if d["dependency_class"] == "USER_FACTS")
        self.assertEqual(dep["requiredness"], "optional")
        self.assertEqual(action.source_dependency_id, dep["dependency_id"])

    def test_diary_data_only_goal(self):
        state = AdaptiveAgentState(goal="分析过去两周的睡眠日记趋势", task_type=TaskType.DATA_ANALYSIS,
                                   diary_authorized=True, diary_available=True)
        action = decide(state, RequirementSet((), (), False, resources=("sleep_diary",)))
        self.assertEqual(action.action, "READ_DIARY")
        dep = next(d for d in state.dependencies_considered if d["dependency_class"] == "DIARY_DATA")
        self.assertEqual(action.source_dependency_id, dep["dependency_id"])

    def test_user_facts_and_evidence_goal(self):
        state = AdaptiveAgentState(goal="判断我的作息是否符合 CBT-I 原则", task_type=TaskType.PERSONALIZED_DECISION)
        action = decide(state, RequirementSet(("bedtime",), (), True))
        classes = {d["dependency_class"] for d in state.dependencies_considered}
        self.assertEqual(classes, {"USER_FACTS", "EXTERNAL_EVIDENCE"})
        self.assertEqual(action.action, "RETRIEVE")
        self.assertEqual(action.source_dependency_id,
                         next(d["dependency_id"] for d in state.dependencies_considered if d["dependency_class"] == "EXTERNAL_EVIDENCE"))

    def test_diary_and_evidence_goal(self):
        state = AdaptiveAgentState(goal="比较睡眠日记并解释为什么周末更差", task_type=TaskType.DATA_ANALYSIS,
                                   diary_authorized=True, diary_available=True)
        action = decide(state, RequirementSet((), (), False, resources=("sleep_diary",)))
        classes = {d["dependency_class"] for d in state.dependencies_considered}
        self.assertEqual(classes, {"DIARY_DATA", "EXTERNAL_EVIDENCE"})
        self.assertEqual(action.action, "READ_DIARY")

    def test_optional_user_facts_do_not_block_evidence(self):
        state = AdaptiveAgentState(goal="半夜醒了，我应该继续躺着还是先起来", task_type=TaskType.PERSONALIZED_DECISION)
        req = RequirementSet(("bedtime", "wake_time"), (), True)
        action = decide(state, req)
        self.assertEqual(action.action, "RETRIEVE")
        self.assertTrue(any(d["dependency_class"] == "EXTERNAL_EVIDENCE" for d in state.dependencies_considered))

    def test_available_diary_is_not_converted_to_ask(self):
        state = AdaptiveAgentState(goal="比较我的睡眠日记中工作日和周末", task_type=TaskType.DATA_ANALYSIS,
                                   diary_authorized=True, diary_available=True)
        action = decide(state, RequirementSet(("bedtime", "wake_time"), (), False, resources=("sleep_diary",)))
        self.assertEqual(action.action, "READ_DIARY")
        self.assertFalse(any(c.action == "ASK" for c in state.candidate_actions))

    def test_unknown_dependency_fails_safely(self):
        state = AdaptiveAgentState(goal="请处理这个睡眠问题", task_type=None)
        self.assertEqual(DependencyResolver().resolve(state, RequirementSet((), (), False)), [])
        self.assertEqual(decide(state, RequirementSet((), (), False)).action, "ANSWER")
        self.assertFalse(any(c.source_dependency_id for c in state.candidate_actions))


if __name__ == "__main__":
    unittest.main()
