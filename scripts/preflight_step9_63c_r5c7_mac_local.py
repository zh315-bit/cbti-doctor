#!/usr/bin/env python3
"""R10 Mac-local final preflight; non-consuming and never invokes inference."""
from __future__ import annotations

import hashlib
import fcntl
import json
import os
import re
import stat
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
AUTH_PATH = ROOT / "evaluation/v1_2_3/step9_63c_r5c6_r10_v3_authorization_manifest.json"
AUTH_ID = "auth-step9_63c_r5c6-aff5c4b96bb74278a14d3fd08bf8a84e"
ATTEMPT_ID = "attempt-step9_63c_r5c6-3401b701486c4fdeb4019b461d024bd4"
NAMESPACE_ID = "heldout-v4-treatment-v3-run-8e4bd0fd803f31b9e0da"
AUTH_SHA256 = "beac52d1ed3bc11efa02b1a924a8abc7b210171bf5cc1b7910011a6ef9741241"
INVOCATION_REGISTRY_PATH = ROOT / "evaluation/v1_2_3/step9_63c_r5c8f_preflight_invocations.jsonl"
INVOCATION_PRODUCER = "scripts/preflight_step9_63c_r5c7_mac_local.py"
REGISTRY_GENESIS = {"event_type": "PREFLIGHT_INVOCATION_REGISTRY_INITIALIZED",
                    "producer": INVOCATION_PRODUCER, "registry_version": 1}
INVOCATION_ID_RE = re.compile(r"preflight-step9_63c_r5-r5c8b-[0-9a-f]{32}\Z")
EXPECTED_RUNNER_SHA256 = "d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693"
EXPECTED_AGENT_SHA256 = "085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607"
EXPECTED_DISTRIBUTION = {"KNOWLEDGE_QA": 10, "CAUSE_ASSESSMENT": 10,
                         "PERSONALIZED_DECISION": 10, "DATA_ANALYSIS": 10}
