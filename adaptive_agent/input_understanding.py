"""LLM extraction plus conservative deterministic fact normalization."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Annotated, Protocol, TypedDict

from .state import AdaptiveAgentState, TaskType
from .requirements import normalize_target


FACT_FIELDS = (
    "bedtime", "sleep_time", "sleep_onset_latency", "wake_time", "total_sleep_time",
    "nighttime_awakenings", "awake_duration", "recent_sleep_pattern", "caffeine", "nap", "exercise",
    "screen_before_bed", "perceived_stress",
)
_DIRECTIONAL_BEDTIME_TERMS = ("早点上床", "更早上床", "提前上床", "调整上床时间")


class RawFactsOutput(TypedDict, total=False):
    bedtime: Annotated[str | None, "Explicit clock time when the user gets into bed, e.g. 23:00."]
    sleep_time: Annotated[str | None, "Explicit clock time when the user falls asleep, e.g. 00:00."]
    sleep_onset_latency: Annotated[int | None, "Explicit minutes from bed to sleep; do not infer."]
    wake_time: Annotated[str | None, "Explicit wake-up clock time, e.g. 07:00."]
    total_sleep_time: Annotated[int | None, "Explicit total minutes slept; do not infer."]
    nighttime_awakenings: Annotated[int | None, "Explicit nightly awakening count; do not infer."]
    awake_duration: Annotated[int | None, "Explicit minutes awake during an awakening; do not infer."]
    recent_sleep_pattern: Annotated[str | None, "Explicit recent duration or repeated sleep pattern."]
    caffeine: Annotated[str | bool | None, "Explicit caffeine consumption or explicit non-use."]
    nap: Annotated[str | bool | None, "Explicit nap behavior or explicit non-use."]
    exercise: Annotated[str | bool | None, "Explicit exercise behavior or explicit non-use."]
    screen_before_bed: Annotated[str | bool | None, "Explicit pre-bed screen behavior or explicit non-use."]
    perceived_stress: Annotated[str | bool | None, "Explicit stress, worry, or anxiety statement."]


@dataclass(frozen=True)
class Understanding:
    goal: str | None
    task_type: TaskType | None
    facts: dict[str, Any]
    is_new_goal: bool = False
    raw_facts: dict[str, Any] = field(default_factory=dict)
    fact_sources: dict[str, dict[str, Any]] = field(default_factory=dict)
    target_updates: dict[str, dict[str, Any]] = field(default_factory=dict)
    user_input: str = ""


class InputUnderstander(Protocol):
    def understand(self, user_input: str, prior_state: AdaptiveAgentState | None = None) -> Understanding:
        """Extract only facts present in this text; unknown fields remain null."""


class StructuredOutput(TypedDict):
    goal: str
    task_type: str
    facts: RawFactsOutput
    is_new_goal: bool


class LLMInputUnderstander:
    """LLM provides goal/task/raw facts; deterministic code validates fact values."""

    system_prompt = """Extract CBT-I conversation state. Return one task_type from
