#!/usr/bin/env python3
"""Mac-local, non-consuming r7 authorization preflight. No HTTP or inference."""
from __future__ import annotations

import hashlib
import importlib
import ipaddress
import json
import os
import re
import socket
import ssl
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from scripts import authorization_lifecycle as lifecycle  # noqa: E402
from scripts import issue_step9_63a_r3_authorization as issued  # noqa: E402
from scripts import preflight_step9_62b_mac_local as prior  # noqa: E402
from scripts import run_step9_35a_matched_treatment as parent  # noqa: E402
from scripts import run_step9_53_v3_identity_adapter as adapter  # noqa: E402
from scripts import v3_execution_transaction as transaction  # noqa: E402
from scripts.run_step9_35a_matched_treatment import supplied_hash_keys, verify_case_order  # noqa: E402
from scripts.v3_namespace_allocator import derive_namespace_id  # noqa: E402

EXPECTED_ROOT = Path("/Volumes/Elements/cbti-doctor-main")
EXPECTED_PYTHON = EXPECTED_ROOT / ".venv/bin/python"
AUTH_ID = "auth-step9_63a_r3-d53bbaa35b1e4522bc4a5f57d42c8ef7"
ATTEMPT_ID = "attempt-step9_63a_r3-3b66e84b7b1f4f538e87156c85b0e7dd"
NAMESPACE_ID = "heldout-v4-treatment-v3-run-2b23978e98ac414ca26e"
AUTH_SHA256 = "1514438d0afe23a39de2a696e9ea5bd97faac4dd546a88cdbd7b91f450046345"
HOST = "api.deepseek.com"
ARTIFACT = ROOT / "evaluation/v1_2_3/step9_63b_mac_local_final_preclearance.json"
RUN_ROOT = ROOT / "evaluation/v4_runs"


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise RuntimeError(reason)


def _addresses(output: str, *, system: bool = False) -> list[str]:
    found = set()
    for line in output.splitlines():
        value = line.strip()
        if system:
            if not value.startswith("ip_address:"):
                continue
            value = value.partition(":")[2].strip()
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            continue
        if address.is_global:
            found.add(str(address))
    return sorted(found)


def _resolver_command(args: list[str], *, system: bool = False) -> list[str]:
    result = subprocess.run(args, capture_output=True, text=True, timeout=10, check=False)
    return _addresses(result.stdout, system=system) if result.returncode == 0 else []


def connectivity(stage_callback=None) -> dict:
    """DNS plus verified transport; deliberately sends no bytes over TLS."""
    if stage_callback:
        stage_callback("SYSTEM_DNS")
    system = _resolver_command(["dscacheutil", "-q", "host", "-a", "name", HOST], system=True)
    if stage_callback:
        stage_callback("PYTHON_GETADDRINFO")
    try:
        python = sorted({item[4][0] for item in socket.getaddrinfo(
            HOST, 443, type=socket.SOCK_STREAM) if ipaddress.ip_address(item[4][0]).is_global})
    except OSError:
        python = []
    if stage_callback:
        stage_callback("DIG_DEFAULT")
    default = _resolver_command(["dig", "+short", "+time=3", "+tries=1", HOST])
    if stage_callback:
        stage_callback("DIG_GOOGLE")
    google = _resolver_command(["dig", "+short", "+time=3", "+tries=1", "@8.8.8.8", HOST])
    if stage_callback:
        stage_callback("DIG_CLOUDFLARE")
    cloudflare = _resolver_command(["dig", "+short", "+time=3", "+tries=1", "@1.1.1.1", HOST])
    dns = {
        "SYSTEM_DNS_STATUS": "PASS" if system else "FAIL",
        "PYTHON_GETADDRINFO_STATUS": "PASS" if python else "FAIL",
        "DEFAULT_DIG_STATUS": "PASS" if default else "FAIL",
        "GOOGLE_DNS_STATUS": "PASS" if google else "FAIL",
        "CLOUDFLARE_DNS_STATUS": "PASS" if cloudflare else "FAIL",
        "DNS_ADDRESSES": {"system": system, "python": python, "default_dig": default,
                          "google": google, "cloudflare": cloudflare},
    }
    dns_stages = (("SYSTEM_DNS_STATUS", "SYSTEM_DNS"),
                  ("PYTHON_GETADDRINFO_STATUS", "PYTHON_GETADDRINFO"),
                  ("DEFAULT_DIG_STATUS", "DIG_DEFAULT"),
                  ("GOOGLE_DNS_STATUS", "DIG_GOOGLE"),
                  ("CLOUDFLARE_DNS_STATUS", "DIG_CLOUDFLARE"))
    for key, stage in dns_stages:
        if dns[key] != "PASS":
            if stage_callback:
                stage_callback(stage)
            _require(False, "DNS_NOT_READY")
    try:
        if stage_callback:
            stage_callback("TCP_CONNECTION")
        with socket.create_connection((HOST, 443), timeout=8) as raw:
            tcp = "PASS"
            if stage_callback:
                stage_callback("TLS_CONNECTION")
            context = ssl.create_default_context()
            _require(context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname,
                     "TLS_VERIFICATION_DISABLED")
            with context.wrap_socket(raw, server_hostname=HOST) as tls:
                if stage_callback:
                    stage_callback("TLS_CERTIFICATE_VALIDATION")
                certificate = bool(tls.getpeercert())
                version = tls.version()
                _require(certificate and bool(version), "TLS_CERTIFICATE_NOT_VERIFIED")
                # Handshake only: no HTTP request, authorization header, prompt, or API key.
                return {**dns, "TCP_CONNECTION": tcp, "TLS_CONNECTION": "PASS",
                        "TLS_VERSION": version, "TLS_CERTIFICATE_PRESENT": certificate,
                        "TLS_CERTIFICATE_VERIFIED": True}
    except (OSError, ssl.SSLError) as error:
        raise RuntimeError("TRANSPORT_OR_TLS_FAILURE") from error


