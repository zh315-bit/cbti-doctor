import unittest
from unittest.mock import Mock

from adaptive_agent.answer_generation import (
    LLMAnswerGenerator, data_derived_claims, relevant_evidence,
)
from adaptive_agent.state import AdaptiveAgentState, TaskType


def model_returning(text):
    model = Mock()
    model.invoke.return_value.content = text
    model.invoke.return_value.response_metadata = {}
    return model


class AnswerGenerationGroundingTests(unittest.TestCase):
    def state(self, **facts):
        return AdaptiveAgentState(goal="分析最近7天的睡眠日记", task_type=TaskType.DATA_ANALYSIS,
                                  facts=facts, answer_scope="只作基于日记的描述性分析。")

    def test_empty_evidence_strips_unsupported_quantitative_threshold(self):
        state = self.state(bedtime="23:00", wake_time="07:00", total_sleep_time=360)
        answer = LLMAnswerGenerator(model_returning("睡眠效率约75%。睡眠效率低于85%属于异常。 ")).answer(state)
        self.assertIn("75%", answer)
        self.assertNotIn("85%", answer)

    def test_evidence_supported_threshold_is_allowed(self):
        state = self.state()
        state.evidence = ["睡眠日记分析的资料：睡眠效率低于85%时需要进一步评估。"]
        answer = LLMAnswerGenerator(model_returning("根据资料，85% 是该资料提到的阈值。 ")).answer(state)
        self.assertIn("85%", answer)

    def test_directional_scope_removes_supported_but_prescriptive_rule(self):
        state = AdaptiveAgentState(goal="判断是否应该提前上床", task_type=TaskType.PERSONALIZED_DECISION,
                                   evidence=["提前上床的资料：睡眠效率达到90%后提前15分钟。"],
                                   answer_scope="仅讨论是否提前上床的方向；不指定具体新上床时间、睡眠窗口或睡眠限制处方。")
        answer = LLMAnswerGenerator(model_returning("睡眠效率达到90%后提前15分钟。可以先观察困意。 ")).answer(state)
        self.assertNotIn("15分钟", answer)
        self.assertIn("观察困意", answer)

    def test_diary_facts_produce_deterministic_descriptive_claims(self):
        claims = data_derived_claims({"bedtime": "23:00", "wake_time": "07:00", "total_sleep_time": 360,
                                      "recent_sleep_pattern": [{}, {}, {}, {}, {}, {}, {}]})
        self.assertIn("480 分钟", " ".join(claims))
        self.assertIn("75%", " ".join(claims))
        self.assertIn("7 天", " ".join(claims))

    def test_data_analysis_answer_keeps_deterministic_description_when_model_claim_is_removed(self):
        state = self.state(bedtime="23:00", wake_time="07:00", total_sleep_time=360)
        answer = LLMAnswerGenerator(model_returning("睡眠效率低于85%属于异常。 ")).answer(state)
        self.assertIn("卧床时间为 480 分钟", answer)
        self.assertIn("睡眠效率约为 75%", answer)
        self.assertNotIn("85%", answer)

    def test_fake_diary_value_is_removed(self):
        state = self.state(bedtime="23:00", wake_time="07:00", total_sleep_time=360)
        answer = LLMAnswerGenerator(model_returning("你夜里醒2次。总睡眠时间为360分钟。 ")).answer(state)
        self.assertNotIn("醒2次", answer)
        self.assertIn("360分钟", answer)

    def test_answer_scope_is_the_only_scope_passed_to_model(self):
        state = self.state(total_sleep_time=360)
        model = model_returning("已依据日记描述。")
        LLMAnswerGenerator(model).answer(state)
        prompt = model.invoke.call_args.args[0][1][1]
        self.assertIn(state.answer_scope, prompt)
        self.assertNotIn("critical_missing", prompt)

    def test_irrelevant_retrieved_evidence_is_not_used(self):
        state = AdaptiveAgentState(goal="解释刺激控制", task_type=TaskType.KNOWLEDGE_QA,
                                   evidence=["咖啡因摄入与睡眠的资料"], answer_scope="只解释刺激控制。")
        model = model_returning("刺激控制的解释。")
        LLMAnswerGenerator(model).answer(state)
        self.assertEqual(relevant_evidence(state.goal, state.evidence), [])
        self.assertIn("'relevant_evidence': []", model.invoke.call_args.args[0][1][1])

    def test_english_goal_keeps_matching_english_evidence(self):
        evidence = ["Stimulus control is a CBT-I behavioral technique."]
        self.assertEqual(relevant_evidence("Explain stimulus control", evidence), evidence)

    def test_model_parameter_knowledge_cannot_be_presented_as_retrieved_evidence(self):
        state = self.state()
        answer = LLMAnswerGenerator(model_returning("模型知识表明睡眠效率应达到85%。 ")).answer(state)
        self.assertNotIn("85%", answer)
        self.assertIn("当前回答范围不提供具体阈值", answer)


if __name__ == "__main__":
    unittest.main()
