"""Step 9.43a identity-contract adapter over the frozen 9.35a runner.

This module only validates treatment identity and authorization bindings. Once
authorized, case execution is delegated unchanged to the Step 9.35a runner.
Importing it never reads benchmark cases or creates a run namespace.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FREEZE_DIR = ROOT / "evaluation" / "v1_2_3"
RUNNER_FREEZE_PATH = FREEZE_DIR / "step9_43a_treatment_v2_runner_freeze.json"
LEGACY_RUNNER_SHA256 = "920486b1d7984fae6ee77b5ac51af0d0a98caf42e445d1abcf7ff75b46038505"
LEGACY_RUNNER_FREEZE_SHA256 = "0c4e6ab752164bfe436d14b06d3bdc6d5cfc1506cbca92bc1bb9675c437aa7e9"
EXPECTED_TREATMENT_V2_AGENT_SHA256 = "b9e891e7cd077dd5b3c6fa72b71faad978a24226c2b5e89e0b06aabde93b51d6"
IDENTITY_CONTRACTS = {
    "evaluation/v1_2_3/step9_43a_treatment_v1_identity_contract.json",
    "evaluation/v1_2_3/step9_43a_treatment_v2_identity_contract.json",
}
REQUIRED_CONTRACT_FIELDS = (
    "evaluation_id", "treatment_agent_sha256", "treatment_freeze_path",
    "treatment_freeze_sha256", "benchmark_sha256", "harness_sha256",
    "scoring_sha256", "metric_registry_sha256", "one_shot_rules_sha256",
    "matched_protocol_sha256", "comparison_class", "benchmark_path",
    "case_order_fingerprint_sha256",
)
SHA_FIELDS = (
    "treatment_agent_sha256", "treatment_freeze_sha256", "benchmark_sha256",
    "benchmark_manifest_sha256", "baseline_agent_sha256", "harness_sha256",
    "scoring_sha256", "scoring_rubric_sha256", "metric_registry_sha256",
    "one_shot_rules_sha256", "matched_protocol_sha256",
    "baseline_metric_lock_sha256", "claim_policy_sha256",
    "model_configuration_fingerprint_sha256", "rag_configuration_fingerprint_sha256",
    "tool_adapter_sha256", "dependency_lock_sha256",
    "case_order_fingerprint_sha256",
)
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path.name}")
    return value


def validate_contract_shape(contract: dict[str, Any], allowed_contract_paths: set[str],
                            contract_path: str) -> None:
    if contract_path not in allowed_contract_paths:
        raise RuntimeError("unknown, mutable, or latest identity contract path")
    if contract.get("status") != "FROZEN_IDENTITY_CONTRACT_NOT_AUTHORIZATION":
        raise RuntimeError("identity contract is not frozen or is executable")
    if contract_path.endswith("treatment_v2_identity_contract.json"):
        if (contract.get("artifact_type") != "TREATMENT_V2_IDENTITY_CONTRACT_NOT_AUTHORIZATION" or
                contract.get("treatment_agent_sha256") != EXPECTED_TREATMENT_V2_AGENT_SHA256):
            raise RuntimeError("treatment-v2 identity contract pin mismatch")
    if contract_path.endswith("treatment_v1_identity_contract.json") and contract.get(
            "artifact_type") != "EXPLICIT_HISTORICAL_TREATMENT_V1_IDENTITY_CONTRACT_NOT_AUTHORIZATION":
        raise RuntimeError("historical treatment-v1 identity contract type mismatch")
    if contract.get("authorization_id") is not None or contract.get("attempt_id") is not None:
        raise RuntimeError("identity contract must not pre-issue authorization or attempt IDs")
    missing = [name for name in REQUIRED_CONTRACT_FIELDS if name not in contract]
    if missing:
        raise RuntimeError("identity contract missing required field: " + ",".join(missing))
    if any(not isinstance(contract.get(name), str) or not contract[name] for name in REQUIRED_CONTRACT_FIELDS):
        raise RuntimeError("identity contract has absent or invalid required identity field")
    if not isinstance(contract.get("case_count"), int) or contract["case_count"] <= 0:
        raise RuntimeError("identity contract has invalid case_count")
    if not isinstance(contract.get("max_runner_turns"), int) or not isinstance(contract.get("agent_loop_max_steps"), int):
        raise RuntimeError("identity contract has invalid execution limits")
    if contract.get("fresh_session_per_case") is not True:
        raise RuntimeError("identity contract session isolation mismatch")
    if any(contract[name] in {"latest", "current", "default"} for name in
           ("treatment_freeze_path", "evaluation_id")):
        raise RuntimeError("mutable identity alias is forbidden")
    if not SAFE_ID.fullmatch(contract["evaluation_id"]):
        raise RuntimeError("invalid evaluation_id")
    for name in SHA_FIELDS:
        value = contract.get(name)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise RuntimeError(f"missing or invalid pinned hash: {name}")


def validate_agent_identity(contract: dict[str, Any], observed_agent_sha256: str) -> None:
    if observed_agent_sha256 != contract.get("treatment_agent_sha256"):
        raise RuntimeError("current Agent does not match explicit treatment identity contract")
    if observed_agent_sha256 == contract.get("baseline_agent_sha256"):
        raise RuntimeError("baseline Agent cannot be supplied as treatment")


def validate_authorization_bindings(contract: dict[str, Any], authorization: dict[str, Any],
                                    *, evaluation_id: str, authorization_id: str,
                                    attempt_id: str, supplied: dict[str, str],
                                    contract_path: str, contract_sha256: str,
                                    runner_sha256: str, runner_freeze_sha256: str) -> None:
    for name, value in (("evaluation_id", evaluation_id),
                        ("authorization_id", authorization_id), ("attempt_id", attempt_id)):
        if not SAFE_ID.fullmatch(value) or authorization.get(name) != value:
            raise RuntimeError(f"authorization {name} mismatch or invalid")
    if evaluation_id != contract["evaluation_id"]:
        raise RuntimeError("authorization evaluation_id differs from identity contract")
    if authorization.get("status") != "ISSUED_NOT_EXECUTED":
        raise RuntimeError("authorization is not issued")
    if authorization.get("authorization_type") != "ONE_SHOT_MATCHED_TREATMENT":
        raise RuntimeError("authorization type mismatch")
    if authorization.get("consumed") is not False or authorization.get("consumed_at_utc") is not None:
        raise RuntimeError("authorization is consumed or consumption state is missing")
    if authorization.get("max_formal_attempts") != 1 or not authorization.get("authorized_by"):
        raise RuntimeError("one-shot authorization issuer/attempt contract invalid")
    for name in ("treatment_freeze_path", "treatment_freeze_sha256", "treatment_agent_sha256",
                 "identity_contract_path", "identity_contract_sha256", "treatment_runner_sha256",
                 "treatment_runner_freeze_sha256", "comparison_class", "baseline_agent_sha256",
                 "benchmark_path", "benchmark_sha256", "benchmark_manifest_sha256", "harness_sha256",
                 "scoring_sha256", "scoring_rubric_sha256", "metric_registry_sha256",
                 "one_shot_rules_sha256", "matched_protocol_sha256", "baseline_metric_lock_sha256",
                 "claim_policy_sha256", "model_configuration_fingerprint_sha256",
                 "rag_configuration_fingerprint_sha256", "tool_adapter_sha256",
                 "dependency_lock_sha256", "case_order_fingerprint_sha256", "max_runner_turns",
                 "agent_loop_max_steps", "fresh_session_per_case"):
        expected = {
            "treatment_freeze_path": contract["treatment_freeze_path"],
            "treatment_freeze_sha256": contract["treatment_freeze_sha256"],
            "treatment_agent_sha256": contract["treatment_agent_sha256"],
            "identity_contract_path": contract_path,
            "identity_contract_sha256": contract_sha256,
            "treatment_runner_sha256": runner_sha256,
            "treatment_runner_freeze_sha256": runner_freeze_sha256,
            "comparison_class": contract["comparison_class"],
            "baseline_agent_sha256": contract["baseline_agent_sha256"],
            "benchmark_path": contract["benchmark_path"],
            "benchmark_sha256": contract["benchmark_sha256"],
            "benchmark_manifest_sha256": contract["benchmark_manifest_sha256"],
            "harness_sha256": contract["harness_sha256"],
            "scoring_sha256": contract["scoring_sha256"],
            "scoring_rubric_sha256": contract["scoring_rubric_sha256"],
            "metric_registry_sha256": contract["metric_registry_sha256"],
            "one_shot_rules_sha256": contract["one_shot_rules_sha256"],
            "matched_protocol_sha256": contract["matched_protocol_sha256"],
            "baseline_metric_lock_sha256": contract["baseline_metric_lock_sha256"],
            "claim_policy_sha256": contract["claim_policy_sha256"],
            "model_configuration_fingerprint_sha256": contract["model_configuration_fingerprint_sha256"],
            "rag_configuration_fingerprint_sha256": contract["rag_configuration_fingerprint_sha256"],
            "tool_adapter_sha256": contract["tool_adapter_sha256"],
            "dependency_lock_sha256": contract["dependency_lock_sha256"],
            "case_order_fingerprint_sha256": contract["case_order_fingerprint_sha256"],
            "max_runner_turns": contract["max_runner_turns"],
            "agent_loop_max_steps": contract["agent_loop_max_steps"],
            "fresh_session_per_case": contract["fresh_session_per_case"],
        }[name]
        if authorization.get(name) != expected:
            raise RuntimeError(f"authorization {name} mismatch")
    if authorization.get("case_count") != contract["case_count"]:
        raise RuntimeError("authorization case_count mismatch")
    for name in ("treatment_agent_sha256", "benchmark_sha256", "harness_sha256",
                 "scoring_sha256", "metric_registry_sha256", "one_shot_rules_sha256",
                 "matched_protocol_sha256"):
        if supplied.get(name) != contract[name]:
            raise RuntimeError(f"supplied {name} differs from identity contract")


def load_verified_identity(contract_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Verify runner freeze, explicit contract, Agent inventory, and infra pins."""
    from scripts import run_step9_35a_matched_treatment as legacy

    freeze = read_json(RUNNER_FREEZE_PATH)
    runner_sha = sha256_file(Path(__file__))
    if freeze.get("status") != "FROZEN_NOT_AUTHORIZED" or freeze.get("runner_sha256") != runner_sha:
        raise RuntimeError("Step 9.43a runner freeze mismatch")
    if (freeze.get("parent_runner_sha256") != LEGACY_RUNNER_SHA256 or
            freeze.get("parent_runner_freeze_sha256") != LEGACY_RUNNER_FREEZE_SHA256):
        raise RuntimeError("unexpected parent runner identity")
    test_path = ROOT / freeze["runner_test_path"]
    if sha256_file(test_path) != freeze.get("runner_test_sha256"):
        raise RuntimeError("runner contract test hash mismatch")
    parent_path = ROOT / freeze["parent_runner_path"]
    parent_freeze_path = ROOT / freeze["parent_runner_freeze_path"]
    if (sha256_file(parent_path) != freeze.get("parent_runner_sha256") or
            sha256_file(parent_freeze_path) != freeze.get("parent_runner_freeze_sha256")):
        raise RuntimeError("parent Step 9.35a runner identity mismatch")
    production_path = ROOT / "scripts" / "run_step9_28_v4_heldout.py"
    if sha256_file(production_path) != freeze.get("production_case_path_runner_sha256"):
        raise RuntimeError("production case-path runner identity mismatch")
    try:
        rel = contract_path.resolve().relative_to(ROOT).as_posix()
    except ValueError as error:
        raise RuntimeError("identity contract must be repository-relative") from error
    allowed = freeze.get("identity_contracts", {})
    if rel not in allowed or rel not in IDENTITY_CONTRACTS:
        raise RuntimeError("unknown, mutable, or latest identity contract path")
    contract_sha = sha256_file(contract_path)
    if contract_sha != allowed[rel]:
        raise RuntimeError("identity contract hash mismatch")
    contract = read_json(contract_path)
    validate_contract_shape(contract, set(allowed), rel)
    treatment_freeze_path = ROOT / contract["treatment_freeze_path"]
    if sha256_file(treatment_freeze_path) != contract["treatment_freeze_sha256"]:
        raise RuntimeError("treatment freeze hash mismatch")
    agent_freeze = read_json(treatment_freeze_path)
    rows = agent_freeze.get("agent_behavior_files")
    actual_aggregate = agent_freeze.get("treatment_v2_agent_sha256") or agent_freeze.get("treatment_agent_aggregate_sha256")
    if actual_aggregate != contract["treatment_agent_sha256"] or not legacy._verify_inventory(
            rows, contract["treatment_agent_sha256"]):
        raise RuntimeError("current Agent inventory does not match explicit treatment freeze")
    source_path = contract.get("step9_43_preclearance_path")
    source_sha = contract.get("step9_43_preclearance_sha256")
    if (source_path is None) != (source_sha is None):
        raise RuntimeError("preclearance lineage pin is incomplete")
    if source_path is not None and sha256_file(ROOT / source_path) != source_sha:
        raise RuntimeError("prior Step 9.43 preclearance artifact hash mismatch")
    base = legacy.current_frozen_bindings()
    if not all(value for key, value in base["checks"].items() if key != "treatment_agent"):
        raise RuntimeError("one or more frozen evaluation infrastructure identities mismatch")
    comparisons = {
        "baseline_agent_sha256": "baseline_agent_sha256",
        "benchmark_sha256": "benchmark_sha256",
        "benchmark_manifest_sha256": "benchmark_manifest_sha256",
        "harness_sha256": "harness_sha256",
        "scoring_sha256": "scoring_sha256",
        "scoring_rubric_sha256": "scoring_rubric_sha256",
        "metric_registry_sha256": "metric_registry_sha256",
        "one_shot_rules_sha256": "one_shot_rules_sha256",
        "matched_protocol_sha256": "matched_protocol_sha256",
        "baseline_metric_lock_sha256": "baseline_metric_lock_sha256",
        "claim_policy_sha256": "claim_policy_sha256",
        "model_configuration_fingerprint_sha256": "model_configuration_fingerprint_sha256",
        "rag_configuration_fingerprint_sha256": "rag_configuration_fingerprint_sha256",
        "tool_adapter_sha256": "tool_adapter_sha256",
        "dependency_lock_sha256": "dependency_lock_sha256",
        "case_order_fingerprint_sha256": "case_order_fingerprint_sha256",
    }
    for field, key in comparisons.items():
        if base.get(field) != contract.get(key):
            raise RuntimeError(f"live {field} differs from identity contract")
    if base["case_count"] != contract["case_count"] or base["comparison_class"] != contract["comparison_class"]:
        raise RuntimeError("case count or comparison protocol mismatch")
    for key, value in freeze.get("shared_evaluation_identities", {}).items():
        if base.get(key) != value or contract.get(key) != value:
            raise RuntimeError(f"runner freeze {key} mismatch")
    pins = dict(base)
    verified_checks = dict(base["checks"])
    verified_checks.update({"treatment_agent": True, "treatment_v2_freeze": True,
                            "treatment_runner_freeze": True, "identity_contract": True})
    pins.update({"treatment_agent_sha256": contract["treatment_agent_sha256"],
                 "evaluation_id": contract["evaluation_id"],
                 "treatment_runner_sha256": runner_sha,
                 "checks": verified_checks,
                 "all_frozen_hashes_match": True})
    return contract, freeze, {"pins": pins, "contract_sha256": contract_sha,
                              "runner_sha256": runner_sha, "contract_path": rel}


