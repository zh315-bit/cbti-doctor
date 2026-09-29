import unittest

from adaptive_agent.candidates import build_candidates
from adaptive_agent.policy import HeuristicDecisionPolicy
from adaptive_agent.requirements import RequirementSet
from adaptive_agent.state import AdaptiveAgentState, TaskType
from adaptive_agent.state_update import apply_diary_result
from adaptive_agent.sufficiency import SufficiencyEstimator
from adaptive_agent.tools import DiaryResult


class HardPreconditionTests(unittest.TestCase):
    def decide(self, state, req):
        SufficiencyEstimator().update(state, req)
        state.candidate_actions = build_candidates(state, req)
        return HeuristicDecisionPolicy().choose(state)

    def test_evidence_required_retrieves_before_optional_policy(self):
        state = AdaptiveAgentState(goal='解释一种睡眠原则', task_type=TaskType.KNOWLEDGE_QA)
        action = self.decide(state, RequirementSet((), (), True))
        self.assertEqual(action.action, 'RETRIEVE')
        self.assertEqual(state.preconditions_considered[0]['type'], 'EVIDENCE')

    def test_existing_evidence_does_not_retrieve_again(self):
        state = AdaptiveAgentState(goal='解释一种睡眠原则', task_type=TaskType.KNOWLEDGE_QA, evidence=['support'])
        self.assertEqual(self.decide(state, RequirementSet((), (), True)).action, 'ANSWER')

    def test_authorized_available_diary_is_hard_read(self):
        state = AdaptiveAgentState(goal='分析记录', task_type=TaskType.DATA_ANALYSIS, diary_authorized=True, diary_available=True)
        self.assertEqual(self.decide(state, RequirementSet((), (), False, resources=('sleep_diary',))).action, 'READ_DIARY')

    def test_unavailable_or_unauthorized_diary_never_reads(self):
        req = RequirementSet((), (), False, resources=('sleep_diary',))
        for state in (AdaptiveAgentState(goal='分析记录', task_type=TaskType.DATA_ANALYSIS, diary_available=False), AdaptiveAgentState(goal='分析记录', task_type=TaskType.DATA_ANALYSIS, diary_authorized=False)):
            self.assertEqual(self.decide(state, req).action, 'ANSWER')

    def test_optional_state_stays_optional_but_genuine_critical_state_asks(self):
        optional = AdaptiveAgentState(goal='比较作息', task_type=TaskType.PERSONALIZED_DECISION)
        self.assertEqual(self.decide(optional, RequirementSet((), ('caffeine',), False)).action, 'ANSWER')
        critical = AdaptiveAgentState(goal='调整起床时间', task_type=TaskType.PERSONALIZED_DECISION)
        self.assertEqual(self.decide(critical, RequirementSet(('wake_time',), (), False)).action, 'ASK')

    def test_validity_criticality_is_goal_dependent_and_diary_precedes_ask(self):
        req = RequirementSet(('wake_time', 'recent_sleep_pattern'), (), False)
        directional = AdaptiveAgentState(goal='我该提前还是推迟上床时间', task_type=TaskType.PERSONALIZED_DECISION)
        self.assertEqual(self.decide(directional, req).action, 'ASK')
        self.assertIn('wake_time', directional.validity_critical_missing)
        educational = AdaptiveAgentState(goal='规律起床时间为什么重要', task_type=TaskType.KNOWLEDGE_QA)
        self.decide(educational, req)
        self.assertEqual(educational.validity_critical_missing, [])
        self.assertFalse(any(p['type'] == 'VALIDITY_CRITICAL_STATE'
                             for p in educational.preconditions_considered))
        diary = AdaptiveAgentState(goal='我该提前还是推迟上床时间', task_type=TaskType.PERSONALIZED_DECISION,
                                   available_diary=True, diary_authorized=True, diary_available=True)
        self.assertEqual(self.decide(diary, req).action, 'READ_DIARY')

    def test_validity_critical_trace_and_semantic_boundary(self):
        directional_req = RequirementSet(('wake_time',), (), False)
        directional = AdaptiveAgentState(goal='我该提前还是推迟上床时间', task_type=TaskType.PERSONALIZED_DECISION)
        self.assertEqual(self.decide(directional, directional_req).action, 'ASK')
        item = directional.preconditions_considered[0]
        self.assertEqual(item['type'], 'SOFT_VALIDITY_PRECONDITION')
        self.assertEqual(item['target'], 'wake_time')
        self.assertEqual(item['required_for'], directional.goal)
        self.assertIsNone(item['required_action'])
        self.assertEqual(item['status'], 'awaiting_information_value_gate')
        self.assertEqual(directional.candidate_actions[0].action, 'ASK')
        self.assertEqual(directional.candidate_actions[0].gate_decision, 'ACCEPT')
        self.assertTrue(item['reason'])
        self.assertEqual(directional.candidate_actions[0].gate_decision, 'ACCEPT')

        # The same field is not intrinsically hard: an educational goal remains
        # answerable without a user's wake time.
        educational = AdaptiveAgentState(goal='规律起床时间为什么重要', task_type=TaskType.KNOWLEDGE_QA)
        self.decide(educational, directional_req)
        self.assertEqual(educational.validity_critical_missing, [])
        self.assertFalse(any(p['type'] == 'VALIDITY_CRITICAL_STATE'
                             for p in educational.preconditions_considered))

    def test_other_important_fields_do_not_become_hard_solely_by_requirement_rank(self):
        # These fields can be useful or even decision-relevant.  They are not made
        # validity-critical merely because a requirement labels them critical.
        for field in ('caffeine', 'nighttime_awakenings', 'recent_sleep_pattern'):
            state = AdaptiveAgentState(goal='我想改善睡眠习惯', task_type=TaskType.PERSONALIZED_DECISION)
            self.decide(state, RequirementSet((field,), (), False))
            self.assertEqual(state.validity_critical_missing, [], field)
            self.assertFalse(any(p['type'] == 'VALIDITY_CRITICAL_STATE'
                                 for p in state.preconditions_considered), field)

        # Sleep-onset latency becomes hard only in the directional timing context,
        # not for a knowledge explanation about that same field.
        directional = AdaptiveAgentState(goal='我该提前还是推迟上床时间', task_type=TaskType.PERSONALIZED_DECISION)
        self.decide(directional, RequirementSet(('sleep_onset_latency',), (), False))
        self.assertIn('sleep_onset_latency', directional.validity_critical_missing)
        explanation = AdaptiveAgentState(goal='入睡潜伏期是什么意思', task_type=TaskType.KNOWLEDGE_QA)
        self.decide(explanation, RequirementSet(('sleep_onset_latency',), (), False))
        self.assertEqual(explanation.validity_critical_missing, [])

    def test_unanswered_validity_question_is_deferred_not_repeated(self):
        state = AdaptiveAgentState(
            goal='是否应该早点上床', task_type=TaskType.PERSONALIZED_DECISION,
            facts={'bedtime': '23:00', 'sleep_time': '00:00'},
            action_history=[{'action': 'ASK', 'target': 'wake_time'}],
        )
        action = self.decide(state, RequirementSet(
            ('bedtime', 'sleep_time_or_sleep_onset_latency', 'wake_time'), (), False,
        ))
        self.assertEqual(action.action, 'ANSWER')
        item = state.preconditions_considered[0]
        self.assertEqual(item['type'], 'SOFT_VALIDITY_PRECONDITION')
        self.assertEqual(item['status'], 'awaiting_information_value_gate')
        self.assertEqual(action.action, 'ANSWER')
        self.assertFalse(any(candidate.action == 'ASK' for candidate in state.candidate_actions))

    def test_diary_projection_invariants_preserve_entries_dates_and_provenance(self):
        state = AdaptiveAgentState(action_history=[{'action':'READ_DIARY'}])
        entries=[{'date':'2026-01-01','total_sleep_time':400},{'date':'2026-01-02','total_sleep_time':420}]
        apply_diary_result(state, DiaryResult({'recent_sleep_pattern':entries}, True, source_entry_count=2, source_dates=('2026-01-01','2026-01-02'), date_coverage=('2026-01-01','2026-01-02'), provenance={'source':'test'}))
        self.assertEqual(state.diary_projection['projection_status'], 'valid')
        self.assertEqual(state.diary_projection['projected_entry_count'], 2)
        self.assertIn('projection', state.fact_sources['recent_sleep_pattern'])

    def test_malformed_projection_is_invalid_and_adds_no_facts(self):
        state = AdaptiveAgentState(action_history=[{'action':'READ_DIARY'}])
        apply_diary_result(state, DiaryResult({'recent_sleep_pattern':[{'date':'2026-01-01'}]}, True, source_entry_count=2))
        self.assertEqual(state.diary_projection['projection_status'], 'invalid')
        self.assertEqual(state.facts, {})


if __name__ == '__main__': unittest.main()
