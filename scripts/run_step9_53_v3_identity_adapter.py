"""Step 9.53 identity adapter for the frozen V3 treatment.

This module owns identity validation only. Formal execution, if separately
authorized in a later step, is delegated unchanged to the Step 9.35a runner.
Import and preflight never parse benchmark cases or create an output namespace.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FREEZE_DIR = ROOT / "evaluation" / "v1_2_3"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
V3_CONTRACT_PATH = "evaluation/v1_2_3/step9_58a_r1_v3_identity_contract.json"
from scripts.v3_runner_identity import IDENTITY_CONFIG_PATH, load_identity_config, resolve_current_freeze

_CURRENT_IDENTITY = load_identity_config(ROOT)
V3_RUNNER_FREEZE_PATH = _CURRENT_IDENTITY["runner_freeze_path"]
RUNNER_FREEZE_REVISION = _CURRENT_IDENTITY["runner_freeze_revision"]
AUTHORIZATION_LIFECYCLE_CONTRACT_PATH = "evaluation/v1_2_3/step9_61a_v3_authorization_lifecycle_contract.json"
AUTHORIZATION_LIFECYCLE_MODULE_PATH = "scripts/authorization_lifecycle.py"
TRANSACTION_CONTRACT_PATH = "evaluation/v1_2_3/step9_63a_r1_atomic_commit_contract.json"
TRANSACTION_MODULE_PATH = "scripts/v3_execution_transaction.py"
V3_AGENT_SHA256 = "085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607"
BASELINE_AGENT_SHA256 = "4e2bffea0d7eaa9299074a960df84a1806b3ae9d4930662929abc58ca5b2ae79"
EVALUATION_ID = "heldout-v4-step9_55a-treatment-v3-20260930-01"
OUT_ROOT = ROOT / "evaluation" / "v4_runs"
GLOBAL_OUT_ROOT = OUT_ROOT
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")
PRE_ATTEMPT = "PRE_ATTEMPT"
POST_ATTEMPT_CREATION_PRE_FIRST_CASE = "POST_ATTEMPT_CREATION_PRE_FIRST_CASE"
CONSUMED_STEP9_54_AUTHORIZATION_ID = "auth-step9_54r1-b43c3282fd9344f6a7c3548e376ec6d1"
FAILED_STEP9_55_ATTEMPT_ID = "attempt-step9_54r1-d2e272e499e24f5f82096a01b2bf9fe9"
FAILED_STEP9_55_EVALUATION_ID = "heldout-v4-step9_53-treatment-v3-20260930-01"
V3_IMPLEMENTATION_HASHES = {
    "adaptive_agent/answer_generation.py": "b331a4264bbbb4d5ff5bd810f2e11c6016d1a2518da0ef740e33309bc46608e7",
    "adaptive_agent/runner.py": "489806f4e6e9af27c7145b7c766f8e8de1700038a605c2a1752922c6cbedfa1c",
    "adaptive_agent/dependency_resolver.py": "8af9da5a035be7aee52e77f1ee6b10031005fe20516445c041fee766796d3ceb",
    "adaptive_agent/preconditions.py": "b4dc3f3f389b785db9b4483fff0da64261d035cc3ee415a1d4f77e74a3020365",
    "evaluation/recorder.py": "0d631d2d8a1bf4678e542a97b4ecf2f377380c1ebe2c7df2694bd823f9627e7b",
    "evaluation/v3_trace_adapter.py": "459d3ce09566d32fba1cac3f8c4518564ab7d373c9972bab496ece28cd26617c",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path.name}")
    return value


BOUND_IDENTITY_FIELDS = (
    "treatment_agent_sha256", "baseline_agent_sha256", "benchmark_path",
    "benchmark_sha256", "benchmark_manifest_sha256", "harness_sha256",
    "scoring_sha256", "scoring_rubric_sha256", "metric_registry_sha256",
    "one_shot_rules_sha256", "matched_protocol_sha256", "baseline_metric_lock_sha256",
    "claim_policy_sha256", "model_configuration_fingerprint_sha256",
    "rag_configuration_fingerprint_sha256", "tool_adapter_sha256", "dependency_lock_sha256",
    "case_count", "task_distribution", "case_order_fingerprint_sha256", "max_runner_turns",
    "agent_loop_max_steps", "fresh_session_per_case", "comparison_class",
    "production_case_path_runner_sha256",
)


def _canonical_json_sha256(value: Any) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                  ensure_ascii=False).encode("utf-8"))


def _load_v3_contract() -> dict[str, Any]:
    """Resolve the Step 9.58a-r1 namespace identity over immutable Step 9.55a."""
    overlay = read_json(ROOT / V3_CONTRACT_PATH)
    source_path = overlay.get("inherited_identity_contract_path")
    if source_path != "evaluation/v1_2_3/step9_55a_v3_identity_contract.json":
        raise RuntimeError("Step 9.55a contract has an unknown identity parent")
    source_file = ROOT / source_path
    if sha256_file(source_file) != overlay.get("inherited_identity_contract_sha256"):
        raise RuntimeError("inherited frozen identity contract mismatch")
    parent = read_json(source_file)
    grandparent_path = parent.get("inherited_identity_contract_path")
    if grandparent_path != "evaluation/v1_2_3/step9_53_v3_identity_contract.json":
        raise RuntimeError("Step 9.55a identity parent is unexpected")
    return {**read_json(ROOT / grandparent_path), **parent, **overlay}


def validate_candidate_identity(identity_kind: str, contract: dict[str, Any],
                                contract_path: str, observed_agent_sha256: str) -> None:
    """Validate an explicit V1/V2/V3 contract pairing; never infer from source state."""
    if identity_kind == "TREATMENT_V2":
        from scripts import run_step9_43a_treatment_v2 as v2_adapter

        allowed = {"evaluation/v1_2_3/step9_43a_treatment_v2_identity_contract.json"}
        v2_adapter.validate_contract_shape(contract, allowed, contract_path)
        v2_adapter.validate_agent_identity(contract, observed_agent_sha256)
        return
    if identity_kind != "TREATMENT_V3" or contract_path != V3_CONTRACT_PATH:
        raise RuntimeError("unknown or mismatched explicit treatment identity contract")
    if contract.get("artifact_type") != "TREATMENT_V3_IDENTITY_CONTRACT_NOT_AUTHORIZATION":
        raise RuntimeError("V3 identity contract type mismatch")
    if contract.get("status") != "FROZEN_IDENTITY_CONTRACT_NOT_AUTHORIZATION":
        raise RuntimeError("V3 identity contract is not frozen or is executable")
    if contract.get("authorization_id") is not None or contract.get("attempt_id") is not None:
        raise RuntimeError("identity contract must not pre-issue authorization or attempt IDs")
    if contract.get("treatment_agent_sha256") != V3_AGENT_SHA256:
        raise RuntimeError("V3 identity contract Agent pin mismatch")
    if observed_agent_sha256 == contract.get("baseline_agent_sha256") or observed_agent_sha256 == BASELINE_AGENT_SHA256:
        raise RuntimeError("baseline Agent cannot be supplied as V3 treatment")
    if observed_agent_sha256 != contract.get("treatment_agent_sha256"):
        raise RuntimeError("current Agent does not match explicit V3 identity contract")
    if contract.get("evaluation_id") != EVALUATION_ID:
        raise RuntimeError("V3 evaluation namespace mismatch")


def _directory_fingerprint(root: Path) -> str:
    entries = []
    for path in sorted(root.glob("*")):
        if path.is_file() and not path.name.startswith("._"):
            digest = sha256_file(path)
            entries.append(f"{digest}  {path.relative_to(ROOT)}\n")
    return sha256_bytes("".join(entries).encode())


def _fingerprint_rows(rows: list[list[str]]) -> str:
    payload = "".join(f"{path}\t{digest}\n" for path, digest in sorted(rows))
    return sha256_bytes(payload.encode())


def current_v3_agent_identity() -> tuple[str, bool]:
    """Recompute the frozen 26-entry development inventory without loading cases."""
    dev_freeze = read_json(FREEZE_DIR / "step9_51_v3_development_freeze_r1.json")
    v2_source = read_json(FREEZE_DIR / "step9_42_treatment_v2_freeze.json")
    current = []
    for relative_path, frozen_digest in v2_source["agent_behavior_files"]:
        if relative_path == "runtime:deepseek_nonsecret_configuration":
            digest = frozen_digest
        elif relative_path == "rag_lib/pdfs/":
            digest = _directory_fingerprint(ROOT / "rag_lib" / "pdfs")
        else:
            digest = sha256_file(ROOT / relative_path)
        current.append([relative_path, digest])
    aggregate = _fingerprint_rows(current)
    implementation_ok = all(sha256_file(ROOT / path) == digest
                            for path, digest in V3_IMPLEMENTATION_HASHES.items())
    v3_ok = aggregate == dev_freeze.get("v3_development_agent_sha256") == V3_AGENT_SHA256
    return aggregate, bool(v3_ok and implementation_ok)


def _current_evaluation_bindings() -> dict[str, Any]:
    """Read-only hashes of frozen protocol inputs; no benchmark parsing or scoring."""
    contract_v2 = read_json(FREEZE_DIR / "step9_43a_treatment_v2_identity_contract.json")
    runner_freeze = read_json(FREEZE_DIR / "step9_35a_treatment_runner_freeze.json")
    lifecycle_freeze, _, _ = resolve_current_freeze(ROOT)
    harness = read_json(FREEZE_DIR / "step9_13a_harness_freeze.json")
    scoring = read_json(FREEZE_DIR / "step9_11_clean_freeze_manifest.json")
    protocol = read_json(FREEZE_DIR / "step9_34a_matched_comparison_protocol.json")
    registry = read_json(FREEZE_DIR / "step9_26_v4_metric_registry.json")
    step9_29a = read_json(FREEZE_DIR / "step9_29a_v4_runner_freeze.json")
    identity_runner_freeze = read_json(FREEZE_DIR / "step9_43a_treatment_v2_runner_freeze.json")
    v3_contract = _load_v3_contract()

    h_rows = harness["new_harness_files"]
    s_rows = scoring["scoring_files"]
    harness_ok = (all(sha256_file(ROOT / path) == digest for path, digest in h_rows)
                  and _fingerprint_rows(h_rows) == contract_v2["harness_sha256"])
    scoring_ok = (all(sha256_file(ROOT / path) == digest for path, digest in s_rows)
                  and _fingerprint_rows(s_rows) == contract_v2["scoring_sha256"])
    benchmark_path = ROOT / contract_v2["benchmark_path"]
    benchmark_manifest = ROOT / "evaluation/benchmarks/benchmark_v4_manifest.json"

    source_rows = read_json(FREEZE_DIR / "step9_42_treatment_v2_freeze.json")["agent_behavior_files"]
    rag_paths = {item["path"] for item in read_json(FREEZE_DIR / "step9_32_baseline_agent_freeze.json")["baseline_rag_config_files"]}
    rag_current = []
    for path, _ in source_rows:
        if path in rag_paths:
            digest = (_directory_fingerprint(ROOT / "rag_lib" / "pdfs")
                      if path == "rag_lib/pdfs/" else sha256_file(ROOT / path))
            rag_current.append([path, digest])
    rag_fp = _fingerprint_rows(rag_current)

    v3_agent_sha, v3_agent_ok = current_v3_agent_identity()
    from scripts.run_step9_28_v4_heldout import model_configuration_match

    contract_bindings = {
        "baseline_agent_sha256": contract_v2["baseline_agent_sha256"],
        "benchmark_path": contract_v2["benchmark_path"],
        "benchmark_sha256": sha256_file(benchmark_path),
        "benchmark_manifest_sha256": sha256_file(benchmark_manifest),
        "harness_sha256": _fingerprint_rows(h_rows),
        "scoring_sha256": _fingerprint_rows(s_rows),
        "scoring_rubric_sha256": sha256_file(ROOT / "evaluation/benchmark_v1_1_scoring.md"),
        "metric_registry_sha256": sha256_file(FREEZE_DIR / "step9_26_v4_metric_registry.json"),
        "one_shot_rules_sha256": sha256_file(FREEZE_DIR / "step9_26_v4_one_shot_rules.md"),
        "matched_protocol_sha256": sha256_file(FREEZE_DIR / "step9_34a_matched_comparison_protocol.json"),
        "baseline_metric_lock_sha256": sha256_file(FREEZE_DIR / "step9_34a_baseline_metric_lock.json"),
        "claim_policy_sha256": sha256_file(FREEZE_DIR / "step9_34a_claim_policy.json"),
        "model_configuration_fingerprint_sha256": contract_v2["model_configuration_fingerprint_sha256"],
        "rag_configuration_fingerprint_sha256": rag_fp,
        "tool_adapter_sha256": sha256_file(ROOT / "adaptive_agent/tools.py"),
        "dependency_lock_sha256": sha256_file(ROOT / "requirements-lock.txt"),
        "case_count": protocol["design_classification"]["case_count"],
        "task_distribution": registry["planned_task_distribution"],
        "case_order_fingerprint_sha256": protocol["design_classification"]["case_set_and_order_fingerprint_sha256"],
        "max_runner_turns": contract_v2["max_runner_turns"],
        "agent_loop_max_steps": contract_v2["agent_loop_max_steps"],
        "fresh_session_per_case": contract_v2["fresh_session_per_case"],
        "comparison_class": contract_v2["comparison_class"],
        "production_case_path_runner_sha256": sha256_file(ROOT / "scripts/run_step9_28_v4_heldout.py"),
    }
    expected = {
        "benchmark_sha256": contract_v2["benchmark_sha256"],
        "benchmark_manifest_sha256": contract_v2["benchmark_manifest_sha256"],
        "harness_sha256": contract_v2["harness_sha256"],
        "scoring_sha256": contract_v2["scoring_sha256"],
        "scoring_rubric_sha256": contract_v2["scoring_rubric_sha256"],
        "metric_registry_sha256": contract_v2["metric_registry_sha256"],
        "one_shot_rules_sha256": contract_v2["one_shot_rules_sha256"],
        "matched_protocol_sha256": contract_v2["matched_protocol_sha256"],
        "baseline_metric_lock_sha256": contract_v2["baseline_metric_lock_sha256"],
        "claim_policy_sha256": contract_v2["claim_policy_sha256"],
        "model_configuration_fingerprint_sha256": contract_v2["model_configuration_fingerprint_sha256"],
        "rag_configuration_fingerprint_sha256": contract_v2["rag_configuration_fingerprint_sha256"],
        "tool_adapter_sha256": contract_v2["tool_adapter_sha256"],
        "dependency_lock_sha256": contract_v2["dependency_lock_sha256"],
        "case_count": contract_v2["case_count"],
        "case_order_fingerprint_sha256": contract_v2["case_order_fingerprint_sha256"],
        "max_runner_turns": contract_v2["max_runner_turns"],
        "agent_loop_max_steps": contract_v2["agent_loop_max_steps"],
        "fresh_session_per_case": contract_v2["fresh_session_per_case"],
        "comparison_class": contract_v2["comparison_class"],
        "production_case_path_runner_sha256": step9_29a["runner_sha256"],
    }
    checks = {key: contract_bindings[key] == value for key, value in expected.items()}
    checks.update({
        "v3_agent": v3_agent_ok,
        "harness_inventory": harness_ok,
        "scoring_inventory": scoring_ok,
        "model_configuration_live": bool(model_configuration_match()),
        "benchmark_manifest_status": read_json(benchmark_manifest).get("status") == "SEALED_NOT_EVALUATED",
        "task_distribution": registry.get("planned_task_distribution") == {
            "KNOWLEDGE_QA": 10, "CAUSE_ASSESSMENT": 10,
            "PERSONALIZED_DECISION": 10, "DATA_ANALYSIS": 10},
        "runner_parent": sha256_file(ROOT / lifecycle_freeze["parent_runner"]["path"])
        == lifecycle_freeze["parent_runner"]["sha256"],
        "runner_parent_freeze": lifecycle_freeze.get("status") == "FROZEN_NOT_AUTHORIZED",
        "authorization_lifecycle_contract": (
            sha256_file(ROOT / AUTHORIZATION_LIFECYCLE_CONTRACT_PATH)
            == lifecycle_freeze.get("authorization_lifecycle_contract_sha256")
            and sha256_file(ROOT / AUTHORIZATION_LIFECYCLE_MODULE_PATH)
            == lifecycle_freeze.get("authorization_lifecycle_module_sha256")
        ),
        "identity_adapter_parent_runner": identity_runner_freeze.get("parent_runner_sha256")
        == runner_freeze.get("treatment_runner_sha256"),
        "identity_adapter_parent_freeze": identity_runner_freeze.get("parent_runner_freeze_sha256")
        == sha256_file(FREEZE_DIR / "step9_35a_treatment_runner_freeze.json"),
        "production_case_path_runner": identity_runner_freeze.get("production_case_path_runner_sha256")
        == contract_bindings["production_case_path_runner_sha256"],
        "v2_identity_adapter": sha256_file(ROOT / "scripts/run_step9_43a_treatment_v2.py")
        == identity_runner_freeze.get("runner_sha256"),
        "v2_identity_adapter_freeze": sha256_file(FREEZE_DIR / "step9_43a_treatment_v2_runner_freeze.json")
        == v3_contract.get("identity_runner_freeze_sha256"),
    })
    contract_bindings.update({"treatment_agent_sha256": v3_agent_sha,
                              "evaluation_id": EVALUATION_ID,
                              "treatment_runner_sha256": sha256_file(Path(__file__)),
                              "all_frozen_hashes_match": all(checks.values()),
                              "checks": checks})
    return contract_bindings


def _assert_authorization_runner_binding(bindings: dict[str, Any], freeze: dict[str, Any],
                                         current_runner_sha256: str) -> None:
    """Fail closed unless the validator pins the single current frozen runner."""
    identity = load_identity_config(ROOT)
    if (freeze.get("runner_freeze_revision") != identity["runner_freeze_revision"]
            or freeze.get("status") != "FROZEN_NOT_AUTHORIZED"
            or freeze.get("runner_sha256") != current_runner_sha256
            or bindings.get("treatment_runner_sha256") != current_runner_sha256
            or freeze.get("parent_runner", {}).get("sha256")
            != sha256_file(ROOT / freeze.get("parent_runner", {}).get("path", "missing"))
            or freeze.get("authorization_lifecycle_contract_sha256")
            != sha256_file(ROOT / AUTHORIZATION_LIFECYCLE_CONTRACT_PATH)
            or freeze.get("authorization_lifecycle_module_sha256")
            != sha256_file(ROOT / AUTHORIZATION_LIFECYCLE_MODULE_PATH)
            or freeze.get("transaction_module_sha256") != sha256_file(ROOT / TRANSACTION_MODULE_PATH)
            or freeze.get("transaction_contract_sha256") != sha256_file(ROOT / TRANSACTION_CONTRACT_PATH)
            or freeze.get("namespace_allocator_sha256")
            != sha256_file(ROOT / "scripts/v3_namespace_allocator.py")
            or freeze.get("formal_entry_runner_sha256")
            != sha256_file(ROOT / "scripts/run_step9_63_v3_formal_execution.py")):
        raise RuntimeError("authorization validator identity differs from current runner freeze")


def _authoritative_authorization_bindings() -> dict[str, Any]:
    bindings = _current_evaluation_bindings()
    freeze, _, _ = resolve_current_freeze(ROOT)
    current_runner_sha256 = sha256_file(Path(__file__))
    _assert_authorization_runner_binding(bindings, freeze, current_runner_sha256)
    return bindings


def _assert_identity_unused_in_other_ledgers(run_root: Path, authorization_id: str,
                                             attempt_id: str, current_ledger: Path | None = None,
                                             current_namespace_id: str | None = None,
                                             evaluation_id: str | None = None) -> None:
    current = current_ledger.resolve() if current_ledger is not None else None
    for ledger_path in run_root.rglob("attempts.jsonl"):
        if current is not None and ledger_path.resolve() == current:
            continue
        for line_number, line in enumerate(ledger_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise RuntimeError(f"malformed historical attempt ledger: {ledger_path.name}:{line_number}") from error
            if (event.get("authorization_id") == authorization_id
                    or event.get("attempt_id") == attempt_id):
                raise RuntimeError("authorization or attempt identity already appears in another ledger")
    for marker in run_root.rglob(".namespace_allocation.json"):
        try:
            reservation = read_json(marker)
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError("malformed namespace allocation marker") from error
        if current_namespace_id is not None and marker.parent.name == current_namespace_id:
            if (reservation.get("authorization_id") == authorization_id
                    and reservation.get("attempt_id") == attempt_id
                    and reservation.get("evaluation_id") == evaluation_id
                    and reservation.get("namespace_id") == current_namespace_id):
                continue
            raise RuntimeError("namespace reservation identity mismatch")
        if (reservation.get("authorization_id") == authorization_id
                or reservation.get("attempt_id") == attempt_id):
            raise RuntimeError("authorization or attempt identity already has a namespace reservation")


def _validate_namespace_lifecycle(
    *, run_root: Path, evaluation_id: str, phase: str,
    authorization_id: str | None = None, attempt_id: str | None = None,
    authorization_file: Path | None = None, treatment_agent_sha256: str,
    runner_sha256: str, benchmark_sha256: str, case_count: int,
    case_order_fingerprint_sha256: str, identity_root: Path | None = None,
    transaction_id: str | None = None,
) -> dict[str, bool]:
    """Enforce distinct pre-attempt and parent-created pre-first-case invariants."""
    if phase not in {PRE_ATTEMPT, POST_ATTEMPT_CREATION_PRE_FIRST_CASE}:
        raise RuntimeError("unknown attempt namespace lifecycle phase")
    if not SAFE_ID.fullmatch(evaluation_id):
        raise RuntimeError("invalid evaluation namespace identity")
    namespace = run_root / evaluation_id

    if phase == PRE_ATTEMPT:
        if namespace.exists() or namespace.is_symlink():
            raise RuntimeError("pre-attempt output namespace already exists")
        if (authorization_id is None) != (attempt_id is None):
            raise RuntimeError("authorization and attempt IDs must be supplied together")
        if authorization_id is not None:
            if transaction_id is None:
                from scripts.authorization_lifecycle import assert_executable_authorization

                assert_executable_authorization(authorization_id)
            else:
                from scripts.v3_execution_transaction import TRANSACTION_ROOT, require_committed
                from scripts.v3_namespace_allocator import derive_namespace_id

                require_committed(
                    transaction_root=TRANSACTION_ROOT, authorization_id=authorization_id,
                    attempt_id=attempt_id,
                    namespace_id=derive_namespace_id(evaluation_id, authorization_id, attempt_id),
                    expected_bindings={"transaction_id": transaction_id,
                                       "runner_sha256": runner_sha256,
                                       "agent_sha256": treatment_agent_sha256,
                                       "case_set_sha256": case_order_fingerprint_sha256},
                )
            if not SAFE_ID.fullmatch(authorization_id) or not SAFE_ID.fullmatch(attempt_id or ""):
                raise RuntimeError("invalid authorization or attempt identity")
            if authorization_id == CONSUMED_STEP9_54_AUTHORIZATION_ID or attempt_id == FAILED_STEP9_55_ATTEMPT_ID:
                raise RuntimeError("consumed Step 9.54 authorization or failed Step 9.55 attempt cannot be reused")
            if authorization_file is None or not authorization_file.is_file():
                raise RuntimeError("new authorization manifest is required for identity preflight")
            authorization = read_json(authorization_file)
            if any((authorization.get("evaluation_id") != evaluation_id,
                    authorization.get("authorization_id") != authorization_id,
                    authorization.get("attempt_id") != attempt_id,
                    authorization.get("runner_freeze_revision") != RUNNER_FREEZE_REVISION,
                    authorization.get("runner_freeze_sha256") != sha256_file(ROOT / V3_RUNNER_FREEZE_PATH),
                    authorization.get("status") != "ISSUED_NOT_EXECUTED",
                    authorization.get("consumed") is not False,
                    authorization.get("consumed_at_utc") is not None)):
                raise RuntimeError("authorization manifest does not bind an unconsumed future attempt")
            _assert_identity_unused_in_other_ledgers(
                identity_root or run_root, authorization_id, attempt_id,
                current_namespace_id=(run_root.name if identity_root is not None else None),
                evaluation_id=evaluation_id,
            )
        return {"namespace_isolated_for_phase": True, "current_attempt_exact": False,
                "no_case_outputs": True, "zero_case_counters": True,
                "no_completed_attempt": True, "authorization_lifecycle_valid": True,
                "no_prior_identity_reuse": True}

    if not (namespace.is_dir() and not namespace.is_symlink()):
        raise RuntimeError("post-create namespace is not a real current-attempt directory")
    if (authorization_id is None or attempt_id is None or authorization_file is None
            or not SAFE_ID.fullmatch(authorization_id) or not SAFE_ID.fullmatch(attempt_id)):
        raise RuntimeError("post-create identity verification requires authorization, attempt, and manifest")
    from scripts.authorization_lifecycle import assert_not_retired

    assert_not_retired(authorization_id)
    from scripts.v3_execution_transaction import TRANSACTION_ROOT, require_committed
    from scripts.v3_namespace_allocator import derive_namespace_id

    if transaction_id is None:
        raise RuntimeError("post-create validation requires transaction identity")
    require_committed(
        transaction_root=TRANSACTION_ROOT, authorization_id=authorization_id,
        attempt_id=attempt_id,
        namespace_id=derive_namespace_id(evaluation_id, authorization_id, attempt_id),
        expected_bindings={
            "transaction_id": transaction_id,
            "runner_sha256": runner_sha256,
            "agent_sha256": treatment_agent_sha256,
            "case_set_sha256": case_order_fingerprint_sha256,
        },
    )
    marker = run_root / ".namespace_allocation.json"
    if not marker.is_file() or marker.is_symlink():
        raise RuntimeError("committed namespace reservation marker is missing")
    if any(read_json(marker).get(key) != value for key, value in {
        "evaluation_id": evaluation_id,
        "authorization_id": authorization_id,
        "attempt_id": attempt_id,
        "transaction_id": transaction_id,
        "namespace_id": run_root.name,
    }.items()):
        raise RuntimeError("namespace reservation does not bind the committed transaction")
    if authorization_id == CONSUMED_STEP9_54_AUTHORIZATION_ID or attempt_id == FAILED_STEP9_55_ATTEMPT_ID:
        raise RuntimeError("consumed Step 9.54 authorization or failed Step 9.55 attempt cannot be resumed")

    ledger = namespace / "attempts.jsonl"
    if not ledger.is_file() or ledger.is_symlink():
        raise RuntimeError("parent-created attempt ledger is missing or unsafe")
    authorization = read_json(authorization_file)
    if any((authorization.get("evaluation_id") != evaluation_id,
            authorization.get("authorization_id") != authorization_id,
            authorization.get("attempt_id") != attempt_id,
            authorization.get("status") != "ISSUED_NOT_EXECUTED",
            authorization.get("consumed") is not False,
            authorization.get("consumed_at_utc") is not None)):
        raise RuntimeError("authorization manifest identity/lifecycle mismatch")

    try:
        events = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError("current attempt ledger is unreadable or malformed") from error
    expected_statuses = ["PREPARED", "AUTHORIZATION_CONSUMED", "FIRST_EVALUATION_ACCESS",
                         "CASE_SET_AND_ORDER_VERIFIED"]
    if [event.get("status") for event in events] != expected_statuses:
        raise RuntimeError("current ledger is not exactly at the pre-first-case lifecycle boundary")
    for event in events:
        if any((event.get("evaluation_id") != evaluation_id,
                event.get("authorization_id") != authorization_id,
                event.get("attempt_id") != attempt_id,
                event.get("transaction_id") != transaction_id,
                event.get("treatment_agent_sha256") != treatment_agent_sha256,
                event.get("runner_sha256") != runner_sha256,
                event.get("cases_started") != 0,
                event.get("cases_completed") != 0)):
            raise RuntimeError("current attempt ledger identity or case counter mismatch")
    first_access, verified = events[2], events[3]
    if any((first_access.get("dataset_sha256") != benchmark_sha256,
            first_access.get("case_order_fingerprint_sha256") != case_order_fingerprint_sha256,
            verified.get("case_count") != case_count,
            verified.get("case_order_fingerprint_sha256") != case_order_fingerprint_sha256)):
        raise RuntimeError("current attempt's first-access or case-set identity mismatch")
    allowed_files = {"attempts.jsonl"}
    if any(path.name not in allowed_files and not path.name.startswith("._") for path in namespace.iterdir()):
        raise RuntimeError("current attempt namespace contains unexpected or prior output files")
    if any(namespace.glob("*_case_results.jsonl")) or any(namespace.glob("*_raw_traces.jsonl")):
        raise RuntimeError("case result or raw trace already exists before first case")
    _assert_identity_unused_in_other_ledgers(
        identity_root or run_root, authorization_id, attempt_id, ledger,
        current_namespace_id=(run_root.name if identity_root is not None else None),
        evaluation_id=evaluation_id,
    )
    return {"namespace_isolated_for_phase": True, "current_attempt_exact": True,
            "no_case_outputs": True, "zero_case_counters": True,
            "no_completed_attempt": True, "authorization_lifecycle_valid": True,
            "no_prior_identity_reuse": True}


def _assert_one_shot_and_namespace(
    contract: dict[str, Any], *, lifecycle_phase: str = PRE_ATTEMPT,
    authorization_id: str | None = None, attempt_id: str | None = None,
    authorization_file: Path | None = None,
    namespace_root: Path | None = None, identity_root: Path | None = None,
    transaction_id: str | None = None,
) -> dict[str, bool]:
    run_freeze = read_json(FREEZE_DIR / "step9_35a_treatment_runner_freeze.json")
    semantics = run_freeze.get("one_shot_semantics", {})
    required_true = (
        "one_attempt_only", "authorization_or_attempt_id_reuse_rejected",
        "exclusive_new_output_namespace", "exclusive_append_only_ledger_creation",
        "first_access_event_fsynced_before_dataset_read",
        "case_set_and_order_verified_before_first_agent_call",
        "per_case_started_event_fsynced_before_agent_call",
        "raw_trace_and_case_result_files_created_exclusively",
        "per_case_records_fsynced", "interruption_preserves_attempt_and_automatic_resume_forbidden",
    )
    competing_ids = {
        "heldout-v4-step9_28-20260925-01",
        read_json(FREEZE_DIR / "step9_43a_treatment_v1_identity_contract.json")["evaluation_id"],
        read_json(FREEZE_DIR / "step9_43a_treatment_v2_identity_contract.json")["evaluation_id"],
        FAILED_STEP9_55_EVALUATION_ID,
    }
    evaluation_id = contract["evaluation_id"]
    lifecycle = _validate_namespace_lifecycle(
        run_root=namespace_root or OUT_ROOT, evaluation_id=evaluation_id, phase=lifecycle_phase,
        authorization_id=authorization_id, attempt_id=attempt_id,
        authorization_file=authorization_file,
        treatment_agent_sha256=contract["treatment_agent_sha256"],
        runner_sha256=sha256_file(Path(__file__)),
        benchmark_sha256=contract["benchmark_sha256"], case_count=contract["case_count"],
        case_order_fingerprint_sha256=contract["case_order_fingerprint_sha256"],
        identity_root=identity_root or GLOBAL_OUT_ROOT,
        transaction_id=transaction_id,
    )
    return {
        "exactly_once_guard_ready": run_freeze.get("status") == "FROZEN_NOT_AUTHORIZED"
        and all(semantics.get(key) is True for key in required_true),
        "output_namespace_isolated": evaluation_id not in competing_ids and lifecycle["namespace_isolated_for_phase"],
        # This means no *prior* V3 attempt exists for this identity. In the
        # post-create phase the current ledger is allowed, but duplicate IDs in
        # any other ledger have already been rejected above.
        "prior_treatment_v3_attempt": not lifecycle["no_prior_identity_reuse"],
        "attempt_has_no_case_outputs": lifecycle["no_case_outputs"],
        "attempt_case_counters_zero": lifecycle["zero_case_counters"],
        "attempt_not_completed_or_reused": lifecycle["no_completed_attempt"] and lifecycle["no_prior_identity_reuse"],
        "authorization_lifecycle_valid": lifecycle["authorization_lifecycle_valid"],
    }


def validate_frozen_v3_identity(
    *, lifecycle_phase: str = PRE_ATTEMPT,
    authorization_id: str | None = None,
    attempt_id: str | None = None,
    authorization_file: Path | None = None,
    namespace_root: Path | None = None,
    identity_root: Path | None = None,
    transaction_id: str | None = None,
) -> dict[str, Any]:
    """Preflight current V3 and shared evaluation pins; never loads case content."""
    contract_path = ROOT / V3_CONTRACT_PATH
    freeze, freeze_path, identity = resolve_current_freeze(ROOT)
    allocator_path = ROOT / "scripts" / "v3_namespace_allocator.py"
    contract = _load_v3_contract()
    contract_hash = sha256_file(contract_path)
    runner_hash = sha256_file(Path(__file__))
    validate_candidate_identity("TREATMENT_V3", contract, V3_CONTRACT_PATH, current_v3_agent_identity()[0])
    if not all((
        sha256_file(FREEZE_DIR / "step9_51_v3_development_freeze_r1.json") == contract["development_freeze_sha256"],
        sha256_file(FREEZE_DIR / "step9_52_v3_pre_evaluation_validation.json") == contract["step9_52_validation_sha256"],
        sha256_file(FREEZE_DIR / "step9_52_v3_identity_audit.json") == contract["step9_52_identity_audit_sha256"],
        read_json(FREEZE_DIR / "step9_51_v3_development_freeze_r1.json")["v3_development_agent_sha256"] == V3_AGENT_SHA256,
    )):
        raise RuntimeError("V3 development or Step 9.52 lineage identity mismatch")
    if freeze.get("status") != "FROZEN_NOT_AUTHORIZED" or any((
        freeze.get("runner_sha256") != runner_hash,
        freeze.get("identity_adapter_sha256") != runner_hash,
        freeze.get("namespace_allocator_sha256") != sha256_file(allocator_path),
        freeze.get("parent_runner", {}).get("sha256")
        != sha256_file(ROOT / freeze.get("parent_runner", {}).get("path", "missing")),
        freeze.get("authorization_lifecycle_module_sha256")
        != sha256_file(ROOT / AUTHORIZATION_LIFECYCLE_MODULE_PATH),
        freeze.get("authorization_lifecycle_contract_sha256")
        != sha256_file(ROOT / AUTHORIZATION_LIFECYCLE_CONTRACT_PATH),
        freeze.get("transaction_module_sha256")
        != sha256_file(ROOT / TRANSACTION_MODULE_PATH),
        freeze.get("transaction_contract_sha256")
        != sha256_file(ROOT / TRANSACTION_CONTRACT_PATH),
        freeze.get("identity_contract_sha256") != contract_hash,
        freeze.get("development_freeze_sha256") != contract["development_freeze_sha256"],
        freeze.get("step9_52_validation_sha256") != contract["step9_52_validation_sha256"],
    )):
        raise RuntimeError("Step 9.53 runner freeze mismatch")
    bindings = _current_evaluation_bindings()
    if not bindings["all_frozen_hashes_match"]:
        raise RuntimeError("one or more frozen V3/evaluation identity pins mismatch")
    freeze = read_json(freeze_path)
    _assert_authorization_runner_binding(bindings, freeze, runner_hash)
    bound_fields = BOUND_IDENTITY_FIELDS
    if any(contract.get(key) != bindings.get(key) for key in bound_fields):
        raise RuntimeError("V3 identity contract differs from current frozen evaluation bindings")
    resolved_bound_identities = {key: contract[key] for key in bound_fields}
    if (freeze.get("bound_identities") != resolved_bound_identities
            or freeze.get("bound_identities_sha256") != _canonical_json_sha256(resolved_bound_identities)):
        raise RuntimeError("V3 runner freeze bound identities mismatch")
    one_shot = _assert_one_shot_and_namespace(
        contract, lifecycle_phase=lifecycle_phase,
        authorization_id=authorization_id, attempt_id=attempt_id,
        authorization_file=authorization_file,
        namespace_root=namespace_root, identity_root=identity_root,
        transaction_id=transaction_id,
    )
    positive_guards = [value for key, value in one_shot.items()
                       if key != "prior_treatment_v3_attempt"]
    if one_shot["prior_treatment_v3_attempt"] or not all(positive_guards):
        raise RuntimeError("one-shot guard or output namespace preflight failed")
    trace_contract = read_json(FREEZE_DIR / "step9_52_v3_trace_schema_audit.json")
    if (sha256_file(FREEZE_DIR / "step9_52_v3_trace_schema_audit.json")
            != contract.get("trace_schema_contract_sha256")
            or trace_contract.get("trace_schema_change") != "ADDITIVE_COMPATIBLE"
            or trace_contract.get("schema_version") != contract.get("trace_schema_version")):
        raise RuntimeError("V3 trace schema contract is incompatible")
    return {"evaluation_id": EVALUATION_ID, "treatment_agent_sha256": V3_AGENT_SHA256,
            "runner_sha256": runner_hash, "identity_contract_sha256": contract_hash,
            "all_frozen_hashes_match": True, "checks": bindings["checks"],
            "authorization_validator_binding_match": True,
            "namespace_lifecycle_phase": lifecycle_phase, **one_shot}


def preflight() -> dict[str, Any]:
    from scripts.v3_namespace_allocator import derive_namespace_id

    candidate_root = GLOBAL_OUT_ROOT / derive_namespace_id(
        EVALUATION_ID, "synthetic-preflight-auth", "synthetic-preflight-attempt")
    result = validate_frozen_v3_identity(namespace_root=candidate_root,
                                         identity_root=GLOBAL_OUT_ROOT)
    return {"preflight_type": "STEP9_53_IDENTITY_ONLY_PREFLIGHT", **result,
            "namespace_allocation": "AUTHORIZATION_ATTEMPT_DERIVED_EXCLUSIVE_CONTAINER",
            "authorization_status": "NOT_ISSUED", "prior_treatment_v3_attempt": False,
            "v4_case_executed": 0, "v5_accessed": False}


def run(*, evaluation_id: str, authorization_id: str, attempt_id: str,
        authorization_file: Path, supplied: dict[str, str]) -> None:
    """Delegate only after future authorization; no Step 9.53 invocation uses this."""
    from scripts import run_step9_35a_matched_treatment as parent

    if evaluation_id != EVALUATION_ID or not all(SAFE_ID.fullmatch(value)
                                                 for value in (evaluation_id, authorization_id, attempt_id)):
        raise RuntimeError("invalid or mismatched V3 treatment execution identity")
    from scripts.v3_namespace_allocator import derive_namespace_id, reserve_namespace

    # Probe the derived destination without touching the occupied historical namespace.
    namespace_id = derive_namespace_id(evaluation_id, authorization_id, attempt_id)
    candidate_root = GLOBAL_OUT_ROOT / namespace_id
    validate_frozen_v3_identity(
        lifecycle_phase=PRE_ATTEMPT, authorization_id=authorization_id,
        attempt_id=attempt_id, authorization_file=authorization_file,
        namespace_root=candidate_root, identity_root=GLOBAL_OUT_ROOT,
    )
    validator_bindings = _authoritative_authorization_bindings()
    parent.validate_authorization(authorization_file, evaluation_id, authorization_id,
                                  attempt_id, supplied, run_root=candidate_root,
                                  frozen=validator_bindings)
    from scripts.v3_execution_transaction import (
        LOCK_PATH as TRANSACTION_LOCK_PATH, RUN_ROOT as TRANSACTION_RUN_ROOT,
        TRANSACTION_ROOT, begin_and_commit,
    )

    transaction_id = f"txn-v3-{uuid.uuid4().hex}"
    freeze, _, _ = resolve_current_freeze(ROOT)

    def revalidate_under_lock() -> dict[str, Any]:
        validate_frozen_v3_identity(
            lifecycle_phase=PRE_ATTEMPT, authorization_id=authorization_id,
            attempt_id=attempt_id, authorization_file=authorization_file,
            namespace_root=candidate_root, identity_root=GLOBAL_OUT_ROOT,
        )
        fresh_bindings = _authoritative_authorization_bindings()
        parent.validate_authorization(
            authorization_file, evaluation_id, authorization_id, attempt_id, supplied,
            run_root=candidate_root, frozen=fresh_bindings,
        )
        return read_json(authorization_file)

    begin_and_commit(
        transaction_root=TRANSACTION_ROOT, lock_path=TRANSACTION_LOCK_PATH,
        run_root=TRANSACTION_RUN_ROOT,
        bindings={
            "transaction_id": transaction_id,
            "authorization_id": authorization_id,
            "attempt_id": attempt_id,
            "namespace_id": namespace_id,
            "runner_sha256": validator_bindings["treatment_runner_sha256"],
            "agent_sha256": validator_bindings["treatment_agent_sha256"],
            "evaluation_identity_sha256": freeze["bound_identities_sha256"],
            "case_set_sha256": validator_bindings["case_order_fingerprint_sha256"],
        },
        authorization_state=read_json(authorization_file),
        revalidate_under_lock=revalidate_under_lock,
    )
    allocated_id, candidate_root = reserve_namespace(
        GLOBAL_OUT_ROOT, evaluation_id, authorization_id, attempt_id,
        transaction_id=transaction_id)
    if allocated_id != namespace_id:
        raise RuntimeError("derived namespace identity changed during allocation")
    original_loader = parent.current_frozen_bindings
    binding_call_count = 0

    def fresh_v3_bindings() -> dict[str, Any]:
        nonlocal binding_call_count
        binding_call_count += 1
        # The parent validates before claiming and before creating its ledger,
        # then again after case-set verification and before case 1.
        phase = (PRE_ATTEMPT if binding_call_count <= 2
                else POST_ATTEMPT_CREATION_PRE_FIRST_CASE)
        validate_frozen_v3_identity(
            lifecycle_phase=phase, authorization_id=authorization_id,
            attempt_id=attempt_id, authorization_file=authorization_file,
            namespace_root=candidate_root, identity_root=GLOBAL_OUT_ROOT,
            transaction_id=transaction_id,
        )
        pins = _current_evaluation_bindings()
        if not pins["all_frozen_hashes_match"]:
            raise RuntimeError("V3 treatment identity changed before case access")
        return pins

    parent.current_frozen_bindings = fresh_v3_bindings
    try:
        parent.run(evaluation_id, authorization_id, attempt_id, authorization_file, supplied,
                   transaction_id=transaction_id, execution_root=candidate_root)
    finally:
        parent.current_frozen_bindings = original_loader


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Step 9.53 frozen V3 treatment identity adapter")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--preflight", action="store_true")
    action.add_argument("--execute", action="store_true")
    parser.add_argument("--evaluation-id")
    parser.add_argument("--authorization-id")
    parser.add_argument("--attempt-id")
    parser.add_argument("--authorization-file", type=Path)
    for name in ("treatment-agent-sha256", "benchmark-sha256", "harness-sha256",
                 "scoring-sha256", "metric-registry-sha256", "one-shot-rules-sha256",
                 "matched-protocol-sha256"):
        parser.add_argument("--" + name)
    args = parser.parse_args(argv)
    if args.preflight:
        print(json.dumps(preflight(), ensure_ascii=False, sort_keys=True, indent=2))
        return
    required = (args.evaluation_id, args.authorization_id, args.attempt_id, args.authorization_file,
                args.treatment_agent_sha256, args.benchmark_sha256, args.harness_sha256,
                args.scoring_sha256, args.metric_registry_sha256, args.one_shot_rules_sha256,
                args.matched_protocol_sha256)
    if not all(required):
        parser.error("--execute requires all identity IDs, authorization file, and frozen hash arguments")
    supplied = {
        "treatment_agent_sha256": args.treatment_agent_sha256,
        "benchmark_sha256": args.benchmark_sha256,
        "harness_sha256": args.harness_sha256,
        "scoring_sha256": args.scoring_sha256,
        "metric_registry_sha256": args.metric_registry_sha256,
        "one_shot_rules_sha256": args.one_shot_rules_sha256,
        "matched_protocol_sha256": args.matched_protocol_sha256,
    }
    run(evaluation_id=args.evaluation_id, authorization_id=args.authorization_id,
        attempt_id=args.attempt_id, authorization_file=args.authorization_file, supplied=supplied)


if __name__ == "__main__":
    main()
