"""Goal-aware, qualitative information sufficiency for V1."""

from __future__ import annotations

from .requirements import RequirementSet, calculate_missing, resolve_requirements, requirement_is_known
from .preconditions import classify_validity_critical
from .state import AdaptiveAgentState, Sufficiency


class SufficiencyEstimator:
    """Estimate whether information is sufficient to address this *current* goal.

    Secondary fields are intentionally excluded from the completion threshold.  They
    can improve an answer but must not turn an otherwise answerable goal into an
    endless collection loop.
    """

    def update(self, state: AdaptiveAgentState, requirements: RequirementSet) -> AdaptiveAgentState:
        requirements = resolve_requirements(requirements, state.goal)
        critical_missing, secondary_missing = calculate_missing(requirements, state.facts)
        state.critical_missing = critical_missing
        state.required_missing = list(dict.fromkeys(critical_missing + secondary_missing))
        state.secondary_missing = secondary_missing
        state.required_resources = list(requirements.resources)
        for resource in state.required_resources:
            state.resource_status.setdefault(resource, 'unread')
        state.decision_missing = [name for name in requirements.decision_fields or ()
                                  if not requirement_is_known(name, state.facts)]
        state.decision_relevant_missing = list(state.decision_missing)
        state.validity_critical_missing = classify_validity_critical(state, requirements)
        state.answer_scope = requirements.answer_scope
        state.user_info_sufficiency = self.user_information(state, requirements)
        state.evidence_sufficiency = self.evidence(state, requirements)
        return state

    def user_information(self, state: AdaptiveAgentState, requirements: RequirementSet) -> Sufficiency:
        if not state.goal.strip():
            return "LOW"
        if any(state.resource_status.get(resource, "unread") != "loaded"
               for resource in state.required_resources):
            return "LOW"
        if state.decision_missing:
            return "MEDIUM" if state.facts else "LOW"
        return "HIGH"

    def evidence(self, state: AdaptiveAgentState, requirements: RequirementSet) -> Sufficiency:
        if not state.goal.strip():
            return "LOW"
        if not requirements.evidence_required:
            return "HIGH"
        return "HIGH" if state.evidence else "LOW"
