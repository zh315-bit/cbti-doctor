"""Synthetic Step 9.6 synchronization and lineage tests; not Benchmark cases."""
from __future__ import annotations

import unittest

from adaptive_agent.candidates import build_candidates
from adaptive_agent.dependency_resolver import DependencyResolver, DependencyType
from adaptive_agent.input_understanding import Understanding
from adaptive_agent.requirements import RequirementSet
from adaptive_agent.runner import AdaptiveAgentLoop
from adaptive_agent.state import AdaptiveAgentState, TaskType
from adaptive_agent.sufficiency import SufficiencyEstimator
from adaptive_agent.tools import DiaryResult, RetrievalResult


class StaticUnderstander:
    def __init__(self, goal, task, facts=None, new=False):
        self.result = Understanding(goal, task, facts or {}, is_new_goal=new)
    def understand(self, _text, _state): return self.result


class Retrieval:
    def __init__(self): self.calls = 0
    def retrieve(self, _query): self.calls += 1; return RetrievalResult(("synthetic evidence",), detail="synthetic")


class Diary:
    def __init__(self, result): self.result, self.calls = result, 0
    def read(self, _requirements): self.calls += 1; return self.result


def loop(goal, task, diary=None, facts=None, new=False):
    return AdaptiveAgentLoop(StaticUnderstander(goal, task, facts, new), Retrieval(), diary or Diary(DiaryResult({}, False)), max_steps=4)