def run(*, identity_contract_path: Path, authorization_file: Path,
        evaluation_id: str, authorization_id: str, attempt_id: str,
        supplied: dict[str, str]) -> None:
    from scripts import run_step9_35a_matched_treatment as legacy

    contract, freeze, runtime = load_verified_identity(identity_contract_path)
    authorization = read_json(authorization_file)
    validate_authorization_bindings(
        contract, authorization, evaluation_id=evaluation_id,
        authorization_id=authorization_id, attempt_id=attempt_id, supplied=supplied,
        contract_path=runtime["contract_path"], contract_sha256=runtime["contract_sha256"],
        runner_sha256=runtime["runner_sha256"],
        runner_freeze_sha256=sha256_file(RUNNER_FREEZE_PATH),
    )
    # Preserve the frozen runner's execution/one-shot implementation verbatim.
    # Its pre-first-case refresh must re-read every identity, not reuse a snapshot.
    original_loader = legacy.current_frozen_bindings

    def fresh_verified_bindings() -> dict[str, Any]:
        legacy.current_frozen_bindings = original_loader
        try:
            _, _, fresh = load_verified_identity(identity_contract_path)
        finally:
            legacy.current_frozen_bindings = fresh_verified_bindings
        return fresh["pins"]

    legacy.current_frozen_bindings = fresh_verified_bindings
    try:
        legacy.run(evaluation_id, authorization_id, attempt_id, authorization_file, supplied)
    finally:
        legacy.current_frozen_bindings = original_loader


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Step 9.43a explicit treatment identity adapter")
    parser.add_argument("--identity-contract", required=True, type=Path)
    parser.add_argument("--evaluation-id", required=True)
    parser.add_argument("--authorization-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--authorization-file", required=True, type=Path)
    for name in ("treatment-agent-sha256", "benchmark-sha256", "harness-sha256",
                 "scoring-sha256", "metric-registry-sha256", "one-shot-rules-sha256",
                 "matched-protocol-sha256"):
        parser.add_argument("--" + name, required=True)
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
    run(identity_contract_path=args.identity_contract, authorization_file=args.authorization_file,
        evaluation_id=args.evaluation_id, authorization_id=args.authorization_id,
        attempt_id=args.attempt_id, supplied=supplied)


if __name__ == "__main__":
    main()
