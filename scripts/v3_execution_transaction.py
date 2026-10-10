"""Authoritative V3 execution transaction journal and crash reconciliation."""
from __future__ import annotations

import fcntl
import json
import os
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")
STATES = {"PREPARED", "COMMITTING", "COMMITTED", "ABORTED_UNCONSUMED",
          "RECONCILIATION_REQUIRED"}
TERMINAL = {"COMMITTED", "ABORTED_UNCONSUMED", "RECONCILIATION_REQUIRED"}
ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / "evaluation/v4_runs"
TRANSACTION_ROOT = RUN_ROOT / ".execution_transactions"
LOCK_PATH = RUN_ROOT / ".namespace-allocation.lock"
IDENTITY_FIELDS = ("transaction_id", "authorization_id", "attempt_id", "namespace_id",
                   "runner_sha256", "agent_sha256", "evaluation_identity_sha256",
                   "case_set_sha256")


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def transaction_lock(lock_path: Path):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "r+b") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _journal_path(transaction_root: Path, authorization_id: str) -> Path:
    if not SAFE_ID.fullmatch(authorization_id):
        raise RuntimeError("unsafe authorization identity")
    return transaction_root / f"{authorization_id}.jsonl"


def read_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        if path.is_symlink():
            raise RuntimeError("transaction journal symlink; fail closed")
        return []
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("transaction journal is not a regular file")
    events = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"transaction journal corrupt at line {n}; manual reconciliation required") from exc
        if not isinstance(value, dict):
            raise RuntimeError("transaction journal event is not an object")
        events.append(value)
    _validate_events(events)
    return events


def _validate_events(events: list[dict[str, Any]]) -> None:
    allowed = {
        (): {"PREPARED"},
        ("PREPARED",): {"COMMITTING", "ABORTED_UNCONSUMED", "RECONCILIATION_REQUIRED"},
        ("PREPARED", "COMMITTING"): {"COMMITTED", "RECONCILIATION_REQUIRED"},
    }
    state_history: list[str] = []
    seq = 0
    attempt_claimed = False
    identity = {key: events[0].get(key) for key in IDENTITY_FIELDS} if events else {}
    for event in events:
        if any(event.get(key) != value for key, value in identity.items()):
            raise RuntimeError("transaction journal identity drift")
        event_type = event.get("event_type")
        if event_type in STATES:
            if event_type not in allowed.get(tuple(state_history), set()):
                raise RuntimeError("illegal transaction state transition")
            seq += 1
            if event.get("sequence") != seq:
                raise RuntimeError("transaction journal sequence mismatch")
            if event_type == "COMMITTED" and (event.get("commit_point") is not True
                    or event.get("authorization_irreversibly_burned") is not True):
                raise RuntimeError("committed transaction lacks durable burn marker")
            state_history.append(event_type)
        elif event_type == "CASE_STARTED":
            if not state_history or state_history[-1] != "COMMITTED":
                raise RuntimeError("case start event requires committed transaction")
            if not attempt_claimed:
                raise RuntimeError("case start event requires claimed attempt")
        elif event_type == "ATTEMPT_CLAIMED":
            if not state_history or state_history[-1] != "COMMITTED":
                raise RuntimeError("attempt claim requires committed transaction")
            if attempt_claimed:
                raise RuntimeError("attempt may be claimed only once")
            attempt_claimed = True
        else:
            raise RuntimeError("unknown transaction event")
    if len(state_history) > 3:
        raise RuntimeError("invalid terminal transaction history")


def current_state(events: list[dict[str, Any]]) -> str | None:
    return next((e["event_type"] for e in reversed(events) if e.get("event_type") in STATES), None)


def validate_authorization_state(manifest: dict[str, Any]) -> None:
    """Require exact issued/unconsumed shape; retirement and consumption are terminal."""
    status = manifest.get("authorization_status")
    if (status != "ISSUED_NOT_CONSUMED" or manifest.get("consumed") is not False
            or manifest.get("authorization_consumption_count") != 0):
        raise RuntimeError("authorization is not ISSUED_NOT_CONSUMED")


def _append(path: Path, event: dict[str, Any], *, create: bool = False) -> None:
    flags = os.O_WRONLY | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
    if create:
        flags |= os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    _fsync_dir(path.parent)


def _find_identity(transaction_root: Path, *, authorization_id: str,
                   attempt_id: str, namespace_id: str) -> bool:
    if transaction_root.is_symlink():
        raise RuntimeError("transaction root symlink; fail closed")
    if not transaction_root.exists():
        return False
    if not transaction_root.is_dir():
        raise RuntimeError("transaction root is not a directory")
    found = False
    for path in sorted(transaction_root.iterdir(), key=lambda item: item.name):
        if not path.name.endswith(".jsonl"):
            continue
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("transaction journal candidate is not a regular file")
        if path.name.startswith("._"):
            companion = path.with_name(path.name[2:])
            stem = companion.name[:-len(".jsonl")]
            if (not SAFE_ID.fullmatch(stem) or companion.is_symlink()
                    or not companion.is_file()):
                raise RuntimeError("unrecognized transaction AppleDouble companion")
            with path.open("rb") as stream:
                if stream.read(4) != b"\x00\x05\x16\x07":
                    raise RuntimeError("unrecognized transaction AppleDouble companion")
            continue
        stem = path.name[:-len(".jsonl")]
        if not SAFE_ID.fullmatch(stem):
            raise RuntimeError("invalid transaction journal filename")
        events = read_events(path)
        if not events or events[0].get("authorization_id") != stem:
            raise RuntimeError("transaction journal filename or identity mismatch")
        if any(events[0].get(key) == value for key, value in (
            ("authorization_id", authorization_id), ("attempt_id", attempt_id),
            ("namespace_id", namespace_id),
        )):
            found = True
    return found


