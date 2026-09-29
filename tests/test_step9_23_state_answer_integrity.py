"""Synthetic State→Answer integrity checks; no benchmark or external model."""
import unittest
from unittest.mock import Mock

from adaptive_agent.answer_generation import LLMAnswerGenerator, build_answer_context
from adaptive_agent.state import AdaptiveAgentState, TaskType
from adaptive_agent.state_update import apply_diary_result, apply_retrieval_result
from adaptive_agent.tools import DiaryResult, RetrievalResult


def generator(text):
    model = Mock()
    model.invoke.return_value.content = text
    model.invoke.return_value.response_metadata = {}
    return LLMAnswerGenerator(model), model


def diary_state(entries):
    dates = tuple(item["date"] for item in entries)
    state = AdaptiveAgentState(goal="总结这组睡眠记录", task_type=TaskType.DATA_ANALYSIS,
                               goal_id="synthetic", action_history=[{"action": "READ_DIARY", "action_id": "act_synthetic"}],
                               answer_scope="仅基于有效记录作描述。")
    apply_diary_result(state, DiaryResult({"entries": entries}, True, source_entry_count=len(entries),
                                          source_dates=dates, date_coverage=tuple(dict.fromkeys(dates)),
                                          provenance={"source": "synthetic"}))
    return state


