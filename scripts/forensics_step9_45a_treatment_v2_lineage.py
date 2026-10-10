"""Read-only lineage forensics for the explicitly authorized treatment-v2 run.

This module never invokes an execution runner, Agent, model, or RAG. Its
``main`` reads only the pinned formal run artifacts and writes five new
forensic outputs using exclusive creation. Importing the module is inert.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.step9_30a2_lineage_sidecar import classify_true_failure_dimensions

OUT = ROOT / "evaluation/v1_2_3"
RUN = ROOT / "evaluation/v4_runs/heldout-v4-step9_43-treatment-v2-20260928-01"
EVALUATION_ID = "heldout-v4-step9_43-treatment-v2-20260928-01"
AUTHORIZATION_ID = "auth-step9_44r1-ecce3f6d87e64ace822fc46c97c18f55"
ATTEMPT_ID = "attempt-step9_44r1-cb362342ae31449aaffba8092c346864"
COMPARISON_CLASS = "POST_HOC_MATCHED_FROZEN_BASELINE"
TASK_DISTRIBUTION = {
    "KNOWLEDGE_QA": 10,
    "CAUSE_ASSESSMENT": 10,
    "PERSONALIZED_DECISION": 10,
    "DATA_ANALYSIS": 10,
}

LEDGER = RUN / "attempts.jsonl"
RESULTS = RUN / f"{ATTEMPT_ID}_case_results.jsonl"
TRACES = RUN / f"{ATTEMPT_ID}_raw_traces.jsonl"
TREATMENT_FREEZE = OUT / "step9_42_treatment_v2_freeze.json"
IDENTITY_CONTRACT = OUT / "step9_43a_treatment_v2_identity_contract.json"
RUNNER_FREEZE = OUT / "step9_43a_treatment_v2_runner_freeze.json"
AUTHORIZATION = OUT / "step9_44_r1_treatment_v2_authorization_manifest.json"
AUTHORIZATION_AUDIT = OUT / "step9_44_r1_treatment_v2_authorization_audit.json"
V2_RUNNER = ROOT / "scripts/run_step9_43a_treatment_v2.py"
HARNESS_FREEZE = OUT / "step9_13a_harness_freeze.json"
SCORING_FREEZE = OUT / "step9_11_clean_freeze_manifest.json"
METRIC_REGISTRY = OUT / "step9_26_v4_metric_registry.json"
ONE_SHOT_RULES = OUT / "step9_26_v4_one_shot_rules.md"
MATCHED_PROTOCOL = OUT / "step9_34a_matched_comparison_protocol.json"
BENCHMARK = ROOT / "evaluation/benchmarks/benchmark_v4_cases.yaml"
BENCHMARK_MANIFEST = ROOT / "evaluation/benchmarks/benchmark_v4_manifest.json"
ADJUDICATION_SCHEMA = OUT / "step9_30a_v4_adjudication_schema.json"

EXPECTED_RESULT_SHA256 = "4648b8e320f535001922f13a969d1482433bfa15f88233cf9a7e70b06cafed6c"
EXPECTED_TRACE_SHA256 = "d7ddf2a9a47ba62a85a7d1b85f069cc9593fd8f46cc4a01c1f3c8a055698cec2"
EXPECTED_SCHEMA_SHA256 = "21367c176f6b070d875a203ff779cfd44e2cb86a4e8956e1f93870fd054834c8"
EXPECTED_AGENT_SHA256 = "b9e891e7cd077dd5b3c6fa72b71faad978a24226c2b5e89e0b06aabde93b51d6"
EXPECTED_BENCHMARK_SHA256 = "8b8c72092fcd7544e69d5d2ecd13610c7bb4c14210fca330698b3e5ab3f01d7f"
EXPECTED_HARNESS_SHA256 = "8bc271bebc1c5da5351d517e2bb4a0d1a99fda3de1b713a6197b12f81fad70c7"
EXPECTED_SCORING_SHA256 = "f742a8f8af7c8747818dadad81621c15d12d74f50538019913dfe18ab53bf59b"
EXPECTED_RUBRIC_SHA256 = "a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899"
EXPECTED_REGISTRY_SHA256 = "de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056"
EXPECTED_RULES_SHA256 = "1c7ed4ef47865b117bc943f3e0ad9a859f4f74cfb4e8001f723ac5532af140d0"
EXPECTED_PROTOCOL_SHA256 = "a71ba06090370b576fbba66bc4b005e519ddbabff3021a40c6546fc855f90265"

OUTFILES = (
    OUT / "step9_45a_v2_run_input_freeze.json",
    OUT / "step9_45a_v2_lineage_forensics.json",
    OUT / "step9_45a_v2_lineage_forensics.md",
    OUT / "step9_45a_v2_lineage_case_matrix.jsonl",
    OUT / "step9_45a_v2_lineage_sidecar.jsonl",
)

DIMENSIONS = (
    "goal_alignment",
    "facts_state_integrity",
    "action_resource_selection",
    "evidence_answer_scope",
    "interaction_efficiency",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json_bytes(data: bytes, label: str) -> dict[str, Any]:
    value = json.loads(data.decode("utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"FAIL CLOSED: expected JSON object: {label}")
    return value


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"FAIL CLOSED: required JSON missing: {path}")
    return read_json_bytes(path.read_bytes(), path.relative_to(ROOT).as_posix())


def parse_jsonl(data: bytes, label: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(data.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict):
            raise RuntimeError(f"FAIL CLOSED: JSONL row is not an object: {label}:{number}")
        rows.append(item)
    return rows


def initial_execution_hash_gate() -> dict[Path, bytes]:
    """Hash formal results/traces before parsing or any other input work."""
    data: dict[Path, bytes] = {}
    for path in (RESULTS, TRACES):
        if not path.is_file():
            raise RuntimeError(f"FAIL CLOSED: formal execution file missing: {path}")
        raw = path.read_bytes()
        actual = sha256_bytes(raw)
        expected = EXPECTED_RESULT_SHA256 if path == RESULTS else EXPECTED_TRACE_SHA256
        if actual != expected:
            raise RuntimeError(f"FAIL CLOSED: formal execution SHA-256 mismatch: {path.name}")
        data[path] = raw
    if not LEDGER.is_file():
        raise RuntimeError(f"FAIL CLOSED: formal attempt ledger missing: {LEDGER}")
    data[LEDGER] = LEDGER.read_bytes()
    return data


def verify_execution_unchanged(start: dict[Path, bytes]) -> dict[str, str]:
    ending: dict[str, str] = {}
    for path, raw in start.items():
        if not path.is_file():
            raise RuntimeError(f"FAIL CLOSED: formal execution file disappeared: {path}")
        actual = sha256_file(path)
        if actual != sha256_bytes(raw):
            raise RuntimeError(f"FAIL CLOSED: formal execution file changed during forensics: {path.name}")
        ending[path.relative_to(ROOT).as_posix()] = actual
    return ending


def file_record(path: Path, raw: bytes | None = None) -> dict[str, Any]:
    data = path.read_bytes() if raw is None else raw
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": sha256_bytes(data),
        "byte_size": len(data),
        "line_count": len(data.splitlines()),
    }


def line_reference(path: Path, raw: bytes, case_id: str) -> dict[str, Any]:
    for number, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("case_id") == case_id:
            return {
                "path": path.relative_to(ROOT).as_posix(),
                "line_number": number,
                "line_sha256": sha256_bytes(line.encode("utf-8")),
            }
    raise RuntimeError(f"FAIL CLOSED: case line absent in {path.name}: {case_id}")


def inventory_aggregate(rows: list[list[str]]) -> str:
    payload = "".join(f"{path}\t{digest}\n" for path, digest in sorted(rows))
    return sha256_bytes(payload.encode("utf-8"))


def corpus_hash() -> str:
    rows: list[str] = []
    for path in sorted((ROOT / "rag_lib/pdfs").glob("*")):
        if path.is_file() and not path.name.startswith("._"):
            rows.append(f"{sha256_file(path)}  {path.relative_to(ROOT).as_posix()}\n")
    return sha256_bytes("".join(rows).encode("utf-8"))


def actual_inventory_hash(rel_path: str, expected: str) -> str:
    if rel_path == "runtime:deepseek_nonsecret_configuration":
        # The secret-free runtime fingerprint is pinned in the frozen V2
        # inventory; this forensic tool never loads or emits credentials.
        return expected
    if rel_path == "rag_lib/pdfs/":
        return corpus_hash()
    target = ROOT / rel_path
    if not target.is_file():
        raise RuntimeError(f"FAIL CLOSED: V2 inventory file missing: {rel_path}")
    return sha256_file(target)


def verify_v2_identities() -> dict[str, Any]:
    contract = read_json(IDENTITY_CONTRACT)
    treatment_freeze = read_json(TREATMENT_FREEZE)
    runner_freeze = read_json(RUNNER_FREEZE)
    authorization = read_json(AUTHORIZATION)
    authorization_audit = read_json(AUTHORIZATION_AUDIT)
    harness_freeze = read_json(HARNESS_FREEZE)
    scoring_freeze = read_json(SCORING_FREEZE)
    protocol = read_json(MATCHED_PROTOCOL)
    registry = read_json(METRIC_REGISTRY)

    actual_hashes = {
        "identity_contract_sha256": sha256_file(IDENTITY_CONTRACT),
        "treatment_freeze_sha256": sha256_file(TREATMENT_FREEZE),
        "runner_freeze_sha256": sha256_file(RUNNER_FREEZE),
        "v2_runner_sha256": sha256_file(V2_RUNNER),
        "authorization_manifest_sha256": sha256_file(AUTHORIZATION),
        "authorization_audit_sha256": sha256_file(AUTHORIZATION_AUDIT),
        "benchmark_sha256": sha256_file(BENCHMARK),
        "benchmark_manifest_sha256": sha256_file(BENCHMARK_MANIFEST),
        "harness_sha256": harness_freeze.get("new_harness_aggregate_hash", ""),
        "scoring_sha256": scoring_freeze.get("scoring_aggregate_hash", ""),
        "scoring_rubric_sha256": sha256_file(ROOT / "evaluation/benchmark_v1_1_scoring.md"),
        "metric_registry_sha256": sha256_file(METRIC_REGISTRY),
        "one_shot_rules_sha256": sha256_file(ONE_SHOT_RULES),
        "matched_protocol_sha256": sha256_file(MATCHED_PROTOCOL),
        "adjudication_schema_sha256": sha256_file(ADJUDICATION_SCHEMA),
    }
    if actual_hashes["adjudication_schema_sha256"] != EXPECTED_SCHEMA_SHA256:
        raise RuntimeError("FAIL CLOSED: frozen adjudication schema hash mismatch")

    contract_path = IDENTITY_CONTRACT.relative_to(ROOT).as_posix()
    identity_rows = treatment_freeze.get("agent_behavior_files")
    if not isinstance(identity_rows, list) or not identity_rows:
        raise RuntimeError("FAIL CLOSED: treatment-v2 inventory is missing")
    inventory_ok = all(
        isinstance(row, list) and len(row) == 2 and
        actual_inventory_hash(row[0], row[1]) == row[1]
        for row in identity_rows
    )
    agent_aggregate = inventory_aggregate(identity_rows)
    if (not inventory_ok or len(identity_rows) != treatment_freeze.get("agent_behavior_file_count") or
            agent_aggregate != EXPECTED_AGENT_SHA256 or
            treatment_freeze.get("treatment_v2_agent_sha256") != EXPECTED_AGENT_SHA256):
        raise RuntimeError("FAIL CLOSED: treatment-v2 Agent inventory/freeze mismatch")

    harness_rows = harness_freeze.get("new_harness_files", [])
    scoring_rows = scoring_freeze.get("scoring_files", [])
    harness_actual_rows = [[path, actual_inventory_hash(path, digest)] for path, digest in harness_rows]
    scoring_actual_rows = [[path, actual_inventory_hash(path, digest)] for path, digest in scoring_rows]
    harness_actual = inventory_aggregate(harness_actual_rows)
    scoring_actual = inventory_aggregate(scoring_actual_rows)
    harness_files_match = all(actual == expected for (_, expected), (_, actual) in zip(harness_rows, harness_actual_rows))
    scoring_files_match = all(actual == expected for (_, expected), (_, actual) in zip(scoring_rows, scoring_actual_rows))
    shared_frozen_pin_audit = [
        {
            "path": BENCHMARK.relative_to(ROOT).as_posix(),
            "expected_sha256": EXPECTED_BENCHMARK_SHA256,
            "actual_sha256": actual_hashes["benchmark_sha256"],
            "match": EXPECTED_BENCHMARK_SHA256 == actual_hashes["benchmark_sha256"],
        },
        {
            "path": f"{HARNESS_FREEZE.relative_to(ROOT).as_posix()}#new_harness_files",
            "expected_sha256": EXPECTED_HARNESS_SHA256,
            "actual_sha256": harness_actual,
            "match": EXPECTED_HARNESS_SHA256 == harness_actual,
        },
        {
            "path": f"{SCORING_FREEZE.relative_to(ROOT).as_posix()}#scoring_files",
            "expected_sha256": EXPECTED_SCORING_SHA256,
            "actual_sha256": scoring_actual,
            "match": EXPECTED_SCORING_SHA256 == scoring_actual,
        },
        {
            "path": "evaluation/benchmark_v1_1_scoring.md",
            "expected_sha256": EXPECTED_RUBRIC_SHA256,
            "actual_sha256": actual_hashes["scoring_rubric_sha256"],
            "match": EXPECTED_RUBRIC_SHA256 == actual_hashes["scoring_rubric_sha256"],
        },
        {
            "path": METRIC_REGISTRY.relative_to(ROOT).as_posix(),
            "expected_sha256": EXPECTED_REGISTRY_SHA256,
            "actual_sha256": actual_hashes["metric_registry_sha256"],
            "match": EXPECTED_REGISTRY_SHA256 == actual_hashes["metric_registry_sha256"],
        },
        {
            "path": ONE_SHOT_RULES.relative_to(ROOT).as_posix(),
            "expected_sha256": EXPECTED_RULES_SHA256,
            "actual_sha256": actual_hashes["one_shot_rules_sha256"],
            "match": EXPECTED_RULES_SHA256 == actual_hashes["one_shot_rules_sha256"],
        },
        {
            "path": MATCHED_PROTOCOL.relative_to(ROOT).as_posix(),
            "expected_sha256": EXPECTED_PROTOCOL_SHA256,
            "actual_sha256": actual_hashes["matched_protocol_sha256"],
            "match": EXPECTED_PROTOCOL_SHA256 == actual_hashes["matched_protocol_sha256"],
        },
    ]
    if any(not item["match"] for item in shared_frozen_pin_audit):
        raise RuntimeError("FAIL CLOSED: shared frozen pin SHA-256 audit mismatch")
    identities = runner_freeze.get("shared_evaluation_identities", {})
    freeze_contract_sha = runner_freeze.get("identity_contracts", {}).get(contract_path)
    if (treatment_freeze.get("freeze_kind") != "TREATMENT_V2_DEVELOPMENT_FREEZE_NOT_EVALUATION_AUTHORIZATION" or
            treatment_freeze.get("status") != "FROZEN_AFTER_SYNTHETIC_AND_FULL_REGRESSION_PASS"):
        raise RuntimeError("FAIL CLOSED: treatment-v2 freeze status mismatch")
    if (runner_freeze.get("status") != "FROZEN_NOT_AUTHORIZED" or
            runner_freeze.get("freeze_kind") != "TREATMENT_IDENTITY_COMPATIBILITY_RUNNER_NOT_AUTHORIZATION" or
            runner_freeze.get("runner_path") != V2_RUNNER.relative_to(ROOT).as_posix() or
            runner_freeze.get("runner_sha256") != actual_hashes["v2_runner_sha256"] or
            freeze_contract_sha != actual_hashes["identity_contract_sha256"]):
        raise RuntimeError("FAIL CLOSED: V2 runner freeze or contract binding mismatch")

    contract_pins = {
        "treatment_agent_sha256": EXPECTED_AGENT_SHA256,
        "treatment_freeze_sha256": actual_hashes["treatment_freeze_sha256"],
        "benchmark_sha256": EXPECTED_BENCHMARK_SHA256,
        "benchmark_manifest_sha256": actual_hashes["benchmark_manifest_sha256"],
        "harness_sha256": EXPECTED_HARNESS_SHA256,
        "scoring_sha256": EXPECTED_SCORING_SHA256,
        "scoring_rubric_sha256": EXPECTED_RUBRIC_SHA256,
        "metric_registry_sha256": EXPECTED_REGISTRY_SHA256,
        "one_shot_rules_sha256": EXPECTED_RULES_SHA256,
        "matched_protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "case_order_fingerprint_sha256": identities.get("case_order_fingerprint_sha256"),
        "model_configuration_fingerprint_sha256": identities.get("model_configuration_fingerprint_sha256"),
        "rag_configuration_fingerprint_sha256": identities.get("rag_configuration_fingerprint_sha256"),
        "tool_adapter_sha256": identities.get("tool_adapter_sha256"),
        "dependency_lock_sha256": identities.get("dependency_lock_sha256"),
        "comparison_class": COMPARISON_CLASS,
        "benchmark_path": BENCHMARK.relative_to(ROOT).as_posix(),
        "max_runner_turns": identities.get("max_runner_turns"),
        "agent_loop_max_steps": identities.get("agent_loop_max_steps"),
        "fresh_session_per_case": identities.get("fresh_session_per_case"),
    }
    if contract.get("status") != "FROZEN_IDENTITY_CONTRACT_NOT_AUTHORIZATION":
        raise RuntimeError("FAIL CLOSED: V2 identity contract status mismatch")
    if contract.get("artifact_type") != "TREATMENT_V2_IDENTITY_CONTRACT_NOT_AUTHORIZATION":
        raise RuntimeError("FAIL CLOSED: V2 identity contract type mismatch")
    if (contract.get("evaluation_id") != EVALUATION_ID or contract.get("case_count") != 40 or
            contract.get("authorization_id") is not None or contract.get("attempt_id") is not None):
        raise RuntimeError("FAIL CLOSED: V2 evaluation identity or case count mismatch")
    if any(contract.get(key) != value for key, value in contract_pins.items()):
        raise RuntimeError("FAIL CLOSED: V2 contract identity pin mismatch")
    if identities.get("benchmark_path") != contract.get("benchmark_path"):
        raise RuntimeError("FAIL CLOSED: frozen benchmark path mismatch")

    required_authorization = {
        "status": "ISSUED_NOT_EXECUTED",
        "authorization_type": "ONE_SHOT_MATCHED_TREATMENT",
        "regression_purpose": "REGRESSION_ONLY_CONFIRMATION",
        "evaluation_id": EVALUATION_ID,
        "authorization_id": AUTHORIZATION_ID,
        "attempt_id": ATTEMPT_ID,
        "treatment_agent_sha256": EXPECTED_AGENT_SHA256,
        "baseline_agent_sha256": identities.get("baseline_agent_sha256"),
        "treatment_freeze_path": TREATMENT_FREEZE.relative_to(ROOT).as_posix(),
        "treatment_freeze_sha256": actual_hashes["treatment_freeze_sha256"],
        "treatment_runner_sha256": actual_hashes["v2_runner_sha256"],
        "treatment_runner_freeze_sha256": actual_hashes["runner_freeze_sha256"],
        "identity_contract_path": contract_path,
        "identity_contract_sha256": actual_hashes["identity_contract_sha256"],
        "benchmark_path": BENCHMARK.relative_to(ROOT).as_posix(),
        "benchmark_sha256": EXPECTED_BENCHMARK_SHA256,
        "benchmark_manifest_sha256": actual_hashes["benchmark_manifest_sha256"],
        "harness_sha256": EXPECTED_HARNESS_SHA256,
        "scoring_sha256": EXPECTED_SCORING_SHA256,
        "scoring_rubric_sha256": EXPECTED_RUBRIC_SHA256,
        "metric_registry_sha256": EXPECTED_REGISTRY_SHA256,
        "one_shot_rules_sha256": EXPECTED_RULES_SHA256,
        "matched_protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "model_configuration_fingerprint_sha256": identities.get("model_configuration_fingerprint_sha256"),
        "rag_configuration_fingerprint_sha256": identities.get("rag_configuration_fingerprint_sha256"),
        "tool_adapter_sha256": identities.get("tool_adapter_sha256"),
        "dependency_lock_sha256": identities.get("dependency_lock_sha256"),
        "case_count": 40,
        "case_order_fingerprint_sha256": contract.get("case_order_fingerprint_sha256"),
        "comparison_class": COMPARISON_CLASS,
        "max_formal_attempts": 1,
    }
    if any(authorization.get(key) != value for key, value in required_authorization.items()):
        raise RuntimeError("FAIL CLOSED: V2 authorization manifest identity mismatch")
    if authorization.get("consumed") is not False or authorization.get("attempt_created") is not False:
        raise RuntimeError("FAIL CLOSED: authorization issuance state is not pre-execution")
    if authorization_audit.get("authorization_status") != "ISSUED_NOT_EXECUTED":
        raise RuntimeError("FAIL CLOSED: V2 authorization audit status mismatch")
    if authorization_audit.get("audit_status") != "PASS_AUTHORIZED_NOT_EXECUTED":
        raise RuntimeError("FAIL CLOSED: V2 authorization audit did not pass")
    if authorization_audit.get("authorization_manifest_sha256") != actual_hashes["authorization_manifest_sha256"]:
        raise RuntimeError("FAIL CLOSED: V2 authorization audit manifest hash mismatch")
    audit_identity = authorization_audit.get("identity_resolution", {})
    if (audit_identity.get("authorization_id") != AUTHORIZATION_ID or
            audit_identity.get("attempt_id") != ATTEMPT_ID or
            audit_identity.get("evaluation_id") != EVALUATION_ID):
        raise RuntimeError("FAIL CLOSED: V2 authorization audit identity mismatch")

    if (actual_hashes["benchmark_sha256"] != EXPECTED_BENCHMARK_SHA256 or
            actual_hashes["harness_sha256"] != EXPECTED_HARNESS_SHA256 or
            not harness_files_match or harness_actual != EXPECTED_HARNESS_SHA256 or
            actual_hashes["scoring_sha256"] != EXPECTED_SCORING_SHA256 or
            not scoring_files_match or scoring_actual != EXPECTED_SCORING_SHA256 or
            actual_hashes["scoring_rubric_sha256"] != EXPECTED_RUBRIC_SHA256 or
            actual_hashes["metric_registry_sha256"] != EXPECTED_REGISTRY_SHA256 or
            actual_hashes["one_shot_rules_sha256"] != EXPECTED_RULES_SHA256 or
            actual_hashes["matched_protocol_sha256"] != EXPECTED_PROTOCOL_SHA256 or
            actual_hashes["benchmark_manifest_sha256"] != contract.get("benchmark_manifest_sha256")):
        raise RuntimeError("FAIL CLOSED: shared frozen evaluation identity mismatch")

    protocol_identity = protocol.get("identities", {})
    registry_plan = registry.get("planned_task_distribution", {})
    if (protocol.get("comparison_class") != COMPARISON_CLASS or
            protocol.get("design_classification", {}).get("case_count") != 40 or
            protocol.get("design_classification", {}).get("case_set_and_order_fingerprint_sha256") != contract.get("case_order_fingerprint_sha256") or
            protocol_identity.get("benchmark_v4_sha256") != EXPECTED_BENCHMARK_SHA256 or
            protocol_identity.get("harness_sha256") != EXPECTED_HARNESS_SHA256 or
            protocol_identity.get("scoring_aggregate_sha256") != EXPECTED_SCORING_SHA256 or
            protocol_identity.get("one_shot_rules_sha256") != EXPECTED_RULES_SHA256 or
            protocol_identity.get("paired_metric_registry_sha256") != EXPECTED_REGISTRY_SHA256 or
            registry_plan != TASK_DISTRIBUTION):
        raise RuntimeError("FAIL CLOSED: protocol or registry identity mismatch")

    return {
        "contract": contract,
        "treatment_freeze": treatment_freeze,
        "runner_freeze": runner_freeze,
        "authorization": authorization,
        "authorization_audit": authorization_audit,
        "pins": {
            **actual_hashes,
            "treatment_agent_sha256": EXPECTED_AGENT_SHA256,
            "comparison_class": COMPARISON_CLASS,
            "case_count": 40,
            "case_order_fingerprint_sha256": contract["case_order_fingerprint_sha256"],
            "model_configuration_fingerprint_sha256": contract["model_configuration_fingerprint_sha256"],
            "tool_adapter_sha256": contract["tool_adapter_sha256"],
            "rag_configuration_fingerprint_sha256": contract["rag_configuration_fingerprint_sha256"],
            "dependency_lock_sha256": contract["dependency_lock_sha256"],
            "shared_frozen_pin_audit": shared_frozen_pin_audit,
            "max_runner_turns": contract["max_runner_turns"],
            "agent_loop_max_steps": contract["agent_loop_max_steps"],
            "fresh_session_per_case": contract["fresh_session_per_case"],
        },
    }


def _collect_records(container: dict[str, Any], key: str, id_key: str) -> set[str]:
    value = container.get(key, [])
    if not isinstance(value, list):
        return set()
    return {
        item[id_key]
        for item in value
        if isinstance(item, dict) and isinstance(item.get(id_key), str) and item[id_key]
    }


def _has_nonempty_tool(event: dict[str, Any]) -> bool:
    if "tool" not in event or event["tool"] is None:
        return False
    value = event["tool"]
    return not isinstance(value, str) or bool(value.strip())


def derive(trace: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    """Reconstruct only links evidenced by persisted IDs; never invent IDs."""
    turns = trace.get("turns", [])
    if not isinstance(turns, list):
        turns = []
    decisions: dict[str, dict[str, Any]] = {}
    dependency_ids: set[str] = set()
    semantic_ids: set[str] = set()
    lineage_events: list[dict[str, Any]] = []

    for turn in turns:
        if not isinstance(turn, dict):
            continue
        state = turn.get("state", {})
        if not isinstance(state, dict):
            state = {}
        dependency_ids.update(_collect_records(state, "dependencies_considered", "dependency_id"))
        semantic_ids.update(_collect_records(state, "semantic_provenance", "semantic_id"))
        state_events = state.get("lineage_events", [])
        if isinstance(state_events, list):
            lineage_events.extend(event for event in state_events if isinstance(event, dict))

        snapshots = turn.get("state_history", [])
        if not isinstance(snapshots, list):
            snapshots = []
        for snapshot in snapshots:
            if not isinstance(snapshot, dict):
                continue
            dependency_ids.update(_collect_records(snapshot, "dependencies_considered", "dependency_id"))
            semantic_ids.update(_collect_records(snapshot, "semantic_provenance", "semantic_id"))
            if snapshot.get("event") == "DECISION":
                chosen = snapshot.get("chosen_action", {})
                if isinstance(chosen, dict) and isinstance(chosen.get("candidate_id"), str) and chosen["candidate_id"]:
                    decisions[chosen["candidate_id"]] = snapshot

    final = trace.get("final_state", {})
    if not isinstance(final, dict):
        final = {}
    dependency_ids.update(_collect_records(final, "dependencies_considered", "dependency_id"))
    semantic_ids.update(_collect_records(final, "semantic_provenance", "semantic_id"))
    actions = final.get("action_history", [])
    if not isinstance(actions, list):
        actions = []
    missing: list[str] = []

    for action in actions:
        if not isinstance(action, dict):
            missing.append("MALFORMED_ACTION_RECORD")
            continue
        candidate_id = action.get("selected_candidate_id")
        decision = decisions.get(candidate_id) if isinstance(candidate_id, str) else None
        if decision is None:
            missing.append("MISSING_CANDIDATE_DECISION_LINK")
            continue
        chosen = decision.get("chosen_action", {})
        if not isinstance(chosen, dict):
            missing.append("MALFORMED_DECISION_ACTION")
            chosen = {}
        source_dependency_id = chosen.get("source_dependency_id")
        if source_dependency_id is not None and (
            not isinstance(source_dependency_id, str) or source_dependency_id not in dependency_ids
        ):
            missing.append("MISSING_DEPENDENCY_LINK")
        if (chosen.get("origin") == "HARD_PRECONDITION" and
                not (isinstance(chosen.get("source_precondition_id"), str) and
                     chosen.get("source_precondition_id"))):
            missing.append("MISSING_SOURCE_ID")

        action_kind = action.get("action")
        if action_kind in {"RETRIEVE", "READ_DIARY"}:
            action_id = action.get("action_id")
            linked = [event for event in lineage_events if event.get("source_action_id") == action_id]
            complete_links = [event for event in linked if event.get("tool_result_id") and event.get("state_update_id")]
            if not complete_links:
                missing.append("MISSING_TOOL_RESULT_LINK")
            required_source = "RAG" if action_kind == "RETRIEVE" else "session_diary"
            source_links = [event for event in complete_links if event.get("source_type") == required_source]
            if action_kind == "RETRIEVE" and not source_links:
                missing.append("MISSING_RETRIEVAL_PROVENANCE")
            if action_kind == "READ_DIARY" and not source_links:
                missing.append("MISSING_DIARY_PROVENANCE")
            if not any(_has_nonempty_tool(event) for event in source_links):
                missing.append("MISSING_TOOL_IDENTITY")

    if not final.get("goal_id"):
        missing.append("MISSING_GOAL_ROOT")
    if not semantic_ids:
        missing.append("MISSING_SEMANTIC_ROOT")
    if not dependency_ids:
        missing.append("MISSING_DEPENDENCY_ROOT")

    graph = {
        "goal_root_id": final.get("goal_id"),
        "semantic_root_ids": sorted(semantic_ids),
        "dependency_roots": sorted(dependency_ids),
        "decisions": decisions,
        "lineage_events": lineage_events,
        "actions": actions,
    }
    return sorted(set(missing)), graph


def validate_formal_execution(
    ledger: list[dict[str, Any]],
    results: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    contract: dict[str, Any],
) -> list[str]:
    if len(results) != 40 or len(traces) != 40:
        raise RuntimeError("FAIL CLOSED: formal result/trace counts must both be 40")
    result_ids = [row.get("case_id") for row in results]
    trace_ids = [row.get("case_id") for row in traces]
    if (any(not isinstance(case_id, str) or not case_id for case_id in result_ids + trace_ids) or
            len(set(result_ids)) != 40 or len(set(trace_ids)) != 40 or result_ids != trace_ids):
        raise RuntimeError("FAIL CLOSED: result/trace case IDs must be unique, equal, and ordered alike")
    if any(row.get("evaluation_id") != EVALUATION_ID or
           row.get("score_status") != "PENDING_FROZEN_RUBRIC_REVIEW" for row in results):
        raise RuntimeError("FAIL CLOSED: result evaluation identity or score status mismatch")
    if any(row.get("evaluation_id") != EVALUATION_ID for row in traces):
        raise RuntimeError("FAIL CLOSED: raw trace evaluation identity mismatch")

    task_counts = Counter(row.get("task_type") for row in results)
    if dict(task_counts) != TASK_DISTRIBUTION:
        raise RuntimeError("FAIL CLOSED: formal task distribution is not frozen 10/10/10/10")
    order_payload = "\n".join(result_ids).encode("utf-8")
    if (len(result_ids) != contract.get("case_count") or
            sha256_bytes(order_payload) != contract.get("case_order_fingerprint_sha256")):
        raise RuntimeError("FAIL CLOSED: formal case set/order fingerprint mismatch")

    if not ledger:
        raise RuntimeError("FAIL CLOSED: formal ledger is empty")
    for event in ledger:
        if (event.get("evaluation_id") != EVALUATION_ID or
                event.get("authorization_id") != AUTHORIZATION_ID or
                event.get("attempt_id") != ATTEMPT_ID or
                event.get("comparison_class") != COMPARISON_CLASS):
            raise RuntimeError("FAIL CLOSED: ledger contains a foreign execution identity")
    required_once = (
        "PREPARED", "AUTHORIZATION_CONSUMED", "FIRST_EVALUATION_ACCESS",
        "CASE_SET_AND_ORDER_VERIFIED", "COMPLETED",
    )
    for status in required_once:
        if sum(event.get("status") == status for event in ledger) != 1:
            raise RuntimeError(f"FAIL CLOSED: ledger must contain exactly one {status}")
    status_sequence = [event.get("status") for event in ledger]
    if not (status_sequence.index("PREPARED") < status_sequence.index("AUTHORIZATION_CONSUMED") <
            status_sequence.index("FIRST_EVALUATION_ACCESS") <
            status_sequence.index("CASE_SET_AND_ORDER_VERIFIED") < status_sequence.index("COMPLETED")):
        raise RuntimeError("FAIL CLOSED: one-shot ledger event ordering mismatch")
    first_access = next(event for event in ledger if event.get("status") == "FIRST_EVALUATION_ACCESS")
    if first_access.get("dataset_sha256") != EXPECTED_BENCHMARK_SHA256:
        raise RuntimeError("FAIL CLOSED: ledger first-access benchmark hash mismatch")
    case_set_event = next(event for event in ledger if event.get("status") == "CASE_SET_AND_ORDER_VERIFIED")
    if (case_set_event.get("case_count") != 40 or
            case_set_event.get("case_order_fingerprint_sha256") != contract.get("case_order_fingerprint_sha256")):
        raise RuntimeError("FAIL CLOSED: ledger case-set/order verification mismatch")

    attempt_starts = [event for event in ledger if event.get("status") == "STARTED" and event.get("scope") == "ATTEMPT"]
    case_starts = [event for event in ledger if event.get("status") == "STARTED" and event.get("scope") == "CASE"]
    completions = [event for event in ledger if event.get("status") == "CASE_COMPLETED"]
    if len(attempt_starts) != 1 or len(case_starts) != 40 or len(completions) != 40:
        raise RuntimeError("FAIL CLOSED: ledger attempt/case start or completion count mismatch")
    if ([event.get("case_id") for event in case_starts] != result_ids or
            [event.get("case_id") for event in completions] != result_ids):
        raise RuntimeError("FAIL CLOSED: ledger case START/COMPLETED order differs from results")
    for case_id in result_ids:
        start_index = next(i for i, event in enumerate(ledger)
                           if event.get("status") == "STARTED" and event.get("scope") == "CASE" and
                           event.get("case_id") == case_id)
        completed_index = next(i for i, event in enumerate(ledger)
                               if event.get("status") == "CASE_COMPLETED" and event.get("case_id") == case_id)
        if start_index >= completed_index:
            raise RuntimeError(f"FAIL CLOSED: case completion precedes its start: {case_id}")
    final = ledger[-1]
    if (final.get("status") != "COMPLETED" or final.get("cases_started") != 40 or
            final.get("cases_completed") != 40):
        raise RuntimeError("FAIL CLOSED: ledger final state is not COMPLETED 40/40")
    return result_ids


def build_forensics(
    execution_bytes: dict[Path, bytes],
    identities: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    ledger = parse_jsonl(execution_bytes[LEDGER], LEDGER.name)
    results = parse_jsonl(execution_bytes[RESULTS], RESULTS.name)
    traces = parse_jsonl(execution_bytes[TRACES], TRACES.name)
    case_order = validate_formal_execution(ledger, results, traces, identities["contract"])
    results_by_id = {row["case_id"]: row for row in results}
    traces_by_id = {row["case_id"]: row for row in traces}
    matrix: list[dict[str, Any]] = []
    sidecar: list[dict[str, Any]] = []

    for case_id in case_order:
        result, trace = results_by_id[case_id], traces_by_id[case_id]
        missing, graph = derive(trace)
        formal_ready = result.get("lineage_ready")
        if type(formal_ready) is not bool:
            raise RuntimeError(f"FAIL CLOSED: formal lineage flag is not boolean: {case_id}")
        if not missing:
            recomputed = "COMPLETE"
            root_cause = "NO_FAILURE" if formal_ready else "RUNNER_DERIVATION_BUG"
            sidecar_status = "COMPLETE_FORMAL" if formal_ready else "COMPLETE_DERIVED"
        elif "MISSING_SEMANTIC_ROOT" in missing:
            recomputed = "INCOMPLETE"
            root_cause = "TRUE_LINEAGE_FAILURE"
            sidecar_status = "INCOMPLETE_FORMAL"
        else:
            recomputed = "INDETERMINATE"
            root_cause = "INDETERMINATE"
            sidecar_status = "INDETERMINATE"

        if recomputed == "COMPLETE":
            dimensions = {name: "SCORABLE" for name in DIMENSIONS}
            eligibility = "FULL"
        else:
            evidence = classify_true_failure_dimensions(trace)
            dimensions = evidence["dimensions"]
            eligibility = evidence["eligibility"]
        if not trace.get("final_answer") and not result.get("answer"):
            eligibility = "NONE"
        elif eligibility not in {"FULL", "PARTIAL"}:
            raise RuntimeError(f"FAIL CLOSED: unexpected eligibility classification: {case_id}")

        raw_ref = line_reference(TRACES, execution_bytes[TRACES], case_id)
        result_ref = line_reference(RESULTS, execution_bytes[RESULTS], case_id)
        action_links: list[dict[str, Any]] = []
        for action in graph["actions"]:
            if not isinstance(action, dict):
                continue
            candidate_id = action.get("selected_candidate_id")
            decision = graph["decisions"].get(candidate_id, {})
            chosen = decision.get("chosen_action", {}) if isinstance(decision, dict) else {}
            if not isinstance(chosen, dict):
                chosen = {}
            links = [event for event in graph["lineage_events"]
                     if event.get("source_action_id") == action.get("action_id")]
            action_links.append({
                "action_id": action.get("action_id"),
                "action": action.get("action"),
                "candidate_id": candidate_id if candidate_id in graph["decisions"] else None,
                "candidate_decision_link_present": candidate_id in graph["decisions"],
                "origin": chosen.get("origin"),
                "source_precondition_id": chosen.get("source_precondition_id"),
                "source_dependency_id": chosen.get("source_dependency_id"),
                "tool_result_state_update_links": [
                    {key: event.get(key) for key in
                     ("tool_result_id", "state_update_id", "source_type", "tool")}
                    for event in links
                ],
            })

        matrix.append({
            "case_id": case_id,
            "task_type": result.get("task_type"),
            "lineage_ready_frozen": formal_ready,
            "action_path": trace.get("action_path", []),
            "ASK_count": result.get("ASK_count"),
            "RETRIEVE_count": result.get("RETRIEVE_count"),
            "READ_DIARY_count": result.get("READ_DIARY_count"),
            "tool_calls": result.get("tool_calls", []),
            "turn_count": result.get("turn_count"),
            "step_count": result.get("step_count"),
            "final_status": result.get("final_status"),
            "score_status": result.get("score_status"),
            "raw_trace_present": True,
            "case_result_present": True,
            "raw_trace_provenance": raw_ref,
            "case_result_provenance": result_ref,
            "recomputed_lineage_status": recomputed,
            "reason_codes": missing,
            "root_cause_class": root_cause,
            "adjudication_eligibility": eligibility,
            "dimension_evidence": dimensions,
        })
        sidecar.append({
            "case_id": case_id,
            "formal_lineage_ready": formal_ready,
            "recomputed_lineage_status": recomputed,
            "root_cause_class": root_cause,
            "sidecar_lineage_status": sidecar_status,
            "lineage_reconstructed": sidecar_status == "COMPLETE_DERIVED",
            "reconstruction_source": {
                "raw_trace_line": raw_ref,
                "reconstruction_method": "join persisted final_state.action_history to persisted DECISION snapshots; preserve recorded IDs only",
            },
            "reason_codes": missing,
            "semantic_root_status": "PRESENT" if graph["semantic_root_ids"] else "MISSING_IN_FORMAL_TRACE",
            "adjudication_lineage_status": (
                "INCOMPLETE" if sidecar_status in {"INCOMPLETE_FORMAL", "INDETERMINATE"} else "COMPLETE"
            ),
            "lineage_graph": {
                "goal_root_id": graph["goal_root_id"],
                "semantic_root_ids": graph["semantic_root_ids"],
                "dependency_roots": [{"dependency_id": dep} for dep in graph["dependency_roots"]],
                "action_candidate_links": action_links,
            },
            "trace_provenance": raw_ref,
            "reviewer_scores_populated": False,
        })

    return ledger, matrix, sidecar, {"results": results, "traces": traces, "case_order": case_order}


def output_documents(
    execution_bytes: dict[Path, bytes],
    identities: dict[str, Any],
    ledger: list[dict[str, Any]],
    matrix: list[dict[str, Any]],
    sidecar: list[dict[str, Any]],
    parsed: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], str]:
    pins = identities["pins"]
    records = [file_record(path, execution_bytes[path]) for path in (LEDGER, RESULTS, TRACES)]
    freeze = {
        "step": "9.45a",
        "freeze_type": "TREATMENT_V2_READ_ONLY_FORMAL_INPUTS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_id": EVALUATION_ID,
        "authorization_id": AUTHORIZATION_ID,
        "attempt_id": ATTEMPT_ID,
        "comparison_class": COMPARISON_CLASS,
        "artifact_files": records,
        "identity_artifacts": {
            "treatment_v2_freeze_path": TREATMENT_FREEZE.relative_to(ROOT).as_posix(),
            "treatment_v2_freeze_sha256": pins["treatment_freeze_sha256"],
            "identity_contract_path": IDENTITY_CONTRACT.relative_to(ROOT).as_posix(),
            "identity_contract_sha256": pins["identity_contract_sha256"],
            "runner_freeze_path": RUNNER_FREEZE.relative_to(ROOT).as_posix(),
            "runner_freeze_sha256": pins["runner_freeze_sha256"],
            "authorization_manifest_path": AUTHORIZATION.relative_to(ROOT).as_posix(),
            "authorization_manifest_sha256": pins["authorization_manifest_sha256"],
            "authorization_audit_path": AUTHORIZATION_AUDIT.relative_to(ROOT).as_posix(),
            "authorization_audit_sha256": pins["authorization_audit_sha256"],
        },
        "shared_evaluation_identities": {
            key: pins[key] for key in (
                "benchmark_sha256", "benchmark_manifest_sha256", "harness_sha256",
                "scoring_sha256", "scoring_rubric_sha256", "metric_registry_sha256",
                "one_shot_rules_sha256", "matched_protocol_sha256",
                "adjudication_schema_sha256", "case_count", "case_order_fingerprint_sha256",
                "model_configuration_fingerprint_sha256", "tool_adapter_sha256",
                "rag_configuration_fingerprint_sha256", "dependency_lock_sha256",
                "max_runner_turns", "agent_loop_max_steps", "fresh_session_per_case",
            )
        },
        "shared_frozen_pins": pins["shared_frozen_pin_audit"],
        "formal_inputs_read_only": True,
    }

    formal_true = sum(row["lineage_ready_frozen"] is True for row in matrix)
    formal_false = sum(row["lineage_ready_frozen"] is False for row in matrix)
    recomputed_counts = Counter(row["recomputed_lineage_status"] for row in matrix)
    root_counts = Counter(row["root_cause_class"] for row in matrix)
    eligibility_counts = Counter(row["adjudication_eligibility"] for row in matrix)
    task_counts = Counter(row["task_type"] for row in matrix)
    audit = {
        "step": "9.45a",
        "forensic_type": "READ_ONLY_TREATMENT_V2_LINEAGE_FORENSICS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_id": EVALUATION_ID,
        "authorization_id": AUTHORIZATION_ID,
        "attempt_id": ATTEMPT_ID,
        "comparison_class": COMPARISON_CLASS,
        "attempt_status": ledger[-1]["status"],
        "formal_case_count": len(matrix),
        "case_result_count": len(parsed["results"]),
        "raw_trace_count": len(parsed["traces"]),
        "case_id_order_preserved": True,
        "case_order_fingerprint_sha256": pins["case_order_fingerprint_sha256"],
        "task_distribution": dict(sorted(task_counts.items())),
        "formal_lineage_ready_count": formal_true,
        "formal_lineage_false_count": formal_false,
        "recomputed_lineage_counts": {
            key: recomputed_counts[key] for key in ("COMPLETE", "INCOMPLETE", "INDETERMINATE")
        },
        "root_cause_counts": {
            key: root_counts[key] for key in ("NO_FAILURE", "RUNNER_DERIVATION_BUG", "TRUE_LINEAGE_FAILURE", "INDETERMINATE")
        },
        "adjudication_eligibility_counts": {
            key: eligibility_counts[key] for key in ("FULL", "PARTIAL", "NONE")
        },
        "trace_contract": (
            "Every action links to a persisted DECISION candidate; source dependencies resolve; HARD_PRECONDITION "
            "actions carry a source precondition; RETRIEVE/READ_DIARY actions link to lineage events with tool and "
            "state IDs plus RAG/session_diary provenance; goal, semantic, and dependency roots are present. "
            "No identifiers are synthesized."
        ),
        "adjudication_eligibility_contract": (
            "COMPLETE lineage is FULL with all five dimensions SCORABLE. For incomplete lineage, the frozen "
            "trace-evidence classifier determines FULL/PARTIAL; no final answer in either trace or result yields NONE. "
            "Eligibility is not a score."
        ),
        "no_scoring": True,
        "no_adjudication": True,
        "no_aggregate": True,
        "no_overall": True,
        "no_baseline_comparison": True,
        "no_rerun": True,
        "no_model_agent_rag_execution": True,
        "no_v5_access": True,
        "no_missing_semantic_root_synthesized": True,
        "formal_artifacts_modified": False,
        "case_results_sha256_at_start": sha256_bytes(execution_bytes[RESULTS]),
        "raw_traces_sha256_at_start": sha256_bytes(execution_bytes[TRACES]),
        "shared_frozen_pins": pins["shared_frozen_pin_audit"],
    }

    md = [
        "# Step 9.45a — Treatment-v2 Lineage Forensics",
        "",
        "Read-only forensic step for the explicitly pinned treatment-v2 execution. Formal ledger, results, and traces were hash-checked before parsing and are never modified.",
        "",
        f"Evaluation `{EVALUATION_ID}`; attempt `{ATTEMPT_ID}`; status **{ledger[-1]['status']}**. Formal results/traces: **{len(parsed['results'])}/{len(parsed['traces'])}**. Task distribution: " + ", ".join(f"{key}={task_counts[key]}" for key in sorted(TASK_DISTRIBUTION)) + ".",
        "",
        f"Formal lineage ready={formal_true}; false={formal_false}. Recomputed lineage: COMPLETE={recomputed_counts['COMPLETE']}, INCOMPLETE={recomputed_counts['INCOMPLETE']}, INDETERMINATE={recomputed_counts['INDETERMINATE']}.",
        "",
        f"Root classifications: NO_FAILURE={root_counts['NO_FAILURE']}, RUNNER_DERIVATION_BUG={root_counts['RUNNER_DERIVATION_BUG']}, TRUE_LINEAGE_FAILURE={root_counts['TRUE_LINEAGE_FAILURE']}, INDETERMINATE={root_counts['INDETERMINATE']}.",
        "",
        f"Adjudication eligibility (not scoring): FULL={eligibility_counts['FULL']}, PARTIAL={eligibility_counts['PARTIAL']}, NONE={eligibility_counts['NONE']}. Reviewer scores were not populated.",
        "",
        "The deterministic derivation joins existing `final_state.action_history` IDs to persisted DECISION snapshots, dependencies, semantics, and lineage events. No candidate, dependency, or semantic identifier was generated, repaired, inferred, or guessed. Missing semantic roots remain missing.",
        "",
        "No scoring, adjudication, aggregation, Overall, baseline comparison, rerun, model/Agent/RAG execution, or V5 access occurred. This report makes no performance or comparative claim.",
        "",
        f"Start-of-step hashes: case results `{sha256_bytes(execution_bytes[RESULTS])}`; raw traces `{sha256_bytes(execution_bytes[TRACES])}`. The script rechecks both files against the starting bytes before exit.",
        "",
        "## Shared frozen pin SHA-256 audit",
        "",
        *[
            f"- `{item['path']}`: EXPECTED_SHA=`{item['expected_sha256']}`; ACTUAL_SHA=`{item['actual_sha256']}`; MATCH=`{str(item['match']).upper()}`"
            for item in pins["shared_frozen_pin_audit"]
        ],
        "",
        "Input freeze: `step9_45a_v2_run_input_freeze.json`.",
        "",
    ]
    return freeze, audit, "\n".join(md)


def write_exclusive(path: Path, data: str) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(data)
        stream.flush()


def main() -> None:
    execution_bytes = initial_execution_hash_gate()
    try:
        if any(path.exists() for path in OUTFILES):
            raise RuntimeError("FAIL CLOSED: a Step 9.45a output already exists")
        identities = verify_v2_identities()
        if sha256_file(ADJUDICATION_SCHEMA) != EXPECTED_SCHEMA_SHA256:
            raise RuntimeError("FAIL CLOSED: adjudication schema hash changed")
        ledger, matrix, sidecar, parsed = build_forensics(execution_bytes, identities)
        freeze, audit, report = output_documents(execution_bytes, identities, ledger, matrix, sidecar, parsed)

        # Refuse to publish outputs if formal bytes changed during parsing.
        ending_hashes = verify_execution_unchanged(execution_bytes)
        for key, path in (("case_results_sha256_end", RESULTS), ("raw_traces_sha256_end", TRACES)):
            audit[key] = ending_hashes[path.relative_to(ROOT).as_posix()]

        write_exclusive(OUTFILES[0], json.dumps(freeze, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        write_exclusive(OUTFILES[1], json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        write_exclusive(OUTFILES[2], report)
        write_exclusive(OUTFILES[3], "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in matrix))
        write_exclusive(OUTFILES[4], "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in sidecar))
        verify_execution_unchanged(execution_bytes)
    finally:
        # This runs after success or any failed forensic check.
        verify_execution_unchanged(execution_bytes)


if __name__ == "__main__":
    main()
