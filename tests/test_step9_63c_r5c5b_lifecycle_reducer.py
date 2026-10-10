from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import authorization_lifecycle as lifecycle
from scripts import preflight_step9_62b_mac_local as legacy


class LifecycleReducerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.run_root = self.root / "runs"
        self.tx_root = self.run_root / ".execution_transactions"
        self.ledger = self.root / "lifecycle.jsonl"
        self.aid = "auth-test-001"
        self.tid = "attempt-test-001"
        self.nsid = "namespace-test-001"
        self.manifest = {
            "authorization_id": self.aid, "attempt_id": self.tid,
            "authorization_status": "ISSUED_NOT_CONSUMED", "consumed": False,
            "authorization_consumption_count": 0,
            "execution_namespace": {"namespace_id": self.nsid},
            "runner_sha256": "a" * 64, "treatment_agent_sha256": "b" * 64,
            "case_set_fingerprint_sha256": "c" * 64,
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def reduce(self):
        return lifecycle.reduce_authorization_lifecycle(
            authorization_id=self.aid, manifest=self.manifest,
            ledger_path=self.ledger, run_root=self.run_root,
            transaction_root=self.tx_root)

    def add_retirement(self):
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self.ledger.write_text(json.dumps({
            "authorization_id": self.aid,
            "event_type": lifecycle.RETIRE_EVENT,
            "final_status": lifecycle.RETIRED,
            "authorization_consumed": False,
            "authorization_consumption_count": 0,
            "lifecycle_event_id": "retire-test-001",
        }) + "\n")

    def add_transaction(self, *, state="COMMITTED", burned=True, case_started=False,
                        attempt_claimed=False):
        self.tx_root.mkdir(parents=True, exist_ok=True)
        common = {"transaction_id": "txn-test-001", "authorization_id": self.aid,
                  "attempt_id": self.tid, "namespace_id": self.nsid,
                  "runner_sha256": self.manifest["runner_sha256"],
                  "agent_sha256": self.manifest["treatment_agent_sha256"],
                  "case_set_sha256": self.manifest["case_set_fingerprint_sha256"],
                  "evaluation_identity_sha256": "d" * 64}
        rows = []
        if state == "UNKNOWN":
            rows = [{**common, "event_type": "MYSTERY", "sequence": 1}]
        else:
            for seq, evt in enumerate(("PREPARED", "COMMITTING", "COMMITTED"), 1):
                row = {**common, "event_type": evt, "sequence": seq}
                if evt == "COMMITTED":
                    row.update(commit_point=True, authorization_irreversibly_burned=burned)
                rows.append(row)
            if attempt_claimed:
                rows.append({**common, "event_type": "ATTEMPT_CLAIMED"})
            if case_started:
                rows.append({**common, "event_type": "CASE_STARTED"})
        (self.tx_root / f"{self.aid}.jsonl").write_text("".join(json.dumps(x) + "\n" for x in rows))
        ns = self.run_root / self.nsid
        ns.mkdir(parents=True, exist_ok=True)
        (ns / ".namespace_allocation.json").write_text(json.dumps({
            "authorization_id": self.aid, "attempt_id": self.tid,
            "namespace_id": self.nsid, "transaction_id": "txn-test-001"}) + "\n")

    def add_consumption(self):
        ledger = self.run_root / self.nsid / "attempts.jsonl"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(json.dumps({"authorization_id": self.aid,
                                      "attempt_id": self.tid,
                                      "status": "AUTHORIZATION_CONSUMED"}) + "\n")

    def synthetic_current_identity_root(self) -> Path:
        """Exercise version filtering without inventing a live r11 identity."""
        artifacts = self.root / "evaluation/v1_2_3"
        artifacts.mkdir(parents=True, exist_ok=True)
        for name in (
                "step9_63a_r3_v3_authorization_manifest.json",
                "step9_63c_r4_r8_authorization_manifest.json",
                "step9_63c_r5c6_r10_v3_authorization_manifest.json"):
            shutil.copyfile(lifecycle.ROOT / "evaluation/v1_2_3" / name,
                            artifacts / name)
        (artifacts / "step9_63c_r11_current_runner_identity.json").write_text(
            json.dumps({
                "artifact_type": "V3_CURRENT_RUNNER_IDENTITY_POINTER",
                "status": "FROZEN_IDENTITY_POINTER_NOT_AUTHORIZATION",
                "runner_freeze_revision": "r11",
                "runner_freeze_path": "evaluation/v1_2_3/step9_63c_r11_runner_freeze.json",
                "execution_permission": False,
                "synthetic_test_fixture": True,
            }) + "\n", encoding="utf-8")
        return self.root

    def test_01_clean_issuance_is_executable(self):
        self.assertEqual(self.reduce()["derived_state"], lifecycle.ISSUED_EXECUTABLE)

    def test_02_clean_issuance_is_reusable(self):
        self.assertTrue(self.reduce()["reusable"])

    def test_03_retirement_is_terminal(self):
        self.add_retirement(); self.assertEqual(self.reduce()["derived_state"], lifecycle.RETIRED_STATE)

    def test_04_retired_is_not_executable(self):
        self.add_retirement(); self.assertFalse(self.reduce()["executable"])

    def test_05_burned_commit_is_terminal(self):
        self.add_transaction(); self.assertEqual(self.reduce()["derived_state"], lifecycle.BURNED_PRE_CASE)

    def test_06_burned_commit_is_not_executable(self):
        self.add_transaction(); self.assertFalse(self.reduce()["executable"])

    def test_07_manifest_issued_does_not_override_burn(self):
        self.add_transaction(); self.assertFalse(self.reduce()["reusable"])

    def test_08_consumption_is_terminal(self):
        self.add_consumption(); self.assertEqual(self.reduce()["derived_state"], lifecycle.CONSUMED_STATE)

    def test_09_consumed_is_not_executable(self):
        self.add_consumption(); self.assertFalse(self.reduce()["executable"])

    def test_10_retirement_and_transaction_conflict_fail_closed(self):
        self.add_retirement(); self.add_transaction()
        self.assertEqual(self.reduce()["derived_state"], lifecycle.INCONSISTENT)

    def test_11_malformed_transaction_fails_closed(self):
        self.add_transaction(state="UNKNOWN")
        self.assertEqual(self.reduce()["derived_state"], lifecycle.INCONSISTENT)

    def test_12_unburned_commit_fails_closed(self):
        self.add_transaction(burned=False)
        self.assertEqual(self.reduce()["derived_state"], lifecycle.INCONSISTENT)

    def test_13_stray_namespace_marker_fails_closed(self):
        ns = self.run_root / self.nsid; ns.mkdir(parents=True)
        (ns / ".namespace_allocation.json").write_text(json.dumps({
            "authorization_id": self.aid, "attempt_id": self.tid}) + "\n")
        self.assertEqual(self.reduce()["derived_state"], lifecycle.INCONSISTENT)

    def test_14_case_started_without_attempt_fails_closed(self):
        self.add_transaction(case_started=True)
        self.assertEqual(self.reduce()["derived_state"], lifecycle.INCONSISTENT)

    def test_15_old_r7_historical_regression(self):
        p = lifecycle.ROOT / "evaluation/v1_2_3/step9_63a_r3_v3_authorization_manifest.json"
        manifest = lifecycle.read_json(p)
        result = lifecycle.reduce_authorization_lifecycle(
            authorization_id=manifest["authorization_id"], manifest=manifest,
            manifest_path=p)
        self.assertEqual(result["derived_state"], lifecycle.BURNED_PRE_CASE)

    def test_16_old_r8_historical_regression(self):
        p = lifecycle.ROOT / "evaluation/v1_2_3/step9_63c_r4_r8_authorization_manifest.json"
        manifest = lifecycle.read_json(p)
        result = lifecycle.reduce_authorization_lifecycle(
            authorization_id=manifest["authorization_id"], manifest=manifest,
            manifest_path=p)
        self.assertEqual(result["derived_state"], lifecycle.RETIRED_STATE)

    def test_17_r7_and_r8_are_not_in_legacy_active_list(self):
        active = legacy.active_authorizations(self.synthetic_current_identity_root())
        self.assertNotIn("auth-step9_63a_r3-d53bbaa35b1e4522bc4a5f57d42c8ef7", active)
        self.assertNotIn("auth-step9_63c_r4-4b2749ce10014634ac6de155d37ec6a9", active)

    def test_18_active_count_is_zero(self):
        self.assertEqual(len(lifecycle.active_authorizations(self.synthetic_current_identity_root())), 0)

    def test_19_assert_executable_rejects_r7(self):
        with self.assertRaises(RuntimeError):
            lifecycle.assert_executable_authorization(
                "auth-step9_63a_r3-d53bbaa35b1e4522bc4a5f57d42c8ef7")

    def test_20_manifest_and_transaction_bytes_unchanged(self):
        p = lifecycle.ROOT / "evaluation/v1_2_3/step9_63a_r3_v3_authorization_manifest.json"
        tx = lifecycle.ROOT / "evaluation/v4_runs/.execution_transactions/auth-step9_63a_r3-d53bbaa35b1e4522bc4a5f57d42c8ef7.jsonl"
        before = (hashlib.sha256(p.read_bytes()).hexdigest(), hashlib.sha256(tx.read_bytes()).hexdigest())
        lifecycle.reduce_authorization_lifecycle(
            authorization_id="auth-step9_63a_r3-d53bbaa35b1e4522bc4a5f57d42c8ef7",
            manifest_path=p)
        after = (hashlib.sha256(p.read_bytes()).hexdigest(), hashlib.sha256(tx.read_bytes()).hexdigest())
        self.assertEqual(before, after)

    def test_21_historical_pin_inventory_still_passes(self):
        inventory = lifecycle.read_json(
            lifecycle.ROOT / "evaluation/v1_2_3/step9_60a_v3_historical_integrity_audit.json")
        checked = 0
        for pin in inventory["historical_pins"].values():
            path = lifecycle.ROOT / pin["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), pin["sha256"])
            checked += 1
        # The append-only lifecycle ledger uses a frozen prefix pin, not its
        # historical full-file digest, because later authorized events append.
        supplemental = dict(legacy.SUPPLEMENTAL_HISTORICAL_PINS)
        ledger_rel = "evaluation/v1_2_3/authorization_lifecycle_events.jsonl"
        supplemental.pop(ledger_rel)
        for relpath, expected in supplemental.items():
            self.assertEqual(hashlib.sha256((lifecycle.ROOT / relpath).read_bytes()).hexdigest(), expected)
            checked += 1
        ledger = (lifecycle.ROOT / ledger_rel).read_bytes()
        self.assertEqual(hashlib.sha256(ledger[:1161]).hexdigest(),
                         "ca168f6939c4697a7a7bccc0b365b414d9a0e632f40de4242eb0a47e2d985285")
        checked += 1
        self.assertEqual(checked, 55)


if __name__ == "__main__":
    unittest.main()