def _runtime_and_config() -> dict:
    _require(sys.platform == "darwin", "NOT_MACOS")
    _require(Path.cwd().resolve() == EXPECTED_ROOT.resolve()
             and ROOT.resolve() == EXPECTED_ROOT.resolve(), "PROJECT_ROOT_MISMATCH")
    _require(Path(sys.executable).resolve() == EXPECTED_PYTHON.resolve()
             and Path(sys.prefix).resolve() == (ROOT / ".venv").resolve(),
             "PROJECT_VENV_MISMATCH")
    _require((ROOT / ".env").is_file(), "PROJECT_DOTENV_MISSING")
    for name in ("yaml", "dotenv", "langchain_openai"):
        importlib.import_module(name)
    load_dotenv(ROOT / ".env")  # Same non-overriding dotenv behavior as model_config.py.
    key_present = bool(os.getenv("DEEPSEEK_API_KEY", "").strip())
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    parsed = urlsplit(base_url)
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-flash")
    _require(key_present, "API_KEY_MISSING")
    _require(parsed.scheme == "https" and parsed.hostname == HOST
             and parsed.port is None and parsed.username is None
             and parsed.password is None and parsed.path in ("", "/")
             and not parsed.query and not parsed.fragment, "MODEL_BASE_URL_MISMATCH")
    _require(model == "deepseek-flash", "MODEL_PROFILE_MISMATCH")
    return {"PROJECT_ROOT_MATCH": True, "PROJECT_VENV_MATCH": True,
            "DEEPSEEK_API_KEY_PRESENT": True, "DEEPSEEK_BASE_URL_HOST": HOST,
            "DEEPSEEK_MODEL": model}


