"""Synthetic-only tests for V3 authorization trace lineage."""
import unittest

from adaptive_agent.runner import LoopResult
from adaptive_agent.state import AdaptiveAgentState
from evaluation.v3_trace_adapter import build_v3_trace, validate_authorization_mirrors
from evaluation.recorder import serialize_state


def authorization(mode="AUTHORIZED_FULL"):
    bounded = mode == "AUTHORIZED_BOUNDED"
    return {
        "status": mode,
        "answer_authorization_mode": mode,
        "answer_authorization_reason_codes": ["UNSUPPORTED_SCOPE_EXCLUDED"] if bounded else ["ALL_MATERIAL_REQUIREMENTS_SATISFIED"],
        "blocked_dependency_ids": ["dep_synthetic"] if bounded else [],
        "blocked_precondition_ids": [],
        "bounded_excluded_actions": ["individualized_action:synthetic_field"] if bounded else [],
        "bounded_supported_content_basis": ["fact:known_constraint"] if bounded else [],
        "authorization_decision_source": "synthetic_authorization_fixture",
        "authorization_decision_version": "step9_50_authorization_trace_v1",
        "material_missing": ["synthetic_field"] if bounded else [],
    }


def trace_for(auth=None):
    auth = auth or authorization()
    state = AdaptiveAgentState(goal="synthetic goal", facts={"known_constraint": "synthetic fact"},
                              evidence=["synthetic evidence"])
    state.answer_context_audit = {"final_answer_authorization": auth,
        "answer_generation_outcome": "GENERATED_BOUNDED" if auth["status"] == "AUTHORIZED_BOUNDED" else "GENERATED_FULL",
        "bounded_contract_validation": "PASS" if auth["status"] == "AUTHORIZED_BOUNDED" else "NOT_APPLICABLE",
        "generated_content_basis_ids": list(auth["bounded_supported_content_basis"]),
        "terminal_response_kind": "BOUNDED_ANSWER" if auth["status"] == "AUTHORIZED_BOUNDED" else "FULL_ANSWER"}
    history = [{"event": "DECISION", "answer_authorization": auth},
               {"event": "ANSWER", "answer_authorization": auth}]
    return LoopResult(state, "ANSWER", "synthetic response", 1, state_history=history)


class Step950TraceabilityTests(unittest.TestCase):
    def test_t31_authorization_is_mirrored_decision_terminal_and_final_state(self):
        trace = build_v3_trace(trace_for())
        decision = trace["state_history"][0]["answer_authorization"]
        self.assertEqual(trace["state_history"][-1]["answer_authorization"], decision)
        self.assertEqual(trace["final_state"]["answer_authorization"], decision)

    def test_t32_blocked_ids_are_present_and_deterministic(self):
        auth = authorization("AUTHORIZED_BOUNDED")
        trace = build_v3_trace(trace_for(auth))
        mirrored = trace["final_state"]["answer_authorization"]
        self.assertEqual(mirrored["blocked_dependency_ids"], ["dep_synthetic"])
        self.assertEqual(mirrored["blocked_precondition_ids"], [])

    def test_t33_bounded_basis_references_existing_sources(self):
        trace = build_v3_trace(trace_for(authorization("AUTHORIZED_BOUNDED")))
        basis = trace["final_state"]["answer_authorization"]["bounded_supported_content_basis"]
        self.assertTrue(all(item == "fact:known_constraint" for item in basis))

    def test_t34_missing_source_or_version_fails_trace_schema(self):
        auth = authorization()
        auth.pop("authorization_decision_version")
        result = trace_for(auth)
        with self.assertRaises(ValueError):
            build_v3_trace(result)

    def test_t35_weak_bounded_generation_is_distinct_from_safety_block(self):
        trace = build_v3_trace(trace_for(authorization("AUTHORIZED_BOUNDED")))
        outcome = trace["final_state"]["answer_generation_audit"]["answer_generation_outcome"]
        self.assertEqual(outcome, "GENERATED_BOUNDED")
        blocked = authorization("BLOCKED_UNSAFE_OR_INVALID")
        blocked_trace = trace_for(blocked)
        blocked_trace.state.answer_context_audit["answer_generation_outcome"] = "NOT_GENERATED_BLOCKED"
        blocked_trace.state_history[-1]["event"] = "ANSWER"
        blocked_trace.state_history[-1]["answer_authorization"] = blocked
        blocked_trace.state_history[0]["answer_authorization"] = blocked
        rendered = build_v3_trace(blocked_trace)
        self.assertNotEqual(outcome, rendered["final_state"]["answer_generation_audit"]["answer_generation_outcome"])

    def test_t36_production_sources_have_no_benchmark_case_branches(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        files = [root / "adaptive_agent/answer_generation.py", root / "adaptive_agent/runner.py",
                 root / "evaluation/recorder.py", root / "evaluation/v3_trace_adapter.py"]
        source = "\n".join(path.read_text(encoding="utf-8") for path in files)
        self.assertNotRegex(source, r"V4-(?:KQ|CA|PD|DA)-\d+")
        self.assertNotRegex(source, r"step9_49.*(?:case|recovery)")

    def test_t37_user_constraints_survive_bounded_projection(self):
        from adaptive_agent.answer_generation import build_answer_context
        result = trace_for(authorization("AUTHORIZED_BOUNDED"))
        result.state.fact_sources["known_constraint"] = {"source_type": "user_explicit"}
        context = build_answer_context(result.state)
        self.assertEqual(context["user_facts"]["known_constraint"]["value"], "synthetic fact")

    def test_t38_conflicting_material_state_is_blocked(self):
        from adaptive_agent.answer_generation import authorize_final_answer
        from adaptive_agent.requirements import RequirementSet
        state = trace_for().state
        state.decision_missing = ["choice"]
        state.information_estimates = {"choice": {"decision_impact": "decision_changing"}}
        state.fact_status = {"choice": "INVALID"}
        state.target_status = {"choice": {"status": "INVALID"}}
        state.fact_conflicts = {"choice": [{"source": "synthetic"}]}
        state.dependencies_considered = [{"dependency_id": "dep_choice", "dependency_type": "USER_FACTS",
            "target": "choice", "status": "INVALID", "requiredness": "required", "fallback": "bounded"}]
        req = RequirementSet((), (), False, decision_fields=("choice",), answer_scope="synthetic bounded scope")
        self.assertEqual(authorize_final_answer(state, req)["status"], "BLOCKED_UNSAFE_OR_INVALID")

    def test_t39_exhausted_optional_ask_does_not_remove_safe_bounded_mode(self):
        from adaptive_agent.answer_generation import authorize_final_answer
        from adaptive_agent.requirements import RequirementSet
        state = trace_for(authorization("AUTHORIZED_BOUNDED")).state
        state.dependencies_considered = [{"dependency_id": "dep_optional", "dependency_type": "USER_FACTS",
            "target": "optional", "status": "DEFERRED", "requiredness": "optional", "fallback": None}]
        state.action_history = [{"action": "ASK", "target": "optional"}]
        req = RequirementSet((), (), False, decision_fields=(), answer_scope="synthetic scope")
        self.assertEqual(authorize_final_answer(state, req)["status"], "AUTHORIZED_FULL")

    def test_t40_mutated_final_state_mirror_fails_closed(self):
        trace = build_v3_trace(trace_for())
        trace["final_state"]["answer_authorization"]["authorization_decision_version"] = "mutated"
        with self.assertRaises(ValueError):
            validate_authorization_mirrors(trace)


if __name__ == "__main__":
    unittest.main()
