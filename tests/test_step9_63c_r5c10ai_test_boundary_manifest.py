"""Step 9.63c-r5c10ai: the r5c10ai versioned test boundary manifest.

It covers every current ``tests/test_*.py`` module. The r5c10ah manifest stays
byte-identical (pinned by SHA-256); the validator names the r5c10ai manifest by
constant and never selects "the latest". Any new test module needs a new version.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import unittest
from pathlib import Path

from scripts import validate_step9_63c_r5c10ai_test_boundary as boundary
from scripts import validate_step9_63c_test_boundary as previous

ROOT = Path(__file__).resolve().parents[1]
STEP9_51A_PINS = {
    "evaluation/v1_2_3/step9_51a_safe_test_manifest.json":
        "a639ab7e674227f5c676071da6a6186572138fc88d0c899a9cf3fbaa6a59169d",
    "scripts/validate_step9_51a_test_boundary.py":
        "312f3ca29670c7b092851a37f161aa3cb2e0af17d275c38ca924a3987d7fc9fe",
    "tests/test_step9_51a_validation_boundary.py":
        "127751fe917bca0c6992a2c722d6f7a70c32c34603e444292e5a8a097685573e",
}


class Step963cR5c10aiManifestTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(boundary.MANIFEST.read_text(encoding="utf-8"))

    def test_version_is_pinned_by_constants_never_discovered(self):
        self.assertEqual(boundary.MANIFEST_VERSION, "r5c10ai")
        self.assertEqual(boundary.MANIFEST.relative_to(ROOT).as_posix(),
                         "evaluation/v1_2_3/step9_63c_r5c10ai_test_boundary_manifest.json")
        self.assertEqual(self.data["version_id"], "r5c10ai")
        tree = ast.parse(Path(boundary.__file__).read_text(encoding="utf-8"))
        calls = {node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
                 for node in ast.walk(tree) if isinstance(node, ast.Call)}
        self.assertFalse(calls & {"glob", "rglob", "iterdir", "listdir", "scandir", "walk"}, calls)
        # A "newer" manifest next to it must not be picked up: the path is the constant.
        decoy = ROOT / "evaluation/v1_2_3/step9_63c_r5c10zz_test_boundary_manifest.json"
        self.assertFalse(decoy.exists())
        self.assertEqual(boundary.MANIFEST.name, "step9_63c_r5c10ai_test_boundary_manifest.json")

    def test_previous_version_is_preserved_and_referenced(self):
        self.assertEqual(hashlib.sha256(boundary.PREVIOUS_MANIFEST.read_bytes()).hexdigest(),
                         boundary.PREVIOUS_MANIFEST_SHA256)
        self.assertEqual(boundary.PREVIOUS_MANIFEST.name, "step9_63c_r5c10ah_test_boundary_manifest.json")
        self.assertEqual(self.data["previous_version"]["sha256"], boundary.PREVIOUS_MANIFEST_SHA256)

    def test_decisions_carried_over_and_new_modules_are_not_allowlisted(self):
        old = {row["module"]: row for row in json.loads(boundary.PREVIOUS_MANIFEST.read_text(encoding="utf-8"))["modules"]}
        new = {row["module"]: row for row in self.data["modules"]}
        # the only module that left the inventory is the one retired (FULL) under the standing rule in this step
        self.assertEqual(set(old) - set(new), {"test_step9_63c_r5c10ad_v2_archival_replay"})
        old = {name: row for name, row in old.items() if name in new}
        for name, row in old.items():
            for field in boundary.CARRIED_FIELDS:
                self.assertEqual(new[name][field], row[field], f"{name}.{field}")
        added = sorted(set(new) - set(old))
        self.assertEqual(self.data["added_since_previous"], added)
        self.assertGreaterEqual(len(added), 3)
        for name in added:
            self.assertIs(new[name]["allowed"], False)
            self.assertEqual(new[name]["origin"], "STEP9_63C_DERIVED")
        self.assertEqual({n for n, r in new.items() if r["allowed"]}, previous.SAFE_ALLOWLIST & set(new))

    def test_step9_51a_artifacts_remain_byte_identical(self):
        for path, digest in STEP9_51A_PINS.items():
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest)

    def test_missing_or_extra_module_is_rejected(self):
        missing = copy.deepcopy(self.data)
        missing["modules"].pop()
        extra = copy.deepcopy(self.data)
        extra["modules"].append({**extra["modules"][0], "module": "test_not_present", "path": "tests/test_not_present.py"})
        for case in (missing, extra):
            self.assertTrue(any("inventory differs" in e for e in boundary.audit_manifest(case)))

    def test_allowlist_cannot_be_widened(self):
        data = copy.deepcopy(self.data)
        next(r for r in data["modules"] if r["origin"] == "STEP9_63C_DERIVED")["allowed"] = True
        self.assertTrue(any("allowlist" in e or "decision fields" in e for e in boundary.audit_manifest(data)))

    def test_risk_level_and_carried_decision_tampering_is_rejected(self):
        data = copy.deepcopy(self.data)
        next(r for r in data["modules"] if r["risk_level"] == "HIGH")["risk_level"] = "LOW"
        self.assertTrue(any("mechanical derivation" in e for e in boundary.audit_manifest(data)))
        data = copy.deepcopy(self.data)
        row = next(r for r in data["modules"] if r["origin"] == "STEP9_51A_VERBATIM")
        row["may_access_v5"] = not row["may_access_v5"]
        self.assertTrue(any("verbatim" in e for e in boundary.audit_manifest(data)))
        data = copy.deepcopy(self.data)
        data["modules"][0]["reason"] = "changed after the fact"
        self.assertTrue(any("decision fields differ" in e or "verbatim" in e for e in boundary.audit_manifest(data)))

    def test_decision_of_a_row_carried_from_r5c10ah_cannot_change(self):
        # A mechanically derived row: only the carry-over check (not the 9.51a verbatim check)
        # can notice a changed decision.
        old_names = {row["module"] for row in json.loads(boundary.PREVIOUS_MANIFEST.read_text(encoding="utf-8"))["modules"]}
        for field in boundary.CARRIED_FIELDS:
            with self.subTest(field=field):
                data = copy.deepcopy(self.data)
                row = next(r for r in data["modules"] if r["origin"] == "STEP9_63C_DERIVED" and r["module"] in old_names)
                row[field] = (not row[field]) if isinstance(row[field], bool) else row[field] + " (edited)"
                self.assertTrue(any(f"{row['module']}: decision fields differ" in e for e in boundary.audit_manifest(data)))

    def test_the_previous_manifest_byte_pin_is_enforced(self):
        from unittest.mock import patch
        with patch.object(boundary, "PREVIOUS_MANIFEST_SHA256", "0" * 64):
            self.assertTrue(any("bytes changed" in e for e in boundary.audit_manifest(self.data)))

    def test_added_since_previous_must_match_the_inventory_difference(self):
        data = copy.deepcopy(self.data)
        data["added_since_previous"] = data["added_since_previous"][:-1]
        self.assertTrue(any("added_since_previous" in e for e in boundary.audit_manifest(data)))

    def test_wrong_version_or_previous_reference_is_rejected(self):
        wrong_version = {**self.data, "version_id": "r5c10zz"}
        wrong_previous = {**self.data, "previous_version": {**self.data["previous_version"], "sha256": "0" * 64}}
        self.assertTrue(any("version_id" in e for e in boundary.audit_manifest(wrong_version)))
        self.assertTrue(any("pinned previous version" in e for e in boundary.audit_manifest(wrong_previous)))


if __name__ == "__main__":
    unittest.main()
