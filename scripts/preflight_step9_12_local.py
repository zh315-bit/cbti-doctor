"""Local connectivity and production-smoke preflight for Step 9.12."""
from __future__ import annotations

import argparse
import importlib
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from scripts.run_step9_12_frozen_evaluation import EVALUATION_ID, verify_frozen_identity

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_DIR = ROOT / "evaluation" / "v1_2_3"


class _SmokeCaptureRecorder:
    """Keep the production loop result in memory for observer-only validation."""

    def __init__(self) -> None:
        self.results = []

    def record(self, _session_id, _initial_state, result, *_args) -> None:
        self.results.append(result)


def _first_id(items: list[dict], key: str) -> str | None:
    return next((item.get(key) for item in items if item.get(key)), None)


def _lineage_validation(state, state_history: list[dict]) -> dict:
    """Validate only IDs applicable to each real recorded action.

    The loop's final State is intentionally a current-state projection.  Decision
    snapshots retain candidate and precondition observability for earlier
    revisions, so this observer reconstructs links from those real snapshots.
    """
    decisions = [snapshot for snapshot in state_history if snapshot.get("event") == "DECISION"]
    actions = list(state.action_history)
    lineage_events = list(state.lineage_events)
    semantic_id = _first_id(state.semantic_provenance, "semantic_id")
    dependency_ids = {
        item.get("dependency_id")
        for snapshot in state_history
        for item in snapshot.get("dependencies_considered", [])
        if item.get("dependency_id")
    }
    decision_by_candidate = {
        snapshot.get("chosen_action", {}).get("candidate_id"): snapshot
        for snapshot in decisions
        if snapshot.get("chosen_action", {}).get("candidate_id")
    }
    action_records = []
    missing = []
    for action in actions:
        candidate_id = action.get("selected_candidate_id")
        decision = decision_by_candidate.get(candidate_id)
        chosen = (decision or {}).get("chosen_action", {})
        origin = chosen.get("origin")
        precondition_id = chosen.get("source_precondition_id")
        source_dependency_id = chosen.get("source_dependency_id")
        tool_events = [
            event for event in lineage_events
            if event.get("source_action_id") == action.get("action_id")
        ]
        is_tool = action.get("action") in {"RETRIEVE", "READ_DIARY"}
        record = {
            "action_id": action.get("action_id"),
            "action": action.get("action"),
            "origin": origin,
            "candidate_id": candidate_id,
            "candidate_history_found": decision is not None,
            "precondition_id": precondition_id,
            "source_dependency_id": source_dependency_id,
            "tool_result_ids": [event.get("tool_result_id") for event in tool_events if event.get("tool_result_id")],
            "state_update_ids": [event.get("state_update_id") for event in tool_events if event.get("state_update_id")],
            "lineage_shape": (
                "PRECONDITION_FORCED_ACTION" if origin == "HARD_PRECONDITION"
                else "POLICY_SELECTED_ACTION"
            ),
        }
        if not record["action_id"]:
            missing.append({"action": action.get("action"), "missing": "action_id"})
        if not candidate_id or decision is None:
            missing.append({"action_id": action.get("action_id"), "missing": "candidate_id"})
        if source_dependency_id and source_dependency_id not in dependency_ids:
            missing.append({"action_id": action.get("action_id"), "missing": "dependency_lineage"})
        if origin == "HARD_PRECONDITION" and not precondition_id:
            missing.append({"action_id": action.get("action_id"), "missing": "precondition_id"})
        if is_tool and not record["tool_result_ids"]:
            missing.append({"action_id": action.get("action_id"), "missing": "tool_result_id"})
        if is_tool and not record["state_update_ids"]:
            missing.append({"action_id": action.get("action_id"), "missing": "state_update_id"})
        action_records.append(record)

    root_missing = []
    if not state.goal_id: root_missing.append("goal_id")
    if not semantic_id: root_missing.append("semantic_id")
    if not dependency_ids: root_missing.append("dependency_id")
    return {
        "ready": not root_missing and not missing and bool(action_records),
        "root_ids": {
            "goal_id": state.goal_id,
            "semantic_id": semantic_id,
            "dependency_ids": sorted(dependency_ids),
        },
        "actions": action_records,
        "missing_required_lineage": missing,
        "missing_root_lineage": root_missing,
        "candidate_lineage_missing": any(item.get("missing") == "candidate_id" for item in missing),
        "fake_lineage_ids_created": False,
    }


def _import_ready() -> tuple[bool, list[str]]:
    missing = []
    for name in ("flask", "flask_cors", "langchain_openai", "httpx"):
        try: importlib.import_module(name)
        except Exception: missing.append(name)
    return not missing, missing


def _dns_ready() -> bool:
    try:
        socket.getaddrinfo("api.deepseek.com", 443, type=socket.SOCK_STREAM)
        return True
    except OSError:
        return False


def _https_ready() -> bool:
    try:
        import httpx
        with httpx.Client(timeout=10) as client:
            response = client.get("https://api.deepseek.com")
        return response.status_code < 500
    except Exception:
        return False


