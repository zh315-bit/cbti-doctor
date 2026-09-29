"""Recover the Step 9.28 local real preflight without touching V4 cases."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import run_step9_28_v4_heldout as runner
from scripts.preflight_step9_12_local import _SmokeCaptureRecorder, _dns_ready, _https_ready, _import_ready, _lineage_validation, _model_probe

OUT = runner.FREEZE_DIR


def _write(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush(); os.fsync(stream.fileno())


def _contract_fields(ready: bool, accessed_for_evaluation: bool) -> dict:
    """Emit canonical and recovery aliases from the same two safety facts."""
    return {
        "ready_for_final_authorization": ready,
        "ready_for_v4_final_authorization": ready,
        "benchmark_v4_accessed_by_agent": accessed_for_evaluation,
        "benchmark_v4_accessed_for_evaluation": accessed_for_evaluation,
    }


def _synthetic_production_smoke(trace_path: Path) -> tuple[str, bool, dict]:
    """Exercise only a fixed synthetic input through the real production route."""
    try:
        from adaptive_agent.flask_app import _create_adaptive_chat_service, create_app
        from evaluation.recorder import serialize_state
        service, capture = _create_adaptive_chat_service(), _SmokeCaptureRecorder()
        service.recorder = capture
        app = create_app(service)
        session_id = "step9_28a_synthetic_preflight"
        started = perf_counter()
        response = app.test_client().post("/api/chat", json={
            "session_id": session_id,
            "message": "Please explain in general terms why a consistent wake time can support sleep routines.",
        })
        payload = response.get_json(silent=True) or {"http_body": response.get_data(as_text=True)[:4000]}
        state = service.sessions.get(session_id).state if session_id in service.sessions else None
        loop = capture.results[-1] if capture.results else None
        lineage = _lineage_validation(state, loop.state_history if loop else []) if state else {"ready": False}
        ok = bool(payload.get("assistant")) and bool(state and state.action_history) and lineage.get("ready") is True
        trace = {
            "trace_type": "STEP9_28A_SYNTHETIC_PRODUCTION_PREFLIGHT",
            "evaluation_id": runner.EVALUATION_ID,
            "contains_v4_case_input": False,
            "session_id": session_id,
            "http_status": response.status_code,
            "response": payload,
            "latency_ms": round((perf_counter() - started) * 1000, 2),
            "state": serialize_state(state) if state else None,
            "state_history": loop.state_history if loop else [],
            "lineage": lineage,
        }
        _write(trace_path, trace)
        return ("PASS" if ok else "FAIL"), bool(lineage.get("ready")), {"trace_path": str(trace_path.relative_to(runner.ROOT))}
    except Exception as error:
        return "FAIL", False, {"error_type": type(error).__name__}


def run() -> tuple[dict, Path]:
    frozen = runner.verify_frozen_identity()
    imports_ready, missing = _import_ready()
    credential = runner.model_configuration_match()
    dns = _dns_ready()
    https = _https_ready() if dns else False
    endpoint, model_name, latency, error = (
        _model_probe() if frozen["freeze_match"] and imports_ready and credential and dns and https
        else (False, None, None, "NOT_RUN")
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    trace_path = OUT / f"step9_28a_synthetic_trace_{stamp}_{uuid4().hex}.json"
    smoke, lineage, smoke_detail = (
        _synthetic_production_smoke(trace_path) if endpoint else ("NOT_RUN", False, {})
    )
    result = {
        "preflight_type": "LOCAL_REAL_PREFLIGHT_RECOVERY",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_id": runner.EVALUATION_ID,
        "frozen_hashes": frozen,
        "credential_present": bool(os.getenv("DEEPSEEK_API_KEY", "").strip()),
        "required_imports_ready": imports_ready,
        "missing_imports": missing,
        "dns_ready": dns,
        "https_ready": https,
        "model_endpoint_reachable": endpoint,
        "model_name": model_name,
        "probe_latency_ms": latency,
        "model_probe_error_type": error,
        "synthetic_production_smoke": smoke,
        "trace_lineage_ready": lineage,
        "synthetic_trace": smoke_detail,
        "v4_formal_attempt_created": False,
        "v4_case_executed": 0,
        "v4_score_generated": False,
    }
    ready = all((
        frozen["freeze_match"], imports_ready, credential, dns, https, endpoint,
        smoke == "PASS", lineage, not runner._prior_formal_attempt_exists(),
    ))
    result.update(_contract_fields(ready, accessed_for_evaluation=False))
    artifact = OUT / f"step9_28a_v4_local_preflight_{stamp}_{uuid4().hex}.json"
    _write(artifact, result)
    return result, artifact


if __name__ == "__main__":
    outcome, artifact_path = run()
    print(json.dumps({**outcome, "artifact": str(artifact_path.relative_to(runner.ROOT))}, ensure_ascii=False, sort_keys=True))
