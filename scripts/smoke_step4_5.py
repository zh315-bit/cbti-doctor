"""Real-model Step 4.5 smoke test through the existing Flask /api/chat route.

All user messages and diary entries below are fictional test data.  The script uses
the configured real input-understanding model, project RAG, and answer generator;
it observes them without replacing the Adaptive Agent policy or production flow.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _encode(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    raise TypeError(type(value).__name__)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()

    from adaptive_agent.service import AdaptiveSession
    from adaptive_agent.tools import SessionDiaryTool
    from evaluation.recorder import EvaluationRecorder
    from main_flask import _create_adaptive_chat_service, create_app

    output = ROOT / "evaluation" / "runs" / f"step4_5-{args.tag}"
    output.mkdir(parents=True, exist_ok=True)
    service = _create_adaptive_chat_service()
    service.recorder = EvaluationRecorder(output)
    app = create_app(service)
    observations: list[dict[str, Any]] = []

    def observe(owner: Any, method: str, event: str) -> None:
        original = getattr(owner, method)

        def wrapped(*inputs: Any, **kwargs: Any) -> Any:
            result = original(*inputs, **kwargs)
            observations.append({"event": event, "inputs": deepcopy(inputs),
                                 "result": deepcopy(result)})
            return result

        setattr(owner, method, wrapped)

    observe(service.loop.understander, "understand", "input_understanding")
    observe(service.loop.retrieval_tool, "retrieve", "retrieval")
    observe(service.loop.policy, "choose", "decision")
    observe(service.loop, "run_turn", "loop_result")

    fictional_diary = {
        "bedtime": "23:00",
        "wake_time": "07:00",
        "sleep_onset_latency": 60,
        "total_sleep_time": 360,
        "nighttime_awakenings": 1,
        "recent_sleep_pattern": [
            {"date": f"2026-09-{day:02d}", "bedtime": "23:00", "wake_time": "07:00",
             "sleep_onset_latency": 60, "total_sleep_time": 360,
             "nighttime_awakenings": 1}
            for day in range(11, 18)
        ],
    }

    cases = [
        ("knowledge_qa", "虚构测试：什么是刺激控制？为什么 CBT-I 建议只在困倦时上床？"),
        ("personalized_needs_ask", "虚构测试：一名成人每晚23:00上床，通常60分钟才能睡着；他应该提前上床吗？"),
        ("personalized_sufficient", "虚构测试：一名成人每晚23:00上床，通常60分钟才能睡着，早上07:00起床；他应该提前上床吗？"),
        ("cause_assessment", "虚构测试：一名成人最近两周每晚23:30上床、约90分钟入睡、早上07:00起床，下午会喝两杯咖啡。哪些可改变因素可能影响他的入睡困难？"),
        ("data_analysis", "虚构测试：请分析这名虚构用户最近7天的睡眠日记。"),
    ]

    def request(case: str, message: str) -> dict[str, Any]:
        observations.clear()
        prior = deepcopy(service.sessions.get(case))
        response = app.test_client().post("/api/chat", json={"session_id": case, "message": message})
        result = response.get_json()
        updated = deepcopy(service.sessions.get(case))
        trace = {
            "mode": "real_model",
            "fictional_test_data": True,
            "case": case,
            "raw_user_input": message,
            "http_status": response.status_code,
            "response": result,
            "prior": prior,
            "observations": observations,
            "updated": updated,
        }
        with (output / "http-traces.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(trace, ensure_ascii=False, default=_encode) + "\n")
        print(json.dumps({"case": case, "http_status": response.status_code, "response": result},
                         ensure_ascii=False), flush=True)
        return result

    for case, message in cases:
        if case == "data_analysis":
            service.loop.diary_tool = SessionDiaryTool(fictional_diary)
            observe(service.loop.diary_tool, "read", "read_diary")
            service.sessions[case] = AdaptiveSession()
        request(case, message)


if __name__ == "__main__":
    main()
