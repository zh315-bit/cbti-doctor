import unittest

from adaptive_agent.input_understanding import LLMInputUnderstander, Understanding, understanding_from_mapping
from adaptive_agent.runner import AdaptiveAgentLoop
from adaptive_agent.state import ActionCandidate, AdaptiveAgentState, TaskType
from adaptive_agent.tools import DiaryResult, RetrievalResult


class StaticUnderstander:
    def __init__(self, goal, task_type, facts=None):
        self.result = Understanding(goal, task_type, facts or {})

    def understand(self, user_input, prior_state=None):
        return self.result


class FakeRetrievalTool:
    def __init__(self, result):
        self.result = result
        self.queries = []

    def retrieve(self, query):
        self.queries.append(query)
        return self.result


class FakeDiaryTool:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def read(self, requirements):
        self.calls += 1
        return self.result


class AlwaysRetrievePolicy:
    def choose(self, state):
        return ActionCandidate(action="RETRIEVE", query=state.goal, expected_benefit="HIGH", cost="LOW")


class StructuredModelSpy:
    def __init__(self):
        self.schema = None
        self.kwargs = None

    def with_structured_output(self, schema, **kwargs):
        self.schema = schema
        self.kwargs = kwargs
        return self


class AdaptiveLoopTests(unittest.TestCase):
    def test_llm_understander_uses_function_calling_for_configured_endpoint_compatibility(self):
        model = StructuredModelSpy()

        LLMInputUnderstander(model)

        self.assertEqual(model.kwargs, {"method": "function_calling"})

    def knowledge_loop(self, retrieval_result):
        retrieval = FakeRetrievalTool(retrieval_result)
        loop = AdaptiveAgentLoop(
            StaticUnderstander("解释刺激控制", TaskType.KNOWLEDGE_QA), retrieval,
            FakeDiaryTool(DiaryResult({}, False)), max_steps=4,
        )
        return loop.run_turn("什么是刺激控制？"), retrieval

    def test_retrieval_updates_evidence_then_re_evaluates_to_answer(self):
        result, retrieval = self.knowledge_loop(RetrievalResult(("CBT-I evidence",), detail="mock RAG"))

        self.assertEqual(result.status, "ANSWER")
        self.assertEqual([item.action for item in result.state.candidate_actions], ["ANSWER"])
        self.assertEqual(result.state.evidence, ["CBT-I evidence"])
        self.assertEqual([entry["action"] for entry in result.state.action_history], ["RETRIEVE", "ANSWER"])
        self.assertEqual(retrieval.queries, ["解释刺激控制"])

    def test_read_diary_updates_facts_and_recalculates_missing(self):
        diary_entries = [{"date": "2026-01-01", "bedtime": "23:00", "sleep_onset_latency": 60,
                          "wake_time": "07:00", "total_sleep_time": 420, "nighttime_awakenings": 1}]
        diary_facts = {"recent_sleep_pattern": diary_entries}
        loop = AdaptiveAgentLoop(
            StaticUnderstander("分析最近睡眠日记", TaskType.DATA_ANALYSIS),
            FakeRetrievalTool(RetrievalResult(("CBT-I evidence",))),
            FakeDiaryTool(DiaryResult(diary_facts, True, "session diary", source_entry_count=1,
                                      source_dates=("2026-01-01",), date_coverage=("2026-01-01",),
                                      provenance={"source": "test fixture"})), max_steps=4,
        )
        state = AdaptiveAgentState(available_diary=True)

        result = loop.run_turn("分析我的记录", state)

        self.assertEqual(result.status, "ANSWER")
        self.assertEqual(result.state.facts["recent_sleep_pattern"], diary_entries)
        self.assertEqual(result.state.facts["diary_derived"]["diary_day_count"], 1)
        self.assertEqual(result.state.diary_projection["projection_status"], "valid")
        self.assertEqual([item.action for item in result.transitions], ["READ_DIARY", "ANSWER"])

    def test_ask_stops_the_current_turn_without_running_tools(self):
        retrieval = FakeRetrievalTool(RetrievalResult(("must not be used",)))
        loop = AdaptiveAgentLoop(
            StaticUnderstander("是否应该早点上床", TaskType.PERSONALIZED_DECISION,
                              {"bedtime": "23:00", "sleep_onset_latency": 60}),
            retrieval, FakeDiaryTool(DiaryResult({}, False)), max_steps=4,
        )

        result = loop.run_turn("我应该早点上床吗？")

        self.assertEqual(result.status, "ASK")
        self.assertEqual(result.steps, 1)
        self.assertEqual(result.state.action_history[-1]["action"], "ASK")
        self.assertEqual(retrieval.queries, [])

    def test_answer_stops_the_loop(self):
        result, _ = self.knowledge_loop(RetrievalResult(("CBT-I evidence",)))

        self.assertEqual(result.transitions[-1].action, "ANSWER")
        self.assertEqual(result.steps, 2)

    def test_max_steps_stops_an_unproductive_tool_loop(self):
        loop = AdaptiveAgentLoop(
            StaticUnderstander("解释刺激控制", TaskType.KNOWLEDGE_QA),
            FakeRetrievalTool(RetrievalResult(())), FakeDiaryTool(DiaryResult({}, False)),
            policy=AlwaysRetrievePolicy(), max_steps=2,
        )

        result = loop.run_turn("什么是刺激控制？")

        self.assertEqual(result.status, "MAX_STEPS")
        self.assertEqual(result.steps, 2)
        self.assertEqual([item.action for item in result.transitions], ["RETRIEVE", "RETRIEVE"])

    def test_unavailable_diary_does_not_create_facts(self):
        diary = FakeDiaryTool(DiaryResult({}, False, "sleep diary unavailable"))
        loop = AdaptiveAgentLoop(
            StaticUnderstander("分析最近七天日记", TaskType.DATA_ANALYSIS),
            FakeRetrievalTool(RetrievalResult(())), diary, max_steps=3,
        )

        result = loop.run_turn("帮我分析最近7天的睡眠日记")

        self.assertEqual(result.status, "ANSWER")
        self.assertFalse(result.state.available_diary)
        self.assertEqual(result.state.facts, {})
        self.assertIn("无法补足", result.response)
        self.assertEqual(diary.calls, 1)

    def test_unknown_fields_are_materialized_as_none_not_guessed(self):
        understood = understanding_from_mapping({
            "goal": "解释刺激控制", "task_type": "KNOWLEDGE_QA", "facts": {"bedtime": "23:00"},
        }, "我每晚23点上床。")

        self.assertEqual(understood.facts["bedtime"], "23:00")
        self.assertIsNone(understood.facts["wake_time"])
        self.assertIsNone(understood.facts["perceived_stress"])


if __name__ == "__main__":
    unittest.main()
