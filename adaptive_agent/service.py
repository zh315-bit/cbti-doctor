"""Session persistence and API-facing orchestration for the adaptive loop."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Protocol

from evaluation.recorder import EvaluationRecorder

from .runner import AdaptiveAgentLoop
from .state import AdaptiveAgentState


class Recorder(Protocol):
    def record(self, session_id: str, initial_state: AdaptiveAgentState, result: Any,
               total_turns: int, started_at: float, token_usage: dict[str, Any] | None = None) -> Any:
        """Persist a completed API turn without changing its decision result."""


@dataclass
class AdaptiveSession:
    state: AdaptiveAgentState = field(default_factory=AdaptiveAgentState)
    total_turns: int = 0


class AdaptiveChatService:
    """Owns per-session state; Flask remains a thin HTTP adapter."""

    def __init__(self, loop: AdaptiveAgentLoop, recorder: Recorder | None = None) -> None:
        self.loop = loop
        self.recorder = recorder or EvaluationRecorder()
        self.sessions: dict[str, AdaptiveSession] = {}

    def chat(self, session_id: str, message: str) -> dict[str, Any]:
        session = self.sessions.setdefault(session_id, AdaptiveSession())
        initial_state = deepcopy(session.state)
        started_at = perf_counter()
        result = self.loop.run_turn(message, deepcopy(session.state))
        session.state = result.state
        session.total_turns += 1
        token_usage = getattr(self.loop.answer_generator, "last_token_usage", None)
        self.recorder.record(session_id, initial_state, result, session.total_turns, started_at, token_usage)
        tools_used = [
            "retrieval_augmentation_generation" if item.action == "RETRIEVE" else "read_diary"
            for item in result.transitions if item.action in {"RETRIEVE", "READ_DIARY"}
        ]
        return {
            "assistant": result.response,
            "tools_used": tools_used,
            "status": result.status,
            "steps": result.steps,
        }

    def reset(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)
