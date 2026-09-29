import unittest

from adaptive_agent.answer_generation import authorize_final_answer
from adaptive_agent.candidates import generate_candidates
from adaptive_agent.dependency_resolver import DependencyResolver
from adaptive_agent.input_understanding import Understanding
from adaptive_agent.requirements import RequirementSet, synchronize_requirements
from adaptive_agent.runner import AdaptiveAgentLoop
from adaptive_agent.state import AdaptiveAgentState, TaskType
from adaptive_agent.sufficiency import SufficiencyEstimator
from adaptive_agent.acquisition_gate import gate_acquisition_candidates
from adaptive_agent.tools import DiaryResult, RetrievalResult


def _requirements(fields=(), *, evidence=False, classes=None, scope="仅在已知事实和证据范围内回答；不得推断未知事实。"):
    return RequirementSet((), (), evidence, decision_fields=tuple(fields), answer_scope=scope,
                         precondition_classes=classes or {})


def _authorize(*, status=None, estimate=None, fields=("choice_factor",), fallback="bounded general response",
               evidence_status=None, fact_value=None):
    state = AdaptiveAgentState(
        goal="synthetic personalized choice",
        task_type=TaskType.PERSONALIZED_DECISION,
        decision_missing=list(fields) if fact_value is None else [],
        decision_relevant_missing=list(fields) if fact_value is None else [],
        facts={} if fact_value is None else {fields[0]: fact_value},
        fact_status={} if status is None else {fields[0]: status},
        information_estimates={} if estimate is None else {fields[0]: estimate},
        dependencies_considered=[],
    )
    if fact_value is not None and status == "ASSERTED":
        state.fact_sources[fields[0]] = {"source_type": "user_explicit"}
    state.dependencies_considered.append({
        "dependency_type": "USER_FACTS", "target": "user_facts",
        "status": "DEFERRED" if fact_value is None else "SATISFIED",
        "fallback": fallback,
    })
    if evidence_status:
        state.dependencies_considered.append({
            "dependency_type": "EVIDENCE", "target": "external_evidence",
            "status": evidence_status, "fallback": "general explanation",
        })
    if fact_value is None and status in {"DEFERRED", "UNKNOWN", "UNAVAILABLE", "INVALID"}:
        state.target_status[fields[0]] = {"status": status}
    requirements = _requirements(fields, evidence=bool(evidence_status))
    # Direct fixtures declare a matched goal-to-fact value estimate, as the
    # production candidate stage does before final answer authorization.
    return state, requirements, authorize_final_answer(state, requirements)


class _Understanding:
    def __init__(self, goal, task_type):
        self.goal = goal
        self.task_type = task_type

    def understand(self, user_input, prior_state=None):
        return Understanding(self.goal, self.task_type, {})


class _Retrieval:
    def __init__(self):
        self.calls = []

    def retrieve(self, query):
        self.calls.append(query)
        return RetrievalResult(("synthetic evidence item",), True, "synthetic retrieval")


class _Diary:
    def read(self, requirements):
        return DiaryResult({}, False, "synthetic no diary")


class _Answer:
    def __init__(self):
        self.calls = 0

    def answer(self, state, limitation=None):
        self.calls += 1
        return "synthetic full answer"


