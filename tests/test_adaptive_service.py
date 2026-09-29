import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from adaptive_agent.input_understanding import Understanding
from adaptive_agent.runner import AdaptiveAgentLoop
from adaptive_agent.service import AdaptiveChatService
from adaptive_agent.state import ActionCandidate, TaskType
from adaptive_agent.tools import DiaryResult, RetrievalResult
from evaluation.recorder import EvaluationRecorder


class SequenceUnderstander:
    def __init__(self, results):
        self.results = iter(results)

    def understand(self, user_input, prior_state=None):
        return next(self.results)


class FakeRetrievalTool:
    def __init__(self, evidence=("CBT-I evidence",)):
        self.evidence = evidence
        self.queries = []

    def retrieve(self, query):
        self.queries.append(query)
        return RetrievalResult(self.evidence, detail="mock RAG")


class NoDiaryTool:
    def read(self, requirements):
        return DiaryResult({}, False, "unavailable")


class FakeAnswerGenerator:
    last_token_usage = {"total_tokens": 7}

    def answer(self, state, limitation=None):
        return limitation or f"answer: {state.goal}; facts={state.facts}; evidence={state.evidence}"


class InMemoryRecorder:
    def __init__(self):
        self.calls = []

    def record(self, *args):
        self.calls.append(args)


class AlwaysRetrievePolicy:
    def choose(self, state):
        return ActionCandidate(action="RETRIEVE", query=state.goal, expected_benefit="HIGH", cost="LOW")


class AdaptiveServiceTests(unittest.TestCase):
    def make_service(self, understandings, retrieval=None, recorder=None, policy=None, max_steps=4):
        loop = AdaptiveAgentLoop(
            SequenceUnderstander(understandings), retrieval or FakeRetrievalTool(), NoDiaryTool(),
            answer_generator=FakeAnswerGenerator(), policy=policy, max_steps=max_steps,
        )
        return AdaptiveChatService(loop, recorder or InMemoryRecorder())

    def test_two_ask_turns_preserve_goal_facts_and_action_history(self):
        service = self.make_service([
            Understanding("是否应该早点上床", TaskType.PERSONALIZED_DECISION,
                          {"bedtime": "23:00"}),
            Understanding(None, None, {"sleep_onset_latency": 60}),
        ])

        first = service.chat("s1", "我应该早点上床吗？")
        second = service.chat("s1", "我需要60分钟入睡")
        state = service.sessions["s1"].state

        self.assertEqual(first["status"], "ASK")
        self.assertEqual(second["status"], "ASK")
        self.assertEqual(state.goal, "是否应该早点上床")
        self.assertEqual(state.facts["bedtime"], "23:00")
        self.assertEqual(state.facts["sleep_onset_latency"], 60)
        self.assertEqual([item["action"] for item in state.action_history], ["ASK", "ASK"])

    def test_retrieved_evidence_persists_across_loop_turns(self):
        retrieval = FakeRetrievalTool()
        service = self.make_service([
            Understanding("解释刺激控制", TaskType.KNOWLEDGE_QA, {}),
            Understanding(None, None, {}),
        ], retrieval)

        first = service.chat("s1", "什么是刺激控制？")
        second = service.chat("s1", "请继续")
        state = service.sessions["s1"].state

        self.assertEqual(first["status"], "ANSWER")
        self.assertEqual(second["status"], "ANSWER")
        self.assertEqual(state.evidence, ["CBT-I evidence"])
        self.assertEqual(retrieval.queries, ["解释刺激控制"])

    def test_new_goal_resets_old_facts_and_history(self):
        service = self.make_service([
            Understanding("是否应该早点上床", TaskType.PERSONALIZED_DECISION,
                          {"bedtime": "23:00", "sleep_onset_latency": 60}),
            Understanding("解释刺激控制", TaskType.KNOWLEDGE_QA, {}, is_new_goal=True),
        ])

        service.chat("s1", "我应该早点上床吗？")
        result = service.chat("s1", "换个问题，什么是刺激控制？")
        state = service.sessions["s1"].state

        self.assertEqual(result["status"], "ANSWER")
        self.assertEqual(state.goal, "解释刺激控制")
        self.assertEqual(state.facts, {})
        self.assertEqual([item["action"] for item in state.action_history], ["RETRIEVE", "ANSWER"])

    def test_max_steps_remains_visible_through_service(self):
        service = self.make_service(
            [Understanding("解释刺激控制", TaskType.KNOWLEDGE_QA, {})],
            policy=AlwaysRetrievePolicy(), max_steps=2,
        )

        result = service.chat("s1", "什么是刺激控制？")

        self.assertEqual(result["status"], "MAX_STEPS")
        self.assertEqual(result["steps"], 2)

    def test_evaluation_jsonl_contains_required_turn_data(self):
        with TemporaryDirectory() as directory:
            recorder = EvaluationRecorder(Path(directory))
            service = self.make_service(
                [Understanding("解释刺激控制", TaskType.KNOWLEDGE_QA, {})], recorder=recorder,
            )

            service.chat("case-1", "什么是刺激控制？")
            files = list(Path(directory).glob("*.jsonl"))
            self.assertEqual(len(files), 1)
            payload = json.loads(files[0].read_text(encoding="utf-8").strip())

        self.assertEqual(payload["session_id"], "case-1")
        self.assertEqual(payload["goal"], "解释刺激控制")
        self.assertEqual(payload["final_status"], "ANSWER")
        self.assertEqual(payload["tool_calls"], ["RETRIEVE"])
        self.assertEqual(payload["token_usage"], {"total_tokens": 7})
        self.assertTrue(payload["state_history"])


if __name__ == "__main__":
    unittest.main()
