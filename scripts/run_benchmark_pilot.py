"""Run Benchmark V1 cases through the existing real Flask /api/chat route.

The YAML hidden profile is evaluator-only: follow-up facts are released only after
an ASK, and a diary fixture is exposed only through SessionDiaryTool. This script
observes the existing adaptive agent; it does not replace its policy, requirements,
input-understanding, retrieval, or answer-generation components.
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


def encode(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    raise TypeError(type(value).__name__)


def follow_up_message(target: str | None, facts: dict[str, Any]) -> str:
    """Turn the one permitted follow-up fact into a user message, without injection."""
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
    if target == "sleep_onset_latency" and isinstance(value, (int, float)):
        return f"我通常上床后约 {value:g} 分钟才能睡着。"
    if target == "total_sleep_time":
        if isinstance(value, (int, float)):
            return f"我每晚总共大约睡 {value:g} 分钟。"
        if value:
            return "我目前无法可靠估计每晚总睡眠时间。"
    if target == "recent_sleep_pattern" and value:
        return f"我的近期睡眠模式是：{value}。"
    if target in {"caffeine", "nap", "exercise", "screen_before_bed", "perceived_stress",
                  "nighttime_awakenings"} and value is not None:
        return f"关于 {target}，我提供的信息是：{value}。"
    return "这项信息我目前不清楚。"


def diary_facts(fixture: Any) -> dict[str, Any] | None:
    """Pass the stored seven-entry fixture as data, not as model-visible prompt text."""
    if not isinstance(fixture, dict) or fixture.get("availability") != "available":
        return None
    entries = fixture.get("entries")
    return {"recent_sleep_pattern": entries} if isinstance(entries, list) and entries else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()

    from adaptive_agent.service import AdaptiveSession
    from adaptive_agent.tools import SessionDiaryTool
    from evaluation.recorder import EvaluationRecorder
    from main_flask import _create_adaptive_chat_service, create_app

    spec = yaml.safe_load((ROOT / "evaluation" / "benchmark_v1_cases.yaml").read_text(encoding="utf-8"))
    output = ROOT / "evaluation" / "runs" / f"step5_1-{args.tag}"
    output.mkdir(parents=True, exist_ok=True)
    service = _create_adaptive_chat_service()
    service.recorder = EvaluationRecorder(output)
    app = create_app(service)
    app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=True)

    observations: list[dict[str, Any]] = []

    def observe(owner: Any, method: str, event: str) -> None:
        original = getattr(owner, method)

        def wrapped(*inputs: Any, **kwargs: Any) -> Any:
            result = original(*inputs, **kwargs)
            observations.append({"event": event, "inputs": deepcopy(inputs), "result": deepcopy(result)})
            return result

        setattr(owner, method, wrapped)

    observe(service.loop.understander, "understand", "input_understanding")
    observe(service.loop.retrieval_tool, "retrieve", "retrieval")
    observe(service.loop.policy, "choose", "decision")
    observe(service.loop, "run_turn", "loop_result")

    with (output / "pilot-traces.jsonl").open("w", encoding="utf-8") as trace_stream:
        for case in spec["cases"]:
            case_id = case["case_id"]
            profile = case["hidden_profile"]
            service.sessions[case_id] = AdaptiveSession()
            service.loop.diary_tool = SessionDiaryTool(diary_facts(profile.get("diary_fixture")))
            observe(service.loop.diary_tool, "read", "read_diary")
            messages = [case["user_query"]]
            turns: list[dict[str, Any]] = []

            for turn_number in range(1, 7):
                message = messages[-1]
                observations.clear()
                started = perf_counter()
                try:
                    response = app.test_client().post(
                        "/api/chat", json={"session_id": case_id, "message": message}
                    )
                except Exception as exc:
                    response = None
                    payload = {"exception_type": type(exc).__name__, "exception": str(exc),
                               "traceback": traceback.format_exc()}
                latency_ms = round((perf_counter() - started) * 1000, 2)
                if response is not None:
                    payload = response.get_json(silent=True)
                if response is not None and payload is None:
                    payload = {"raw_http_body": response.get_data(as_text=True)[:4000]}
                state = deepcopy(service.sessions[case_id].state)
                turns.append({
                    "turn": turn_number,
                    "raw_input": message,
                    "http_status": response.status_code if response is not None else 0,
                    "response": payload,
                    "latency_ms": latency_ms,
                    "observations": deepcopy(observations),
                    "state_after_turn": state,
                })
                if response is None or response.status_code != 200 or payload.get("status") != "ASK":
                    break
                target = state.action_history[-1].get("target") if state.action_history else None
                messages.append(follow_up_message(target, profile.get("follow_up_facts", {})))

            final_state = service.sessions[case_id].state
            action_path = [item["action"] for item in final_state.action_history]
            trace = {
                "benchmark_version": spec["schema_version"],
                "mode": "real_adaptive_agent_via_flask_test_client",
                "fictional_test_data": True,
                "case_id": case_id,
                "raw_input": case["user_query"],
                "goal": final_state.goal,
                "task_type": final_state.task_type.value if final_state.task_type else None,
                "extracted_facts": final_state.facts,
                "action_path": action_path,
                "ask_targets": [item.get("target") for item in final_state.action_history if item["action"] == "ASK"],
                "ask_count": action_path.count("ASK"),
                "retrieve_count": action_path.count("RETRIEVE"),
                "read_diary_count": action_path.count("READ_DIARY"),
                "tool_calls": [item["action"] for item in final_state.action_history if item["action"] in {"RETRIEVE", "READ_DIARY"}],
                "total_steps": sum(turn["response"].get("steps", 0) for turn in turns if turn["response"]),
                "total_turns": len(turns),
                "retrieved_evidence": final_state.evidence,
                "answer_scope": final_state.answer_scope,
                "final_status": turns[-1]["response"].get("status") if turns[-1]["response"] else "HTTP_ERROR",
                "final_answer": turns[-1]["response"].get("assistant") if turns[-1]["response"] else "",
                "latency_ms": round(sum(turn["latency_ms"] for turn in turns), 2),
                "token_usage": getattr(service.loop.answer_generator, "last_token_usage", None),
                "turns": turns,
            }
            trace_stream.write(json.dumps(trace, ensure_ascii=False, default=encode) + "\n")
            trace_stream.flush()
            print(json.dumps({
                "case_id": case_id,
                "status": trace["final_status"],
                "action_path": action_path,
                "turns": len(turns),
            }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
