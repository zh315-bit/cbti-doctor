"""Grounded final-answer generation from State facts and relevant evidence only."""

from __future__ import annotations

import re
from typing import Any

from .state import AdaptiveAgentState, TaskType
from .requirements import RequirementSet, requirement_is_known


def authorize_final_answer(state: AdaptiveAgentState, requirements: RequirementSet) -> dict[str, Any]:
    """Authorize the proposed answer scope independently from resource acquisition."""
    dependencies = state.dependencies_considered
    material_missing: set[str] = set()
    detail_missing: set[str] = set()

    for item in dependencies:
        if item.get("dependency_type") == "VALIDITY_STATE" and item.get("status") != "SATISFIED":
            material_missing.add(str(item.get("target")))

    decision_fields = tuple(requirements.decision_fields or ())
    for field in decision_fields:
        status = (state.fact_status.get(field) or
                  state.target_status.get(field, {}).get("status"))
        source_type = state.fact_sources.get(field, {}).get("source_type")
        valid_status = (
            status == "ASSERTED" and source_type == "user_explicit"
            or status == "DERIVED" and source_type == "user_derived"
            or status == "RETRIEVED" and source_type == "diary"
            and state.diary_projection.get("projection_status") == "valid"
        )
        if status is None and source_type == "user_explicit":
            valid_status = True
        estimate = state.information_estimates.get(field, {})
        material = (
            estimate.get("decision_impact") in {"decision_changing", "answer_scope_changing"}
            or requirements.precondition_classes.get(field) in {"SAFETY_CRITICAL", "EXECUTION_CRITICAL"}
        )
        if material and (not valid_status or not requirement_is_known(field, state.facts)):
            material_missing.add(field)
        elif ((not valid_status or not requirement_is_known(field, state.facts))
              and estimate.get("decision_impact") == "detail_improving"):
            detail_missing.add(field)
        if status == "INVALID" and field in decision_fields:
            material_missing.add(field)

    unresolved_resources = [
        item for item in dependencies
        if item.get("dependency_type") in {"EVIDENCE", "RESOURCE"}
        and item.get("status") in {"REQUIRED", "AVAILABLE", "UNAVAILABLE", "INVALID"}
    ]
    invalid_conflicts = sorted(
        field for field in material_missing
        if state.fact_status.get(field) == "INVALID"
        or state.target_status.get(field, {}).get("status") == "INVALID"
        or bool(state.fact_conflicts.get(field))
    )
    safe_fallback = bool(requirements.answer_scope.strip()) and any(
        bool(item.get("fallback")) for item in dependencies
        if item.get("dependency_type") in {"USER_FACTS", "VALIDITY_STATE", "EVIDENCE", "RESOURCE"}
    )
    acquisition_available = any(
        item.get("status") in {"REQUIRED", "AVAILABLE"}
        and item.get("dependency_type") in {"EVIDENCE", "RESOURCE", "VALIDITY_STATE"}
        for item in dependencies
    )

    if not material_missing and not unresolved_resources and not detail_missing:
        status = "AUTHORIZED_FULL"
        reason = "all material answer dependencies are satisfied"
    elif safe_fallback:
        status = "AUTHORIZED_BOUNDED"
        reason = "safe bounded scope excludes unresolved dependencies or optional detail"
    elif material_missing or unresolved_resources:
        if acquisition_available:
            status = "BLOCKED_NEEDS_INFORMATION"
            reason = "a material dependency remains resolvable and no safe bounded scope is available"
        else:
            status = "BLOCKED_UNSAFE_OR_INVALID"
            reason = "no safe bounded scope or valid acquisition route remains"
    elif detail_missing and acquisition_available:
        status = "BLOCKED_NEEDS_INFORMATION"
    else:
        status = "BLOCKED_UNSAFE_OR_INVALID"

    if invalid_conflicts and status == "AUTHORIZED_FULL":
        status = "AUTHORIZED_BOUNDED" if requirements.answer_scope.strip() else "BLOCKED_UNSAFE_OR_INVALID"
        reason = "invalid or conflicting state excludes the affected individualized scope"
    return {
        "status": status,
        "reason": reason,
        "material_missing": sorted(field for field in material_missing if field and field != "None"),
        "detail_missing": sorted(detail_missing),
        "unresolved_resource_dependencies": [
            {"dependency_type": item.get("dependency_type"), "target": item.get("target"),
             "status": item.get("status")} for item in unresolved_resources
        ],
        "invalid_conflicts": invalid_conflicts,
        "answer_scope": state.answer_scope,
    }