def _assert_no_physical_collision(run_root: Path, *, authorization_id: str,
                                  attempt_id: str, namespace_id: str) -> None:
    target = run_root / namespace_id
    if target.exists() or target.is_symlink():
        raise RuntimeError("namespace collision; no reuse")
    if not run_root.exists():
        return
    for marker in run_root.rglob(".namespace_allocation.json"):
        try:
            event = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("malformed namespace marker; fail closed") from exc
        if event.get("authorization_id") == authorization_id or event.get("attempt_id") == attempt_id:
            raise RuntimeError("authorization/attempt collision in namespace reservations")
    for ledger in run_root.rglob("attempts.jsonl"):
        try:
            lines = ledger.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise RuntimeError("unreadable attempt ledger; fail closed") from exc
        for line in lines:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError("malformed attempt ledger; fail closed") from exc
            if event.get("authorization_id") == authorization_id or event.get("attempt_id") == attempt_id:
                raise RuntimeError("authorization/attempt collision in attempt history")


def begin_and_commit(*, transaction_root: Path, lock_path: Path, run_root: Path,
                     bindings: dict[str, Any], authorization_state: dict[str, Any],
                     revalidate_under_lock: Callable[[], dict[str, Any]] | None = None) -> dict[str, Any]:
    """Create durable PREPARED→COMMITTING→COMMITTED under one process lock.

    COMMITTED line fsync is the irreversible exactly-once point. Any partial
    journal write is corrupt and fails closed; no rollback/deletion is used.
    """
    required = IDENTITY_FIELDS
    if any(not isinstance(bindings.get(k), str) or not SAFE_ID.fullmatch(bindings[k])
           for k in required[:4]):
        raise RuntimeError("transaction identity bindings are incomplete/unsafe")
    validate_authorization_state(authorization_state)
    if authorization_state.get("authorization_id") != bindings["authorization_id"]:
        raise RuntimeError("authorization state does not match transaction identity")
    if authorization_state.get("attempt_id") != bindings["attempt_id"]:
        raise RuntimeError("authorization attempt does not match transaction identity")
    transaction_root.mkdir(parents=True, exist_ok=True)
    _fsync_dir(transaction_root.parent)
    path = _journal_path(transaction_root, bindings["authorization_id"])
    with transaction_lock(lock_path):
        if revalidate_under_lock is not None:
            fresh_authorization = revalidate_under_lock()
            validate_authorization_state(fresh_authorization)
            if fresh_authorization != authorization_state:
                raise RuntimeError("authorization changed before durable transaction")
        _assert_no_physical_collision(run_root, authorization_id=bindings["authorization_id"],
            attempt_id=bindings["attempt_id"], namespace_id=bindings["namespace_id"])
        if _find_identity(transaction_root, authorization_id=bindings["authorization_id"],
                          attempt_id=bindings["attempt_id"], namespace_id=bindings["namespace_id"]):
            raise RuntimeError("authorization/attempt/namespace already bound to a transaction")
        if path.exists() or path.is_symlink():
            raise RuntimeError("transaction journal collision; no reuse")
        identity = {key: bindings[key] for key in required}
        common = {"transaction_id": identity["transaction_id"], **identity,
                  "created_at": _utc(), "durability": "file_and_parent_directory_fsync"}
        _append(path, {**common, "event_type": "PREPARED", "sequence": 1}, create=True)
        _append(path, {**common, "event_type": "COMMITTING", "sequence": 2})
        committed = {**common, "event_type": "COMMITTED", "sequence": 3,
                     "commit_point": True, "authorization_irreversibly_burned": True}
        _append(path, committed)
        return committed


def append_case_started(*, transaction_root: Path, lock_path: Path,
                        authorization_id: str, transaction_id: str,
                        case_id: str, ordinal: int,
                        expected_bindings: dict[str, str] | None = None) -> dict[str, Any]:
    with transaction_lock(lock_path):
        events = read_events(_journal_path(transaction_root, authorization_id))
        if current_state(events) != "COMMITTED" or events[0].get("transaction_id") != transaction_id:
            raise RuntimeError("case execution requires exact COMMITTED transaction")
        if not any(e.get("event_type") == "ATTEMPT_CLAIMED" for e in events):
            raise RuntimeError("case start requires claimed attempt")
        if expected_bindings and any(events[0].get(key) != value for key, value in expected_bindings.items()):
            raise RuntimeError("case start transaction identity mismatch")
        if any(e.get("event_type") == "CASE_STARTED" and e.get("ordinal") == ordinal for e in events):
            raise RuntimeError("case ordinal already started; rerun forbidden")
        if any(e.get("event_type") == "CASE_STARTED" and e.get("case_id") == case_id for e in events):
            raise RuntimeError("case already started; rerun forbidden")
        event = {**events[0], "event_type": "CASE_STARTED", "ordinal": ordinal,
                 "case_id": case_id, "timestamp": _utc()}
        _append(_journal_path(transaction_root, authorization_id), event)
        return event


