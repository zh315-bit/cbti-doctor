"""Fixtures for the Step 9.63c-r5c10ah gated-entry tests (not a test module).

The NEW activation flow, driven only through the gated entries, on temporary roots:
signed approval (before anything) -> --retire-r10 -> --create-pointer -> --create-freeze -> --issue.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import types
import uuid
from pathlib import Path
from unittest.mock import patch

import r11_activation_fixtures as fx
from scripts import build_step9_63c_r11_runner_freeze as builder
from scripts import issue_step9_63c_r11_authorization as issuer
from scripts import run_step9_63_v3_formal_execution as formal

REPO = fx.REPO
CREATED_AT = fx.CREATED_AT
POINTER_MODULE = fx.POINTER_MODULE
ISSUER_MODULE = fx.ISSUER_MODULE


def signed(approval: dict, *, approver: str = "test-approver") -> dict:
    approval.update(status=builder.APPROVAL_SIGNED, approver=approver, signed_at_utc="2026-01-01T00:00:01+00:00")
    return approval


def new_flow_root(base: Path, *, sign: bool = True, approval_id: str | None = None, created_at: str = CREATED_AT) -> tuple[Path, dict]:
    """State S0 with the approval already signed and the determination in place, nothing activated."""
    root = fx.build_root(Path(base))
    aid = approval_id or f"approval-step9_63c_r11-{uuid.uuid4().hex}"
    (root / builder.DETERMINATION_PATH).write_bytes(builder.canonical_determination_bytes(aid))
    approval = builder.build_approval(root, created_at_utc=created_at, approval_id=aid)
    if sign:
        signed(approval)
    fx.write_approval(root, approval)
    return root, approval


def rewrite_approval(root: Path, mutate) -> dict:
    approval = json.loads((root / builder.APPROVAL_PATH).read_text())
    mutate(approval)
    fx.write_approval(root, approval)
    return approval


def cli(root: Path, flag: str, *, token: str | None = None, mode: str = "tty", env: dict | None = None) -> tuple[int, str]:
    lines = [token] if token is not None else []
    return fx.run_cli(POINTER_MODULE, root, [flag], mode=mode, lines=lines, env=env)


def retire_token(root: Path) -> str:
    return builder.plan_retirement(root)["confirmation_token"]


def freeze_token(root: Path) -> str:
    return builder.plan_freeze(root)["confirmation_token"]


def do_retire(root: Path) -> None:
    code, output = cli(root, "--retire-r10", token=retire_token(root))
    assert code == 0, output


def do_pointer(root: Path) -> None:
    code, output = fx.create_pointer(root)
    assert code == 0, output


def do_freeze(root: Path) -> None:
    code, output = cli(root, "--create-freeze", token=freeze_token(root))
    assert code == 0, output


def do_issue(root: Path) -> None:
    code, output = fx.issue(root)
    assert code == 0, output


def through(base: Path, stage: str) -> tuple[Path, dict]:
    """stage in: s0 | retired | pointer | freeze | issued"""
    root, approval = new_flow_root(base)
    order = ["retired", "pointer", "freeze", "issued"]
    steps = {"retired": do_retire, "pointer": do_pointer, "freeze": do_freeze, "issued": do_issue}
    if stage == "s0":
        return root, approval
    for name in order:
        steps[name](root)
        if name == stage:
            break
    return root, approval


def gate_args(root: Path):
    manifest_path = root / builder.AUTHORIZATION_MANIFEST_PATH
    authorization = json.loads(manifest_path.read_text(encoding="utf-8"))
    freeze, freeze_path, identity = formal.resolve_current_freeze(root)
    preflight_file = root / "preflight.json"
    preflight_file.write_text(json.dumps({
        "authorization_id": authorization["authorization_id"], "attempt_id": authorization["attempt_id"],
        "runner_freeze_sha256": fx.sha256(freeze_path), "status": "PASS_NON_CONSUMING_PREFLIGHT",
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
    return args, adapter


def with_gate(root: Path, function):
    """Run `function(args)` with the consumer's REAL precommit checks rooted in a temporary root.
    Only the identity adapter and the separately tested preflight-evidence check are stood in."""
    args, adapter = gate_args(root)
    real_collect = formal.collect_r11_precommit_state

    def collect(**kwargs):
        return real_collect(**kwargs, adapter_module=adapter)

    with patch.object(formal, "ROOT", root), \
         patch.object(formal, "validate_preflight_evidence", return_value=None), \
         patch.object(formal, "collect_r11_precommit_state", side_effect=collect), \
         patch.object(formal, "EXPECTED_PROJECT_ROOT", root), \
         patch.object(formal, "EXPECTED_PYTHON", Path(sys.executable)):
        return function(args)


class Templates:
    """Per-module cache of the new-flow stages; `clone` gives every test its own copy."""

    def __init__(self, prefix: str):
        self.tmp = tempfile.TemporaryDirectory(prefix=prefix)
        self.roots: dict[str, Path] = {}

    def build(self, *stages: str) -> None:
        for stage in stages:
            self.roots[stage], _ = through(Path(self.tmp.name) / stage, stage)

    def clone(self, stage: str) -> Path:
        target = Path(tempfile.mkdtemp(dir=self.tmp.name)) / "root"
        shutil.copytree(self.roots[stage], target)
        return target

    def close(self) -> None:
        self.tmp.cleanup()