def bounded_authorization_response(authorization: dict[str, Any]) -> str:
    """Deterministic non-personalized fallback; does not call a generative model."""
    if authorization.get("status") == "BLOCKED_UNSAFE_OR_INVALID":
        return "当前状态不足以安全支持所请求的结论，因此我不能生成该项个性化判断。"
    unavailable = authorization.get("unresolved_resource_dependencies", [])
    if any(item.get("dependency_type") == "RESOURCE" and item.get("status") in {"UNAVAILABLE", "INVALID"}
           for item in unavailable):
        return "所需资源目前无法补足，因此我不能据此生成个性化分析或结论。"
    if any(item.get("dependency_type") == "EVIDENCE" and item.get("status") in {"UNAVAILABLE", "INVALID"}
           for item in unavailable):
        return "目前无法获得所需外部证据；我不能据此给出确定结论或个性化建议。"
    return ("我可以提供一般性、非个体化的信息；但目前仍缺少会影响个体化判断的已验证资料，"
            "所以不能据此判断哪项具体行动适合你。")
from .facts import duration_between


_QUANTITY = re.compile(r"\d+(?:\.\d+)?\s*(?:%|％|小时|分钟|分|天|周|次)")
_CLINICAL_QUANTIFIER = re.compile(r"(?:正常|异常|偏低|偏高|阈值|标准|参考|建议|推荐|应当|需要)")
_GENERIC_WORDS = {"睡眠", "日记", "资料", "信息", "问题", "分析", "解释", "什么", "为什么", "一般",
                  "sleep", "diary", "about", "what", "why", "explain", "information"}


def _numbers(text: str) -> set[str]:
    normalized = set()
    for item in _QUANTITY.findall(text):
        item = item.replace("％", "%").replace(" ", "")
        normalized.add(item[:-1] + "分钟" if item.endswith("分") and not item.endswith("分钟") else item)
    return normalized


def _topic_tokens(text: str) -> set[str]:
    """Lexical fallback for evidence without retrieval lineage, not a topic whitelist."""
    words = set(re.findall(r"[a-z][a-z0-9-]{2,}", text.lower()))
    for run in re.findall(r"[\u4e00-\u9fff]{2,}", text):
        words.update(run[index:index + size] for size in (2, 3, 4)
                     for index in range(len(run) - size + 1))
    return {word for word in words if word not in _GENERIC_WORDS}


def relevant_evidence(goal: str, evidence: list[str]) -> list[str]:
    """Backward-compatible content-only view; projection also uses tool lineage."""
    goal_tokens = _topic_tokens(goal)
    return [item for item in evidence if isinstance(item, str) and
            bool(goal_tokens & _topic_tokens(item))]


def project_evidence(state: AdaptiveAgentState) -> tuple[list[str], list[dict[str, Any]]]:
    """Project goal-relevant, valid evidence and explain every exclusion."""
    included: list[str] = []
    audit: list[dict[str, Any]] = []
    active = any(item.get("dependency_type") == "EVIDENCE" and
                 item.get("status") in {"SATISFIED", "REQUIRED", "AVAILABLE"}
                 for item in state.dependencies_considered)
    excluded_topics = re.findall(r"不(?:讨论|涉及|回答)([\u4e00-\u9fff]{2,12})", state.answer_scope)
    for index, item in enumerate(state.evidence):
        source = next((entry for entry in state.evidence_sources
                       if entry.get("evidence") == item), {})
        status = source.get("projection_status", "valid")
        if not isinstance(item, str) or not item.strip():
            reason = "invalid"
        elif status in {"invalid", "unavailable"}:
            reason = status
        elif item in included:
            reason = "duplicate"
        elif any(topic in item for topic in excluded_topics):
            reason = "outside answer_scope"
        elif (active and source.get("source_type") == "RAG" and
              source.get("goal_id") == state.goal_id and source.get("retrieval_query")):
            reason = None  # Same-goal retrieval, verified by action/tool lineage.
        elif item in relevant_evidence(state.goal, [item]):
            reason = None
        else:
            reason = "irrelevant"
        audit.append({"index": index, "content": item, "included": reason is None,
                      "exclusion_reason": reason, "source": source,
                      "dependency_id": next((entry.get("dependency_id") for entry in state.dependencies_considered
                                             if entry.get("dependency_type") == "EVIDENCE"), None)})
        if reason is None:
            included.append(item)
    return included, audit


