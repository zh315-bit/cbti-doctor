"""Hard preconditions selected from goal-semantic dependencies."""
from __future__ import annotations

from .dependency_resolver import DependencyResolver, DependencyStatus, DependencyType, validity_critical_fields
from .requirements import RequirementSet
from .state import ActionCandidate, AdaptiveAgentState

_QUESTIONS = {"wake_time": "你通常几点起床？", "sleep_onset_latency": "你上床后通常需要多久才能睡着？", "sleep_time_or_sleep_onset_latency": "你通常几点入睡，或大约需要多久才能睡着？"}


def _asked_equivalent(state: AdaptiveAgentState, field: str) -> bool:
    aliases = {"sleep_time", "sleep_onset_latency", "sleep_time_or_sleep_onset_latency"}
    normalized = "sleep_time_or_sleep_onset_latency" if field in aliases else field
    return any(item.get("action") == "ASK" and
               ("sleep_time_or_sleep_onset_latency" if item.get("target") in aliases else item.get("target")) == normalized
               for item in state.action_history)


def classify_validity_critical(state: AdaptiveAgentState, requirements: RequirementSet) -> list[str]:
    """Compatibility helper; semantics now belong to DependencyResolver."""
    return validity_critical_fields(state, requirements)


def evaluate_preconditions(state: AdaptiveAgentState, requirements: RequirementSet) -> ActionCandidate | None:
    """Consume dependencies before optional Information Value candidates."""
    dependencies = DependencyResolver().resolve(state, requirements)
    state.dependencies_considered = [item.to_dict() for item in dependencies]
    state.dependencies_required = [item.to_dict() for item in dependencies if item.status in {DependencyStatus.REQUIRED, DependencyStatus.AVAILABLE}]
    state.dependencies_satisfied = [item.to_dict() for item in dependencies if item.status is DependencyStatus.SATISFIED]
    state.dependencies_unavailable = [item.to_dict() for item in dependencies if item.status in {DependencyStatus.UNAVAILABLE, DependencyStatus.INVALID}]
    state.preconditions_considered = []
    state.validity_critical_missing = [item.target for item in dependencies if item.dependency_type is DependencyType.VALIDITY_STATE]

    def precondition(item, forced_action, **extra):
        precondition_id = f"pre_{state.goal_id or 'goal'}_r{state.state_revision}_{len(state.preconditions_considered) + 1}"
        record = {"precondition_id": precondition_id, "source_dependency_id": item.dependency_id,
                  "semantic_ids": list(item.semantic_ids), "precondition_forced_action": forced_action is not None,
                  "counterfactual_candidate": None, "counterfactual_action": "not_available",
                  "counterfactual_stop_reason": "not_available", **extra}
        state.preconditions_considered.append(record)
        return precondition_id

    resource = next((item for item in dependencies if item.dependency_type is DependencyType.RESOURCE), None)
    if resource and resource.status is DependencyStatus.AVAILABLE:
        pre_id = precondition(resource, "READ_DIARY", type="RESOURCE", target=resource.target, required_for=state.goal, status="unsatisfied", satisfaction_source=None, required_action="READ_DIARY", reason=resource.reason, dependency_source=list(resource.source), satisfiers_considered=list(resource.satisfiable_by), selected_satisfier="READ_DIARY")
        return ActionCandidate(action="READ_DIARY", target="sleep_diary", expected_benefit="HIGH", cost="LOW", rationale="满足日记资源硬前置条件。", candidate_id=f"cand_{state.goal_id or 'goal'}_r{state.state_revision}_1", source_dependency_id=resource.dependency_id, source_precondition_id=pre_id, origin="HARD_PRECONDITION")
    if resource and resource.status in {DependencyStatus.UNAVAILABLE, DependencyStatus.INVALID}:
        pre_id = precondition(resource, None, type="RESOURCE", target=resource.target, required_for=state.goal, status=resource.status.value.lower(), satisfaction_source=resource.status.value.lower(), required_action=None, reason=resource.reason, dependency_source=list(resource.source), satisfiers_considered=list(resource.satisfiable_by), selected_satisfier=None)
        return ActionCandidate(action="ANSWER", expected_benefit="MEDIUM", rationale="所需睡眠日记不可用或无效；不得伪造日记分析。", candidate_id=f"cand_{state.goal_id or 'goal'}_r{state.state_revision}_1", source_dependency_id=resource.dependency_id, source_precondition_id=pre_id, origin="HARD_PRECONDITION")

    # Required external evidence is a hard, source-independent prerequisite and
    # is resolved before optional/decision-classified validity facts.
    evidence = next((item for item in dependencies if item.dependency_type is DependencyType.EVIDENCE), None)
    user_facts = next((item for item in dependencies if item.dependency_type is DependencyType.USER_FACTS
                       and item.status is DependencyStatus.DEFERRED), None)
    # Evidence remains independently actionable, but a material personal-fact
    # ASK is not unconditionally displaced; the candidate value/cost policy
    # chooses the more direct next acquisition step.
    if evidence and evidence.status is DependencyStatus.REQUIRED and user_facts is None:
        pre_id = precondition(evidence, "RETRIEVE", type="EVIDENCE", target=evidence.target, required_for=state.goal, status="unsatisfied", satisfaction_source=None, required_action="RETRIEVE", reason=evidence.reason, dependency_source=list(evidence.source), satisfiers_considered=list(evidence.satisfiable_by), selected_satisfier="RETRIEVE")
        return ActionCandidate(action="RETRIEVE", query=state.goal, expected_benefit="HIGH", cost="MEDIUM", rationale="满足证据硬前置条件。", candidate_id=f"cand_{state.goal_id or 'goal'}_r{state.state_revision}_1", source_dependency_id=evidence.dependency_id, source_precondition_id=pre_id, origin="HARD_PRECONDITION")
    validity = next((item for item in dependencies if item.dependency_type is DependencyType.VALIDITY_STATE
                     and (item.provenance or {}).get("precondition_class") in {"SAFETY_CRITICAL", "EXECUTION_CRITICAL"}), None)
    if validity:
        diary_available = state.available_diary and state.diary_authorized is not False and state.diary_available is not False and state.resource_status.get("sleep_diary", "unread") == "unread"
        if diary_available:
            selected = "READ_DIARY"; candidate = ActionCandidate(action="READ_DIARY", target="sleep_diary", expected_benefit="HIGH", cost="LOW", rationale="日记可满足 validity-state 前置条件。")
        elif _asked_equivalent(state, validity.target):
            selected = None; candidate = None
        else:
            selected = "ASK"; candidate = ActionCandidate(action="ASK", target=validity.target, question=_QUESTIONS.get(validity.target, f"请补充 {validity.target}。"), expected_benefit="HIGH", cost="LOW", rationale="满足 validity-state 前置条件。")
        pre_id = precondition(validity, selected, type="VALIDITY_CRITICAL_STATE", target=validity.target, required_for=state.goal, status="deferred" if candidate is None else "unsatisfied", satisfaction_source="previous_unanswered_ask" if candidate is None else None, required_action=selected, validity_reason=validity.reason, reason=validity.reason, resource_alternative="sleep_diary" if diary_available else None, dependency_source=list(validity.source), satisfiers_considered=list(validity.satisfiable_by), selected_satisfier=selected)
        if candidate is not None:
            candidate = ActionCandidate(**{**candidate.__dict__, "candidate_id": f"cand_{state.goal_id or 'goal'}_r{state.state_revision}_1", "source_dependency_id": validity.dependency_id, "source_precondition_id": pre_id, "origin": "HARD_PRECONDITION"})
        return candidate

    soft_validity = next((item for item in dependencies if item.dependency_type is DependencyType.VALIDITY_STATE
                          and item.status is DependencyStatus.REQUIRED), None)
    if soft_validity:
        precondition(soft_validity, None, type="SOFT_VALIDITY_PRECONDITION", target=soft_validity.target,
                     required_for=state.goal, status="awaiting_information_value_gate",
                     satisfaction_source=None, required_action=None, reason=soft_validity.reason,
                     precondition_class=(soft_validity.provenance or {}).get("precondition_class", "DECISION_CRITICAL"),
                     dependency_source=list(soft_validity.source), selected_satisfier="INFORMATION_VALUE_GATE")
    return None
