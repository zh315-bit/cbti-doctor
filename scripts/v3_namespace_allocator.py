"""Infrastructure-only allocator for fresh V3 treatment output namespaces."""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
from pathlib import Path

SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")
FAILED_EVALUATION_ID = "heldout-v4-step9_53-treatment-v3-20260930-01"
OCCUPIED_EVALUATION_ID = "heldout-v4-step9_55a-treatment-v3-20260930-01"
MARKER = ".namespace_allocation.json"


def derive_namespace_id(evaluation_id: str, authorization_id: str, attempt_id: str) -> str:
    """Stable one-attempt namespace key; no case data participates in derivation."""
    if not all(SAFE_ID.fullmatch(value) for value in (evaluation_id, authorization_id, attempt_id)):
        raise RuntimeError("invalid namespace allocation identity")
    digest = hashlib.sha256(f"{evaluation_id}\0{authorization_id}\0{attempt_id}".encode()).hexdigest()[:20]
    return f"heldout-v4-treatment-v3-run-{digest}"


def validate_namespace_id(namespace_id: str, evaluation_id: str) -> None:
    if (not SAFE_ID.fullmatch(namespace_id) or namespace_id in {evaluation_id, FAILED_EVALUATION_ID,
                                                               OCCUPIED_EVALUATION_ID}
            or namespace_id.startswith(".")):
        raise RuntimeError("reserved or unsafe output namespace cannot be allocated")


def _identity_seen(run_root: Path, authorization_id: str, attempt_id: str) -> bool:
    from scripts import authorization_lifecycle

    authorization_lifecycle.assert_not_retired(
        authorization_id, ledger_path=authorization_lifecycle.EVENT_LEDGER_PATH)
    for marker in run_root.rglob(MARKER):
        try:
            value = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError("malformed namespace allocation marker; fail closed") from error
        if value.get("authorization_id") == authorization_id or value.get("attempt_id") == attempt_id:
            return True
    for ledger in run_root.rglob("attempts.jsonl"):
        try:
            events = ledger.read_text(encoding="utf-8").splitlines()
        except OSError as error:
            raise RuntimeError("unreadable historical attempt ledger; fail closed") from error
        for line in events:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as error:
                raise RuntimeError("malformed historical attempt ledger; fail closed") from error
            if event.get("authorization_id") == authorization_id or event.get("attempt_id") == attempt_id:
                return True
    return False


def reserve_namespace(run_root: Path, evaluation_id: str, authorization_id: str,
                      attempt_id: str, *, transaction_id: str | None = None) -> tuple[str, Path]:
    """Atomically reserve a derived container; interrupted reservations are never reusable."""
    namespace_id = derive_namespace_id(evaluation_id, authorization_id, attempt_id)
    validate_namespace_id(namespace_id, evaluation_id)
    run_root.mkdir(parents=True, exist_ok=True)
    lock_path = run_root / ".namespace-allocation.lock"
    lock_flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    lock_fd = os.open(lock_path, lock_flags, 0o600)
    with os.fdopen(lock_fd, "r+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if run_root.resolve() == (Path(__file__).resolve().parents[1] / "evaluation/v4_runs").resolve():
            from scripts.v3_execution_transaction import TRANSACTION_ROOT, require_committed

            if transaction_id is None:
                raise RuntimeError("production namespace reservation requires committed transaction")
            commit = require_committed(
                transaction_root=TRANSACTION_ROOT, authorization_id=authorization_id,
                attempt_id=attempt_id, namespace_id=namespace_id,
                expected_bindings={"transaction_id": transaction_id},
            )
            if commit.get("commit_point") is not True:
                raise RuntimeError("namespace transaction commit point missing")
        if _identity_seen(run_root, authorization_id, attempt_id):
            raise RuntimeError("authorization or attempt identity already allocated")
        container = run_root / namespace_id
        if container.exists() or container.is_symlink():
            raise RuntimeError("derived output namespace collision; reuse forbidden")
        container.mkdir(mode=0o700, exist_ok=False)
        root_fd = os.open(run_root, os.O_RDONLY)
        try:
            os.fsync(root_fd)
        finally:
            os.close(root_fd)
        marker = container / MARKER
        payload = {
            "artifact_type": "V3_NAMESPACE_ALLOCATION_RESERVATION",
            "evaluation_id": evaluation_id,
            "authorization_id": authorization_id,
            "attempt_id": attempt_id,
            "namespace_id": namespace_id,
            "transaction_id": transaction_id,
            "status": "RESERVED_FAIL_CLOSED_ON_INTERRUPTION",
        }
        fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        dir_fd = os.open(container, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        os.fsync(lock.fileno())
        return namespace_id, container
