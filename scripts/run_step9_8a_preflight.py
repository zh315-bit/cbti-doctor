"""One non-Benchmark production-route smoke check for Step 9.8a."""
from __future__ import annotations
import json
from pathlib import Path

from scripts.run_step9_7_integration import run_i1


def main():
    service, retrieval, diary, route_calls, assertions = run_i1()
    state = service.sessions["i1"].state
    payload = {
        "kind": "synthetic_non_benchmark_preflight",
        "route": "/api/chat",
        "result": "PASS",
        "assertions": assertions,
        "action_path": [item["action"] for item in state.action_history],
        "trace": route_calls,
        "lineage": {"goal_id": state.goal_id, "semantic_provenance": state.semantic_provenance,
                    "dependencies": state.dependencies_considered, "preconditions": state.preconditions_considered,
                    "lineage_events": state.lineage_events},
        "tool_counts": {"RETRIEVE": retrieval.calls, "READ_DIARY": diary.calls},
        "benchmark_case_used": False,
    }
    path = Path("evaluation/v1_2_2/step9_8a_preflight_trace.json")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"result": "PASS", "action_path": payload["action_path"]}, ensure_ascii=False))


if __name__ == "__main__": main()