def deterministic_claim_records(facts: dict[str, Any]) -> list[dict[str, Any]]:
    """Return descriptive claims with machine-checkable derivation metadata."""
    records: list[dict[str, Any]] = []
    def add(claim: str, source_fields: list[str], derived_from: str, certainty: str = "exact") -> None:
        records.append({"claim": claim, "claim_type": "deterministically-derived",
                        "source": "state", "source_fields": source_fields,
                        "derived_from": derived_from, "certainty": certainty})

    bedtime, wake_time = facts.get("bedtime"), facts.get("wake_time")
    total_sleep = facts.get("total_sleep_time")
    time_in_bed = duration_between(bedtime, wake_time)
    if time_in_bed is not None and time_in_bed:
        add(f"根据记录的上床和起床时间，卧床时间为 {time_in_bed} 分钟。",
            ["bedtime", "wake_time"], "cross_midnight_duration")
    if isinstance(total_sleep, (int, float)):
        add(f"记录的总睡眠时间为 {int(total_sleep)} 分钟。", ["total_sleep_time"], "normalized_fact")
    if time_in_bed and isinstance(total_sleep, (int, float)):
        efficiency = round(total_sleep / time_in_bed * 100, 1)
        add(f"根据上述两项记录计算，睡眠效率约为 {efficiency:g}%。",
            ["bedtime", "wake_time", "total_sleep_time"], "sleep_efficiency")
    pattern = facts.get("recent_sleep_pattern")
    if isinstance(pattern, list) and pattern:
        add(f"日记中包含 {len(pattern)} 天记录。", ["recent_sleep_pattern"], "diary_entry_count")
        totals = [item.get("total_sleep_time") for item in pattern
                  if isinstance(item, dict) and isinstance(item.get("total_sleep_time"), (int, float))]
        if totals:
            average = round(sum(totals) / len(totals), 1)
            add(f"日记中可用条目的平均总睡眠时间约为 {average:g} 分钟。",
                ["recent_sleep_pattern"], "diary_average_total_sleep")
        dates = [str(item.get("date")) for item in pattern
                 if isinstance(item, dict) and item.get("date")]
        if dates:
            add(f"日记覆盖 {len(set(dates))} 个日期。", ["recent_sleep_pattern"], "diary_date_coverage")
        for item in pattern:
            if isinstance(item, dict) and _is_valid_diary_date(item.get("date")):
                minutes = duration_between(item.get("bedtime"), item.get("wake_time"))
                if minutes is not None:
                    add(f"{item['date']} 记录的卧床时间为 {minutes} 分钟。",
                        ["recent_sleep_pattern", "bedtime", "wake_time"], "cross_midnight_duration")
    diary_derived = facts.get("diary_derived")
    if isinstance(diary_derived, dict):
        descriptions = {
            "diary_day_count": ("日记覆盖 {value} 天。", "date_coverage"),
            "average_sleep_duration_minutes": ("可用日记条目的平均总睡眠时间约为 {value} 分钟。", "mean"),
            "bedtime_variation_minutes": ("记录中的上床时间变化范围为 {value} 分钟。", "circular_range"),
            "wake_time_variation_minutes": ("记录中的起床时间变化范围为 {value} 分钟。", "circular_range"),
        }
        for field, (template, method) in descriptions.items():
            value = diary_derived.get(field)
            if isinstance(value, (int, float)):
                add(template.format(value=value), ["diary_derived", field], method,
                    "approximate" if field == "average_sleep_duration_minutes" else "exact")
        efficiencies = diary_derived.get("sleep_efficiency_by_day")
        if isinstance(efficiencies, list):
            for item in efficiencies:
                if isinstance(item, dict) and _is_valid_diary_date(item.get("date")) and isinstance(item.get("percent"), (int, float)):
                    add(f"{item['date']} 的日记计算睡眠效率约为 {item['percent']:g}%。",
                        ["diary_derived", "sleep_efficiency_by_day"], "total_sleep_time / time_in_bed",
                        "approximate")
    return records


