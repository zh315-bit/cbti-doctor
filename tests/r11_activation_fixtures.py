"""Shared fixtures for the Step 9.63c-r5c10ag activation tests (not a test module).

Everything happens in temporary roots holding byte copies of the real inputs. The
repository itself is only read. Write entries are exercised the way they are meant to
be used: in a real pseudo-terminal, with a person (the test) typing the token.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pty
import select
import shutil
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from scripts import authorization_lifecycle as lifecycle  # noqa: E402
from scripts import build_step9_63c_r11_runner_freeze as builder  # noqa: E402
from scripts import issue_step9_63c_r11_authorization as issuer  # noqa: E402
from scripts import run_step9_63_v3_formal_execution as formal  # noqa: E402
from scripts.preflight_step9_62b_mac_local import SUPPLEMENTAL_HISTORICAL_PINS  # noqa: E402

CREATED_AT = "2026-01-01T00:00:00+00:00"
PRE_RETIREMENT_LEDGER_SIZE = 3856
PRE_RETIREMENT_LEDGER_SHA256 = "aaa2e9898a8869db052a1248a0ca2b0574d9c36093aee608db59457f24c2a60e"
AGENT = "085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607"


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def material_paths() -> list[str]:
    inventory_path = "evaluation/v1_2_3/step9_60a_v3_historical_integrity_audit.json"
    inventory = json.loads((REPO / inventory_path).read_text(encoding="utf-8"))
    paths = set(builder.MEMBER_PATHS) - {builder.IDENTITY_CONFIG_PATH}
    paths |= {builder.PARENT_PATH, builder.R10_AUTHORIZATION_PATH, builder.LEDGER_PATH, inventory_path}
    paths |= {pin["path"] for pin in inventory["historical_pins"].values()} | set(SUPPLEMENTAL_HISTORICAL_PINS)
    paths |= {p.relative_to(REPO).as_posix() for p in (REPO / "evaluation/v1_2_3").glob("step*authorization_manifest.json")
              if not p.name.startswith("._") and "_r11_" not in p.name}  # the issued r11 manifest is an ACTIVATION OUTPUT
    runs = REPO / "evaluation/v4_runs"
    for pattern in ("attempts.jsonl", ".namespace_allocation.json"):
        paths |= {p.relative_to(REPO).as_posix() for p in runs.rglob(pattern) if not p.name.startswith("._")}
    journals = runs / ".execution_transactions"
    if journals.exists():
        paths |= {p.relative_to(REPO).as_posix() for p in journals.glob("*.jsonl") if not p.name.startswith("._")}
    return sorted(paths)


def build_root(base: Path) -> Path:
    """State S0: all inputs present, nothing of r11 created, r10 authorization not retired."""
    root = Path(base).resolve() / "root"
    for relative in material_paths():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / relative, root / relative)
    # State S0 means the PRE-activation ledger: after the real activation the live ledger has two more events
    # (the r10 retirement and the r11 issuance). Cut it back to the pinned pre-retirement prefix.
    ledger = root / builder.LEDGER_PATH
    raw = ledger.read_bytes()
    if len(raw) > PRE_RETIREMENT_LEDGER_SIZE:
        if hashlib.sha256(raw[:PRE_RETIREMENT_LEDGER_SIZE]).hexdigest() != PRE_RETIREMENT_LEDGER_SHA256:
            raise RuntimeError("the live ledger does not start with the pinned pre-retirement bytes")
        ledger.write_bytes(raw[:PRE_RETIREMENT_LEDGER_SIZE])
    return root


def tree_digest(root: Path) -> dict[str, str]:
    rows = {}
    for path in sorted(Path(root).rglob("*")):
        if path.is_symlink():
            rows[path.relative_to(root).as_posix()] = "link:" + os.readlink(path)
        elif path.is_file():
            rows[path.relative_to(root).as_posix()] = sha256(path)
    return rows


def retire_r10(root: Path) -> dict:
    """AR-14 rehearsal with the FROZEN retirement function, entirely inside the temp root."""
    determination = root / "evaluation/v1_2_3/step9_63c_r11_ar14_determination.json"
    determination.write_text(json.dumps({
        "artifact_type": "V3_SUPERSEDED_AUTHORIZATION_NONREUSE_DETERMINATION",
        "old_authorization_id": builder.R10_AUTHORIZATION_ID,
        "old_authorization_reuse_status": "PROVEN_NON_REUSABLE_BY_FROZEN_CONTRACT",
        "retirement_reason": "SUPERSEDED_BY_APPROVED_R11_ACTIVATION", "current_runner_equality_required": False,
    }, sort_keys=True), encoding="utf-8")
    return lifecycle.retire_unconsumed_authorization(
        authorization_path=root / builder.R10_AUTHORIZATION_PATH, expected_authorization_id=builder.R10_AUTHORIZATION_ID,
        run_root=root / "evaluation/v4_runs", ledger_path=root / builder.LEDGER_PATH,
        lock_path=root / builder.LOCK_RELATIVE,
        contract_path=root / "evaluation/v1_2_3/step9_61a_v3_authorization_lifecycle_contract.json",
        determination_path=determination, determination_sha256=sha256(determination))


def sign_approval(root: Path, *, created_at: str = CREATED_AT, issuance: dict | None = None) -> dict:
    """Build the approval from the CURRENT bytes of the temp root and sign it."""
    approval = builder.build_approval(root, created_at_utc=created_at, issuance=issuance)
    approval.update(status=builder.APPROVAL_SIGNED, approver="test-approver", signed_at_utc="2026-01-01T00:00:01+00:00")
    (root / builder.APPROVAL_PATH).write_text(json.dumps(approval, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return approval


def write_approval(root: Path, approval: dict) -> None:
    (root / builder.APPROVAL_PATH).write_text(json.dumps(approval, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cli_env(extra: dict | None = None) -> dict:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", builder.SYNTHETIC_ROOT_ENV: "1"}
    env.update(extra or {})
    return env


def build_command(module: str, root: Path, args: list[str]) -> list[str]:
    """Child command line. The mutation tools replace this to run a CLI with an in-memory mutant."""
    return [sys.executable, "-m", module, "--root", str(root), *args]


def run_cli(module: str, root: Path, args: list[str], *, mode: str = "pipe", lines: list[str] | None = None,
            env: dict | None = None, timeout: float = 120.0) -> tuple[int, str]:
    """Run a CLI as a child. mode: 'pipe' (no terminal), 'tty' (full pty), 'tty-in-only', 'tty-out-only'."""
    command = build_command(module, root, args)
    env = env if env is not None else cli_env()
    if mode == "pipe":
        done = subprocess.run(command, cwd=REPO, env=env, input="\n".join(lines or []) + "\n", capture_output=True,
                              text=True, timeout=timeout)
        return done.returncode, done.stdout + done.stderr
    master, slave = pty.openpty()
    stdin = slave if mode in ("tty", "tty-in-only") else subprocess.PIPE
    stdout = slave if mode in ("tty", "tty-out-only") else subprocess.PIPE
    process = subprocess.Popen(command, cwd=REPO, env=env, stdin=stdin, stdout=stdout,
                               stderr=slave if stdout == slave else subprocess.PIPE, close_fds=True)
    os.close(slave)
    for line in lines or []:
        os.write(master, (line + "\n").encode())
    output = b""
    deadline = time.time() + timeout
    while time.time() < deadline:
        ready, _, _ = select.select([master], [], [], 0.2)
        if ready:
            try:
                chunk = os.read(master, 65536)
            except OSError:
                chunk = b""
            if not chunk:
                break
            output += chunk
        elif process.poll() is not None:
            break
    try:
        code = process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        raise
    extra = b""
    if process.stdout:
        extra += process.stdout.read() or b""
    os.close(master)
    return code, (output + extra).decode(errors="replace")


POINTER_MODULE = "scripts.build_step9_63c_r11_runner_freeze"
ISSUER_MODULE = "scripts.issue_step9_63c_r11_authorization"


def create_pointer(root: Path) -> tuple[int, str]:
    return run_cli(POINTER_MODULE, root, ["--create-pointer"], mode="tty", lines=[builder.POINTER_TOKEN])


def persist_freeze(root: Path, approval: dict) -> str:
    candidate = builder.assemble_candidate(root, created_at_utc=approval["freeze"]["created_at_utc"])
    return builder.persist_candidate(candidate, root)


def issue(root: Path, token: str | None = None) -> tuple[int, str]:
    if token is None:
        plan = issuer.plan_issuance(root)
        token = plan["confirmation_token"]
    return run_cli(ISSUER_MODULE, root, ["--issue"], mode="tty", lines=[token])


def activated_through_freeze(base: Path) -> tuple[Path, dict]:
    """AR-14 -> signed approval -> pointer -> freeze (state S2), all in the temp root."""
    root = build_root(base)
    retire_r10(root)
    approval = sign_approval(root)
    code, output = create_pointer(root)
    assert code == 0, output
    persist_freeze(root, approval)
    return root, approval


def fully_issued(base: Path) -> tuple[Path, dict]:
    root, approval = activated_through_freeze(base)
    code, output = issue(root)
    assert code == 0, output
    return root, approval


def gate_failures(root: Path, *, preflight_validated: bool = True) -> tuple[list[str], dict]:
    """The consumer's real prepare_formal_gates against a temp root.

    Only the identity adapter (needs a real formal runner) and the separately tested
    preflight-evidence check are stood in for; every precommit check runs for real.
    """
    manifest_path = root / builder.AUTHORIZATION_MANIFEST_PATH
    authorization = json.loads(manifest_path.read_text(encoding="utf-8"))
    freeze, freeze_path, identity = formal.resolve_current_freeze(root)
    preflight_file = root / "preflight.json"
    preflight_file.write_text(json.dumps({
        "authorization_id": authorization["authorization_id"], "attempt_id": authorization["attempt_id"],
        "runner_freeze_sha256": sha256(freeze_path), "status": "PASS_NON_CONSUMING_PREFLIGHT",
        "authorization_consumed": False, "attempt_created": False, "namespace_created": False,
        "dns_ready": True, "tcp_ready": True, "tls_ready": True}), encoding="utf-8")
    from scripts.run_step9_35a_matched_treatment import supplied_hash_keys
    args = argparse.Namespace(
        authorization_id=authorization["authorization_id"], attempt_id=authorization["attempt_id"],
        evaluation_id=authorization["evaluation_id"], authorization_file=manifest_path, preflight_file=preflight_file,
        preflight_id="p", preflight_sha256="0" * 64, **{key: "a" * 64 for key in supplied_hash_keys()})
    adapter = types.SimpleNamespace(
        current_v3_agent_identity=lambda: (freeze["v3_agent_sha256"], True),
        _authoritative_authorization_bindings=lambda: {"all_frozen_hashes_match": True})
    real_collect = formal.collect_r11_precommit_state

    def collect(**kwargs):
        return real_collect(**kwargs, adapter_module=adapter)

    with patch.object(formal, "ROOT", root), \
         patch.object(formal, "validate_preflight_evidence", return_value=None), \
         patch.object(formal, "collect_r11_precommit_state", side_effect=collect), \
         patch.object(formal, "EXPECTED_PROJECT_ROOT", root), \
         patch.object(formal, "EXPECTED_PYTHON", Path(sys.executable)):
        gates = formal.prepare_formal_gates(args)
    return gates["precommit_failures"], gates["state"]


def ledger_lines(root: Path) -> list[str]:
    return (root / builder.LEDGER_PATH).read_text(encoding="utf-8").splitlines(keepends=True)


def write_ledger(root: Path, lines: list[str]) -> None:
    (root / builder.LEDGER_PATH).write_text("".join(lines), encoding="utf-8")


def issued_event_index(root: Path) -> int:
    return next(i for i, line in enumerate(ledger_lines(root)) if json.loads(line).get("event_type") == issuer.ISSUED_EVENT)