def _execution_state() -> dict:
    auth = issued.read_json(issued.MANIFEST_PATH)
    freeze = issued.read_json(issued.FREEZE_PATH)
    _require(issued.sha256(issued.MANIFEST_PATH) == AUTH_SHA256, "AUTHORIZATION_MANIFEST_HASH_MISMATCH")
    _require(auth.get("authorization_id") == AUTH_ID
             and auth.get("attempt_id") == ATTEMPT_ID
             and auth.get("execution_namespace", {}).get("namespace_id") == NAMESPACE_ID,
             "AUTHORIZATION_IDENTITY_MISMATCH")
    _require(auth.get("authorization_status") == "ISSUED_NOT_CONSUMED"
             and auth.get("status") == "ISSUED_NOT_EXECUTED"
             and auth.get("consumed") is False
             and auth.get("authorization_consumption_count") == 0,
             "AUTHORIZATION_NOT_ISSUED_UNCONSUMED")
    _require(issued.sha256(issued.FREEZE_PATH) == issued.EXPECTED_R7_SHA256
             and freeze.get("runner_freeze_revision") == "r7", "R7_FREEZE_MISMATCH")
    issued.validate_manifest_bindings(auth, freeze)
    _require(derive_namespace_id(auth["evaluation_id"], AUTH_ID, ATTEMPT_ID) == NAMESPACE_ID,
             "NAMESPACE_BINDING_MISMATCH")
    _require(prior.active_authorizations(ROOT) == [AUTH_ID], "ACTIVE_AUTHORIZATION_MISMATCH")
    old = lifecycle.authorization_retirement_event(
        "auth-step9_62-e796755748e14418b9da641f5d6c15e2")
    _require(old is not None and old.get("final_status") == lifecycle.RETIRED
             and old.get("authorization_consumed") is False
             and old.get("authorization_consumption_count") == 0,
             "OLD_AUTHORIZATION_RETIREMENT_MISMATCH")
    namespace = RUN_ROOT / NAMESPACE_ID
    _require(not namespace.exists() and not namespace.is_symlink(), "NAMESPACE_EXISTS")
    transaction.assert_no_transaction(AUTH_ID)
    _require(not transaction._find_identity(transaction.TRANSACTION_ROOT,
                                           authorization_id=AUTH_ID, attempt_id=ATTEMPT_ID,
                                           namespace_id=NAMESPACE_ID), "TRANSACTION_IDENTITY_COLLISION")
    for marker in RUN_ROOT.rglob(".namespace_allocation.json"):
        value = issued.read_json(marker)
        _require(not any((value.get("authorization_id") == AUTH_ID,
                          value.get("attempt_id") == ATTEMPT_ID,
                          value.get("namespace_id") == NAMESPACE_ID)),
                 "NAMESPACE_RESERVATION_COLLISION")
    for ledger in RUN_ROOT.rglob("attempts.jsonl"):
        for line in ledger.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            value = json.loads(line)
            _require(not any((value.get("authorization_id") == AUTH_ID,
                              value.get("attempt_id") == ATTEMPT_ID,
                              value.get("namespace_id") == NAMESPACE_ID)),
                     "ATTEMPT_LEDGER_COLLISION")
    for path in RUN_ROOT.rglob("*"):
        if path.is_file() and (ATTEMPT_ID in path.name or NAMESPACE_ID in path.name):
            raise RuntimeError("ATTEMPT_RESULT_OR_TRACE_COLLISION")
    _require(issued.historical_pins_match() == 55, "HISTORICAL_PIN_MISMATCH")
    checked = adapter.validate_frozen_v3_identity(
        lifecycle_phase=adapter.PRE_ATTEMPT, authorization_id=AUTH_ID,
        attempt_id=ATTEMPT_ID, authorization_file=issued.MANIFEST_PATH,
        namespace_root=namespace, identity_root=RUN_ROOT)
    _require(checked.get("all_frozen_hashes_match") is True, "FROZEN_IDENTITY_MISMATCH")
    bindings = adapter._authoritative_authorization_bindings()
    supplied = {key: bindings[key] for key in supplied_hash_keys()}
    parent.validate_authorization(issued.MANIFEST_PATH, auth["evaluation_id"],
                                  AUTH_ID, ATTEMPT_ID, supplied,
                                  run_root=namespace, frozen=bindings)
    _require(freeze["bound_identities_sha256"] == auth["frozen_evaluation_identity_sha256"],
             "EVALUATION_IDENTITY_MISMATCH")
    import yaml
    cases = yaml.safe_load((ROOT / auth["benchmark_path"]).read_bytes())["cases"]
    _require(len(cases) == 40 and verify_case_order(
        [case["case_id"] for case in cases], 40, auth["case_order_fingerprint_sha256"]),
        "CASE_SET_OR_ORDER_MISMATCH")
    distribution = {task: sum(case["task_type"] == task for case in cases)
                    for task in issued.EXPECTED_DISTRIBUTION}
    _require(distribution == issued.EXPECTED_DISTRIBUTION, "TASK_DISTRIBUTION_MISMATCH")
    return {"RUNNER_FREEZE_REVISION": "r7", "CURRENT_RUNNER_MATCH": True,
            "V3_AGENT_MATCH": True, "FROZEN_EVALUATION_IDENTITIES_MATCH": True,
            "AUTHORIZATION_ID": AUTH_ID, "AUTHORIZATION_MANIFEST_SHA256": AUTH_SHA256,
            "AUTHORIZATION_STATUS": "ISSUED_NOT_CONSUMED", "AUTHORIZATION_CONSUMED": False,
            "AUTHORIZATION_CONSUMPTION_COUNT": 0,
            "ACTIVE_EXECUTABLE_AUTHORIZATION_COUNT": 1,
            "ATTEMPT_ID": ATTEMPT_ID, "ATTEMPT_EXISTS": False,
            "ATTEMPT_ID_COLLISION": False, "NAMESPACE_ID": NAMESPACE_ID,
            "NAMESPACE_EXISTS": False, "NAMESPACE_RESERVED": False,
            "NAMESPACE_ID_COLLISION": False, "HISTORICAL_PIN_COUNT": 55,
            "HISTORICAL_PIN_MISMATCH_COUNT": 0,
            "STEP9_58_PROVENANCE_GAP": "PRESENT_AND_DOCUMENTED"}


