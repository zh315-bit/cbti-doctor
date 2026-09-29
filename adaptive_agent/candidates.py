"""Build specific, goal-relevant actions from the current state."""

from __future__ import annotations

from .requirements import RequirementSet, resolve_requirements, requirement_is_known, FIELD_SIGNALS, normalize_target, synchronize_requirements
from .state import ActionCandidate, AdaptiveAgentState
from .information_value import estimate_information_value
from .preconditions import evaluate_preconditions


QUESTIONS = {
    "bedtime": "你通常几点上床？",
    "sleep_time_or_sleep_onset_latency": "你通常几点入睡，或大约需要多久才能睡着？",
    "sleep_onset_latency": "你上床后通常需要多久才能睡着？",
    "wake_time": "你通常几点起床？",
    "total_sleep_time": "你估计每晚总共睡多久？",
    "nighttime_awakenings": "你夜里通常会醒几次、每次多久？",
    "recent_sleep_pattern": "最近一到两周的睡眠作息大致是怎样的？",
    "caffeine": "你下午或晚上会摄入咖啡、茶或能量饮料吗？",
    "nap": "你白天会午睡吗？通常多久？",
    "exercise": "你最近的运动通常在什么时间、持续多久？",
    "screen_before_bed": "睡前一小时通常会使用手机或其他屏幕吗？",
    "perceived_stress": "最近压力或担忧对睡眠的影响大吗？",
}


def _normalized_target(target: str | None) -> str | None:
    """Collapse requirement aliases so equivalent questions share one key."""
    return normalize_target(target)


def _asked_targets(state: AdaptiveAgentState) -> set[str]:
    return {
        normalized for normalized in
        (_normalized_target(entry.get("target")) for entry in state.action_history
         if entry.get("action") == "ASK")
        if normalized
    }


def ask_is_eligible(state: AdaptiveAgentState, target: str) -> bool:
    """ASK gate: unknown, decision-relevant, valuable, and not already asked."""
    if target not in state.decision_relevant_missing:
        return False
    if requirement_is_known(target, state.facts):
        return False
    status = state.target_status.get(_normalized_target(target) or "", {}).get("status")
    if status in {"ASSERTED", "DERIVED", "RETRIEVED", "UNAVAILABLE", "NOT_APPLICABLE"}:
        return False
    if _normalized_target(target) in _asked_targets(state):
        return False
    return True


