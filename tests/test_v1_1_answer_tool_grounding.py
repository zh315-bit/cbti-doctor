import unittest
from unittest.mock import Mock

from adaptive_agent.answer_generation import (
    LLMAnswerGenerator, data_derived_claims, deterministic_claim_records,
)
from adaptive_agent.state import AdaptiveAgentState, TaskType
from adaptive_agent.state_update import apply_diary_result
from adaptive_agent.tools import DiaryResult


def model_returning(text):
    model = Mock()
    model.invoke.return_value.content = text
    model.invoke.return_value.response_metadata = {}
    return model


class V11AnswerToolGroundingTests(unittest.TestCase):
    def state(self, **facts):
        return AdaptiveAgentState(goal="分析睡眠日记", task_type=TaskType.DATA_ANALYSIS,
                                  facts=facts, answer_scope="仅作描述性分析。")

    def test_cross_midnight_and_range_do_not_create_false_duration(self):
        exact = data_derived_claims({"bedtime": "23:30", "wake_time": "07:00"})
        self.assertIn("450 分钟", " ".join(exact))
        ranged = data_derived_claims({"bedtime": "23:30", "wake_time": {"uncertainty": "range", "low": "07:00", "high": "08:00"}})
        self.assertNotIn("卧床时间", " ".join(ranged))

    def test_diary_count_average_and_coverage_are_deterministic(self):
        facts = {"recent_sleep_pattern": [
            {"date": "2026-09-01", "total_sleep_time": 360},
            {"date": "2026-09-02", "total_sleep_time": 420},
        ]}
        claims = " ".join(data_derived_claims(facts))
        self.assertIn("2 天记录", claims)
        self.assertIn("平均总睡眠时间约为 390 分钟", claims)
        self.assertIn("2 个日期", claims)
        self.assertNotIn("7 天", claims)

    def test_approximate_fact_is_preserved_in_context_and_provenance(self):
        state = self.state(wake_time={"uncertainty": "approximate", "value": "07:00"})
        state.fact_sources["wake_time"] = {"source_type": "user_explicit", "certainty": "approximate"}
        model = model_returning("你大约在07:00起床。")
        LLMAnswerGenerator(model).answer(state)
        prompt = model.invoke.call_args.args[0][1][1]
        self.assertIn("approximate", prompt)
        self.assertTrue(any(item["source_field"] == "wake_time" for item in state.claim_provenance))

    def test_unavailable_diary_data_is_not_used(self):
        state = self.state()
        answer = LLMAnswerGenerator(model_returning("日记覆盖7天，平均睡眠360分钟。")).answer(state)
        self.assertNotIn("7天", answer)
        self.assertNotIn("360分钟", answer)

    def test_user_fact_is_allowed_but_unsupported_user_fact_is_removed(self):
        state = self.state(bedtime="00:00")
        state.fact_sources["bedtime"] = {"source_type": "user_explicit", "certainty": "exact"}
        answer = LLMAnswerGenerator(model_returning("你通常00:00上床。你夜里醒2次。 ")).answer(state)
        self.assertIn("00:00", answer)
        self.assertNotIn("醒2次", answer)

    def test_evidence_backed_medical_threshold_and_claim_provenance(self):
        state = self.state()
        state.evidence = ["睡眠日记资料指出睡眠效率低于85%时需要进一步评估。"]
        answer = LLMAnswerGenerator(model_returning("资料提到85%的阈值。 ")).answer(state)
        self.assertIn("85%", answer)
        evidence_records = [item for item in state.claim_provenance if item["claim_type"] == "evidence-grounded"]
        self.assertEqual(evidence_records[0]["source"], "evidence:0")

    def test_tool_state_answer_value_consistency(self):
        state = self.state()
        state.action_history.append({"action": "READ_DIARY"})
        entries = [{"date": "2026-01-01", "bedtime": "23:30", "wake_time": "07:00"}]
        apply_diary_result(state, DiaryResult({"entries": entries}, True, source_entry_count=1,
                                              source_dates=("2026-01-01",), date_coverage=("2026-01-01",),
                                              provenance={"source": "test"}))
        answer = LLMAnswerGenerator(model_returning("记录显示卧床时间为450分钟。 ")).answer(state)
        self.assertIn("450 分钟", answer)
        self.assertEqual(state.fact_sources["recent_sleep_pattern"]["source_type"], "diary")


if __name__ == "__main__":
    unittest.main()