def _write_attestation(payload: dict) -> str:
    """Exclusive preflight evidence only; never creates execution state."""
    data = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd = os.open(ARTIFACT, os.O_CREAT | os.O_EXCL | os.O_WRONLY |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    parent_fd = os.open(ARTIFACT.parent, os.O_RDONLY)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)
    return hashlib.sha256(data).hexdigest()


def run_preflight() -> dict:
    _require(not ARTIFACT.exists() and not ARTIFACT.is_symlink(), "PREFLIGHT_ARTIFACT_EXISTS")
    runtime = _runtime_and_config()
    before = _execution_state()  # Identity and non-consumption gate before transport.
    network = connectivity()
    after = _execution_state()   # Re-read authorization, ledgers, namespace, and all pins.
    _require(before == after, "PRE_POST_STATE_MISMATCH")
    return {**runtime, **after, **network,
            "STEP9_63B_STATUS": "PASS_MAC_LOCAL_FINAL_NON_CONSUMING_PRECLEARANCE",
            "EXECUTION_ENVIRONMENT": "MAC_LOCAL",
            "FORMAL_V4_CASE_EXECUTED": 0, "MODEL_INFERENCE_EXECUTED": False,
            "AGENT_EVALUATION_EXECUTED": False, "RAG_EVALUATION_EXECUTED": False,
            "READY_FOR_STEP9_63C_ATOMIC_FORMAL_EXECUTION": True,
            # Frozen r7 formal entry consumes these read-only preflight fields.
            "status": "PASS_NON_CONSUMING_PREFLIGHT", "authorization_id": AUTH_ID,
            "attempt_id": ATTEMPT_ID, "runner_freeze_sha256": issued.EXPECTED_R7_SHA256,
            "authorization_consumed": False, "attempt_created": False,
            "namespace_created": False, "dns_ready": True, "tcp_ready": True,
            "tls_ready": True, "timestamp_utc": datetime.now(timezone.utc).isoformat()}


def main() -> int:
    try:
        summary = run_preflight()
        digest = _write_attestation(summary)
        summary["PREFLIGHT_ARTIFACT_PATH"] = ARTIFACT.relative_to(ROOT).as_posix()
        summary["PREFLIGHT_ARTIFACT_SHA256"] = digest
        for key, value in summary.items():
            if key in {"DNS_ADDRESSES", "timestamp_utc"} or key[0].islower():
                continue
            if isinstance(value, bool):
                value = "YES" if value else "NO"
            print(f"{key} = {value}")
        return 0
    except Exception as error:
        # Never print exception text: dotenv/transport errors may contain secrets.
        reason = str(error)
        if not isinstance(error, RuntimeError) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", reason):
            reason = "UNEXPECTED_ERROR"
        print(f"STEP9_63B_STATUS = FAIL_CLOSED_{reason}")
        print(f"FAILURE_TYPE = {type(error).__name__}")
        print("READY_FOR_STEP9_63C_ATOMIC_FORMAL_EXECUTION = NO")
        print("FORMAL_V4_CASE_EXECUTED = 0")
        print("MODEL_INFERENCE_EXECUTED = NO")
        print("AGENT_EVALUATION_EXECUTED = NO")
        print("RAG_EVALUATION_EXECUTED = NO")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
