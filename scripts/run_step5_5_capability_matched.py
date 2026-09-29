"""Run the frozen V1.1 cases through normalized, observation-only adapters.

This runner changes neither Fixed nor Adaptive decisions.  It standardizes the
experiment boundary and makes unavailable telemetry explicit instead of inferred.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import sys
from time import perf_counter
import traceback
from typing import Any, Protocol

import yaml


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MAX_TURNS = 6


def encode(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump()
    raise TypeError(type(value).__name__)


def load_cases() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    overlay_path = ROOT / "evaluation" / "benchmark_v1_1.yaml"
    overlay = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))
    base = yaml.safe_load((overlay_path.parent / overlay["base_benchmark"]).read_text(encoding="utf-8"))
    overrides = overlay.get("case_overrides", {})
    cases = []
    for raw in base["cases"]:
        case = deepcopy(raw)
        case.update(deepcopy(overrides.get(case["case_id"], {})))
        cases.append(case)
    return overlay, cases, overrides


def follow_up_message(target: str | None, facts: dict[str, Any]) -> str:
    """Release only a response to the actual ASK target."""
    target = target or ""
    value = facts.get(target)
    if target == "sleep_time_or_sleep_onset_latency":
        value = facts.get("sleep_onset_latency", facts.get("sleep_time"))
        if isinstance(value, (int, float)):
            return f"我通常上床后约 {value:g} 分钟才能睡着。"
        if value:
            return f"我通常 {value} 入睡。"
    if target == "bedtime" and value:
        return f"我通常 {value} 上床。"
    if target == "wake_time" and value:
        return f"我通常 {value} 起床。"
    if target == "total_sleep_time" and isinstance(value, (int, float)):
        return f"我每晚总共大约睡 {value:g} 分钟。"
    if target == "recent_sleep_pattern" and value:
        return f"我的近期睡眠模式是：{value}。"
    if target == "nighttime_awakenings" and value is not None:
        return f"我夜里通常醒 {value} 次。"
    return "这项信息我目前不清楚。"


def diary_facts(fixture: Any) -> dict[str, Any] | None:
    """Use only the V1.1 canonical DA-01 diary projection."""
    if not isinstance(fixture, dict) or fixture.get("availability") != "available":
        return None
    entries = fixture.get("entries")
    return {"recent_sleep_pattern": entries} if isinstance(entries, list) and entries else None


def fixed_ask_target(text: str) -> str | None:
    """Telemetry-only classifier; it never feeds back into Fixed behavior."""
    if "上床" in text or "躺下" in text:
        return "bedtime"
    if "入睡" in text or "睡着" in text:
        return "sleep_time_or_sleep_onset_latency"
    if "起床" in text or "醒来时间" in text:
        return "wake_time"
    if "夜" in text and "醒" in text:
        return "nighttime_awakenings"
    if "总睡眠" in text or "睡多久" in text:
        return "total_sleep_time"
    if "最近" in text and ("睡眠" in text or "作息" in text):
        return "recent_sleep_pattern"
    return None


def fixed_is_ask(text: str) -> bool:
    return "？" in text or "?" in text


def message_content(message: Any) -> str:
    value = getattr(message, "content", "")
    return value if isinstance(value, str) else str(value)


def direct_message_usage(messages: list[Any]) -> dict[str, int] | None:
    """Read only API metadata already attached to legacy direct responses."""
    total = prompt = completion = 0
    found = False
    for message in messages:
        metadata = getattr(message, "response_metadata", {}) or {}
        usage = metadata.get("token_usage") or metadata.get("usage") or {}
        if not isinstance(usage, dict):
            continue
        found = True
        total += int(usage.get("total_tokens") or 0)
        prompt += int(usage.get("prompt_tokens") or 0)
        completion += int(usage.get("completion_tokens") or 0)
    if not found:
        return None
    return {"input_tokens": prompt, "output_tokens": completion, "total_tokens": total}


def cost_record(*, usage: dict[str, Any] | None, usage_scope: str, rag_calls: int,
                tool_calls: int, turns: int, steps: int, latency_ms: float,
                observed_direct_llm_responses: int | None) -> dict[str, Any]:
    """Never convert partial telemetry into a fictional end-to-end measurement."""
    return {
        "input_tokens": (usage or {}).get("input_tokens", (usage or {}).get("prompt_tokens", "not_available")),
        "output_tokens": (usage or {}).get("output_tokens", (usage or {}).get("completion_tokens", "not_available")),
        "total_tokens": (usage or {}).get("total_tokens", "not_available"),
        "token_usage_scope": usage_scope if usage else "not_available",
        "LLM_calls": "not_available",
        "observed_direct_llm_responses": observed_direct_llm_responses if observed_direct_llm_responses is not None else "not_available",
        "RAG_calls": rag_calls,
        "tool_calls": tool_calls,
        "total_latency_ms": latency_ms,
        "LLM_latency_ms": "not_available",
        "retrieval_latency_ms": "not_available",
        "tool_latency_ms": "not_available",
        "conversation_turns": turns,
        "internal_steps": steps,
    }


class ExperimentAdapter(Protocol):
    """Common experiment boundary: case + turn + session + resources → normalized trace."""

    system_name: str

    def run_case(self, case: dict[str, Any]) -> dict[str, Any]:
        """Run one isolated benchmark case without changing Agent behavior."""


class AdaptiveExperimentAdapter:
    system_name = "adaptive"

    def __init__(self, service: Any, app: Any) -> None:
        self.service = service
        self.app = app

    def run_case(self, case: dict[str, Any]) -> dict[str, Any]:
        from adaptive_agent.service import AdaptiveSession
        from adaptive_agent.tools import SessionDiaryTool

        case_id, profile = case["case_id"], case["hidden_profile"]
        self.service.sessions[case_id] = AdaptiveSession()
        self.service.loop.diary_tool = SessionDiaryTool(diary_facts(profile.get("diary_fixture")))
        messages, turns = [case["user_query"]], []
        for turn in range(1, MAX_TURNS + 1):
            started = perf_counter()
            try:
                response = self.app.test_client().post("/api/chat", json={"session_id": case_id, "message": messages[-1]})
                payload = response.get_json(silent=True) or {"raw_http_body": response.get_data(as_text=True)[:4000]}
                status = response.status_code
            except Exception as exc:
                payload, status = {"exception": str(exc), "traceback": traceback.format_exc()}, 0
            state = deepcopy(self.service.sessions[case_id].state)
            turns.append({"turn": turn, "raw_input": messages[-1], "http_status": status, "response": payload,
                          "latency_ms": round((perf_counter() - started) * 1000, 2), "state_snapshot": state})
            if status != 200 or payload.get("status") != "ASK":
                break
            history = state.action_history
            messages.append(follow_up_message(history[-1].get("target") if history else None,
                                              profile.get("follow_up_facts", {})))

        state = self.service.sessions[case_id].state
        path = [entry["action"] for entry in state.action_history]
        usage = getattr(self.service.loop.answer_generator, "last_token_usage", None)
        cost = cost_record(
            usage=usage, usage_scope="final_answer_generation_response_only", rag_calls=path.count("RETRIEVE"),
            tool_calls=sum(path.count(action) for action in ("RETRIEVE", "READ_DIARY")), turns=len(turns),
            steps=sum(turn["response"].get("steps", 0) for turn in turns),
            latency_ms=round(sum(turn["latency_ms"] for turn in turns), 2), observed_direct_llm_responses=1,
        )
        return {
            "system": self.system_name, "benchmark_version": "1.1", "case_id": case_id,
            "goal": state.goal, "task_type": state.task_type.value if state.task_type else None,
            "assistant_response": turns[-1]["response"].get("assistant", "") if turns else "",
            "action_path": path,
            "ask_targets": [entry.get("target") for entry in state.action_history if entry["action"] == "ASK"],
            "tool_calls": [entry["action"] for entry in state.action_history if entry["action"] in {"RETRIEVE", "READ_DIARY"}],
            "evidence_used": deepcopy(state.evidence),
            "state_snapshot": {
                "availability": "available", "goal": state.goal,
                "task_type": state.task_type.value if state.task_type else None, "facts": deepcopy(state.facts),
                "missing_information": {"critical": list(state.critical_missing), "secondary": list(state.secondary_missing),
                                        "decision": list(state.decision_missing)},
                "sufficiency": {"user_info": state.user_info_sufficiency, "evidence": state.evidence_sufficiency},
                "candidates": [asdict(item) for item in state.candidate_actions],
                "selected_action": deepcopy(state.action_history[-1]) if state.action_history else None,
                "evidence": deepcopy(state.evidence), "resource_status": deepcopy(state.resource_status),
            },
            "steps": cost["internal_steps"], "turns": cost["conversation_turns"], "token_usage": usage,
            "latency_ms": cost["total_latency_ms"], "cost_metrics": cost,
            "final_status": turns[-1]["response"].get("status", "HTTP_ERROR") if turns else "HTTP_ERROR", "turn_log": turns,
        }


class FixedExperimentAdapter:
    system_name = "fixed"

    def __init__(self, fixed: Any, base_history: list[Any]) -> None:
        self.fixed = fixed
        self.base_history = base_history

    def run_case(self, case: dict[str, Any]) -> dict[str, Any]:
        from langchain_core.messages import HumanMessage, ToolMessage

        case_id, profile = case["case_id"], case["hidden_profile"]
        history, messages, turns = deepcopy(self.base_history), [case["user_query"]], []
        actions, targets = [], []
        for turn in range(1, MAX_TURNS + 1):
            current, started = messages[-1], perf_counter()
            try:
                request_messages = history + [HumanMessage(content=current)]
                outcome = self.fixed.main_graph.invoke({"messages": request_messages, "enter_stage": ""})
                all_messages = outcome.get("messages", [])
                new_messages, status, error = all_messages[len(request_messages):], 200, None
            except Exception:
                outcome, new_messages, status, error = {}, [], 0, traceback.format_exc()
            tool_messages = [item for item in new_messages if isinstance(item, ToolMessage)]
            if any(getattr(item, "name", "") == "retrieval_augmentation_generation" for item in tool_messages):
                actions.append("RETRIEVE")
            ai_messages = [item for item in new_messages if item.__class__.__name__ == "AIMessage"]
            answer = message_content(ai_messages[-1]) if ai_messages else ""
            action = "ASK" if fixed_is_ask(answer) else "ANSWER"
            target = fixed_ask_target(answer) if action == "ASK" else None
            actions.append(action)
            if action == "ASK":
                targets.append(target)
            history.extend([HumanMessage(content=current)] + new_messages)
            turns.append({"turn": turn, "raw_input": current, "http_status": status,
                          "legacy_workflow_state": outcome.get("enter_stage", "not_available"),
                          "new_messages": new_messages, "assistant_response": answer, "derived_action": action,
                          "derived_ask_target": target, "latency_ms": round((perf_counter() - started) * 1000, 2), "error": error})
            if status != 200 or action != "ASK":
                break
            messages.append(follow_up_message(target, profile.get("follow_up_facts", {})))

        final = turns[-1] if turns else {}
        new_messages = [message for turn in turns for message in turn.get("new_messages", [])]
        usage = direct_message_usage(new_messages)
        rag_calls = actions.count("RETRIEVE")
        cost = cost_record(
            usage=usage, usage_scope="legacy_direct_response_metadata_only", rag_calls=rag_calls, tool_calls=rag_calls,
            turns=len(turns), steps=len(actions), latency_ms=round(sum(turn["latency_ms"] for turn in turns), 2),
            observed_direct_llm_responses=sum(message.__class__.__name__ == "AIMessage" for message in new_messages),
        )
        return {
            "system": self.system_name, "benchmark_version": "1.1", "case_id": case_id,
            "goal": "not_available", "task_type": "not_available", "assistant_response": final.get("assistant_response", ""),
            "action_path": actions, "ask_targets": targets,
            "tool_calls": ["RETRIEVE"] * rag_calls, "evidence_used": "not_available",
            "state_snapshot": {"availability": "legacy_observable_only", "legacy_workflow_state": final.get("legacy_workflow_state", "not_available"),
                               "goal": "not_available", "task_type": "not_available", "facts": "not_available",
                               "missing_information": "not_available", "sufficiency": "not_available", "candidates": "not_available",
                               "selected_action": final.get("derived_action", "not_available"), "evidence": "not_available"},
            "steps": cost["internal_steps"], "turns": cost["conversation_turns"], "token_usage": usage,
            "latency_ms": cost["total_latency_ms"], "cost_metrics": cost,
            "final_status": final.get("derived_action", "HTTP_ERROR"), "turn_log": turns,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()

    from adaptive_agent.service import AdaptiveSession
    from adaptive_agent.tools import SessionDiaryTool
    from evaluation.recorder import EvaluationRecorder
    from main_flask import CognitiveTherapyAgent, _create_adaptive_chat_service, create_app

    spec, cases, overrides = load_cases()
    output = ROOT / "evaluation" / "runs" / f"step5_5-{args.tag}"
    output.mkdir(parents=True, exist_ok=True)

    service = _create_adaptive_chat_service()
    service.recorder = EvaluationRecorder(output / "adaptive-recorder")
    app = create_app(service)
    app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=True)
    fixed = CognitiveTherapyAgent()
    adapters: list[ExperimentAdapter] = [
        FixedExperimentAdapter(fixed, deepcopy(fixed.message_history)),
        AdaptiveExperimentAdapter(service, app),
    ]
    files = {"fixed": (output / "fixed_matched_traces.jsonl").open("w", encoding="utf-8"),
             "adaptive": (output / "adaptive_matched_traces.jsonl").open("w", encoding="utf-8")}
    try:
        for case in cases:
            results = {adapter.system_name: adapter.run_case(case) for adapter in adapters}
            for system, result in results.items():
                files[system].write(json.dumps(result, ensure_ascii=False, default=encode) + "\n")
                files[system].flush()
            print(json.dumps({"case_id": case["case_id"], "fixed": results["fixed"]["action_path"],
                              "adaptive": results["adaptive"]["action_path"]}, ensure_ascii=False), flush=True)
    finally:
        for handle in files.values():
            handle.close()

    confounds = [
        "Fixed is run through its existing LangGraph entrypoint; Adaptive is run through existing Flask /api/chat.",
        "Fixed has no structured goal/task/fact/sufficiency/candidate State; fields are recorded as not_available rather than synthesized.",
        "Fixed has no READ_DIARY capability. DA-01 and DA-02 are capability_gap_cases, excluded from the primary matched subset.",
        "Fixed retains its legacy prompt-level medical constraints while Adaptive retains its existing constrained answer prompt; these prompts are not identical and cannot be normalized without changing behavior.",
        "Token metadata is partial: Fixed exposes direct response metadata; Adaptive exposes final answer-generation metadata. Full LLM calls and component latency are not available from current interfaces.",
    ]
    (output / "experimental_confounds.json").write_text(json.dumps({
        "benchmark_version": spec["benchmark_version"], "capability_matched_cases": [case["case_id"] for case in cases if not case["case_id"].startswith("DA-")],
        "capability_gap_cases": ["DA-01-seven-day-diary-available", "DA-02-seven-day-diary-unavailable"],
        "confounds": confounds, "case_overrides_applied": sorted(overrides),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
