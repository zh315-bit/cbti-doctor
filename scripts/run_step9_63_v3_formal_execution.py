#!/usr/bin/env python3
"""V3 formal execution entry point, bound to the current transaction runner freeze."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
EXPECTED_AUTHORIZATION_ID = "auth-step9_62-e796755748e14418b9da641f5d6c15e2"
EXPECTED_ATTEMPT_ID = "attempt-step9_62-6620ce3a79684874a15f5e35eac97938"
EXPECTED_NAMESPACE_ID = "heldout-v4-treatment-v3-run-52b2c0c8ebbb06258291"
EXPECTED_EVALUATION_ID = "heldout-v4-step9_55a-treatment-v3-20260930-01"
R6_FREEZE_PATH = "evaluation/v1_2_3/step9_61a_v3_runner_freeze_r6.json"
R6_FREEZE_SHA256 = "4e6c0bf9ed718546ea1efa12ae48324fd5438129ad3cd3860f93bd33037f1593"
AUTH_PATH = "evaluation/v1_2_3/step9_62_v3_authorization_manifest.json"
LIFECYCLE_PATH = "evaluation/v1_2_3/step9_61a_v3_authorization_lifecycle_contract.json"
from scripts.v3_runner_identity import load_identity_config, resolve_current_freeze
HISTORICAL_GAP = "PRESENT_AND_DOCUMENTED"
EXPECTED_DISTRIBUTION = {
    "KNOWLEDGE_QA": 10,
    "CAUSE_ASSESSMENT": 10,
    "PERSONALIZED_DECISION": 10,
    "DATA_ANALYSIS": 10,
}
EXPECTED_PROJECT_ROOT = Path("/Volumes/Elements/cbti-doctor-main")
EXPECTED_PYTHON = EXPECTED_PROJECT_ROOT / ".venv/bin/python"
HISTORICAL_INVENTORY_PATH = "evaluation/v1_2_3/step9_60a_v3_historical_integrity_audit.json"
LIFECYCLE_LEDGER_PATH = "evaluation/v1_2_3/authorization_lifecycle_events.jsonl"
# The ledger is append-only: only its frozen 1161-byte prefix is a historical pin.
LEDGER_PREFIX_LENGTH = 1161
LEDGER_PREFIX_SHA256 = "ca168f6939c4697a7a7bccc0b365b414d9a0e632f40de4242eb0a47e2d985285"
HISTORICAL_PIN_COUNT = 55
# Step 9.63c-r5c10ag (D13-4): the ledger must hold exactly one issuance event for the authorization.
ISSUED_EVENT_TYPE = "AUTHORIZATION_ISSUED"
ISSUANCE_KEY = "authorization_issuance_event_recorded"
ATOMIC_COMMIT_BINDING_FIELDS = (
    "transaction_id", "authorization_id", "attempt_id", "namespace_id", "runner_sha256",
    "agent_sha256", "evaluation_identity_sha256", "case_set_sha256",
)
CRASH_RECONCILIATION_STATES = (
    "before_prepared", "after_prepared", "committing", "committed_pre_claim",
    "claimed_pre_case", "after_case_start", "ambiguous_or_corrupt",
)
LEGACY_PRECOMMIT_KEYS = (
    "project_root_match", "python_runtime_match", "r6_freeze_match", "runner_sha_match",
    "agent_match", "frozen_identities_match", "lifecycle_contract_match",
    "authorization_id_match", "authorization_status_issued_unconsumed",
    "authorization_consumption_count_zero", "exactly_one_active_authorization",
    "active_authorization_is_bound_id", "old_authorization_retired",
    "old_authorization_non_executable", "attempt_id_match", "attempt_absent",
    "namespace_id_match", "namespace_absent", "case_set_match", "case_order_match",
    "task_distribution_match", "historical_integrity_match", "provenance_gap_preserved",
    "fresh_connectivity_pass",
)
# Current-freeze (r11) gate: every key is produced by collect_r11_precommit_state().
R11_PRECOMMIT_KEYS = (
    "project_root_match", "python_runtime_match", "runner_freeze_match",
    "agent_match", "frozen_identities_match", "evaluation_identity_match",
    "lifecycle_contract_match", "authorization_id_match",
    "authorization_status_issued_unconsumed", "authorization_consumption_count_zero",
    "authorization_lifecycle_executable", "exactly_one_active_authorization",
    "active_authorization_is_bound_id", "old_authorization_retired",
    "old_authorization_non_executable", "attempt_id_match", "attempt_absent",
    "namespace_id_match", "namespace_absent", "case_set_match", "case_order_match",
    "task_distribution_match", "historical_integrity_match", "provenance_gap_preserved",
    "fresh_connectivity_pass",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path.name}")
    return value


def validate_preflight_evidence(*, authorization: dict[str, Any], authorization_file: Path,
                                preflight: dict[str, Any], preflight_file: Path,
                                preflight_id: str | None, preflight_sha256: str | None,
                                freeze_sha256: str) -> None:
    """Bind one instance-scoped Mac preflight before any formal execution side effect."""
    if not isinstance(preflight_id, str) or not re.fullmatch(
            r"preflight-step9_63c_r5-[a-z0-9]+-[0-9a-f]{32}", preflight_id):
        raise RuntimeError("invalid preflight instance identity")
    if not isinstance(preflight_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", preflight_sha256):
        raise RuntimeError("preflight SHA-256 must be explicitly pinned")
    expected_path = ROOT / "evaluation/v1_2_3" / (
        f"step9_63c_r5_{authorization['authorization_id']}_{preflight_id}_mac_local_preclearance.json")
    if (preflight_file.is_symlink() or preflight_file.resolve() != expected_path.resolve()
            or sha256(preflight_file) != preflight_sha256):
        raise RuntimeError("preflight path or SHA-256 differs from explicit binding")
    expected = {
        "PREFLIGHT_ID": preflight_id,
        "STEP9_63C_R5_STATUS": (
            f"PASS_{authorization['runner_freeze_revision'].upper()}_"
            "MAC_LOCAL_FINAL_NON_CONSUMING_PRECLEARANCE"),
        "EXECUTION_ENVIRONMENT": "MAC_LOCAL",
        "AUTHORIZATION_ID": authorization["authorization_id"],
        "AUTHORIZATION_MANIFEST_SHA256": sha256(authorization_file),
        "RUNNER_FREEZE_REVISION": authorization["runner_freeze_revision"],
        "RUNNER_AGGREGATE_SHA256": freeze_sha256,
        "V3_AGENT_SHA256": authorization["treatment_agent_sha256"],
        "ATTEMPT_ID": authorization["attempt_id"],
        "NAMESPACE_ID": authorization["execution_namespace"]["namespace_id"],
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
        "READY_FOR_SINGLE_ATOMIC_FORMAL_EXECUTION": True,
    }
    if authorization["runner_freeze_revision"].lower() == "r8":
        expected["R8_RUNNER_AGGREGATE_SHA256"] = freeze_sha256
    if any(preflight.get(key) != value for key, value in expected.items()):
        raise RuntimeError("preflight evidence identity or safety invariant mismatch")
    if any(preflight.get(key) != "PASS" for key in (
            "SYSTEM_DNS_STATUS", "PYTHON_GETADDRINFO_STATUS", "DEFAULT_DIG_STATUS",
            "GOOGLE_DNS_STATUS", "CLOUDFLARE_DNS_STATUS", "TCP_CONNECTION", "TLS_CONNECTION")):
        raise RuntimeError("preflight connectivity evidence is incomplete")
    if (preflight.get("TLS_CERTIFICATE_PRESENT") is not True
            or preflight.get("TLS_CERTIFICATE_VERIFIED") is not True):
        raise RuntimeError("preflight TLS certificate evidence is incomplete")
    try:
        issued = datetime.fromisoformat(authorization["issued_at_utc"])
        checked = datetime.fromisoformat(preflight["timestamp_utc"])
        if issued.tzinfo is None or checked.tzinfo is None or checked <= issued:
            raise ValueError("preflight must postdate authorization")
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("preflight freshness cannot be established") from exc
    if authorization["runner_freeze_revision"] == "r11":
        validate_r11_preflight_provenance(
            authorization=authorization, preflight=preflight,
            preflight_file=preflight_file, preflight_id=preflight_id,
            preflight_sha256=preflight_sha256, freeze_sha256=freeze_sha256,
        )


def validate_r11_preflight_provenance(*, authorization: dict[str, Any],
                                      preflight: dict[str, Any], preflight_file: Path,
                                      preflight_id: str, preflight_sha256: str,
                                      freeze_sha256: str) -> None:
    """Verify producer and durable invocation provenance before adapter.run()."""
    producer_path = "scripts/preflight_step9_63c_r11_mac_local.py"
    freeze, freeze_file, identity = resolve_current_freeze(ROOT)
    producer_file = ROOT / producer_path
    if (identity["runner_freeze_revision"] != "r11"
            or authorization.get("runner_freeze_path") != identity["runner_freeze_path"]
            or authorization.get("runner_freeze_sha256") != freeze_sha256
            or sha256(freeze_file) != freeze_sha256
            or producer_file.is_symlink() or not producer_file.is_file()
            or freeze.get("preflight_producer_path") != producer_path
            or freeze.get("preflight_producer_sha256") != sha256(producer_file)
            or preflight.get("preflight_script_sha256") != sha256(producer_file)):
        raise RuntimeError("r11 producer or runner freeze identity mismatch")
    expected = {
        "preflight_id": preflight_id,
        "preflight_target": str(preflight_file.relative_to(ROOT)),
        "authorization_id": authorization["authorization_id"],
        "attempt_id": authorization["attempt_id"],
        "evaluation_id": authorization["evaluation_id"],
        "runner_freeze_revision": "r11",
        "runner_freeze_sha256": freeze_sha256,
        "case_count": authorization["case_count"],
        "case_set_fingerprint_sha256": authorization["case_set_fingerprint_sha256"],
        "case_order_fingerprint_sha256": authorization["case_order_fingerprint_sha256"],
        "task_distribution": authorization["task_distribution"],
    }
    if (any(preflight.get(key) != value for key, value in expected.items())
            or authorization["case_count"] != 40
            or authorization["task_distribution"] != EXPECTED_DISTRIBUTION):
        raise RuntimeError("r11 preflight artifact identity mismatch")
    bound = preflight.get("identity_bindings")
    identity_keys = (
        "treatment_agent_sha256", "benchmark_sha256", "harness_sha256",
        "scoring_sha256", "scoring_rubric_sha256", "metric_registry_sha256",
        "one_shot_rules_sha256", "matched_protocol_sha256",
        "model_configuration_fingerprint_sha256", "tool_adapter_sha256",
        "rag_configuration_fingerprint_sha256", "case_set_fingerprint_sha256",
        "case_order_fingerprint_sha256",
    )
    if not isinstance(bound, dict) or any(
            bound.get(key) != authorization.get(key) for key in identity_keys):
        raise RuntimeError("r11 preflight frozen evaluation identity mismatch")
    # Import only after the pinned member bytes have been independently verified.
    from scripts.preflight_step9_63c_r11_mac_local import verify_registry_evidence

    verify_registry_evidence(
        registry_path=ROOT / "evaluation/v1_2_3/step9_63c_r11_preflight_invocations.jsonl",
        freeze_path=identity["runner_freeze_path"], freeze_sha256=freeze_sha256,
        producer_sha256=sha256(producer_file), authorization=authorization,
        preflight=preflight, preflight_id=preflight_id,
        artifact_path_value=preflight_file, artifact_sha256=preflight_sha256,
        root=ROOT,
    )


def validate_precommit(state: dict[str, Any],
                       required: tuple[str, ...] = LEGACY_PRECOMMIT_KEYS) -> list[str]:
    """Pure eligibility check; never changes authorization or execution state.

    A key that is absent, not exactly True, or whose check did not execute fails.
    """
    failures = []
    failures.extend(name for name in required if state.get(name) is not True)
    failures.extend(f"check_not_executed:{name}"
                    for name in state.get("checks_not_executed", ()))
    if state.get("authorization_consumption_count") != 0:
        failures.append("authorization_consumption_count")
    if state.get("active_authorization_count") != 1:
        failures.append("active_authorization_count")
    if state.get("case_count") != 40:
        failures.append("case_count")
    if state.get("task_distribution") != EXPECTED_DISTRIBUTION:
        failures.append("task_distribution")
    if state.get("step9_58_provenance_gap") != HISTORICAL_GAP:
        failures.append("step9_58_provenance_gap")
    if state.get("atomic_commit_protocol_match") is not True:
        failures.append("atomic_commit_protocol_match")
    if state.get("crash_reconciliation_protocol_match") is not True:
        failures.append("crash_reconciliation_protocol_match")
    return failures


def classify_commit_state(*, consumed_event: bool, attempt_ledger: bool,
                          namespace_reservation: bool) -> str:
    """Classify crash states without attempting repair, resume, or cleanup."""
    bits = (consumed_event, attempt_ledger, namespace_reservation)
    if bits == (False, False, False):
        return "PRE_COMMIT_UNCONSUMED"
    if bits == (True, True, True):
        return "COMMITTED_EXACTLY_ONCE"
    return "PARTIAL_COMMIT_FAIL_CLOSED_BURNED"


def partial_trace_policy(*, traces_exist: bool, attempt_completed: bool) -> str:
    if traces_exist or attempt_completed:
        return "PRESERVE_APPEND_ONLY_NO_RESUME_OR_RERUN"
    return "NO_PARTIAL_TRACE_STATE"


def verify_historical_pins(root: Path) -> int:
    """Read-only check of the 55 historical pins; raises on any mismatch.

    34 inventory pins + 20 supplemental pins + the frozen prefix of the append-only
    lifecycle ledger (its full-file hash legitimately changes as events are appended).
    """
    from scripts.append_only_ledger import prefix_matches
    from scripts.preflight_step9_62b_mac_local import SUPPLEMENTAL_HISTORICAL_PINS

    inventory = read_json(root / HISTORICAL_INVENTORY_PATH)
    if inventory.get("step9_58_provenance_gap") != HISTORICAL_GAP:
        raise RuntimeError("Step 9.58 provenance gap state mismatch")
    pins: dict[str, str] = {}
    for pin in inventory["historical_pins"].values():
        if pin.get("match") is not True or sha256(root / pin["path"]) != pin["sha256"]:
            raise RuntimeError(f"historical pin mismatch: {pin['path']}")
        pins[pin["path"]] = pin["sha256"]
    for relpath, expected in SUPPLEMENTAL_HISTORICAL_PINS.items():
        if relpath == LIFECYCLE_LEDGER_PATH:
            continue
        if sha256(root / relpath) != expected:
            raise RuntimeError(f"historical pin mismatch: {relpath}")
        pins[relpath] = expected
    if not prefix_matches((root / LIFECYCLE_LEDGER_PATH).read_bytes(),
                          LEDGER_PREFIX_LENGTH, LEDGER_PREFIX_SHA256):
        raise RuntimeError("historical lifecycle ledger prefix mismatch or truncation")
    pins[LIFECYCLE_LEDGER_PATH] = LEDGER_PREFIX_SHA256
    if len(pins) != HISTORICAL_PIN_COUNT:
        raise RuntimeError(f"historical pin count {len(pins)} != {HISTORICAL_PIN_COUNT}")
    return len(pins)


def _superseded_v3_authorizations(root: Path, current_revision: str) -> list[dict[str, Any]]:
    """Reducer view of every V3 authorization bound to a non-current runner revision."""
    from scripts.authorization_lifecycle import reduce_authorization_lifecycle

    rows = []
    for path in sorted((root / "evaluation/v1_2_3").glob("step*authorization_manifest.json")):
        if path.is_symlink():
            raise RuntimeError("authorization manifest symlink")
        manifest = read_json(path)
        aid = manifest.get("authorization_id")
        is_v3 = (manifest.get("treatment") == "TREATMENT_V3" or "_v3_authorization_manifest" in path.name
                 or path.name == "step9_63c_r4_r8_authorization_manifest.json")
        if not is_v3 or not isinstance(aid, str) or manifest.get("runner_freeze_revision") == current_revision:
            continue
        result = reduce_authorization_lifecycle(
            authorization_id=aid, manifest=manifest, manifest_path=path,
            ledger_path=root / LIFECYCLE_LEDGER_PATH, run_root=root / "evaluation/v4_runs",
            transaction_root=root / "evaluation/v4_runs/.execution_transactions")
        rows.append({"authorization_id": aid, "revision": manifest.get("runner_freeze_revision"),
                     "derived_state": result["derived_state"], "executable": result["executable"]})
    return rows


def verify_issuance_event(root: Path, authorization: dict[str, Any],
                          authorization_file: Path) -> tuple[bool, str]:
    """Cross-check the append-only ledger against the manifest on disk.

    Exactly one AUTHORIZATION_ISSUED event must exist for this authorization, no other
    issuance event may reuse its attempt identity, and the event must agree with the
    manifest bytes on disk. A missing, duplicated or inconsistent event is a plain
    False (with a reason); an unreadable ledger raises and is recorded as not executed.
    """
    from scripts import authorization_lifecycle as lifecycle

    issued = [event for event in lifecycle._events(root / LIFECYCLE_LEDGER_PATH)
              if event.get("event_type") == ISSUED_EVENT_TYPE]
    authorization_id = authorization.get("authorization_id")
    mine = [event for event in issued if event.get("authorization_id") == authorization_id]
    if not mine:
        return False, "no AUTHORIZATION_ISSUED event for this authorization"
    if len(mine) != 1:
        return False, f"{len(mine)} AUTHORIZATION_ISSUED events for this authorization"
    event = mine[0]
    if any(other is not event and other.get("attempt_id") == authorization.get("attempt_id")
           for other in issued):
        return False, "another AUTHORIZATION_ISSUED event reuses this attempt identity"
    try:
        manifest_path = authorization_file.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return False, "authorization manifest is outside the repository root"
    expected = {
        "authorization_id": authorization_id,
        "attempt_id": authorization.get("attempt_id"),
        "evaluation_id": authorization.get("evaluation_id"),
        "authorization_manifest_path": manifest_path,
        "authorization_manifest_sha256": sha256(authorization_file),
        "runner_freeze_revision": authorization.get("runner_freeze_revision"),
        "runner_freeze_sha256": authorization.get("runner_freeze_sha256"),
        "authorization_consumed": False,
        "authorization_consumption_count": 0,
    }
    differing = sorted(key for key, value in expected.items() if event.get(key) != value)
    if differing:
        return False, "issuance event differs from the manifest on disk: " + ", ".join(differing)
    return True, "ok"


def validate_issuance_cross_check(state: dict[str, Any]) -> list[str]:
    """Failure list for the issuance cross-check; absent or non-True fails."""
    return [] if state.get(ISSUANCE_KEY) is True else [ISSUANCE_KEY]


def collect_r11_precommit_state(*, args: argparse.Namespace, authorization: dict[str, Any],
                                preflight: dict[str, Any], freeze: dict[str, Any],
                                freeze_path: Path, identity: dict[str, str],
                                preflight_validated: bool, root: Path | None = None,
                                adapter_module: Any = None) -> dict[str, Any]:
    """Read-only r11 precommit facts. Each check runs independently; a check that
    raises is recorded as not executed and evaluates to False (fail closed).

    ``adapter_module`` exists only so offline tests can supply a stand-in; formal
    execution always passes None and therefore imports the frozen identity adapter.
    """
    from scripts import authorization_lifecycle as lifecycle
    from scripts.v3_namespace_allocator import derive_namespace_id

    root = ROOT if root is None else root
    state: dict[str, Any] = {"checks_not_executed": [], "check_errors": {}}

    def check(name: str, function: Any) -> Any:
        try:
            value = function()
        except Exception as error:  # fail closed: record and treat as not satisfied
            state["checks_not_executed"].append(name)
            state["check_errors"][name] = f"{type(error).__name__}: {error}"
            value = False
        state[name] = value
        return value

    def adapter() -> Any:
        if adapter_module is not None:
            return adapter_module
        from scripts import run_step9_53_v3_identity_adapter as frozen_adapter
        return frozen_adapter

    bound = freeze.get("bound_identities", {})
    authorization_id = authorization.get("authorization_id")
    attempt_id = authorization.get("attempt_id")
    run_root = root / "evaluation/v4_runs"
    check("project_root_match", lambda: root.resolve() == EXPECTED_PROJECT_ROOT.resolve())
    check("python_runtime_match", lambda: Path(sys.executable).resolve() == EXPECTED_PYTHON.resolve())
    check("runner_freeze_match", lambda: (
        freeze.get("runner_freeze_revision") == identity["runner_freeze_revision"]
        and freeze.get("status") == "FROZEN_NOT_AUTHORIZED"
        and freeze.get("formal_entry_runner_sha256") == sha256(Path(__file__))
        and authorization.get("runner_freeze_revision") == identity["runner_freeze_revision"]
        and authorization.get("runner_freeze_path") == identity["runner_freeze_path"]
        and authorization.get("runner_freeze_sha256") == sha256(freeze_path)))
    check("agent_match", lambda: (lambda result: result[1] is True
          and result[0] == freeze.get("v3_agent_sha256") == authorization.get("treatment_agent_sha256"))(
              adapter().current_v3_agent_identity()))
    check("frozen_identities_match", lambda: adapter()._authoritative_authorization_bindings()
          .get("all_frozen_hashes_match") is True)
    check("evaluation_identity_match", lambda: (
        authorization.get("frozen_evaluation_identity_sha256") == freeze.get("bound_identities_sha256")))
    check("lifecycle_contract_match", lambda: (
        sha256(root / freeze["authorization_lifecycle_contract_path"]) == freeze["authorization_lifecycle_contract_sha256"]
        and sha256(root / freeze["authorization_lifecycle_module_path"]) == freeze["authorization_lifecycle_module_sha256"]))
    # The commit and crash protocol live in the frozen atomic-commit (transaction) contract.
    transaction_contract = check("transaction_contract", lambda: (
        read_json(root / freeze["transaction_contract_path"])
        if sha256(root / freeze["transaction_contract_path"]) == freeze["transaction_contract_sha256"]
        else {}))
    state.pop("transaction_contract", None)
    check("atomic_commit_protocol_match", lambda: isinstance(transaction_contract, dict)
          and str(transaction_contract.get("commit_point", "")).startswith("COMMITTED")
          and transaction_contract.get("committed_binding_fields") == list(ATOMIC_COMMIT_BINDING_FIELDS))
    check("crash_reconciliation_protocol_match", lambda: isinstance(transaction_contract, dict)
          and set(transaction_contract.get("reconciliation", {})) == set(CRASH_RECONCILIATION_STATES)
          and transaction_contract["reconciliation"]["ambiguous_or_corrupt"]
          == "FAIL_CLOSED_MANUAL_RECONCILIATION_REQUIRED")
    check("authorization_id_match", lambda: authorization_id == args.authorization_id)
    check("authorization_status_issued_unconsumed", lambda: (
        authorization.get("authorization_status") == "ISSUED_NOT_CONSUMED"
        and authorization.get("status") == "ISSUED_NOT_EXECUTED"
        and authorization.get("consumed") is False))
    state["authorization_consumption_count"] = authorization.get("authorization_consumption_count")
    check("authorization_consumption_count_zero", lambda: authorization.get("authorization_consumption_count") == 0)
    check("authorization_lifecycle_executable", lambda: (lambda result: result["derived_state"]
          == lifecycle.ISSUED_EXECUTABLE and result["executable"] is True)(
              lifecycle.reduce_authorization_lifecycle(
                  authorization_id=authorization_id, manifest=authorization,
                  manifest_path=args.authorization_file, ledger_path=root / LIFECYCLE_LEDGER_PATH,
                  run_root=run_root, transaction_root=run_root / ".execution_transactions")))
    # Independent consumer-side recount; never relies on the producer's earlier view.
    active = check("active_authorizations", lambda: lifecycle.active_authorizations(root))
    state["active_authorization_count"] = len(active) if isinstance(active, list) else None
    check("exactly_one_active_authorization", lambda: isinstance(active, list) and len(active) == 1)
    check("active_authorization_is_bound_id", lambda: active == [authorization_id])
    superseded = check("superseded_authorizations",
                       lambda: _superseded_v3_authorizations(root, identity["runner_freeze_revision"]))
    check("old_authorization_retired", lambda: isinstance(superseded, list) and all(
        row["derived_state"] != lifecycle.ISSUED_EXECUTABLE for row in superseded))
    check("old_authorization_non_executable", lambda: isinstance(superseded, list) and all(
        row["executable"] is False for row in superseded))
    check("attempt_id_match", lambda: attempt_id == args.attempt_id)
    check("attempt_absent", lambda: not any(
        json.loads(line).get("attempt_id") == attempt_id or json.loads(line).get("authorization_id") == authorization_id
        for ledger in run_root.rglob("attempts.jsonl")
        for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()))
    namespace_id = check("namespace_id", lambda: derive_namespace_id(
        authorization["evaluation_id"], authorization_id, attempt_id))
    check("namespace_id_match", lambda: isinstance(namespace_id, str)
          and authorization.get("execution_namespace", {}).get("namespace_id") == namespace_id)
    check("namespace_absent", lambda: isinstance(namespace_id, str)
          and not (run_root / namespace_id).exists() and not (run_root / namespace_id).is_symlink())
    state["case_count"] = authorization.get("case_count") if authorization.get("case_count") == bound.get("case_count") else None
    check("case_set_match", lambda: authorization["case_set_fingerprint_sha256"] == bound["case_order_fingerprint_sha256"])
    check("case_order_match", lambda: authorization["case_order_fingerprint_sha256"] == bound["case_order_fingerprint_sha256"])
    state["task_distribution"] = authorization.get("task_distribution")
    check("task_distribution_match", lambda: (
        authorization["task_distribution"] == bound["task_distribution"] == EXPECTED_DISTRIBUTION))
    check("historical_integrity_match", lambda: verify_historical_pins(root) == HISTORICAL_PIN_COUNT)
    state["step9_58_provenance_gap"] = check("provenance_gap_state", lambda: read_json(
        root / HISTORICAL_INVENTORY_PATH).get("step9_58_provenance_gap"))
    check("provenance_gap_preserved", lambda: state["step9_58_provenance_gap"] == HISTORICAL_GAP)
    check("fresh_connectivity_pass", lambda: preflight_validated is True and all(
        preflight.get(key) is True for key in ("dns_ready", "tcp_ready", "tls_ready")))

    def issuance_recorded() -> bool:
        recorded, detail = verify_issuance_event(root, authorization, args.authorization_file)
        state["authorization_issuance_event_detail"] = detail
        return recorded

    check(ISSUANCE_KEY, issuance_recorded)
    return state


def prepare_formal_gates(args: argparse.Namespace) -> dict[str, Any]:
    """All read-only gates of formal execution, in order; never creates state."""
    from scripts.run_step9_35a_matched_treatment import supplied_hash_keys

    freeze, freeze_path, identity = resolve_current_freeze(ROOT)
    if (freeze.get("runner_freeze_revision") != identity["runner_freeze_revision"]
            or freeze.get("status") != "FROZEN_NOT_AUTHORIZED"
            or freeze.get("formal_entry_runner_sha256") != sha256(Path(__file__))):
        raise RuntimeError("current formal entry differs from runner freeze")
    if (args.authorization_file is None or args.preflight_file is None
            or args.preflight_id is None or args.preflight_sha256 is None):
        raise RuntimeError("current authorization and pinned fresh preflight are required")
    authorization = read_json(args.authorization_file)
    preflight = read_json(args.preflight_file)
    if any((authorization.get("runner_freeze_revision") != identity["runner_freeze_revision"],
            authorization.get("runner_freeze_sha256") != sha256(freeze_path),
            authorization.get("authorization_id") != args.authorization_id,
            authorization.get("attempt_id") != args.attempt_id,
            authorization.get("evaluation_id") != args.evaluation_id,
            preflight.get("authorization_id") != args.authorization_id,
            preflight.get("attempt_id") != args.attempt_id,
            preflight.get("runner_freeze_sha256") != sha256(freeze_path),
            preflight.get("status") != "PASS_NON_CONSUMING_PREFLIGHT",
            preflight.get("authorization_consumed") is not False,
            preflight.get("attempt_created") is not False,
            preflight.get("namespace_created") is not False,
            preflight.get("dns_ready") is not True,
            preflight.get("tcp_ready") is not True,
            preflight.get("tls_ready") is not True)):
        raise RuntimeError("authorization or connectivity preflight is not bound to current runner identity")
    validate_preflight_evidence(
        authorization=authorization, authorization_file=args.authorization_file,
        preflight=preflight, preflight_file=args.preflight_file,
        preflight_id=args.preflight_id, preflight_sha256=args.preflight_sha256,
        freeze_sha256=sha256(freeze_path),
    )
    supplied = {key: getattr(args, key) for key in supplied_hash_keys()}
    if not all(isinstance(value, str) and value for value in supplied.values()):
        raise RuntimeError("all frozen hash arguments are required")
    state = collect_r11_precommit_state(
        args=args, authorization=authorization, preflight=preflight, freeze=freeze,
        freeze_path=freeze_path, identity=identity, preflight_validated=True)
    failures = validate_precommit(state, R11_PRECOMMIT_KEYS)
    failures += [name for name in validate_issuance_cross_check(state) if name not in failures]
    return {"state": state, "precommit_failures": failures, "supplied": supplied}


def execute_formal(args: argparse.Namespace) -> None:
    """Only a current-freeze, freshly preflighted authorization that passes every
    precommit check reaches the adapter, whose run() is the first side effect."""
    gates = prepare_formal_gates(args)
    if gates["precommit_failures"]:
        raise RuntimeError("formal precommit gate failed closed: "
                           + ", ".join(gates["precommit_failures"]))
    from scripts import run_step9_53_v3_identity_adapter as adapter

    adapter.run(
        evaluation_id=args.evaluation_id, authorization_id=args.authorization_id,
        attempt_id=args.attempt_id, authorization_file=args.authorization_file,
        supplied=gates["supplied"],
    )


def audit_current_state() -> dict[str, Any]:
    """Read-only identity audit. It deliberately performs no connectivity probe."""
    from scripts import run_step9_35a_matched_treatment as parent
    from scripts import run_step9_53_v3_identity_adapter as adapter
    from scripts import preflight_step9_62b_mac_local as prior
    from scripts.run_step9_35a_matched_treatment import supplied_hash_keys, verify_case_order
    from scripts.v3_namespace_allocator import derive_namespace_id
    from scripts.authorization_lifecycle import authorization_retirement_event

    freeze_path = ROOT / R6_FREEZE_PATH
    auth_path = ROOT / AUTH_PATH
    lifecycle_path = ROOT / LIFECYCLE_PATH
    freeze = read_json(freeze_path)
    auth = read_json(auth_path)
    lifecycle = read_json(lifecycle_path)
    bindings = adapter._authoritative_authorization_bindings()
    current_agent, agent_ok = adapter.current_v3_agent_identity()
    runner_sha_match = sha256(ROOT / freeze["runner_path"]) == freeze.get("runner_sha256")
    r6_match = (
        freeze.get("runner_freeze_revision") == "r6"
        and sha256(freeze_path) == R6_FREEZE_SHA256
        and runner_sha_match
    )
    namespace_id = derive_namespace_id(EXPECTED_EVALUATION_ID,
                                       EXPECTED_AUTHORIZATION_ID, EXPECTED_ATTEMPT_ID)
    namespace_root = ROOT / "evaluation/v4_runs" / namespace_id
    supplied = {key: bindings[key] for key in supplied_hash_keys()}
    adapter_result = adapter.validate_frozen_v3_identity(
        lifecycle_phase=adapter.PRE_ATTEMPT,
        authorization_id=EXPECTED_AUTHORIZATION_ID,
        attempt_id=EXPECTED_ATTEMPT_ID,
        authorization_file=auth_path,
        namespace_root=namespace_root,
        identity_root=ROOT / "evaluation/v4_runs",
    )
    parent.validate_authorization(
        auth_path, EXPECTED_EVALUATION_ID, EXPECTED_AUTHORIZATION_ID,
        EXPECTED_ATTEMPT_ID, supplied, run_root=namespace_root, frozen=bindings,
    )
    import yaml

    cases = yaml.safe_load((ROOT / auth["benchmark_path"]).read_bytes())["cases"]
    case_ids = [case["case_id"] for case in cases]
    distribution: dict[str, int] = {}
    for case in cases:
        task = case.get("task_type")
        distribution[task] = distribution.get(task, 0) + 1
    old_retirement = authorization_retirement_event(
        "auth-step9_59b-0f63fb3bd6934e4b9a1c7e5808c24825"
    )
    historical = prior.historical_hashes(ROOT)
    historical_auth_before = prior.historical_authorization_hashes(ROOT)
    active = prior.active_authorizations(ROOT)
    try:
        parent.validate_authorization(
            ROOT / "evaluation/v1_2_3/step9_59b_v3_authorization_manifest.json",
            EXPECTED_EVALUATION_ID,
            "auth-step9_59b-0f63fb3bd6934e4b9a1c7e5808c24825",
            "attempt-step9_59b-f3a11b5d44914eb9b335ccec4f1bcf86",
            {}, frozen=bindings,
        )
        old_rejected = False
    except RuntimeError as error:
        old_rejected = "retired" in str(error).lower()

    # A second read-only pass proves the audit itself did not alter historical
    # pins or authorization artifacts. No files are created by this module.
    historical_after = prior.historical_hashes(ROOT)
    historical_auth_after = prior.historical_authorization_hashes(ROOT)
    history_unchanged = historical == historical_after and historical_auth_before == historical_auth_after

    contract_commit = lifecycle.get("formal_execution_commit_protocol")
    state = {
        "project_root_match": ROOT.resolve() == Path("/Volumes/Elements/cbti-doctor-main"),
        "python_runtime_match": Path(sys.executable).resolve()
        == Path("/Volumes/Elements/cbti-doctor-main/.venv/bin/python").resolve(),
        "r6_freeze_match": r6_match,
        "runner_sha_match": runner_sha_match,
        "agent_match": agent_ok and current_agent == freeze.get("v3_agent_sha256"),
        "frozen_identities_match": bindings.get("all_frozen_hashes_match") is True,
        "lifecycle_contract_match": (
            sha256(lifecycle_path) == freeze.get("authorization_lifecycle_contract_sha256")
            and lifecycle.get("status") == "FROZEN_CONTRACT_R6"
        ),
        "authorization_id_match": auth.get("authorization_id") == EXPECTED_AUTHORIZATION_ID,
        "authorization_status_issued_unconsumed": (
            auth.get("authorization_status") == "ISSUED_NOT_CONSUMED"
            and auth.get("status") == "ISSUED_NOT_EXECUTED"
            and auth.get("consumed") is False
        ),
        "authorization_consumption_count": auth.get("authorization_consumption_count"),
        "authorization_consumption_count_zero": auth.get("authorization_consumption_count") == 0,
        "active_authorization_count": len(active),
        "exactly_one_active_authorization": len(active) == 1,
        "active_authorization_is_bound_id": active == [EXPECTED_AUTHORIZATION_ID],
        "old_authorization_retired": bool(
            old_retirement and old_retirement.get("final_status") == "RETIRED_UNCONSUMED_NON_REUSABLE"
        ),
        "old_authorization_non_executable": old_rejected,
        "attempt_id_match": auth.get("attempt_id") == EXPECTED_ATTEMPT_ID,
        "attempt_absent": not any(
            EXPECTED_ATTEMPT_ID in path.read_text(encoding="utf-8")
            for path in (ROOT / "evaluation/v4_runs").rglob("attempts.jsonl")
        ),
        "namespace_id_match": auth.get("execution_namespace", {}).get("namespace_id") == namespace_id
        == EXPECTED_NAMESPACE_ID,
        "namespace_absent": not namespace_root.exists() and not namespace_root.is_symlink(),
        "case_count": len(cases),
        "case_set_match": auth.get("case_set_fingerprint_sha256")
        == freeze["frozen_evaluation_identity"]["case_order_fingerprint_sha256"],
        "case_order_match": verify_case_order(
            case_ids, 40, freeze["frozen_evaluation_identity"]["case_order_fingerprint_sha256"]
        ),
        "task_distribution": distribution,
        "task_distribution_match": distribution == EXPECTED_DISTRIBUTION,
        "historical_integrity_match": len(historical) == 55 and history_unchanged,
        "historical_pin_count": len(historical),
        "historical_authorization_hashes_unchanged": historical_auth_before == historical_auth_after,
        "historical_pins_before_sha256": hashlib.sha256(
            json.dumps(historical, sort_keys=True).encode()
        ).hexdigest(),
        "historical_pins_after_sha256": hashlib.sha256(
            json.dumps(historical_after, sort_keys=True).encode()
        ).hexdigest(),
        "step9_58_provenance_gap": read_json(
            ROOT / "evaluation/v1_2_3/step9_62_v3_historical_integrity_audit.json"
        ).get("step9_58_provenance_gap"),
        "provenance_gap_preserved": read_json(
            ROOT / "evaluation/v1_2_3/step9_62_v3_historical_integrity_audit.json"
        ).get("step9_58_provenance_gap") == HISTORICAL_GAP,
        "fresh_connectivity_pass": False,
        "connectivity_probe_performed": False,
        "adapter_pre_attempt_validator_pass": adapter_result.get("all_frozen_hashes_match") is True,
        "parent_validator_pass": True,
        "atomic_commit_protocol_match": isinstance(contract_commit, dict)
        and contract_commit.get("atomic_commit_boundary") is True,
        "crash_reconciliation_protocol_match": isinstance(contract_commit, dict)
        and contract_commit.get("partial_commit_reconciliation") == "FROZEN_FAIL_CLOSED",
        "authorization_consumed": auth.get("consumed"),
        "formal_attempt_created": not not any(
            EXPECTED_ATTEMPT_ID in path.read_text(encoding="utf-8")
            for path in (ROOT / "evaluation/v4_runs").rglob("attempts.jsonl")
        ),
        "formal_v4_case_executed": 0,
    }
    return state


def audit_current_runner_non_consuming() -> dict[str, Any]:
    """Read-only current-runner audit; no V4 case, connectivity, or auth mutation."""
    from scripts import run_step9_53_v3_identity_adapter as adapter

    freeze, freeze_path, identity = resolve_current_freeze(ROOT)
    if (freeze.get("runner_freeze_revision") != identity["runner_freeze_revision"]
            or freeze.get("formal_entry_runner_sha256") != sha256(Path(__file__))):
        raise RuntimeError("current formal entry freeze mismatch")
    result = adapter.preflight()
    return {
        "mode": "AUDIT_ONLY_NON_CONSUMING",
        "runner_freeze_revision": identity["runner_freeze_revision"],
        "runner_freeze_sha256": sha256(freeze_path),
        "runner_identity_match": result["all_frozen_hashes_match"],
        "agent_identity_match": result["treatment_agent_sha256"] == freeze["v3_agent_sha256"],
        "authorization_consumed": "NOT_ASSESSED_BY_RUNNER_IDENTITY_AUDIT",
        "attempt_created": "NOT_ASSESSED_BY_RUNNER_IDENTITY_AUDIT",
        "formal_case_executed": "NOT_ASSESSED_BY_RUNNER_IDENTITY_AUDIT",
        "ready_for_formal_execution": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--audit-only", action="store_true")
    action.add_argument("--reconcile-transaction", action="store_true")
    action.add_argument("--execute-formal-v4", action="store_true")
    parser.add_argument("--evaluation-id")
    parser.add_argument("--authorization-id")
    parser.add_argument("--attempt-id")
    parser.add_argument("--authorization-file", type=Path)
    parser.add_argument("--preflight-file", type=Path)
    parser.add_argument("--preflight-id")
    parser.add_argument("--preflight-sha256")
    for key in ("treatment_agent_sha256", "benchmark_sha256", "harness_sha256",
                "scoring_sha256", "metric_registry_sha256", "one_shot_rules_sha256",
                "matched_protocol_sha256"):
        parser.add_argument("--" + key.replace("_", "-"), dest=key)
    args = parser.parse_args(argv)
    if args.reconcile_transaction:
        if not args.authorization_id:
            parser.error("--reconcile-transaction requires --authorization-id")
        from scripts.v3_execution_transaction import (
            LOCK_PATH, TRANSACTION_ROOT, reconcile_journal,
        )
        print(reconcile_journal(transaction_root=TRANSACTION_ROOT, lock_path=LOCK_PATH,
                                authorization_id=args.authorization_id))
        return 0
    if args.execute_formal_v4:
        execute_formal(args)
        return 0
    try:
        state = audit_current_runner_non_consuming()
        if all(value is not None for value in (args.authorization_file, args.preflight_file,
                                               args.preflight_id, args.preflight_sha256)):
            gates = prepare_formal_gates(args)  # read-only; never reaches the adapter
            precommit = gates["state"]
            failures = gates["precommit_failures"]
        else:
            precommit = None
            failures = ["precommit_not_evaluated:authorization_and_preflight_required"]
    except Exception as error:
        print("STEP9_63_BUILD_STATUS = FAIL_CLOSED_AUDIT_ERROR")
        print(f"FAILURE_TYPE = {type(error).__name__}")
        print("AUTHORIZATION_CONSUMED = NO")
        print("ATTEMPT_CREATED = NO")
        print("FORMAL_NAMESPACE_CREATED = NO")
        print("FORMAL_V4_CASE_EXECUTED = 0")
        return 1
    print(json.dumps({"state": state, "precommit_state": precommit,
                      "precommit_failures": failures,
                      "ready_for_controlled_execution": not failures},
                     sort_keys=True, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
