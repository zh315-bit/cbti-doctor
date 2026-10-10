#!/usr/bin/env python3
"""Step 9.63c-r5c10ai versioned test boundary manifest: builder and fail-closed auditor.

Same pattern as the r5c10ah validator: ONE manifest is named by constant path and constant
version id, never discovered. The previous (r5c10ah) manifest stays byte-identical and is
pinned here by SHA-256. The new r5c10ai test modules (final-form approval and tokens, the V2 archival replay from
commit 201ef5c) make the r5c10ah inventory stale.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from scripts import validate_step9_63c_r5c10ah_test_boundary as previous_validator

base = previous_validator.base
ROOT = base.ROOT
TEST_DIR = base.TEST_DIR
MANIFEST_VERSION = "r5c10ai"
MANIFEST = ROOT / "evaluation/v1_2_3/step9_63c_r5c10ai_test_boundary_manifest.json"
PREVIOUS_MANIFEST = previous_validator.MANIFEST
PREVIOUS_MANIFEST_VERSION = "r5c10ah"
PREVIOUS_MANIFEST_SHA256 = "f3207365eb1393337297471e9d337407f4d911e91539a2d0156986854e75429c"
# Decision fields of a carried-over module that must never change between versions.
CARRIED_FIELDS = previous_validator.CARRIED_FIELDS


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_manifest() -> dict:
    data = base.build_manifest()
    previous = json.loads(PREVIOUS_MANIFEST.read_text(encoding="utf-8"))
    recorded = {row["module"] for row in previous["modules"]}
    data.update({
        "version": 5, "version_id": MANIFEST_VERSION, "step": "9.63c-r5c10ai",
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
        errors.append("previous (r5c10ah) manifest bytes changed")
    previous = (data.get("previous_version") or {})
    if previous.get("sha256") != PREVIOUS_MANIFEST_SHA256 or previous.get("version_id") != PREVIOUS_MANIFEST_VERSION:
        errors.append("manifest does not reference the pinned previous version")
    old_rows = {row["module"]: row for row in json.loads(PREVIOUS_MANIFEST.read_text(encoding="utf-8"))["modules"]}
    new_rows = {row.get("module"): row for row in data.get("modules", []) if isinstance(row, dict)}
    for name, old in old_rows.items():
        if name in new_rows and any(new_rows[name].get(field) != old.get(field) for field in CARRIED_FIELDS):
            errors.append(f"{name}: decision fields differ from the r5c10ah manifest")
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
