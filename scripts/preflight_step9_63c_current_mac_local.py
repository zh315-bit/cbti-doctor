#!/usr/bin/env python3
"""Instance-scoped, non-consuming Mac preflight for the resolved V3 freeze."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "evaluation/v1_2_3"
ID_RE = re.compile(r"preflight-step9_63c-[a-z0-9]+-[0-9a-f]{32}\Z")


def new_preflight_id(revision: str = "r9") -> str:
    return f"preflight-step9_63c-{revision}-{uuid.uuid4().hex}"


def artifact_path(authorization_id: str, preflight_id: str,
                  artifact_dir: Path = ARTIFACT_DIR) -> Path:
    if not ID_RE.fullmatch(preflight_id) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}", authorization_id):
        raise RuntimeError("INVALID_PREFLIGHT_IDENTITY")
    return artifact_dir / f"step9_63c_r5_{authorization_id}_{preflight_id}_mac_local_preclearance.json"


def validate_authorization_state(authorization_path: Path) -> tuple[dict, dict, Path]:
    from scripts import authorization_lifecycle as lifecycle
    from scripts import run_step9_53_v3_identity_adapter as adapter
    from scripts import v3_execution_transaction as transaction
    from scripts.v3_namespace_allocator import derive_namespace_id
    from scripts.v3_runner_identity import resolve_current_freeze

    freeze, freeze_path, identity = resolve_current_freeze(ROOT)
    if authorization_path.is_symlink() or not authorization_path.is_file():
        raise RuntimeError("AUTHORIZATION_PATH_INVALID")
    path = authorization_path.resolve(strict=True)
    manifests_root = (ROOT / "evaluation/v1_2_3").resolve()
    if path.is_symlink() or manifests_root not in path.parents:
        raise RuntimeError("AUTHORIZATION_PATH_INVALID")
    auth = json.loads(path.read_text(encoding="utf-8"))
    if (auth.get("runner_freeze_revision") != identity["runner_freeze_revision"]
            or auth.get("runner_freeze_path") != identity["runner_freeze_path"]
            or auth.get("runner_freeze_sha256") != hashlib.sha256(freeze_path.read_bytes()).hexdigest()
            or auth.get("status") != "ISSUED_NOT_EXECUTED"
            or auth.get("authorization_status") != "ISSUED_NOT_CONSUMED"
            or auth.get("consumed") is not False
            or auth.get("authorization_consumption_count") != 0
            or lifecycle.authorization_retirement_event(auth.get("authorization_id")) is not None):
        raise RuntimeError("AUTHORIZATION_FREEZE_BINDING_MISMATCH")
    lifecycle_state = lifecycle.reduce_authorization_lifecycle(
        authorization_id=auth.get("authorization_id"), manifest=auth,
        manifest_path=path, run_root=ROOT / "evaluation/v4_runs")
    if (lifecycle_state.get("derived_state") != lifecycle.ISSUED_EXECUTABLE
            or lifecycle_state.get("executable") is not True):
        raise RuntimeError("AUTHORIZATION_LIFECYCLE_NOT_EXECUTABLE")
    namespace_id = derive_namespace_id(auth["evaluation_id"], auth["authorization_id"], auth["attempt_id"])
    if auth.get("execution_namespace", {}).get("namespace_id") != namespace_id:
        raise RuntimeError("NAMESPACE_BINDING_MISMATCH")
    namespace = ROOT / "evaluation/v4_runs" / namespace_id
    if namespace.exists() or namespace.is_symlink():
        raise RuntimeError("NAMESPACE_ALREADY_EXISTS")
    transaction.assert_no_transaction(auth["authorization_id"])
    active = lifecycle.active_authorizations(ROOT)
    if active != [auth["authorization_id"]]:
        raise RuntimeError("ACTIVE_AUTHORIZATION_MISMATCH")
    for marker in (ROOT / "evaluation/v4_runs").rglob(".namespace_allocation.json"):
        marker_obj = json.loads(marker.read_text(encoding="utf-8"))
        if marker_obj.get("authorization_id") == auth["authorization_id"] or marker_obj.get("attempt_id") == auth["attempt_id"]:
            raise RuntimeError("NAMESPACE_IDENTITY_COLLISION")
    for ledger in (ROOT / "evaluation/v4_runs").rglob("attempts.jsonl"):
        for line in ledger.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("authorization_id") == auth["authorization_id"] or event.get("attempt_id") == auth["attempt_id"]:
                raise RuntimeError("ATTEMPT_IDENTITY_COLLISION")
    if adapter._authoritative_authorization_bindings().get("all_frozen_hashes_match") is not True:
        raise RuntimeError("FROZEN_IDENTITY_MISMATCH")
    return auth, freeze, freeze_path


def build_preflight_payload(*, authorization_path: Path, preflight_id: str,
                            connectivity: dict, runtime: dict) -> dict:
    """Pure payload builder; writes nothing and does not initiate transport."""
    from scripts.v3_runner_identity import resolve_current_freeze

    auth, freeze, freeze_path = validate_authorization_state(authorization_path)
    from scripts.v3_runner_identity import load_identity_config
    identity = load_identity_config(ROOT)
    auth_sha = hashlib.sha256(authorization_path.read_bytes()).hexdigest()
    if (not ID_RE.fullmatch(preflight_id)
            or auth.get("runner_freeze_revision") != identity["runner_freeze_revision"]
            or auth.get("runner_freeze_path") != identity["runner_freeze_path"]
            or auth.get("runner_freeze_sha256") != hashlib.sha256(freeze_path.read_bytes()).hexdigest()
            or auth.get("status") != "ISSUED_NOT_EXECUTED"
            or auth.get("authorization_status") != "ISSUED_NOT_CONSUMED"
            or auth.get("consumed") is not False
            or auth.get("authorization_consumption_count") != 0):
        raise RuntimeError("AUTHORIZATION_FREEZE_BINDING_MISMATCH")
    checks = ("SYSTEM_DNS_STATUS", "PYTHON_GETADDRINFO_STATUS", "DEFAULT_DIG_STATUS",
              "GOOGLE_DNS_STATUS", "CLOUDFLARE_DNS_STATUS", "TCP_CONNECTION", "TLS_CONNECTION")
    if (any(connectivity.get(key) != "PASS" for key in checks)
            or connectivity.get("TLS_CERTIFICATE_VERIFIED") is not True):
        raise RuntimeError("CONNECTIVITY_NOT_READY")
    return {
        **runtime, **connectivity,
        "artifact_type": "V3_INSTANCE_SCOPED_MAC_LOCAL_NON_CONSUMING_PREFLIGHT",
        "step": "9.63c-r5c4", "status": "PASS_NON_CONSUMING_PREFLIGHT",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "PREFLIGHT_ID": preflight_id, "preflight_id": preflight_id,
        "authorization_id": auth["authorization_id"],
        "authorization_manifest_sha256": auth_sha,
        "attempt_id": auth["attempt_id"],
        "evaluation_id": auth["evaluation_id"],
        "runner_freeze_revision": identity["runner_freeze_revision"],
        "runner_freeze_path": identity["runner_freeze_path"],
        "runner_freeze_sha256": hashlib.sha256(freeze_path.read_bytes()).hexdigest(),
        "runner_member_count": freeze["member_count"],
        "execution_environment": "USER_MAC_LOCAL_PROJECT_VENV",
        "EXECUTION_ENVIRONMENT": "MAC_LOCAL",
        "STEP9_63C_R5_STATUS": f"PASS_{identity['runner_freeze_revision'].upper()}_MAC_LOCAL_FINAL_NON_CONSUMING_PRECLEARANCE",
        "RUNNER_FREEZE_REVISION": identity["runner_freeze_revision"],
        "RUNNER_AGGREGATE_SHA256": hashlib.sha256(freeze_path.read_bytes()).hexdigest(),
        "V3_AGENT_SHA256": auth["treatment_agent_sha256"],
        "ATTEMPT_ID": auth["attempt_id"],
        "NAMESPACE_ID": auth["execution_namespace"]["namespace_id"],
        "AUTHORIZATION_ID": auth["authorization_id"],
        "AUTHORIZATION_MANIFEST_SHA256": auth_sha,
        "NAMESPACE_RESERVED": False,
        "AUTHORIZATION_CONSUMED": False,
        "AUTHORIZATION_CONSUMPTION_COUNT": 0,
        "ATTEMPT_CREATED": False, "NAMESPACE_CREATED": False,
        "NAMESPACE_RESERVED": False, "HTTP_REQUEST_SENT": False,
        "MODEL_INFERENCE_EXECUTED": False, "AGENT_EVALUATION_EXECUTED": False,
        "RAG_EVALUATION_EXECUTED": False, "FORMAL_V4_CASE_EXECUTED": 0,
        "READY_FOR_SINGLE_ATOMIC_FORMAL_EXECUTION": True,
        "dns_ready": True, "tcp_ready": True, "tls_ready": True,
        "authorization_consumed": False, "authorization_consumption_count": 0,
        "attempt_created": False, "namespace_created": False,
        "namespace_reserved": False, "http_request_sent": False,
        "model_inference_executed": False, "agent_evaluation_executed": False,
        "rag_evaluation_executed": False, "formal_v4_case_executed": 0,
        "ready_for_single_atomic_formal_execution": True,
    }


def write_preflight(payload: dict, *, artifact_dir: Path = ARTIFACT_DIR) -> tuple[Path, str]:
    """Persist only on explicit preflight invocation, using exclusive creation."""
    if (payload.get("status") != "PASS_NON_CONSUMING_PREFLIGHT"
            or payload.get("ready_for_single_atomic_formal_execution") is not True
            or payload.get("authorization_consumed") is not False
            or payload.get("authorization_consumption_count") != 0
            or payload.get("attempt_created") is not False
            or payload.get("namespace_created") is not False
            or payload.get("namespace_reserved") is not False
            or payload.get("formal_v4_case_executed") != 0
            or payload.get("http_request_sent") is not False):
        raise RuntimeError("PREFLIGHT_NOT_PASSED")
    target = artifact_path(payload["authorization_id"], payload["preflight_id"], artifact_dir)
    data = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    dir_fd = os.open(target.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
    return target, hashlib.sha256(data).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorization-file", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        from scripts import preflight_step9_63b_mac_local as transport
        from dotenv import dotenv_values, load_dotenv
        from scripts.v3_runner_identity import load_identity_config

        load_dotenv(ROOT / ".env", override=False)
        identity = load_identity_config(ROOT)
        key_present = bool(os.environ.get("DEEPSEEK_API_KEY") or
                           dotenv_values(ROOT / ".env").get("DEEPSEEK_API_KEY"))
        runtime = {"credential_present": key_present,
                   "python_executable": os.path.realpath(os.sys.executable),
                   "project_root": str(ROOT)}
        validate_authorization_state(args.authorization_file)
        network = transport.connectivity()
        payload = build_preflight_payload(authorization_path=args.authorization_file,
                                          preflight_id=new_preflight_id(identity["runner_freeze_revision"]),
                                          connectivity=network, runtime=runtime)
        path, digest = write_preflight(payload)
        print(json.dumps({"artifact_path": path.relative_to(ROOT).as_posix(),
                          "artifact_sha256": digest,
                          "preflight_id": payload["preflight_id"],
                          "ready_for_single_atomic_formal_execution": True}, sort_keys=True))
        return 0
    except Exception:
        print("FAIL_CLOSED_PREFLIGHT")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