def _is_valid_diary_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        from datetime import date
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _answer_facts(state: AdaptiveAgentState) -> dict[str, Any]:
    """Exclude tool-derived diary values unless the active projection is valid."""
    facts = {}
    projection_valid = state.diary_projection.get("projection_status") == "valid"
    for field, value in state.facts.items():
        if state.fact_status.get(field) == "INVALID" or (isinstance(value, dict) and value.get("uncertainty") == "conflict"):
            continue
        source = state.fact_sources.get(field, {})
        if value is None or value == "":
            continue
        if source.get("source_type") == "diary" and not projection_valid:
            continue
        facts[field] = value
    return facts


def diary_semantic_status(state: AdaptiveAgentState, facts: dict[str, Any]) -> dict[str, Any]:
    """Represent record existence separately from each field's completeness."""
    projection = state.diary_projection
    status = projection.get("projection_status")
    if status in {"unavailable", "invalid"}:
        return {"resource": "RESOURCE_UNAVAILABLE" if status == "unavailable" else "INVALID",
                "records": []}
    records = []
    if status == "valid":
        for entry in facts.get("recent_sleep_pattern", []):
            if not isinstance(entry, dict):
                continue
            fields = {}
            for field in ("bedtime", "sleep_time", "sleep_onset_latency", "wake_time", "total_sleep_time",
                          "nighttime_awakenings"):
                value = entry.get(field)
                if field not in entry or value is None or value == "":
                    field_status = "RECORD_PRESENT_FIELD_MISSING"
                elif isinstance(value, dict) and value.get("uncertainty") == "invalid":
                    field_status = "RECORD_PRESENT_FIELD_INVALID"
                else:
                    field_status = "RECORD_PRESENT_FIELD_VALID"
                fields[field] = field_status
            records.append({"date": entry.get("date"), "record_status": "PRESENT", "fields": fields})
    return {"resource": "AVAILABLE" if status == "valid" else "UNKNOWN", "records": records,
            "record_absence": "RECORD_ABSENT" if status == "valid" and
            projection.get("source_entry_count") == 0 else "NOT_ESTABLISHED"}


