"""Run frozen Benchmark V1.1 cases against legacy Fixed and current Adaptive paths.

This is evaluation tooling only. It does not alter either system's behavior. Fixed
uses its existing LangGraph entrypoint; Adaptive uses its existing Flask /api/chat
route. The resulting traces record interface differences as experimental confounds.
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
from typing import Any

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


def load_cases() -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    overlay_path = ROOT / "evaluation" / "benchmark_v1_1.yaml"
    overlay = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))
    base = yaml.safe_load((overlay_path.parent / overlay["base_benchmark"]).read_text(encoding="utf-8"))
    overrides = overlay.get("case_overrides", {})
    cases = []
    for raw in base["cases"]:
        case = deepcopy(raw)
        case.update(deepcopy(overrides.get(case["case_id"], {})))
        cases.append(case)
    overlay["cases"] = cases
    return overlay, overrides


def follow_up_message(target: str | None, facts: dict[str, Any]) -> str:
    """Release only a response to an actual/inferred ASK target as a user message."""
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
    if target == "total_sleep_time":
        if isinstance(value, (int, float)):
            return f"我每晚总共大约睡 {value:g} 分钟。"
        if value:
            return "我目前无法可靠估计每晚总睡眠时间。"
    if target == "recent_sleep_pattern" and value:
        return f"我的近期睡眠模式是：{value}。"
    if target == "nighttime_awakenings" and value is not None:
        return f"我夜里通常醒 {value} 次。"
    return "这项信息我目前不清楚。"


def diary_facts(fixture: Any) -> dict[str, Any] | None:
    """V1.1 canonical DA-01 projection; no derived diary summary is fabricated."""
    if not isinstance(fixture, dict) or fixture.get("availability") != "available":
        return None
    entries = fixture.get("entries")
    return {"recent_sleep_pattern": entries} if isinstance(entries, list) and entries else None


def inferred_fixed_ask_target(text: str) -> str | None:
    """Telemetry-only target classifier; it does not steer the legacy workflow."""
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


def is_fixed_ask(text: str) -> bool:
    return "？" in text or "?" in text


def message_content(message: Any) -> str:
    value = getattr(message, "content", "")
    return value if isinstance(value, str) else str(value)


def observed_usage(messages: list[Any]) -> dict[str, int] | None:
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
    return {"total_tokens": total, "prompt_tokens": prompt, "completion_tokens": completion} if found else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()

    from adaptive_agent.service import AdaptiveSession
    from adaptive_agent.tools import SessionDiaryTool
    from evaluation.recorder import EvaluationRecorder
    from langchain_core.messages import HumanMessage, ToolMessage
    from main_flask import CognitiveTherapyAgent, _create_adaptive_chat_service, create_app

    spec, overrides = load_cases()
    output = ROOT / "evaluation" / "runs" / f"step5_3-{args.tag}"
    output.mkdir(parents=True, exist_ok=True)

    adaptive = _create_adaptive_chat_service()
    adaptive.recorder = EvaluationRecorder(output / "adaptive-recorder")
    app = create_app(adaptive)
    app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=True)
    fixed = CognitiveTherapyAgent()
    fixed_base_history = deepcopy(fixed.message_history)

    confounds = [
        "Fixed is invoked through its existing LangGraph entrypoint; it has no legacy /api/chat route.",
        "Fixed has message history rather than AdaptiveAgentState, so fixed structured facts/state are unavailable.",
        "Fixed has no READ_DIARY tool; diary fixtures remain unavailable to Fixed rather than being injected into prompts.",
        "Adaptive token_usage is answer-generator metadata only; Fixed token usage is response metadata when exposed. These are observed, not end-to-end comparable token totals.",
    ]

    def run_adaptive(case: dict[str, Any]) -> dict[str, Any]:
        case_id, profile = case["case_id"], case["hidden_profile"]
        adaptive.sessions[case_id] = AdaptiveSession()
        adaptive.loop.diary_tool = SessionDiaryTool(diary_facts(profile.get("diary_fixture")))
        messages, turns = [case["user_query"]], []
        for turn in range(1, MAX_TURNS + 1):
            started = perf_counter()
            try:
                response = app.test_client().post("/api/chat", json={"session_id": case_id, "message": messages[-1]})
                payload = response.get_json(silent=True) or {"raw_http_body": response.get_data(as_text=True)[:4000]}
                status = response.status_code
            except Exception as exc:
                payload, status = {"exception": str(exc), "traceback": traceback.format_exc()}, 0
            state = deepcopy(adaptive.sessions[case_id].state)
            turns.append({"turn": turn, "raw_input": messages[-1], "http_status": status,
                          "response": payload, "latency_ms": round((perf_counter() - started) * 1000, 2),
                          "state_after_turn": state})
            if status != 200 or payload.get("status") != "ASK":
                break
            target = state.action_history[-1].get("target") if state.action_history else None
            messages.append(follow_up_message(target, profile.get("follow_up_facts", {})))
        state = adaptive.sessions[case_id].state
        path = [entry["action"] for entry in state.action_history]
        return {
            "system": "adaptive", "benchmark_version": spec["benchmark_version"], "case_id": case_id,
            "goal": state.goal, "task_type": state.task_type.value if state.task_type else None,
            "facts_state": {"facts": state.facts, "resource_status": state.resource_status,
                            "evidence": state.evidence, "action_history": state.action_history},
            "action_path": path, "ask_count": path.count("ASK"),
            "ask_targets": [entry.get("target") for entry in state.action_history if entry["action"] == "ASK"],
            "retrieve_count": path.count("RETRIEVE"), "read_diary_count": path.count("READ_DIARY"),
            "total_tool_calls": sum(path.count(action) for action in ("RETRIEVE", "READ_DIARY")),
            "total_steps": sum(turn["response"].get("steps", 0) for turn in turns), "total_turns": len(turns),
            "token_usage": getattr(adaptive.loop.answer_generator, "last_token_usage", None),
            "latency_ms": round(sum(turn["latency_ms"] for turn in turns), 2),
            "final_answer": turns[-1]["response"].get("assistant", ""),
            "final_status": turns[-1]["response"].get("status", "HTTP_ERROR"),
            "critical_failure": None, "failure_attribution": None, "turns": turns,
        }

    def run_fixed(case: dict[str, Any]) -> dict[str, Any]:
        case_id, profile = case["case_id"], case["hidden_profile"]
        history, messages, turns = deepcopy(fixed_base_history), [case["user_query"]], []
        action_path: list[str] = []
        ask_targets: list[str | None] = []
        for turn in range(1, MAX_TURNS + 1):
            current = messages[-1]
            started = perf_counter()
            try:
                request_messages = history + [HumanMessage(content=current)]
                outcome = fixed.main_graph.invoke({"messages": request_messages, "enter_stage": ""})
                all_messages = outcome.get("messages", [])
                new_messages = all_messages[len(request_messages):]
                status, error = 200, None
            except Exception as exc:
                outcome, new_messages, status, error = {}, [], 0, traceback.format_exc()
            latency = round((perf_counter() - started) * 1000, 2)
            tool_messages = [item for item in new_messages if isinstance(item, ToolMessage)]
            if any(getattr(item, "name", "") == "retrieval_augmentation_generation" for item in tool_messages):
                action_path.append("RETRIEVE")
            ai_messages = [item for item in new_messages if item.__class__.__name__ == "AIMessage"]
            answer = message_content(ai_messages[-1]) if ai_messages else ""
            ask = is_fixed_ask(answer)
            target = inferred_fixed_ask_target(answer) if ask else None
            action_path.append("ASK" if ask else "ANSWER")
            if ask:
                ask_targets.append(target)
            history.extend([HumanMessage(content=current)] + new_messages)
            turns.append({"turn": turn, "raw_input": current, "http_status": status, "enter_stage": outcome.get("enter_stage"),
                          "new_messages": new_messages, "final_turn_answer": answer, "derived_action": action_path[-1],
                          "derived_ask_target": target, "latency_ms": latency, "error": error})
            if status != 200 or not ask:
                break
            messages.append(follow_up_message(target, profile.get("follow_up_facts", {})))
        final = turns[-1] if turns else {}
        usage = observed_usage([message for turn in turns for message in turn.get("new_messages", [])])
        return {
            "system": "fixed", "benchmark_version": spec["benchmark_version"], "case_id": case_id,
            "goal": None, "task_type": None,
            "facts_state": {"structured_state_available": False, "message_history_length": len(history),
                            "diary_fixture_access": False},
            "action_path": action_path, "ask_count": action_path.count("ASK"), "ask_targets": ask_targets,
            "retrieve_count": action_path.count("RETRIEVE"), "read_diary_count": 0,
            "total_tool_calls": action_path.count("RETRIEVE"), "total_steps": len(action_path), "total_turns": len(turns),
            "token_usage": usage, "latency_ms": round(sum(turn["latency_ms"] for turn in turns), 2),
            "final_answer": final.get("final_turn_answer", ""), "final_status": final.get("derived_action", "HTTP_ERROR"),
            "critical_failure": None, "failure_attribution": None, "turns": turns,
        }

    with (output / "adaptive-traces.jsonl").open("w", encoding="utf-8") as adaptive_out, \
         (output / "fixed-traces.jsonl").open("w", encoding="utf-8") as fixed_out:
        for case in spec["cases"]:
            adaptive_result, fixed_result = run_adaptive(case), run_fixed(case)
            adaptive_out.write(json.dumps(adaptive_result, ensure_ascii=False, default=encode) + "\n")
            fixed_out.write(json.dumps(fixed_result, ensure_ascii=False, default=encode) + "\n")
            adaptive_out.flush(); fixed_out.flush()
            print(json.dumps({"case_id": case["case_id"], "adaptive": adaptive_result["action_path"],
                              "fixed": fixed_result["action_path"]}, ensure_ascii=False), flush=True)

    (output / "experimental-confounds.json").write_text(json.dumps({
        "benchmark_version": spec["benchmark_version"], "confounds": confounds,
        "case_overrides_applied": sorted(overrides),
    }, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