KNOWLEDGE_QA, CAUSE_ASSESSMENT, PERSONALIZED_DECISION, DATA_ANALYSIS and a tightly scoped goal.
Facts must be copied only when explicit in the current user input: 60 minutes to fall asleep
is sleep_onset_latency=60; two cups of coffee is caffeine; "recent two weeks" is a
recent_sleep_pattern. Do not omit explicit clock times, durations, counts, caffeine, naps,
exercise, screens, or stress. Do not guess, estimate, diagnose, invent diary data, or fill
unstated fields. Use null for every unknown fact. Set is_new_goal true only for a clearly
different task; otherwise retain the ongoing goal."""

    def __init__(self, model: Any) -> None:
        # The configured DeepSeek-compatible endpoint does not support the SDK's
        # json_schema default; tool/function calling preserves the explicit schema.
        self._model = model.with_structured_output(StructuredOutput, method="function_calling")

    def understand(self, user_input: str, prior_state: AdaptiveAgentState | None = None) -> Understanding:
        context = ""
        if prior_state and prior_state.goal:
            context = f"\nExisting goal: {prior_state.goal}\nKnown facts: {prior_state.facts}"
        response = self._model.invoke(f"{self.system_prompt}{context}\nUser input: {user_input}")
        return understanding_from_mapping(response, user_input, prior_state)


_TIME = r"(?P<period>晚上|夜里|夜晚|凌晨|早上|早晨|上午|中午|下午|at night|in the morning|in the evening|around midnight)?\s*(?:at\s*)?(?P<hour>\d{1,2})(?:[:：](?P<minute>\d{2})|点半)?\s*(?:点|时|o'clock)?\s*(?P<ampm>a\.m\.|p\.m\.|am|pm)?"


def _clock(match: re.Match[str]) -> str:
    hour, minute = int(match["hour"]), int(match["minute"] or (30 if "点半" in match.group(0) else 0))
    period = match["period"] or ""
    ampm = (match["ampm"] or "").lower()
    if ampm == "pm" and hour < 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    if period in {"晚上", "夜里", "夜晚", "下午", "at night", "in the evening"} and hour < 12:
        hour += 12
    if period in {"凌晨", "around midnight"} and hour == 12:
        hour = 0
    return f"{hour % 24:02d}:{minute:02d}"


def _minutes(value: str, unit: str) -> int:
    return round(float(value) * (60 if unit in {"小时", "hour", "hours"} else 1))


def _duration_unit(unit: str) -> str:
    unit = unit.lower()
    return "小时" if unit in {"小时", "hour", "hours"} else "分钟"


_CN_DIGITS = {"零": 0, "一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _number(value: str) -> float:
    if value.isdigit() or "." in value:
        return float(value)
    if value in _CN_DIGITS:
        return float(_CN_DIGITS[value])
    if value.startswith("十"):
        return float(10 + (_CN_DIGITS.get(value[1:], 0) if len(value) > 1 else 0))
    if "十" in value:
        left, right = value.split("十", 1)
        return float(_CN_DIGITS.get(left, 1) * 10 + _CN_DIGITS.get(right, 0))
    return float("nan")


def _source(kind: str, text: str, source_fields: tuple[str, ...] = (), raw_value: Any = None,
            normalized_value: Any = None, certainty: str = "exact") -> dict[str, Any]:
    return {
        "kind": kind, "source_type": "user_explicit" if kind == "explicit" else "user_derived",
        "text": text, "raw_value": text if raw_value is None else raw_value,
        "normalized_value": normalized_value, "certainty": certainty,
        "source_turn": None, "source_fields": list(source_fields),
    }


def extract_explicit_facts(text: str) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Recognize only narrow, explicit statements; absence intentionally yields no fact."""
    facts: dict[str, Any] = {}
    sources: dict[str, dict[str, Any]] = {}

    def capture(name: str, value: Any, match: re.Match[str], kind: str = "explicit",
                certainty: str = "exact") -> None:
        facts[name] = value
        sources[name] = _source(kind, match.group(0), raw_value=match.group(0),
                                normalized_value=value, certainty=certainty)

    for name, suffix in (("bedtime", r"\s*(?:左右)?\s*(?:上床|躺下|go to bed|in bed)"),
                         ("sleep_time", r"\s*(?:后)?\s*(?:才)?\s*(?:睡着|入睡|fall asleep|asleep)"),
                         ("wake_time", r"\s*(?:左右)?\s*(?:起床|醒来|wake(?: up)?|awake)")):
        match = re.search(_TIME + suffix, text)
        if match:
            value = _clock(match)
            context = text[max(0, match.start() - 4):match.end() + 4]
            certainty = "approximate" if "左右" in context or "around" in context.lower() or "后才" in context else "exact"
            if certainty == "approximate":
                value = {"uncertainty": certainty, "value": value}
            capture(name, value, match, certainty=certainty)

    late_sleep = re.search(_TIME + r"\s*后\s*(?:才)?睡", text, re.I)
    if late_sleep:
        value = {"uncertainty": "approximate", "value": _clock(late_sleep)}
        capture("sleep_time", value, late_sleep, certainty="approximate")

    for name, action in (("bedtime", r"(?:go to bed|in bed)"), ("wake_time", r"(?:wake(?: up)?|awake)")):
        match = re.search(action + r"\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(a\.m\.|p\.m\.|am|pm)", text, re.I)
        if match:
            hour = int(match.group(1)); minute = int(match.group(2) or 0)
            if match.group(3).lower().startswith("p") and hour < 12: hour += 12
            if match.group(3).lower().startswith("a") and hour == 12: hour = 0
            capture(name, f"{hour:02d}:{minute:02d}", match)

    # Preserve a clock range instead of silently selecting an endpoint.
    range_match = re.search(r"(?P<start>\d{1,2})(?:[:：](?P<smin>\d{2}))?\s*(?:到|至|[-–])\s*(?P<end>\d{1,2})(?:[:：](?P<emin>\d{2}))?\s*点?(?:醒来|起床|wake(?: up)?|醒)", text, re.I)
    if range_match:
        start = f"{int(range_match['start']):02d}:{int(range_match['smin'] or 0):02d}"
        end = f"{int(range_match['end']):02d}:{int(range_match['emin'] or 0):02d}"
        value = {"uncertainty": "range", "low": start, "high": end}
        capture("wake_time", value, range_match, certainty="range")
    approx = re.search(r"(?:大约|大概|左右|around|about|approximately)\s*(午夜|midnight|\d{1,2}(?::\d{2})?\s*(?:点|o'clock)?)", text, re.I)
    if approx and ("上床" in text or "go to bed" in text.lower()):
        token = approx.group(1)
        if token in {"午夜", "midnight"}:
            value = "00:00"
        else:
            hour, minute = re.match(r"(\d{1,2})(?::(\d{2}))?", token).groups()
            value = f"{int(hour):02d}:{int(minute or 0):02d}"
        value = {"uncertainty": "approximate", "value": value}
        capture("bedtime", value, approx, certainty="approximate")

    match = re.search(r"(?:需要|要|约|大约|通常|takes?|about|approximately)?\s*(超过|more than|over)?\s*([0-9一二两三四五六七八九十]+(?:\.\d+)?)\s*个?\s*(分钟|分|小时|minutes?|hours?)\s*(?:才|才能|to)?\s*(?:睡着|入睡|fall asleep)", text, re.I)
    reverse = None
    if match:
        raw_number, unit = match.group(2), match.group(3)
        minutes = round(_number(raw_number) * (60 if _duration_unit(unit) == "小时" else 1))
        capture("sleep_onset_latency", minutes, match)
    else:
        reverse = re.search(r"(?:入睡|睡着|fall asleep).{0,8}(?:超过|more than|over)\s*([0-9一二两三四五六七八九十]+(?:\.\d+)?)\s*(分钟|分|小时|minutes?|hours?)", text, re.I)
        if reverse:
            unit = _duration_unit(reverse.group(2))
            capture("sleep_onset_latency", round(_number(reverse.group(1)) * (60 if unit == "小时" else 1)), reverse)
    if not match and not reverse and isinstance(facts.get("bedtime"), str) and isinstance(facts.get("sleep_time"), str):
        start = int(facts["bedtime"][:2]) * 60 + int(facts["bedtime"][3:])
        end = int(facts["sleep_time"][:2]) * 60 + int(facts["sleep_time"][3:])
        facts["sleep_onset_latency"] = (end - start) % (24 * 60)
        sources["sleep_onset_latency"] = _source("derived", "clock-time difference",
                                                    ("bedtime", "sleep_time"), normalized_value=facts["sleep_onset_latency"])

    match = re.search(r"(?:总睡眠时间|睡眠时长|总共睡(?:了)?|实际睡(?:了)?|每晚睡|total sleep|sleep)\s*(?:是|为|约|is|of)?\s*([0-9一二两三四五六七八九十]+(?:\.\d+)?)\s*(分钟|分|小时|minutes?|hours?)", text, re.I)
    if match:
        capture("total_sleep_time", round(_number(match.group(1)) * (60 if _duration_unit(match.group(2)) == "小时" else 1)), match)
    match = re.search(r"(?:夜里|夜间|半夜|每晚|at night|nightly).{0,15}?醒(?:来|了)?\s*([0-9一二两三四五六七八九十]+)\s*(?:次|times?)", text, re.I)
    if match:
        capture("nighttime_awakenings", int(_number(match.group(1))), match)
    match = re.search(r"(?:醒着|清醒|awake|awakened)\s*(?:了|for)?\s*([0-9一二两三四五六七八九十]+(?:\.\d+)?)\s*(分钟|分|小时|minutes?|hours?)", text, re.I)
    if match:
        capture("awake_duration", round(_number(match.group(1)) * (60 if _duration_unit(match.group(2)) == "小时" else 1)), match)

    match = re.search(r"(?:已经这样(?:两个|两|2)星期|最近(?:两|2)周(?:都是这样)?|持续了?大概?(?:14天|两周|两个星期)|这个情况持续.{0,8}(?:14天|两周|两个星期))", text)
    if match:
        capture("recent_sleep_pattern", match.group(0), match)

    patterns = {
        "caffeine": r"(?:下午|午饭后|每天|最近|晚上)?\s*(?:喝|饮用|来一杯)\s*(?:\d+|一|两)?\s*(?:咖啡|拿铁|茶|能量饮料)|(?:咖啡|拿铁)[^。；，]{0,6}(?:每天|经常|喝)|(?:每天\s*)?(?:\d+|一|两)杯(?:咖啡|拿铁|茶|能量饮料)",
        "exercise": r"(?:我|最近|每天|每周)[^。；，]{0,12}(?:运动|锻炼|跑步|健身)",
        "screen_before_bed": r"(?:睡前[^。；，]{0,10}(?:刷手机|看手机|使用[^。；，]{0,6}屏幕)|(?:刷手机|看手机)[^。；，]{0,10}睡前)",
        "perceived_stress": r"(?:我|最近|工作|睡前|before bed|at night)[^。；，,.]{0,20}(?:压力很大|焦虑|担心|紧张|worry about work|stressed|anxious)",
    }
    for name, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            capture(name, match.group(0), match)
    match = re.search(r"(?:不|没有|从不)\s*(?:午睡|睡午觉|小睡)", text)
    if match:
        capture("nap", False, match)
    else:
        match = re.search(r"(?:会|经常|每天|偶尔|有时)[^。；，]{0,8}(?:午睡|睡午觉|小睡)", text)
        if match:
            capture("nap", match.group(0), match)
    return facts, sources


