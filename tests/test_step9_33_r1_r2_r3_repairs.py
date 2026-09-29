"""Synthetic architecture regressions for Step 9.33 (no benchmark fixtures)."""
import unittest
from adaptive_agent.answer_generation import build_answer_context
from adaptive_agent.candidates import ask_is_eligible, generate_candidates
from adaptive_agent.dependency_resolver import DependencyResolver
from adaptive_agent.input_understanding import apply_understanding, understanding_from_mapping
from adaptive_agent.preconditions import evaluate_preconditions
from adaptive_agent.requirements import RequirementSet, requirement_is_known
from adaptive_agent.requirements import synchronize_requirements
from adaptive_agent.sufficiency import SufficiencyEstimator
from adaptive_agent.acquisition_gate import gate_acquisition_candidates
from adaptive_agent.state import AdaptiveAgentState, TaskType
from adaptive_agent.state_update import apply_diary_result, apply_retrieval_result
from adaptive_agent.tools import DiaryResult, RetrievalResult


def _req(fields=(), *, evidence=False, resources=(), classes=None):
    return RequirementSet((), (), evidence, resources=tuple(resources), decision_fields=tuple(fields),
                         precondition_classes=classes or {})


def _production_candidates(state, req):
    SufficiencyEstimator().update(state, req)
    deps = DependencyResolver().resolve(state, req)
    effective = synchronize_requirements(req, state, deps)
    SufficiencyEstimator().update(state, effective)
    return gate_acquisition_candidates(state, effective, generate_candidates(state, effective))


class Step933ArchitectureRepairTests(unittest.TestCase):
 def test_a_external_evidence_is_independent_of_missing_user_facts(self):
    state = AdaptiveAgentState(goal="我想了解一般睡眠知识", task_type=TaskType.CAUSE_ASSESSMENT,
                               decision_missing=["wake_time"])
    deps = DependencyResolver().resolve(state, _req(("wake_time",), evidence=True))
    assert any(d.dependency_type.value == "EVIDENCE" and d.status.value == "REQUIRED" for d in deps)
    assert evaluate_preconditions(state, _req(("wake_time",), evidence=True)).action == "RETRIEVE"


 def test_b_directional_soft_missing_fact_remains_information_value_candidate(self):
    state = AdaptiveAgentState(goal="我该如何改变我的睡眠安排？", task_type=TaskType.PERSONALIZED_DECISION,
                               decision_missing=["wake_time"])
    req = _req(("wake_time",))
    assert evaluate_preconditions(state, req) is None
    actions = _production_candidates(state, req)
    assert any(a.action == "ASK" and a.target == "wake_time" for a in actions)


 def test_c_immaterial_missing_fact_does_not_force_ask(self):
    state = AdaptiveAgentState(goal="我的周末生活", task_type=TaskType.PERSONALIZED_DECISION,
                               decision_missing=["caffeine"])
    req = _req(("caffeine",))
    assert evaluate_preconditions(state, req) is None
    assert not any(a.action == "ASK" for a in generate_candidates(state, req))


 def test_d_explicit_safety_critical_precondition_is_hard(self):
    state = AdaptiveAgentState(goal="调整起床时间", task_type=TaskType.PERSONALIZED_DECISION,
                               decision_missing=["wake_time"])
    req = _req(("wake_time",), classes={"wake_time": "SAFETY_CRITICAL"})
    action = evaluate_preconditions(state, req)
    assert action and action.action == "ASK" and action.origin == "HARD_PRECONDITION"


 def test_e_asserted_fact_status_survives_fact_projection_and_prevents_ask(self):
    state = AdaptiveAgentState(goal="我该如何改变我的睡眠安排？", decision_missing=["caffeine"])
    apply_understanding(state, understanding_from_mapping({"facts": {}}, "我下午喝咖啡。"))
    assert state.fact_status["caffeine"] == "ASSERTED"
    assert not ask_is_eligible(state, "caffeine")
    assert build_answer_context(state)["fact_status"]["caffeine"] == "ASSERTED"


 def test_f_explicit_unavailability_persists_and_stops_reasking(self):
    state = AdaptiveAgentState(goal="咖啡会影响我的睡眠吗？", turn_index=1,
                               action_history=[{"action": "ASK", "target": "caffeine"}],
                               decision_missing=["caffeine"])
    understanding = understanding_from_mapping({"facts": {}}, "这项信息我目前不清楚。", state)
    apply_understanding(state, understanding)
    assert state.target_status["caffeine"]["status"] == "UNAVAILABLE"
    assert not ask_is_eligible(state, "caffeine")
    assert not any(item.action == "ASK" for item in _production_candidates(state, _req(("caffeine",))))


 def test_g_unavailable_diary_is_not_retried_or_fabricated(self):
    state = AdaptiveAgentState(goal="分析我的睡眠日记趋势", task_type=TaskType.DATA_ANALYSIS,
                               resource_status={"sleep_diary": "unread"})
    req = _req(resources=("sleep_diary",))
    assert evaluate_preconditions(state, req).action == "READ_DIARY"
    state.record_action(evaluate_preconditions(state, req))
    apply_diary_result(state, DiaryResult({}, False, kind="UNAVAILABLE"))
    next_action = evaluate_preconditions(state, req)
    assert next_action.action == "ANSWER"
    assert "recent_sleep_pattern" not in state.facts


 def test_h_retrieval_lineage_is_projected_to_answer_context(self):
    state = AdaptiveAgentState(goal="解释刺激控制", goal_id="synthetic", state_revision=1)
    state.record_action(__import__("adaptive_agent.state", fromlist=["ActionCandidate"]).ActionCandidate(
        action="RETRIEVE", query=state.goal))
    apply_retrieval_result(state, RetrievalResult(("刺激控制的一般说明",), True, "synthetic"))
    state.dependencies_considered = [{"dependency_type": "EVIDENCE", "status": "SATISFIED", "dependency_id": "dep-syn"}]
    context = build_answer_context(state)
    assert context["relevant_evidence"] == ["刺激控制的一般说明"]
    assert state.lineage_events[0]["source_action_id"]

 def test_k_failed_retrieval_is_not_retried_or_fabricated(self):
    state = AdaptiveAgentState(goal="说明一般睡眠知识", goal_id="synthetic", state_revision=1)
    state.record_action(__import__("adaptive_agent.state", fromlist=["ActionCandidate"]).ActionCandidate(
        action="RETRIEVE", query=state.goal))
    apply_retrieval_result(state, RetrievalResult((), False, "synthetic unavailable"))
    assert state.resource_status["external_evidence"] == "unavailable"
    assert state.evidence == []
    assert evaluate_preconditions(state, _req(evidence=True)) is None


 def test_i_no_required_evidence_means_no_forced_retrieval(self):
    state = AdaptiveAgentState(goal="闲聊", task_type=TaskType.PERSONALIZED_DECISION)
    assert evaluate_preconditions(state, _req(evidence=False)) is None


 def test_j_conflicting_explicit_facts_are_invalid_not_silently_overwritten(self):
    state = AdaptiveAgentState()
    apply_understanding(state, understanding_from_mapping({"facts": {}}, "我下午喝咖啡。"))
    apply_understanding(state, understanding_from_mapping({"facts": {}}, "我晚上喝茶。"))
    assert state.fact_status["caffeine"] == "INVALID"
    assert not requirement_is_known("caffeine", state.facts)
    assert "caffeine" not in build_answer_context(state)["relevant_facts"]
