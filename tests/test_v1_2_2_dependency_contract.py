"""Mechanism tests for V1.2.2 dependencies and diary contract; no benchmark."""
import unittest

from adaptive_agent.candidates import build_candidates
from adaptive_agent.dependency_resolver import DependencyResolver, DependencyStatus, DependencyType
from adaptive_agent.policy import HeuristicDecisionPolicy
from adaptive_agent.requirements import RequirementSet
from adaptive_agent.state import AdaptiveAgentState, TaskType
from adaptive_agent.state_update import apply_diary_result
from adaptive_agent.sufficiency import SufficiencyEstimator
from adaptive_agent.tools import DiaryResult


class DependencyContractTests(unittest.TestCase):
    def decide(self, state, req):
        SufficiencyEstimator().update(state, req)
        state.candidate_actions = build_candidates(state, req)
        return HeuristicDecisionPolicy().choose(state)

    def test_goal_semantics_forms_evidence_despite_wrong_task_signal(self):
        state = AdaptiveAgentState(goal="解释刺激控制的一般原则", task_type=TaskType.PERSONALIZED_DECISION)
        action = self.decide(state, RequirementSet((), (), False))
        self.assertEqual(action.action, "RETRIEVE")
        self.assertEqual(state.dependencies_required[0]["dependency_type"], "EVIDENCE")

    def test_goal_semantics_forms_diary_resource_despite_wrong_task_signal(self):
        state = AdaptiveAgentState(goal="分析过去两周的睡眠日记变化", task_type=TaskType.PERSONALIZED_DECISION,
                                   diary_authorized=True, diary_available=True)
        self.assertEqual(self.decide(state, RequirementSet((), (), False)).action, "READ_DIARY")
        self.assertEqual(state.dependencies_required[0]["dependency_type"], "RESOURCE")

    def test_optional_knowledge_evidence_and_ordinary_knowledge_no_diary(self):
        state = AdaptiveAgentState(goal="比较我的作息", task_type=TaskType.PERSONALIZED_DECISION)
        self.assertEqual(self.decide(state, RequirementSet((), (), False)).action, "ANSWER")
        self.assertFalse(any(x["dependency_type"] == "EVIDENCE" for x in state.dependencies_considered))
        knowledge = AdaptiveAgentState(goal="什么是刺激控制？", task_type=TaskType.KNOWLEDGE_QA)
        self.decide(knowledge, RequirementSet((), (), False))
        self.assertFalse(any(x["dependency_type"] == "RESOURCE" for x in knowledge.dependencies_considered))

    def test_required_dependencies_survive_cost_diminishing_and_stop(self):
        state = AdaptiveAgentState(goal="解释 CBT-I 原则", task_type=TaskType.KNOWLEDGE_QA,
                                   action_history=[{"action": "ASK"}] * 5)
        self.assertEqual(self.decide(state, RequirementSet((), (), False)).action, "RETRIEVE")
        diary = AdaptiveAgentState(goal="分析睡眠日记趋势", task_type=TaskType.PERSONALIZED_DECISION,
                                   diary_authorized=True, diary_available=True, action_history=[{"action": "ASK"}] * 5)
        self.assertEqual(self.decide(diary, RequirementSet((), (), False)).action, "READ_DIARY")

    def test_validity_state_is_goal_dependent_and_uses_ask(self):
        state = AdaptiveAgentState(goal="我该提前还是推迟上床时间", task_type=TaskType.PERSONALIZED_DECISION)
        self.assertEqual(self.decide(state, RequirementSet(("wake_time",), (), False)).action, "ASK")
        self.assertIn("VALIDITY_STATE", [x["dependency_type"] for x in state.dependencies_required])
        educational = AdaptiveAgentState(goal="规律起床时间为什么重要", task_type=TaskType.KNOWLEDGE_QA)
        self.decide(educational, RequirementSet(("wake_time",), (), False))
        self.assertFalse(any(x["dependency_type"] == "VALIDITY_STATE" for x in educational.dependencies_considered))

    def projection(self, result):
        state = AdaptiveAgentState(action_history=[{"action": "READ_DIARY"}])
        apply_diary_result(state, result)
        return state

    def test_entry_and_complete_summary_contracts_are_valid(self):
        entry = self.projection(DiaryResult({"recent_sleep_pattern": [{"date": "2026-01-01"}]}, True,
                                             source_entry_count=1, source_dates=("2026-01-01",), date_coverage=("2026-01-01",), provenance={"source": "test"}))
        self.assertEqual(entry.diary_projection["projection_status"], "valid")
        summary = self.projection(DiaryResult({"recent_sleep_pattern": ["7-day average"]}, True,
                                               kind="SUMMARY_SHAPED", source_entry_count=7,
                                               date_coverage=("2026-01-01", "2026-01-07"), provenance={"source": "test"}, summary_semantics="seven_day_aggregate"))
        self.assertEqual(summary.diary_projection["projection_status"], "valid")

    def test_summary_missing_contract_fields_and_entry_mismatch_fail_closed(self):
        for result in (
            DiaryResult({"recent_sleep_pattern": ["summary"]}, True, kind="SUMMARY_SHAPED", date_coverage=("2026-01-01",), provenance={"source": "test"}, summary_semantics="aggregate"),
            DiaryResult({"recent_sleep_pattern": ["summary"]}, True, kind="SUMMARY_SHAPED", source_entry_count=2, provenance={"source": "test"}, summary_semantics="aggregate"),
            DiaryResult({"recent_sleep_pattern": ["summary"]}, True, kind="SUMMARY_SHAPED", source_entry_count=2, date_coverage=("2026-01-01",), summary_semantics="aggregate"),
            DiaryResult({"recent_sleep_pattern": [{"date": "2026-01-01"}]}, True, source_entry_count=2, source_dates=("2026-01-01",), date_coverage=("2026-01-01",), provenance={"source": "test"}),
        ):
            state = self.projection(result)
            self.assertEqual(state.diary_projection["projection_status"], "invalid")
            self.assertEqual(state.facts, {})

    def test_unavailable_is_not_projected(self):
        state = self.projection(DiaryResult({}, False, kind="UNAVAILABLE"))
        self.assertEqual(state.diary_projection["projection_status"], "unavailable")
        self.assertEqual(state.resource_status["sleep_diary"], "unavailable")


if __name__ == "__main__":
    unittest.main()