def build_answer_context(state: AdaptiveAgentState, limitation: str | None = None) -> dict[str, Any]:
    """Only validated State values cross the State→Answer boundary."""
    facts = _answer_facts(state)
    evidence, evidence_audit = project_evidence(state)
    def source_metadata(source: dict[str, Any]) -> dict[str, Any]:
        # Raw utterances and raw tool payloads are not a second fact channel.
        allowed = ("source_type", "source_turn", "certainty", "source_fields", "kind",
                   "tool_result_id", "state_update_id", "payload_shape", "source_entry_count",
                   "projected_entry_count", "date_coverage", "provenance")
        return {key: source[key] for key in allowed if key in source}

    user_facts = {field: {"value": value, "source": source_metadata(state.fact_sources.get(field, {}))}
                  for field, value in facts.items()
                  if state.fact_sources.get(field, {}).get("source_type") == "user_explicit"}
    diary_facts = {field: {"value": value, "source": source_metadata(state.fact_sources.get(field, {}))}
                   for field, value in facts.items()
                   if state.fact_sources.get(field, {}).get("source_type") == "diary"}
    unavailable = [name for name, status in state.resource_status.items() if status in {"unavailable", "invalid"}]
    if state.diary_projection.get("projection_status") in {"unavailable", "invalid"} and "sleep_diary" not in unavailable:
        unavailable.append("sleep_diary")
    context = {
        "goal": state.goal, "task_type": state.task_type.value if state.task_type else None,
        "answer_scope": state.answer_scope,
        "user_facts": user_facts, "diary_facts": diary_facts,
        "fact_status": dict(state.fact_status), "target_status": dict(state.target_status),
        "fact_conflicts": {key: list(value) for key, value in state.fact_conflicts.items()},
        "relevant_facts": facts, "relevant_evidence": evidence,
        "evidence": [{"content": item["content"], "source": source_metadata(item["source"]),
                      "dependency_id": item["dependency_id"], "relevance": "current_goal"}
                     for item in evidence_audit if item["included"]],
        "evidence_projection": evidence_audit,
        "known_missing": list(dict.fromkeys(state.decision_missing + state.critical_missing +
                                            state.secondary_missing)),
        "unavailable_resources": unavailable,
        "semantic_status": diary_semantic_status(state, facts),
        "provenance": {"facts": {field: source_metadata(state.fact_sources.get(field, {})) for field in facts},
                       "evidence": [source_metadata(item["source"]) for item in evidence_audit if item["included"]]},
        "limitation": limitation,
    }
    # The audit is visible in the terminal State snapshot without sending excluded
    # evidence content to the model.
    state.answer_context_audit = {"evidence_projection": evidence_audit,
                                  "semantic_status": context["semantic_status"],
                                  "user_fact_fields": list(user_facts), "diary_fact_fields": list(diary_facts),
                                  "fact_status": dict(state.fact_status), "target_status": dict(state.target_status),
                                  "fact_conflicts": {key: list(value) for key, value in state.fact_conflicts.items()}}
    return context


def data_derived_claims(facts: dict[str, Any]) -> list[str]:
    """Backward-compatible text view of deterministic claim records."""
    return [record["claim"] for record in deterministic_claim_records(facts)]


def user_fact_claim_records(state: AdaptiveAgentState) -> list[dict[str, Any]]:
    records = []
    for field, value in state.facts.items():
        source = state.fact_sources.get(field)
        if source and source.get("source_type") == "user_explicit":
            records.append({"claim": field, "claim_type": "user-derived", "source": source.get("source_type"),
                            "source_field": field, "derived_from": [], "certainty": source.get("certainty", "exact")})
    return records


def allowed_quantities(facts: dict[str, Any], evidence: list[str], derived_claims: list[str]) -> set[str]:
    """Quantities can come from user data, deterministic calculations, or evidence."""
    values = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
        else:
            values.update(_numbers(str(value)))

    visit(facts)
    for item in evidence + derived_claims:
        values.update(_numbers(item))
    return values


def remove_unsupported_quantitative_claims(answer: str, allowed: set[str], has_evidence: bool) -> str:
    """Remove model-added quantitative rules rather than special-casing any threshold."""
    kept: list[str] = []
    removed = False
    for sentence in re.split(r"(?<=[。！？!?])", answer):
        quantities = _numbers(sentence)
        unsupported = quantities - allowed
        clinical_rule_without_evidence = bool(quantities and _CLINICAL_QUANTIFIER.search(sentence) and not has_evidence)
        if unsupported or clinical_rule_without_evidence:
            removed = True
            continue
        kept.append(sentence)
    result = "".join(kept).strip()
    if removed:
        result = (result + "\n\n当前回答范围不提供具体阈值、时长或治疗规则。 ").strip()
    return result


def remove_out_of_scope_claims(answer: str, answer_scope: str) -> str:
    """Honor a narrow directional scope even when retrieved evidence is more prescriptive."""
    if "不指定具体新上床时间" not in answer_scope:
        return answer
    prescription = re.compile(r"(?:上床|卧床|睡眠限制|睡眠窗口|提前|推迟|减少).*(?:\d|分钟|小时|天|周|%)|(?:\d|分钟|小时|天|周|%).*(?:上床|卧床|睡眠限制|睡眠窗口|提前|推迟|减少)")
    return "".join(sentence for sentence in re.split(r"(?<=[。！？!?])", answer)
                   if not prescription.search(sentence)).strip()


