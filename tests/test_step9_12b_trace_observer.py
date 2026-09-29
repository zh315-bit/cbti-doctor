"""Focused Step 9.12b observer tests; no Flask model, Benchmark, or network."""
from __future__ import annotations

from copy import deepcopy
import unittest

from adaptive_agent.state import AdaptiveAgentState, TaskType
from scripts.preflight_step9_12_local import _lineage_validation


def forced_retrieval_fixture():
    state = AdaptiveAgentState(
        goal="解释一般睡眠规律", task_type=TaskType.KNOWLEDGE_QA,
        goal_id="goal_test", semantic_provenance=[{"semantic_id": "sem_test"}],
        action_history=[
            {"action_id": "act_retrieve", "selected_candidate_id": "cand_retrieve", "action": "RETRIEVE"},
            {"action_id": "act_answer", "selected_candidate_id": "cand_answer", "action": "ANSWER"},
        ],
        # These final per-revision views deliberately do not retain the older
        # hard-precondition candidate.  History is the durable observer source.
        preconditions_considered=[], considered_information=[],
        lineage_events=[{
            "tool_result_id": "tool_retrieve", "state_update_id": "upd_retrieve",
            "source_action_id": "act_retrieve", "source_tool_result_id": "tool_retrieve",
        }],
    )
    history = [
        {
            "event": "DECISION", "goal_id": "goal_test",
            "semantic_provenance": [{"semantic_id": "sem_test"}],
            "dependencies_considered": [{"dependency_id": "dep_evidence"}],
            "chosen_action": {
                "action": "RETRIEVE", "candidate_id": "cand_retrieve",
                "origin": "HARD_PRECONDITION", "source_dependency_id": "dep_evidence",
                "source_precondition_id": "pre_evidence",
            },
        },
        {
            "event": "DECISION", "goal_id": "goal_test",
            "semantic_provenance": [{"semantic_id": "sem_test"}],
            "dependencies_considered": [{"dependency_id": "dep_evidence", "status": "SATISFIED"}],
            "chosen_action": {
                "action": "ANSWER", "candidate_id": "cand_answer",
                "origin": "OPTIONAL_ACQUISITION", "source_dependency_id": "dep_evidence",
                "source_precondition_id": None,
            },
        },
    ]
    return state, history


class Step912bTraceObserverTests(unittest.TestCase):
    def test_t1_recovers_candidate_from_history_when_final_state_has_none(self):
        state, history = forced_retrieval_fixture()
        result = _lineage_validation(state, history)
        self.assertTrue(result["ready"])
        self.assertEqual(result["actions"][0]["candidate_id"], "cand_retrieve")
        self.assertTrue(result["actions"][0]["candidate_history_found"])

    def test_t2_satisfied_answer_without_active_precondition_is_valid(self):
        state, history = forced_retrieval_fixture()
        result = _lineage_validation(state, history)
        answer = result["actions"][1]
        self.assertIsNone(answer["precondition_id"])
        self.assertEqual(answer["lineage_shape"], "POLICY_SELECTED_ACTION")
        self.assertTrue(result["ready"])

    def test_t3_precondition_forced_action_requires_precondition_id(self):
        state, history = forced_retrieval_fixture()
        history[0]["chosen_action"]["source_precondition_id"] = None
        result = _lineage_validation(state, history)
        self.assertFalse(result["ready"])
        self.assertIn("precondition_id", [item["missing"] for item in result["missing_required_lineage"]])

    def test_t4_policy_selected_action_requires_real_candidate_id(self):
        state, history = forced_retrieval_fixture()
        state.action_history[1]["selected_candidate_id"] = None
        result = _lineage_validation(state, history)
        self.assertFalse(result["ready"])
        self.assertTrue(result["candidate_lineage_missing"])

    def test_t5_tool_action_requires_tool_result_and_state_update(self):
        state, history = forced_retrieval_fixture()
        state.lineage_events = []
        result = _lineage_validation(state, history)
        missing = [item["missing"] for item in result["missing_required_lineage"]]
        self.assertIn("tool_result_id", missing)
        self.assertIn("state_update_id", missing)

    def test_t6_observer_never_creates_fake_lineage_ids(self):
        state, history = forced_retrieval_fixture()
        state.action_history[1]["selected_candidate_id"] = None
        result = _lineage_validation(state, history)
        self.assertFalse(result["fake_lineage_ids_created"])
        self.assertIsNone(result["actions"][1]["candidate_id"])

    def test_t7_missing_required_lineage_fails_closed(self):
        state, history = forced_retrieval_fixture()
        for snapshot in history:
            snapshot["dependencies_considered"] = []
        result = _lineage_validation(state, history)
        self.assertFalse(result["ready"])
        self.assertIn("dependency_lineage", [item["missing"] for item in result["missing_required_lineage"]])

    def test_t8_observer_does_not_change_action_path_or_state(self):
        state, history = forced_retrieval_fixture()
        before_state, before_history = deepcopy(state), deepcopy(history)
        _lineage_validation(state, history)
        self.assertEqual(state, before_state)
        self.assertEqual(history, before_history)
        self.assertEqual([item["action"] for item in state.action_history], ["RETRIEVE", "ANSWER"])


if __name__ == "__main__":
    unittest.main()
