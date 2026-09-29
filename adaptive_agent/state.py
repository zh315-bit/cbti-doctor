"""State types shared by each iteration of the adaptive-agent loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class TaskType(str, Enum):
    KNOWLEDGE_QA = "KNOWLEDGE_QA"
    CAUSE_ASSESSMENT = "CAUSE_ASSESSMENT"
    PERSONALIZED_DECISION = "PERSONALIZED_DECISION"
    DATA_ANALYSIS = "DATA_ANALYSIS"


Sufficiency = Literal["LOW", "MEDIUM", "HIGH"]
ActionName = Literal["ASK", "RETRIEVE", "READ_DIARY", "ANSWER"]
Level = Literal["LOW", "MEDIUM", "HIGH"]


@dataclass(frozen=True)
class ActionCandidate:
    """A concrete action considered by the policy, not merely an action name."""

    action: ActionName
    target: str | None = None
    question: str | None = None
    query: str | None = None
    expected_benefit: Level = "LOW"
    cost: Level = "LOW"
    rationale: str = ""
    goal_relevance: Level = "MEDIUM"
    decision_impact: Level = "MEDIUM"
    redundancy: Level = "LOW"
    information_value: str = ""
    acquisition_cost: str = ""
    candidate_id: str | None = None
    source_requirement_id: str | None = None
    source_dependency_id: str | None = None
    source_precondition_id: str | None = None
    origin: str = "OPTIONAL_ACQUISITION"
    expected_information_gain: str = ""
    acquisition_value: str = ""
    gate_decision: str = ""
    gate_reason: str = ""


@dataclass
class AdaptiveAgentState:
    """Serializable domain state; message history remains owned by the web layer."""

    goal: str = ""
    task_type: TaskType | None = None
    facts: dict[str, Any] = field(default_factory=dict)
    fact_sources: dict[str, dict[str, Any]] = field(default_factory=dict)
    # Canonical epistemic status is carried independently from the value itself.
    fact_status: dict[str, str] = field(default_factory=dict)
    target_status: dict[str, dict[str, Any]] = field(default_factory=dict)
    fact_conflicts: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    critical_missing: list[str] = field(default_factory=list)
    required_missing: list[str] = field(default_factory=list)
    decision_relevant_missing: list[str] = field(default_factory=list)
    validity_critical_missing: list[str] = field(default_factory=list)
    secondary_missing: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    evidence_sources: list[dict[str, Any]] = field(default_factory=list)
    user_info_sufficiency: Sufficiency = "LOW"
    evidence_sufficiency: Sufficiency = "LOW"
    available_diary: bool = False
    candidate_actions: list[ActionCandidate] = field(default_factory=list)
    action_history: list[dict[str, Any]] = field(default_factory=list)
    resource_status: dict[str, str] = field(default_factory=dict)
    required_resources: list[str] = field(default_factory=list)
    decision_missing: list[str] = field(default_factory=list)
    answer_scope: str = ""
    turn_index: int = 0
    claim_provenance: list[dict[str, Any]] = field(default_factory=list)
    answer_context_audit: dict[str, Any] = field(default_factory=dict)
    information_estimates: dict[str, dict[str, Any]] = field(default_factory=dict)
    considered_information: list[dict[str, Any]] = field(default_factory=list)
    rejected_information: list[dict[str, Any]] = field(default_factory=list)
    acquisition_decisions: list[dict[str, Any]] = field(default_factory=list)
    stop_reason: str = ""
    preconditions_considered: list[dict[str, Any]] = field(default_factory=list)
    dependencies_considered: list[dict[str, Any]] = field(default_factory=list)
    dependencies_required: list[dict[str, Any]] = field(default_factory=list)
    dependencies_satisfied: list[dict[str, Any]] = field(default_factory=list)
    dependencies_unavailable: list[dict[str, Any]] = field(default_factory=list)
    diary_authorized: bool | None = None
    diary_available: bool | None = None
    diary_projection: dict[str, Any] = field(default_factory=dict)
    goal_id: str = ""
    state_revision: int = 0
    semantic_provenance: list[dict[str, Any]] = field(default_factory=list)
    base_requirements: dict[str, Any] = field(default_factory=dict)
    effective_requirements: dict[str, Any] = field(default_factory=dict)
    lineage_events: list[dict[str, Any]] = field(default_factory=list)

    def record_action(self, candidate: ActionCandidate) -> dict[str, Any]:
        action_id = f"act_{self.goal_id or 'unknown'}_r{self.state_revision}_{len(self.action_history) + 1}"
        item = {
            "action_id": action_id,
            "selected_candidate_id": candidate.candidate_id,
            "action": candidate.action,
            "target": candidate.target,
            "query": candidate.query,
        }
        self.action_history.append(item)
        return item
