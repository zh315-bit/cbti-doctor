"""Stable, injectable interfaces for retrieval and session-backed sleep diaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .requirements import RequirementSet
from .input_understanding import FACT_FIELDS
from copy import deepcopy


@dataclass(frozen=True)
class RetrievalResult:
    evidence: tuple[str, ...] = ()
    available: bool = True
    detail: str = ""


@dataclass(frozen=True)
class DiaryResult:
    facts: dict[str, Any]
    available: bool
    detail: str = ""
    source_entry_count: int | None = None
    source_dates: tuple[str, ...] = ()
    kind: str = "ENTRY_SHAPED"
    date_coverage: tuple[str, ...] = ()
    provenance: dict[str, Any] | None = None
    summary_semantics: str | None = None


class RetrievalTool(Protocol):
    def retrieve(self, query: str) -> RetrievalResult:
        """Return evidence for this goal-specific query, without generating user facts."""


class DiaryTool(Protocol):
    def read(self, requirements: RequirementSet) -> DiaryResult:
        """Return only stored diary facts or an explicit unavailable result."""


class RagRetrievalTool:
    """Lazy wrapper around the project RAG tool so tests need no model/index setup."""

    def retrieve(self, query: str) -> RetrievalResult:
        try:
            from rag_client import retrieval_augmentation_generation
            response = retrieval_augmentation_generation.invoke({"user_input": query})
            return RetrievalResult(evidence=(str(response),), detail="project_rag")
        except Exception as exc:
            return RetrievalResult(available=False, detail=f"RAG unavailable: {exc}")


class SessionDiaryTool:
    """A diary source backed only by data explicitly supplied by the session/mock."""

    def __init__(self, diary_facts: dict[str, Any] | None = None) -> None:
        self._diary_facts = diary_facts

    def read(self, requirements: RequirementSet) -> DiaryResult:
        if self._diary_facts is None:
            return DiaryResult(facts={}, available=False, detail="sleep diary unavailable", kind="UNAVAILABLE")
        allowed = set(requirements.critical) | set(requirements.secondary)
        if requirements.diary_preferred or 'sleep_diary' in requirements.resources:
            allowed.update(FACT_FIELDS)
        # Keep canonical `sleep_time` and latency support for the alternative field.
        allowed.update({"sleep_time", "sleep_onset_latency"})
        facts = {
            name: deepcopy(value) for name, value in self._diary_facts.items()
            if name in allowed and value is not None and value != "" and value != [] and value != {}
        }
        pattern = facts.get('recent_sleep_pattern')
        entries = pattern if isinstance(pattern, list) and all(isinstance(item, dict) for item in pattern) else None
        dates = tuple(str(item['date']) for item in entries or () if item.get('date'))
        if not facts:
            return DiaryResult(facts={}, available=False, detail="sleep diary unavailable", kind="UNAVAILABLE")
        if entries is not None:
            return DiaryResult(facts=facts, available=True, detail="session diary",
                               source_entry_count=len(entries), source_dates=dates,
                               date_coverage=dates, provenance={"source": "session_diary"})
        # Existing session fixtures that carry a textual aggregate are explicitly
        # summary-shaped.  They need source truth supplied by a V2 tool before
        # State projection can accept them.
        return DiaryResult(facts=facts, available=True, detail="session diary summary",
                           kind="SUMMARY_SHAPED")