def claim_attempt(*, transaction_root: Path, lock_path: Path,
                  authorization_id: str, transaction_id: str,
                  expected_bindings: dict[str, str]) -> dict[str, Any]:
    """Durably claim the single physical attempt; any crash burns the claim."""
    with transaction_lock(lock_path):
        events = read_events(_journal_path(transaction_root, authorization_id))
        if current_state(events) != "COMMITTED":
            raise RuntimeError("attempt claim requires committed transaction")
        if events[0].get("transaction_id") != transaction_id or any(
            events[0].get(key) != value for key, value in expected_bindings.items()
        ):
            raise RuntimeError("attempt claim transaction identity mismatch")
        if any(e.get("event_type") == "ATTEMPT_CLAIMED" for e in events):
            raise RuntimeError("attempt already claimed; rerun forbidden")
        event = {**events[0], "event_type": "ATTEMPT_CLAIMED", "timestamp": _utc()}
        _append(_journal_path(transaction_root, authorization_id), event)
        return event


def require_committed(*, transaction_root: Path, authorization_id: str,
                      attempt_id: str, namespace_id: str,
                      expected_bindings: dict[str, str] | None = None) -> dict[str, Any]:
    events = read_events(_journal_path(transaction_root, authorization_id))
    if current_state(events) != "COMMITTED":
        raise RuntimeError("formal execution requires COMMITTED transaction")
    commit = next(e for e in events if e.get("event_type") == "COMMITTED")
    if commit.get("commit_point") is not True or commit.get("authorization_irreversibly_burned") is not True:
        raise RuntimeError("committed transaction lacks durable burn marker")
    if any(commit.get(k) != v for k, v in (("authorization_id", authorization_id),
        ("attempt_id", attempt_id), ("namespace_id", namespace_id))):
        raise RuntimeError("committed transaction binding mismatch")
    if expected_bindings and any(commit.get(key) != value for key, value in expected_bindings.items()):
        raise RuntimeError("committed transaction frozen identity mismatch")
    return commit


def assert_no_transaction(authorization_id: str, *, transaction_root: Path = TRANSACTION_ROOT) -> None:
    """Reject all prior states, including PREPARED, ABORTED, and torn records."""
    path = _journal_path(transaction_root, authorization_id)
    if path.exists() or path.is_symlink():
        read_events(path)
        raise RuntimeError("authorization already bound to an execution transaction")


def reconcile(events: list[dict[str, Any]]) -> str:
    """Deterministic classification only; never resumes cases or rewrites evidence."""
    state = current_state(events)
    if state is None:
        return "SAFE_TO_ABORT_UNCONSUMED"
    if state == "PREPARED":
        return "SAFE_TO_ABORT_UNCONSUMED"
    if state == "COMMITTING":
        return "MUST_COMPLETE_COMMIT"
    if state == "COMMITTED":
        if any(e.get("event_type") == "CASE_STARTED" for e in events):
            return "COMMITTED_EXECUTION_ALREADY_STARTED"
        if any(e.get("event_type") == "ATTEMPT_CLAIMED" for e in events):
            return "COMMITTED_ATTEMPT_CLAIMED_NO_AUTO_RESUME"
        return "COMMITTED_READY_FOR_EXECUTION"
    return "FAIL_CLOSED_MANUAL_RECONCILIATION_REQUIRED"


def reconcile_journal(*, transaction_root: Path, lock_path: Path,
                      authorization_id: str) -> str:
    """Persist deterministic pre-case recovery; never resumes an execution."""
    path = _journal_path(transaction_root, authorization_id)
    with transaction_lock(lock_path):
        events = read_events(path)
        outcome = reconcile(events)
        if outcome == "SAFE_TO_ABORT_UNCONSUMED":
            state = current_state(events)
            if state is None:
                return outcome
            if state != "PREPARED":
                raise RuntimeError("unexpected state for safe abort")
            last = events[-1]
            _append(path, {**last, "event_type": "ABORTED_UNCONSUMED",
                           "sequence": 2, "timestamp": _utc(),
                           "authorization_consumed": False,
                           "authorization_reuse_allowed": False})
        elif outcome == "MUST_COMPLETE_COMMIT":
            last = events[-1]
            _append(path, {**last, "event_type": "COMMITTED", "sequence": 3,
                           "timestamp": _utc(), "commit_point": True,
                           "authorization_irreversibly_burned": True,
                           "recovered_from_committing": True})
        return outcome
