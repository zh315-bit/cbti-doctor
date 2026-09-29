"""Prepared one-shot V3 runner. Import and local preflight never open V3."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
FREEZE_DIR = ROOT / "evaluation" / "v1_2_3"
FINAL_MANIFEST = FREEZE_DIR / "step9_19_final_candidate_manifest.json"
RUNNER_FREEZE = FREEZE_DIR / "step9_20a_v3_runner_freeze.json"
OUT_ROOT = ROOT / "evaluation" / "v3_runs"
EVALUATION_ID = "heldout-v3-step9_20-20260923-01"
FINAL_MANIFEST_SHA = "21e325516f955986497b69e18eebca1d0a0658a24c4293fe75853dd464c901f5"
METRICS_SHA = "a44f8959b1683775b3f8f956f7f990572faa5c204ae5da3fa1201245c56755ab"
RULES_SHA = "8333e4f7a42258a740d938e0315df00ea38ce15a9b6726ac43d5d9cecf925d6f"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def model_configuration_match() -> bool:
    """Check the frozen non-secret DeepSeek configuration, including key presence."""
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    return bool(os.getenv("DEEPSEEK_API_KEY", "").strip()) and (
        os.getenv("DEEPSEEK_MODEL", "deepseek-flash") == "deepseek-flash"
        and os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/") == "https://api.deepseek.com"
    )


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"invalid JSON object: {path.name}")
    return value


def verify_frozen_identity() -> dict:
    """Check only Step 9.19 inputs and this runner; never inspect V3."""
    from scripts.run_step9_12_frozen_evaluation import _actual_hash, _aggregate

    manifest = _json(FINAL_MANIFEST)
    agent_freeze = _json(ROOT / manifest["candidate_freeze_source"])
    harness_freeze = _json(ROOT / manifest["component_hashes"]["evaluation_harness"]["freeze"])
    scoring_freeze = _json(ROOT / manifest["component_hashes"]["scoring_specification"]["source_freeze"])
    runner_freeze = _json(RUNNER_FREEZE)

    def matches(rows: list[list[str]], expected: str) -> bool:
        return _aggregate(rows) == expected and all(_actual_hash(path, digest) == digest for path, digest in rows)

    agent_hash = manifest["agent_aggregate_sha256"]
    harness_hash = manifest["component_hashes"]["evaluation_harness"]["sha256"]
    scoring_hash = manifest["component_hashes"]["scoring_specification"]["sha256"]
    result = {
        "evaluation_id": EVALUATION_ID,
        "final_candidate_manifest_sha256": sha256(FINAL_MANIFEST),
        "agent_hash": agent_hash,
        "harness_hash": harness_hash,
        "scoring_hash": scoring_hash,
        "metric_registry_sha256": sha256(FREEZE_DIR / "step9_19_metric_registry.json"),
        "one_shot_rules_sha256": sha256(FREEZE_DIR / "step9_19_one_shot_rules.md"),
        "runner_sha256": sha256(Path(__file__)),
        "agent_match": matches(agent_freeze["agent_behavior_files"], agent_hash),
        "harness_match": matches(harness_freeze["new_harness_files"], harness_hash),
        "scoring_match": matches(scoring_freeze["scoring_files"], scoring_hash),
    }
    result["freeze_match"] = all((
        result["final_candidate_manifest_sha256"] == FINAL_MANIFEST_SHA,
        sha256(ROOT / manifest["candidate_freeze_source"]) == manifest["candidate_freeze_source_sha256"],
        sha256(ROOT / manifest["component_hashes"]["evaluation_harness"]["freeze"])
        == manifest["component_hashes"]["evaluation_harness"]["freeze_sha256"],
        result["agent_match"], result["harness_match"], result["scoring_match"],
        result["metric_registry_sha256"] == METRICS_SHA,
        result["one_shot_rules_sha256"] == RULES_SHA,
        result["runner_sha256"] == runner_freeze.get("runner_sha256"),
        runner_freeze.get("parent_harness_aggregate_sha256") == harness_hash,
        runner_freeze.get("final_candidate_manifest_sha256") == FINAL_MANIFEST_SHA,
        manifest.get("candidate_logic_audit", {}).get("case_specific_logic_present") is False,
    ))
    return result


def local_preflight(capture: bool = False) -> dict:
    """Synthetic provider and production smoke; no authorization or case access."""
    from scripts.preflight_step9_12_local import (
        _dns_ready, _https_ready, _import_ready, _model_probe, _smoke,
    )

    frozen = verify_frozen_identity()
    imports_ready, missing_imports = _import_ready()
    configuration_ready = model_configuration_match()
    credential = bool(os.getenv("DEEPSEEK_API_KEY", "").strip())
    nonsecret_configuration_match = (
        os.getenv("DEEPSEEK_MODEL", "deepseek-flash") == "deepseek-flash"
        and os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/") == "https://api.deepseek.com"
    )
    dns = _dns_ready()
    https = _https_ready() if dns else False
    model_ok, model_name, latency, error_type = (
        _model_probe() if frozen["freeze_match"] and configuration_ready and dns and https and imports_ready
        else (False, None, None, "NOT_RUN")
    )
    smoke, detail = _smoke() if model_ok else ("NOT_RUN", {})
    result = {
        "preflight_type": "LOCAL_REAL_PREFLIGHT", "evaluation_id": EVALUATION_ID,
        "timestamp_utc": utc_now(), "frozen_hashes": frozen,
        "credential_present": credential, "required_imports_ready": imports_ready,
        "missing_imports": missing_imports, "dns_ready": dns, "https_ready": https,
        "model_configuration_match": nonsecret_configuration_match,
        "model_endpoint_reachable": model_ok, "model_name": model_name,
        "probe_latency_ms": latency, "model_probe_error_type": error_type,
        "synthetic_production_smoke": smoke,
        "trace_lineage_ready": detail.get("lineage_created", False),
        "benchmark_v3_accessed": False,
    }
    result["ready_for_authorization"] = all((
        frozen["freeze_match"], imports_ready, configuration_ready,
        dns, https, model_ok,
        smoke == "PASS", result["trace_lineage_ready"],
    ))
    if capture:
        target = FREEZE_DIR / f"step9_20a_local_preflight_{uuid4().hex}.json"
        with target.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
        result["artifact"] = str(target.relative_to(ROOT))
    return result


def validate_authorization(auth_path: Path, evaluation_id: str, authorization_id: str,
                           attempt_id: str) -> tuple[dict, dict]:
    """Validate an issued authorization before any V3 filesystem operation."""
    if evaluation_id != EVALUATION_ID or not all(SAFE_ID.fullmatch(x) for x in (authorization_id, attempt_id)):
        raise RuntimeError("invalid or mismatched evaluation/authorization/attempt identity")
    frozen = verify_frozen_identity()
    if not frozen["freeze_match"]:
        raise RuntimeError("frozen identity mismatch")
    if not model_configuration_match():
        raise RuntimeError("frozen runtime model configuration or credential is unavailable")
    auth = _json(auth_path)
    if not all((
        auth.get("status") == "ISSUED_NOT_EXECUTED",
        auth.get("evaluation_id") == evaluation_id,
        auth.get("authorization_id") == authorization_id,
        auth.get("attempt_id") == attempt_id,
        auth.get("final_candidate_manifest_sha256") == FINAL_MANIFEST_SHA,
        auth.get("agent_sha256") == frozen["agent_hash"],
        auth.get("harness_sha256") == frozen["harness_hash"],
        auth.get("scoring_sha256") == frozen["scoring_hash"],
        auth.get("metric_registry_sha256") == METRICS_SHA,
        auth.get("one_shot_rules_sha256") == RULES_SHA,
        auth.get("runner_sha256") == frozen["runner_sha256"],
        isinstance(auth.get("benchmark_path"), str),
        isinstance(auth.get("preflight_artifact"), str),
        isinstance(auth.get("preflight_artifact_sha256"), str),
    )):
        raise RuntimeError("authorization is not issued or its frozen binding is invalid")
    benchmark_path = Path(auth["benchmark_path"])
    if (benchmark_path.is_absolute() or ".." in benchmark_path.parts
            or benchmark_path.parts[:2] != ("evaluation", "benchmarks")):
        raise RuntimeError("authorized benchmark path is outside the sealed benchmark directory")
    preflight_path = ROOT / auth["preflight_artifact"]
    preflight = _json(preflight_path)
    if not all((
        sha256(preflight_path) == auth["preflight_artifact_sha256"],
        preflight.get("preflight_type") == "LOCAL_REAL_PREFLIGHT",
        preflight.get("evaluation_id") == EVALUATION_ID,
        preflight.get("ready_for_authorization") is True,
        preflight.get("model_configuration_match") is True,
        preflight.get("benchmark_v3_accessed") is False,
        preflight.get("frozen_hashes", {}).get("runner_sha256") == frozen["runner_sha256"],
        preflight.get("frozen_hashes", {}).get("agent_hash") == frozen["agent_hash"],
        preflight.get("frozen_hashes", {}).get("harness_hash") == frozen["harness_hash"],
        preflight.get("frozen_hashes", {}).get("scoring_hash") == frozen["scoring_hash"],
    )):
        raise RuntimeError("local real preflight is missing, stale, or mismatched")
    return auth, frozen


def _append(stream, event: dict) -> None:
    stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True, default=str) + "\n")
    stream.flush()
    os.fsync(stream.fileno())


class _CaptureRecorder:
    def __init__(self) -> None:
        self.results: list = []

    def record(self, _session_id, _initial_state, result, *_args) -> None:
        self.results.append(result)


def _case_result(case: dict, service, app, capture: _CaptureRecorder, max_turns: int) -> tuple[dict, dict]:
    from adaptive_agent.service import AdaptiveSession
    from adaptive_agent.tools import SessionDiaryTool
    from evaluation.recorder import serialize_state
    from scripts.preflight_step9_12_local import _lineage_validation
    from scripts.run_step8_9_v1_2_1 import diary_payload, follow_up

    case_id = case["case_id"]
    session = AdaptiveSession()
    for field, value in case.get("initial_session_facts", {}).items():
        session.state.facts[field] = deepcopy(value)
        session.state.fact_sources[field] = {"source": "benchmark_initial_session"}
    service.sessions[case_id] = session
    service.loop.diary_tool = SessionDiaryTool(diary_payload(case))
    messages = [case["user_query"]]
    turns = []
    start = perf_counter()
    for turn_number in range(1, max_turns + 1):
        prior = len(capture.results)
        turn_start = perf_counter()
        response = app.test_client().post("/api/chat", json={"session_id": case_id, "message": messages[-1]})
        payload = response.get_json(silent=True) or {"http_body": response.get_data(as_text=True)[:4000]}
        if len(capture.results) != prior + 1:
            raise RuntimeError("production recorder did not capture exactly one loop result")
        loop_result = capture.results[-1]
        state = service.sessions[case_id].state
        turns.append({
            "turn": turn_number, "user_turn": messages[-1], "http_status": response.status_code,
            "response": payload, "latency_ms": round((perf_counter() - turn_start) * 1000, 2),
            "state": serialize_state(state), "state_history": loop_result.state_history,
            "lineage": _lineage_validation(state, loop_result.state_history),
        })
        if response.status_code != 200 or payload.get("status") != "ASK":
            break
        target = state.action_history[-1].get("target") if state.action_history else None
        messages.append(follow_up(target, case.get("follow_up_facts", {})))
    state = service.sessions[case_id].state
    path = [entry["action"] for entry in state.action_history]
    raw = {
        "case_id": case_id, "evaluation_id": EVALUATION_ID, "user_turns": messages[:len(turns)],
        "turns": turns, "action_path": path, "final_state": serialize_state(state),
        "final_answer": turns[-1]["response"].get("assistant", ""),
        "final_status": turns[-1]["response"].get("status", "HTTP_ERROR"),
        "latency_ms": round((perf_counter() - start) * 1000, 2),
        "token_usage": "NOT_MEASURED",
    }
    result = {
        "case_id": case_id, "evaluation_id": EVALUATION_ID, "task_type": case["task_type"],
        "action_path": path, "ASK_count": path.count("ASK"),
        "RETRIEVE_count": path.count("RETRIEVE"), "READ_DIARY_count": path.count("READ_DIARY"),
        "turn_count": len(turns), "step_count": sum(item["response"].get("steps", 0) for item in turns),
        "tool_calls": [action for action in path if action in {"RETRIEVE", "READ_DIARY"}],
        "latency_ms": raw["latency_ms"], "token_usage": "NOT_MEASURED",
        "final_status": raw["final_status"], "answer": raw["final_answer"],
        "lineage_ready": all(item["lineage"]["ready"] for item in turns),
        "score_status": "PENDING_FROZEN_RUBRIC_REVIEW", "dimension_scores": None,
        "critical_failure": "PENDING_REVIEW", "failure_classification": "PENDING_REVIEW",
    }
    return raw, result


def run(evaluation_id: str, authorization_id: str, attempt_id: str, auth_path: Path) -> None:
    auth, frozen = validate_authorization(auth_path, evaluation_id, authorization_id, attempt_id)
    out = OUT_ROOT / evaluation_id
    out.mkdir(parents=True, exist_ok=True)
    ledger_path = out / "attempts.jsonl"
    try:
        fd = os.open(ledger_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise RuntimeError("one-shot attempt ledger already exists") from error
    completed = 0
    started = 0
    stage = "INITIALIZATION"
    with os.fdopen(fd, "w", encoding="utf-8") as ledger:
        fcntl.flock(ledger.fileno(), fcntl.LOCK_EX)
        base_event = {
            "evaluation_id": evaluation_id, "authorization_id": authorization_id,
            "attempt_id": attempt_id, "agent_hash": frozen["agent_hash"],
            "harness_hash": frozen["harness_hash"], "runner_hash": frozen["runner_sha256"],
            "scoring_hash": frozen["scoring_hash"], "metric_registry_sha256": METRICS_SHA,
        }

        def event(status: str, **details) -> None:
            _append(ledger, {**base_event, "timestamp_utc": utc_now(), "status": status,
                             "cases_started": started, "cases_completed": completed, **details})

        event("PREPARED")
        try:
            from adaptive_agent.flask_app import _create_adaptive_chat_service, create_app
            service = _create_adaptive_chat_service()
            capture = _CaptureRecorder()
            service.recorder = capture
            app = create_app(service)
            app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=True)
            if not verify_frozen_identity()["freeze_match"] or not model_configuration_match():
                raise RuntimeError("frozen identity changed before V3 access")

            # This is the first V3 filesystem operation; the access record is durable first.
            benchmark_path = ROOT / auth["benchmark_path"]
            stage = "FIRST_V3_ACCESS"
            event("V3_FIRST_ACCESS", evaluator=auth.get("authorized_by"),
                  purpose="one_shot_heldout_evaluation", source_identity=auth["benchmark_path"])
            source = benchmark_path.read_bytes()
            benchmark_hash = hashlib.sha256(source).hexdigest()
            if auth.get("benchmark_sha256") and auth["benchmark_sha256"] != benchmark_hash:
                raise RuntimeError("authorized V3 source hash mismatch")
            event("V3_SOURCE_HASHED", benchmark_sha256=benchmark_hash)

            import yaml
            spec = yaml.safe_load(source)
            if not isinstance(spec, dict) or not isinstance(spec.get("cases"), list) or not spec["cases"]:
                raise RuntimeError("invalid sealed benchmark structure")
            cases = spec["cases"]
            ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
            if len(ids) != len(cases) or len(set(ids)) != len(ids) or not all(ids):
                raise RuntimeError("invalid or duplicate sealed case identifiers")
            for case in cases:
                if not all(key in case for key in ("user_query", "task_type", "diary_facts", "follow_up_facts")):
                    raise RuntimeError("sealed case does not satisfy the frozen fixture contract")

            raw_path = out / f"{attempt_id}_raw_traces.jsonl"
            results_path = out / f"{attempt_id}_case_results.jsonl"
            with raw_path.open("x", encoding="utf-8") as raw_stream, results_path.open("x", encoding="utf-8") as result_stream:
                for case in cases:
                    if not verify_frozen_identity()["freeze_match"] or not model_configuration_match():
                        raise RuntimeError("frozen identity changed during execution")
                    started += 1
                    stage = "AGENT_CASE"
                    event("STARTED", case_id=case["case_id"])
                    raw, result = _case_result(case, service, app, capture, max_turns=6)
                    _append(raw_stream, raw)
                    _append(result_stream, result)
                    completed += 1
                    event("CASE_COMPLETED", case_id=case["case_id"])
            stage = "POST_RUN_FREEZE"
            if not verify_frozen_identity()["freeze_match"] or not model_configuration_match():
                raise RuntimeError("frozen identity changed after execution")
            event("COMPLETED", benchmark_sha256=benchmark_hash, valid_raw_results=completed == len(cases),
                  scoring_status="PENDING_FROZEN_RUBRIC_REVIEW")
        except BaseException as error:
            kind = "MODEL_API_FAILURE" if type(error).__module__.startswith(("openai", "httpx")) else (
                "AGENT_FAILURE" if stage == "AGENT_CASE" else
                "ENVIRONMENT_FAILURE" if stage == "INITIALIZATION" else "HARNESS_FAILURE"
            )
            event("FAILED_AFTER_PARTIAL_EXECUTION" if started else "FAILED_BEFORE_FIRST_CASE",
                  failure_classification=kind, failure_stage=stage, failure_type=type(error).__name__)
            raise


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Step 9.20 V3 one-shot held-out evaluation")
    parser.add_argument("--evaluation-id", required=True)
    parser.add_argument("--authorization-id")
    parser.add_argument("--attempt-id")
    parser.add_argument("--authorization-file", type=Path)
    parser.add_argument("--local-preflight", action="store_true")
    parser.add_argument("--capture", action="store_true")
    args = parser.parse_args(argv)
    if args.evaluation_id != EVALUATION_ID:
        parser.error("evaluation ID does not match the prepared V3 identity")
    if args.local_preflight:
        print(json.dumps(local_preflight(capture=args.capture), ensure_ascii=False, sort_keys=True))
        return
    if args.capture or not all((args.authorization_id, args.attempt_id, args.authorization_file)):
        parser.error("formal execution requires authorization ID, attempt ID, and authorization file")
    run(args.evaluation_id, args.authorization_id, args.attempt_id, args.authorization_file)


if __name__ == "__main__":
    main()
