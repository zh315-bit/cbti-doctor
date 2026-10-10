#!/usr/bin/env python3
"""Read-only Mac-local binding/connectivity preflight for the Step 9.62 authorization."""
from __future__ import annotations

import hashlib
import json
import os
import socket
import ssl
import sys
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from dotenv import dotenv_values, load_dotenv

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ROOT = Path("/Volumes/Elements/cbti-doctor-main")
EXPECTED_PYTHON = EXPECTED_ROOT / ".venv/bin/python"
AUTH_ID = "auth-step9_62-e796755748e14418b9da641f5d6c15e2"
ATTEMPT_ID = "attempt-step9_62-6620ce3a79684874a15f5e35eac97938"
NAMESPACE_ID = "heldout-v4-treatment-v3-run-52b2c0c8ebbb06258291"
EVALUATION_ID = "heldout-v4-step9_55a-treatment-v3-20260930-01"
R6_FREEZE = ROOT / "evaluation/v1_2_3/step9_61a_v3_runner_freeze_r6.json"
R6_FREEZE_SHA256 = "4e6c0bf9ed718546ea1efa12ae48324fd5438129ad3cd3860f93bd33037f1593"
AUTH_PATH = ROOT / "evaluation/v1_2_3/step9_62_v3_authorization_manifest.json"
OLD_AUTH_ID = "auth-step9_59b-0f63fb3bd6934e4b9a1c7e5808c24825"
OLD_AUTH_PATH = ROOT / "evaluation/v1_2_3/step9_59b_v3_authorization_manifest.json"
OLD_RETIREMENT_STATUS = "RETIRED_UNCONSUMED_NON_REUSABLE"
EXPECTED_DISTRIBUTION = {
    "KNOWLEDGE_QA": 10, "CAUSE_ASSESSMENT": 10,
    "PERSONALIZED_DECISION": 10, "DATA_ANALYSIS": 10,
}
SUPPLEMENTAL_HISTORICAL_PINS = {
    "evaluation/v1_2_3/step9_55b_safe_test_manifest.json": "751a4202b6859441c5de26080779b645944feb2182911f12e9864cb4be62e7ce",
    "evaluation/v1_2_3/step9_55b_v3_runner_audit.json": "2cb2fd8d5b8313c8e5f8ab5d9920c8c18bc6027779cacc8b8bd39aac856e9680",
    "evaluation/v1_2_3/step9_55b_v3_runner_freeze_r3.json": "581edb8e0091c3dd060735435091be0c5d826b6244a562fa1bfb21a0b3d850fc",
    "evaluation/v1_2_3/step9_55b_v3_runner_preclearance.json": "a2aa8ba41c73ee2f8f76ec1ba2020c4b4449458dd78f1d63e708bb5adec37309",
    "evaluation/v1_2_3/step9_55b_v3_runner_preclearance.md": "626e84d6e111882f789c99ae689e416f87d83b97e39a9f8f2ef33a58cfa273c7",
    "evaluation/v1_2_3/step9_56_v3_authorization_audit.json": "925484ba15ec248f765459e80f0f4d2f78698479806d7ac775a72ff3661fed51",
    "evaluation/v1_2_3/step9_56_v3_authorization_freeze.json": "9a45b3fb85632ad5cc0629f0b77fe479834291d05ffd136ab7d98138b23e7870",
    "evaluation/v1_2_3/step9_56_v3_authorization_manifest.json": "c4baa12b60a2166c03d8d7c98d6aefe1897873141f5b9b18e6c8a4fb795dd606",
    "evaluation/v1_2_3/step9_56_v3_authorization_report.md": "981c9b0ea4e8feed2cbf877ef2307fd4b920b80d77ae94ed6c6b6a713fd99172",
    "evaluation/v1_2_3/step9_61_v3_authorization_audit.json": "8917201996c69ae7f8ac283fdf49391c771a620fc3e6ba08cb8594122df6888d",
    "evaluation/v1_2_3/step9_61_v3_authorization_freeze.json": "9d567bac4a5dcd7c6808c8f9e2e0dae080318ef8d4b6dbf6cb11fec8ef8114e9",
    "evaluation/v1_2_3/step9_61_v3_authorization_manifest.json": "5aeaf9ce3c4f8996e04f1f9e0c8ff578693c1e65da02c113d2fc9de5817df6be",
    "evaluation/v1_2_3/step9_61_v3_authorization_report.md": "044340e6cc19aaef7765f8a6037d37342f87f203c90b7e1a41482179cb1501a6",
    "evaluation/v1_2_3/step9_61a_v3_authorization_lifecycle_contract.json": "addb3880e7141ca14d7b3011cadb439ac83076fa6b7c2b9f28f3b024d3fd1174",
    "evaluation/v1_2_3/step9_61a_v3_runner_freeze_r6.json": R6_FREEZE_SHA256,
    "evaluation/v1_2_3/step9_61a_v3_retirement_event.json": "b04c3630b6b01ccbcd38d1d91810da3ebbb200617f92a497a0eaf877500595ae",
    "evaluation/v1_2_3/step9_61a_v3_validator_audit.json": "43c70ad74968685ddb2329d5dd91c474e7972e14643c24566d81041d5fb79cce",
    "evaluation/v1_2_3/step9_61a_v3_safe_test_report.json": "b7e793afe356bfc722c83cef5ef1137570dff896038d6167e62dd277180eef3b",
    "evaluation/v1_2_3/step9_61a_v3_historical_integrity_audit.json": "9c32844a46852ce246c6f0a70ea21edbf194c4d104ff4769c25e28c0eba341b4",
    "evaluation/v1_2_3/step9_61a_v3_lifecycle_repair_report.md": "416f76f7824a8909111084824423fb10a95c31fbbecd7600e598f91787fd5580",
    "evaluation/v1_2_3/authorization_lifecycle_events.jsonl": "ca168f6939c4697a7a7bccc0b365b414d9a0e632f40de4242eb0a47e2d985285",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path.name}")
    return value