_PERSONAL_FACT_SIGNALS = {
    "bedtime": ("上床",), "sleep_time": ("睡着", "入睡时间"),
    "sleep_onset_latency": ("入睡需要", "入睡耗时"), "wake_time": ("起床",),
    "total_sleep_time": ("睡眠时长", "总睡眠"), "nighttime_awakenings": ("夜醒", "夜里醒"),
    "caffeine": ("咖啡", "咖啡因"), "nap": ("午睡",), "exercise": ("运动",),
    "screen_before_bed": ("睡前看屏幕", "睡前玩手机"),
    "perceived_stress": ("压力", "焦虑"),
}


def remove_state_conflicting_claims(answer: str, state: AdaptiveAgentState,
                                    semantic_status: dict[str, Any]) -> str:
    """Fail closed on recognizable factual contradictions, not clinical advice."""
    by_date = {item["date"]: item for item in semantic_status.get("records", []) if item.get("date")}
    resource_status = semantic_status.get("resource")
    kept = []
    removed = False
    for sentence in re.split(r"(?<=[。！？!?])", answer):
        if not sentence.strip():
            continue
        dates = re.findall(r"\d{4}-\d{2}-\d{2}", sentence)
        claims_absence = bool(re.search(r"(?:没有|无|不存在|缺失|未找到|未记录).{0,6}(?:日记|记录|条目)|(?:日记|记录|条目).{0,6}(?:没有|不存在|缺失|未找到)", sentence))
        if claims_absence and (resource_status in {"RESOURCE_UNAVAILABLE", "INVALID"} or
                               any(day in by_date for day in dates) or
                               (by_date and re.search(r"(?:没有|无|不存在)(?:任何|全部|所有)?(?:日记)?记录", sentence))):
            removed = True
            continue
        # An unavailable/invalid resource is not evidence that records do not exist.
        if resource_status in {"RESOURCE_UNAVAILABLE", "INVALID"} and re.search(
                r"(?:没有|无|不存在).{0,5}日记|日记.{0,5}(?:没有|不存在)", sentence):
            removed = True
            continue
        # Guard direct second-person assertions only. Questions, hypotheticals,
        # and statements about information not being supplied are not user facts.
        assertion = (re.search(r"(?:你|您)(?:通常|每天|经常|总是|一直|会|有|没有|不)?", sentence) and
                     not re.search(r"[？?]|如果|假如|可能|是否|未提供|没有提供|尚未提供|未说明|没有说明|未提到|未知", sentence))
        if assertion:
            unsupported = [field for field, signals in _PERSONAL_FACT_SIGNALS.items()
                           if any(signal in sentence for signal in signals) and
                           (field not in state.facts or state.facts[field] is None)]
            if unsupported:
                removed = True
                continue
        kept.append(sentence)
    result = "".join(kept).strip()
    if removed and not result:
        return "当前已验证的资料不足以支持该事实判断。"
    return result


def validate_answer(answer: str, state: AdaptiveAgentState, allowed: set[str], has_evidence: bool,
                    semantic_status: dict[str, Any] | None = None) -> str:
    """Deterministically reject unsupported data claims and precision upgrades."""
    answer = remove_unsupported_quantitative_claims(answer, allowed, has_evidence)
    # An exact clock in the answer is not allowed when State only contains a range/approximation.
    for field in ("bedtime", "wake_time", "sleep_time"):
        value = state.facts.get(field)
        if isinstance(value, dict) and value.get("uncertainty") in {"range", "approximate"}:
            exact = re.findall(r"\b\d{1,2}:\d{2}\b", answer)
            if exact:
                if value.get("uncertainty") == "range":
                    answer = re.sub(r"\b\d{1,2}:\d{2}\b", "该时间范围", answer)
                else:
                    answer = re.sub(r"\b\d{1,2}:\d{2}\b", "大约这个时间", answer)
    answer = remove_out_of_scope_claims(answer, state.answer_scope)
    return remove_state_conflicting_claims(answer, state, semantic_status or {})


