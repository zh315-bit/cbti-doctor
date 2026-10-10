"""Fail-closed authorization lifecycle events for one-shot V3 execution."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "evaluation/v1_2_3/step9_61a_v3_authorization_lifecycle_contract.json"
EVENT_LEDGER_PATH = ROOT / "evaluation/v1_2_3/authorization_lifecycle_events.jsonl"
RUN_ROOT = ROOT / "evaluation/v4_runs"
LOCK_PATH = RUN_ROOT / ".namespace-allocation.lock"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")
ISSUED = "ISSUED_NOT_CONSUMED"
RETIRED = "RETIRED_UNCONSUMED_NON_REUSABLE"
RETIRE_EVENT = "AUTHORIZATION_RETIRED_UNCONSUMED_NON_REUSABLE"
ISSUED_EXECUTABLE = "ISSUED_EXECUTABLE"
RETIRED_STATE = "RETIRED_UNCONSUMED_NON_REUSABLE"
BURNED_PRE_CASE = "COMMITTED_BURNED_PRE_CASE_NON_REUSABLE"
CONSUMED_STATE = "CONSUMED_NON_REUSABLE"
INCONSISTENT = "INCONSISTENT_FAIL_CLOSED"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


@contextmanager
def lifecycle_lock(lock_path: Path = LOCK_PATH):
    """Serialize retirement with the runner's exclusive namespace reservation."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock_path, flags, 0o600)
    with os.fdopen(fd, "r+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    result = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"malformed authorization lifecycle ledger line {number}") from error
        if not isinstance(event, dict):
            raise RuntimeError(f"invalid authorization lifecycle event at line {number}")
        result.append(event)
    return result


def authorization_retirement_event(
    authorization_id: str, *, ledger_path: Path | None = None,
) -> dict[str, Any] | None:
    if not isinstance(authorization_id, str) or not SAFE_ID.fullmatch(authorization_id):
        raise RuntimeError("invalid authorization identity")
    path = ledger_path or EVENT_LEDGER_PATH
    found = [event for event in _events(path)
             if event.get("authorization_id") == authorization_id
             and event.get("event_type") == RETIRE_EVENT]
    if len(found) > 1:
        raise RuntimeError("duplicate retirement events for authorization; fail closed")
    if found and (found[0].get("final_status") != RETIRED
                  or found[0].get("authorization_consumed") is not False
                  or found[0].get("authorization_consumption_count") != 0):
        raise RuntimeError("retirement event violates frozen terminal-state invariants")
    return found[0] if found else None


def assert_not_retired(
    authorization_id: str, *, ledger_path: Path | None = None,
) -> None:
    if authorization_retirement_event(authorization_id, ledger_path=ledger_path) is not None:
        raise RuntimeError("authorization is retired and permanently non-executable")


def assert_executable_authorization(
    authorization_id: str, *, ledger_path: Path | None = None,
    transaction_root: Path | None = None,
) -> None:
    """Require the reducer's single derived lifecycle state to be executable."""
    result = reduce_authorization_lifecycle(
        authorization_id=authorization_id, ledger_path=ledger_path,
        transaction_root=transaction_root,
    )
    if result["derived_state"] != ISSUED_EXECUTABLE or result["executable"] is not True:
        raise RuntimeError(f"authorization lifecycle is not executable: {result['derived_state']}")


def _matching_attempt_evidence(run_root: Path, authorization_id: str,
                               attempt_id: str) -> tuple[bool, bool]:
    consumed = False
    any_attempt = False
    if not run_root.exists():
        return False, False
    for ledger in run_root.rglob("attempts.jsonl"):
        if ledger.is_symlink() or not ledger.is_file():
            raise RuntimeError("attempt ledger is not a regular file")
        for number, line in enumerate(ledger.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise RuntimeError(f"malformed attempt ledger {ledger}:{number}") from error
            if not isinstance(event, dict):
                raise RuntimeError("attempt ledger event is not an object")
            if (event.get("authorization_id") == authorization_id
                    or event.get("attempt_id") == attempt_id):
                any_attempt = True
                if event.get("authorization_id") != authorization_id or event.get("attempt_id") != attempt_id:
                    raise RuntimeError("attempt evidence identity mismatch")
                if event.get("status") == "AUTHORIZATION_CONSUMED":
                    consumed = True
    return consumed, any_attempt


def _matching_namespace_markers(run_root: Path, authorization_id: str,
                                attempt_id: str) -> list[dict[str, Any]]:
    found = []
    if not run_root.exists():
        return found
    for marker in run_root.rglob(".namespace_allocation.json"):
        if marker.is_symlink() or not marker.is_file():
            raise RuntimeError("namespace marker is not a regular file")
        value = read_json(marker)
        if (value.get("authorization_id") == authorization_id
                or value.get("attempt_id") == attempt_id):
            if (value.get("authorization_id") != authorization_id
                    or value.get("attempt_id") != attempt_id):
                raise RuntimeError("namespace marker identity mismatch")
            found.append(value)
    return found


def reduce_authorization_lifecycle(
    *, authorization_id: str, manifest: dict[str, Any] | None = None,
    manifest_path: Path | None = None, ledger_path: Path | None = None,
    run_root: Path | None = None, transaction_root: Path | None = None,
) -> dict[str, Any]:
    """Reduce immutable issuance plus append-only lifecycle evidence, fail closed.

    This is the only current-state interpretation used by authorization consumers.
    No branch mutates, reconciles, resumes, or appends to lifecycle evidence.
    """
    from scripts import v3_execution_transaction as transaction

    evidence: dict[str, Any] = {"authorization_id": authorization_id}
    try:
        if not SAFE_ID.fullmatch(authorization_id):
            raise RuntimeError("invalid authorization identity")
        if manifest is None:
            if manifest_path is None:
                candidates = []
                for candidate in (ROOT / "evaluation/v1_2_3").glob("step*authorization_manifest.json"):
                    if candidate.is_symlink() or not candidate.is_file():
                        continue
                    try:
                        obj = read_json(candidate)
                    except (OSError, ValueError):
                        continue
                    if obj.get("authorization_id") == authorization_id:
                        candidates.append((candidate, obj))
                if len(candidates) != 1:
                    raise RuntimeError("authorization manifest identity is missing or ambiguous")
                manifest_path, manifest = candidates[0]
            if manifest_path.is_symlink() or not manifest_path.is_file():
                raise RuntimeError("authorization manifest unavailable")
            if manifest is None:
                manifest = read_json(manifest_path)
        if manifest.get("authorization_id") != authorization_id:
            raise RuntimeError("manifest authorization identity mismatch")
        if (manifest.get("authorization_status") != ISSUED
                or manifest.get("consumed") is not False
                or manifest.get("authorization_consumption_count") != 0):
            raise RuntimeError("manifest issuance fields are not the frozen issued shape")
        attempt_id = manifest.get("attempt_id")
        if not isinstance(attempt_id, str) or not SAFE_ID.fullmatch(attempt_id):
            raise RuntimeError("manifest attempt identity invalid")

        retire = authorization_retirement_event(authorization_id, ledger_path=ledger_path)
        tx_root = transaction_root or transaction.TRANSACTION_ROOT
        journal = tx_root / f"{authorization_id}.jsonl"
        events = transaction.read_events(journal)
        state = transaction.current_state(events)
        if events:
            identity = events[0]
            expected = {
                "authorization_id": authorization_id,
                "attempt_id": attempt_id,
                "namespace_id": manifest.get("execution_namespace", {}).get("namespace_id"),
                "runner_sha256": manifest.get("runner_sha256"),
                "agent_sha256": manifest.get("treatment_agent_sha256"),
                "evaluation_identity_sha256": manifest.get("frozen_evaluation_identity_sha256"),
                "case_set_sha256": manifest.get("case_set_fingerprint_sha256"),
            }
            # Older frozen manifests carry equivalent binding names in nested identity.
            for key, value in expected.items():
                if value is not None and identity.get(key) != value:
                    raise RuntimeError(f"transaction {key} differs from issuance identity")
            if identity.get("authorization_id") != authorization_id or identity.get("attempt_id") != attempt_id:
                raise RuntimeError("transaction identity does not match issuance")
        consumed, attempted = _matching_attempt_evidence(
            run_root or transaction.RUN_ROOT, authorization_id, attempt_id)
        markers = _matching_namespace_markers(run_root or transaction.RUN_ROOT,
                                              authorization_id, attempt_id)
        case_started = any(event.get("event_type") == "CASE_STARTED" for event in events)
        burned = bool(events and state == "COMMITTED"
                      and events[-1].get("event_type") == "COMMITTED"
                      and events[-1].get("authorization_irreversibly_burned") is True)

        if retire and (events or attempted or markers):
            raise RuntimeError("retirement conflicts with transaction or attempt evidence")
        if consumed and retire:
            raise RuntimeError("consumption conflicts with retirement")
        if burned:
            if not markers or any(marker.get("transaction_id") != events[0].get("transaction_id")
                                  for marker in markers):
                raise RuntimeError("committed transaction lacks its exact namespace marker")
            if consumed or attempted or case_started:
                if case_started and attempted:
                    return {**evidence, "derived_state": CONSUMED_STATE,
                            "executable": False, "reusable": False,
                            "evidence": {"transaction_state": state, "burned": True,
                                         "case_started": True}}
                raise RuntimeError("committed pre-case evidence conflicts with attempt state")
            return {**evidence, "derived_state": BURNED_PRE_CASE,
                    "executable": False, "reusable": False,
                    "evidence": {"transaction_state": state, "burned": True,
                                 "case_started": False}}
        if events:
            raise RuntimeError("transaction exists without a valid irreversible committed burn")
        if retire:
            return {**evidence, "derived_state": RETIRED_STATE,
                    "executable": False, "reusable": False,
                    "evidence": {"retirement_event_id": retire.get("lifecycle_event_id")}}
        if consumed or attempted:
            if not consumed:
                raise RuntimeError("attempt exists without authoritative consumption event")
            return {**evidence, "derived_state": CONSUMED_STATE,
                    "executable": False, "reusable": False,
                    "evidence": {"attempt_consumption": True}}
        if markers:
            raise RuntimeError("namespace marker exists without a committed transaction")
        return {**evidence, "derived_state": ISSUED_EXECUTABLE,
                "executable": True, "reusable": True,
                "evidence": {"transaction_state": None, "retired": False,
                             "consumed": False, "namespace_markers": 0}}
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        return {**evidence, "derived_state": INCONSISTENT,
                "executable": False, "reusable": False,
                "error": str(error)}


def active_authorizations(root: Path = ROOT) -> list[str]:
    """Return only current-freeze authorizations reduced to executable.

    Superseded runner-bound manifests cannot execute under the current protocol;
    their historical lifecycle remains available through the reducer for audit.
    """
    from scripts.v3_runner_identity import load_identity_config

    current_revision = load_identity_config(root)["runner_freeze_revision"]
    active = []
    paths = sorted((root / "evaluation/v1_2_3").glob("step*authorization_manifest.json"))
    seen: set[str] = set()
    for path in paths:
        if path.is_symlink():
            raise RuntimeError("authorization manifest symlink; active count unknown")
        try:
            manifest = read_json(path)
        except (OSError, ValueError) as error:
            raise RuntimeError("authorization manifest unreadable; active count unknown") from error
        is_v3 = (manifest.get("treatment") == "TREATMENT_V3"
                 or "_v3_authorization_manifest" in path.name
                 or path.name == "step9_63c_r4_r8_authorization_manifest.json")
        if not is_v3:
            continue
        if manifest.get("authorization_status") == "NOT_ISSUED" or manifest.get("status", "").startswith("NOT_ISSUED"):
            continue
        # Old issuance formats and superseded runner bindings are historical evidence,
        # not executable authorizations in the current runner protocol.
        if manifest.get("runner_freeze_revision") != current_revision:
            continue
        aid = manifest.get("authorization_id")
        if not isinstance(aid, str) or aid in seen:
            raise RuntimeError("missing or duplicate V3 authorization identity")
        seen.add(aid)
        result = reduce_authorization_lifecycle(authorization_id=aid, manifest=manifest,
                                                manifest_path=path, run_root=root / "evaluation/v4_runs")
        if result["derived_state"] == INCONSISTENT:
            raise RuntimeError(f"authorization lifecycle is inconsistent: {aid}: {result.get('error')}")
        if result["derived_state"] == ISSUED_EXECUTABLE and result["executable"] is True:
            active.append(aid)
    return active


def _has_matching_attempt_or_reservation(
    run_root: Path, authorization_id: str, attempt_id: str,
) -> tuple[bool, bool]:
    attempt_found = False
    namespace_found = False
    if run_root.exists():
        for ledger in run_root.rglob("attempts.jsonl"):
            try:
                rows = ledger.read_text(encoding="utf-8").splitlines()
            except OSError as error:
                raise RuntimeError("unreadable attempt ledger; retirement fails closed") from error
            for number, line in enumerate(rows, 1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as error:
                    raise RuntimeError(f"malformed attempt ledger {ledger}:{number}") from error
                if (event.get("authorization_id") == authorization_id
                        or event.get("attempt_id") == attempt_id):
                    attempt_found = True
        for marker in run_root.rglob(".namespace_allocation.json"):
            try:
                record = read_json(marker)
            except (OSError, json.JSONDecodeError) as error:
                raise RuntimeError("malformed namespace marker; retirement fails closed") from error
            if (record.get("authorization_id") == authorization_id
                    or record.get("attempt_id") == attempt_id):
                namespace_found = True
        for path in run_root.rglob("*"):
            if path.name != "attempts.jsonl" and attempt_id in path.name:
                attempt_found = True
    return attempt_found, namespace_found


def retire_unconsumed_authorization(
    *, authorization_path: Path,
    expected_authorization_id: str,
    run_root: Path = RUN_ROOT,
    ledger_path: Path = EVENT_LEDGER_PATH,
    lock_path: Path = LOCK_PATH,
    contract_path: Path = CONTRACT_PATH,
    determination_path: Path,
    determination_sha256: str,
) -> dict[str, Any]:
    """Append a terminal non-consuming retirement event iff the frozen predicate holds."""
    from scripts.v3_namespace_allocator import derive_namespace_id

    if not SAFE_ID.fullmatch(expected_authorization_id):
        raise RuntimeError("invalid authorization identity")
    with lifecycle_lock(lock_path):
        contract = read_json(contract_path)
        required_contract = (
                contract.get("artifact_type") == "V3_AUTHORIZATION_LIFECYCLE_CONTRACT"
                and contract.get("contract_version") == "1"
                and contract.get("status") == "FROZEN_CONTRACT_R6"
                and contract.get("retirement_event", {}).get("append_only") is True
            )
        if not required_contract:
            raise RuntimeError("frozen retirement lifecycle contract missing or incompatible")
        if not determination_path.is_file() or sha256_file(determination_path) != determination_sha256:
            raise RuntimeError("pinned non-reuse determination missing or hash mismatch")
        determination = read_json(determination_path)
        if (determination.get("old_authorization_id") != expected_authorization_id
                    or determination.get("old_authorization_reuse_status")
                    != "PROVEN_NON_REUSABLE_BY_FROZEN_CONTRACT"):
            raise RuntimeError("non-reuse determination does not bind this authorization")
        auth = read_json(authorization_path)
        attempt_id = auth.get("attempt_id")
        evaluation_id = auth.get("evaluation_id")
        if not all(isinstance(v, str) and SAFE_ID.fullmatch(v)
                       for v in (attempt_id, evaluation_id)):
            raise RuntimeError("authorization does not bind safe evaluation and attempt identities")
        if (auth.get("authorization_id") != expected_authorization_id
                    or auth.get("status") != "ISSUED_NOT_EXECUTED"
                    or auth.get("authorization_status") != ISSUED
                    or auth.get("consumed") is not False
                    or auth.get("consumed_at_utc") is not None
                    or auth.get("authorization_consumption_count") != 0
                    or auth.get("attempt_id_status") != "PREBOUND_IDENTITY_ONLY_NOT_CREATED"):
            raise RuntimeError("authorization does not satisfy unconsumed retirement predicate")
        historical_freeze_path = auth.get("runner_freeze_path")
        historical_freeze_sha256 = auth.get("runner_freeze_sha256")
        historical_revision = auth.get("runner_freeze_revision")
        if (not isinstance(historical_freeze_path, str)
                or Path(historical_freeze_path).is_absolute()
                or ".." in Path(historical_freeze_path).parts
                or not isinstance(historical_freeze_sha256, str)
                or not re.fullmatch(r"[0-9a-f]{64}", historical_freeze_sha256)
                or not isinstance(historical_revision, str)):
            raise RuntimeError("authorization historical runner binding is incomplete")
        historical_freeze_file = ROOT / historical_freeze_path
        if (not historical_freeze_file.is_file()
                or sha256_file(historical_freeze_file) != historical_freeze_sha256):
            raise RuntimeError("authorization historical runner freeze hash mismatch")
        historical_freeze = read_json(historical_freeze_file)
        if (historical_freeze.get("runner_freeze_revision") != historical_revision
                or historical_freeze.get("status") != "FROZEN_NOT_AUTHORIZED"
                or auth.get("runner_sha256", auth.get("treatment_runner_sha256"))
                != historical_freeze.get("runner_sha256")):
            raise RuntimeError("authorization was not bound to the recorded historical runner freeze")
        if authorization_retirement_event(expected_authorization_id, ledger_path=ledger_path):
            raise RuntimeError("authorization already has a terminal retirement event")
        from scripts.v3_execution_transaction import assert_no_transaction

        assert_no_transaction(expected_authorization_id,
                              transaction_root=run_root / ".execution_transactions")
        attempt_found, namespace_marker_found = _has_matching_attempt_or_reservation(
                run_root, expected_authorization_id, attempt_id)
        namespace_id = derive_namespace_id(evaluation_id, expected_authorization_id, attempt_id)
        namespace_path = run_root / namespace_id
        if (attempt_found or namespace_marker_found or namespace_path.exists()
                    or namespace_path.is_symlink()):
            raise RuntimeError("attempt, namespace, or reservation already exists; retirement forbidden")
        event = {
                "artifact_type": "AUTHORIZATION_LIFECYCLE_EVENT",
                "event_type": RETIRE_EVENT,
                "lifecycle_event_id": f"retire-{uuid.uuid4().hex}",
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "evaluation_id": evaluation_id,
                "authorization_id": expected_authorization_id,
                "attempt_id": attempt_id,
                "original_status": ISSUED,
                "final_status": RETIRED,
                "authorization_consumed": False,
                "authorization_consumption_count": 0,
                "attempt_created": False,
                "namespace_created": False,
                "cases_started": 0,
                "cases_completed": 0,
                "reuse_determination": determination_path.as_posix(),
                "reuse_determination_sha256": determination_sha256,
                "authorization_manifest_sha256": sha256_file(authorization_path),
                "historical_runner_freeze_path": historical_freeze_path,
                "historical_runner_freeze_sha256": historical_freeze_sha256,
                "historical_runner_freeze_revision": historical_revision,
                "lifecycle_contract_path": contract_path.as_posix(),
                "lifecycle_contract_sha256": sha256_file(contract_path),
                "terminal": True,
        }
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(ledger_path, os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        dir_fd = os.open(ledger_path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        return event


def assert_fresh_authorization_identity(
    *, authorization_id: str,
    attempt_id: str,
    evaluation_id: str,
    run_root: Path = RUN_ROOT,
    ledger_path: Path = EVENT_LEDGER_PATH,
    manifest_root: Path = ROOT / "evaluation/v1_2_3",
) -> None:
    """Guard future issuers against reusing retired, attempted, or allocated identities."""
    if not all(isinstance(value, str) and SAFE_ID.fullmatch(value)
               for value in (authorization_id, attempt_id, evaluation_id)):
        raise RuntimeError("invalid fresh authorization identity")
    if authorization_retirement_event(authorization_id, ledger_path=ledger_path):
        raise RuntimeError("retired authorization identity cannot be reissued")
    from scripts.v3_execution_transaction import assert_no_transaction

    assert_no_transaction(authorization_id, transaction_root=run_root / ".execution_transactions")
    retired_attempt_ids = {
        event.get("attempt_id") for event in _events(ledger_path)
        if event.get("event_type") == RETIRE_EVENT
    }
    if attempt_id in retired_attempt_ids:
        raise RuntimeError("retired attempt identity cannot be rebound")
    for manifest_path in manifest_root.glob("step*_v3_authorization_manifest.json"):
        try:
            manifest = read_json(manifest_path)
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError("malformed authorization manifest; uniqueness cannot be proven") from error
        if authorization_id == manifest.get("authorization_id") or attempt_id == manifest.get("attempt_id"):
            raise RuntimeError("fresh authorization and attempt identities must be globally unique")
    attempt_found, namespace_found = _has_matching_attempt_or_reservation(
        run_root, authorization_id, attempt_id)
    if attempt_found or namespace_found:
        raise RuntimeError("fresh authorization identity already exists in execution history")
    from scripts.v3_namespace_allocator import derive_namespace_id
    if (run_root / derive_namespace_id(evaluation_id, authorization_id, attempt_id)).exists():
        raise RuntimeError("fresh authorization namespace collision")