class StateAnswerIntegrityTests(unittest.TestCase):
    def test_a_explicit_user_fact_has_source_in_context(self):
        state = AdaptiveAgentState(goal="讨论作息", task_type=TaskType.PERSONALIZED_DECISION,
                                   facts={"bedtime": "23:00"}, fact_sources={"bedtime": {
                                       "source_type": "user_explicit", "source_turn": 1, "certainty": "exact"}})
        context = build_answer_context(state)
        self.assertEqual(context["user_facts"]["bedtime"]["value"], "23:00")
        self.assertEqual(context["provenance"]["facts"]["bedtime"]["source_turn"], 1)

    def test_raw_user_utterance_is_not_a_second_fact_channel(self):
        state = AdaptiveAgentState(goal="讨论作息", facts={"bedtime": "23:00"},
                                   fact_sources={"bedtime": {"source_type": "user_explicit", "source_turn": 1,
                                                               "text": "我喝了三杯咖啡", "raw_value": "23点"}})
        context = build_answer_context(state)
        self.assertNotIn("我喝了三杯咖啡", str(context))
        self.assertNotIn("raw_value", str(context))

    def test_b_same_goal_retrieval_enters_context_without_keyword_whitelist(self):
        state = AdaptiveAgentState(goal="为什么固定起床有助于节律稳定", goal_id="synthetic",
                                   task_type=TaskType.KNOWLEDGE_QA,
                                   action_history=[{"action": "RETRIEVE", "action_id": "act_synthetic", "query": "为什么固定起床有助于节律稳定"}],
                                   dependencies_considered=[{"dependency_type": "EVIDENCE", "status": "SATISFIED", "dependency_id": "dep1"}])
        apply_retrieval_result(state, RetrievalResult(("规律的早晨光照有助于昼夜节律同步。",), True, "synthetic"))
        context = build_answer_context(state)
        self.assertEqual(len(context["relevant_evidence"]), 1)
        self.assertEqual(context["evidence_projection"][0]["dependency_id"], "dep1")

    def test_c_unrelated_evidence_is_excluded_with_reason(self):
        state = AdaptiveAgentState(goal="说明刺激控制", evidence=["咖啡因摄入的资料"])
        self.assertEqual(build_answer_context(state)["relevant_evidence"], [])
        self.assertEqual(state.answer_context_audit["evidence_projection"][0]["exclusion_reason"], "irrelevant")

    def test_d_present_record_missing_field_is_not_absent(self):
        state = diary_state([{"date": "2027-02-01", "total_sleep_time": None}])
        semantic = build_answer_context(state)["semantic_status"]
        self.assertEqual(semantic["records"][0]["fields"]["total_sleep_time"], "RECORD_PRESENT_FIELD_MISSING")
        answer, _ = generator("2027-02-01 的日记记录缺失。")
        self.assertNotIn("记录缺失", answer.answer(state))

    def test_present_records_cannot_be_described_as_no_records_at_all(self):
        state = diary_state([{"date": "2027-02-03", "total_sleep_time": None}])
        answer, _ = generator("没有日记记录。")
        self.assertNotIn("没有日记记录", answer.answer(state))

    def test_e_unavailable_resource_is_not_absent_record(self):
        state = AdaptiveAgentState(goal="总结日记", task_type=TaskType.DATA_ANALYSIS,
                                   diary_projection={"projection_status": "unavailable"},
                                   resource_status={"sleep_diary": "unavailable"})
        self.assertEqual(build_answer_context(state)["semantic_status"]["resource"], "RESOURCE_UNAVAILABLE")
        answer, _ = generator("你没有日记记录。")
        self.assertNotIn("没有日记记录", answer.answer(state))

    def test_f_invalid_field_is_not_absent_record(self):
        state = diary_state([{"date": "2027-02-02", "total_sleep_time": {"uncertainty": "invalid"}}])
        semantic = build_answer_context(state)["semantic_status"]
        self.assertEqual(semantic["records"][0]["fields"]["total_sleep_time"], "RECORD_PRESENT_FIELD_INVALID")
        answer, _ = generator("2027-02-02 没有日记记录。")
        self.assertNotIn("没有日记记录", answer.answer(state))

    def test_g_missing_user_fact_is_not_reintroduced(self):
        state = AdaptiveAgentState(goal="讨论当前作息", task_type=TaskType.PERSONALIZED_DECISION)
        answer, _ = generator("你经常喝咖啡。")
        self.assertNotIn("喝咖啡", answer.answer(state))

    def test_h_evidence_backed_quantitative_rule_remains(self):
        state = AdaptiveAgentState(goal="解释睡眠效率阈值", task_type=TaskType.KNOWLEDGE_QA,
                                   evidence=["睡眠效率低于85%时应进一步评估。"])
        answer, _ = generator("资料指出低于85%时应进一步评估。")
        self.assertIn("85%", answer.answer(state))

    def test_i_unsupported_quantitative_rule_is_removed(self):
        state = AdaptiveAgentState(goal="解释睡眠效率", task_type=TaskType.KNOWLEDGE_QA)
        answer, _ = generator("低于83%应治疗。")
        self.assertNotIn("83%", answer.answer(state))

    def test_j_answer_scope_still_limits_prescription(self):
        state = AdaptiveAgentState(goal="讨论是否提早上床", task_type=TaskType.PERSONALIZED_DECISION,
                                   answer_scope="仅讨论方向；不指定具体新上床时间。")
        answer, _ = generator("建议提前上床30分钟。可以先观察困意。")
        result = answer.answer(state)
        self.assertNotIn("30分钟", result)
        self.assertIn("观察困意", result)

    def test_invalid_projection_never_enters_context_or_answer(self):
        state = AdaptiveAgentState(goal="总结日记", task_type=TaskType.DATA_ANALYSIS,
                                   facts={"recent_sleep_pattern": [{"date": "2027-03-01", "total_sleep_time": 390}]},
                                   fact_sources={"recent_sleep_pattern": {"source_type": "diary"}},
                                   diary_projection={"projection_status": "invalid"})
        self.assertNotIn("recent_sleep_pattern", build_answer_context(state)["relevant_facts"])
        answer, model = generator("无法验证日记数据。")
        answer.answer(state)
        self.assertNotIn("2027-03-01", model.invoke.call_args.args[0][1][1])

    def test_answer_trace_records_evidence_exclusion_without_sending_it_to_model(self):
        state = AdaptiveAgentState(goal="说明刺激控制", evidence=["咖啡因摄入的资料"])
        answer, model = generator("当前材料不足。")
        answer.answer(state)
        self.assertEqual(state.answer_context_audit["evidence_projection"][0]["exclusion_reason"], "irrelevant")
        self.assertNotIn("咖啡因摄入的资料", model.invoke.call_args.args[0][1][1])


if __name__ == "__main__":
    unittest.main()