def base_url_host(value: str) -> str:
    parsed = urlsplit(value if "://" in value else f"//{value}")
    return (parsed.hostname or "").lower()


def check_task_distribution(cases: list[dict]) -> bool:
    counts: dict[str, int] = {}
    for case in cases:
        task = case.get("task_type")
        counts[task] = counts.get(task, 0) + 1
    return len(cases) == 40 and counts == EXPECTED_DISTRIBUTION


def authorization_is_issued_unconsumed(manifest: dict) -> bool:
    return (
        manifest.get("authorization_id") == AUTH_ID
        and manifest.get("attempt_id") == ATTEMPT_ID
        and manifest.get("authorization_status") == "ISSUED_NOT_CONSUMED"
        and manifest.get("status") == "ISSUED_NOT_EXECUTED"
        and manifest.get("consumed") is False
        and manifest.get("consumed_at_utc") is None
        and manifest.get("authorization_consumption_count") == 0
        and manifest.get("attempt_id_status") == "PREBOUND_IDENTITY_ONLY_NOT_CREATED"
    )


def historical_hashes(root: Path) -> dict[str, str]:
    inventory_path = root / "evaluation/v1_2_3/step9_60a_v3_historical_integrity_audit.json"
    inventory = read_json(inventory_path)
    if inventory.get("step9_58_provenance_gap") != "PRESENT_AND_DOCUMENTED":
        raise ValueError("Step 9.58 provenance gap state mismatch")
    result = {}
    for pin in inventory.get("historical_pins", {}).values():
        path = root / pin["path"]
        actual = sha256(path)
        if actual != pin.get("sha256") or pin.get("match") is not True:
            raise ValueError(f"historical pin mismatch: {pin['path']}")
        result[pin["path"]] = actual
    for relpath, expected in SUPPLEMENTAL_HISTORICAL_PINS.items():
        actual = sha256(root / relpath)
        if actual != expected:
            raise ValueError(f"historical pin mismatch: {relpath}")
        result[relpath] = actual
    return result