class LLMAnswerGenerator:
    """Communicate data-derived and evidence-grounded claims without model-only rules."""

    system_prompt = """你是 CBT-I 辅助系统的回答生成器。回答只能使用给定的 goal、
relevant facts、relevant evidence、data-derived claims 与 answer_scope。数据计算只可描述
给定事实本身；外部医学知识、百分比阈值、建议时长、治疗规则、临床 cutoffs 或其他具体
量化结论，必须在 relevant evidence 中有直接依据。没有依据时，明确说明当前证据不支持，
不要使用模型自身知识补充。State 中没有的用户事实不得推测。semantic_status 中的
RECORD_PRESENT_FIELD_MISSING/INVALID 表示记录存在、字段缺失/无效，不是没有记录；
RESOURCE_UNAVAILABLE 不代表记录不存在。不得诊断疾病或扩大 answer_scope。请使用中文、简洁且共情。"""

    def __init__(self, model: Any) -> None:
        self.model = model
        self.last_token_usage: dict[str, Any] | None = None

    def answer(self, state: AdaptiveAgentState, limitation: str | None = None) -> str:
        context = build_answer_context(state, limitation)
        evidence = context["relevant_evidence"]
        answer_facts = context["relevant_facts"]
        derived_records = deterministic_claim_records(answer_facts)
        summary_records = []
        diary_source = state.fact_sources.get("diary_derived") or state.fact_sources.get("recent_sleep_pattern") or {}
        projection = diary_source.get("projection", {})
        if projection.get("projection_status") == "valid":
            summary = answer_facts.get("diary_summary")
            if isinstance(summary, dict):
                for name, value in summary.items():
                    summary_records.append({
                        "claim": {"summary_field": name, "value": value},
                        "claim_type": "validated-diary-summary", "source": "diary_projection",
                        "source_fields": ["diary_summary", name], "certainty": "summary-as-provided",
                        "tool_result_id": projection.get("tool_result_id"),
                        "state_update_id": projection.get("state_update_id"),
                        "projection_status": projection.get("projection_status"),
                        "source_entry_count": projection.get("source_entry_count"),
                        "date_coverage": projection.get("date_coverage"),
                        "provenance": projection.get("provenance"),
                    })
            for record in derived_records:
                if any(field in {"recent_sleep_pattern", "diary_derived", "diary_summary"}
                       for field in record.get("source_fields", [])):
                    record["tool_result_id"] = projection.get("tool_result_id")
                    record["state_update_id"] = projection.get("state_update_id")
                    record["projection_status"] = projection.get("projection_status")
                    record["source_entry_count"] = projection.get("source_entry_count")
                    record["date_coverage"] = projection.get("date_coverage")
                    record["provenance"] = projection.get("provenance")
        derived = [record["claim"] for record in derived_records]
        state.claim_provenance = user_fact_claim_records(state) + derived_records + summary_records
        for index, item in enumerate(evidence):
            source = next((entry for entry in state.evidence_sources if entry.get("evidence") == item), {})
            state.claim_provenance.append({"claim": item, "claim_type": "evidence-grounded",
                                           "source": f"evidence:{index}", "source_field": None,
                                           "derived_from": [], "certainty": "exact",
                                           "tool_result_id": source.get("tool_result_id"),
                                           "state_update_id": source.get("state_update_id")})
        context["data_derived_claims"] = derived
        context["claim_provenance"] = state.claim_provenance
        # Exclusion decisions belong in the State trace, not in the model input.
        context.pop("evidence_projection")
        response = self.model.invoke([
            ("system", self.system_prompt),
            ("human", f"请根据以下受限上下文生成回答：\n{context}"),
        ])
        metadata = getattr(response, "response_metadata", {}) or {}
        self.last_token_usage = metadata.get("token_usage") or metadata.get("usage")
        answer = str(getattr(response, "content", response))
        answer = validate_answer(answer, state, allowed_quantities(answer_facts, evidence, derived),
                                 bool(evidence), context["semantic_status"])
        if state.task_type == TaskType.DATA_ANALYSIS and derived:
            description = "\n".join(f"- {claim}" for claim in derived)
            return f"基于日记的描述性计算：\n{description}\n\n{answer}"
        return answer
