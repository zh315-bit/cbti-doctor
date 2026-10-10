"""Step 9.63c-r5c10ad AR-7: versioned test boundary manifest covering every test module.

Replaces, for the current inventory, the property historically asserted by
``test_step9_51a_validation_boundary.test_current_manifest_passes_pinned_allowlist``.
The Step 9.51a manifest, validator and test are pinned by the frozen development
freeze and are asserted here to remain byte-identical.
"""
from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path

from scripts import validate_step9_63c_test_boundary as boundary

ROOT = Path(__file__).resolve().parents[1]
# Pins recorded in evaluation/v1_2_3/step9_51_v3_development_freeze_r1.json (r10/r11 member).
STEP9_51A_PINS = {
    "evaluation/v1_2_3/step9_51a_safe_test_manifest.json":
        "a639ab7e674227f5c676071da6a6186572138fc88d0c899a9cf3fbaa6a59169d",
    "scripts/validate_step9_51a_test_boundary.py":
        "312f3ca29670c7b092851a37f161aa3cb2e0af17d275c38ca924a3987d7fc9fe",
    "tests/test_step9_51a_validation_boundary.py":
        "127751fe917bca0c6992a2c722d6f7a70c32c34603e444292e5a8a097685573e",
}


class Step963cTestBoundaryManifestTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(boundary.MANIFEST.read_text(encoding="utf-8"))

    def test_current_manifest_covers_inventory_and_passes_audit(self):
        self.assertEqual(boundary.audit_manifest(self.data), [])
        names = {row["module"] for row in self.data["modules"]}
        self.assertEqual(names, {p.stem for p in (ROOT / "tests").glob("test_*.py")})
        self.assertTrue(all(row["risk_level"] in boundary.RISK_LEVELS for row in self.data["modules"]))

    def test_step9_51a_artifacts_remain_byte_identical(self):
        for path, digest in STEP9_51A_PINS.items():
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), digest)
        freeze = json.loads((ROOT / "evaluation/v1_2_3/step9_51_v3_development_freeze_r1.json")
                            .read_text(encoding="utf-8"))["validation_boundary"]
        self.assertEqual(freeze["guard_sha256"], STEP9_51A_PINS["scripts/validate_step9_51a_test_boundary.py"])
        self.assertEqual(freeze["guard_test_sha256"], STEP9_51A_PINS["tests/test_step9_51a_validation_boundary.py"])

    def test_manifest_is_reproducible_from_sources(self):
        self.assertEqual(boundary.build_manifest(), self.data)

    def test_missing_or_extra_module_is_rejected(self):
        missing = copy.deepcopy(self.data); missing["modules"].pop()
        extra = copy.deepcopy(self.data)
        extra["modules"].append({**extra["modules"][0], "module": "test_not_present",
                                 "path": "tests/test_not_present.py"})
        for case in (missing, extra):
            self.assertTrue(any("inventory differs" in e for e in boundary.audit_manifest(case)))

    def test_allowlist_cannot_be_widened(self):
        data = copy.deepcopy(self.data)
        row = next(r for r in data["modules"] if r["origin"] == "STEP9_63C_DERIVED")
        row["allowed"] = True
        self.assertTrue(any("allowlist" in e for e in boundary.audit_manifest(data)))

    def test_risk_level_tampering_is_rejected(self):
        data = copy.deepcopy(self.data)
        row = next(r for r in data["modules"] if r["risk_level"] == "HIGH")
        row["risk_level"] = "LOW"
        self.assertTrue(any("mechanical derivation" in e for e in boundary.audit_manifest(data)))

    def test_step9_51a_decisions_cannot_be_rewritten(self):
        data = copy.deepcopy(self.data)
        row = next(r for r in data["modules"] if r["origin"] == "STEP9_51A_VERBATIM")
        row["may_access_v5"] = not row["may_access_v5"]
        self.assertTrue(any("verbatim" in e for e in boundary.audit_manifest(data)))


if __name__ == "__main__":
    unittest.main()
