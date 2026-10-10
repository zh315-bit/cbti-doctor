"""Step 9.63c-r5c10ad AR-4: r11-contract rewrites of retired r9 bootstrap resolver tests.

The historical ``test_09``/``test_10``/``test_18`` in
``tests/test_step9_63c_r5c4_bootstrap_repair.py`` asserted the r9 resolver contract
(r9 pointer, one-member freeze, live pointer equal to r9). The resolver is now
deliberately r11-only, so those assertions can never hold again. The same properties
are re-expressed here against the r11 contract using a temporary-root synthetic r11
identity; the repository pointer is never created, read as authority, or faked.
Originals are archived in ``tests/retired/test_step9_63c_r5c4_bootstrap_repair.py.retired``.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts import v3_runner_identity as identity

HISTORICAL_R8_FREEZE = "evaluation/v1_2_3/step9_63c_r3_runner_freeze.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class R11ResolverContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pointer = self.root / identity.IDENTITY_CONFIG_PATH
        self.freeze_path = self.root / identity.EXPECTED_FREEZE_PATH
        self.pointer.parent.mkdir(parents=True)
        self.write_pointer(identity.EXPECTED_REVISION, identity.EXPECTED_FREEZE_PATH)
        self.write_freeze()

    def write_pointer(self, revision: str, freeze_path: str) -> None:
        self.pointer.write_text(json.dumps({
            "artifact_type": "V3_CURRENT_RUNNER_IDENTITY_POINTER",
            "status": "FROZEN_IDENTITY_POINTER_NOT_AUTHORIZATION",
            "runner_freeze_revision": revision, "runner_freeze_path": freeze_path}), encoding="utf-8")

    def write_freeze(self, **overrides) -> None:
        members = []
        for index in range(20):
            member = self.root / "members" / f"member_{index:02d}.txt"
            member.parent.mkdir(exist_ok=True)
            member.write_text(f"synthetic member {index}\n", encoding="utf-8")
            members.append({"path": member.relative_to(self.root).as_posix(), "sha256": sha256(member)})
        rows = "".join(sorted(f"{m['path']}\t{m['sha256']}\n" for m in members))
        freeze = {"runner_freeze_revision": identity.EXPECTED_REVISION, "status": "FROZEN_NOT_AUTHORIZED",
                  "identity_config_path": identity.IDENTITY_CONFIG_PATH,
                  "identity_config_sha256": sha256(self.pointer), "members": members,
                  "member_count": 20, "member_aggregate_sha256": hashlib.sha256(rows.encode()).hexdigest()}
        freeze.update(overrides)
        self.freeze_path.write_text(json.dumps(freeze), encoding="utf-8")

    def test_09_pointer_resolves_only_exact_freeze(self):
        freeze, freeze_file, resolved = identity.resolve_current_freeze(self.root)
        self.assertEqual(freeze["runner_freeze_revision"], "r11")
        self.assertEqual(freeze_file, self.freeze_path)
        self.assertEqual(resolved["identity_config_sha256"], sha256(self.pointer))
        # "Only exact": a pointer naming any other freeze path or revision is rejected.
        for revision, path in (("r11", "evaluation/v1_2_3/other_freeze.json"),
                               ("r10", identity.EXPECTED_FREEZE_PATH)):
            with self.subTest(revision=revision, path=path):
                self.write_pointer(revision, path)
                with self.assertRaisesRegex(RuntimeError, "identity pointer is invalid"):
                    identity.resolve_current_freeze(self.root)

    def test_10_pointer_freeze_hash_mismatch_fails(self):
        self.write_freeze(identity_config_sha256="0" * 64)
        with self.assertRaisesRegex(RuntimeError, "does not match the identity pointer"):
            identity.resolve_current_freeze(self.root)
        # Editing the pointer after freezing breaks the same binding.
        self.write_freeze()
        self.pointer.write_text(self.pointer.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "does not match the identity pointer"):
            identity.resolve_current_freeze(self.root)

    def test_18_old_r8_freeze_is_not_a_current_freeze_binding(self):
        self.assertEqual(identity.EXPECTED_REVISION, "r11")
        self.assertNotEqual(identity.EXPECTED_FREEZE_PATH, HISTORICAL_R8_FREEZE)
        for revision in ("r8", "r11"):
            with self.subTest(revision=revision):
                self.write_pointer(revision, HISTORICAL_R8_FREEZE)
                with self.assertRaisesRegex(RuntimeError, "identity pointer is invalid"):
                    identity.load_identity_config(self.root)


if __name__ == "__main__":
    unittest.main()
