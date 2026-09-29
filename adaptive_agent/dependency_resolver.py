"""Goal-semantic dependency resolution, separate from optional requirements."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum

from .requirements import RequirementSet, requirement_is_known
from .state import AdaptiveAgentState


class DependencyType(str, Enum):
    # Legacy wire values remain stable for existing traces and integrations.
    USER_FACTS = "USER_FACTS"
    EVIDENCE = "EVIDENCE"
    RESOURCE = "RESOURCE"
    VALIDITY_STATE = "VALIDITY_STATE"


class DependencyClass(str, Enum):
    """Canonical information-source classes used by dependency formation."""

    USER_FACTS = "USER_FACTS"
    EXTERNAL_EVIDENCE = "EXTERNAL_EVIDENCE"
    DIARY_DATA = "DIARY_DATA"
    VALIDITY_STATE = "VALIDITY_STATE"


class DependencyStatus(str, Enum):
    REQUIRED = "REQUIRED"
    AVAILABLE = "AVAILABLE"
    SATISFIED = "SATISFIED"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID = "INVALID"
    DEFERRED = "DEFERRED"


@dataclass(frozen=True)
class Dependency:
    dependency_id: str
    dependency_type: DependencyType
    target: str
    status: DependencyStatus
    reason: str
    source: tuple[str, ...]
    required_for_goal: str
    satisfiable_by: tuple[str, ...]
    fallback: str | None = None
    provenance: dict[str, object] | None = None
    semantic_ids: tuple[str, ...] = ()
    supersedes_dependency_id: str | None = None
    dependency_class: DependencyClass | None = None
    requiredness: str = "required"

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["dependency_type"] = self.dependency_type.value
        result["status"] = self.status.value
        result["source"] = list(self.source)
        result["satisfiable_by"] = list(self.satisfiable_by)
        result["dependency_class"] = (self.dependency_class or _canonical_class(self.dependency_type)).value
        result["dependency_source"] = list(self.source)
        result["dependency_reason"] = self.reason
        result["requiredness"] = self.requiredness
        result["satisfied_by"] = list(self.satisfiable_by) if self.status in {DependencyStatus.SATISFIED, DependencyStatus.AVAILABLE} else []
        return result


def _canonical_class(dependency_type: DependencyType) -> DependencyClass:
    return {
        DependencyType.USER_FACTS: DependencyClass.USER_FACTS,
        DependencyType.EVIDENCE: DependencyClass.EXTERNAL_EVIDENCE,
        DependencyType.RESOURCE: DependencyClass.DIARY_DATA,
        DependencyType.VALIDITY_STATE: DependencyClass.VALIDITY_STATE,
    }[dependency_type]


_KNOWLEDGE_TERMS = ("什么是", "为什么", "区别", "解释", "定义", "原则", "一般", "cbt-i", "stimulus control", "sleep hygiene", "what is", "why ", "difference", "explain", "definition")
_DIARY_TERMS = ("睡眠日记", "日记", "diary", "sleep diary")
_DIRECTION_TERMS = ("早点上床", "提前上床", "推迟上床", "调整上床", "上床时间", "调整起床", "bedtime")
_VALIDITY_FIELDS = ("sleep_time_or_sleep_onset_latency", "sleep_onset_latency", "wake_time")
_GENERAL_ADVICE_TERMS = ("半夜醒", "夜里醒", "夜醒后", "午睡要不要", "是否午睡", "睡眠卫生", "刺激控制", "what should i do", "should i", "is it better")
_ANALYSIS_TERMS = ("趋势", "分析", "比较", "总结", "变化", "trend", "analy", "compare", "summar")
_PERSONAL_DECISION_TERMS = ("我的作息", "我的睡眠", "我该", "是否应该", "哪个更值得", "优先改善", "my schedule", "my sleep", "should i change")


class DependencyResolver:
    """Resolve mandatory answer dependencies from goal semantics plus State."""

    def resolve(self, state: AdaptiveAgentState, requirements: RequirementSet) -> list[Dependency]:
        goal = state.goal.lower()
        dependencies: list[Dependency] = []
        diary_goal = any(term in goal for term in _DIARY_TERMS) or (
            any(term in goal for term in ("记录", "entries", "history"))
            and any(term in goal for term in _ANALYSIS_TERMS)
        )
        knowledge_goal = self._is_external_knowledge_goal(state, goal, diary_goal)
        state.semantic_provenance = self._semantic_provenance(state, knowledge_goal, diary_goal)
        semantic_ids = {item["semantic_rule_id"]: item["semantic_id"] for item in state.semantic_provenance}
        # A task-level evidence flag becomes mandatory only after state is ready;
        # explicit knowledge semantics remain mandatory even when task type is wrong.
        # Evidence is a separate dependency class: missing USER_FACTS must never
        # suppress a required external resource acquisition.
        evidence_needed = knowledge_goal or requirements.evidence_required
        if evidence_needed:
            dependencies.append(self._dependency(state, DependencyType.EVIDENCE, "external_evidence",
                (DependencyStatus.SATISFIED if state.evidence else
                 DependencyStatus.UNAVAILABLE if state.resource_status.get("external_evidence") == "unavailable" else
                 DependencyStatus.INVALID if state.resource_status.get("external_evidence") == "invalid" else
                 DependencyStatus.REQUIRED),
                "current answer scope includes external CBT-I knowledge" if knowledge_goal else "requirements signal evidence grounding",
                tuple(source for source, enabled in (("goal_semantics", knowledge_goal), ("requirements", requirements.evidence_required), ("task_type_signal", state.task_type is not None)) if enabled),
                state.goal, ("RETRIEVE",), "state evidence limitation" if not state.evidence else None,
                {"evidence_count": len(state.evidence)}, (semantic_ids.get("KNOWLEDGE_EVIDENCE_REQUIRED"),)))
        resource_needed = "sleep_diary" in requirements.resources or diary_goal
        if resource_needed:
            status = state.resource_status.get("sleep_diary", "unread")
            available = state.diary_available is not False and state.diary_authorized is not False
            if status == "loaded": resolved = DependencyStatus.SATISFIED
            elif status in {"unavailable", "invalid"}: resolved = DependencyStatus.INVALID if status == "invalid" else DependencyStatus.UNAVAILABLE
            elif not available: resolved = DependencyStatus.UNAVAILABLE
            else: resolved = DependencyStatus.AVAILABLE
            dependencies.append(self._dependency(state, DependencyType.RESOURCE, "sleep_diary", resolved,
                "goal requests diary-derived historical analysis" if diary_goal else "requirements signal diary resource",
                tuple(source for source, enabled in (("goal_semantics", diary_goal), ("requirements", "sleep_diary" in requirements.resources), ("task_type_signal", state.task_type is not None)) if enabled),
                state.goal, ("READ_DIARY",), "state diary unavailable or invalid" if resolved in {DependencyStatus.UNAVAILABLE, DependencyStatus.INVALID} else None,
                {"resource_status": status, "authorized": state.diary_authorized, "available": state.diary_available}, (semantic_ids.get("DIARY_RESOURCE_REQUIRED"),)))
        if self._needs_user_facts(state, requirements, knowledge_goal, diary_goal):
            missing = list(state.decision_missing or state.critical_missing)
            dependencies.append(self._dependency(
                state, DependencyType.USER_FACTS, "user_facts",
                DependencyStatus.SATISFIED if not missing else DependencyStatus.DEFERRED,
                "personalized goal may use user facts; missing fields remain candidate-level acquisition",
                ("goal_semantics", "requirements"), state.goal, ("ASK", "READ_DIARY"),
                "bounded answer using only supplied facts", {"missing_fields": missing},
                (semantic_ids.get("USER_FACTS_CONTEXT"),),
                dependency_class=DependencyClass.USER_FACTS, requiredness="optional"))
        if any(term in goal for term in _DIRECTION_TERMS):
            for field in _VALIDITY_FIELDS:
                if field in state.decision_missing and not requirement_is_known(field, state.facts):
                    precondition_class = requirements.precondition_classes.get(field, "DECISION_CRITICAL")
                    dependencies.append(self._dependency(state, DependencyType.VALIDITY_STATE, field, DependencyStatus.REQUIRED,
                        "direction cannot be determined without this timing context", ("goal_semantics", "state_missing"),
                        state.goal, ("READ_DIARY", "ASK"), "bounded non-directional limitation",
                        {"decision_missing": list(state.decision_missing), "precondition_class": precondition_class}, (semantic_ids.get("DIRECTIONAL_VALIDITY_CONTEXT"),)))
                    break
        existing_validity = {item.target for item in dependencies if item.dependency_type is DependencyType.VALIDITY_STATE}
        for field, precondition_class in requirements.precondition_classes.items():
            if (precondition_class in {"SAFETY_CRITICAL", "EXECUTION_CRITICAL"}
                    and field in state.decision_missing and field not in existing_validity
                    and not requirement_is_known(field, state.facts)):
                dependencies.append(self._dependency(state, DependencyType.VALIDITY_STATE, field,
                    DependencyStatus.REQUIRED, f"{precondition_class.lower()} state is required before proceeding",
                    ("requirement_precondition_class", "state_missing"), state.goal, ("ASK",),
                    "bounded safe fallback", {"decision_missing": list(state.decision_missing),
                                               "precondition_class": precondition_class}, ()))
        return dependencies

    def _is_external_knowledge_goal(self, state: AdaptiveAgentState, goal: str, diary_goal: bool) -> bool:
        if diary_goal:
            return any(term in goal for term in _KNOWLEDGE_TERMS) or "为什么" in goal or "why" in goal
        if any(term in goal for term in _KNOWLEDGE_TERMS):
            return True
        # Task type is only a semantic prior. The generic advice shape below
        # prevents a misclassified educational question from becoming a data
        # collection task, without mapping a task type directly to an action.
        if state.task_type and state.task_type.value == "KNOWLEDGE_QA":
            return True
        if any(term in goal for term in _GENERAL_ADVICE_TERMS):
            return not any(term in goal for term in _PERSONAL_DECISION_TERMS)
        return False

    def _needs_user_facts(self, state: AdaptiveAgentState, requirements: RequirementSet,
                          knowledge_goal: bool, diary_goal: bool) -> bool:
        goal = state.goal.lower()
        mixed_personal_knowledge = any(term in goal for term in _PERSONAL_DECISION_TERMS)
        if knowledge_goal and not diary_goal and not mixed_personal_knowledge:
            return False
        if state.task_type is None:
            return bool(requirements.decision_fields or requirements.critical)
        return state.task_type.value in {"CAUSE_ASSESSMENT", "PERSONALIZED_DECISION"} or bool(
            requirements.decision_fields or requirements.critical)

    def _semantic_provenance(self, state: AdaptiveAgentState, knowledge: bool, diary: bool) -> list[dict[str, object]]:
        goal = state.goal
        rules: list[tuple[str, bool, str]] = [
            ("KNOWLEDGE_EVIDENCE_REQUIRED", knowledge, "goal requests general external CBT-I knowledge"),
            ("DIARY_RESOURCE_REQUIRED", diary, "goal requests diary-derived historical analysis"),
            ("DIRECTIONAL_VALIDITY_CONTEXT", any(term in goal.lower() for term in _DIRECTION_TERMS), "goal requests a directional sleep-timing decision"),
            ("USER_FACTS_CONTEXT", self._needs_user_facts(state, RequirementSet((), (), False), knowledge, diary), "goal may use user-specific facts"),
        ]
        items = []
        for ordinal, (rule, matched, reason) in enumerate(rules, 1):
            if matched:
                terms = _KNOWLEDGE_TERMS if rule.startswith("KNOWLEDGE") else _DIARY_TERMS if rule.startswith("DIARY") else _DIRECTION_TERMS
                text = next((term for term in terms if term in goal.lower()), goal)
                items.append({"semantic_id": f"sem_{state.goal_id or 'goal'}_r{state.state_revision}_{ordinal}", "semantic_rule_id": rule,
                              "matched_text": text, "semantic_reason": reason, "certainty": "HIGH", "match_method": "deterministic_rule"})
        return items

    def _dependency(self, state: AdaptiveAgentState, dependency_type: DependencyType, target: str,
                    status: DependencyStatus, reason: str, source: tuple[str, ...], required_for_goal: str,
                    satisfiable_by: tuple[str, ...], fallback: str | None, provenance: dict[str, object],
                    semantic_ids: tuple[str | None, ...], dependency_class: DependencyClass | None = None,
                    requiredness: str = "required") -> Dependency:
        prior = next((item for item in state.dependencies_considered
                      if item.get("dependency_type") == dependency_type.value and item.get("target") == target), None)
        dependency_id = f"dep_{state.goal_id or 'goal'}_r{state.state_revision}_{dependency_type.value.lower()}_{target}"
        inherited = prior.get("supersedes_dependency_id") if prior and prior.get("dependency_id") == dependency_id else None
        return Dependency(dependency_id, dependency_type, target, status,
                          reason, source, required_for_goal, satisfiable_by, fallback, provenance,
                          tuple(item for item in semantic_ids if item),
                          inherited or (prior.get("dependency_id") if prior and prior.get("dependency_id") != dependency_id else None),
                          dependency_class or _canonical_class(dependency_type), requiredness)


def validity_critical_fields(state: AdaptiveAgentState, requirements: RequirementSet) -> list[str]:
    return [item.target for item in DependencyResolver().resolve(state, requirements)
            if item.dependency_type is DependencyType.VALIDITY_STATE and item.status is DependencyStatus.REQUIRED]
