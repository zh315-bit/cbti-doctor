"""Offline regressions for goal-scoped readiness, resource lifecycle and ties."""
from dataclasses import replace
from itertools import permutations
import unittest

from adaptive_agent.state import AdaptiveAgentState, ActionCandidate, TaskType
from adaptive_agent.requirements import load_requirements, RequirementSet
from adaptive_agent.requirements import synchronize_requirements
from adaptive_agent.dependency_resolver import DependencyResolver
from adaptive_agent.sufficiency import SufficiencyEstimator
from adaptive_agent.candidates import build_candidates
from adaptive_agent.policy import HeuristicDecisionPolicy
from adaptive_agent.state_update import apply_diary_result
from adaptive_agent.tools import DiaryResult


class PolicyRefinementTests(unittest.TestCase):
    def decide(self, state, requirements=None):
        requirements = requirements or load_requirements()[state.task_type]
        SufficiencyEstimator().update(state, requirements)
        dependencies = DependencyResolver().resolve(state, requirements)
        state.dependencies_considered = [item.to_dict() for item in dependencies]
        requirements = synchronize_requirements(requirements, state, dependencies)
        SufficiencyEstimator().update(state, requirements)
        state.candidate_actions = build_candidates(state, requirements)
        return HeuristicDecisionPolicy().choose(state)

    def test_direction_goal_stops_asking_while_critical_fields_still_missing(self):
        state = AdaptiveAgentState(goal='判断是否应该早点上床', task_type=TaskType.PERSONALIZED_DECISION,
                                   facts={'bedtime': '23:00', 'sleep_onset_latency': 60})
        first = self.decide(state)
        self.assertEqual((first.action, first.target), ('ASK', 'wake_time'))
        state.record_action(first)
        state.facts['wake_time'] = '07:00'
        self.assertEqual(self.decide(state).action, 'RETRIEVE')
        self.assertEqual(set(state.critical_missing), {'total_sleep_time', 'nighttime_awakenings', 'recent_sleep_pattern'})
        self.assertEqual(state.decision_missing, [])
        state.evidence = ['fixture']
        self.assertEqual(self.decide(state).action, 'ANSWER')
        self.assertIn('不指定具体', state.answer_scope)

    def test_exact_prescription_does_not_use_directional_shortcut(self):
        state = AdaptiveAgentState(goal='请给具体调整上床时间的睡眠限制处方', task_type=TaskType.PERSONALIZED_DECISION,
                                   facts={'bedtime': '23:00', 'sleep_onset_latency': 60, 'wake_time': '07:00'})
        self.assertEqual(self.decide(state).action, 'ASK')
        self.assertNotEqual(state.user_info_sufficiency, 'HIGH')

    def test_explicit_goal_factor_remains_valuable_after_schedule_is_known(self):
        state = AdaptiveAgentState(goal='咖啡影响下是否应该早点上床', task_type=TaskType.PERSONALIZED_DECISION,
                                   facts={'bedtime': '23:00', 'sleep_onset_latency': 60, 'wake_time': '07:00'})
        self.assertEqual(self.decide(state).target, 'caffeine')
        state.facts['caffeine'] = False
        self.assertEqual(self.decide(state).action, 'RETRIEVE')

    def test_resource_requirements_work_independently_of_task_type(self):
        req = RequirementSet((), (), False, resources=('sleep_diary',))
        for task in TaskType:
            state = AdaptiveAgentState(goal='读取已有日记', task_type=task, available_diary=True)
            action = self.decide(state, req)
            self.assertEqual(action.action, 'READ_DIARY')
            self.assertEqual(state.user_info_sufficiency, 'LOW')
            state.record_action(action)
            apply_diary_result(state, DiaryResult({'entries': [{'date': '2026-01-01'}]}, True,
                                                  source_entry_count=1, source_dates=('2026-01-01',),
                                                  date_coverage=('2026-01-01',), provenance={'source': 'test'}))
            self.assertEqual(state.resource_status['sleep_diary'], 'loaded')
            self.assertEqual(state.diary_projection['projection_status'], 'valid')
            self.assertEqual(self.decide(state, req).action, 'ANSWER')

    def test_unavailable_resource_returns_limited_answer_without_retry(self):
        state = AdaptiveAgentState(goal='分析日记', task_type=TaskType.DATA_ANALYSIS)
        state.record_action(self.decide(state))
        apply_diary_result(state, DiaryResult({}, False))
        selected = self.decide(state)
        self.assertEqual(selected.action, 'ANSWER')
        self.assertEqual(selected.expected_benefit, 'MEDIUM')
        self.assertEqual(state.facts, {})
        self.assertEqual(state.user_info_sufficiency, 'LOW')

    def test_question_order_independent_of_requirements_permutation(self):
        req = RequirementSet(('wake_time', 'total_sleep_time', 'recent_sleep_pattern'), (), True)
        for order in permutations(req.critical):
            state = AdaptiveAgentState(goal='了解最近睡眠趋势', task_type=TaskType.PERSONALIZED_DECISION)
            self.assertEqual(self.decide(state, replace(req, critical=order)).target, 'recent_sleep_pattern')

    def test_each_tie_factor_and_final_stable_key(self):
        base = ActionCandidate('ASK', target='a', expected_benefit='HIGH', cost='MEDIUM')
        improvements = ({'goal_relevance': 'HIGH'}, {'decision_impact': 'HIGH'},
                        {'redundancy': 'LOW'}, {'cost': 'LOW'})
        for change in improvements:
            worse = replace(base, redundancy='MEDIUM')
            better = replace(worse, target='z', **change)
            for order in [(worse, better), (better, worse)]:
                chosen = HeuristicDecisionPolicy().choose(AdaptiveAgentState(candidate_actions=list(order)))
                self.assertEqual(chosen.target, 'z')
        for order in [(base, replace(base, target='b')), (replace(base, target='b'), base)]:
            self.assertEqual(HeuristicDecisionPolicy().choose(AdaptiveAgentState(candidate_actions=list(order))).target, 'a')

    def test_known_alternative_and_unanswered_question_not_repeated(self):
        state = AdaptiveAgentState(goal='是否应该早点上床', task_type=TaskType.PERSONALIZED_DECISION,
                                   facts={'bedtime': '23:00', 'sleep_time': '00:00'})
        action = self.decide(state)
        self.assertEqual(action.target, 'wake_time')
        state.record_action(action)
        result = self.decide(state)
        # Step 9.32 R1 makes the independent required evidence dependency
        # actionable even after the personal-fact ASK is unanswered. Preserve
        # the prior bounded-answer assertion in the Step 9.33a regression
        # resolution report as the superseded pre-R1 behavior.
        self.assertEqual(result.action, 'RETRIEVE')
        self.assertEqual(result.gate_decision, 'ACCEPT')
        self.assertIn('wake_time', state.decision_missing)

    def test_more_questions_are_allowed_when_goal_has_more_dependencies(self):
        state = AdaptiveAgentState(goal='最近夜醒和咖啡影响下是否应该早点上床',
                                   task_type=TaskType.PERSONALIZED_DECISION,
                                   facts={'bedtime': '23:00', 'sleep_onset_latency': 60})
        answers = {'wake_time': '07:00', 'nighttime_awakenings': 1,
                   'caffeine': False, 'recent_sleep_pattern': '近两周夜醒'}
        targets = []
        for _ in range(5):
            choice = self.decide(state)
            if choice.action != 'ASK':
                break
            targets.append(choice.target)
            state.record_action(choice)
            state.facts[choice.target] = answers[choice.target]
        self.assertEqual(set(targets), set(answers))
        self.assertEqual(choice.action, 'RETRIEVE')
        self.assertIn('total_sleep_time', state.critical_missing)

    def test_answer_generator_receives_directional_boundary(self):
        from adaptive_agent.answer_generation import LLMAnswerGenerator
        from unittest.mock import Mock
        state = AdaptiveAgentState(goal='是否应该早点上床', task_type=TaskType.PERSONALIZED_DECISION,
                                   facts={'bedtime': '23:00', 'sleep_onset_latency': 60, 'wake_time': '07:00'},
                                   evidence=['fixture'])
        self.assertEqual(self.decide(state).action, 'ANSWER')
        model = Mock()
        model.invoke.return_value.content = 'fixture response'
        model.invoke.return_value.response_metadata = {}
        LLMAnswerGenerator(model).answer(state)
        self.assertIn('不指定具体新上床时间', model.invoke.call_args.args[0][1][1])


if __name__ == '__main__':
    unittest.main()
