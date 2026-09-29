"""One immutable V1.2.1 development/regression run on frozen Benchmark V2."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation/v1_2_1"
BENCHMARK = ROOT / "evaluation/benchmarks/benchmark_v2_cases.yaml"
MAX_TURNS = 6

SOURCE_FILES = (
    "adaptive_agent/state.py", "adaptive_agent/requirements.py",
    "adaptive_agent/sufficiency.py", "adaptive_agent/information_value.py",
    "adaptive_agent/preconditions.py", "adaptive_agent/candidates.py",
    "adaptive_agent/policy.py", "adaptive_agent/runner.py",
    "adaptive_agent/state_update.py", "adaptive_agent/tools.py",
    "adaptive_agent/answer_generation.py", "adaptive_agent/input_understanding.py",
    "model_config.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def diary_payload(case: dict) -> dict | None:
    fixture = case["diary_facts"]
    return deepcopy(fixture.get("facts") or None) if fixture.get("availability") == "available" else None


def follow_up(target: str | None, facts: dict) -> str:
    value = facts.get(target or "")
    templates = {
        "bedtime": "我通常 {v} 上床。",
        "wake_time": "我通常 {v} 起床。",
        "sleep_time_or_sleep_onset_latency": "我通常上床后约 {v} 才睡着。",
        "nighttime_awakenings": "我夜里通常醒 {v}。",
        "total_sleep_time": "我估计每晚总共睡 {v}。",
        "recent_sleep_pattern": "最近的模式是：{v}。",
    }
    if value in (None, "", [], {}):
        return "这项信息我目前不清楚。"
    return templates.get(target, "关于" + str(target) + "，{v}。").format(v=value)


def state_view(state) -> dict:
    return {
        "goal": state.goal,
        "task_type": state.task_type.value if state.task_type else None,
        "facts": deepcopy(state.facts),
        "fact_sources": deepcopy(state.fact_sources),
        "missing_information": {
            "critical": list(state.critical_missing),
            "required": list(state.required_missing),
            "decision": list(state.decision_missing),
            "decision_relevant": list(state.decision_relevant_missing),
            "validity_critical": list(state.validity_critical_missing),
            "secondary": list(state.secondary_missing),
        },
        "sufficiency": {"user_info": state.user_info_sufficiency, "evidence": state.evidence_sufficiency},
        "preconditions_considered": deepcopy(state.preconditions_considered),
        "information_estimates": deepcopy(state.information_estimates),
        "considered_information": deepcopy(state.considered_information),
        "rejected_information": deepcopy(state.rejected_information),
        "candidate_actions": [asdict(item) for item in state.candidate_actions],
        "selected_actions": deepcopy(state.action_history),
        "evidence_used": deepcopy(state.evidence),
        "resource_status": deepcopy(state.resource_status),
        "diary_projection": deepcopy(state.diary_projection),
        "stop_reason": state.stop_reason,
        "answer_scope": state.answer_scope,
    }


def write_manifest(spec: dict) -> None:
    manifest_path = OUT / "step8_9_freeze_manifest.json"
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing.get("benchmark", {}).get("sha256") != sha256(BENCHMARK):
            raise RuntimeError("existing freeze manifest does not match Benchmark V2")
        # The first execution can be interrupted before case one (for example by
        # runner infrastructure).  Preserve its manifest and permit continuation
        # only while no raw trace exists; completed runs still refuse overwrite.
        return
    manifest = {
        "run_name": "v1_2_1_development_regression_evaluation_on_benchmark_v2",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "agent_version": "adaptive-agent-v1.2.1",
        "git_commit": "not_available_no_HEAD_commit",
        "benchmark": {
            "path": str(BENCHMARK.relative_to(ROOT)),
            "version": spec.get("benchmark_version"),
            "status": spec.get("status"),
            "sha256": sha256(BENCHMARK),
            "interpretation": "development_regression_set_not_held_out",
        },
        "evaluation_configuration": {
            "rubric": "evaluation/benchmark_v1_1_scoring.md",
            "rubric_sha256": sha256(ROOT / "evaluation/benchmark_v1_1_scoring.md"),
            "max_turns": MAX_TURNS,
            "entrypoint": "Flask /api/chat via test_client",
            "follow_up_release": "only answers the actual ASK target; never directly mutates State",
            "diary_fixture_visibility": "only via SessionDiaryTool and READ_DIARY",
        },
        "model_configuration": {
            "factory": "model_config.create_chat_model",
            "model": os.getenv("DEEPSEEK_MODEL") or os.getenv("KIMI_MODEL") or "default_from_model_config",
            "base_url_configured": bool(os.getenv("DEEPSEEK_BASE_URL") or os.getenv("KIMI_BASE_URL")),
            "api_key": "redacted_not_recorded",
        },
        "source_sha256": {name: sha256(ROOT / name) for name in SOURCE_FILES},
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(*, before_case=None, after_case=None, trace_path: Path | None = None) -> None:
    sys.path.insert(0, str(ROOT))
    spec = yaml.safe_load(BENCHMARK.read_text(encoding="utf-8"))
    if spec.get("status") != "benchmark_v2_frozen":
        raise RuntimeError("Benchmark V2 must be frozen before this run.")
    OUT.mkdir(parents=True, exist_ok=True)
    trace_path = trace_path or OUT / "step8_9_raw_traces.jsonl"
    if trace_path.exists() and trace_path.stat().st_size:
        raise RuntimeError(f"refusing to overwrite first complete run: {trace_path}")
    write_manifest(spec)

    from adaptive_agent.service import AdaptiveSession
    from adaptive_agent.tools import SessionDiaryTool
    from evaluation.recorder import EvaluationRecorder
    from main_flask import _create_adaptive_chat_service, create_app

    service = _create_adaptive_chat_service()
    service.recorder = EvaluationRecorder(OUT / "step8_9_recorder")
    app = create_app(service)
    app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=True)

    with trace_path.open("w", encoding="utf-8") as stream:
        for case in spec["cases"]:
            case_id = case["case_id"]
            if before_case:
                before_case(case)
            service.sessions[case_id] = AdaptiveSession()
            service.loop.diary_tool = SessionDiaryTool(diary_payload(case))
            messages, turns = [case["user_query"]], []
            for turn in range(1, MAX_TURNS + 1):
                started = perf_counter()
                response = app.test_client().post("/api/chat", json={"session_id": case_id, "message": messages[-1]})
                latency_ms = round((perf_counter() - started) * 1000, 2)
                payload = response.get_json(silent=True) or {"raw_http_body": response.get_data(as_text=True)[:4000]}
                state = deepcopy(service.sessions[case_id].state)
                turns.append({
                    "turn": turn, "user_turn": messages[-1], "http_status": response.status_code,
                    "response": payload, "latency_ms": latency_ms, "state_transition": state_view(state),
                })
                if response.status_code != 200 or payload.get("status") != "ASK":
                    break
                target = state.action_history[-1].get("target") if state.action_history else None
                messages.append(follow_up(target, case["follow_up_facts"]))

            state = service.sessions[case_id].state
            path = [entry["action"] for entry in state.action_history]
            result = {
                "case_id": case_id, "task_type": case["task_type"], "difficulty": case["difficulty"],
                "language_type": case["language"], "user_turns": messages[:len(turns)],
                "extracted_facts": deepcopy(state.facts), "state_transitions": turns,
                "missing_information": state_view(state)["missing_information"],
                "sufficiency": state_view(state)["sufficiency"],
                "preconditions_considered": deepcopy(state.preconditions_considered),
                "information_estimates": deepcopy(state.information_estimates),
                "considered_information": [item for current in turns for item in current["state_transition"]["considered_information"]],
                "rejected_information": [item for current in turns for item in current["state_transition"]["rejected_information"]],
                "candidate_actions": [item for current in turns for item in current["state_transition"]["candidate_actions"]],
                "selected_actions": deepcopy(state.action_history),
                "tool_calls": [action for action in path if action in {"RETRIEVE", "READ_DIARY"}],
                "evidence_used": deepcopy(state.evidence), "answer_scope": state.answer_scope,
                "stop_reason": state.stop_reason, "final_answer": turns[-1]["response"].get("assistant", ""),
                "action_path": path, "ASK_count": path.count("ASK"), "RETRIEVE_count": path.count("RETRIEVE"),
                "READ_DIARY_count": path.count("READ_DIARY"), "turns": len(turns),
                "steps": sum(current["response"].get("steps", 0) for current in turns),
                "total_latency_ms": round(sum(current["latency_ms"] for current in turns), 2),
                "token_usage": "not_available", "LLM_calls": "not_available",
                "LLM_latency": "not_available", "retrieval_latency": "not_available", "tool_latency": "not_available",
                "final_status": turns[-1]["response"].get("status", "HTTP_ERROR"),
            }
            stream.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
            stream.flush()
            if after_case:
                after_case(case, result)
            print(json.dumps({"case_id": case_id, "path": path, "status": result["final_status"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
