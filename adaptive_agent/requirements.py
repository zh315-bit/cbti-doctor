"""Configurable requirements and missing-information calculation."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from .state import TaskType


DEFAULT_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "KNOWLEDGE_QA": {"critical": [], "secondary": [], "evidence_required": True},
    "CAUSE_ASSESSMENT": {
        "critical": ["bedtime", "sleep_time_or_sleep_onset_latency", "wake_time", "recent_sleep_pattern"],
        "secondary": ["caffeine", "nap", "exercise", "screen_before_bed", "perceived_stress"],
        "evidence_required": True,
    },
    "PERSONALIZED_DECISION": {
        "critical": ["bedtime", "sleep_onset_latency", "wake_time", "total_sleep_time", "nighttime_awakenings", "recent_sleep_pattern"],
        "secondary": ["perceived_stress", "nap", "caffeine"], "evidence_required": True,
    },
    "DATA_ANALYSIS": {"critical": [], "secondary": [], "evidence_required": False, "diary_preferred": True,
                      "resources": ["sleep_diary"]},
}


@dataclass(frozen=True)
class RequirementSet:
    critical: tuple[str, ...]
    secondary: tuple[str, ...]
    evidence_required: bool
    diary_preferred: bool = False
    resources: tuple[str, ...] = ()
    decision_fields: tuple[str, ...] | None = None
    answer_scope: str = "仅在已知事实和证据范围内回答；不得推断未知事实。"
    requirement_ids: dict[str, str] = field(default_factory=dict)
    classifications: dict[str, str] = field(default_factory=dict)
    semantic_adjustments: tuple[dict[str, str], ...] = ()
    is_effective: bool = False
    precondition_classes: dict[str, str] = field(default_factory=dict)


# Goal-level requirements, not task-to-action rules. A directional discussion is
# deliberately narrower than prescribing an exact bedtime/sleep-restriction plan.
BEDTIME_DIRECTION_TERMS = ("早点上床", "更早上床", "提前上床", "调整上床时间")
PRESCRIPTION_TERMS = ("具体", "几点", "处方", "睡眠限制", "睡眠窗口", "精确", "方案")
FIELD_SIGNALS = {
    "bedtime": ("上床",),
    "sleep_onset_latency": ("入睡", "睡着"),
    "sleep_time_or_sleep_onset_latency": ("入睡", "睡着"),
    "wake_time": ("起床", "早醒"),
    "total_sleep_time": ("时长", "睡多久"),
    "nighttime_awakenings": ("夜醒", "半夜", "醒几次"),
    "recent_sleep_pattern": ("趋势", "规律", "最近", "一周"),
    "caffeine": ("咖啡", "咖啡因", "茶"),
    "nap": ("午睡",), "exercise": ("运动", "锻炼"),
    "screen_before_bed": ("屏幕", "手机"),
    "perceived_stress": ("压力", "焦虑", "担心"),
}


def resolve_requirements(base: RequirementSet, goal: str) -> RequirementSet:
    """Make the supported decision explicit; unknown goals retain conservative needs."""
    fields = base.decision_fields if base.decision_fields is not None else base.critical
    scope = base.answer_scope
    if base.critical and any(term in goal for term in BEDTIME_DIRECTION_TERMS) and not any(
        term in goal for term in PRESCRIPTION_TERMS
    ):
        fields = ("bedtime", "sleep_time_or_sleep_onset_latency", "wake_time")
        scope = ("仅讨论是否提前上床的方向和现有作息约束；不指定具体新上床时间、"
                 "睡眠窗口或睡眠限制处方。不把未收集的睡眠总量、夜醒或近期规律当作已知。")
    # An explicitly named factor can change the current decision even if it was
    # only secondary in the task-level defaults.
    explicit = tuple(name for name in base.critical + base.secondary
                     if any(term in goal for term in FIELD_SIGNALS.get(name, ())))
    # bedtime/latency are already covered by the directional alternative group.
    if "sleep_time_or_sleep_onset_latency" in fields:
        explicit = tuple(name for name in explicit if name != "sleep_onset_latency")
    fields = tuple(dict.fromkeys(fields + explicit))
    return replace(base, decision_fields=fields, answer_scope=scope)


def synchronize_requirements(base: RequirementSet, state: Any, dependencies: list[Any]) -> RequirementSet:
    """Return goal-compatible optional requirements; dependencies remain mandatory elsewhere.

    This is deliberately a pure synchronization boundary.  It never chooses an
    action and never turns a missing optional field into an ASK.
    """
    semantic_rules = {item.get("semantic_rule_id") for item in state.semantic_provenance}
    knowledge_only = "KNOWLEDGE_EVIDENCE_REQUIRED" in semantic_rules and not any(
        rule in semantic_rules for rule in ("DIARY_RESOURCE_REQUIRED", "DIRECTIONAL_VALIDITY_CONTEXT")
    )
    diary_goal = "DIARY_RESOURCE_REQUIRED" in semantic_rules
    active_critical = base.critical
    active_secondary = base.secondary
    active_decision = base.decision_fields or base.critical
    adjustments: list[dict[str, str]] = []
    # A general knowledge goal can retain supplied facts as State/answer context,
    # but task-type sleep-schedule fields do not become optional acquisition work.
    if knowledge_only:
        suppressed = tuple(dict.fromkeys(active_critical + active_secondary + active_decision))
        active_critical = (); active_secondary = (); active_decision = ()
        if suppressed:
            adjustments.append({"rule_id": "KNOWLEDGE_OPTIONAL_FIELDS_SUPPRESSED", "reason": "goal requests external knowledge, not personal fact acquisition"})
    elif diary_goal:
        # The RESOURCE dependency governs data acquisition.  Do not duplicate it
        # with legacy task-type user fact collection.
        active_decision = ()
        adjustments.append({"rule_id": "DIARY_RESOURCE_OWNS_ACQUISITION", "reason": "diary dependency is evaluated as a resource precondition"})
    dependency_targets = {getattr(item, "target", None) for item in dependencies}
    classifications: dict[str, str] = {}
    requirement_ids: dict[str, str] = {}
    for name in dict.fromkeys(active_critical + active_secondary + active_decision):
        requirement_ids[name] = f"req_{state.goal_id or 'goal'}_{name}"
        classifications[name] = "mandatory" if name in dependency_targets else "useful_optional"
    for name in dict.fromkeys(base.critical + base.secondary + (base.decision_fields or base.critical)):
        if name not in classifications:
            requirement_ids[name] = f"req_{state.goal_id or 'goal'}_{name}"
            classifications[name] = "irrelevant"
    return replace(base, critical=active_critical, secondary=active_secondary,
                   decision_fields=active_decision, requirement_ids=requirement_ids,
                   classifications=classifications, semantic_adjustments=tuple(adjustments),
                   # A diary semantic goal owns its resource dependency; an
                   # incompatible task-type knowledge flag must not add a second
                   # stale retrieval requirement.
                   evidence_required=False if diary_goal else base.evidence_required,
                   is_effective=True)


def load_requirements(path: Path | None = None) -> dict[TaskType, RequirementSet]:
    config_path = path or Path(__file__).resolve().parents[1] / "configs" / "requirements.yaml"
    try:
        import yaml
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except ModuleNotFoundError:
        # The project dependency provides PyYAML in production. This fallback keeps
        # the pure-domain modules testable with the system Python as well.
        raw = {"task_types": DEFAULT_REQUIREMENTS}
    return {
        TaskType(name): RequirementSet(
            critical=tuple(value.get("critical", [])),
            secondary=tuple(value.get("secondary", [])),
            evidence_required=bool(value.get("evidence_required", False)),
            diary_preferred=bool(value.get("diary_preferred", False)),
            resources=tuple(value.get("resources", [])),
        )
        for name, value in raw["task_types"].items()
    }


def is_known(value: object) -> bool:
    return (value is not None and value != "" and value != [] and value != {}
            and not (isinstance(value, dict) and value.get("uncertainty") in {"invalid", "conflict"}))


def normalize_target(target: str | None) -> str | None:
    """Canonicalize semantic aliases at every state/dependency boundary."""
    if target in {"sleep_time", "sleep_onset_latency", "sleep_time_or_sleep_onset_latency"}:
        return "sleep_time_or_sleep_onset_latency"
    aliases = {"nap_duration": "nap", "caffeine_intake": "caffeine",
               "bedtime_time": "bedtime", "wake_up_time": "wake_time",
               "recent_sleep_pattern": "recent_sleep_pattern"}
    return aliases.get(target, target)


def requirement_is_known(requirement: str, facts: dict[str, object]) -> bool:
    """The cause-assessment requirement accepts either a clock time or latency."""
    requirement = normalize_target(requirement) or requirement
    if requirement == "sleep_time_or_sleep_onset_latency":
        return is_known(facts.get("sleep_time")) or is_known(facts.get("sleep_onset_latency"))
    return is_known(facts.get(requirement))


def calculate_missing(requirements: RequirementSet, facts: dict[str, object]) -> tuple[list[str], list[str]]:
    """Unknown means null/empty; zero and false are valid collected values."""
    return (
        [name for name in requirements.critical if not requirement_is_known(name, facts)],
        [name for name in requirements.secondary if not requirement_is_known(name, facts)],
    )
