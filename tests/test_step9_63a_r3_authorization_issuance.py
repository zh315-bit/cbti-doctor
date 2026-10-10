"""Synthetic, non-consuming checks for fresh-r7 authorization issuance."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts import issue_step9_63a_r3_authorization as issuer


class FreshR7IssuanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.runs = self.root / "runs"
        self.runs.mkdir()
        self.manifest_root = self.root / "manifests"
        self.manifest_root.mkdir()
        self.path = self.manifest_root / "step_synthetic_v3_authorization_manifest.json"
        self.ledger = self.root / "lifecycle.jsonl"
        self.lock = self.runs / ".namespace-allocation.lock"
        self.freeze = issuer.read_json(issuer.FREEZE_PATH)
        self.old = issuer.read_json(issuer.OLD_AUTH_PATH)
        self.auth_id = "auth-synthetic-r7-unique"
        self.attempt_id = "attempt-synthetic-r7-unique"
        self.namespace_id = issuer.derive_namespace_id(
            self.old["evaluation_id"], self.auth_id, self.attempt_id)
        self.manifest = issuer.build_manifest(
            self.freeze, self.old, self.auth_id, self.attempt_id, self.namespace_id)

    def tearDown(self):
        self.tmp.cleanup()

    def issue(self, *, manifest=None, path=None, active_ids=None):
        return issuer.issue_exactly_once(
            manifest=manifest or self.manifest, path=path or self.path,
            run_root=self.runs, ledger_path=self.ledger,
            manifest_root=self.manifest_root, lock_path=self.lock,
            active_ids=active_ids or (lambda: [self.auth_id] if self.path.exists() else []),
            revalidate=lambda: None,
        )

    def test_manifest_binds_exact_r7_and_frozen_evaluation(self):
        issuer.validate_manifest_bindings(self.manifest, self.freeze)
        self.assertEqual(self.manifest["runner_freeze_revision"], "r7")
        self.assertEqual(self.manifest["treatment_agent_sha256"], self.freeze["v3_agent_sha256"])
        self.assertEqual(self.manifest["frozen_evaluation_identity_sha256"],
                         self.freeze["bound_identities_sha256"])

    def test_manifest_is_issued_unconsumed_without_attempt(self):
        self.assertEqual(self.manifest["authorization_status"], "ISSUED_NOT_CONSUMED")
        self.assertFalse(self.manifest["consumed"])
        self.assertEqual(self.manifest["authorization_consumption_count"], 0)
        self.assertEqual(self.manifest["attempt_id_status"], "PREBOUND_IDENTITY_ONLY_NOT_CREATED")

    def test_synthetic_issue_creates_only_manifest(self):
        digest = self.issue()
        self.assertEqual(digest, issuer.sha256(self.path))
        self.assertFalse((self.runs / self.namespace_id).exists())
        self.assertEqual(list(self.runs.rglob("attempts.jsonl")), [])
        self.assertEqual(list(self.runs.rglob(".namespace_allocation.json")), [])

    def test_duplicate_issue_rejected_without_second_authorization(self):
        self.issue()
        before = self.path.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "active authorization"):
            self.issue()
        self.assertEqual(self.path.read_bytes(), before)

    def test_other_target_rejected_when_active_exists(self):
        self.issue()
        other = copy.deepcopy(self.manifest)
        other["authorization_id"] = "auth-synthetic-r7-second"
        other["attempt_id"] = "attempt-synthetic-r7-second"
        other["execution_namespace"]["namespace_id"] = issuer.derive_namespace_id(
            other["evaluation_id"], other["authorization_id"], other["attempt_id"])
        with self.assertRaisesRegex(RuntimeError, "active authorization"):
            self.issue(manifest=other, path=self.manifest_root / "step_second_v3_authorization_manifest.json",
                       active_ids=lambda: [self.auth_id])

    def test_authorization_id_collision_rejected(self):
        prior = self.manifest_root / "step_prior_v3_authorization_manifest.json"
        prior.write_text(json.dumps({"authorization_id": self.auth_id,
                                     "attempt_id": "different-attempt"}))
        with self.assertRaisesRegex(RuntimeError, "globally unique"):
            self.issue(active_ids=lambda: [])

    def test_attempt_id_collision_rejected(self):
        prior = self.manifest_root / "step_prior_v3_authorization_manifest.json"
        prior.write_text(json.dumps({"authorization_id": "different-auth",
                                     "attempt_id": self.attempt_id}))
        with self.assertRaisesRegex(RuntimeError, "globally unique"):
            self.issue(active_ids=lambda: [])

    def test_namespace_id_collision_rejected(self):
        prior = self.manifest_root / "step_prior_v3_authorization_manifest.json"
        prior.write_text(json.dumps({"authorization_id": "different-auth",
            "attempt_id": "different-attempt",
            "execution_namespace": {"namespace_id": self.namespace_id}}))
        with self.assertRaisesRegex(RuntimeError, "namespace collision"):
            self.issue(active_ids=lambda: [])

    def test_existing_physical_namespace_rejected(self):
        (self.runs / self.namespace_id).mkdir()
        with self.assertRaisesRegex(RuntimeError, "namespace collision"):
            self.issue(active_ids=lambda: [])

    def test_runner_mismatch_rejected(self):
        bad = copy.deepcopy(self.manifest)
        bad["runner_freeze_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "exact r7"):
            issuer.validate_manifest_bindings(bad, self.freeze)

    def test_agent_mismatch_rejected(self):
        bad = copy.deepcopy(self.manifest)
        bad["treatment_agent_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "exact r7"):
            issuer.validate_manifest_bindings(bad, self.freeze)

    def test_evaluation_mismatch_rejected(self):
        bad = copy.deepcopy(self.manifest)
        bad["benchmark_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "exact r7"):
            issuer.validate_manifest_bindings(bad, self.freeze)

    def test_attempt_identity_mismatch_rejected(self):
        bad = copy.deepcopy(self.manifest)
        bad["attempt_id"] = "attempt-synthetic-wrong"
        with self.assertRaisesRegex(RuntimeError, "namespace identity"):
            issuer.validate_manifest_bindings(bad, self.freeze)

    def test_namespace_identity_mismatch_rejected(self):
        bad = copy.deepcopy(self.manifest)
        bad["execution_namespace"]["namespace_id"] = "wrong-namespace"
        with self.assertRaisesRegex(RuntimeError, "namespace identity"):
            issuer.validate_manifest_bindings(bad, self.freeze)

    def test_lifecycle_contract_mismatch_rejected(self):
        bad = copy.deepcopy(self.manifest)
        bad["authorization_lifecycle_contract_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "exact r7"):
            issuer.validate_manifest_bindings(bad, self.freeze)

    def test_transaction_contract_mismatch_rejected(self):
        bad = copy.deepcopy(self.manifest)
        bad["transaction_contract_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "exact r7"):
            issuer.validate_manifest_bindings(bad, self.freeze)

    def test_import_does_not_create_real_authorization(self):
        self.assertFalse(self.path.exists())
        self.assertFalse((self.runs / self.namespace_id).exists())

    def test_macos_appledouble_sidecar_is_not_treated_as_json_manifest(self):
        (self.manifest_root / "._step_prior_authorization_manifest.json").write_bytes(b"\x00\xb0\xff")
        self.issue(active_ids=lambda: [])
        self.assertTrue(self.path.is_file())


if __name__ == "__main__":
    unittest.main()
