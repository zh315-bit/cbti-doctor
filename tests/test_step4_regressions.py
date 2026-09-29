"""Small regression checks exposed by Step 4 trace validation (no network)."""
from copy import deepcopy
import unittest

from adaptive_agent.requirements import load_requirements
from adaptive_agent.state import AdaptiveAgentState, ActionCandidate, TaskType
from adaptive_agent.state_update import apply_diary_result, apply_retrieval_result
from adaptive_agent.tools import SessionDiaryTool, DiaryResult, RetrievalResult
from adaptive_agent.runner import AdaptiveAgentLoop
from adaptive_agent.input_understanding import Understanding
from adaptive_agent.service import AdaptiveChatService


class Step4Regressions(unittest.TestCase):
    def test_known_policy_failure_available_diary_must_be_read_before_answer(self):
        """Tracked acceptance failure: availability alone is not analyzed information."""
        from adaptive_agent.sufficiency import SufficiencyEstimator
        from adaptive_agent.candidates import build_candidates
        from adaptive_agent.policy import HeuristicDecisionPolicy
        state = AdaptiveAgentState(goal='分析最近7天日记', task_type=TaskType.DATA_ANALYSIS,
                                   available_diary=True)
        requirements = load_requirements()[TaskType.DATA_ANALYSIS]
        SufficiencyEstimator().update(state, requirements)
        state.candidate_actions = build_candidates(state, requirements)
        self.assertEqual(HeuristicDecisionPolicy().choose(state).action, 'READ_DIARY')

    def test_analysis_diary_does_not_discard_requested_data(self):
        facts = {'bedtime': '23:00', 'wake_time': '07:00', 'total_sleep_time': 360,
                 'recent_sleep_pattern': [{'date': '2026-09-11', 'total_sleep_time': 360}]}
        result = SessionDiaryTool(facts).read(load_requirements()[TaskType.DATA_ANALYSIS])
        self.assertEqual(result.facts, facts)
        self.assertTrue(result.available)

    def test_empty_diary_is_unavailable(self):
        self.assertFalse(SessionDiaryTool({}).read(load_requirements()[TaskType.DATA_ANALYSIS]).available)

    def test_unavailable_tool_payload_is_not_merged(self):
        state = AdaptiveAgentState(action_history=[{'action': 'READ_DIARY'}])
        apply_diary_result(state, DiaryResult({'wake_time': 'invented'}, False))
        apply_retrieval_result(state, RetrievalResult(('invalid',), False))
        self.assertEqual(state.facts, {})
        self.assertEqual(state.evidence, [])

    def test_last_tool_step_refreshes_state_and_records_decision(self):
        class Understander:
            def understand(self, text, state):
                return Understanding('知识问题', TaskType.KNOWLEDGE_QA, {})
        class Retrieve:
            def retrieve(self, query):
                return RetrievalResult(('fixture evidence',))
        loop = AdaptiveAgentLoop(Understander(), Retrieve(), SessionDiaryTool(), max_steps=1)
        result = loop.run_turn('知识问题')
        self.assertEqual(result.status, 'MAX_STEPS')
        self.assertEqual(result.state.evidence_sufficiency, 'HIGH')
        decision = next(s for s in result.state_history if s['event'] == 'DECISION')
        self.assertIn('requirements', decision)
        self.assertEqual(decision['chosen_action']['query'], '知识问题')
        tool = next(s for s in result.state_history if s['event'] == 'RETRIEVE')
        self.assertEqual(tool['tool_result']['evidence'], ('fixture evidence',))

    def test_failed_turn_does_not_mutate_saved_session(self):
        class FailingLoop:
            answer_generator = None
            def run_turn(self, text, state):
                state.facts['wake_time'] = 'corrupted'
                raise RuntimeError('fixture failure')
        from adaptive_agent.service import AdaptiveSession
        service = AdaptiveChatService(FailingLoop())
        service.sessions['s'] = AdaptiveSession(AdaptiveAgentState(goal='old'))
        before = deepcopy(service.sessions['s'])
        with self.assertRaises(RuntimeError):
            service.chat('s', 'reply')
        self.assertEqual(service.sessions['s'], before)


if __name__ == '__main__':
    unittest.main()
