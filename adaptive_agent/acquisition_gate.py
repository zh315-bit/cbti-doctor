"""Goal- and dependency-aware gate for optional information acquisition.

All levels are ordinal heuristics, not calibrated probabilities or learned rewards.
Hard precondition actions are preserved and cannot be rejected by this gate.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from .information_value import acquisition_threshold_met, estimate_information_value
from .requirements import RequirementSet
from .state import ActionCandidate, AdaptiveAgentState


_RANK = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}


def _dependency(state: AdaptiveAgentState, dependency_class: str) -> dict[str, Any] | None:
    return next((item for item in state.dependencies_considered
                 if item.get("dependency_class") == dependency_class), None)


def _acquisition_value(gain: str, relevance: str, impact: str, redundancy: str, cost: str) -> str:
    """Combine transparent ordinal components without claiming numeric utility."""
    if gain == "NONE" or redundancy == "HIGH" or relevance == "LOW" or impact == "LOW":
        return "NONE"
    if gain == "HIGH" and relevance == "HIGH" and impact == "HIGH":
        return "HIGH"
    if _RANK.get(gain, 0) >= _RANK["MEDIUM"] and (relevance == "HIGH" or impact == "HIGH"):
        return "MEDIUM" if cost != "HIGH" else "LOW"
    return "LOW"


def gate_acquisition_candidates(
    state: AdaptiveAgentState, requirements: RequirementSet,
    candidates: list[ActionCandidate],
) -> list[ActionCandidate]:
    """Annotate and filter acquisition candidates before the decision policy."""
    state.acquisition_decisions = []
    accepted: list[ActionCandidate] = []
    prior_asks = sum(item.get("action") == "ASK" for item in state.action_history)

    for candidate in candidates:
        if candidate.action == "ANSWER":
            accepted.append(candidate)
            continue

        action = candidate.action
        target = candidate.target or candidate.query or action.lower()
        estimate = None
        if action == "ASK":
            estimate = estimate_information_value(state, target, requirements)
            relevance = "HIGH" if target in state.goal.lower() else candidate.goal_relevance
            impact = estimate.answer_scope_impact
            redundancy = "HIGH" if estimate.redundancy == "HIGH" else candidate.redundancy
            cost = estimate.acquisition_cost
            gain = estimate.value_level
            dependency = _dependency(state, "USER_FACTS")
            dependency_active = bool(dependency and dependency.get("requiredness") == "required"
                                     and dependency.get("status") in {"REQUIRED", "AVAILABLE"})
            if estimate.resource_alternative != dependency_active:
                estimate = replace(estimate, resource_alternative=dependency_active)
            # Decision-relevant missing facts remain eligible even if user-fact
            # context is optional; unrelated/secondary fields do not become asks.
            relevant = (estimate.decision_relevant and estimate.lineage_complete) or dependency_active
            reason = estimate.rationale
            allowed_by_value, threshold_reason = acquisition_threshold_met(estimate, prior_asks)
            counterfactual_actionable = estimate.decision_impact in {"decision_changing", "answer_scope_changing"}
            allowed = (relevant and redundancy != "HIGH" and counterfactual_actionable
                       and allowed_by_value)
            if not relevant:
                reason = "not_decision_relevant_and_no_active_user_fact_dependency"
            elif redundancy == "HIGH":
                reason = "equivalent_information_already_known_or_asked"
            elif not counterfactual_actionable:
                reason = "counterfactual_values_do_not_change_action_direction_or_answer_scope"
            elif not allowed_by_value:
                reason = threshold_reason or "information_value_does_not_cover_interaction_cost"
        elif action == "RETRIEVE":
            dependency = _dependency(state, "EXTERNAL_EVIDENCE")
            dependency_active = bool(dependency and dependency.get("status") in {"REQUIRED", "AVAILABLE"})
            relevant = dependency_active
            gain = "HIGH" if relevant else "NONE"
            relevance = "HIGH" if relevant else "LOW"
            impact = "HIGH" if relevant else "LOW"
            evidence_known = bool(state.evidence) or bool(dependency and dependency.get("status") == "SATISFIED")
            redundancy = "HIGH" if evidence_known else "LOW"
            cost = candidate.cost
            allowed = relevant and not evidence_known
            reason = ("active_evidence_dependency_unsatisfied" if allowed else
                      "evidence_dependency_already_satisfied" if evidence_known else
                      "no_active_evidence_dependency")
        elif action == "READ_DIARY":
            dependency = _dependency(state, "DIARY_DATA")
            if dependency is None:
                # A diary may be the explicitly declared satisfier for a
                # goal-scoped validity dependency (for example, timing facts).
                dependency = next((item for item in state.dependencies_considered
                                   if item.get("dependency_type") == "VALIDITY_STATE"
                                   and "READ_DIARY" in item.get("satisfiable_by", [])), None)
            dependency_active = bool(dependency and dependency.get("status") in {"REQUIRED", "AVAILABLE"})
            relevant = dependency_active
            gain = "HIGH" if relevant else "NONE"
            relevance = "HIGH" if relevant else "LOW"
            impact = "HIGH" if relevant else "LOW"
            loaded = state.resource_status.get("sleep_diary") == "loaded" or bool(
                dependency and dependency.get("status") == "SATISFIED")
            unavailable = state.resource_status.get("sleep_diary") in {"unavailable", "invalid"}
            redundancy = "HIGH" if loaded or unavailable else "LOW"
            cost = candidate.cost
            allowed = relevant and not loaded and not unavailable
            reason = ("active_diary_dependency_unsatisfied" if allowed else
                      "diary_dependency_already_satisfied" if loaded else
                      "diary_unavailable_or_invalid_no_retry" if unavailable else
                      "no_active_diary_dependency")
        else:
            accepted.append(candidate)
            continue

        if not relevant:
            relevance = "LOW"
            impact = "LOW"
        value = _acquisition_value(gain, relevance, impact, redundancy, cost)
        # Hard dependencies are emitted by preconditions before this gate. Keep
        # this invariant explicit in case a future caller supplies one here.
        mandatory = candidate.origin == "HARD_PRECONDITION"
        if mandatory:
            allowed = True
            reason = "mandatory_dependency_precondition_cannot_be_overridden"
            value = "HIGH"
        annotated = replace(
            candidate,
            goal_relevance=relevance,
            decision_impact=impact,
            redundancy=redundancy,
            acquisition_cost=cost,
            information_value=gain,
            expected_information_gain=gain,
            acquisition_value=value,
            gate_decision="ACCEPT" if allowed else "REJECT",
            gate_reason=reason,
        )
        record = {
            "candidate_id": candidate.candidate_id,
            "action": action,
            "target": target,
            "expected_information_gain": gain,
            "goal_relevance": relevance,
            "decision_impact": impact,
            "missing_criticality": ("VALIDITY_CRITICAL" if target in state.validity_critical_missing
                                   else "CRITICAL_REQUIREMENT" if target in state.critical_missing
                                   else "DECISION_RELEVANT" if target in state.decision_relevant_missing
                                   else "SECONDARY_OR_UNSCOPED"),
            "redundancy": redundancy,
            "resource_dependency": dependency,
            "estimated_cost": cost,
            "acquisition_value": value,
            "gate_decision": annotated.gate_decision,
            "accepted": allowed,
            "reason": reason,
            "dependency_id": (estimate.dependency_id if estimate is not None else
                              (dependency or {}).get("dependency_id") if action != "ANSWER" else None),
            "lineage_complete": (estimate.lineage_complete if estimate is not None else
                                 bool(dependency and dependency.get("dependency_id"))),
            "decision_relevant": (estimate.decision_relevant if estimate is not None else relevant),
            "counterfactual_outcomes": (list(estimate.counterfactual_outcomes) if estimate is not None else
                                        ["dependency unsatisfied" if allowed else "dependency satisfied or absent"]),
            "impact_dimensions": (list(estimate.impact_dimensions) if estimate is not None else
                                  (["evidence_dependency"] if action == "RETRIEVE" else ["diary_resource"] if action == "READ_DIARY" else [])),
            "counterfactual_candidate": ({"if_unknown": estimate.counterfactual_outcomes[0],
                                          "if_resolved": estimate.counterfactual_outcomes[1]}
                                         if estimate is not None and len(estimate.counterfactual_outcomes) >= 2 else None),
            "heuristic_not_calibrated_probability": True,
        }
        state.acquisition_decisions.append(record)
        if allowed:
            accepted.append(annotated)
        else:
            state.rejected_information.append({**record, "rejection_reason": reason})

    if accepted:
        return accepted

    state.stop_reason = "no_worthwhile_information_after_acquisition_gate"
    return [ActionCandidate(
        action="ANSWER", expected_benefit="MEDIUM", cost="LOW",
        rationale="没有值得继续获取的信息；仅在现有事实与证据支持的范围内回答并说明限制。",
        candidate_id=f"cand_{state.goal_id or 'goal'}_r{state.state_revision}_bounded_answer",
        origin="BOUNDED_STOP", gate_decision="ACCEPT",
        gate_reason=state.stop_reason,
    )]