def historical_authorization_hashes(root: Path) -> dict[str, str]:
    paths = list((root / "evaluation/v1_2_3").glob("step*_v3_authorization_manifest.json"))
    paths += list((root / "evaluation/v1_2_3").glob("step*_v3_authorization_freeze.json"))
    paths += [root / "evaluation/v1_2_3/step9_61a_v3_runner_freeze_r6.json"]
    return {p.relative_to(root).as_posix(): sha256(p) for p in sorted(set(paths))}


def consumed_authorization_ids(root: Path) -> set[str]:
    consumed = set()
    for ledger in (root / "evaluation/v4_runs").rglob("attempts.jsonl"):
        for line_number, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("status") == "AUTHORIZATION_CONSUMED":
                consumed.add(event.get("authorization_id"))
    return consumed


def active_authorizations(root: Path) -> list[str]:
    from scripts.authorization_lifecycle import active_authorizations as reduce_active

    return reduce_active(root)


def side_effect_snapshot(root: Path) -> dict:
    namespace = root / "evaluation/v4_runs" / NAMESPACE_ID
    ledger_matches = []
    result_matches = []
    trace_matches = []
    for path in (root / "evaluation/v4_runs").rglob("*"):
        if path.is_file():
            if path.name == "attempts.jsonl" and ATTEMPT_ID in path.read_text(encoding="utf-8"):
                ledger_matches.append(path)
            if ATTEMPT_ID in path.name and path.name.endswith("_case_results.jsonl"):
                result_matches.append(path)
            if ATTEMPT_ID in path.name and path.name.endswith("_raw_traces.jsonl"):
                trace_matches.append(path)
    return {
        "authorization_consumption_count": sum(
            1 for ledger in (root / "evaluation/v4_runs").rglob("attempts.jsonl")
            for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()
            if (lambda event: event.get("authorization_id") == AUTH_ID
                and event.get("status") == "AUTHORIZATION_CONSUMED")(json.loads(line))
        ),
        "attempt_created": bool(ledger_matches),
        "formal_namespace_created": namespace.exists() or namespace.is_symlink(),
        "case_results_created": bool(result_matches),
        "raw_traces_created": bool(trace_matches),
    }


def connectivity(host: str) -> tuple[str, str, str, bool]:
    if host != "api.deepseek.com":
        return "NOT_RUN", "NOT_RUN", "NOT_RUN", False
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError:
        return "FAIL", "NOT_RUN", "NOT_RUN", False
    if not addresses:
        return "FAIL", "NOT_RUN", "NOT_RUN", False
    try:
        raw = socket.create_connection((host, 443), timeout=8)
    except OSError:
        return "PASS", "FAIL", "NOT_RUN", False
    with raw:
        try:
            context = ssl.create_default_context()
            with context.wrap_socket(raw, server_hostname=host) as tls:
                verified = (tls.getpeercert() != {} and context.verify_mode == ssl.CERT_REQUIRED
                            and context.check_hostname)
                return "PASS", "PASS", tls.version() or "UNKNOWN", verified
        except (OSError, ssl.SSLError):
            return "PASS", "PASS", "FAIL", False


