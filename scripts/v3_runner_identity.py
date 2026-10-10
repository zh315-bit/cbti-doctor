"""Resolve the single current V3 runner identity without creating state."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
IDENTITY_CONFIG_PATH = "evaluation/v1_2_3/step9_63c_r11_current_runner_identity.json"
EXPECTED_FREEZE_PATH = "evaluation/v1_2_3/step9_63c_r11_runner_freeze.json"
EXPECTED_REVISION = "r11"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("runner identity artifact must be a JSON object")
    return value


def load_identity_config(root: Path = ROOT) -> dict[str, str]:
    path = root / IDENTITY_CONFIG_PATH
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("current runner identity pointer is missing or unsafe")
    config = read_json(path)
    revision = config.get("runner_freeze_revision")
    freeze_path = config.get("runner_freeze_path")
    if (config.get("artifact_type") != "V3_CURRENT_RUNNER_IDENTITY_POINTER"
            or config.get("status") != "FROZEN_IDENTITY_POINTER_NOT_AUTHORIZATION"
            or revision != EXPECTED_REVISION
            or freeze_path != EXPECTED_FREEZE_PATH):
        raise RuntimeError("current runner identity pointer is invalid")
    return {"runner_freeze_revision": revision, "runner_freeze_path": freeze_path,
            "identity_config_sha256": sha256_file(path)}


def resolve_current_freeze(root: Path = ROOT, *, verify_members: bool = True
                           ) -> tuple[dict[str, Any], Path, dict[str, str]]:
    identity = load_identity_config(root)
    freeze_path = root / identity["runner_freeze_path"]
    if freeze_path.is_symlink() or not freeze_path.is_file():
        raise RuntimeError("current runner freeze is missing or unsafe")
    freeze = read_json(freeze_path)
    if (freeze.get("runner_freeze_revision") != identity["runner_freeze_revision"]
            or freeze.get("status") != "FROZEN_NOT_AUTHORIZED"
            or freeze.get("identity_config_path") != IDENTITY_CONFIG_PATH
            or freeze.get("identity_config_sha256") != identity["identity_config_sha256"]):
        raise RuntimeError("current runner freeze does not match the identity pointer")
    members = freeze.get("members")
    if not isinstance(members, list) or len(members) != 20:
        raise RuntimeError("current runner freeze has no member inventory")
    seen: set[str] = set()
    rows: list[str] = []
    for member in members:
        relpath, digest = member.get("path"), member.get("sha256")
        if (not isinstance(relpath, str) or Path(relpath).is_absolute()
                or ".." in Path(relpath).parts or not isinstance(digest, str)
                or not re.fullmatch(r"[0-9a-f]{64}", digest) or relpath in seen):
            raise RuntimeError("current runner freeze member inventory is invalid")
        seen.add(relpath)
        rows.append(f"{relpath}\t{digest}\n")
        if verify_members:
            target = root / relpath
            if target.is_symlink() or not target.is_file() or sha256_file(target) != digest:
                raise RuntimeError(f"current runner freeze member mismatch: {relpath}")
    aggregate = hashlib.sha256("".join(sorted(rows)).encode("utf-8")).hexdigest()
    if (freeze.get("member_count") != len(members)
            or freeze.get("member_aggregate_sha256") != aggregate):
        raise RuntimeError("current runner freeze member aggregate mismatch")
    return freeze, freeze_path, identity
