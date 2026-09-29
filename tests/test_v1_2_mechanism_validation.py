"""Controlled, non-Benchmark validation for the V1.2 information-value mechanism."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
import unittest

from adaptive_agent.candidates import build_candidates
from adaptive_agent.information_value import estimate_information_value
from adaptive_agent.policy import HeuristicDecisionPolicy
from adaptive_agent.requirements import RequirementSet
from adaptive_agent.state import AdaptiveAgentState, TaskType
from adaptive_agent.sufficiency import SufficiencyEstimator


ROOT = Path(__file__).resolve().parents[1]
TRACE_PATH = ROOT / "evaluation/v1_2/step8_3_mechanism_traces.jsonl"


def asks(n: int) -> list[dict[str, str]]:
    return [{"action": "ASK", "target": f"prior_{index}"} for index in range(n)]


def evaluate(case_id: str, expected: str, state: AdaptiveAgentState,
             requirements: RequirementSet, target: str, predicate) -> dict:
    SufficiencyEstimator().update(state, requirements)
    estimate = estimate_information_value(state, target, requirements)
    state.candidate_actions = build_candidates(state, requirements)
    selected = HeuristicDecisionPolicy().choose(state)
    record = {
        "scenario": case_id,
        "expected_behavior": expected,
        "considered_information": state.considered_information,
        "target": target,
        "information_value": estimate.to_dict(),
        "decision_impact": estimate.decision_impact,
        "acquisition_cost": estimate.acquisition_cost,
        "resource_alternative": estimate.resource_alternative,
        "candidate_actions": [asdict(candidate) for candidate in state.candidate_actions],
        "rejected_information": state.rejected_information,
        "selected_action": asdict(selected),
        "stop_reason": state.stop_reason,
        "missing_information": {"required": state.required_missing, "decision": state.decision_missing,
                                "secondary": state.secondary_missing},
    }
    record["pass"] = bool(predicate(record))
    return record


class V12MechanismValidationTests(unittest.TestCase):
    def test_controlled_information_value_scenarios(self):
        cases = [
            ("A_missing_irrelevant", "irrelevant missing field is NONE and does not produce ASK",
             AdaptiveAgentState(goal="解释刺激控制", task_type=TaskType.KNOWLEDGE_QA),
             RequirementSet((), (), False), "exercise",
             lambda r: r["information_value"]["value_level"] == "NONE" and r["selected_action"]["action"] == "ANSWER"),
            ("B_detail_only", "detail-only secondary gap is LOW and permits bounded ANSWER",
             AdaptiveAgentState(goal="解释刺激控制", task_type=TaskType.KNOWLEDGE_QA),
             RequirementSet((), ("caffeine",), False), "caffeine",
             lambda r: r["information_value"]["value_level"] == "LOW" and r["selected_action"]["action"] == "ANSWER"),
            ("C_scope_changing", "a MEDIUM scope-changing gap may ASK early",
             AdaptiveAgentState(goal="比较睡眠模式", task_type=TaskType.PERSONALIZED_DECISION),
             RequirementSet(("perceived_stress",), (), False, decision_fields=("perceived_stress",)), "perceived_stress",
             lambda r: r["information_value"]["value_level"] == "MEDIUM" and r["selected_action"]["action"] == "ASK"),
            ("D_decision_changing", "a HIGH timing gap remains eligible for ASK",
             AdaptiveAgentState(goal="是否应该调整起床时间", task_type=TaskType.PERSONALIZED_DECISION),
             RequirementSet(("wake_time",), (), False), "wake_time",
             lambda r: r["information_value"]["value_level"] == "HIGH" and r["selected_action"]["action"] == "ASK"),
            ("E_approximate_sufficient", "approximate known timing does not invite precision ASK",
             AdaptiveAgentState(goal="是否应该早点上床", task_type=TaskType.PERSONALIZED_DECISION,
                                facts={"bedtime":"23:00", "sleep_onset_latency":{"value":60,"uncertainty":"approximate"}, "wake_time":"07:00"}),
             RequirementSet(("bedtime", "sleep_onset_latency", "wake_time"), (), False), "sleep_onset_latency",
             lambda r: r["information_value"]["value_level"] == "NONE" and r["selected_action"]["action"] == "ANSWER"),
            ("F_range_sufficient", "a range fact does not invite an exact-value ASK",
             AdaptiveAgentState(goal="是否应该早点上床", task_type=TaskType.PERSONALIZED_DECISION,
                                facts={"bedtime":"23:00", "sleep_onset_latency":60, "wake_time":{"low":"07:00","high":"08:00","uncertainty":"range"}}),
             RequirementSet(("bedtime", "sleep_onset_latency", "wake_time"), (), False), "wake_time",
             lambda r: r["information_value"]["value_level"] == "NONE" and r["selected_action"]["action"] == "ANSWER"),
            ("G_semantic_repeat", "an equivalent previous ASK is NONE and cannot repeat",
             AdaptiveAgentState(goal="比较入睡时间", task_type=TaskType.PERSONALIZED_DECISION,
                                action_history=[{"action":"ASK","target":"sleep_time"}]),
             RequirementSet(("sleep_onset_latency",), (), False), "sleep_onset_latency",
             lambda r: r["information_value"]["value_level"] == "NONE" and r["selected_action"]["action"] == "ANSWER"),
            ("H_diary_alternative", "authorized unread diary is preferred over user ASK",
             AdaptiveAgentState(goal="读取日记中的起床时间", task_type=TaskType.DATA_ANALYSIS, available_diary=True),
             RequirementSet(("wake_time",), (), False, resources=("sleep_diary",)), "wake_time",
             lambda r: r["resource_alternative"] and r["selected_action"]["action"] == "READ_DIARY"),
            ("I_diary_unavailable", "unavailable diary does not retry and gives a bounded ANSWER",
             AdaptiveAgentState(goal="分析睡眠日记", task_type=TaskType.DATA_ANALYSIS,
                                resource_status={"sleep_diary":"unavailable"}),
             RequirementSet((), (), False, resources=("sleep_diary",)), "sleep_diary",
             lambda r: r["selected_action"]["action"] == "ANSWER" and not any(c["action"] == "READ_DIARY" for c in r["candidate_actions"])),
            ("J_high_after_five", "HIGH decision-changing information survives five prior ASK actions",
             AdaptiveAgentState(goal="是否应该调整起床时间", task_type=TaskType.PERSONALIZED_DECISION, action_history=asks(5)),
             RequirementSet(("wake_time",), (), False), "wake_time",
             lambda r: r["information_value"]["value_level"] == "HIGH" and r["selected_action"]["action"] == "ASK"),
            ("K_medium_after_three", "MEDIUM information is rejected after diminishing return raises threshold",
             AdaptiveAgentState(goal="比较睡眠模式", task_type=TaskType.PERSONALIZED_DECISION, action_history=asks(3)),
             RequirementSet(("perceived_stress",), (), False, decision_fields=("perceived_stress",)), "perceived_stress",
             lambda r: r["information_value"]["value_level"] == "MEDIUM" and r["selected_action"]["action"] == "ANSWER" and r["stop_reason"]),
            ("L_bounded_stop", "missing information with no worthwhile acquisition ends in bounded ANSWER",
             AdaptiveAgentState(goal="比较咖啡因影响", task_type=TaskType.PERSONALIZED_DECISION,
                                action_history=[{"action":"ASK","target":"caffeine"}]),
             RequirementSet(("caffeine",), (), False, decision_fields=("caffeine",)), "caffeine",
             lambda r: r["missing_information"]["decision"] and r["selected_action"]["action"] == "ANSWER" and r["stop_reason"]),
            ("M_medium_ask_0", "MEDIUM value clears the initial acquisition threshold",
             AdaptiveAgentState(goal="比较睡眠模式", task_type=TaskType.PERSONALIZED_DECISION),
             RequirementSet(("perceived_stress",), (), False, decision_fields=("perceived_stress",)), "perceived_stress",
             lambda r: r["selected_action"]["action"] == "ASK"),
            ("M_medium_ask_1", "MEDIUM value clears the threshold after one ASK",
             AdaptiveAgentState(goal="比较睡眠模式", task_type=TaskType.PERSONALIZED_DECISION, action_history=asks(1)),
             RequirementSet(("perceived_stress",), (), False, decision_fields=("perceived_stress",)), "perceived_stress",
             lambda r: r["selected_action"]["action"] == "ASK"),
            ("M_medium_ask_3", "MEDIUM value is rejected after three ASK actions",
             AdaptiveAgentState(goal="比较睡眠模式", task_type=TaskType.PERSONALIZED_DECISION, action_history=asks(3)),
             RequirementSet(("perceived_stress",), (), False, decision_fields=("perceived_stress",)), "perceived_stress",
             lambda r: r["selected_action"]["action"] == "ANSWER" and r["stop_reason"]),
            ("M_medium_ask_5", "MEDIUM value remains rejected after five ASK actions",
             AdaptiveAgentState(goal="比较睡眠模式", task_type=TaskType.PERSONALIZED_DECISION, action_history=asks(5)),
             RequirementSet(("perceived_stress",), (), False, decision_fields=("perceived_stress",)), "perceived_stress",
             lambda r: r["selected_action"]["action"] == "ANSWER" and r["stop_reason"]),
            ("N_counterfactual_A", "the same caffeine gap is detail-only for general education",
             AdaptiveAgentState(goal="解释刺激控制", task_type=TaskType.KNOWLEDGE_QA),
             RequirementSet((), ("caffeine",), False), "caffeine",
             lambda r: r["information_value"]["value_level"] == "LOW" and r["selected_action"]["action"] == "ANSWER"),
            ("N_counterfactual_B", "the same caffeine gap is HIGH when the current goal explicitly turns on it",
             AdaptiveAgentState(goal="咖啡因会不会影响我今晚入睡", task_type=TaskType.PERSONALIZED_DECISION),
             RequirementSet(("caffeine",), (), False, decision_fields=("caffeine",)), "caffeine",
             lambda r: r["information_value"]["value_level"] == "HIGH" and r["selected_action"]["action"] == "ASK"),
        ]
        traces = [evaluate(*case) for case in cases]
        TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
        TRACE_PATH.write_text("".join(json.dumps(trace, ensure_ascii=False) + "\n" for trace in traces), encoding="utf-8")
        self.assertEqual(len(traces), 18)
        self.assertTrue(all("information_value" in trace and "selected_action" in trace for trace in traces))


if __name__ == "__main__":
    unittest.main()
