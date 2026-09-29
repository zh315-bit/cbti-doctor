"""Explicit state transitions after tool execution."""

from __future__ import annotations

from collections import Counter
from datetime import date
from statistics import mean

from .state import AdaptiveAgentState
from .tools import DiaryResult, RetrievalResult
from .facts import clock_minutes


def _valid_date(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
        return len(value) == 10
    except ValueError:
        return False


def _exact_clock(value):
    if isinstance(value, str):
        return clock_minutes(value)
    if isinstance(value, dict) and value.get("uncertainty", "known") == "known":
        return clock_minutes(value.get("value"))
    return None


def _circular_variation(values: list[int]) -> int | None:
    if len(values) < 2:
        return None
    ordered = sorted(set(values))
    if len(ordered) < 2:
        return 0
    gaps = [b - a for a, b in zip(ordered, ordered[1:])]
    gaps.append(ordered[0] + 1440 - ordered[-1])
    return 1440 - max(gaps)


def _diary_derived(entries: list[dict]) -> dict:
    unique_dates = sorted({entry["date"] for entry in entries})
    derived = {"diary_day_count": len(unique_dates)}
    durations = [entry["total_sleep_time"] for entry in entries
                 if isinstance(entry.get("total_sleep_time"), (int, float))
                 and not isinstance(entry.get("total_sleep_time"), bool)]
    if durations:
        derived["average_sleep_duration_minutes"] = round(mean(durations), 1)
        derived["average_sleep_duration_source_entry_count"] = len(durations)
    for field, output in (("bedtime", "bedtime_variation_minutes"), ("wake_time", "wake_time_variation_minutes")):
        clocks = [_exact_clock(entry.get(field)) for entry in entries]
        clocks = [item for item in clocks if item is not None]
        variation = _circular_variation(clocks)
        if variation is not None:
            derived[output] = variation
            derived[f"{output}_source_entry_count"] = len(clocks)
    efficiencies = []
    time_in_bed_by_day = []
    for entry in entries:
        sleep = entry.get("total_sleep_time")
        in_bed = None
        bedtime, wake = _exact_clock(entry.get("bedtime")), _exact_clock(entry.get("wake_time"))
        if bedtime is not None and wake is not None:
            in_bed = (wake - bedtime) % 1440
            time_in_bed_by_day.append({"date": entry["date"], "minutes": in_bed})
        if (isinstance(sleep, (int, float)) and not isinstance(sleep, bool)
                and in_bed and 0 <= sleep <= in_bed):
            efficiencies.append({"date": entry["date"], "percent": round(sleep / in_bed * 100, 1)})
    if efficiencies:
        derived["sleep_efficiency_by_day"] = efficiencies
    if time_in_bed_by_day:
        derived["time_in_bed_by_day"] = time_in_bed_by_day
    return derived


def apply_retrieval_result(state: AdaptiveAgentState, result: RetrievalResult) -> AdaptiveAgentState:
    tool_result_id = f"tool_{state.goal_id or 'goal'}_r{state.state_revision}_{len(state.lineage_events) + 1}"
    state_update_id = f"upd_{state.goal_id or 'goal'}_r{state.state_revision + 1}_{len(state.lineage_events) + 1}"
    source_count = len(result.evidence) if result.available else 0
    projected_count = 0
    for item in result.evidence if result.available else ():
        if item not in state.evidence:
            state.evidence.append(item)
            projected_count += 1
            state.evidence_sources.append({"evidence": item, "tool_result_id": tool_result_id,
                                           "state_update_id": state_update_id, "source_type": "RAG",
                                           "retrieval_query": state.action_history[-1].get("query"),
                                           "goal_id": state.goal_id})
    state.resource_status["external_evidence"] = "loaded" if result.available and source_count else "unavailable"
    state.target_status["external_evidence"] = {"status": "RETRIEVED" if result.available and source_count else "UNAVAILABLE",
                                                 "source_turn": state.turn_index, "tool_result_id": tool_result_id}
    state.action_history[-1]["result"] = result.detail or ("ok" if result.evidence else "no evidence")
    action_id = state.action_history[-1].get("action_id")
    state.lineage_events.append({"tool_result_id": tool_result_id, "source_action_id": action_id,
                                 "state_update_id": state_update_id, "source_tool_result_id": tool_result_id,
                                 "tool": "RETRIEVE", "available": result.available,
                                 "source_type": "RAG", "payload_shape": "EVIDENCE_LIST",
                                 "source_entry_count": source_count, "projected_entry_count": projected_count,
                                 "date_coverage": None,
                                 "provenance": {"adapter": result.detail or "retrieval_tool"},
                                 "projection_status": "valid" if result.available else "unavailable",
                                 "projection_warnings": [] if result.available and source_count else ["no evidence returned"]})
    return state


def apply_diary_result(state: AdaptiveAgentState, result: DiaryResult) -> AdaptiveAgentState:
    # A new read replaces the prior tool projection; stale diary-derived values
    # must not survive an invalid or unavailable result for this resource read.
    for field, source in list(state.fact_sources.items()):
        if source.get("source_type") == "diary":
            state.facts.pop(field, None)
            state.fact_sources.pop(field, None)
    entries_value = result.facts.get("entries", result.facts.get("recent_sleep_pattern"))
    projected_entries = entries_value if isinstance(entries_value, list) and all(isinstance(item, dict) for item in entries_value) else None
    received_entry_count = len(projected_entries) if projected_entries is not None else 0
    received_dates = tuple(str(item.get("date")) for item in projected_entries or () if item.get("date") is not None)
    warnings: list[str] = []
    tool_result_id = f"tool_{state.goal_id or 'goal'}_r{state.state_revision}_{len(state.lineage_events) + 1}"
    state_update_id = f"upd_{state.goal_id or 'goal'}_r{state.state_revision + 1}_{len(state.lineage_events) + 1}"
    if result.kind == "UNAVAILABLE" or not result.available:
        status = "unavailable"; warnings.append("diary unavailable")
    elif result.kind == "SUMMARY_SHAPED":
        coverage = tuple(result.date_coverage)
        metadata_valid = (
            isinstance(result.source_entry_count, int) and not isinstance(result.source_entry_count, bool)
            and result.source_entry_count > 0 and bool(coverage)
            and all(_valid_date(item) for item in coverage) and len(set(coverage)) == len(coverage)
            and isinstance(result.provenance, dict) and bool(result.provenance)
            and isinstance(result.summary_semantics, str) and bool(result.summary_semantics.strip())
            and isinstance(result.facts, dict) and bool(result.facts)
            and projected_entries is None
        )
        status = "valid" if metadata_valid else "invalid"
        if not metadata_valid:
            warnings.append("summary payload must include positive source cardinality, valid date coverage, provenance, semantics, and summary-shaped values")
    elif result.kind == "INVALID":
        status = "invalid"; warnings.append("tool marked diary payload invalid")
    elif result.kind == "ENTRY_SHAPED":
        source_dates = tuple(result.source_dates)
        coverage = tuple(result.date_coverage)
        entries_well_formed = projected_entries is not None and all(
            isinstance(entry.get("date"), str) and _valid_date(entry.get("date")) for entry in projected_entries
        )
        metadata_valid = (
            entries_well_formed and isinstance(result.source_entry_count, int)
            and not isinstance(result.source_entry_count, bool) and result.source_entry_count == received_entry_count
            and all(_valid_date(item) for item in source_dates)
            and Counter(source_dates) == Counter(received_dates)
            and set(coverage) == set(received_dates)
            and all(_valid_date(item) for item in coverage)
            and isinstance(result.provenance, dict) and bool(result.provenance)
        )
        status = "valid" if metadata_valid else "invalid"
        if not metadata_valid:
            warnings.append("entry shape, source/projected cardinality, dates/date coverage, or provenance failed validation")
    else:
        status = "invalid"
        warnings.append(f"unknown payload shape: {result.kind}")
    valid = status == "valid"
    projected_count = received_entry_count if valid and result.kind == "ENTRY_SHAPED" else 0
    projected_dates = received_dates if valid and result.kind == "ENTRY_SHAPED" else ()
    date_coverage = sorted(set(result.date_coverage if result.kind == "SUMMARY_SHAPED" else received_dates))
    state.diary_projection = {'source_entry_count': result.source_entry_count, 'received_entry_count': received_entry_count,
                              'projected_entry_count': projected_count,
                              'source_dates': list(result.source_dates), 'received_dates': list(received_dates),
                              'projected_dates': list(projected_dates),
                              'date_coverage': date_coverage, 'provenance': result.provenance,
                              'projection_status': status, 'projection_warnings': warnings,
                              'tool_result_id': tool_result_id, 'state_update_id': state_update_id,
                              'source_type': "session_diary", 'payload_shape': result.kind,
                              'summary_semantics': result.summary_semantics if result.kind == "SUMMARY_SHAPED" else None}
    usable = valid and result.available
    state.available_diary = usable
    state.diary_available = result.available
    state.resource_status['sleep_diary'] = (
        'loaded' if usable else 'unavailable' if status == 'unavailable' else 'invalid'
    )
    state.target_status['sleep_diary'] = {
        'status': 'RETRIEVED' if usable else 'UNAVAILABLE' if status == 'unavailable' else 'INVALID',
        'source_turn': state.turn_index, 'tool_result_id': tool_result_id, 'state_update_id': state_update_id,
    }
    # Only explicit, non-null diary values become facts; unavailable never becomes data.
    projected_facts = (({"diary_summary": result.facts} if result.kind == "SUMMARY_SHAPED" else
                        {"recent_sleep_pattern": projected_entries, "diary_derived": _diary_derived(projected_entries)})
                       if usable else {})
    for name, value in projected_facts.items():
        if value is not None and value != "":
            existing = state.fact_sources.get(name, {})
            # Diary/tool values are lower priority than an explicit user fact.
            if existing.get("source_type") == "user_explicit":
                continue
            state.facts[name] = value
            state.fact_sources[name] = {
                "kind": "diary", "source_type": "diary", "source_turn": None,
                "raw_value": value, "normalized_value": value, "certainty": "exact",
                "payload_shape": result.kind, "projection": dict(state.diary_projection),
                "source_entry_count": result.source_entry_count,
                "projected_entry_count": projected_count,
                "date_coverage": list(date_coverage), "provenance": result.provenance,
            }
            state.fact_status[name] = "RETRIEVED"
    state.action_history[-1]["result"] = result.detail or ("ok" if result.available else "unavailable")
    action_id = state.action_history[-1].get("action_id")
    state.lineage_events.append({"tool_result_id": tool_result_id, "source_action_id": action_id,
                                 "state_update_id": state_update_id, "source_tool_result_id": tool_result_id,
                                 "tool": "READ_DIARY", "available": usable,
                                 "source_type": "session_diary", "payload_shape": result.kind,
                                 "source_entry_count": result.source_entry_count,
                                 "received_entry_count": received_entry_count,
                                 "projected_entry_count": projected_count,
                                 "date_coverage": date_coverage, "provenance": result.provenance,
                                 "projection_status": state.diary_projection["projection_status"],
                                 "projection_warnings": warnings})
    return state
