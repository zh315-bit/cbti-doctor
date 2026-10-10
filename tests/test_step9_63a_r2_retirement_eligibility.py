"""Offline, synthetic superseded-authorization retirement checks.

Step 9.63c-r5c10ad (AR-1): the synthetic authorization fixture previously
declared ``runner_freeze_revision`` twice ("r8", then "r6"); Python kept only
the last value, so the fixture claimed r6 while being bound to the r8 freeze
``step9_63c_r3_runner_freeze.json``. The retirement predicate correctly rejects
such a self-inconsistent binding. The approved resolution keeps "r8" because
the bound freeze path, its SHA-256 and ``runner_sha256`` are all read from that
r8 freeze; only the stray "r6" key was removed. The determination's
``old_runner_revision`` ("r6") and the real r6/r7 manifest checks are unchanged.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import authorization_lifecycle as lifecycle
from scripts import preflight_step9_62b_mac_local as preflight
from scripts import run_step9_35a_matched_treatment as parent
from scripts import v3_execution_transaction as transaction
from scripts import v3_namespace_allocator as allocator


class SupersededRetirementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.run_root = self.root / "runs"
        self.run_root.mkdir()
        self.ledger = self.root / "authorization_lifecycle_events.jsonl"
        self.auth_path = self.root / "authorization.json"
        self.determination_path = self.root / "determination.json"
        self.auth = {
            "authorization_id": "synthetic-superseded-auth",
            "attempt_id": "synthetic-superseded-attempt",
            "evaluation_id": "synthetic-v3-evaluation",
            "status": "ISSUED_NOT_EXECUTED",
            "authorization_status": lifecycle.ISSUED,
            "consumed": False,
            "consumed_at_utc": None,
            "authorization_consumption_count": 0,
            "runner_freeze_path": "evaluation/v1_2_3/step9_63c_r3_runner_freeze.json",
            "runner_freeze_sha256": hashlib.sha256(
                (lifecycle.ROOT / "evaluation/v1_2_3/step9_63c_r3_runner_freeze.json").read_bytes()
            ).hexdigest(),
            "runner_freeze_revision": "r8",
            "runner_sha256": lifecycle.read_json(
                lifecycle.ROOT / "evaluation/v1_2_3/step9_63c_r3_runner_freeze.json"
            )["runner_sha256"],
            "attempt_id_status": "PREBOUND_IDENTITY_ONLY_NOT_CREATED",
        }
        self.auth_path.write_text(json.dumps(self.auth))
        self.determination = {
            "old_authorization_id": self.auth["authorization_id"],
            "old_authorization_reuse_status": "PROVEN_NON_REUSABLE_BY_FROZEN_CONTRACT",
            "retirement_reason": "SUPERSEDED_RUNNER_FREEZE",
            "old_runner_revision": "r6",
            "current_runner_revision": "r7",
        }
        self.determination_path.write_text(json.dumps(self.determination))

    def tearDown(self):
        self.tmp.cleanup()

    def retire(self):
        return lifecycle.retire_unconsumed_authorization(
            authorization_path=self.auth_path,
            expected_authorization_id=self.auth["authorization_id"],
            run_root=self.run_root, ledger_path=self.ledger,
            lock_path=self.run_root / ".namespace-allocation.lock",
            contract_path=lifecycle.CONTRACT_PATH,
            determination_path=self.determination_path,
            determination_sha256=hashlib.sha256(self.determination_path.read_bytes()).hexdigest(),
        )

    def test_frozen_contract_explicitly_supports_transition(self):
        contract = lifecycle.read_json(lifecycle.CONTRACT_PATH)
        self.assertIn({"from": lifecycle.ISSUED, "to": lifecycle.RETIRED,
            "trigger": "append-only retirement event after all retirement predicates pass"},
            contract["allowed_transitions"])

    def test_retirement_reason_and_runner_identity_are_pinned_transitively(self):
        event = self.retire()
        self.assertEqual(event["reuse_determination_sha256"],
                         hashlib.sha256(self.determination_path.read_bytes()).hexdigest())
        record = json.loads(Path(event["reuse_determination"]).read_text())
        self.assertEqual(record["retirement_reason"], "SUPERSEDED_RUNNER_FREEZE")
        self.assertEqual((record["old_runner_revision"], record["current_runner_revision"]),
                         ("r6", "r7"))

    def test_retirement_is_non_consuming_and_terminal(self):
        event = self.retire()
        self.assertEqual(event["final_status"], lifecycle.RETIRED)
        self.assertFalse(event["authorization_consumed"])
        self.assertEqual(event["authorization_consumption_count"], 0)
        self.assertTrue(event["terminal"])

    def test_original_authorization_remains_immutable(self):
        before = self.auth_path.read_bytes()
        self.retire()
        self.assertEqual(self.auth_path.read_bytes(), before)

    def test_duplicate_retirement_rejected_without_second_event(self):
        self.retire()
        with self.assertRaisesRegex(RuntimeError, "terminal|retired"):
            self.retire()
        self.assertEqual(len(self.ledger.read_text().splitlines()), 1)

    def test_retired_auth_cannot_enter_new_transaction(self):
        # Step 9.63c-r5c10ad AR-3 (same RC7 root cause, surfaced after AR-1): assert the
        # reducer's derived state; the frozen reducer no longer emits a "retired" message.
        journals = self.run_root / ".execution_transactions"
        def reduce():
            return lifecycle.reduce_authorization_lifecycle(
                authorization_id=self.auth["authorization_id"], manifest=self.auth,
                ledger_path=self.ledger, run_root=self.run_root, transaction_root=journals)
        self.assertEqual(reduce()["derived_state"], lifecycle.ISSUED_EXECUTABLE)  # control
        self.retire()
        with self.assertRaisesRegex(RuntimeError, "not executable: INCONSISTENT_FAIL_CLOSED"):
            lifecycle.assert_executable_authorization(
                self.auth["authorization_id"], ledger_path=self.ledger,
                transaction_root=journals)
        retired = reduce()
        self.assertEqual(retired["derived_state"], lifecycle.RETIRED_STATE)
        self.assertIs(retired["executable"], False)
        self.assertFalse(journals.exists())

    def test_retired_auth_cannot_reserve_namespace(self):
        self.retire()
        with mock.patch.object(lifecycle, "EVENT_LEDGER_PATH", self.ledger):
            with self.assertRaisesRegex(RuntimeError, "retired"):
                allocator.reserve_namespace(self.run_root, self.auth["evaluation_id"],
                    self.auth["authorization_id"], self.auth["attempt_id"])

    def test_retirement_does_not_create_attempt_or_namespace(self):
        self.retire()
        namespace = allocator.derive_namespace_id(self.auth["evaluation_id"],
            self.auth["authorization_id"], self.auth["attempt_id"])
        self.assertFalse((self.run_root / namespace).exists())
        self.assertEqual(list(self.run_root.rglob("attempts.jsonl")), [])

    def test_old_attempt_identity_is_not_freshly_reusable(self):
        self.retire()
        with self.assertRaisesRegex(RuntimeError, "retired attempt"):
            lifecycle.assert_fresh_authorization_identity(
                authorization_id="synthetic-new-auth",
                attempt_id=self.auth["attempt_id"],
                evaluation_id=self.auth["evaluation_id"],
                run_root=self.run_root, ledger_path=self.ledger,
                manifest_root=self.root / "empty")

    def test_new_ids_derive_distinct_namespace_without_creating_it(self):
        old = allocator.derive_namespace_id(self.auth["evaluation_id"],
            self.auth["authorization_id"], self.auth["attempt_id"])
        new = allocator.derive_namespace_id(self.auth["evaluation_id"],
            "synthetic-new-auth", "synthetic-new-attempt")
        self.assertNotEqual(old, new)
        self.assertFalse((self.run_root / new).exists())

    def test_active_authorization_count_becomes_zero(self):
        directory = self.root / "evaluation/v1_2_3"
        directory.mkdir(parents=True)
        (directory / "step_synthetic_v3_authorization_manifest.json").write_text(json.dumps(self.auth))
        self.retire()
        with mock.patch.object(lifecycle, "EVENT_LEDGER_PATH", self.ledger):
            self.assertEqual(preflight.active_authorizations(self.root), [])

    def test_current_r7_identity_rejects_old_r6_authorization(self):
        from scripts import run_step9_53_v3_identity_adapter as adapter
        old = adapter.read_json(adapter.ROOT / "evaluation/v1_2_3/step9_62_v3_authorization_manifest.json")
        historical_r7 = adapter.ROOT / "evaluation/v1_2_3/step9_63a_r1_v3_runner_freeze_r7.json"
        freeze = adapter.read_json(historical_r7)
        self.assertEqual(old["runner_freeze_revision"], "r6")
        self.assertEqual(freeze["runner_freeze_revision"], "r7")
        self.assertNotEqual(old["runner_freeze_sha256"], adapter.sha256_file(
            historical_r7))

    def test_v3_agent_and_evaluation_hash_mismatches_fail_closed(self):
        from scripts import run_step9_53_v3_identity_adapter as adapter
        freeze = adapter.read_json(adapter.ROOT / "evaluation/v1_2_3/step9_63a_r1_v3_runner_freeze_r7.json")
        self.assertNotEqual("0" * 64, freeze["v3_agent_sha256"])
        self.assertNotEqual("0" * 64, freeze["bound_identities_sha256"])
        with self.assertRaisesRegex(RuntimeError, "authorization validator identity"):
            adapter._assert_authorization_runner_binding(
                {"treatment_runner_sha256": "0" * 64}, freeze, "0" * 64)

    def test_frozen_evaluation_identity_mismatch_fails_closed(self):
        from scripts import run_step9_53_v3_identity_adapter as adapter
        with mock.patch.object(adapter, "_current_evaluation_bindings",
                               return_value={"all_frozen_hashes_match": False}):
            with self.assertRaisesRegex(RuntimeError, "frozen V3/evaluation identity"):
                adapter.validate_frozen_v3_identity(
                    namespace_root=self.run_root / "future",
                    identity_root=self.run_root)

    def test_wrong_nonreuse_determination_fails_closed(self):
        self.determination["old_authorization_reuse_status"] = "UNKNOWN"
        self.determination_path.write_text(json.dumps(self.determination))
        with self.assertRaisesRegex(RuntimeError, "does not bind"):
            self.retire()
        self.assertFalse(self.ledger.exists())

    def test_existing_transaction_blocks_retirement(self):
        journal_root = self.run_root / ".execution_transactions"
        journal_root.mkdir()
        journal = journal_root / (self.auth["authorization_id"] + ".jsonl")
        transaction._append(journal, {
            "event_type": "PREPARED", "sequence": 1,
            "transaction_id": "synthetic-transaction",
            "authorization_id": self.auth["authorization_id"],
            "attempt_id": self.auth["attempt_id"],
            "namespace_id": "synthetic-namespace",
            "runner_sha256": "a" * 64, "agent_sha256": "b" * 64,
            "evaluation_identity_sha256": "c" * 64,
            "case_set_sha256": "d" * 64,
        }, create=True)
        with self.assertRaisesRegex(RuntimeError, "already bound"):
            self.retire()

    def test_retired_auth_cannot_enter_prepared_committing_or_committed(self):
        from scripts import run_step9_53_v3_identity_adapter as adapter
        self.retire()
        with mock.patch.object(lifecycle, "EVENT_LEDGER_PATH", self.ledger):
            with self.assertRaisesRegex(RuntimeError, "retired"):
                adapter._validate_namespace_lifecycle(
                    run_root=self.run_root / "synthetic-future",
                    evaluation_id=self.auth["evaluation_id"],
                    phase=adapter.PRE_ATTEMPT,
                    authorization_id=self.auth["authorization_id"],
                    attempt_id=self.auth["attempt_id"],
                    authorization_file=self.auth_path,
                    treatment_agent_sha256="agent", runner_sha256="runner",
                    benchmark_sha256="benchmark", case_count=40,
                    case_order_fingerprint_sha256="order",
                    identity_root=self.run_root)
        self.assertFalse((self.run_root / ".execution_transactions").exists())

    def test_retired_auth_cannot_create_parent_attempt(self):
        self.retire()
        with mock.patch.object(lifecycle, "EVENT_LEDGER_PATH", self.ledger):
            with self.assertRaisesRegex(RuntimeError, "retired"):
                parent.run(self.auth["evaluation_id"], self.auth["authorization_id"],
                    self.auth["attempt_id"], self.auth_path, {})
        self.assertEqual(list(self.run_root.rglob("attempts.jsonl")), [])

    def test_retired_auth_cannot_start_case_without_transaction(self):
        self.retire()
        with self.assertRaises(RuntimeError):
            transaction.append_case_started(
                transaction_root=self.run_root / ".execution_transactions",
                lock_path=self.run_root / ".namespace-allocation.lock",
                authorization_id=self.auth["authorization_id"],
                transaction_id="synthetic-transaction", case_id="synthetic-case", ordinal=1)
        self.assertFalse((self.run_root / ".execution_transactions" /
                          (self.auth["authorization_id"] + ".jsonl")).exists())


if __name__ == "__main__":
    unittest.main()
