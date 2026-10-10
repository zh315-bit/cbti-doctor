"""V3 development trace projection; this module cannot execute an Agent or case."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from adaptive_agent.runner import LoopResult
from evaluation.recorder import serialize_state

TRACE_SCHEMA_VERSION = "step9_50_authorization_trace_v1"
AUTHORIZATION_MODES = {
    "AUTHORIZED_FULL", "AUTHORIZED_BOUNDED",
    "BLOCKED_NEEDS_INFORMATION", "BLOCKED_UNSAFE_OR_INVALID",
}
AUTHORIZATION_FIELDS = (
    "answer_authorization_mode", "answer_authorization_reason_codes",
    "blocked_dependency_ids", "blocked_precondition_ids",
    "bounded_excluded_actions", "bounded_supported_content_basis",
    "authorization_decision_source", "authorization_decision_version",
)


def validate_authorization_mirrors(trace: dict[str, Any]) -> None:
    """Fail closed if the authoritative decision is absent or any mirror differs."""
    decisions = [item.get("answer_authorization") for item in trace.get("state_history", [])
                 if item.get("event") == "DECISION" and isinstance(item.get("answer_authorization"), dict)]
    if not decisions:
        raise ValueError("V3 trace missing authoritative DECISION authorization")
    authoritative = decisions[-1]
    if authoritative.get("answer_authorization_mode") not in AUTHORIZATION_MODES:
        raise ValueError("V3 trace contains unknown authorization mode")
    if any(field not in authoritative for field in AUTHORIZATION_FIELDS):
        raise ValueError("V3 trace authorization missing required contract field")
    if authoritative["answer_authorization_mode"] == "AUTHORIZED_BOUNDED" and (
            not authoritative["bounded_supported_content_basis"]
            or not authoritative["bounded_excluded_actions"]):
        raise ValueError("V3 bounded authorization lacks basis or exclusions")
    final_state = trace.get("final_state", {})
    for reference in authoritative["bounded_supported_content_basis"]:
        if reference.startswith("fact:") and reference[5:] not in final_state.get("facts", {}):
            raise ValueError("V3 authorization basis references an absent fact")
        if reference.startswith("evidence:"):
            try:
                index = int(reference.split(":", 1)[1])
            except ValueError as error:
                raise ValueError("V3 authorization basis has malformed evidence reference") from error
            if index < 0 or index >= len(final_state.get("evidence", [])):
                raise ValueError("V3 authorization basis references absent evidence")
    terminal = next((item for item in reversed(trace.get("state_history", []))
                     if item.get("event") in {"ANSWER", "ASK", "MAX_STEPS"}), None)
    if terminal is None or terminal.get("answer_authorization") != authoritative:
        raise ValueError("V3 terminal authorization mirror differs from DECISION")
    if final_state.get("answer_authorization") != authoritative:
        raise ValueError("V3 final_state authorization mirror differs from DECISION")


def build_v3_trace(result: LoopResult) -> dict[str, Any]:
    """Project an already-completed development turn; it performs no decisions."""
    trace = {
        "trace_schema_version": TRACE_SCHEMA_VERSION,
        "final_status": result.status,
        "final_answer": result.response,
        "state_history": deepcopy(result.state_history),
        "final_state": serialize_state(result.state),
    }
    validate_authorization_mirrors(trace)
    return trace