def _model_probe() -> tuple[bool, str | None, float | None, str | None]:
    try:
        from model_config import create_chat_model
        model = create_chat_model()
        started = perf_counter(); model.invoke("Reply with exactly OK.")
        return True, getattr(model, "model_name", None), round((perf_counter() - started) * 1000, 2), None
    except Exception as error:
        return False, None, None, type(error).__name__


def _smoke() -> tuple[str, dict]:
    try:
        from adaptive_agent.flask_app import _create_adaptive_chat_service, create_app
        service = _create_adaptive_chat_service(); app = create_app(service)
        capture = _SmokeCaptureRecorder()
        service.recorder = capture
        payload = app.test_client().post("/api/chat", json={
            "session_id": "step9_12_synthetic_smoke",
            "message": "Please explain in general terms why a consistent wake time can support sleep routines.",
        }).get_json() or {}
        state = service.sessions["step9_12_synthetic_smoke"].state
        result = capture.results[-1] if capture.results else None
        lineage = _lineage_validation(state, result.state_history if result else [])
        ok = bool(payload.get("assistant")) and bool(state.action_history) and lineage["ready"]
        return "PASS" if ok else "FAIL", {
            "state_created": bool(state.goal_id),
            "action_recorded": bool(state.action_history),
            "lineage_created": lineage["ready"],
            "answer_returned": bool(payload.get("assistant")),
            "lineage": lineage,
        }
    except Exception as error:
        return "FAIL", {"error_type": type(error).__name__}


def _capture_local_result(result: dict, directory: Path | None = None) -> Path:
    """Persist an actual local preflight, including failed checks, without secrets."""
    timestamp = datetime.now(timezone.utc)
    frozen = result["frozen_identity"]
    artifact = {
        "preflight_type": "LOCAL_REAL_PREFLIGHT",
        "timestamp": timestamp.isoformat(),
        "evaluation_id": result["evaluation_id"],
        "frozen_hashes": {
            "agent_aggregate": frozen.get("agent_aggregate_hash"),
            "harness_aggregate": frozen.get("harness_aggregate_hash"),
            "benchmark_sha256": frozen.get("benchmark_hash"),
            "scoring_aggregate": frozen.get("scoring_aggregate_hash"),
            "scoring_sha256": frozen.get("scoring_hash"),
        },
        "frozen_identity_match": frozen.get("frozen_identity_match", False),
        "credential_present": result["credential_present"],
        "dns_ready": result["dns_ready"],
        "https_ready": result["https_ready"],
        "model_endpoint_reachable": result["model_endpoint_reachable"],
        "synthetic_production_smoke": result["synthetic_production_smoke"],
        "trace_lineage_ready": result["trace_lineage_ready"],
        "ready_for_authorized_run": result["ready_for_authorized_run"],
        "benchmark_v2_executed": result["benchmark_v2_executed"],
        "benchmark_v3_accessed": result["benchmark_v3_accessed"],
    }
    directory = directory if directory is not None else CAPTURE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"step9_13a_local_real_preflight_{timestamp.strftime('%Y%m%dT%H%M%SZ')}_{uuid4().hex}.json"
    with path.open("x", encoding="utf-8") as stream:
        json.dump(artifact, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Step 9.12 local real-model preflight")
    parser.add_argument("--capture", action="store_true", help="write an append-only local preflight artifact")
    args = parser.parse_args(argv)
    frozen = verify_frozen_identity()
    imports_ok, missing_imports = _import_ready()
    credential = bool(os.getenv("DEEPSEEK_API_KEY", "").strip())
    # DNS/HTTPS are independent diagnostics. Credential absence blocks only the
    # authenticated model probe, not the network classification.
    dns = _dns_ready()
    https = _https_ready() if dns else False
    if credential and dns and https:
        model_ok, model_name, latency, model_error = _model_probe()
    else:
        model_ok, model_name, latency, model_error = False, None, None, "NOT_RUN"
    smoke, smoke_detail = _smoke() if model_ok else ("NOT_RUN", {})
    result = {"evaluation_id": EVALUATION_ID, "frozen_identity": frozen, "python_version": sys.version.split()[0],
              "virtual_environment": sys.prefix != getattr(sys, "base_prefix", sys.prefix), "required_imports_ready": imports_ok,
              "missing_imports": missing_imports, "credential_present": credential, "dns_ready": dns, "https_ready": https,
              "model_endpoint_reachable": model_ok, "model_name": model_name, "probe_latency_ms": latency,
              "model_probe_error_type": model_error, "synthetic_production_smoke": smoke,
              "trace_lineage_ready": smoke_detail.get("lineage_created", False), "smoke_detail": smoke_detail,
              "token_usage_status": "NOT_MEASURED", "benchmark_v2_executed": False, "benchmark_v3_accessed": False}
    result["ready_for_authorized_run"] = bool(frozen.get("frozen_identity_match") and imports_ok and credential and dns and https and model_ok and smoke == "PASS" and result["trace_lineage_ready"])
    if args.capture:
        result["local_preflight_artifact"] = str(_capture_local_result(result))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
