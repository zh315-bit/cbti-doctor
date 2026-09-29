"""Explainable qualitative policy for choosing exactly one V1 action."""

from __future__ import annotations

from .state import ActionCandidate, AdaptiveAgentState


_HIGH_FIRST = ("HIGH", "MEDIUM", "LOW")
_LOW_FIRST = ("LOW", "MEDIUM", "HIGH")


class HeuristicDecisionPolicy:
    """Select by expected benefit versus cost, with goal-value encoded in candidates."""

    def choose(self, state: AdaptiveAgentState) -> ActionCandidate:
        if not state.candidate_actions:
            raise ValueError("No candidate actions available for the current goal")

        # A legitimate ANSWER wins over optional secondary data collection.
        answer = next((item for item in state.candidate_actions if item.action == "ANSWER"), None)
        if answer:
            return answer

        def preference(candidate: ActionCandidate) -> tuple:
            # Ordinal comparisons only: no arithmetic utility or probability.
            # A diary that can supply missing facts wins first; otherwise an
            # accepted, counterfactually material ASK must not be displaced by
            # an independent evidence fetch. Optional/low-value asks have
            # already been removed by the acquisition gate, so required
            # retrieval remains actionable as soon as no such ASK is pending.
            acquisition_order = {"READ_DIARY": 0, "ASK": 1, "RETRIEVE": 2}
            return (
                acquisition_order.get(candidate.action, 1),
                _HIGH_FIRST.index(candidate.expected_benefit),
                _HIGH_FIRST.index(candidate.goal_relevance),
                _HIGH_FIRST.index(candidate.decision_impact),
                _LOW_FIRST.index(candidate.redundancy),
                _LOW_FIRST.index(candidate.cost),
                candidate.action == 'ASK',
                candidate.target or candidate.query or candidate.action,
            )

        return min(state.candidate_actions, key=preference)
