"""Offline-only bootstrap tests; never call models, Agent, RAG, HTTP, or V4.

Step 9.63c-r5c10ad AR-4: test_09, test_10 and test_18 asserted the superseded r9
resolver contract; they are archived verbatim in
tests/retired/test_step9_63c_r5c4_bootstrap_repair.py.retired and rewritten against the
r11 contract in tests/test_step9_63c_r5c10ad_r11_resolver_contract.py.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts import authorization_lifecycle as lifecycle
from scripts.append_only_ledger import prefix_matches
from scripts import preflight_step9_63c_current_mac_local as preflight
from scripts import v3_runner_identity as identity


class BootstrapRepairTests(unittest.TestCase):
    def test_01_frozen_prefix_exact_match(self):
        data = b"prefix bytes\n"
        self.assertTrue(prefix_matches(data, len(data), hashlib.sha256(data).hexdigest()))

    def test_02_legal_append_preserves_frozen_prefix(self):
        prefix = b"immutable event\n"
        self.assertTrue(prefix_matches(prefix + b"new event\n", len(prefix),
                                                        hashlib.sha256(prefix).hexdigest()))

    def test_03_prefix_byte_mutation_rejected(self):
        prefix = b"immutable event\n"
        self.assertFalse(prefix_matches(b"Immutable event\n", len(prefix),
                                                         hashlib.sha256(prefix).hexdigest()))

    def test_04_prefix_truncation_rejected(self):
        prefix = b"immutable event\n"
        self.assertFalse(prefix_matches(prefix[:-1], len(prefix),
                                                         hashlib.sha256(prefix).hexdigest()))

    def test_05_whitespace_rewrite_rejected(self):
        prefix = b'{"x":1}\n'
        self.assertFalse(prefix_matches(b'{ "x": 1 }\n', len(prefix),
                                                         hashlib.sha256(prefix).hexdigest()))

    def test_06_current_runner_change_does_not_invalidate_historical_freeze_proof(self):
        freeze = lifecycle.read_json(lifecycle.ROOT / "evaluation/v1_2_3/step9_63c_r3_runner_freeze.json")
        self.assertEqual(freeze["runner_freeze_revision"], "r8")
        self.assertNotEqual(hashlib.sha256((lifecycle.ROOT / freeze["formal_entry_runner_path"]).read_bytes()).hexdigest(),
                            freeze["formal_entry_runner_sha256"])
        self.assertEqual(hashlib.sha256((lifecycle.ROOT / "evaluation/v1_2_3/step9_63c_r3_runner_freeze.json").read_bytes()).hexdigest(),
                         "86be96061d8c1cfbf769e21aac388cf2a308f53f6380f67c401d4c64b0bf4e6b")

    def test_07_consumed_authorization_is_not_retired(self):
        self.assertIn('consumed") is not False', Path(lifecycle.__file__).read_text())

    def test_08_duplicate_retirement_is_terminally_rejected(self):
        self.assertIn("already has a terminal retirement event", Path(lifecycle.__file__).read_text())

    def test_11_member_hash_drift_fails_closed(self):
        self.assertIn("current runner freeze member mismatch", Path(identity.__file__).read_text())

    def test_12_member_aggregate_is_order_independent(self):
        rows1 = "a\t" + "1" * 64 + "\nb\t" + "2" * 64 + "\n"
        rows2 = "b\t" + "2" * 64 + "\na\t" + "1" * 64 + "\n"
        self.assertEqual(hashlib.sha256("".join(sorted(rows1.splitlines(keepends=True))).encode()).hexdigest(),
                         hashlib.sha256("".join(sorted(rows2.splitlines(keepends=True))).encode()).hexdigest())

    def test_13_preflight_ids_are_distinct_instances(self):
        self.assertNotEqual(preflight.new_preflight_id(), preflight.new_preflight_id())

    def test_14_preflight_path_is_authorization_scoped(self):
        path = preflight.artifact_path("auth-synthetic", preflight.new_preflight_id(), Path("/tmp"))
        self.assertIn("auth-synthetic", path.name)

    def test_15_failed_preflight_cannot_persist(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(RuntimeError, "PREFLIGHT_NOT_PASSED"):
                preflight.write_preflight({"authorization_id": "auth-synthetic",
                                           "preflight_id": preflight.new_preflight_id()},
                                          artifact_dir=Path(temp))
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_16_import_and_preparation_do_not_create_artifacts(self):
        target = preflight.artifact_path("auth-synthetic", preflight.new_preflight_id(), Path(tempfile.gettempdir()))
        self.assertFalse(target.exists())

    def test_17_old_unknown_provenance_artifact_stays_unaccepted(self):
        self.assertIn("E_STILL_UNPROVEN", Path(
            "evaluation/v1_2_3/step9_63c_r5b_preflight_provenance_resolution.json").read_text())

    def test_19_namespace_source_is_transaction_derived(self):
        source = Path("scripts/run_step9_35a_matched_treatment.py").read_text()
        self.assertIn("assert_transaction_execution_root", source)
        self.assertIn("derive_namespace_id(evaluation_id, authorization_id, attempt_id)", source)

    def test_20_no_global_evaluation_root_collision_in_parent(self):
        source = Path("scripts/run_step9_35a_matched_treatment.py").read_text()
        self.assertIn("out = execution_root / evaluation_id", source)
        self.assertNotIn("out = OUT_ROOT / evaluation_id", source)

    def test_21_preflight_source_has_no_execution_path(self):
        source = Path(preflight.__file__).read_text()
        for forbidden in ("adapter.run(", "begin_and_commit(", "reserve_namespace(", "_case_result(", "/chat/completions"):
            self.assertNotIn(forbidden, source)

    def test_22_old_authorization_is_bound_to_exact_r8_artifact(self):
        auth = json.loads(Path("evaluation/v1_2_3/step9_63c_r4_r8_authorization_manifest.json").read_text())
        self.assertEqual(auth["runner_freeze_revision"], "r8")
        self.assertEqual(auth["runner_freeze_sha256"], "86be96061d8c1cfbf769e21aac388cf2a308f53f6380f67c401d4c64b0bf4e6b")


if __name__ == "__main__":
    unittest.main()
