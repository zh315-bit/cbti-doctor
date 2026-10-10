"""Issue one r7 V3 authorization; never execute, consume, or reserve an attempt."""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import yaml

from scripts.append_only_ledger import prefix_matches as lifecycle_prefix_matches
from scripts import authorization_lifecycle as lifecycle
from scripts import preflight_step9_62b_mac_local as historical
from scripts import run_step9_53_v3_identity_adapter as adapter
from scripts.run_step9_35a_matched_treatment import verify_case_order
from scripts.v3_namespace_allocator import derive_namespace_id

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "evaluation/v1_2_3"
RUN_ROOT = ROOT / "evaluation/v4_runs"
FREEZE_PATH = ARTIFACTS / "step9_63a_r1_v3_runner_freeze_r7.json"
OLD_AUTH_PATH = ARTIFACTS / "step9_62_v3_authorization_manifest.json"
MANIFEST_PATH = ARTIFACTS / "step9_63a_r3_v3_authorization_manifest.json"
EXPECTED_R7_SHA256 = "99ab870303e45497bf750b55f8382912089c2cf80e737b780922695d9906275c"
EXPECTED_DISTRIBUTION = {
    "KNOWLEDGE_QA": 10, "CAUSE_ASSESSMENT": 10,
    "PERSONALIZED_DECISION": 10, "DATA_ANALYSIS": 10,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def historical_pins_match() -> int:
    """Check 54 immutable files and the frozen prefix of the append-only ledger."""
    inventory = read_json(ARTIFACTS / "step9_60a_v3_historical_integrity_audit.json")
    if inventory.get("step9_58_provenance_gap") != "PRESENT_AND_DOCUMENTED":
        raise RuntimeError("Step 9.58 provenance state mismatch")
    pins = {}
    for pin in inventory["historical_pins"].values():
        digest = sha256(ROOT / pin["path"])
        if digest != pin["sha256"] or pin.get("match") is not True:
            raise RuntimeError("historical pin mismatch")
        pins[pin["path"]] = digest
    ledger = (ARTIFACTS / "authorization_lifecycle_events.jsonl").read_bytes()
    prefix_length = 1161
    prefix_sha256 = "ca168f6939c4697a7a7bccc0b365b414d9a0e632f40de4242eb0a47e2d985285"
    if not lifecycle_prefix_matches(ledger, prefix_length, prefix_sha256):
        raise RuntimeError("historical lifecycle ledger prefix mismatch or truncation")
    lifecycle_path = "evaluation/v1_2_3/authorization_lifecycle_events.jsonl"
    for path, expected in historical.SUPPLEMENTAL_HISTORICAL_PINS.items():
        if path.endswith("authorization_lifecycle_events.jsonl"):
            continue  # The frozen 1161-byte prefix is validated above; suffix is append-only.
        digest = sha256(ROOT / path)
        if digest != expected:
            raise RuntimeError("historical supplemental pin mismatch")
        pins[path] = digest
    pins[lifecycle_path] = prefix_sha256
    if len(pins) != 55:
        raise RuntimeError("historical pin inventory mismatch")
    return len(pins)


def validate_current() -> tuple[dict, dict]:
    """Read-only current identity and retirement gates; never sends a prompt."""
    freeze = read_json(FREEZE_PATH)
    old = read_json(OLD_AUTH_PATH)
    if sha256(FREEZE_PATH) != EXPECTED_R7_SHA256 or freeze.get("runner_freeze_revision") != "r7":
        raise RuntimeError("r7 runner freeze mismatch")
    preflight = adapter.preflight()
    if (preflight.get("all_frozen_hashes_match") is not True
            or preflight.get("runner_sha256") != freeze["runner_sha256"]
            or preflight.get("treatment_agent_sha256") != freeze["v3_agent_sha256"]):
        raise RuntimeError("current V3 runner/Agent/evaluation identity mismatch")
    if sha256(OLD_AUTH_PATH) != "7f97f9e42b8711a6ae745e4626d81fa8787a162bbfa8fdad6fe53c9fd4b975c8":
        raise RuntimeError("old authorization manifest changed")
    event = lifecycle.authorization_retirement_event(old["authorization_id"])
    if (event is None or event.get("final_status") != lifecycle.RETIRED
            or event.get("authorization_consumed") is not False
            or event.get("authorization_consumption_count") != 0):
        raise RuntimeError("old authorization is not terminally retired")
    determination = read_json(Path(event["reuse_determination"]))
    if (sha256(Path(event["reuse_determination"])) != event["reuse_determination_sha256"]
            or determination.get("retirement_reason") != "SUPERSEDED_RUNNER_FREEZE"
            or determination.get("old_runner_freeze_sha256") != old["runner_freeze_sha256"]
            or determination.get("current_runner_freeze_sha256") != EXPECTED_R7_SHA256):
        raise RuntimeError("superseded runner retirement provenance mismatch")
    if historical.active_authorizations(ROOT):
        raise RuntimeError("an executable V3 authorization already exists")
    if historical_pins_match() != 55:
        raise RuntimeError("historical pin inventory mismatch")
    r2 = read_json(ARTIFACTS / "step9_63a_r2_fresh_r7_authorization_eligibility_audit.json")
    if r2.get("ready_for_fresh_r7_authorization_issue") is not True:
        raise RuntimeError("r2 eligibility was not established")
    cases = yaml.safe_load((ROOT / old["benchmark_path"]).read_bytes())["cases"]
    counts = {task: sum(case["task_type"] == task for case in cases)
              for task in EXPECTED_DISTRIBUTION}
    if (len(cases) != 40 or counts != EXPECTED_DISTRIBUTION
            or not verify_case_order([case["case_id"] for case in cases], 40,
                                     old["case_order_fingerprint_sha256"])):
        raise RuntimeError("frozen case set/order/distribution mismatch")
    if any(freeze["bound_identities"].get(key) != old.get(key) for key in (
        "benchmark_sha256", "scoring_sha256", "scoring_rubric_sha256",
        "metric_registry_sha256", "rag_configuration_fingerprint_sha256",
        "model_configuration_fingerprint_sha256", "tool_adapter_sha256",
    )):
        raise RuntimeError("frozen scoring/model/tool/RAG identity mismatch")
    if (sha256(ROOT / freeze["transaction_contract_path"])
            != freeze["transaction_contract_sha256"]
            or sha256(ROOT / freeze["authorization_lifecycle_contract_path"])
            != freeze["authorization_lifecycle_contract_sha256"]):
        raise RuntimeError("lifecycle or transaction contract mismatch")
    return freeze, old


def build_manifest(freeze: dict, old: dict, authorization_id: str,
                   attempt_id: str, namespace_id: str) -> dict:
    """Retain frozen evaluation semantics while replacing every execution binding."""
    manifest = json.loads(json.dumps(old))
    manifest.update({
        "artifact_type": "TREATMENT_V3_FRESH_R7_ONE_SHOT_V4_AUTHORIZATION",
        "step": "9.63a-r3",
        "authorized_by": "User-authorized Step 9.63a-r3 Fresh r7 Authorization Issuance Only",
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "authorization_id": authorization_id,
        "attempt_id": attempt_id,
        "runner_freeze_revision": "r7",
        "runner_freeze_path": FREEZE_PATH.relative_to(ROOT).as_posix(),
        "runner_freeze_sha256": sha256(FREEZE_PATH),
        "runner_path": freeze["runner_path"],
        "runner_sha256": freeze["runner_sha256"],
        "treatment_runner_sha256": freeze["runner_sha256"],
        "parent_runner_path": freeze["parent_runner"]["path"],
        "parent_runner_sha256": freeze["parent_runner"]["sha256"],
        "namespace_allocator_path": freeze["namespace_allocator_path"],
        "namespace_allocator_sha256": freeze["namespace_allocator_sha256"],
        "authorization_lifecycle_module_sha256": freeze["authorization_lifecycle_module_sha256"],
        "authorization_lifecycle_contract_path": freeze["authorization_lifecycle_contract_path"],
        "authorization_lifecycle_contract_sha256": freeze["authorization_lifecycle_contract_sha256"],
        "transaction_module_path": freeze["transaction_module_path"],
        "transaction_module_sha256": freeze["transaction_module_sha256"],
        "transaction_contract_path": freeze["transaction_contract_path"],
        "transaction_contract_sha256": freeze["transaction_contract_sha256"],
        "authoritative_commit_point": "COMMITTED_FSYNCED_APPEND_ONLY_TRANSACTION_JOURNAL",
        "authoritative_commit_point_contract_sha256": freeze["transaction_contract_sha256"],
        "formal_entry_runner_path": freeze["formal_entry_runner_path"],
        "formal_entry_runner_sha256": freeze["formal_entry_runner_sha256"],
        "frozen_evaluation_identity_sha256": freeze["bound_identities_sha256"],
        "status": "ISSUED_NOT_EXECUTED",
        "authorization_status": "ISSUED_NOT_CONSUMED",
        "consumed": False,
        "consumed_at_utc": None,
        "authorization_consumption_count": 0,
        "attempt_id_status": "PREBOUND_IDENTITY_ONLY_NOT_CREATED",
        "formal_execution_status": "FORMAL_EXECUTION_AUTHORIZED_BUT_NOT_STARTED",
        "connectivity_evidence": {
            "status": "NOT_TESTED_AT_ISSUANCE",
            "fresh_non_consuming_preflight_required_before_execution": True,
        },
        "prerequisite_audits": [
            {"path": "evaluation/v1_2_3/step9_63a_r1_production_integration_audit.json",
             "sha256": sha256(ARTIFACTS / "step9_63a_r1_production_integration_audit.json")},
            {"path": "evaluation/v1_2_3/step9_63a_r2_fresh_r7_authorization_eligibility_audit.json",
             "sha256": sha256(ARTIFACTS / "step9_63a_r2_fresh_r7_authorization_eligibility_audit.json")},
        ],
    })
    manifest["execution_namespace"].update({
        "namespace_id": namespace_id,
        "unique_and_absent_at_issuance": True,
        "reservation_marker_created": False,
        "attempt_namespace_created": False,
        "case_results_created": False,
        "raw_traces_created": False,
    })
    return manifest


def validate_manifest_bindings(manifest: dict, freeze: dict) -> None:
    """Reject a candidate manifest that weakens or contradicts the single r7 pin."""
    expected = {
        "runner_freeze_revision": "r7",
        "runner_freeze_sha256": EXPECTED_R7_SHA256,
        "runner_sha256": freeze["runner_sha256"],
        "treatment_runner_sha256": freeze["runner_sha256"],
        "treatment_agent_sha256": freeze["v3_agent_sha256"],
        "parent_runner_sha256": freeze["parent_runner"]["sha256"],
        "namespace_allocator_sha256": freeze["namespace_allocator_sha256"],
        "authorization_lifecycle_contract_sha256": freeze["authorization_lifecycle_contract_sha256"],
        "authorization_lifecycle_module_sha256": freeze["authorization_lifecycle_module_sha256"],
        "transaction_module_sha256": freeze["transaction_module_sha256"],
        "transaction_contract_sha256": freeze["transaction_contract_sha256"],
        "authoritative_commit_point_contract_sha256": freeze["transaction_contract_sha256"],
        "frozen_evaluation_identity_sha256": freeze["bound_identities_sha256"],
        "case_count": 40,
        "case_order_fingerprint_sha256": freeze["bound_identities"]["case_order_fingerprint_sha256"],
        "case_set_fingerprint_sha256": freeze["bound_identities"]["case_order_fingerprint_sha256"],
        "task_distribution": EXPECTED_DISTRIBUTION,
        "status": "ISSUED_NOT_EXECUTED",
        "authorization_status": "ISSUED_NOT_CONSUMED",
        "consumed": False,
        "consumed_at_utc": None,
        "authorization_consumption_count": 0,
        "attempt_id_status": "PREBOUND_IDENTITY_ONLY_NOT_CREATED",
        "formal_execution_status": "FORMAL_EXECUTION_AUTHORIZED_BUT_NOT_STARTED",
    }
    expected.update({key: freeze["bound_identities"][key] for key in (
        "benchmark_sha256", "benchmark_manifest_sha256", "harness_sha256",
        "scoring_sha256", "scoring_rubric_sha256", "metric_registry_sha256",
        "one_shot_rules_sha256", "matched_protocol_sha256",
        "model_configuration_fingerprint_sha256", "rag_configuration_fingerprint_sha256",
        "tool_adapter_sha256",
    )})
    if any(manifest.get(key) != value for key, value in expected.items()):
        raise RuntimeError("fresh authorization does not bind exact r7 frozen identities")
    if manifest.get("execution_namespace", {}).get("namespace_id") != derive_namespace_id(
        manifest["evaluation_id"], manifest["authorization_id"], manifest["attempt_id"]
    ):
        raise RuntimeError("fresh authorization namespace identity mismatch")


def issue_exactly_once(*, manifest: dict, path: Path, run_root: Path,
                       ledger_path: Path, manifest_root: Path, lock_path: Path,
                       active_ids: Callable[[], list[str]],
                       revalidate: Callable[[], None]) -> str:
    """Reuse the canonical lifecycle lock and uniqueness guard, then O_EXCL/fsync."""
    with lifecycle.lifecycle_lock(lock_path):
        revalidate()
        if active_ids():
            raise RuntimeError("exactly-once issuance rejected: active authorization exists")
        if path.exists() or path.is_symlink():
            raise RuntimeError("authorization manifest target already exists")
        authorization_id = manifest["authorization_id"]
        attempt_id = manifest["attempt_id"]
        evaluation_id = manifest["evaluation_id"]
        lifecycle.assert_fresh_authorization_identity(
            authorization_id=authorization_id, attempt_id=attempt_id,
            evaluation_id=evaluation_id, run_root=run_root,
            ledger_path=ledger_path, manifest_root=manifest_root,
        )
        namespace_id = derive_namespace_id(evaluation_id, authorization_id, attempt_id)
        if manifest["execution_namespace"]["namespace_id"] != namespace_id:
            raise RuntimeError("prebound namespace identity mismatch")
        for candidate in manifest_root.glob("*authorization_manifest.json"):
            if candidate.name.startswith("._"):
                continue
            prior = read_json(candidate)
            if (authorization_id == prior.get("authorization_id")
                    or attempt_id == prior.get("attempt_id")
                    or namespace_id == prior.get("execution_namespace", {}).get("namespace_id")):
                raise RuntimeError("historical authorization/attempt/namespace collision")
        identity_tokens = tuple(json.dumps(value).encode("utf-8") for value in (
            authorization_id, attempt_id, namespace_id,
        ))
        for candidate in manifest_root.glob("*.json*"):
            if candidate.name.startswith("._"):
                continue
            if any(token in candidate.read_bytes() for token in identity_tokens):
                raise RuntimeError("historical artifact identity collision")
        if (run_root / namespace_id).exists() or (run_root / namespace_id).is_symlink():
            raise RuntimeError("physical namespace collision")
        if any((run_root / namespace_id).glob("*")):
            raise RuntimeError("prebound namespace is not absent")
        payload = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                     getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return hashlib.sha256(payload).hexdigest()


def main() -> None:
    if MANIFEST_PATH.exists() or MANIFEST_PATH.is_symlink():
        raise RuntimeError("Step 9.63a-r3 authorization already issued or target occupied")
    freeze, old = validate_current()
    authorization_id = f"auth-step9_63a_r3-{uuid.uuid4().hex}"
    attempt_id = f"attempt-step9_63a_r3-{uuid.uuid4().hex}"
    namespace_id = derive_namespace_id(old["evaluation_id"], authorization_id, attempt_id)
    manifest = build_manifest(freeze, old, authorization_id, attempt_id, namespace_id)
    validate_manifest_bindings(manifest, freeze)
    def revalidate() -> None:
        fresh_freeze, _ = validate_current()
        if fresh_freeze != freeze:
            raise RuntimeError("frozen runner changed before issuance")
        validate_manifest_bindings(manifest, fresh_freeze)
    manifest_sha = issue_exactly_once(
        manifest=manifest, path=MANIFEST_PATH,
        run_root=RUN_ROOT, ledger_path=lifecycle.EVENT_LEDGER_PATH,
        manifest_root=ARTIFACTS, lock_path=lifecycle.LOCK_PATH,
        active_ids=lambda: historical.active_authorizations(ROOT),
        revalidate=revalidate,
    )
    print(json.dumps({"authorization_id": authorization_id,
                      "attempt_id": attempt_id, "namespace_id": namespace_id,
                      "authorization_manifest_sha256": manifest_sha,
                      "consumed": False, "attempt_created": False,
                      "namespace_created": False}, sort_keys=True))


if __name__ == "__main__":
    main()
