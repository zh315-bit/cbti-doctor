"""Deterministic calculations over normalized sleep facts."""

from __future__ import annotations

from typing import Any


def clock_minutes(value: Any) -> int | None:
    if not isinstance(value, str) or len(value) != 5 or value[2] != ":":
        return None
    try:
        hour, minute = (int(part) for part in value.split(":"))
    except ValueError:
        return None
    if not (0 <= hour < 24 and 0 <= minute < 60):
        return None
    return hour * 60 + minute


def duration_between(start: Any, end: Any) -> int | None:
    """Return a cross-midnight duration only when both clocks are exact."""
    first, last = clock_minutes(start), clock_minutes(end)
    if first is None or last is None:
        return None
    return (last - first) % (24 * 60)


def derive_sleep_facts(facts: dict[str, Any]) -> dict[str, Any]:
    """Compute only unique, deterministic values; ranges remain unknown here."""
    derived: dict[str, Any] = {}
    time_in_bed = duration_between(facts.get("bedtime"), facts.get("wake_time"))
    if time_in_bed is not None:
        derived["time_in_bed"] = time_in_bed
    onset = duration_between(facts.get("bedtime"), facts.get("sleep_time"))
    if onset is not None and facts.get("sleep_onset_latency") is None:
        derived["sleep_onset_latency"] = onset
    return derived
