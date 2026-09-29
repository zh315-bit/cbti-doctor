"""Synthetic runtime wiring/trace audit; no benchmark or external model."""
from __future__ import annotations
import unittest

from adaptive_agent.runner import AdaptiveAgentLoop
from adaptive_agent.input_understanding import Understanding
from adaptive_agent.state import AdaptiveAgentState, TaskType
from adaptive_agent.tools import DiaryResult, RetrievalResult


class StaticUnderstander:
    def __init__(self, goal, task): self.goal, self.task = goal, task
    def understand(self, _message, _state): return Understanding(self.goal, self.task, {})


class Retrieval:
    def retrieve(self, _query): return RetrievalResult(("synthetic evidence",), detail="synthetic")


class Diary:
    def __init__(self, result): self.result = result; self.calls = 0
    def read(self, _requirements): self.calls += 1; return self.result


class IntegrationTraceAuditTests(unittest.TestCase):
    def loop(self, goal, task, diary):
        return AdaptiveAgentLoop(StaticUnderstander(goal, task), Retrieval(), diary, max_steps=4)

    def dependency_types(self, result, event):
        return [x["dependency_type"] for x in next(x for x in result.state_history if x["event"] == event)["dependencies_considered"]]

    def test_wrong_task_knowledge_goal_wires_evidence_to_retrieve_and_satisfied(self):
        result = self.loop("解释刺激控制的一般原则", TaskType.PERSONALIZED_DECISION, Diary(DiaryResult({}, False))).run_turn("synthetic")
        self.assertEqual(result.transitions[0].action, "RETRIEVE")
        self.assertIn("EVIDENCE", self.dependency_types(result, "DECISION"))
        retrieve = next(x for x in result.state_history if x["event"] == "RETRIEVE")
        self.assertEqual(retrieve["dependencies_satisfied"][0]["dependency_type"], "EVIDENCE")

    def test_wrong_task_diary_goal_wires_resource_to_read_and_satisfied(self):
        diary = Diary(DiaryResult({"recent_sleep_pattern": [{"date": "2026-01-01"}]}, True,
                                  source_entry_count=1, source_dates=("2026-01-01",),
                                  date_coverage=("2026-01-01",), provenance={"source": "audit"}))
        result = self.loop("分析过去两周的睡眠日记变化", TaskType.PERSONALIZED_DECISION, diary).run_turn("synthetic")
        self.assertEqual(result.transitions[0].action, "READ_DIARY")
        read = next(x for x in result.state_history if x["event"] == "READ_DIARY")
        self.assertEqual(read["dependencies_satisfied"][0]["dependency_type"], "RESOURCE")
        self.assertEqual(read["diary_projection"]["projection_status"], "valid")

    def test_unavailable_resource_is_bounded_without_tool_call(self):
        diary = Diary(DiaryResult({}, False, kind="UNAVAILABLE"))
        state = AdaptiveAgentState(diary_available=False)
        result = self.loop("分析睡眠日记变化", TaskType.PERSONALIZED_DECISION, diary).run_turn("synthetic", state)
        self.assertEqual(result.status, "ANSWER")
        self.assertEqual(diary.calls, 0)
        self.assertEqual(result.state.dependencies_unavailable[0]["dependency_type"], "RESOURCE")

    def test_general_knowledge_has_no_diary_dependency_and_existing_evidence_no_repeat(self):
        state = AdaptiveAgentState(evidence=["already grounded"])
        result = self.loop("什么是刺激控制？", TaskType.KNOWLEDGE_QA, Diary(DiaryResult({}, False))).run_turn("synthetic", state)
        self.assertNotIn("RESOURCE", result.state.dependencies_considered and [x["dependency_type"] for x in result.state.dependencies_considered])
        self.assertFalse(any(x.action == "RETRIEVE" for x in result.transitions))

    def test_invalid_summary_never_enters_state_or_answer_context(self):
        diary = Diary(DiaryResult({"recent_sleep_pattern": ["14 entries summary"]}, True,
                                  kind="SUMMARY_SHAPED", summary_semantics="aggregate"))
        result = self.loop("分析睡眠日记趋势", TaskType.DATA_ANALYSIS, diary).run_turn("synthetic")
        self.assertEqual(result.state.diary_projection["projection_status"], "invalid")
        self.assertNotIn("recent_sleep_pattern", result.state.facts)
        self.assertEqual(result.status, "ANSWER")

    def test_trace_has_action_causal_fields(self):
        result = self.loop("解释刺激控制的一般原则", TaskType.PERSONALIZED_DECISION, Diary(DiaryResult({}, False))).run_turn("synthetic")
        decision = next(x for x in result.state_history if x["event"] == "DECISION")
        self.assertTrue(decision["dependencies_considered"])
        self.assertTrue(decision["preconditions_considered"])
        self.assertIn("dependency_source", decision["preconditions_considered"][0])
        self.assertIn("selected_satisfier", decision["preconditions_considered"][0])


if __name__ == "__main__": unittest.main()