def normalize_facts(raw_facts: dict[str, Any], user_input: str) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    """Validate only facts grounded by explicit text, then calculate traceable clocks."""
    del raw_facts  # Raw LLM output remains observable but never overrides grounded parsing.
    explicit, sources = extract_explicit_facts(user_input)
    return {field: explicit.get(field) for field in FACT_FIELDS}, sources


def normalize_goal(raw_goal: Any, user_input: str) -> str | None:
    """Keep explicit supported goal phrases stable when an LLM translates them."""
    if any(term in user_input for term in _DIRECTIONAL_BEDTIME_TERMS):
        return "判断是否应该提前上床"
    return str(raw_goal) if raw_goal else None


def understanding_from_mapping(value: dict[str, Any], user_input: str = "",
                               prior_state: AdaptiveAgentState | None = None) -> Understanding:
    """Keep raw LLM facts separate from validated/derived facts before State merge."""
    raw_task_type = value.get("task_type")
    try:
        task_type = TaskType(raw_task_type) if raw_task_type else None
    except ValueError:
        task_type = None
    raw_facts = {field: (value.get("facts") or {}).get(field) for field in FACT_FIELDS}
    facts, fact_sources = normalize_facts(raw_facts, user_input)
    target_updates: dict[str, dict[str, Any]] = {}
    unavailable = re.search(r"不知道|不清楚|不记得|无法提供|不方便回答|不愿提供|暂时无法|don't know|not sure|can't provide|cannot provide|prefer not to say", user_input, re.I)
    if unavailable and prior_state and prior_state.action_history and prior_state.action_history[-1].get("action") == "ASK":
        target = normalize_target(prior_state.action_history[-1].get("target"))
        if target:
            target_updates[target] = {"status": "UNAVAILABLE", "source_turn": prior_state.turn_index + 1,
                                      "reason": "user explicitly cannot or declines to provide the requested fact"}
    return Understanding(normalize_goal(value.get("goal"), user_input), task_type, facts,
                         bool(value.get("is_new_goal", False)), raw_facts, fact_sources, target_updates, user_input)


