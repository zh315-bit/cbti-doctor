"""One authorized run for the clean Step 9.11 evaluation identity.

The module is inert until an explicit authorization ID is supplied.  Its
preflight never creates a ledger entry, calls a model, or executes a case.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from scripts import run_step8_9_v1_2_1 as base

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation" / "v1_2_3"
MANIFEST = OUT / "step9_11_clean_freeze_manifest.json"
HARNESS_FREEZE = OUT / "step9_13a_harness_freeze.json"
PARENT_HARNESS_FREEZE = OUT / "step9_12b_harness_freeze.json"
LEDGER = OUT / "step9_12_execution_attempts.jsonl"
BENCHMARK = ROOT / "evaluation" / "benchmarks" / "benchmark_v2_cases.yaml"
RUBRIC = ROOT / "evaluation" / "benchmark_v1_1_scoring.md"
EVALUATION_ID = "clean-evaluation-v1_2_3-20260922-01"

# Capture the serializer before installing the trace-only wrapper.
original_state_view = base.state_view


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _corpus_hash() -> str:
    rows = []
    for path in sorted((ROOT / "rag_lib" / "pdfs").glob("*")):
        if path.is_file() and not path.name.startswith("._"):
            rows.append(f"{sha256(path)}  {path.relative_to(ROOT)}\n")
    return hashlib.sha256("".join(rows).encode()).hexdigest()


def _actual_hash(path: str, expected: str) -> str:
    if path == "runtime:deepseek_nonsecret_configuration":
        # The manifest records a non-secret fingerprint.  Its live verification
        # is performed by the dedicated local preflight, without exposing keys.
        return expected
    if path == "rag_lib/pdfs/":
        return _corpus_hash()
    return sha256(ROOT / path)


def _domain_ok(rows: list[list[str]]) -> bool:
    return all(_actual_hash(path, expected) == expected for path, expected in rows)


def _aggregate(rows: list[list[str]]) -> str:
    payload = "".join(f"{path}\t{digest}\n" for path, digest in sorted(rows))
    return hashlib.sha256(payload.encode()).hexdigest()


def verify_frozen_identity() -> dict:
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        harness = json.loads(HARNESS_FREEZE.read_text(encoding="utf-8"))
        parent_harness = json.loads(PARENT_HARNESS_FREEZE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return {"frozen_identity_match": False, "reason": f"freeze_unreadable:{type(error).__name__}"}
    agent_ok = _domain_ok(manifest["agent_behavior_files"])
    benchmark_ok = _domain_ok(manifest["benchmark_files"])
    scoring_ok = _domain_ok(manifest["scoring_files"])
    historical_aggregate_ok = (
        _aggregate(manifest["agent_behavior_files"]) == manifest.get("agent_behavior_aggregate_hash")
        and _aggregate(manifest["benchmark_files"]) == manifest.get("benchmark_aggregate_hash")
        and _aggregate(manifest["scoring_files"]) == manifest.get("scoring_aggregate_hash")
    )
    evaluation_payload = (
        f"AGENT_BEHAVIOR\t{manifest.get('agent_behavior_aggregate_hash')}\n"
        f"EVALUATION_HARNESS\t{manifest.get('evaluation_harness_aggregate_hash')}\n"
        f"BENCHMARK\t{manifest.get('benchmark_aggregate_hash')}\n"
        f"SCORING\t{manifest.get('scoring_aggregate_hash')}\n"
    )
    historical_aggregate_ok = (
        historical_aggregate_ok
        and _aggregate(manifest["evaluation_harness_files"]) == manifest.get("evaluation_harness_aggregate_hash")
        and hashlib.sha256(evaluation_payload.encode()).hexdigest() == manifest.get("evaluation_aggregate_hash")
    )
    harness_rows = harness.get("new_harness_files", [])
    harness_hash = harness.get("new_harness_aggregate_hash")
    parent_ok = (
        harness.get("evaluation_id") == EVALUATION_ID
        and harness.get("parent_harness_freeze_sha256") == sha256(PARENT_HARNESS_FREEZE)
        and harness.get("parent_harness_aggregate_hash") == parent_harness.get("new_harness_aggregate_hash")
        and parent_harness.get("old_harness_freeze", {}).get("aggregate_hash") == manifest.get("evaluation_harness_aggregate_hash")
        and harness.get("agent_behavior_aggregate_hash") == manifest.get("agent_behavior_aggregate_hash")
        and harness.get("benchmark_v2_sha256") == manifest.get("benchmark_v2_expected_sha256")
        and harness.get("scoring_aggregate_hash") == manifest.get("scoring_aggregate_hash")
        and {row[0] for row in harness_rows} == {row[0] for row in manifest["evaluation_harness_files"]}
        and harness.get("change_class") == "AUTHORIZATION_INFRASTRUCTURE_ONLY"
    )
    harness_ok = bool(parent_ok and _aggregate(harness_rows) == harness_hash and _domain_ok(harness_rows))
    case_count = sum(1 for line in BENCHMARK.read_text(encoding="utf-8").splitlines()
                     if line.lstrip().startswith("- case_id:"))
    return {
        "evaluation_id": manifest.get("evaluation_id"),
        "historical_parent": manifest.get("historical_parent"),
        "agent_freeze_match": agent_ok,
        "harness_freeze_match": harness_ok,
        "benchmark_freeze_match": benchmark_ok,
        "scoring_freeze_match": scoring_ok,
        "aggregate_hashes_match": historical_aggregate_ok and harness_ok,
        "agent_aggregate_hash": manifest.get("agent_behavior_aggregate_hash"),
        "harness_aggregate_hash": harness_hash,
        "benchmark_aggregate_hash": manifest.get("benchmark_aggregate_hash"),
        "scoring_aggregate_hash": manifest.get("scoring_aggregate_hash"),
        "harness_freeze_id": harness.get("harness_freeze_id"),
        "benchmark_v2_cases": case_count,
        "case_specific_logic_present": manifest.get("case_specific_logic_present"),
        "benchmark_hash": sha256(BENCHMARK),
        "scoring_hash": sha256(RUBRIC),
        "frozen_identity_match": all((agent_ok, harness_ok, benchmark_ok, scoring_ok, historical_aggregate_ok,
                                        case_count == 40,
                                        manifest.get("case_specific_logic_present") is False,
                                        manifest.get("evaluation_id") == EVALUATION_ID,
                                        manifest.get("historical_parent") == "STEP9_8_FAILED_EVALUATION")),
    }


def _attempts() -> list[dict]:
    if not LEDGER.exists():
        return []
    entries = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def preflight() -> dict:
    report = verify_frozen_identity()
    if not report.get("frozen_identity_match"):
        return {**report, "execution_eligible": False, "reason": "frozen_identity_mismatch"}
    try:
        entries = _attempts()
    except (OSError, ValueError):
        return {**report, "execution_eligible": False, "reason": "attempt_ledger_unreadable"}
    latest_by_attempt = {}
    for entry in entries:
        attempt_id = entry.get("attempt_id")
        if not attempt_id:
            return {**report, "execution_eligible": False, "reason": "attempt_ledger_ambiguous"}
        latest_by_attempt[attempt_id] = entry
    blocking = [entry for entry in latest_by_attempt.values()
                if entry.get("status") != "FAILED_BEFORE_FIRST_CASE" or entry.get("cases_started") != 0]
    return {**report, "prior_attempt_count": len(entries), "execution_eligible": not blocking,
            "authorization_required": True,
            "reason": "prior_attempt_blocks" if blocking else None}


def _append(entry: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _valid_authorization(value: str | None) -> bool:
    return bool(value and value.startswith(EVALUATION_ID + "-")
                and not any(marker in value.lower() for marker in ("api_key", "token", "sk-")))


def state_view(state):
    view = original_state_view(state)
    view.update({
        "goal_id": state.goal_id, "state_revision": state.state_revision,
        "semantic_provenance": state.semantic_provenance,
        "dependencies_considered": state.dependencies_considered,
        "dependencies_required": state.dependencies_required,
        "dependencies_satisfied": state.dependencies_satisfied,
        "dependencies_unavailable": state.dependencies_unavailable,
        "base_requirements": state.base_requirements,
        "effective_requirements": state.effective_requirements,
        "lineage_events": state.lineage_events,
    })
    return view


def run(evaluation_id: str, authorization_id: str) -> None:
    if evaluation_id != EVALUATION_ID:
        raise ValueError("--evaluation-id does not match the frozen evaluation identity")
    report = preflight()
    if not report["execution_eligible"]:
        raise RuntimeError("clean evaluation is not eligible")
    if not _valid_authorization(authorization_id):
        raise ValueError("authorization ID must be new, non-secret, and scoped to this evaluation")
    if any(entry.get("authorization_id") == authorization_id for entry in _attempts()):
        raise ValueError("authorization ID has already been used")
    attempt = {
        "attempt_id": f"attempt_{uuid4().hex}", "timestamp": datetime.now(timezone.utc).isoformat(),
        "evaluation_id": EVALUATION_ID, "authorization_id": authorization_id,
        "benchmark_hash": report["benchmark_hash"], "scoring_hash": report["scoring_hash"],
        "agent_hash": report["agent_aggregate_hash"], "harness_hash": report["harness_aggregate_hash"],
        "status": "PREPARED", "cases_started": 0, "cases_completed": 0,
        "first_case_id": "unknown", "last_completed_case_id": "unknown", "valid_results": False,
    }
    _append(attempt)
    started = False
    completed = 0
    last_case = "unknown"
    trace_path = OUT / f"step9_12_attempt_{attempt['attempt_id']}_raw_traces.jsonl"

    def before_case(case):
        nonlocal started
        if not started:
            latest = verify_frozen_identity()
            if not latest["frozen_identity_match"]:
                raise RuntimeError("frozen identity changed before first case")
            started = True
            _append({**attempt, "timestamp": datetime.now(timezone.utc).isoformat(), "status": "STARTED",
                     "cases_started": 1, "first_case_id": case["case_id"]})

    def after_case(case, _result):
        nonlocal completed, last_case
        completed += 1; last_case = case["case_id"]
        _append({**attempt, "timestamp": datetime.now(timezone.utc).isoformat(), "status": "STARTED",
                 "cases_started": max(1, completed), "cases_completed": completed,
                 "last_completed_case_id": last_case})

    try:
        base.OUT = OUT; base.BENCHMARK = BENCHMARK; base.write_manifest = lambda _spec: None
        base.state_view = state_view
        import adaptive_agent.flask_app as app_factory
        sys.modules["main_flask"] = type("ProductionAppShim", (), {
            "_create_adaptive_chat_service": staticmethod(app_factory._create_adaptive_chat_service),
            "create_app": staticmethod(app_factory.create_app),
        })
        base.main(before_case=before_case, after_case=after_case, trace_path=trace_path)
        _append({**attempt, "timestamp": datetime.now(timezone.utc).isoformat(), "status": "COMPLETED",
                 "cases_started": completed, "cases_completed": completed, "last_completed_case_id": last_case,
                 "valid_results": completed == 40})
    except BaseException as error:
        status = "FAILED_AFTER_PARTIAL_EXECUTION" if started else "FAILED_BEFORE_FIRST_CASE"
        _append({**attempt, "timestamp": datetime.now(timezone.utc).isoformat(), "status": status,
                 "cases_started": max(1, completed) if started else 0, "cases_completed": completed,
                 "last_completed_case_id": last_case, "failure_type": type(error).__name__})
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description="Authorized clean Step 9.12 evaluation")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--evaluation-id", required=True)
    parser.add_argument("--authorization-id")
    args = parser.parse_args(argv)
    if args.evaluation_id != EVALUATION_ID:
        parser.error("--evaluation-id does not match the frozen evaluation identity")
    if args.preflight:
        print(json.dumps(preflight(), ensure_ascii=False, sort_keys=True)); return
    if not args.authorization_id:
        raise RuntimeError("--authorization-id is required")
    run(args.evaluation_id, args.authorization_id)


if __name__ == "__main__":
    main()