def run_preflight() -> dict:
    from scripts import run_step9_35a_matched_treatment as parent
    from scripts import run_step9_53_v3_identity_adapter as adapter
    from scripts.run_step9_35a_matched_treatment import supplied_hash_keys
    from scripts.v3_namespace_allocator import derive_namespace_id
    from scripts.authorization_lifecycle import authorization_retirement_event

    results: dict = {}
    load_dotenv(ROOT / ".env")
    dotenv_path = ROOT / ".env"
    dotenv_contents = dotenv_values(dotenv_path)
    auth = read_json(AUTH_PATH)
    freeze = read_json(R6_FREEZE)
    results["project_root_match"] = ROOT.resolve() == EXPECTED_ROOT
    results["python_executable_match"] = Path(sys.executable).resolve() == EXPECTED_PYTHON.resolve()
    results["runner_freeze_revision"] = freeze.get("runner_freeze_revision")
    results["runner_sha_match"] = (
        freeze.get("runner_freeze_revision") == "r6"
        and sha256(R6_FREEZE) == R6_FREEZE_SHA256
        and sha256(ROOT / freeze["runner_path"]) == freeze.get("runner_sha256")
    )
    agent_sha, agent_ok = adapter.current_v3_agent_identity()
    bindings = adapter._authoritative_authorization_bindings()
    results["v3_agent_match"] = agent_ok and agent_sha == freeze.get("v3_agent_sha256")
    results["frozen_identities_match"] = bindings.get("all_frozen_hashes_match") is True
    results["authorization_lifecycle_contract_match"] = (
        sha256(ROOT / freeze["authorization_lifecycle_contract_path"])
        == freeze.get("authorization_lifecycle_contract_sha256")
    )
    results["authorization_id"] = auth.get("authorization_id")
    results["authorization_status"] = auth.get("authorization_status")
    results["authorization_consumed"] = auth.get("consumed")
    results["authorization_consumption_count"] = auth.get("authorization_consumption_count")
    results["authorization_manifest_match"] = authorization_is_issued_unconsumed(auth)
    results["attempt_id"] = auth.get("attempt_id")
    results["namespace_id"] = auth.get("execution_namespace", {}).get("namespace_id")
    results["namespace_binding_match"] = (
        auth.get("attempt_id") == ATTEMPT_ID
        and auth.get("execution_namespace", {}).get("namespace_id") == NAMESPACE_ID
        and derive_namespace_id(EVALUATION_ID, AUTH_ID, ATTEMPT_ID) == NAMESPACE_ID
    )
    namespace_root = ROOT / "evaluation/v4_runs" / NAMESPACE_ID
    adapted = adapter.validate_frozen_v3_identity(
        lifecycle_phase=adapter.PRE_ATTEMPT, authorization_id=AUTH_ID,
        attempt_id=ATTEMPT_ID, authorization_file=AUTH_PATH,
        namespace_root=namespace_root, identity_root=ROOT / "evaluation/v4_runs",
    )
    supplied = {key: bindings[key] for key in supplied_hash_keys()}
    parent.validate_authorization(
        AUTH_PATH, EVALUATION_ID, AUTH_ID, ATTEMPT_ID, supplied,
        run_root=namespace_root, frozen=bindings,
    )
    results["adapter_pre_attempt_validator_pass"] = adapted.get("all_frozen_hashes_match") is True
    results["parent_authorization_validator_pass"] = True
    old_retirement = authorization_retirement_event(OLD_AUTH_ID)
    results["old_authorization_executable"] = False
    results["old_authorization_retirement_match"] = bool(
        old_retirement and old_retirement.get("final_status") == OLD_RETIREMENT_STATUS
        and old_retirement.get("authorization_consumed") is False
        and old_retirement.get("authorization_consumption_count") == 0
        and sha256(OLD_AUTH_PATH) == "163dc22d36dc97f2159f59f6dfcef9f1497c538149949a94683d00bf84420f44"
    )
    try:
        parent.validate_authorization(
            OLD_AUTH_PATH, EVALUATION_ID, OLD_AUTH_ID,
            "attempt-step9_59b-f3a11b5d44914eb9b335ccec4f1bcf86", {}, frozen=bindings,
        )
        results["old_authorization_validator_rejects"] = False
    except RuntimeError as error:
        results["old_authorization_validator_rejects"] = "retired" in str(error).lower()

    results["historical_hashes_before"] = historical_hashes(ROOT)
    results["historical_authorization_hashes_before"] = historical_authorization_hashes(ROOT)
    side_before = side_effect_snapshot(ROOT)
    distribution_cases = yaml.safe_load((ROOT / auth["benchmark_path"]).read_bytes())["cases"]
    ids = [case["case_id"] for case in distribution_cases]
    from scripts.run_step9_35a_matched_treatment import verify_case_order

    results["case_count"] = len(ids)
    results["case_set_match"] = (
        len(ids) == 40 and auth.get("case_set_fingerprint_sha256")
        == auth.get("case_order_fingerprint_sha256")
        == freeze["frozen_evaluation_identity"]["case_order_fingerprint_sha256"]
    )
    results["case_order_match"] = verify_case_order(
        ids, 40, freeze["frozen_evaluation_identity"]["case_order_fingerprint_sha256"]
    )
    task_counts = {}
    for case in distribution_cases:
        task_counts[case.get("task_type")] = task_counts.get(case.get("task_type"), 0) + 1
    results["task_distribution"] = task_counts
    results["task_distribution_match"] = check_task_distribution(distribution_cases)
    results["historical_hashes_after"] = historical_hashes(ROOT)
    results["historical_authorization_hashes_after"] = historical_authorization_hashes(ROOT)
    side_after = side_effect_snapshot(ROOT)
    results["side_effects_unchanged"] = side_before == side_after and side_after == {
        "authorization_consumption_count": 0,
        "attempt_created": False,
        "formal_namespace_created": False,
        "case_results_created": False,
        "raw_traces_created": False,
    }
    results["side_effects_after"] = side_after
    results["historical_hashes_unchanged"] = (
        results["historical_hashes_before"] == results["historical_hashes_after"]
        and results["historical_authorization_hashes_before"]
        == results["historical_authorization_hashes_after"]
    )
    results["historical_pin_count"] = len(results["historical_hashes_after"])
    step62_history = read_json(ROOT / "evaluation/v1_2_3/step9_62_v3_historical_integrity_audit.json")
    results["historical_integrity"] = (
        results["historical_pin_count"] == 55
        and results["historical_hashes_unchanged"]
        and step62_history.get("historical_pin_mismatch_count") == 0
        and step62_history.get("step9_58_provenance_gap") == "PRESENT_AND_DOCUMENTED"
    )
    results["active_authorization_count"] = len(active_authorizations(ROOT))
    results["active_authorization_is_step9_62"] = active_authorizations(ROOT) == [AUTH_ID]
    results["dotenv_loaded"] = (
        dotenv_path.is_file() and "DEEPSEEK_API_KEY" in dotenv_contents
        and os.environ.get("DEEPSEEK_API_KEY") == dotenv_contents.get("DEEPSEEK_API_KEY")
    )
    results["api_key_present"] = bool(os.environ.get("DEEPSEEK_API_KEY", "").strip())
    results["base_url_host"] = base_url_host(os.environ.get("DEEPSEEK_BASE_URL", ""))
    results["model"] = os.environ.get("DEEPSEEK_MODEL", "")
    results["dns_status"], results["tcp_status"], results["tls_status"], results[
        "tls_certificate_verified"] = connectivity(results["base_url_host"])
    return results


