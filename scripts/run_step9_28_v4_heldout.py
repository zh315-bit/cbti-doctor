"""Step 9.28 V4 held-out runner.

Import and ``--local-preflight`` are intentionally case-inert: they may hash
and schema-check the sealed dataset, but never create an attempt, instantiate a
case session, or send V4 input to ``/api/chat``.  ``run`` is deliberately
unreachable until a separately issued authorization replaces the template.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
FREEZE_DIR = ROOT / "evaluation" / "v1_2_3"
MANIFEST = ROOT / "evaluation" / "benchmarks" / "benchmark_v4_manifest.json"
CASES = ROOT / "evaluation" / "benchmarks" / "benchmark_v4_cases.yaml"
FINAL_FREEZE = FREEZE_DIR / "step9_26_final_candidate_freeze.json"
HARNESS_FREEZE = FREEZE_DIR / "step9_13a_harness_freeze.json"
REGISTRY = FREEZE_DIR / "step9_26_v4_metric_registry.json"
RULES = FREEZE_DIR / "step9_26_v4_one_shot_rules.md"
RUNNER_FREEZE = FREEZE_DIR / "step9_29a_v4_runner_freeze.json"
AUTH_TEMPLATE = FREEZE_DIR / "step9_29a_v4_authorization_template.json"
OUT_ROOT = ROOT / "evaluation" / "v4_runs"
EVALUATION_ID = "heldout-v4-step9_28-20260925-01"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"invalid JSON object: {path.name}")
    return value


def _aggregate(rows: list[list[str]]) -> str:
    payload = "".join(f"{path}\t{digest}\n" for path, digest in sorted(rows))
    return hashlib.sha256(payload.encode()).hexdigest()


def _actual_hash(path: str, expected: str) -> str:
    from scripts.run_step9_12_frozen_evaluation import _actual_hash as historical_hash
    return historical_hash(path, expected)


def model_configuration_match() -> bool:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    return bool(os.getenv("DEEPSEEK_API_KEY", "").strip()) and (
        os.getenv("DEEPSEEK_MODEL", "deepseek-flash") == "deepseek-flash"
        and os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/") == "https://api.deepseek.com"
    )


def schema_compatible() -> bool:
    """Generic V4 schema check only; no service/model is constructed here."""
    import yaml
    spec = yaml.safe_load(CASES.read_bytes())
    cases = spec.get("cases") if isinstance(spec, dict) else None
    if not isinstance(cases, list) or len(cases) != 40:
        return False
    ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
    required = {"case_id", "user_query", "task_type", "diary_facts", "follow_up_facts"}
    return (len(ids) == len(cases) and len(set(ids)) == len(ids) and all(ids)
            and all(required.issubset(case) for case in cases if isinstance(case, dict)))


def verify_frozen_identity() -> dict:
    """Verify every V4 binding, including sealed dataset bytes; fail closed."""
    final, harness, manifest, runner = (_json(FINAL_FREEZE), _json(HARNESS_FREEZE),
                                        _json(MANIFEST), _json(RUNNER_FREEZE))
    agent_rows = final["agent_behavior_files"]
    harness_rows = harness["new_harness_files"]
    agent_hash = final["agent_aggregate_sha256"]
    harness_hash = final["harness"]["aggregate_sha256"]
    scoring_hash = final["scoring"]["aggregate_sha256"]
    registry_hash, rules_hash = sha256(REGISTRY), sha256(RULES)
    agent_match = _aggregate(agent_rows) == agent_hash and all(_actual_hash(p, d) == d for p, d in agent_rows)
    harness_match = (_aggregate(harness_rows) == harness_hash
                     and all(_actual_hash(p, d) == d for p, d in harness_rows))
    scoring_match = sha256(ROOT / final["scoring"]["rubric_path"]) == final["scoring"]["rubric_sha256"]
    benchmark_match = sha256(CASES) == manifest["benchmark_sha256"]
    manifest_match = all((manifest["status"] == "SEALED_NOT_EVALUATED", manifest["immutable"] is True,
                          manifest["case_count"] == 40, manifest["schema_version"] == "v2-compatible-1",
                          sha256(FINAL_FREEZE) == manifest["frozen_identity_check"]["final_candidate_manifest_sha256"],
                          manifest["frozen_identity_check"]["agent_aggregate_sha256"] == agent_hash,
                          manifest["frozen_identity_check"]["harness_aggregate_sha256"] == harness_hash,
                          manifest["frozen_identity_check"]["scoring_aggregate_sha256"] == scoring_hash,
                          manifest["frozen_identity_check"]["metric_registry_sha256"] == registry_hash,
                          manifest["frozen_identity_check"]["one_shot_rules_sha256"] == rules_hash))
    result = {
        "evaluation_id": EVALUATION_ID, "agent_hash": agent_hash, "harness_hash": harness_hash,
        "scoring_hash": scoring_hash, "metric_registry_sha256": registry_hash,
        "one_shot_rules_sha256": rules_hash, "benchmark_v4_sha256": sha256(CASES),
        "runner_sha256": sha256(Path(__file__)), "current_agent_matches_final_freeze": agent_match,
        "harness_match": harness_match, "scoring_match": scoring_match,
        "metric_registry_match": registry_hash == final["preregistered_metric_registry"]["sha256"],
        "one_shot_rules_match": rules_hash == final["one_shot_rules"]["sha256"],
        "benchmark_v4_sha256_match": benchmark_match, "manifest_match": manifest_match,
        "case_specific_agent_logic_found": manifest["static_audit"]["case_specific_agent_logic_found"],
    }
    result["runner_freeze_match"] = all((runner.get("runner_sha256") == result["runner_sha256"],
        runner.get("final_candidate_manifest_sha256") == sha256(FINAL_FREEZE),
        runner.get("benchmark_manifest_sha256") == sha256(MANIFEST),
        runner.get("benchmark_v4_sha256") == result["benchmark_v4_sha256"]))
    result["freeze_match"] = all((agent_match, harness_match, scoring_match, result["metric_registry_match"],
        result["one_shot_rules_match"], benchmark_match, manifest_match, result["runner_freeze_match"],
        result["case_specific_agent_logic_found"] is False))
    return result


def _prior_formal_attempt_exists() -> bool:
    ledger = OUT_ROOT / EVALUATION_ID / "attempts.jsonl"
    return ledger.exists() and bool(ledger.read_text(encoding="utf-8").strip())


def _contract_bool(preflight: dict, canonical: str, alias: str) -> bool | None:
    """Accept either spelling, but reject missing, non-boolean, or conflicting state."""
    values = [preflight[key] for key in (canonical, alias) if key in preflight]
    if not values or any(type(value) is not bool for value in values) or len(set(values)) != 1:
        return None
    return values[0]


def preflight_contract_valid(preflight: dict) -> bool:
    """Fail closed on incomplete or contradictory preflight readiness/access state."""
    return (_contract_bool(preflight, "ready_for_final_authorization", "ready_for_v4_final_authorization") is True
            and _contract_bool(preflight, "benchmark_v4_accessed_by_agent", "benchmark_v4_accessed_for_evaluation") is False)


def local_preflight() -> dict:
    """Perform allowed network/synthetic checks without V4 Agent execution."""
    from scripts.preflight_step9_12_local import _dns_ready, _https_ready, _import_ready, _model_probe, _smoke
    frozen = verify_frozen_identity()
    imports_ready, missing = _import_ready()
    config_ready = model_configuration_match()
    dns, https = _dns_ready(), False
    if dns:
        https = _https_ready()
    model_ok, model_name, latency, error = ((*_model_probe(),) if frozen["freeze_match"] and config_ready and dns and https and imports_ready
                                             else (False, None, None, "NOT_RUN"))
    smoke, detail = _smoke() if model_ok else ("NOT_RUN", {})
    result = {
        "preflight_type": "LOCAL_REAL_PREFLIGHT", "evaluation_id": EVALUATION_ID, "timestamp_utc": utc_now(),
        "frozen_hashes": frozen, "credential_present": bool(os.getenv("DEEPSEEK_API_KEY", "").strip()),
        "required_imports_ready": imports_ready, "missing_imports": missing, "dns_ready": dns, "https_ready": https,
        "model_endpoint_reachable": model_ok, "model_name": model_name, "probe_latency_ms": latency,
        "model_probe_error_type": error, "synthetic_production_smoke": smoke,
        "trace_lineage_ready": detail.get("lineage_created", False), "schema_compatible": schema_compatible(),
        "benchmark_v4_accessed_by_agent": False, "v4_case_executed": 0, "v4_score_generated": False,
        "prior_v4_formal_attempt_exists": _prior_formal_attempt_exists(),
    }
    result["ready_for_final_authorization"] = all((frozen["freeze_match"], imports_ready, config_ready, dns, https,
        model_ok, smoke == "PASS", result["trace_lineage_ready"], result["schema_compatible"],
        not result["prior_v4_formal_attempt_exists"]))
    return result


def _append(stream, event: dict) -> None:
    stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True, default=str) + "\n")
    stream.flush(); os.fsync(stream.fileno())


class _CaptureRecorder:
    def __init__(self) -> None: self.results: list = []
    def record(self, _session_id, _initial_state, result, *_args) -> None: self.results.append(result)


def _case_result(case: dict, service, app, capture: _CaptureRecorder, max_turns: int = 6) -> tuple[dict, dict]:
    """The production-only per-case path; no oracle or expected-action input."""
    from adaptive_agent.service import AdaptiveSession
    from adaptive_agent.tools import SessionDiaryTool
    from evaluation.recorder import serialize_state
    from scripts.preflight_step9_12_local import _lineage_validation
    from scripts.run_step8_9_v1_2_1 import diary_payload, follow_up
    session, case_id = AdaptiveSession(), case["case_id"]
    for field, value in case.get("initial_session_facts", {}).items():
        session.state.facts[field] = deepcopy(value); session.state.fact_sources[field] = {"source": "benchmark_initial_session"}
    service.sessions[case_id] = session; service.loop.diary_tool = SessionDiaryTool(diary_payload(case))
    messages, turns, started = [case["user_query"]], [], perf_counter()
    for turn_number in range(1, max_turns + 1):
        prior, turn_started = len(capture.results), perf_counter()
        response = app.test_client().post("/api/chat", json={"session_id": case_id, "message": messages[-1]})
        payload = response.get_json(silent=True) or {"http_body": response.get_data(as_text=True)[:4000]}
        if len(capture.results) != prior + 1: raise RuntimeError("production recorder did not capture exactly one loop result")
        loop_result, state = capture.results[-1], service.sessions[case_id].state
        turns.append({"turn": turn_number, "user_turn": messages[-1], "http_status": response.status_code,
            "response": payload, "latency_ms": round((perf_counter()-turn_started)*1000, 2),
            "state": serialize_state(state), "state_history": loop_result.state_history,
            "lineage": _lineage_validation(state, loop_result.state_history)})
        if response.status_code != 200 or payload.get("status") != "ASK": break
        target = state.action_history[-1].get("target") if state.action_history else None
        messages.append(follow_up(target, case.get("follow_up_facts", {})))
    state, path = service.sessions[case_id].state, [x["action"] for x in service.sessions[case_id].state.action_history]
    raw = {"case_id": case_id, "evaluation_id": EVALUATION_ID, "user_turns": messages[:len(turns)], "turns": turns,
           "action_path": path, "final_state": serialize_state(state), "final_answer": turns[-1]["response"].get("assistant", ""),
           "final_status": turns[-1]["response"].get("status", "HTTP_ERROR"), "latency_ms": round((perf_counter()-started)*1000, 2), "token_usage": "NOT_MEASURED"}
    result = {"case_id": case_id, "evaluation_id": EVALUATION_ID, "task_type": case["task_type"], "action_path": path,
        "ASK_count": path.count("ASK"), "RETRIEVE_count": path.count("RETRIEVE"), "READ_DIARY_count": path.count("READ_DIARY"),
        "turn_count": len(turns), "step_count": sum(x["response"].get("steps", 0) for x in turns),
        "tool_calls": [x for x in path if x in {"RETRIEVE", "READ_DIARY"}], "latency_ms": raw["latency_ms"],
        "token_usage": "NOT_MEASURED", "final_status": raw["final_status"], "answer": raw["final_answer"],
        "lineage_ready": all(x["lineage"]["ready"] for x in turns), "score_status": "PENDING_FROZEN_RUBRIC_REVIEW"}
    return raw, result


def validate_authorization(auth_path: Path, evaluation_id: str, authorization_id: str, attempt_id: str) -> tuple[dict, dict]:
    if evaluation_id != EVALUATION_ID or not all(SAFE_ID.fullmatch(x) for x in (authorization_id, attempt_id)):
        raise RuntimeError("invalid or mismatched evaluation/authorization/attempt identity")
    frozen, auth = verify_frozen_identity(), _json(auth_path)
    if not frozen["freeze_match"]: raise RuntimeError("frozen identity mismatch")
    if _prior_formal_attempt_exists(): raise RuntimeError("prior V4 formal attempt exists; automatic rerun is forbidden")
    preflight_ref = auth.get("preflight_artifact")
    preflight_path = ROOT / preflight_ref if isinstance(preflight_ref, str) else None
    preflight = _json(preflight_path) if preflight_path and preflight_path.is_file() else {}
    preflight_hash_match = bool(preflight_path and preflight_path.is_file()
                               and sha256(preflight_path) == auth.get("preflight_artifact_sha256"))
    required = (auth.get("status") == "ISSUED_NOT_EXECUTED", auth.get("evaluation_id") == evaluation_id,
        auth.get("authorization_id") == authorization_id, auth.get("attempt_id") == attempt_id,
        auth.get("benchmark_path") == "evaluation/benchmarks/benchmark_v4_cases.yaml",
        auth.get("benchmark_sha256") == frozen["benchmark_v4_sha256"], auth.get("runner_sha256") == frozen["runner_sha256"],
        auth.get("final_candidate_manifest_sha256") == sha256(FINAL_FREEZE), auth.get("agent_sha256") == frozen["agent_hash"],
        auth.get("harness_sha256") == frozen["harness_hash"], auth.get("scoring_sha256") == frozen["scoring_hash"],
        auth.get("metric_registry_sha256") == frozen["metric_registry_sha256"], auth.get("one_shot_rules_sha256") == frozen["one_shot_rules_sha256"],
        auth.get("preflight_ready") is True, isinstance(auth.get("preflight_artifact_sha256"), str), auth.get("authorized_by"),
        preflight_hash_match,
        preflight.get("evaluation_id") == EVALUATION_ID, preflight_contract_valid(preflight),
        preflight.get("v4_case_executed") == 0, preflight.get("v4_score_generated") is False,
    )
    if not all(required): raise RuntimeError("authorization is not issued or its frozen binding is invalid")
    return auth, frozen


def run(evaluation_id: str, authorization_id: str, attempt_id: str, auth_path: Path) -> None:
    auth, frozen = validate_authorization(auth_path, evaluation_id, authorization_id, attempt_id)
    out, ledger_path = OUT_ROOT / evaluation_id, OUT_ROOT / evaluation_id / "attempts.jsonl"; out.mkdir(parents=True, exist_ok=True)
    try: fd = os.open(ledger_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error: raise RuntimeError("one-shot attempt ledger already exists") from error
    started = completed = 0; stage = "INITIALIZATION"
    with os.fdopen(fd, "w", encoding="utf-8") as ledger:
        fcntl.flock(ledger.fileno(), fcntl.LOCK_EX)
        base = {"evaluation_id": evaluation_id, "authorization_id": authorization_id, "attempt_id": attempt_id,
                "agent_hash": frozen["agent_hash"], "harness_hash": frozen["harness_hash"], "runner_hash": frozen["runner_sha256"], "scoring_hash": frozen["scoring_hash"]}
        def event(status: str, **details): _append(ledger, {**base, "timestamp_utc": utc_now(), "status": status, "cases_started": started, "cases_completed": completed, **details})
        event("PREPARED")
        try:
            from adaptive_agent.flask_app import _create_adaptive_chat_service, create_app
            service, capture = _create_adaptive_chat_service(), _CaptureRecorder(); service.recorder = capture
            app = create_app(service); app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=True)
            if not verify_frozen_identity()["freeze_match"] or not model_configuration_match(): raise RuntimeError("frozen identity changed before V4 access")
            stage = "FIRST_V4_ACCESS"; event("FIRST_EVALUATION_ACCESS", evaluator=auth["authorized_by"], dataset_sha256=frozen["benchmark_v4_sha256"])
            import yaml
            source = CASES.read_bytes()
            if hashlib.sha256(source).hexdigest() != frozen["benchmark_v4_sha256"]: raise RuntimeError("sealed V4 source hash mismatch")
            cases = yaml.safe_load(source).get("cases", [])
            if not schema_compatible(): raise RuntimeError("sealed V4 schema mismatch")
            with (out / f"{attempt_id}_raw_traces.jsonl").open("x", encoding="utf-8") as raw_stream, (out / f"{attempt_id}_case_results.jsonl").open("x", encoding="utf-8") as result_stream:
                for case in cases:
                    if not verify_frozen_identity()["freeze_match"] or not model_configuration_match(): raise RuntimeError("frozen identity changed during execution")
                    started += 1; stage = "AGENT_CASE"; event("STARTED", case_id=case["case_id"])
                    raw, result = _case_result(case, service, app, capture); _append(raw_stream, raw); _append(result_stream, result)
                    completed += 1; event("CASE_COMPLETED", case_id=case["case_id"])
            event("COMPLETED", valid_raw_results=completed == len(cases), scoring_status="PENDING_FROZEN_RUBRIC_REVIEW")
        except BaseException as error:
            event("FAILED_AFTER_PARTIAL_EXECUTION" if started else "FAILED_BEFORE_FIRST_CASE", failure_stage=stage, failure_type=type(error).__name__); raise


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Step 9.28 V4 one-shot held-out runner")
    parser.add_argument("--evaluation-id", required=True); parser.add_argument("--authorization-id"); parser.add_argument("--attempt-id")
    parser.add_argument("--authorization-file", type=Path); parser.add_argument("--local-preflight", action="store_true")
    args = parser.parse_args(argv)
    if args.evaluation_id != EVALUATION_ID: parser.error("evaluation ID does not match prepared V4 identity")
    if args.local_preflight: print(json.dumps(local_preflight(), ensure_ascii=False, sort_keys=True)); return
    if not all((args.authorization_id, args.attempt_id, args.authorization_file)): parser.error("formal execution requires authorization ID, attempt ID, and authorization file")
    run(args.evaluation_id, args.authorization_id, args.attempt_id, args.authorization_file)


if __name__ == "__main__": main()