class EffectiveRequirementsLineageTests(unittest.TestCase):
    def test_s1_wrong_personalized_signal_knowledge_retrieves_then_has_no_stale_ask(self):
        result = loop("解释刺激控制的一般原则", TaskType.PERSONALIZED_DECISION).run_turn("synthetic")
        self.assertEqual([x.action for x in result.transitions], ["RETRIEVE", "ANSWER"])
        self.assertEqual(result.state.effective_requirements["decision_fields"], ())
        self.assertTrue(all(x["action"] != "ASK" for x in result.state.action_history))

    def test_s2_directional_goal_retains_validity_critical_wake_time_ask(self):
        result = loop("我应该提前还是推迟上床时间", TaskType.PERSONALIZED_DECISION,
                      facts={"bedtime": "23:00", "sleep_onset_latency": 60}).run_turn("synthetic")
        self.assertEqual(result.status, "ASK")
        self.assertEqual(result.state.action_history[-1]["target"], "wake_time")
        self.assertIn("VALIDITY_STATE", [x["dependency_type"] for x in result.state.dependencies_required])

    def test_s3_supplied_optional_facts_are_retained_without_personal_ask(self):
        facts = {"bedtime": "23:00", "wake_time": "07:00"}
        result = loop("什么是刺激控制？", TaskType.KNOWLEDGE_QA, facts=facts).run_turn("synthetic")
        self.assertEqual(result.status, "ANSWER")
        self.assertEqual(result.state.facts, facts)
        self.assertNotIn("ASK", [x["action"] for x in result.state.action_history])

    def test_s4_new_goal_replaces_effective_requirement_provenance(self):
        state = AdaptiveAgentState(goal="判断是否应该提前上床", task_type=TaskType.PERSONALIZED_DECISION,
                                   goal_id="goal_prior", effective_requirements={"decision_fields": ("wake_time",)})
        result = loop("解释刺激控制", TaskType.KNOWLEDGE_QA, new=True).run_turn("synthetic", state)
        self.assertNotEqual(result.state.goal_id, "goal_prior")
        self.assertEqual(result.state.effective_requirements["decision_fields"], ())

    def test_s5_goal_change_to_personalized_forms_current_decision_requirements(self):
        state = AdaptiveAgentState(goal="解释刺激控制", task_type=TaskType.KNOWLEDGE_QA, goal_id="goal_prior", evidence=["e"])
        result = loop("我应该提前还是推迟上床时间", TaskType.PERSONALIZED_DECISION,
                      facts={"bedtime": "23:00", "sleep_onset_latency": 60}, new=True).run_turn("synthetic", state)
        self.assertEqual(result.status, "ASK")
        self.assertIn("wake_time", result.state.decision_relevant_missing)

    def test_s6_retrieval_lineage_links_required_to_satisfied_dependency(self):
        result = loop("解释刺激控制", TaskType.KNOWLEDGE_QA).run_turn("synthetic")
        pre = next(x for x in result.state_history if x["event"] == "DECISION")["preconditions_considered"][0]
        satisfied = result.state.dependencies_satisfied[0]
        self.assertEqual(pre["source_dependency_id"], satisfied["supersedes_dependency_id"])
        self.assertTrue(result.state.lineage_events[0]["source_action_id"])

    def test_s7_diary_semantics_overrides_wrong_task_signal(self):
        diary = Diary(DiaryResult({"recent_sleep_pattern": [{"date": "2026-01-01"}]}, True,
                                  source_entry_count=1, source_dates=("2026-01-01",), date_coverage=("2026-01-01",), provenance={"source": "synthetic"}))
        result = loop("总结我的睡眠日记趋势", TaskType.KNOWLEDGE_QA, diary).run_turn("synthetic")
        self.assertEqual(result.transitions[0].action, "READ_DIARY")
        self.assertEqual(result.state.dependencies_satisfied[0]["dependency_type"], "RESOURCE")

    def test_s8_optional_missing_does_not_become_ask(self):
        state = AdaptiveAgentState(goal="概述规律作息的意义", task_type=TaskType.KNOWLEDGE_QA)
        req = RequirementSet((), ("caffeine",), False, decision_fields=())
        SufficiencyEstimator().update(state, req)
        candidates = build_candidates(state, req)
        self.assertNotIn("ASK", [item.action for item in candidates])
        self.assertIn("caffeine", state.secondary_missing)

    def test_s9_same_field_criticality_is_goal_dependent(self):
        educational = AdaptiveAgentState(goal="规律起床时间为什么重要", task_type=TaskType.KNOWLEDGE_QA)
        directional = AdaptiveAgentState(goal="我应该提前还是推迟上床时间", task_type=TaskType.PERSONALIZED_DECISION)
        req = RequirementSet(("wake_time",), (), False)
        SufficiencyEstimator().update(educational, req); SufficiencyEstimator().update(directional, req)
        self.assertFalse(any(x.dependency_type is DependencyType.VALIDITY_STATE for x in DependencyResolver().resolve(educational, req)))
        self.assertTrue(any(x.dependency_type is DependencyType.VALIDITY_STATE for x in DependencyResolver().resolve(directional, req)))

    def test_s10_mandatory_precondition_survives_prior_asks(self):
        state = AdaptiveAgentState(action_history=[{"action": "ASK", "target": "caffeine"}] * 5)
        result = loop("解释刺激控制", TaskType.KNOWLEDGE_QA).run_turn("synthetic", state)
        self.assertEqual(result.transitions[0].action, "RETRIEVE")

    def test_s11_optional_medium_information_retains_optional_origin(self):
        state = AdaptiveAgentState(goal="比较咖啡因影响", task_type=TaskType.PERSONALIZED_DECISION,
                                   decision_missing=["caffeine"], decision_relevant_missing=["caffeine"])
        req = RequirementSet((), ("caffeine",), False, decision_fields=("caffeine",),
                             requirement_ids={"caffeine": "req_goal_caffeine"}, classifications={"caffeine": "useful_optional"})
        candidates = build_candidates(state, req)
        ask = next(x for x in candidates if x.action == "ASK")
        self.assertEqual(ask.origin, "OPTIONAL_ACQUISITION")
        self.assertEqual(ask.source_requirement_id, "req_goal_caffeine")
        self.assertIsNone(ask.source_precondition_id)

    def test_s12_invalid_diary_has_tool_to_state_lineage_without_facts(self):
        diary = Diary(DiaryResult({"recent_sleep_pattern": ["summary"]}, True, kind="SUMMARY_SHAPED", summary_semantics="aggregate"))
        result = loop("分析我的睡眠日记", TaskType.DATA_ANALYSIS, diary).run_turn("synthetic")
        self.assertEqual(result.state.diary_projection["projection_status"], "invalid")
        self.assertNotIn("recent_sleep_pattern", result.state.facts)
        self.assertEqual(result.state.lineage_events[0]["tool"], "READ_DIARY")


if __name__ == "__main__": unittest.main()