def generate_candidates(state: AdaptiveAgentState, requirements: RequirementSet) -> list[ActionCandidate]:
    requirements = resolve_requirements(requirements, state.goal)
    candidates: list[ActionCandidate] = []
    state.considered_information = []
    state.rejected_information = []
    state.information_estimates = {}
    state.stop_reason = ""
    required = evaluate_preconditions(state, requirements)
    if required is not None:
        state.considered_information.append({
            "target": required.target or required.query or "precondition", "value_level": "HIGH",
            "candidate_action": required.action, "accepted": True, "precondition": True,
            "rationale": required.rationale,
        })
        return [required]
    completed_actions = {entry.get("action") for entry in state.action_history}
    user_facts_dependency = next(
        (item for item in state.dependencies_considered if item.get("dependency_type") == "USER_FACTS"),
        None,
    )
    evidence_dependency = next(
        (item for item in state.dependencies_considered if item.get("dependency_class") == "EXTERNAL_EVIDENCE"),
        None,
    )
    diary_dependency = next(
        (item for item in state.dependencies_considered if item.get("dependency_class") == "DIARY_DATA"),
        None,
    )
    if diary_dependency is None:
        diary_dependency = next(
            (item for item in state.dependencies_considered
             if item.get("dependency_type") == "VALIDITY_STATE"
             and "READ_DIARY" in item.get("satisfiable_by", [])),
            None,
        )
    missing_resources = [r for r in requirements.resources if state.resource_status.get(r, 'unread') != 'loaded']
    if any(state.resource_status.get(r) == 'unavailable' for r in missing_resources):
        return [ActionCandidate(action='ANSWER', expected_benefit='MEDIUM',
                                rationale='目标依赖的日记资源不可用，无法完成基于日记的分析；不得生成分析结论。')]
    should_check_diary = 'sleep_diary' in missing_resources
    can_use_known_diary = (state.available_diary and state.decision_missing
                          and state.resource_status.get('sleep_diary', 'unread') == 'unread')
    if should_check_diary or can_use_known_diary:
        targets = state.decision_missing or ["sleep_diary"]
        state.considered_information.append({
            "target": ", ".join(targets), "value_level": "HIGH", "decision_impact": "decision_changing",
            "uncertainty": "unknown", "answer_scope_impact": "HIGH", "acquisition_cost": "LOW",
            "resource_alternative": True, "redundancy": "LOW", "candidate_action": "READ_DIARY",
            "accepted": True, "rationale": "authorized diary resource may provide the missing facts",
        })
        candidates.append(ActionCandidate(
            action="READ_DIARY", target=", ".join(targets), expected_benefit="HIGH", cost="LOW",
            goal_relevance='HIGH', decision_impact='HIGH',
            rationale="睡眠日记可能直接提供当前目标所需的关键事实。",
            candidate_id=f"cand_{state.goal_id or 'goal'}_r{state.state_revision}_{len(candidates) + 1}",
            source_requirement_id=requirements.requirement_ids.get("sleep_diary"),
            source_dependency_id=(diary_dependency or {}).get("dependency_id"),
        ))

    for field in state.decision_missing:
        estimate = estimate_information_value(state, field, requirements)
        state.information_estimates[estimate.target] = estimate.to_dict()
        considered = {"target": estimate.target, **estimate.to_dict(), "candidate_action": "ASK"}
        state.considered_information.append(considered)
        if not ask_is_eligible(state, field):
            state.rejected_information.append({**considered, "accepted": False, "rejection_reason": "unknown_or_redundant_or_not_decision_relevant"})
            continue
        explicit = any(term in state.goal for term in FIELD_SIGNALS.get(field, ()))
        impact = 'HIGH' if explicit or len(state.decision_relevant_missing) <= 2 else 'MEDIUM'
        candidates.append(ActionCandidate(
            action="ASK", target=field, question=QUESTIONS[field],
            expected_benefit=estimate.value_level if estimate.value_level in {"HIGH", "MEDIUM", "LOW"} else "LOW",
            cost=estimate.acquisition_cost,
            goal_relevance='HIGH' if explicit else 'MEDIUM', decision_impact=impact,
            redundancy='LOW',
            information_value=estimate.value_level, acquisition_cost=estimate.acquisition_cost,
            rationale=f"{field} 尚未知且属于当前目标的 decision_relevant_missing；回答可能改变下一步行动或回答范围。",
            candidate_id=f"cand_{state.goal_id or 'goal'}_r{state.state_revision}_{len(candidates) + 1}",
            source_requirement_id=requirements.requirement_ids.get(field),
            source_dependency_id=(user_facts_dependency or {}).get("dependency_id"),
            expected_information_gain=estimate.value_level,
        ))

    if (evidence_dependency and evidence_dependency.get("status") == "REQUIRED"
            and "RETRIEVE" not in completed_actions):
        candidates.append(ActionCandidate(
            action="RETRIEVE", query=state.goal, expected_benefit="HIGH", cost="MEDIUM",
            rationale="独立 evidence dependency 尚未满足；此资源候选不依赖个人事实完整度。",
            candidate_id=f"cand_{state.goal_id or 'goal'}_r{state.state_revision}_{len(candidates) + 1}",
            source_dependency_id=(evidence_dependency or {}).get("dependency_id"),
        ))

    if state.user_info_sufficiency == "HIGH" and state.evidence_sufficiency == "HIGH":
        candidates.append(ActionCandidate(
            action="ANSWER", expected_benefit="HIGH", cost="LOW",
            rationale="当前目标所需的用户信息和证据均已充分。",
            candidate_id=f"cand_{state.goal_id or 'goal'}_r{state.state_revision}_{len(candidates) + 1}",
        ))

    # A failed one-time tool attempt must not create an internal retry loop. The
    # final responder will state the information limitation rather than invent it.
    if not candidates:
        if state.rejected_information:
            state.stop_reason = "no remaining information value justified acquisition cost"
        candidates.append(ActionCandidate(
            action="ANSWER", expected_benefit="MEDIUM", cost="LOW",
            rationale="当前缺少决策所需信息，且没有值得继续执行的新行动；应说明限制，不得作确定的个性化结论。",
            candidate_id=f"cand_{state.goal_id or 'goal'}_r{state.state_revision}_{len(candidates) + 1}",
        ))

    return candidates


def build_candidates(state: AdaptiveAgentState, requirements: RequirementSet) -> list[ActionCandidate]:
    """Backward-compatible entry point returning gated policy-ready actions."""
    from .acquisition_gate import gate_acquisition_candidates
    if not requirements.is_effective:
        from .dependency_resolver import DependencyResolver
        dependencies = DependencyResolver().resolve(state, requirements)
        state.dependencies_considered = [item.to_dict() for item in dependencies]
        requirements = synchronize_requirements(requirements, state, dependencies)
    return gate_acquisition_candidates(state, requirements, generate_candidates(state, requirements))