FAILURE_STAGES = {
    "CONFIG", "PROJECT_PATH", "VENV", "AUTHORIZATION_VALIDATION", "LIFECYCLE_REDUCER",
    "R10_FREEZE_VALIDATION", "FROZEN_EVALUATION_IDENTITIES", "HISTORICAL_PIN_VALIDATION",
    "INVOCATION_REGISTRY", "PREFLIGHT_TARGET_CHECK", "INVOCATION_REGISTRY_WRITE",
    "SYSTEM_DNS", "PYTHON_GETADDRINFO", "DIG_DEFAULT",
    "DIG_GOOGLE", "DIG_CLOUDFLARE", "TCP_CONNECTION", "TLS_CONNECTION",
    "TLS_CERTIFICATE_VALIDATION", "ARTIFACT_SERIALIZATION", "ARTIFACT_WRITE",
}
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(\b(?:deepseek_api_key|api(?:[_ -]?key)|access[_-]?token|refresh[_-]?token|"
    r"token|password|passwd|secret)\b\s*[=:]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)
_AUTH_HEADER = re.compile(r"(?im)(\bauthorization\s*:\s*)([^\r\n,;]+)")
_HEADERS_BLOCK = re.compile(
    r"(?i)(\b(?:request[_ ]?)?headers?\s*[=:]\s*)(\{[^}]*\}|\[[^]]*\]|[^\r\n]+)"
)
_BEARER = re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/-]+=*")
_SK_TOKEN = re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b")
_URL_CREDENTIALS = re.compile(r"(?i)(https?://)[^/@\s:]+:[^/@\s]+@")


class StageTracker:
    def __init__(self) -> None:
        self.current_stage = "INITIALIZATION"

    def set(self, stage: str) -> None:
        if stage not in FAILURE_STAGES:
            raise ValueError("unknown preflight stage")
        self.current_stage = stage


def run_stage(tracker: StageTracker, stage: str, operation):
    tracker.set(stage)
    return operation()


def sanitize_exception_message(message: str, *, limit: int = 500) -> str:
    """Redact common credential formats without consulting environment secrets."""
    sanitized = str(message)
    sanitized = _AUTH_HEADER.sub(r"\1[REDACTED]", sanitized)
    sanitized = _HEADERS_BLOCK.sub(r"\1[REDACTED_HEADERS]", sanitized)
    sanitized = _BEARER.sub("Bearer [REDACTED]", sanitized)
    sanitized = _SECRET_ASSIGNMENT.sub(r"\1[REDACTED]", sanitized)
    sanitized = _SK_TOKEN.sub("[REDACTED_TOKEN]", sanitized)
    sanitized = _URL_CREDENTIALS.sub(r"\1[REDACTED]@", sanitized)
    return sanitized[:limit]


def failure_payload(stage: str, exc: Exception) -> dict:
    return {
        "STEP9_63C_R5C7C_STATUS": "FAIL_CLOSED_PREFLIGHT_ERROR",
        "STEP9_63C_R5C7E_STATUS": "FAIL_CLOSED_PREFLIGHT_ERROR",
        "FAILURE_STAGE": stage if stage in FAILURE_STAGES else "UNKNOWN",
        "FAILURE_EXCEPTION_TYPE": type(exc).__name__,
        "FAILURE_EXCEPTION_MESSAGE_SANITIZED": sanitize_exception_message(str(exc)),
        "READY_FOR_SINGLE_ATOMIC_FORMAL_EXECUTION": False,
        "authorization_consumed": False,
        "attempt_created": False,
        "namespace_created": False,
        "formal_v4_case_executed": 0,
        "model_inference_executed": False,
        "agent_evaluation_executed": False,
        "rag_evaluation_executed": False,
        "http_inference_request_sent": False,
    }


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_connectivity(value: dict) -> None:
    required = ("SYSTEM_DNS_STATUS", "PYTHON_GETADDRINFO_STATUS", "DEFAULT_DIG_STATUS",
                "GOOGLE_DNS_STATUS", "CLOUDFLARE_DNS_STATUS", "TCP_CONNECTION",
                "TLS_CONNECTION")
    if (any(value.get(key) != "PASS" for key in required)
            or value.get("TLS_CERTIFICATE_PRESENT") is not True
            or value.get("TLS_CERTIFICATE_VERIFIED") is not True):
        raise RuntimeError("CONNECTIVITY_NOT_READY")


def new_preflight_id() -> str:
    return f"preflight-step9_63c_r5-r5c8b-{uuid.uuid4().hex}"


def preflight_path(preflight_id: str) -> Path:
    return ROOT / "evaluation/v1_2_3" / (
        f"step9_63c_r5_{AUTH_ID}_{preflight_id}_mac_local_preclearance.json")


def preflight_target_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


@contextmanager
def _locked_invocation_registry(path: Path, *, exclusive: bool):
    flags = (os.O_RDWR | os.O_APPEND if exclusive else os.O_RDONLY) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise RuntimeError("INVOCATION_REGISTRY_UNREADABLE") from exc
    with os.fdopen(fd, "r+b" if exclusive else "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise RuntimeError("INVOCATION_REGISTRY_INVALID")
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
        yield stream


def _unique_json_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise RuntimeError("INVOCATION_REGISTRY_INVALID")
        value[key] = item
    return value


def _read_invocation_history(stream) -> set[str]:
    stream.seek(0)
    raw = stream.read()
    if not raw.endswith(b"\n"):
        raise RuntimeError("INVOCATION_REGISTRY_INVALID")
    try:
        lines = raw.decode("utf-8").splitlines()
        events = [json.loads(line, object_pairs_hook=_unique_json_object) for line in lines]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("INVOCATION_REGISTRY_INVALID") from exc
    if not events or events[0] != REGISTRY_GENESIS:
        raise RuntimeError("INVOCATION_REGISTRY_INVALID")
    seen = set()
    required = {"event_type", "invocation_id", "created_at_utc", "producer"}
    for event in events[1:]:
        if (not isinstance(event, dict) or set(event) != required
                or event["event_type"] != "PREFLIGHT_INVOCATION_CLAIMED"
                or event["producer"] != INVOCATION_PRODUCER
                or not isinstance(event["invocation_id"], str)
                or not INVOCATION_ID_RE.fullmatch(event["invocation_id"]) or not isinstance(event["created_at_utc"], str)):
            raise RuntimeError("INVOCATION_REGISTRY_INVALID")
        try:
            created = datetime.fromisoformat(event["created_at_utc"])
        except ValueError as exc:
            raise RuntimeError("INVOCATION_REGISTRY_INVALID") from exc
        if created.tzinfo is None or event["invocation_id"] in seen:
            raise RuntimeError("INVOCATION_REGISTRY_INVALID")
        seen.add(event["invocation_id"])
    return seen


def historical_invocation_id_exists(preflight_id: str, *, registry_path: Path = INVOCATION_REGISTRY_PATH) -> bool:
    if not isinstance(preflight_id, str) or not INVOCATION_ID_RE.fullmatch(preflight_id):
        raise RuntimeError("INVALID_PREFLIGHT_INVOCATION_ID")
    with _locked_invocation_registry(registry_path, exclusive=False) as stream:
        return preflight_id in _read_invocation_history(stream)


def claim_new_preflight_invocation(*, registry_path: Path = INVOCATION_REGISTRY_PATH,
                                   set_stage=None) -> tuple[str, Path]:
    """Claim before any preflight work; a failed or interrupted claim is never reusable."""
    with _locked_invocation_registry(registry_path, exclusive=True) as stream:
        preflight_id = new_preflight_id()
        if not INVOCATION_ID_RE.fullmatch(preflight_id):
            raise RuntimeError("INVALID_PREFLIGHT_INVOCATION_ID")
        if preflight_id in _read_invocation_history(stream):
            raise RuntimeError("HISTORICAL_INVOCATION_ID_COLLISION")
        if set_stage:
            set_stage("PREFLIGHT_TARGET_CHECK")
        target = preflight_path(preflight_id)
        if preflight_target_exists(target):
            raise RuntimeError("PREFLIGHT_TARGET_EXISTS")
        event = {"event_type": "PREFLIGHT_INVOCATION_CLAIMED", "invocation_id": preflight_id,
                 "created_at_utc": datetime.now(timezone.utc).isoformat(),
                 "producer": INVOCATION_PRODUCER}
        if set_stage:
            set_stage("INVOCATION_REGISTRY_WRITE")
        stream.write((json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())
    return preflight_id, target


def serialize_payload(payload: dict) -> bytes:
    return (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode()


def write_serialized_exclusive(path: Path, data: bytes) -> str:
    if preflight_target_exists(path):
        raise RuntimeError("PREFLIGHT_TARGET_EXISTS")
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


def write_exclusive(path: Path, payload: dict) -> str:
    return write_serialized_exclusive(path, serialize_payload(payload))


def _runtime(set_stage=None) -> dict:
    if set_stage:
        set_stage("PROJECT_PATH")
    if (sys.platform != "darwin" or Path.cwd().resolve() != ROOT.resolve()
            or ROOT.resolve() != Path("/Volumes/Elements/cbti-doctor-main")):
        raise RuntimeError("MAC_PROJECT_PATH_MISMATCH")
    if set_stage:
        set_stage("VENV")
    if (Path(sys.executable).resolve() != (ROOT / ".venv/bin/python").resolve()
            or Path(sys.prefix).resolve() != (ROOT / ".venv").resolve()):
        raise RuntimeError("MAC_PROJECT_VENV_MISMATCH")
    if set_stage:
        set_stage("CONFIG")
    from dotenv import load_dotenv
    from urllib.parse import urlsplit

    if not (ROOT / ".env").is_file():
        raise RuntimeError("PROJECT_DOTENV_MISSING")
    for module in ("yaml", "dotenv", "langchain_openai"):
        __import__(module)
    load_dotenv(ROOT / ".env", override=False)
    key_present = bool(os.environ.get("DEEPSEEK_API_KEY"))
    base_url = os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
    model = os.environ.get("DEEPSEEK_MODEL") or "deepseek-flash"
    parsed = urlsplit(base_url)
    if not key_present:
        raise RuntimeError("API_CREDENTIAL_MISSING")
    if (parsed.scheme != "https" or parsed.hostname != "api.deepseek.com" or parsed.port
            or parsed.username or parsed.password or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment):
        raise RuntimeError("MODEL_ENDPOINT_CONFIGURATION_MISMATCH")
    if model != "deepseek-flash":
        raise RuntimeError("MODEL_CONFIGURATION_MISMATCH")
    return {"PROJECT_ROOT_MATCH": True, "PROJECT_VENV_MATCH": True,
            "DEEPSEEK_API_KEY_PRESENT": True, "DEEPSEEK_BASE_URL_HOST": parsed.hostname,
            "DEEPSEEK_MODEL": model, "python_executable": str(Path(sys.executable).resolve()),
            "project_root": str(ROOT)}


def _assert_no_transaction_identity_collision(transaction) -> None:
    """Scan journals while recognizing verified macOS AppleDouble sidecars."""
    tx_root = transaction.TRANSACTION_ROOT
    for path in tx_root.glob("*.jsonl"):
        if path.name.startswith("._"):
            companion = path.with_name(path.name[2:])
            try:
                prefix = path.read_bytes()[:4]
            except OSError as exc:
                raise RuntimeError("TRANSACTION_SIDECAR_UNREADABLE") from exc
            # AppleDouble magic; require the real companion journal to exist.
            if prefix != b"\x00\x05\x16\x07" or not companion.is_file() or companion.is_symlink():
                raise RuntimeError("UNRECOGNIZED_TRANSACTION_SIDECAR")
            continue
        try:
            events = transaction.read_events(path)
        except Exception as exc:
            raise RuntimeError("TRANSACTION_JOURNAL_UNREADABLE") from exc
        if any(any(event.get(key) == value for key, value in (
                ("authorization_id", AUTH_ID), ("attempt_id", ATTEMPT_ID),
                ("namespace_id", NAMESPACE_ID))) for event in events):
            raise RuntimeError("TRANSACTION_IDENTITY_COLLISION")


def _snapshot(set_stage=None) -> dict:
    if set_stage:
        set_stage("R10_FREEZE_VALIDATION")
    from scripts import authorization_lifecycle as lifecycle
    from scripts import issue_step9_63a_r3_authorization as issued
    from scripts import run_step9_53_v3_identity_adapter as adapter
    from scripts import v3_execution_transaction as transaction
    from scripts.v3_namespace_allocator import derive_namespace_id
    from scripts.v3_runner_identity import resolve_current_freeze
    from scripts.run_step9_35a_matched_treatment import verify_case_order
    import yaml

    run_root = ROOT / "evaluation/v4_runs"
    freeze, freeze_path, identity = resolve_current_freeze(ROOT)
    runner_sha = _sha(freeze_path)
    if (identity["runner_freeze_revision"] != "r10" or runner_sha != EXPECTED_RUNNER_SHA256
            or freeze.get("member_count") != 20):
        raise RuntimeError("R10_FREEZE_MISMATCH")
    if set_stage:
        set_stage("AUTHORIZATION_VALIDATION")
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    auth_sha = _sha(AUTH_PATH)
    if (auth_sha != AUTH_SHA256 or auth.get("authorization_id") != AUTH_ID
            or auth.get("attempt_id") != ATTEMPT_ID
            or auth.get("execution_namespace", {}).get("namespace_id") != NAMESPACE_ID
            or auth.get("runner_freeze_revision") != "r10"
            or auth.get("runner_freeze_path") != identity["runner_freeze_path"]
            or auth.get("runner_freeze_sha256") != runner_sha
            or auth.get("status") != "ISSUED_NOT_EXECUTED"
            or auth.get("authorization_status") != "ISSUED_NOT_CONSUMED"
            or auth.get("consumed") is not False
            or auth.get("authorization_consumption_count") != 0):
        raise RuntimeError("AUTHORIZATION_BINDING_MISMATCH")
    if set_stage:
        set_stage("LIFECYCLE_REDUCER")
    state = lifecycle.reduce_authorization_lifecycle(
        authorization_id=AUTH_ID, manifest=auth, manifest_path=AUTH_PATH,
        run_root=ROOT / "evaluation/v4_runs")
    if state.get("derived_state") != lifecycle.ISSUED_EXECUTABLE or state.get("executable") is not True:
        raise RuntimeError("AUTHORIZATION_NOT_EXECUTABLE")
    if lifecycle.active_authorizations(ROOT) != [AUTH_ID]:
        raise RuntimeError("ACTIVE_AUTHORIZATION_SET_MISMATCH")
    for old_id, expected_state in (
            ("auth-step9_63a_r3-d53bbaa35b1e4522bc4a5f57d42c8ef7",
             lifecycle.BURNED_PRE_CASE),
            ("auth-step9_63c_r4-4b2749ce10014634ac6de155d37ec6a9",
             lifecycle.RETIRED_STATE)):
        old_manifest = ROOT / "evaluation/v1_2_3" / (
            "step9_63a_r3_v3_authorization_manifest.json" if old_id.startswith("auth-step9_63a")
            else "step9_63c_r4_r8_authorization_manifest.json")
        old = json.loads(old_manifest.read_text(encoding="utf-8"))
        reduced = lifecycle.reduce_authorization_lifecycle(
            authorization_id=old_id, manifest=old, manifest_path=old_manifest,
            run_root=run_root)
        if reduced.get("derived_state") != expected_state or reduced.get("executable") is not False:
            raise RuntimeError("SUPERSEDED_AUTHORIZATION_LIFECYCLE_MISMATCH")
    if derive_namespace_id(auth["evaluation_id"], AUTH_ID, ATTEMPT_ID) != NAMESPACE_ID:
        raise RuntimeError("NAMESPACE_IDENTITY_MISMATCH")
    namespace = run_root / NAMESPACE_ID
    if namespace.exists() or namespace.is_symlink():
        raise RuntimeError("NAMESPACE_ALREADY_EXISTS")
    transaction.assert_no_transaction(AUTH_ID)
    _assert_no_transaction_identity_collision(transaction)
    for marker in run_root.rglob(".namespace_allocation.json"):
        obj = json.loads(marker.read_text(encoding="utf-8"))
        if any(obj.get(k) == v for k, v in (("authorization_id", AUTH_ID),
                ("attempt_id", ATTEMPT_ID), ("namespace_id", NAMESPACE_ID))):
            raise RuntimeError("NAMESPACE_RESERVATION_EXISTS")
    for ledger in run_root.rglob("attempts.jsonl"):
        for line in ledger.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                if item.get("authorization_id") == AUTH_ID or item.get("attempt_id") == ATTEMPT_ID:
                    raise RuntimeError("ATTEMPT_LEDGER_EXISTS")
    if set_stage:
        set_stage("FROZEN_EVALUATION_IDENTITIES")
    checked = adapter.validate_frozen_v3_identity(
        lifecycle_phase=adapter.PRE_ATTEMPT, authorization_id=AUTH_ID,
        attempt_id=ATTEMPT_ID, authorization_file=AUTH_PATH,
        namespace_root=namespace, identity_root=run_root)
    bindings = adapter._authoritative_authorization_bindings()
    if checked.get("all_frozen_hashes_match") is not True or bindings.get("all_frozen_hashes_match") is not True:
        raise RuntimeError("FROZEN_IDENTITIES_MISMATCH")
    if auth.get("treatment_agent_sha256") != EXPECTED_AGENT_SHA256:
        raise RuntimeError("V3_AGENT_MISMATCH")
    if set_stage:
        set_stage("HISTORICAL_PIN_VALIDATION")
    if issued.historical_pins_match() != 55:
        raise RuntimeError("HISTORICAL_PIN_MISMATCH")
    historical_audit = json.loads((ROOT / "evaluation/v1_2_3/step9_63c_r5c5b_lifecycle_reducer_repair_audit.json").read_text())
    history = historical_audit.get("historical_integrity", {})
    if (history.get("step9_58_provenance_gap") != "PRESENT_AND_DOCUMENTED"
            or history.get("pin_count") != 55 or history.get("pin_mismatch_count") != 0):
        raise RuntimeError("STEP958_PROVENANCE_STATE_MISMATCH")
    cases = yaml.safe_load((ROOT / auth["benchmark_path"]).read_bytes())["cases"]
    ids = [case["case_id"] for case in cases]
    if len(cases) != 40 or not verify_case_order(ids, 40, auth["case_order_fingerprint_sha256"]):
        raise RuntimeError("CASE_SET_OR_ORDER_MISMATCH")
    distribution = {task: sum(case["task_type"] == task for case in cases)
                    for task in EXPECTED_DISTRIBUTION}
    if distribution != EXPECTED_DISTRIBUTION:
        raise RuntimeError("TASK_DISTRIBUTION_MISMATCH")
    if _sha(ROOT / auth["benchmark_path"]) != auth["benchmark_sha256"]:
        raise RuntimeError("BENCHMARK_HASH_MISMATCH")
    return {"authorization_sha256": auth_sha, "runner_freeze_sha256": runner_sha,
            "runner_freeze_revision": identity["runner_freeze_revision"],
            "evaluation_id": auth["evaluation_id"],
            "frozen_evaluation_identity_sha256": auth["frozen_evaluation_identity_sha256"],
            "authorization_state": state["derived_state"], "consumed": False,
            "consumption_count": 0, "attempt_exists": False, "namespace_exists": False,
            "namespace_reserved": False, "transaction_started": False,
            "case_count": 40, "case_order_fingerprint_sha256": auth["case_order_fingerprint_sha256"],
            "task_distribution": distribution, "historical_pin_count": 55,
            "step9_58_provenance_gap": "PRESENT_AND_DOCUMENTED",
            "identity_bindings": {k: auth[k] for k in (
                "treatment_agent_sha256", "benchmark_sha256", "harness_sha256",
                "scoring_sha256", "scoring_rubric_sha256", "metric_registry_sha256",
                "one_shot_rules_sha256", "matched_protocol_sha256",
                "model_configuration_fingerprint_sha256", "tool_adapter_sha256",
                "rag_configuration_fingerprint_sha256", "case_set_fingerprint_sha256",
                "case_order_fingerprint_sha256")}}


def derive_connectivity_readiness(network: dict) -> dict[str, bool]:
    dns_ready = all(network.get(key) == "PASS" for key in (
        "SYSTEM_DNS_STATUS", "PYTHON_GETADDRINFO_STATUS", "DEFAULT_DIG_STATUS",
        "GOOGLE_DNS_STATUS", "CLOUDFLARE_DNS_STATUS"))
    tcp_ready = dns_ready and network.get("TCP_CONNECTION") == "PASS"
    tls_ready = (tcp_ready and network.get("TLS_CONNECTION") == "PASS"
                 and network.get("TLS_CERTIFICATE_PRESENT") is True
                 and network.get("TLS_CERTIFICATE_VERIFIED") is True)
    return {"dns_ready": dns_ready, "tcp_ready": tcp_ready, "tls_ready": tls_ready}


def build_preflight_payload(preflight_id: str, before: dict, runtime: dict,
                            network: dict, script_sha256: str) -> dict:
    readiness = derive_connectivity_readiness(network)
    ready = all(readiness.values())
    revision = before["runner_freeze_revision"]
    runner_sha = before["runner_freeze_sha256"]
    auth_sha = before["authorization_sha256"]
    path = preflight_path(preflight_id)
    status = "PASS_NON_CONSUMING_PREFLIGHT" if ready else "FAIL_CLOSED_CONNECTIVITY"
    frozen_status = (f"PASS_{revision.upper()}_MAC_LOCAL_FINAL_NON_CONSUMING_PRECLEARANCE"
                     if ready else "FAIL_CLOSED_CONNECTIVITY")
    identity = before["identity_bindings"]
    return {
        "artifact_type": "STEP9_63C_R5C8B_R10_MAC_LOCAL_NON_CONSUMING_PREFLIGHT",
        "step": "9.63c-r5c8b",
        "producer_contract_target": "FROZEN_R10_FORMAL_PREFLIGHT_CONTRACT",
        "PREFLIGHT_ID": preflight_id,
        "STEP9_63C_R5_STATUS": frozen_status,
        "EXECUTION_ENVIRONMENT": "MAC_LOCAL",
        "AUTHORIZATION_ID": AUTH_ID,
        "AUTHORIZATION_MANIFEST_SHA256": auth_sha,
        "RUNNER_FREEZE_REVISION": revision,
        "RUNNER_AGGREGATE_SHA256": runner_sha,
        "V3_AGENT_SHA256": EXPECTED_AGENT_SHA256,
        "ATTEMPT_ID": ATTEMPT_ID,
        "NAMESPACE_ID": NAMESPACE_ID,
        "AUTHORIZATION_CONSUMED": False,
        "AUTHORIZATION_CONSUMPTION_COUNT": 0,
        "ATTEMPT_CREATED": False,
        "NAMESPACE_CREATED": False,
        "NAMESPACE_RESERVED": False,
        "HTTP_REQUEST_SENT": False,
        "MODEL_INFERENCE_EXECUTED": False,
        "AGENT_EVALUATION_EXECUTED": False,
        "RAG_EVALUATION_EXECUTED": False,
        "FORMAL_V4_CASE_EXECUTED": 0,
        "READY_FOR_SINGLE_ATOMIC_FORMAL_EXECUTION": ready,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        **network,
        **readiness,
        "status": status,
        "authorization_id": AUTH_ID,
        "attempt_id": ATTEMPT_ID,
        "runner_freeze_sha256": runner_sha,
        "authorization_consumed": False,
        "attempt_created": False,
        "namespace_created": False,
        "preflight_id": preflight_id,
        "namespace_id": NAMESPACE_ID,
        "ready_for_single_atomic_formal_execution": ready,
        "evaluation_id": before["evaluation_id"],
        "authorization_manifest_sha256": auth_sha,
        "runner_freeze_revision": revision,
        "v3_agent_sha256": EXPECTED_AGENT_SHA256,
        "preflight_script_sha256": script_sha256,
        "frozen_evaluation_identity_sha256": before["frozen_evaluation_identity_sha256"],
        "case_count": before["case_count"],
        "case_set_fingerprint_sha256": identity["case_set_fingerprint_sha256"],
        "case_order_fingerprint_sha256": before["case_order_fingerprint_sha256"],
        "task_distribution": before["task_distribution"],
        "identity_bindings": identity,
        "historical_pin_count": before["historical_pin_count"],
        "historical_pin_mismatch_count": 0,
        "step9_58_provenance_gap": before["step9_58_provenance_gap"],
        "preflight_target": path.relative_to(ROOT).as_posix(),
        "authorization_status": "ISSUED_NOT_CONSUMED",
        "authorization_derived_state": "ISSUED_EXECUTABLE",
        "attempt_exists": False,
        "namespace_exists": False,
        "namespace_reserved": False,
        "transaction_started": False,
        "formal_v4_case_executed": 0,
        "model_inference_executed": False,
        "agent_evaluation_executed": False,
        "rag_evaluation_executed": False,
        "http_inference_request_sent": False,
        **runtime,
    }


def main() -> int:
    tracker = StageTracker()
    try:
        tracker.set("INVOCATION_REGISTRY")
        preflight_id, target = claim_new_preflight_invocation(set_stage=tracker.set)
        before = _snapshot(tracker.set)
        runtime = _runtime(tracker.set)
        # Transport-only DNS/TCP/TLS handshake; no API key or payload is sent.
        tracker.set("SYSTEM_DNS")
        from scripts.preflight_step9_63b_mac_local import connectivity
        network = connectivity(stage_callback=tracker.set)
        tracker.set("TLS_CERTIFICATE_VALIDATION")
        validate_connectivity(network)
        after = _snapshot(tracker.set)
        if before != after:
            raise RuntimeError("LIFECYCLE_CHANGED_DURING_PREFLIGHT")
        script_sha = _sha(Path(__file__).resolve())
        payload = build_preflight_payload(preflight_id, before, runtime, network, script_sha)
        tracker.set("ARTIFACT_SERIALIZATION")
        serialized = serialize_payload(payload)
        tracker.set("ARTIFACT_WRITE")
        digest = write_serialized_exclusive(target, serialized)
        print(json.dumps({"STEP9_63C_R5_STATUS": payload["STEP9_63C_R5_STATUS"], "preflight_id": preflight_id,
                          "artifact_path": payload["preflight_target"], "artifact_sha256": digest,
                          "ready_for_single_atomic_formal_execution": payload["READY_FOR_SINGLE_ATOMIC_FORMAL_EXECUTION"]}, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps(failure_payload(tracker.current_stage, exc), sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
