#!/usr/bin/env python3
"""Step 9.63c-r5c10ae versioned test boundary manifest: builder and fail-closed auditor.

Version pinning (Step 9.63c-r5c10af decision): this module names ONE manifest by
constant path and constant version id. It never searches for, sorts or selects
"the latest" manifest. A new test module therefore requires a new version of this
file and of its manifest; the previous manifest stays byte-identical and is pinned
here by SHA-256.

The classification rules are those of ``validate_step9_63c_test_boundary`` (r5c10ad):
the Step 9.51a decisions are carried verbatim, the pinned allowlist is never widened,
and every other module is classified mechanically from its source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts import validate_step9_63c_test_boundary as base

ROOT = base.ROOT
TEST_DIR = base.TEST_DIR
MANIFEST_VERSION = "r5c10ae"
MANIFEST = ROOT / "evaluation/v1_2_3/step9_63c_r5c10ae_test_boundary_manifest.json"
PREVIOUS_MANIFEST = base.MANIFEST
PREVIOUS_MANIFEST_VERSION = "r5c10ad"
PREVIOUS_MANIFEST_SHA256 = "acf0b42973083f51c19273c5b9504e5b78491431a6f230df6fd4f8d37728f200"
# Decision fields of a carried-over module that must never change between versions.
CARRIED_FIELDS = ("allowed", "reason", "identity_scope", "origin", "purpose")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest() -> dict:
    data = base.build_manifest()
    previous = json.loads(PREVIOUS_MANIFEST.read_text(encoding="utf-8"))
    recorded = {row["module"] for row in previous["modules"]}
    data.update({
        "version": 2, "version_id": MANIFEST_VERSION, "step": "9.63c-r5c10ae",
        "previous_version": {"version_id": PREVIOUS_MANIFEST_VERSION,
                             "path": str(PREVIOUS_MANIFEST.relative_to(ROOT)),
                             "sha256": PREVIOUS_MANIFEST_SHA256, "preserved_unchanged": True},
        "added_since_previous": sorted(row["module"] for row in data["modules"] if row["module"] not in recorded),
        "selection_rule": "constant path and version id; no discovery of other manifests",
    })
    return data


def audit_manifest(data: dict) -> list[str]:
    errors = list(base.audit_manifest(data))
    if data.get("version_id") != MANIFEST_VERSION:
        errors.append(f"manifest version_id is {data.get('version_id')!r}, expected {MANIFEST_VERSION!r}")
    if sha256_file(PREVIOUS_MANIFEST) != PREVIOUS_MANIFEST_SHA256:
        errors.append("previous (r5c10ad) manifest bytes changed")
    previous = (data.get("previous_version") or {})
    if previous.get("sha256") != PREVIOUS_MANIFEST_SHA256 or previous.get("version_id") != PREVIOUS_MANIFEST_VERSION:
        errors.append("manifest does not reference the pinned previous version")
    old_rows = {row["module"]: row for row in json.loads(PREVIOUS_MANIFEST.read_text(encoding="utf-8"))["modules"]}
    new_rows = {row.get("module"): row for row in data.get("modules", []) if isinstance(row, dict)}
    for name, old in old_rows.items():
        if name in new_rows and any(new_rows[name].get(field) != old.get(field) for field in CARRIED_FIELDS):
            errors.append(f"{name}: decision fields differ from the r5c10ad manifest")
    added = sorted(set(new_rows) - set(old_rows))
    if data.get("added_since_previous") != added:
        errors.append("added_since_previous does not match the inventory difference")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create", action="store_true", help="write the manifest if it does not exist")
    args = parser.parse_args(argv)
    if args.create:
        if MANIFEST.exists():
            raise SystemExit(f"refusing to overwrite existing manifest: {MANIFEST}")
        MANIFEST.write_text(json.dumps(build_manifest(), indent=1) + "\n", encoding="utf-8")
    errors = audit_manifest(json.loads(MANIFEST.read_text(encoding="utf-8")))
    print(json.dumps({"manifest": str(MANIFEST.relative_to(ROOT)), "errors": errors}, indent=1))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
