"""Append-only JSONL evaluation recording; it never affects agent decisions."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from adaptive_agent.runner import LoopResult
from adaptive_agent.state import AdaptiveAgentState


def serialize_state(state: AdaptiveAgentState) -> dict[str, Any]:
    return {
        "goal": state.goal,
        "task_type": state.task_type.value if state.task_type else None,
        "facts": dict(state.facts),
        "fact_sources": dict(state.fact_sources),
        "claim_provenance": list(state.claim_provenance),
        "information_estimates": dict(state.information_estimates),
        "considered_information": list(state.considered_information),
        "rejected_information": list(state.rejected_information),
        "stop_reason": state.stop_reason,
        "preconditions_considered": list(state.preconditions_considered),
        "dependencies_considered": list(state.dependencies_considered),
        "dependencies_required": list(state.dependencies_required),
        "dependencies_satisfied": list(state.dependencies_satisfied),
        "dependencies_unavailable": list(state.dependencies_unavailable),
        "diary_projection": dict(state.diary_projection),
        "goal_id": state.goal_id,
        "state_revision": state.state_revision,
        "semantic_provenance": list(state.semantic_provenance),
        "base_requirements": dict(state.base_requirements),
        "effective_requirements": dict(state.effective_requirements),
        "lineage_events": list(state.lineage_events),
        "critical_missing": list(state.critical_missing),
        "required_missing": list(state.required_missing),
        "decision_relevant_missing": list(state.decision_relevant_missing),
        "validity_critical_missing": list(state.validity_critical_missing),
        "secondary_missing": list(state.secondary_missing),
        "evidence": list(state.evidence),
        "user_info_sufficiency": state.user_info_sufficiency,
        "evidence_sufficiency": state.evidence_sufficiency,
        "candidate_actions": [asdict(item) for item in state.candidate_actions],
        "action_history": list(state.action_history),
        "resource_status": dict(state.resource_status),
        "required_resources": list(state.required_resources),
        "decision_missing": list(state.decision_missing),
        "answer_scope": state.answer_scope,
    }


class EvaluationRecorder:
    def __init__(self, directory: Path | str = "evaluation/runs") -> None:
        self.directory = Path(directory)

    def record(
        self,
        session_id: str,
        initial_state: AdaptiveAgentState,
        result: LoopResult,
        total_turns: int,
        started_at: float,
        token_usage: dict[str, Any] | None = None,
    ) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = serialize_state(result.state)
        payload.update({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "initial_facts": dict(initial_state.facts),
            "state_history": result.state_history,
            "chosen_actions": [asdict(item) for item in result.transitions],
            "tool_calls": [item.action for item in result.transitions if item.action in {"RETRIEVE", "READ_DIARY"}],
            "retrieved_evidence": list(result.state.evidence),
            "total_steps": result.steps,
            "total_turns": total_turns,
            "final_status": result.status,
            "final_answer": result.response,
            "latency_ms": round((perf_counter() - started_at) * 1000, 2),
            "token_usage": token_usage,
        })
        path = self.directory / f"{datetime.now(timezone.utc).date().isoformat()}.jsonl"
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return path
