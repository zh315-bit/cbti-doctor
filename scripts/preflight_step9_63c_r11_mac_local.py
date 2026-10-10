#!/usr/bin/env python3
"""Versioned r11 preflight evidence producer; import is offline and side-effect free."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import stat
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PRODUCER_PATH = "scripts/preflight_step9_63c_r11_mac_local.py"
REGISTRY_PATH = ROOT / "evaluation/v1_2_3/step9_63c_r11_preflight_invocations.jsonl"
ARTIFACT_DIR = ROOT / "evaluation/v1_2_3"
ID_RE = re.compile(r"preflight-step9_63c_r5-r11-[0-9a-f]{32}\Z")
SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,159}\Z")
SHA_RE = re.compile(r"[0-9a-f]{64}\Z")
GENESIS = "PREFLIGHT_INVOCATION_REGISTRY_INITIALIZED"
CLAIM = "PREFLIGHT_INVOCATION_CLAIMED"
PERSISTED = "PREFLIGHT_ARTIFACT_PERSISTED"
FAILED = "PREFLIGHT_INVOCATION_FAILED"
FIELDS = {
    GENESIS: {"event_type", "registry_version", "created_at_utc", "producer",
              "preflight_script_sha256", "runner_freeze_revision",
              "runner_freeze_path", "runner_freeze_sha256"},
    CLAIM: {"event_type", "invocation_id", "created_at_utc", "producer",
            "preflight_script_sha256", "authorization_id", "attempt_id",
            "evaluation_id", "runner_freeze_revision", "runner_freeze_sha256",
            "benchmark_sha256", "case_order_fingerprint_sha256", "preflight_target"},
    PERSISTED: {"event_type", "invocation_id", "persisted_at_utc",
                "preflight_target", "artifact_sha256"},
    FAILED: {"event_type", "invocation_id", "failed_at_utc", "failure_stage"},
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_line(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise RuntimeError("INVOCATION_REGISTRY_INVALID")
        value[key] = item
    return value


def _timestamp(value: Any) -> bool:
    try:
        return isinstance(value, str) and datetime.fromisoformat(value).tzinfo is not None
    except ValueError:
        return False


def artifact_path(authorization_id: str, preflight_id: str,
                  artifact_dir: Path = ARTIFACT_DIR) -> Path:
    if not isinstance(authorization_id, str) or not SAFE_ID.fullmatch(authorization_id):
        raise RuntimeError("INVALID_AUTHORIZATION_ID")
    if not isinstance(preflight_id, str) or not ID_RE.fullmatch(preflight_id):
        raise RuntimeError("INVALID_PREFLIGHT_ID")
    return artifact_dir / f"step9_63c_r5_{authorization_id}_{preflight_id}_mac_local_preclearance.json"


def parse_registry(raw: bytes, *, freeze_path: str, freeze_sha256: str,
                   producer_sha256: str, root: Path = ROOT) -> dict[str, Any]:
    """Strictly parse the entire mutable log, including records after a claim."""
    if not raw or not raw.endswith(b"\n"):
        raise RuntimeError("INVOCATION_REGISTRY_INVALID")
    claims: dict[str, dict[str, Any]] = {}
    persisted: dict[str, dict[str, Any]] = {}
    failed: set[str] = set()
    claim_end: dict[str, int] = {}
    offset = 0
    for index, line in enumerate(raw.splitlines(keepends=True)):
        try:
            event = json.loads(line.decode("utf-8"), object_pairs_hook=_unique_pairs)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("INVOCATION_REGISTRY_INVALID") from exc
        kind = event.get("event_type") if isinstance(event, dict) else None
        if kind not in FIELDS or set(event) != FIELDS[kind] or canonical_line(event) != line:
            raise RuntimeError("INVOCATION_REGISTRY_INVALID")
        offset += len(line)
        if index == 0:
            if (kind != GENESIS or type(event["registry_version"]) is not int
                    or event["registry_version"] != 2 or not _timestamp(event["created_at_utc"])
                    or event["producer"] != PRODUCER_PATH
                    or event["preflight_script_sha256"] != producer_sha256
                    or event["runner_freeze_revision"] != "r11"
                    or event["runner_freeze_path"] != freeze_path
                    or event["runner_freeze_sha256"] != freeze_sha256):
                raise RuntimeError("INVOCATION_REGISTRY_INVALID")
            continue
        invocation_id = event.get("invocation_id")
        if kind == GENESIS or not isinstance(invocation_id, str) or not ID_RE.fullmatch(invocation_id):
            raise RuntimeError("INVOCATION_REGISTRY_INVALID")
        if kind == CLAIM:
            if (invocation_id in claims or not _timestamp(event["created_at_utc"])
                    or event["producer"] != PRODUCER_PATH
                    or event["preflight_script_sha256"] != producer_sha256
                    or event["runner_freeze_revision"] != "r11"
                    or event["runner_freeze_sha256"] != freeze_sha256
                    or any(not isinstance(event[key], str) or not SAFE_ID.fullmatch(event[key])
                           for key in ("authorization_id", "attempt_id", "evaluation_id"))
                    or any(not isinstance(event[key], str) or not SHA_RE.fullmatch(event[key])
                           for key in ("benchmark_sha256", "case_order_fingerprint_sha256"))
                    or event["preflight_target"] != str(artifact_path(
                        event["authorization_id"], invocation_id,
                        root / "evaluation/v1_2_3").relative_to(root))):
                raise RuntimeError("INVOCATION_REGISTRY_INVALID")
            claims[invocation_id] = event
            claim_end[invocation_id] = offset
        elif kind == PERSISTED:
            if (invocation_id not in claims or invocation_id in persisted or invocation_id in failed
                    or not _timestamp(event["persisted_at_utc"])
                    or event["preflight_target"] != claims[invocation_id]["preflight_target"]
                    or not isinstance(event["artifact_sha256"], str)
                    or not SHA_RE.fullmatch(event["artifact_sha256"])):
                raise RuntimeError("INVOCATION_REGISTRY_INVALID")
            persisted[invocation_id] = event
        else:
            if (invocation_id not in claims or invocation_id in persisted or invocation_id in failed
                    or not _timestamp(event["failed_at_utc"])
                    or not isinstance(event["failure_stage"], str)
                    or not re.fullmatch(r"[A-Z_]{1,64}", event["failure_stage"])):
                raise RuntimeError("INVOCATION_REGISTRY_INVALID")
            failed.add(invocation_id)
    return {"claims": claims, "persisted": persisted, "failed": failed,
            "claim_end": claim_end, "raw": raw}


@contextmanager
def locked_registry(path: Path, *, exclusive: bool):
    flags = (os.O_RDWR | os.O_APPEND if exclusive else os.O_RDONLY) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "r+b" if exclusive else "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise RuntimeError("INVOCATION_REGISTRY_INVALID")
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield stream


def initialize_registry(*, registry_path: Path, freeze_path: str,
                        freeze_sha256: str, producer_sha256: str) -> None:
    """Explicit future initialization only; never called on import or by this step."""
    genesis = {"event_type": GENESIS, "registry_version": 2,
               "created_at_utc": datetime.now(timezone.utc).isoformat(),
               "producer": PRODUCER_PATH, "preflight_script_sha256": producer_sha256,
               "runner_freeze_revision": "r11", "runner_freeze_path": freeze_path,
               "runner_freeze_sha256": freeze_sha256}
    fd = os.open(registry_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(canonical_line(genesis))
        stream.flush()
        os.fsync(stream.fileno())
    dir_fd = os.open(registry_path.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)


def ensure_registry_initialized(*, registry_path: Path, freeze_path: str,
                                freeze_sha256: str, producer_sha256: str,
                                root: Path = ROOT) -> None:
    """Initialize once with O_EXCL, or validate the complete existing history."""
    try:
        initialize_registry(registry_path=registry_path, freeze_path=freeze_path,
                            freeze_sha256=freeze_sha256,
                            producer_sha256=producer_sha256)
    except FileExistsError:
        pass
    with locked_registry(registry_path, exclusive=False) as stream:
        parse_registry(stream.read(), freeze_path=freeze_path,
                       freeze_sha256=freeze_sha256,
                       producer_sha256=producer_sha256, root=root)


def claim_invocation(*, registry_path: Path, authorization: dict[str, Any],
                     freeze_path: str, freeze_sha256: str, producer_sha256: str,
                     preflight_id: str | None = None,
                     artifact_dir: Path = ARTIFACT_DIR) -> tuple[str, Path, int, str]:
    preflight_id = preflight_id or f"preflight-step9_63c_r5-r11-{uuid.uuid4().hex}"
    target = artifact_path(authorization["authorization_id"], preflight_id, artifact_dir)
    if target.is_symlink() or target.exists():
        raise RuntimeError("PREFLIGHT_TARGET_EXISTS")
    event = {"event_type": CLAIM, "invocation_id": preflight_id,
             "created_at_utc": datetime.now(timezone.utc).isoformat(),
             "producer": PRODUCER_PATH, "preflight_script_sha256": producer_sha256,
             "authorization_id": authorization["authorization_id"],
             "attempt_id": authorization["attempt_id"],
             "evaluation_id": authorization["evaluation_id"],
             "runner_freeze_revision": "r11", "runner_freeze_sha256": freeze_sha256,
             "benchmark_sha256": authorization["benchmark_sha256"],
             "case_order_fingerprint_sha256": authorization["case_order_fingerprint_sha256"],
             "preflight_target": str(target.relative_to(artifact_dir.parent.parent))}
    with locked_registry(registry_path, exclusive=True) as stream:
        stream.seek(0)
        raw = stream.read()
        history = parse_registry(raw, freeze_path=freeze_path,
                                 freeze_sha256=freeze_sha256, producer_sha256=producer_sha256,
                                 root=artifact_dir.parent.parent)
        if preflight_id in history["claims"] or target.exists() or target.is_symlink():
            raise RuntimeError("HISTORICAL_PREFLIGHT_ID_OR_TARGET_COLLISION")
        line = canonical_line(event)
        stream.seek(0, os.SEEK_END)
        stream.write(line)
        stream.flush()
        os.fsync(stream.fileno())
        prefix = raw + line
    return preflight_id, target, len(prefix), hashlib.sha256(prefix).hexdigest()


def append_terminal_event(*, registry_path: Path, freeze_path: str, freeze_sha256: str,
                          producer_sha256: str, preflight_id: str, target: Path,
                          artifact_sha256: str | None = None,
                          failure_stage: str | None = None,
                          root: Path = ROOT) -> None:
    with locked_registry(registry_path, exclusive=True) as stream:
        stream.seek(0)
        history = parse_registry(stream.read(), freeze_path=freeze_path,
                                 freeze_sha256=freeze_sha256, producer_sha256=producer_sha256,
                                 root=root)
        claim = history["claims"].get(preflight_id)
        if not claim or preflight_id in history["persisted"] or preflight_id in history["failed"]:
            raise RuntimeError("INVOCATION_TERMINAL_STATE_INVALID")
        if claim["preflight_target"] != str(target.relative_to(root)):
            raise RuntimeError("PREFLIGHT_TARGET_MISMATCH")
        if artifact_sha256 is not None and failure_stage is None:
            if (not SHA_RE.fullmatch(artifact_sha256) or target.is_symlink()
                    or not target.is_file() or sha256_file(target) != artifact_sha256):
                raise RuntimeError("PREFLIGHT_ARTIFACT_SHA_MISMATCH")
            event = {"event_type": PERSISTED, "invocation_id": preflight_id,
                     "persisted_at_utc": datetime.now(timezone.utc).isoformat(),
                     "preflight_target": claim["preflight_target"],
                     "artifact_sha256": artifact_sha256}
        elif failure_stage is not None and artifact_sha256 is None:
            event = {"event_type": FAILED, "invocation_id": preflight_id,
                     "failed_at_utc": datetime.now(timezone.utc).isoformat(),
                     "failure_stage": failure_stage}
        else:
            raise RuntimeError("INVALID_INVOCATION_TERMINAL_EVENT")
        line = canonical_line(event)
        stream.seek(0, os.SEEK_END)
        stream.write(line)
        stream.flush()
        os.fsync(stream.fileno())


def verify_registry_evidence(*, registry_path: Path, freeze_path: str,
                             freeze_sha256: str, producer_sha256: str,
                             authorization: dict[str, Any], preflight: dict[str, Any],
                             preflight_id: str, artifact_path_value: Path,
                             artifact_sha256: str, root: Path = ROOT) -> None:
    with locked_registry(registry_path, exclusive=False) as stream:
        stream.seek(0)
        history = parse_registry(stream.read(), freeze_path=freeze_path,
                                 freeze_sha256=freeze_sha256, producer_sha256=producer_sha256,
                                 root=root)
    claim = history["claims"].get(preflight_id)
    persisted = history["persisted"].get(preflight_id)
    if not claim or not persisted or preflight_id in history["failed"]:
        raise RuntimeError("PREFLIGHT_INVOCATION_PROVENANCE_MISSING")
    prefix_length = history["claim_end"][preflight_id]
    raw = history["raw"]
    if (preflight.get("invocation_registry_claim_prefix_length_bytes") != prefix_length
            or preflight.get("invocation_registry_claim_prefix_sha256")
            != hashlib.sha256(raw[:prefix_length]).hexdigest()):
        raise RuntimeError("PREFLIGHT_INVOCATION_PREFIX_MISMATCH")
    target = str(artifact_path_value.relative_to(root))
    expected = {"authorization_id": authorization["authorization_id"],
                "attempt_id": authorization["attempt_id"],
                "evaluation_id": authorization["evaluation_id"],
                "runner_freeze_revision": "r11", "runner_freeze_sha256": freeze_sha256,
                "benchmark_sha256": authorization["benchmark_sha256"],
                "case_order_fingerprint_sha256": authorization["case_order_fingerprint_sha256"],
                "preflight_script_sha256": producer_sha256,
                "producer": PRODUCER_PATH, "preflight_target": target}
    if (any(claim.get(key) != value for key, value in expected.items())
            or persisted["preflight_target"] != target
            or persisted["artifact_sha256"] != artifact_sha256):
        raise RuntimeError("PREFLIGHT_INVOCATION_IDENTITY_MISMATCH")


def build_preflight_payload(*, authorization: dict[str, Any], authorization_sha256: str,
                            freeze_sha256: str, producer_sha256: str,
                            preflight_id: str, target: Path, prefix_length: int,
                            prefix_sha256: str, connectivity: dict[str, Any],
                            runtime: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    required = ("SYSTEM_DNS_STATUS", "PYTHON_GETADDRINFO_STATUS", "DEFAULT_DIG_STATUS",
                "GOOGLE_DNS_STATUS", "CLOUDFLARE_DNS_STATUS", "TCP_CONNECTION", "TLS_CONNECTION")
    if (any(connectivity.get(key) != "PASS" for key in required)
            or connectivity.get("TLS_CERTIFICATE_PRESENT") is not True
            or connectivity.get("TLS_CERTIFICATE_VERIFIED") is not True):
        raise RuntimeError("PREFLIGHT_CONNECTIVITY_INCOMPLETE")
    namespace_id = authorization["execution_namespace"]["namespace_id"]
    identities = {key: authorization[key] for key in (
        "treatment_agent_sha256", "benchmark_sha256", "harness_sha256",
        "scoring_sha256", "scoring_rubric_sha256", "metric_registry_sha256",
        "one_shot_rules_sha256", "matched_protocol_sha256",
        "model_configuration_fingerprint_sha256", "tool_adapter_sha256",
        "rag_configuration_fingerprint_sha256", "case_set_fingerprint_sha256",
        "case_order_fingerprint_sha256")}
    return {**runtime, **connectivity,
        "artifact_type": "V3_R11_INSTANCE_SCOPED_MAC_LOCAL_NON_CONSUMING_PREFLIGHT",
        "status": "PASS_NON_CONSUMING_PREFLIGHT",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "PREFLIGHT_ID": preflight_id, "preflight_id": preflight_id,
        "preflight_target": str(target.relative_to(root)),
        "preflight_script_sha256": producer_sha256,
        "invocation_registry_claim_prefix_length_bytes": prefix_length,
        "invocation_registry_claim_prefix_sha256": prefix_sha256,
        "STEP9_63C_R5_STATUS": "PASS_R11_MAC_LOCAL_FINAL_NON_CONSUMING_PRECLEARANCE",
        "EXECUTION_ENVIRONMENT": "MAC_LOCAL",
        "AUTHORIZATION_ID": authorization["authorization_id"],
        "authorization_id": authorization["authorization_id"],
        "AUTHORIZATION_MANIFEST_SHA256": authorization_sha256,
        "authorization_manifest_sha256": authorization_sha256,
        "RUNNER_FREEZE_REVISION": "r11", "runner_freeze_revision": "r11",
        "RUNNER_AGGREGATE_SHA256": freeze_sha256,
        "runner_freeze_sha256": freeze_sha256,
        "V3_AGENT_SHA256": authorization["treatment_agent_sha256"],
        "ATTEMPT_ID": authorization["attempt_id"],
        "attempt_id": authorization["attempt_id"],
        "NAMESPACE_ID": namespace_id, "namespace_id": namespace_id,
        "evaluation_id": authorization["evaluation_id"],
        "case_count": authorization["case_count"],
        "case_set_fingerprint_sha256": authorization["case_set_fingerprint_sha256"],
        "case_order_fingerprint_sha256": authorization["case_order_fingerprint_sha256"],
        "task_distribution": authorization["task_distribution"],
        "identity_bindings": identities,
        "AUTHORIZATION_CONSUMED": False, "authorization_consumed": False,
        "AUTHORIZATION_CONSUMPTION_COUNT": 0, "authorization_consumption_count": 0,
        "ATTEMPT_CREATED": False, "attempt_created": False,
        "NAMESPACE_CREATED": False, "namespace_created": False,
        "NAMESPACE_RESERVED": False, "namespace_reserved": False,
        "HTTP_REQUEST_SENT": False, "http_request_sent": False,
        "MODEL_INFERENCE_EXECUTED": False, "model_inference_executed": False,
        "AGENT_EVALUATION_EXECUTED": False, "agent_evaluation_executed": False,
        "RAG_EVALUATION_EXECUTED": False, "rag_evaluation_executed": False,
        "FORMAL_V4_CASE_EXECUTED": 0, "formal_v4_case_executed": 0,
        "READY_FOR_SINGLE_ATOMIC_FORMAL_EXECUTION": True,
        "ready_for_single_atomic_formal_execution": True,
        "dns_ready": True, "tcp_ready": True, "tls_ready": True,
    }


def write_artifact(path: Path, payload: dict[str, Any]) -> str:
    if path.exists() or path.is_symlink():
        raise RuntimeError("PREFLIGHT_TARGET_EXISTS")
    data = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode()
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    dir_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
    return hashlib.sha256(data).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorization-file", required=True, type=Path)
    args = parser.parse_args(argv)
    preflight_id: str | None = None
    target: Path | None = None
    freeze_sha: str | None = None
    producer_sha: str | None = None
    identity: dict[str, str] | None = None
    try:
        from scripts.preflight_step9_63c_current_mac_local import validate_authorization_state
        from scripts.v3_runner_identity import resolve_current_freeze

        freeze, freeze_file, identity = resolve_current_freeze(ROOT)
        producer_sha = sha256_file(Path(__file__))
        if (freeze.get("preflight_producer_path") != PRODUCER_PATH
                or freeze.get("preflight_producer_sha256") != producer_sha):
            raise RuntimeError("PRODUCER_FREEZE_MISMATCH")
        authorization, _, _ = validate_authorization_state(args.authorization_file)
        freeze_sha = sha256_file(freeze_file)
        ensure_registry_initialized(registry_path=REGISTRY_PATH,
                                    freeze_path=identity["runner_freeze_path"],
                                    freeze_sha256=freeze_sha,
                                    producer_sha256=producer_sha)
        preflight_id, target, prefix_len, prefix_sha = claim_invocation(
            registry_path=REGISTRY_PATH, authorization=authorization,
            freeze_path=identity["runner_freeze_path"], freeze_sha256=freeze_sha,
            producer_sha256=producer_sha)
        # All transport and credential-presence work occurs after the durable claim.
        if (sys.platform != "darwin" or ROOT.resolve() != Path("/Volumes/Elements/cbti-doctor-main")
                or Path.cwd().resolve() != ROOT.resolve()
                or Path(sys.executable).resolve() != (ROOT / ".venv/bin/python").resolve()):
            raise RuntimeError("MAC_LOCAL_RUNTIME_MISMATCH")
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env", override=False)
        if not os.environ.get("DEEPSEEK_API_KEY"):
            raise RuntimeError("CREDENTIAL_ABSENT")
        from scripts.preflight_step9_63b_mac_local import connectivity
        network = connectivity()
        payload = build_preflight_payload(
            authorization=authorization, authorization_sha256=sha256_file(args.authorization_file),
            freeze_sha256=freeze_sha, producer_sha256=producer_sha,
            preflight_id=preflight_id, target=target,
            prefix_length=prefix_len, prefix_sha256=prefix_sha,
            connectivity=network, runtime={"project_root": str(ROOT),
                                           "python_executable": str(Path(sys.executable).resolve()),
                                           "credential_present": True})
        # A slow connectivity probe cannot silently carry a superseded binding forward.
        refreshed, _, _ = validate_authorization_state(args.authorization_file)
        refreshed_freeze, refreshed_file, _ = resolve_current_freeze(ROOT)
        if (refreshed != authorization or sha256_file(refreshed_file) != freeze_sha
                or refreshed_freeze.get("preflight_producer_sha256") != producer_sha
                or sha256_file(args.authorization_file) != payload["authorization_manifest_sha256"]):
            raise RuntimeError("PREFLIGHT_BINDING_CHANGED_DURING_PROBE")
        digest = write_artifact(target, payload)
        append_terminal_event(registry_path=REGISTRY_PATH,
                              freeze_path=identity["runner_freeze_path"],
                              freeze_sha256=freeze_sha, producer_sha256=producer_sha,
                              preflight_id=preflight_id, target=target,
                              artifact_sha256=digest)
        print(json.dumps({"preflight_id": preflight_id,
                          "artifact_path": str(target.relative_to(ROOT)),
                          "artifact_sha256": digest}, sort_keys=True))
        return 0
    except Exception:
        # A durable claim is non-reusable even if the failure marker cannot be appended.
        if (preflight_id is not None and target is not None and identity is not None
                and freeze_sha is not None and producer_sha is not None):
            try:
                append_terminal_event(
                    registry_path=REGISTRY_PATH,
                    freeze_path=identity["runner_freeze_path"],
                    freeze_sha256=freeze_sha, producer_sha256=producer_sha,
                    preflight_id=preflight_id, target=target,
                    failure_stage="PREFLIGHT_FAILED")
            except Exception:
                # A corrupt registry remains fail-closed; never rewrite it for recovery.
                pass
        print("FAIL_CLOSED_R11_PREFLIGHT")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
