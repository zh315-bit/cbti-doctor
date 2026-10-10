"""Unit tests for the fail-closed Step 9.51a test selector."""
import unittest
import hashlib
import json
from pathlib import Path

from scripts.validate_step9_51a_test_boundary import audit_manifest


class ValidationBoundaryTests(unittest.TestCase):
    def test_current_manifest_passes_pinned_allowlist(self):
        import json
        from scripts.validate_step9_51a_test_boundary import MANIFEST
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        selected, errors = audit_manifest(data)
        self.assertFalse(errors)
        self.assertIn("test_step9_50_bounded_answer_contract", {item["module"] for item in selected})

    def test_risky_metadata_is_fail_closed(self):
        import json
        from scripts.validate_step9_51a_test_boundary import MANIFEST
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        item = next(row for row in data["modules"] if row["module"] == "test_step9_50_bounded_answer_contract")
        item["may_access_v5"] = True
        _, errors = audit_manifest(data)
        self.assertTrue(any("pinned Step 9.51a allowlist" in error for error in errors)
                        or any("disallowed risk metadata" in error for error in errors))

    def test_frozen_v2_inventory_is_self_consistent_without_live_tree_equality(self):
        root = Path(__file__).resolve().parents[1]
        freeze_path = root / "evaluation/v1_2_3/step9_42_treatment_v2_freeze.json"
        freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
        rows = sorted(freeze["agent_behavior_files"])
        recorded = hashlib.sha256("".join(f"{path}\t{digest}\n" for path, digest in rows).encode()).hexdigest()
        self.assertEqual(len(rows), 26)
        self.assertEqual(recorded, freeze["treatment_v2_agent_sha256"])
        for later_freeze in ("step9_49_v2_postmortem_freeze.json", "step9_50_v3_design_freeze.json"):
            audit_freeze = json.loads((root / "evaluation/v1_2_3" / later_freeze).read_text(encoding="utf-8"))
            pinned = audit_freeze["input_hashes"]["evaluation/v1_2_3/step9_42_treatment_v2_freeze.json"]
            actual = hashlib.sha256(freeze_path.read_bytes()).hexdigest()
            self.assertEqual(actual, pinned)

    def test_v3_development_inventory_matches_current_candidate_identity(self):
        root = Path(__file__).resolve().parents[1]
        freeze = json.loads((root / "evaluation/v1_2_3/step9_42_treatment_v2_freeze.json").read_text(encoding="utf-8"))
        current = []
        for relative_path, frozen_digest in freeze["agent_behavior_files"]:
            if relative_path == "runtime:deepseek_nonsecret_configuration":
                digest = frozen_digest
            elif relative_path == "rag_lib/pdfs/":
                entries = []
                for path in sorted((root / "rag_lib/pdfs").glob("*")):
                    if path.is_file() and not path.name.startswith("._"):
                        file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
                        entries.append(f"{file_hash}  {path.relative_to(root)}\n")
                digest = hashlib.sha256("".join(entries).encode()).hexdigest()
            else:
                digest = hashlib.sha256((root / relative_path).read_bytes()).hexdigest()
            current.append((relative_path, digest))
        aggregate = hashlib.sha256("".join(
            f"{path}\t{digest}\n" for path, digest in sorted(current)
        ).encode()).hexdigest()
        self.assertEqual(aggregate, "085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607")


if __name__ == "__main__":
    unittest.main()