def apply_understanding(state: AdaptiveAgentState, understanding: Understanding) -> AdaptiveAgentState:
    """Merge validated new facts only; null/raw omissions cannot erase prior facts."""
    if understanding.goal:
        state.goal = understanding.goal
    if understanding.task_type:
        state.task_type = understanding.task_type
    for name, value in understanding.facts.items():
        if value is not None and value != "":
            incoming = understanding.fact_sources.get(name, {})
            existing = state.fact_sources.get(name, {})
            # Distinct conflicting user assertions are made explicit, never silently overwritten.
            if existing.get("source_type") == "user_explicit" and incoming.get("source_type") == "user_derived":
                continue
            correction_turn = bool(re.search(r"其实|更正|刚才说错|不是.{0,8}(?:是|而是)|actually|correction|i meant", understanding.user_input, re.I))
            if existing.get("source_type") == "user_explicit" and incoming.get("source_type") == "user_explicit" and state.facts.get(name) != value and not correction_turn:
                prior = state.fact_conflicts.setdefault(name, [{"value": state.facts[name], "source": existing}])
                prior.append({"value": value, "source": incoming})
                state.facts[name] = {"uncertainty": "conflict", "values": [entry["value"] for entry in prior]}
                state.fact_status[name] = "INVALID"
                state.fact_sources[name] = {"source_type": "conflict", "conflicting_sources": prior}
                continue
            if incoming:
                incoming = dict(incoming)
                incoming["source_turn"] = state.turn_index or incoming.get("source_turn")
            state.facts[name] = value
            state.fact_sources[name] = incoming
            state.fact_status[name] = "DERIVED" if incoming.get("source_type") == "user_derived" else "ASSERTED"
            canonical = normalize_target(name)
            if canonical:
                state.target_status.pop(canonical, None)
    for target, status in understanding.target_updates.items():
        state.target_status[target] = dict(status)
    return state