def main() -> int:
    try:
        r = run_preflight()
        ready = all((
            r["project_root_match"], r["python_executable_match"], r["runner_sha_match"],
            r["v3_agent_match"], r["frozen_identities_match"],
            r["authorization_lifecycle_contract_match"], r["authorization_manifest_match"],
            r["namespace_binding_match"], r["adapter_pre_attempt_validator_pass"],
            r["parent_authorization_validator_pass"], r["old_authorization_retirement_match"],
            r["old_authorization_validator_rejects"], r["case_count"] == 40,
            r["case_set_match"], r["case_order_match"], r["task_distribution_match"],
            r["historical_integrity"], r["active_authorization_count"] == 1,
            r["active_authorization_is_step9_62"], r["dotenv_loaded"], r["api_key_present"],
            r["base_url_host"] == "api.deepseek.com", r["model"] == "deepseek-flash",
            r["dns_status"] == "PASS", r["tcp_status"] == "PASS",
            r["tls_certificate_verified"], r["side_effects_unchanged"],
        ))
        fields = {
            "STEP9_62B_STATUS": "PASS_NON_CONSUMING_PREFLIGHT" if ready else "FAIL_CLOSED",
            "PROJECT_ROOT_MATCH": r["project_root_match"],
            "PYTHON_EXECUTABLE_MATCH": r["python_executable_match"],
            "RUNNER_FREEZE_REVISION": r["runner_freeze_revision"],
            "RUNNER_SHA_MATCH": r["runner_sha_match"], "V3_AGENT_MATCH": r["v3_agent_match"],
            "FROZEN_IDENTITIES_MATCH": r["frozen_identities_match"],
            "AUTHORIZATION_LIFECYCLE_CONTRACT_MATCH": r["authorization_lifecycle_contract_match"],
            "AUTHORIZATION_ID": r["authorization_id"], "AUTHORIZATION_STATUS": r["authorization_status"],
            "AUTHORIZATION_CONSUMED": r["authorization_consumed"],
            "AUTHORIZATION_CONSUMPTION_COUNT": r["authorization_consumption_count"],
            "ATTEMPT_ID": r["attempt_id"], "ATTEMPT_CREATED": r["side_effects_after"]["attempt_created"],
            "NAMESPACE_ID": r["namespace_id"], "NAMESPACE_COLLISION": (
                not r["namespace_binding_match"] or r["side_effects_after"]["formal_namespace_created"]
            ),
            "FORMAL_NAMESPACE_CREATED": r["side_effects_after"]["formal_namespace_created"],
            "ACTIVE_EXECUTABLE_AUTHORIZATION_COUNT": r["active_authorization_count"],
            "OLD_AUTHORIZATION_STATUS": OLD_RETIREMENT_STATUS,
            "OLD_AUTHORIZATION_EXECUTABLE": r["old_authorization_executable"],
            "CASE_COUNT": r["case_count"], "CASE_SET_MATCH": r["case_set_match"],
            "CASE_ORDER_MATCH": r["case_order_match"], "TASK_DISTRIBUTION": r["task_distribution"],
            "DOTENV_LOADED": r["dotenv_loaded"], "DEEPSEEK_API_KEY_PRESENT": r["api_key_present"],
            "DEEPSEEK_BASE_URL_HOST": r["base_url_host"], "DEEPSEEK_MODEL": r["model"],
            "DNS_STATUS": r["dns_status"], "TCP_STATUS": r["tcp_status"],
            "TLS_STATUS": r["tls_status"], "TLS_CERTIFICATE_VERIFIED": r["tls_certificate_verified"],
            "AUTHORIZATION_CONSUMPTION_STILL_ZERO": (
                r["side_effects_after"]["authorization_consumption_count"] == 0
            ),
            "CASE_RESULTS_CREATED": r["side_effects_after"]["case_results_created"],
            "RAW_TRACES_CREATED": r["side_effects_after"]["raw_traces_created"],
            "HISTORICAL_AUTHORIZATION_HASHES_UNCHANGED": r["historical_hashes_unchanged"],
            "HISTORICAL_ARTIFACT_INTEGRITY": r["historical_integrity"],
            "STEP9_58_PROVENANCE_GAP": "PRESENT_AND_DOCUMENTED",
            "MODEL_CALL_EXECUTED": "NO", "AGENT_EXECUTED": "NO", "RAG_EXECUTED": "NO",
            "FORMAL_V4_CASE_EXECUTED": 0,
            "READY_FOR_AUTHORIZATION_CONSUMPTION": ready,
        }
        for key, value in fields.items():
            if isinstance(value, bool):
                value = "YES" if value else "NO"
            print(f"{key} = {value}")
        return 0 if ready else 1
    except Exception as error:
        print("STEP9_62B_STATUS = FAIL_CLOSED")
        print(f"FAILURE_TYPE = {type(error).__name__}")
        print("MODEL_CALL_EXECUTED = NO")
        print("AGENT_EXECUTED = NO")
        print("RAG_EXECUTED = NO")
        print("FORMAL_V4_CASE_EXECUTED = 0")
        print("READY_FOR_AUTHORIZATION_CONSUMPTION = False")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
