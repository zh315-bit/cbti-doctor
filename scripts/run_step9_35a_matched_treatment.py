"""One-shot Step 9.34a matched-treatment runner adapter.

The adapter binds the frozen treatment identity and matched protocol while
delegating each authorized case to the unchanged production V4 case path. It
does not issue authorization and importing it does not read benchmark cases.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FREEZE_DIR = ROOT / "evaluation" / "v1_2_3"
OUT_ROOT = ROOT / "evaluation" / "v4_runs"
TREATMENT_FREEZE = FREEZE_DIR / "step9_33a_treatment_freeze.json"
BASELINE_FREEZE = FREEZE_DIR / "step9_26_final_candidate_freeze.json"
HARNESS_FREEZE = FREEZE_DIR / "step9_13a_harness_freeze.json"
SCORING_MANIFEST = FREEZE_DIR / "step9_11_clean_freeze_manifest.json"
BENCHMARK_MANIFEST = ROOT / "evaluation" / "benchmarks" / "benchmark_v4_manifest.json"
BENCHMARK = ROOT / "evaluation" / "benchmarks" / "benchmark_v4_cases.yaml"
REGISTRY = FREEZE_DIR / "step9_26_v4_metric_registry.json"
RULES = FREEZE_DIR / "step9_26_v4_one_shot_rules.md"
PROTOCOL = FREEZE_DIR / "step9_34a_matched_comparison_protocol.json"
METRIC_LOCK = FREEZE_DIR / "step9_34a_baseline_metric_lock.json"
CLAIM_POLICY = FREEZE_DIR / "step9_34a_claim_policy.json"
RUNNER_FREEZE = FREEZE_DIR / "step9_35a_treatment_runner_freeze.json"
PRODUCTION_CASE_PATH_RUNNER = ROOT / "scripts" / "run_step9_28_v4_heldout.py"
COMPARISON_CLASS = "POST_HOC_MATCHED_FROZEN_BASELINE"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")
CASE_COUNT = 40


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path.name}")
    return value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _inventory_aggregate(rows: list[list[str]]) -> str:
    payload = "".join(f"{path}\t{digest}\n" for path, digest in sorted(rows))
    return sha256_bytes(payload.encode())


def _actual_inventory_hash(path: str, expected: str) -> str:
    from scripts.run_step9_12_frozen_evaluation import _actual_hash

    return _actual_hash(path, expected)


def _verify_inventory(rows: list[list[str]], expected_aggregate: str) -> bool:
    return (_inventory_aggregate(rows) == expected_aggregate and
            all(_actual_inventory_hash(path, digest) == digest for path, digest in rows))


def current_frozen_bindings() -> dict[str, Any]:
    """Recompute identities used by the treatment contract; case-inert."""
    treatment = read_json(TREATMENT_FREEZE)
    baseline = read_json(BASELINE_FREEZE)
    baseline_environment = read_json(FREEZE_DIR / "step9_32_baseline_agent_freeze.json")
    harness = read_json(HARNESS_FREEZE)
    scoring = read_json(SCORING_MANIFEST)
    manifest = read_json(BENCHMARK_MANIFEST)
    protocol = read_json(PROTOCOL)
    template = read_json(FREEZE_DIR / "step9_34a_treatment_authorization_template.json")
    runner_freeze = read_json(RUNNER_FREEZE) if RUNNER_FREEZE.is_file() else {}
    t_agent = treatment["treatment_agent_aggregate_sha256"]
    b_agent = baseline["agent_aggregate_sha256"]
    h_rows = harness["new_harness_files"]
    s_rows = scoring["scoring_files"]
    t_rows = treatment["agent_behavior_files"]
    h_aggregate = harness["new_harness_aggregate_hash"]
    s_aggregate = scoring["scoring_aggregate_hash"]
    runtime_model_match = False
    try:
        from scripts.run_step9_28_v4_heldout import model_configuration_match

        runtime_model_match = model_configuration_match()
    except (ImportError, OSError):
        runtime_model_match = False

    bound = template["bound_identities"]
    case_fp = protocol["design_classification"]["case_set_and_order_fingerprint_sha256"]
    treatment_model_fp = next((digest for path, digest in t_rows
                               if path == "runtime:deepseek_nonsecret_configuration"), None)
    baseline_model_fp = next((digest for path, digest in baseline["agent_behavior_files"]
                              if path == "runtime:deepseek_nonsecret_configuration"), None)
    treatment_rag_rows = sorted((path, digest) for path, digest in t_rows
                                if path in {item["path"] for item in baseline_environment["baseline_rag_config_files"]})
    baseline_rag_rows = sorted((item["path"], item["sha256"])
                               for item in baseline_environment["baseline_rag_config_files"])
    try:
        from adaptive_agent.runner import AdaptiveAgentLoop
        from scripts.run_step9_28_v4_heldout import _case_result

        max_turns = _case_result.__defaults__[0]
        max_steps = AdaptiveAgentLoop.__init__.__defaults__[-1]
    except (ImportError, IndexError, TypeError):
        max_turns = max_steps = None
    values = {
        "treatment_agent_sha256": t_agent,
        "baseline_agent_sha256": b_agent,
        "benchmark_path": manifest["benchmark_path"],
        "benchmark_sha256": sha256_file(BENCHMARK),
        "benchmark_manifest_sha256": sha256_file(BENCHMARK_MANIFEST),
        "harness_sha256": h_aggregate,
        "scoring_sha256": s_aggregate,
        "scoring_rubric_sha256": sha256_file(ROOT / "evaluation" / "benchmark_v1_1_scoring.md"),
        "metric_registry_sha256": sha256_file(REGISTRY),
        "one_shot_rules_sha256": sha256_file(RULES),
        "matched_protocol_sha256": sha256_file(PROTOCOL),
        "baseline_metric_lock_sha256": sha256_file(METRIC_LOCK),
        "claim_policy_sha256": sha256_file(CLAIM_POLICY),
        "model_configuration_fingerprint_sha256": treatment_model_fp,
        "rag_configuration_fingerprint_sha256": _inventory_aggregate(treatment_rag_rows),
        "tool_adapter_sha256": sha256_file(ROOT / "adaptive_agent" / "tools.py"),
        "dependency_lock_sha256": sha256_file(ROOT / "requirements-lock.txt"),
        "treatment_runner_sha256": sha256_file(Path(__file__)),
        "production_case_path_runner_sha256": sha256_file(PRODUCTION_CASE_PATH_RUNNER),
        "comparison_class": protocol["comparison_class"],
        "evaluation_id": template["evaluation_id"],
        "case_count": protocol["design_classification"]["case_count"],
        "case_order_fingerprint_sha256": case_fp,
        "max_runner_turns": max_turns,
        "agent_loop_max_steps": max_steps,
        "fresh_session_per_case": True,
    }
    checks = {
        "treatment_agent": t_agent == bound["treatment_agent_sha256"]
        and t_agent != b_agent and _verify_inventory(t_rows, t_agent),
        "baseline_agent": b_agent == protocol["identities"]["baseline_agent_sha256"],
        "benchmark": values["benchmark_path"] == template["bound_identities"]["benchmark_path"]
        and values["benchmark_sha256"] == template["bound_identities"]["benchmark_sha256"]
        and manifest["benchmark_sha256"] == values["benchmark_sha256"]
        and manifest["status"] == "SEALED_NOT_EVALUATED" and manifest["immutable"] is True
        and manifest["case_count"] == CASE_COUNT and protocol["design_classification"]["case_count"] == CASE_COUNT,
        "benchmark_manifest": values["benchmark_manifest_sha256"] == template["bound_identities"]["benchmark_manifest_sha256"],
        "case_set_and_order": values["case_count"] == template["bound_identities"]["case_count"] == CASE_COUNT
        and case_fp == template["bound_identities"]["case_order_fingerprint_sha256"],
        "harness": _verify_inventory(h_rows, h_aggregate)
        and h_aggregate == template["bound_identities"]["harness_sha256"],
        "scoring": _verify_inventory(s_rows, s_aggregate)
        and s_aggregate == template["bound_identities"]["scoring_aggregate_sha256"],
        "scoring_rubric": values["scoring_rubric_sha256"]
        == template["bound_identities"]["scoring_rubric_sha256"],
        "metric_registry": values["metric_registry_sha256"] == template["bound_identities"]["metric_registry_sha256"],
        "one_shot_rules": values["one_shot_rules_sha256"] == template["bound_identities"]["one_shot_rules_sha256"],
        "production_case_path_runner": values["production_case_path_runner_sha256"]
        == read_json(FREEZE_DIR / "step9_29a_v4_runner_freeze.json")["runner_sha256"],
        "matched_protocol": values["matched_protocol_sha256"] == template["protocol_sha256"]
        and protocol["comparison_class"] == COMPARISON_CLASS,
        "baseline_metric_lock": values["baseline_metric_lock_sha256"] == template["baseline_metric_lock_sha256"],
        "claim_policy": values["claim_policy_sha256"] == template["claim_policy_sha256"],
        "model_configuration": runtime_model_match and treatment_model_fp == baseline_model_fp
        and treatment_model_fp == bound["model_configuration_fingerprint_sha256"],
        "tool_configuration": values["tool_adapter_sha256"] == bound["tool_adapter_sha256"],
        "dependency_lock": values["dependency_lock_sha256"] == bound["dependency_lock_sha256"],
        "rag_configuration": bool(treatment_rag_rows) and treatment_rag_rows == baseline_rag_rows
        and values["rag_configuration_fingerprint_sha256"] == bound["rag_configuration_fingerprint_sha256"],
        "execution_limits": max_turns == bound["max_runner_turns"]
        and max_steps == bound["agent_loop_max_steps"],
        "treatment_runner_freeze": runner_freeze.get("status") == "FROZEN_NOT_AUTHORIZED"
        and runner_freeze.get("treatment_runner_sha256") == values["treatment_runner_sha256"]
        and runner_freeze.get("comparison_class") == COMPARISON_CLASS
        and runner_freeze.get("evaluation_id") == values["evaluation_id"]
        and runner_freeze.get("bound_identities") == {key: values[key] for key in (
            "baseline_agent_sha256", "treatment_agent_sha256", "benchmark_path",
            "benchmark_sha256", "benchmark_manifest_sha256", "case_count",
            "case_order_fingerprint_sha256", "harness_sha256", "scoring_sha256",
            "scoring_rubric_sha256", "metric_registry_sha256", "one_shot_rules_sha256",
            "matched_protocol_sha256", "baseline_metric_lock_sha256", "claim_policy_sha256",
            "model_configuration_fingerprint_sha256", "rag_configuration_fingerprint_sha256",
            "tool_adapter_sha256", "dependency_lock_sha256", "max_runner_turns",
            "agent_loop_max_steps", "fresh_session_per_case")}
        and runner_freeze.get("implementation_boundary", {}).get("production_case_path_runner_sha256")
        == values["production_case_path_runner_sha256"],
    }
    checks["rag_configuration"] = (checks["rag_configuration"] and
        _inventory_aggregate(treatment_rag_rows) == bound["rag_configuration_fingerprint_sha256"])
    values["checks"] = checks
    values["all_frozen_hashes_match"] = all(checks.values())
    return values


def case_order_fingerprint(case_ids: list[str]) -> str:
    return sha256_bytes("\n".join(case_ids).encode("utf-8"))


def verify_case_order(case_ids: list[str], expected_count: int, expected_fingerprint: str) -> bool:
    return (len(case_ids) == expected_count == CASE_COUNT and
            len(set(case_ids)) == expected_count and
            all(isinstance(case_id, str) and case_id for case_id in case_ids) and
            case_order_fingerprint(case_ids) == expected_fingerprint)


def _read_auth(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError("authorization file is missing")
    return read_json(path)


def _existing_identity_in_ledgers(run_root: Path, auth_id: str, attempt_id: str) -> bool:
    for ledger_path in run_root.glob("*/attempts.jsonl"):
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("authorization_id") == auth_id or event.get("attempt_id") == attempt_id:
                return True
    return False


def validate_authorization(
    auth_path: Path,
    evaluation_id: str,
    authorization_id: str,
    attempt_id: str,
    supplied: dict[str, str],
    *,
    run_root: Path = OUT_ROOT,
    frozen: dict[str, Any] | None = None,
) -> tuple[dict, dict]:
    """Validate IDs, authorization, all pins, uniqueness and output isolation."""
    if not all(isinstance(value, str) and SAFE_ID.fullmatch(value)
               for value in (evaluation_id, authorization_id, attempt_id)):
        raise RuntimeError("invalid evaluation/authorization/attempt identity")
    pins = frozen if frozen is not None else current_frozen_bindings()
    if not pins.get("all_frozen_hashes_match"):
        raise RuntimeError("frozen artifact or treatment runner hash mismatch")
    if evaluation_id != pins["evaluation_id"]:
        raise RuntimeError("evaluation ID does not match treatment namespace")
    if pins["treatment_agent_sha256"] == pins["baseline_agent_sha256"]:
        raise RuntimeError("baseline Agent cannot be supplied as treatment")
    for key in ("treatment_agent_sha256", "benchmark_sha256", "harness_sha256", "scoring_sha256",
                "metric_registry_sha256", "one_shot_rules_sha256", "matched_protocol_sha256"):
        if supplied.get(key) != pins[key]:
            raise RuntimeError(f"supplied {key} does not match frozen identity")

    auth = _read_auth(auth_path)
    expected_fields = {
        "status": "ISSUED_NOT_EXECUTED",
        "authorization_type": "ONE_SHOT_MATCHED_TREATMENT",
        "comparison_class": COMPARISON_CLASS,
        "evaluation_id": evaluation_id,
        "authorization_id": authorization_id,
        "attempt_id": attempt_id,
        "treatment_agent_sha256": pins["treatment_agent_sha256"],
        "baseline_agent_sha256": pins["baseline_agent_sha256"],
        "benchmark_sha256": pins["benchmark_sha256"],
        "benchmark_manifest_sha256": pins["benchmark_manifest_sha256"],
        "harness_sha256": pins["harness_sha256"],
        "scoring_sha256": pins["scoring_sha256"],
        "metric_registry_sha256": pins["metric_registry_sha256"],
        "one_shot_rules_sha256": pins["one_shot_rules_sha256"],
        "matched_protocol_sha256": pins["matched_protocol_sha256"],
        "baseline_metric_lock_sha256": pins["baseline_metric_lock_sha256"],
        "claim_policy_sha256": pins["claim_policy_sha256"],
        "treatment_runner_sha256": pins["treatment_runner_sha256"],
        "production_case_path_runner_sha256": pins["production_case_path_runner_sha256"],
        "case_count": CASE_COUNT,
        "case_order_fingerprint_sha256": pins["case_order_fingerprint_sha256"],
        "max_formal_attempts": 1,
    }
    for key, expected in expected_fields.items():
        if auth.get(key) != expected:
            raise RuntimeError(f"authorization {key} mismatch")
    if auth.get("consumed") is not False or auth.get("consumed_at_utc") is not None:
        raise RuntimeError("authorization is consumed or consumption state is missing")
    if not auth.get("authorized_by"):
        raise RuntimeError("authorization issuer is missing")

    namespace = run_root / evaluation_id
    if namespace.exists():
        raise RuntimeError("treatment output namespace collision; rerun forbidden")
    if _existing_identity_in_ledgers(run_root, authorization_id, attempt_id):
        raise RuntimeError("duplicate authorization or attempt identity")
    return auth, pins


def _append(stream, event: dict) -> None:
    stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True, default=str) + "\n")
    stream.flush()
    os.fsync(stream.fileno())


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def run(
    evaluation_id: str,
    authorization_id: str,
    attempt_id: str,
    authorization_file: Path,
    supplied: dict[str, str],
) -> None:
    auth, pins = validate_authorization(authorization_file, evaluation_id, authorization_id,
                                        attempt_id, supplied)
    out = OUT_ROOT / evaluation_id
    out.mkdir(mode=0o700, parents=False, exist_ok=False)
    _fsync_directory(OUT_ROOT)
    ledger_path = out / "attempts.jsonl"
    try:
        fd = os.open(ledger_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise RuntimeError("one-shot attempt ledger already exists") from error
    _fsync_directory(out)
    started = completed = 0
    base_event = {"evaluation_id": evaluation_id, "authorization_id": authorization_id,
                  "attempt_id": attempt_id, "comparison_class": COMPARISON_CLASS,
                  "treatment_agent_sha256": pins["treatment_agent_sha256"],
                  "runner_sha256": pins["treatment_runner_sha256"]}
    with os.fdopen(fd, "w", encoding="utf-8") as ledger:
        fcntl.flock(ledger.fileno(), fcntl.LOCK_EX)

        def event(status: str, **details: Any) -> None:
            _append(ledger, {**base_event, "timestamp_utc": utc_now(), "status": status,
                             "cases_started": started, "cases_completed": completed, **details})

        event("PREPARED")
        event("AUTHORIZATION_CONSUMED")
        # One-shot rules require this durable marker before reading sealed case bytes.
        event("FIRST_EVALUATION_ACCESS", dataset_sha256=pins["benchmark_sha256"],
              case_order_fingerprint_sha256=pins["case_order_fingerprint_sha256"])
        stage = "FIRST_EVALUATION_ACCESS"
        try:
            if sha256_file(BENCHMARK) != pins["benchmark_sha256"]:
                raise RuntimeError("benchmark hash mismatch after first-access event")
            import yaml

            spec = yaml.safe_load(BENCHMARK.read_bytes())
            cases = spec.get("cases") if isinstance(spec, dict) else None
            required = {"case_id", "user_query", "task_type", "diary_facts", "follow_up_facts"}
            if not isinstance(cases, list) or len(cases) != CASE_COUNT:
                raise RuntimeError("matched treatment requires exactly 40 benchmark cases")
            if any(not isinstance(case, dict) or not required.issubset(case) for case in cases):
                raise RuntimeError("benchmark schema mismatch")
            case_ids = [case["case_id"] for case in cases]
            if not verify_case_order(case_ids, pins["case_count"], pins["case_order_fingerprint_sha256"]):
                raise RuntimeError("case set/order differs from frozen matched baseline")
            event("CASE_SET_AND_ORDER_VERIFIED", case_count=CASE_COUNT,
                  case_order_fingerprint_sha256=case_order_fingerprint(case_ids))
            fresh_pins = current_frozen_bindings()
            if not fresh_pins["all_frozen_hashes_match"] or any(
                fresh_pins[key] != pins[key] for key in supplied_hash_keys()
            ):
                raise RuntimeError("frozen identity changed before first treatment case")

            from adaptive_agent.flask_app import _create_adaptive_chat_service, create_app
            from scripts import run_step9_28_v4_heldout as production_case_path

            service = _create_adaptive_chat_service()
            capture = production_case_path._CaptureRecorder()
            service.recorder = capture
            app = create_app(service)
            app.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=True)
            raw_path = out / f"{attempt_id}_raw_traces.jsonl"
            result_path = out / f"{attempt_id}_case_results.jsonl"
            with raw_path.open("x", encoding="utf-8") as raw_stream, result_path.open("x", encoding="utf-8") as result_stream:
                _fsync_directory(out)
                event("STARTED", scope="ATTEMPT")
                previous_evaluation_id = production_case_path.EVALUATION_ID
                production_case_path.EVALUATION_ID = evaluation_id
                try:
                    for case in cases:
                        started += 1
                        event("STARTED", scope="CASE", case_id=case["case_id"])
                        raw, result = production_case_path._case_result(case, service, app, capture)
                        _append(raw_stream, raw)
                        _append(result_stream, result)
                        completed += 1
                        event("CASE_COMPLETED", case_id=case["case_id"])
                finally:
                    production_case_path.EVALUATION_ID = previous_evaluation_id
            event("COMPLETED", score_status="PENDING_FROZEN_RUBRIC_REVIEW")
        except BaseException as error:
            event("FAILED_AFTER_PARTIAL_EXECUTION" if started else "FAILED_BEFORE_FIRST_CASE",
                  failure_stage=stage, failure_type=type(error).__name__)
            raise


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="One-shot Step 9.34a matched V4 treatment runner")
    parser.add_argument("--evaluation-id", required=True)
    parser.add_argument("--authorization-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--authorization-file", required=True, type=Path)
    parser.add_argument("--treatment-agent-sha256", required=True)
    parser.add_argument("--benchmark-sha256", required=True)
    parser.add_argument("--harness-sha256", required=True)
    parser.add_argument("--scoring-sha256", required=True)
    parser.add_argument("--metric-registry-sha256", required=True)
    parser.add_argument("--one-shot-rules-sha256", required=True)
    parser.add_argument("--matched-protocol-sha256", required=True)
    args = parser.parse_args(argv)
    supplied = {
        "treatment_agent_sha256": args.treatment_agent_sha256,
        "benchmark_sha256": args.benchmark_sha256,
        "harness_sha256": args.harness_sha256,
        "scoring_sha256": args.scoring_sha256,
        "metric_registry_sha256": args.metric_registry_sha256,
        "one_shot_rules_sha256": args.one_shot_rules_sha256,
        "matched_protocol_sha256": args.matched_protocol_sha256,
    }
    run(args.evaluation_id, args.authorization_id, args.attempt_id,
        args.authorization_file, supplied)


def supplied_hash_keys() -> tuple[str, ...]:
    return ("treatment_agent_sha256", "benchmark_sha256", "harness_sha256", "scoring_sha256",
            "metric_registry_sha256", "one_shot_rules_sha256", "matched_protocol_sha256")


if __name__ == "__main__":
    main()
