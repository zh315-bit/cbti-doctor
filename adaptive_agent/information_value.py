"""Interpretable ordinal information-value and acquisition-cost heuristics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from .requirements import FIELD_SIGNALS, RequirementSet, requirement_is_known, normalize_target
from .state import AdaptiveAgentState

ValueLevel = Literal["HIGH", "MEDIUM", "LOW", "NONE"]
CostLevel = Literal["LOW", "MEDIUM", "HIGH"]


@dataclass(frozen=True)
class InformationValueEstimate:
    target: str
    value_level: ValueLevel
    decision_impact: Literal["decision_changing", "answer_scope_changing", "detail_improving", "irrelevant"]
    uncertainty: Literal["unknown", "approximate", "range", "partial", "known"]
    answer_scope_impact: Literal["HIGH", "MEDIUM", "LOW", "NONE"]
    acquisition_cost: CostLevel
    resource_alternative: bool
    redundancy: Literal["HIGH", "MEDIUM", "LOW", "NONE"]
    rationale: str
    decision_relevant: bool = False
    dependency_id: str | None = None
    lineage_complete: bool = False
    counterfactual_outcomes: tuple[str, ...] = ()
    impact_dimensions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _normalized_target(target: str) -> str:
    return normalize_target(target) or target


def _uncertainty(state: AdaptiveAgentState, target: str) -> str:
    status = state.fact_status.get(target) or state.target_status.get(_normalized_target(target), {}).get("status")
    if status:
        return status.lower()
    value = state.facts.get(target)
    if isinstance(value, dict):
        return str(value.get("uncertainty", "partial"))
    return "known" if requirement_is_known(target, state.facts) else "unknown"


def _asked_count(state: AdaptiveAgentState, target: str) -> int:
    normalized = _normalized_target(target)
    return sum(1 for item in state.action_history
               if item.get("action") == "ASK" and _normalized_target(item.get("target") or "") == normalized)


_DECISION_INTENT = (
    "是否应该", "是否调整", "是否需要调整", "判断是否需要", "应不应该", "要不要", "该不该", "怎么调整", "如何调整", "调整吗",
    "改变方案", "具体方案", "建议我", "应该怎么", "应该怎样", "怎样调整", "怎么安排", "该如何", "如何处理", "怎么做",
    "调整", "改变", "改善",
    "should i", "recommend", "adjust", "change the plan", "which option",
)
_COMPARISON_INTENT = ("比较", "对比", "哪种", "哪个", "区别", "compare", "versus", " vs ", "which option")
_SCOPE_INTENT = ("是否影响", "会不会影响", "有没有影响", "影响我的", "relevant to my", "affect my",
                 "趋势", "pattern", "trend", "分析", "总结")
_SCHEDULE_CONTEXT = ("作息", "睡眠安排", "睡眠时间", "sleep schedule", "sleep routine")
_PRESCRIPTION_CONTEXT = ("睡眠限制处方", "睡眠窗口处方", "具体处方", "sleep restriction prescription")
_PRESCRIPTION_RELEVANT_FIELDS = {"total_sleep_time", "nighttime_awakenings", "recent_sleep_pattern"}


def _user_fact_dependency(state: AdaptiveAgentState) -> dict | None:
    return next((item for item in state.dependencies_considered
                 if item.get("dependency_class") == "USER_FACTS"
                 and item.get("target") == "user_facts"
                 and item.get("status") in {"DEFERRED", "SATISFIED"}), None)


def estimate_information_value(state: AdaptiveAgentState, target: str, requirements: RequirementSet) -> InformationValueEstimate:
    normalized = _normalized_target(target)
    known = requirement_is_known(target, state.facts)
    target_status = state.target_status.get(normalized, {}).get("status")
    asked = _asked_count(state, target)
    equivalent_asked = asked > 0
    explicit_goal = any(term in state.goal.lower() for term in FIELD_SIGNALS.get(target, ()))
    decision_relevant = any(_normalized_target(item) == normalized for item in state.decision_relevant_missing)
    resource_alternative = bool(state.available_diary and state.resource_status.get("sleep_diary", "unread") == "unread")
    dependency = _user_fact_dependency(state)
    validity_dependency = next((item for item in state.dependencies_considered
                                if item.get("dependency_type") == "VALIDITY_STATE"
                                and item.get("target") == target
                                and item.get("status") == "REQUIRED"), None)
    requirement_class = requirements.classifications.get(target)
    lineage_complete = bool(
        dependency and dependency.get("dependency_id") and dependency.get("semantic_ids")
        and decision_relevant and target in requirements.requirement_ids
        and requirement_class in {"mandatory", "useful_optional"}
    )
    dependency_id = dependency.get("dependency_id") if dependency else None

    if known or equivalent_asked or target_status in {"UNAVAILABLE", "NOT_APPLICABLE"}:
        return InformationValueEstimate(normalized, "NONE", "irrelevant", _uncertainty(state, target), "NONE",
                                         "LOW", resource_alternative, "HIGH", "already known or semantically asked",
                                         decision_relevant, dependency_id, lineage_complete,
                                         ("already_known_or_already_asked",), ())
    if not decision_relevant or not lineage_complete:
        detail_only = decision_relevant and target in requirements.secondary
        return InformationValueEstimate(
            normalized, "LOW" if detail_only else "NONE",
            "detail_improving" if detail_only else "irrelevant", "unknown",
            "LOW" if detail_only else "NONE", "MEDIUM", resource_alternative, "NONE",
            "no complete goal→USER_FACTS dependency→missing field lineage" if not lineage_complete
            else "not decision-relevant for the current goal",
            decision_relevant, dependency_id, lineage_complete,
            ("unresolved: current answer remains bounded", "resolved: no supported downstream change identified"),
            ("answer_detail",) if detail_only else ())

    goal_text = state.goal.lower()
    decision_goal = any(term in goal_text for term in _DECISION_INTENT) or bool(validity_dependency)
    comparison_goal = any(term in goal_text for term in _COMPARISON_INTENT)
    schedule_context = any(term in goal_text for term in _SCHEDULE_CONTEXT)
    prescription_context = any(term in goal_text for term in _PRESCRIPTION_CONTEXT)
    schedule_fact = target in {"bedtime", "wake_time", "sleep_onset_latency", "sleep_time_or_sleep_onset_latency"}
    prescription_fact = target in _PRESCRIPTION_RELEVANT_FIELDS and target in requirements.critical
    if (validity_dependency or
            (decision_goal and ((explicit_goal and decision_relevant) or (schedule_context and schedule_fact)))
            or (prescription_context and prescription_fact)):
        impact = "decision_changing"
        value: ValueLevel = "HIGH"
        scope: Literal["HIGH", "MEDIUM", "LOW", "NONE"] = "HIGH"
        outcomes = ("unknown: keep the current decision bounded",
                    "plausible values: recommendation/action direction may differ")
        dimensions = ("next_action", "recommendation_direction", "answer_scope")
        rationale = "the goal explicitly links this missing fact to a choice or adjustment; plausible values can change the direction"
    elif ((explicit_goal and (comparison_goal or any(term in goal_text for term in _SCOPE_INTENT)))
          or (schedule_context and schedule_fact and comparison_goal)):
        impact = "answer_scope_changing"
        value = "MEDIUM"
        scope = "MEDIUM"
        outcomes = ("unknown: comparison remains qualified on this dimension",
                    "resolved: comparison can include or exclude the named dimension")
        dimensions = ("answer_scope", "comparison_basis")
        rationale = "the named missing fact changes the requested comparison scope, without establishing a treatment direction"
    else:
        impact = "detail_improving"
        value = "LOW"
        scope = "LOW"
        outcomes = ("unknown: current bounded answer and next action remain unchanged",
                    "plausible values: no supported change to action, direction, or answer scope")
        dimensions = ("answer_detail",)
        rationale = "the target is missing but not directly connected to the requested decision; plausible values do not change its direction"

    # Interaction cost rises with prior questions and cognitively broad prompts.
    cost: CostLevel = "LOW" if asked == 0 else "MEDIUM" if asked == 1 else "HIGH"
    if target in {"recent_sleep_pattern", "total_sleep_time"} and cost == "LOW":
        cost = "MEDIUM"
    return InformationValueEstimate(normalized, value, impact, "unknown", scope, cost,
                                     resource_alternative, "LOW", rationale,
                                     decision_relevant, dependency_id, lineage_complete,
                                     outcomes, dimensions)


def acquisition_threshold_met(estimate: InformationValueEstimate, prior_asks: int) -> tuple[bool, str | None]:
    """Apply diminishing returns without a fixed maximum-ASK rule."""
    if estimate.value_level == "NONE":
        return False, "information_value_none"
    if estimate.resource_alternative:
        return False, "resource_alternative_available"
    required = "HIGH" if prior_asks >= 2 else "MEDIUM" if prior_asks >= 1 else "LOW"
    rank = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    if rank[estimate.value_level] < rank[required]:
        return False, f"value_below_threshold_{required.lower()}"
    if estimate.acquisition_cost == "HIGH" and estimate.value_level != "HIGH":
        return False, "cost_exceeds_value"
    return True, None
