"""Fixtures for the Step 9.63c-r5c10ai tests (not a test module): the FINAL-FORM approval
(content hash, commit pin, accepted exceptions) driven through the gated entries on temporary roots."""
from __future__ import annotations

import json
import shutil
import tempfile
import uuid
from pathlib import Path

import r11_activation_fixtures as fx
import r11_gated_fixtures as g
from scripts import build_step9_63c_r11_runner_freeze as builder

FAKE_COMMIT = "c" * 40
OTHER_COMMIT = "d" * 40


def set_head(root: Path, commit: str | None) -> None:
    git = Path(root) / ".git"
    if commit is None:
        shutil.rmtree(git, ignore_errors=True)
        return
    git.mkdir(exist_ok=True)
    (git / "HEAD").write_text(commit + "\n")


def final_flow_root(base: Path, *, sign: bool = True, commit: str | None = FAKE_COMMIT, head: str | None = FAKE_COMMIT,
                    approval_id: str | None = None, created_at: str = fx.CREATED_AT) -> tuple[Path, dict]:
    root = fx.build_root(Path(base))
    set_head(root, head)
    aid = approval_id or f"approval-step9_63c_r11-{uuid.uuid4().hex}"
    (root / builder.DETERMINATION_PATH).write_bytes(builder.canonical_determination_bytes(aid))
    approval = builder.build_approval(root, created_at_utc=created_at, approval_id=aid, final=True)
    if sign:
        g.signed(approval)
        approval["signed_at_commit"] = commit
    fx.write_approval(root, approval)
    return root, approval


def through_final(base: Path, stage: str) -> tuple[Path, dict]:
    root, approval = final_flow_root(base)
    steps = {"retired": g.do_retire, "pointer": g.do_pointer, "freeze": g.do_freeze, "issued": g.do_issue}
    if stage == "s0":
        return root, approval
    for name in ("retired", "pointer", "freeze", "issued"):
        steps[name](root)
        if name == stage:
            break
    return root, approval


class FinalTemplates(g.Templates):
    def build(self, *stages: str) -> None:
        for stage in stages:
            self.roots[stage], _ = through_final(Path(self.tmp.name) / stage, stage)