class Step942AnswerAuthorizationTests(unittest.TestCase):
    def test_t1_required_evidence_and_unrelated_optional_fact_do_not_force_ask(self):
        state = AdaptiveAgentState(goal="explain synthetic topic", task_type=TaskType.KNOWLEDGE_QA,
                                   decision_missing=["unrelated_preference"])
        req = _requirements(("unrelated_preference",), evidence=True)
        SufficiencyEstimator().update(state, req)
        deps = DependencyResolver().resolve(state, req)
        state.dependencies_considered = [item.to_dict() for item in deps]
        effective = synchronize_requirements(req, state, deps)
        candidates = gate_acquisition_candidates(state, effective, generate_candidates(state, effective))
        self.assertIn("RETRIEVE", [item.action for item in candidates])
        self.assertNotIn("ASK", [item.action for item in candidates])
        evidence_dep = next(item for item in state.dependencies_considered if item["dependency_type"] == "EVIDENCE")
        self.assertEqual(evidence_dep["status"], "REQUIRED")

    def test_t2_evidence_does_not_authorize_missing_safety_fact(self):
        state, req, result = _authorize(status="UNKNOWN",
            estimate={"decision_impact": "decision_changing"}, evidence_status="SATISFIED")
        self.assertEqual(result["status"], "AUTHORIZED_BOUNDED")
        self.assertIn("choice_factor", result["material_missing"])

    def test_t3_detail_only_missing_fact_allows_bounded_answer(self):
        _, _, result = _authorize(status="UNKNOWN",
            estimate={"decision_impact": "detail_improving"})
        self.assertEqual(result["status"], "AUTHORIZED_BOUNDED")
        self.assertEqual(result["material_missing"], [])
        self.assertEqual(result["detail_missing"], ["choice_factor"])

    def test_t4_asserted_required_fact_allows_full_answer(self):
        _, _, result = _authorize(status="ASSERTED",
            estimate={"decision_impact": "decision_changing"}, fact_value="synthetic value")
        self.assertEqual(result["status"], "AUTHORIZED_FULL")

    def test_t5_deferred_and_unknown_are_not_satisfied(self):
        for status in ("DEFERRED", "UNKNOWN"):
            with self.subTest(status=status):
                _, _, result = _authorize(status=status,
                    estimate={"decision_impact": "decision_changing"})
                self.assertEqual(result["status"], "AUTHORIZED_BOUNDED")
                self.assertIn("choice_factor", result["material_missing"])

    def test_t6_unavailable_uses_safe_fallback_without_ask_loop(self):
        state, req, result = _authorize(status="UNAVAILABLE",
            estimate={"decision_impact": "decision_changing"})
        self.assertEqual(result["status"], "AUTHORIZED_BOUNDED")
        state.action_history.append({"action": "ASK", "target": "choice_factor"})
        from adaptive_agent.candidates import ask_is_eligible
        self.assertFalse(ask_is_eligible(state, "choice_factor"))

    def test_r1_resource_acquisition_remains_independent_from_answer_gate(self):
        retrieval = _Retrieval()
        answer = _Answer()
        loop = AdaptiveAgentLoop(_Understanding("explain general synthetic topic", TaskType.KNOWLEDGE_QA),
                                 retrieval, _Diary(), answer_generator=answer, max_steps=3)
        result = loop.run_turn("synthetic request")
        self.assertEqual([item.action for item in result.transitions], ["RETRIEVE", "ANSWER"])
        self.assertEqual(retrieval.calls, ["explain general synthetic topic"])
        self.assertEqual(result.state_history[-2]["answer_authorization"]["status"], "AUTHORIZED_FULL")

    def test_r2_optional_low_value_ask_remains_suppressed_with_answer_gate(self):
        state = AdaptiveAgentState(goal="synthetic general topic", task_type=TaskType.KNOWLEDGE_QA,
                                   decision_missing=["format_preference"])
        req = _requirements((), evidence=False)
        result = authorize_final_answer(state, req)
        self.assertEqual(result["status"], "AUTHORIZED_FULL")
        self.assertNotIn("format_preference", result["material_missing"])

    def test_r3_unknown_deferred_and_unavailable_never_authorize_full(self):
        for status in ("UNKNOWN", "DEFERRED", "UNAVAILABLE"):
            with self.subTest(status=status):
                _, _, result = _authorize(status=status,
                    estimate={"decision_impact": "answer_scope_changing"})
                self.assertNotEqual(result["status"], "AUTHORIZED_FULL")

    def test_retrieve_state_projection_then_authorization_is_traced(self):
        answer = _Answer()
        loop = AdaptiveAgentLoop(_Understanding("explain general synthetic topic", TaskType.KNOWLEDGE_QA),
                                 _Retrieval(), _Diary(), answer_generator=answer, max_steps=3)
        result = loop.run_turn("synthetic request")
        retrieve_snapshot = next(item for item in result.state_history if item["event"] == "RETRIEVE")
        self.assertEqual(retrieve_snapshot["dependencies_satisfied"][0]["dependency_type"], "EVIDENCE")
        decision = next(item for item in result.state_history
                        if item["event"] == "DECISION" and item.get("answer_authorization"))
        self.assertEqual(decision["answer_authorization"]["status"], "AUTHORIZED_FULL")

    def test_ask_then_asserted_state_update_allows_authorization(self):
        state, req, blocked = _authorize(status="UNKNOWN",
            estimate={"decision_impact": "decision_changing"})
        self.assertEqual(blocked["status"], "AUTHORIZED_BOUNDED")
        state.facts["choice_factor"] = "synthetic asserted value"
        state.fact_status["choice_factor"] = "ASSERTED"
        state.fact_sources["choice_factor"] = {"source_type": "user_explicit"}
        state.target_status["choice_factor"] = {"status": "ASSERTED"}
        state.information_estimates["choice_factor"] = {"decision_impact": "decision_changing"}
        result = authorize_final_answer(state, req)
        self.assertEqual(result["status"], "AUTHORIZED_FULL")

    def test_unavailable_dependency_uses_bounded_fallback(self):
        _, _, result = _authorize(status="UNAVAILABLE",
            estimate={"decision_impact": "decision_changing"})
        self.assertEqual(result["status"], "AUTHORIZED_BOUNDED")

    def test_deferred_personalization_never_reaches_full_answer(self):
        _, _, result = _authorize(status="DEFERRED",
            estimate={"decision_impact": "decision_changing"}, evidence_status="SATISFIED")
        self.assertNotEqual(result["status"], "AUTHORIZED_FULL")

    def test_invalid_conflicting_state_cannot_authorize_full(self):
        state, req, _ = _authorize(status="INVALID",
            estimate={"decision_impact": "decision_changing"})
        state.fact_conflicts["choice_factor"] = [{"source": "synthetic"}]
        result = authorize_final_answer(state, req)
        self.assertNotEqual(result["status"], "AUTHORIZED_FULL")

    def test_blocked_needs_information_is_distinct_when_no_fallback_but_acquisition_exists(self):
        state = AdaptiveAgentState(
            goal="synthetic material decision", task_type=TaskType.PERSONALIZED_DECISION,
            decision_missing=["choice_factor"], decision_relevant_missing=["choice_factor"],
            information_estimates={"choice_factor": {"decision_impact": "decision_changing"}},
            dependencies_considered=[{
                "dependency_type": "VALIDITY_STATE", "target": "choice_factor",
                "status": "REQUIRED", "fallback": None,
            }],
        )
        req = _requirements(("choice_factor",), scope="")
        result = authorize_final_answer(state, req)
        self.assertEqual(result["status"], "BLOCKED_NEEDS_INFORMATION")

    def test_blocked_unsafe_or_invalid_is_distinct_when_no_fallback_or_acquisition(self):
        state = AdaptiveAgentState(
            goal="synthetic material decision", task_type=TaskType.PERSONALIZED_DECISION,
            decision_missing=["choice_factor"], decision_relevant_missing=["choice_factor"],
            fact_status={"choice_factor": "INVALID"},
            target_status={"choice_factor": {"status": "INVALID"}},
            fact_conflicts={"choice_factor": [{"source": "synthetic"}]},
            information_estimates={"choice_factor": {"decision_impact": "decision_changing"}},
            dependencies_considered=[{
                "dependency_type": "VALIDITY_STATE", "target": "choice_factor",
                "status": "INVALID", "fallback": None,
            }],
        )
        req = _requirements(("choice_factor",), scope="")
        result = authorize_final_answer(state, req)
        self.assertEqual(result["status"], "BLOCKED_UNSAFE_OR_INVALID")


if __name__ == "__main__":
    unittest.main()
