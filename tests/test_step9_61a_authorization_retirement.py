"""Synthetic/offline coverage for append-only non-consuming authorization retirement."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import authorization_lifecycle as lifecycle
from scripts import v3_namespace_allocator as allocator


AUTH_ID = "synthetic-retire-auth-1"
ATTEMPT_ID = "synthetic-retire-attempt-1"
EVALUATION_ID = "synthetic-retire-eval-1"


class AuthorizationRetirementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.run_root = self.root / "v4_runs"
        self.run_root.mkdir()
        self.ledger = self.root / "evaluation" / "authorization_lifecycle_events.jsonl"
        self.lock = self.run_root / ".namespace-allocation.lock"
        self.auth_path = self.root / "authorization.json"
        self.determination_path = self.root / "retirement-determination.json"
        self.auth = {
            "status": "ISSUED_NOT_EXECUTED",
            "authorization_status": "ISSUED_NOT_CONSUMED",
            "authorization_id": AUTH_ID,
            "attempt_id": ATTEMPT_ID,
            "evaluation_id": EVALUATION_ID,
            "attempt_id_status": "PREBOUND_IDENTITY_ONLY_NOT_CREATED",
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
        }
        self._write_json(self.auth_path, self.auth)
        self._write_json(self.determination_path, {
            "old_authorization_id": AUTH_ID,
            "old_authorization_reuse_status": "PROVEN_NON_REUSABLE_BY_FROZEN_CONTRACT",
        })

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def _write_json(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def _retire(self, *, determination_path=None):
        path = determination_path or self.determination_path
        return lifecycle.retire_unconsumed_authorization(
            authorization_path=self.auth_path,
            expected_authorization_id=AUTH_ID,
            run_root=self.run_root,
            ledger_path=self.ledger,
            lock_path=self.lock,
            contract_path=lifecycle.CONTRACT_PATH,
            determination_path=path,
            determination_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        )

    def _attempt_event(self, **overrides):
        event = {"authorization_id": AUTH_ID, "attempt_id": ATTEMPT_ID,
                 "status": "STARTED", "cases_started": 1, "cases_completed": 0}
        event.update(overrides)
        ledger = self.run_root / "old" / "attempts.jsonl"
        ledger.parent.mkdir()
        ledger.write_text(json.dumps(event) + "\n", encoding="utf-8")

    def test_issued_unconsumed_transitions_to_terminal_retirement(self):
        event = self._retire()
        self.assertEqual(event["original_status"], lifecycle.ISSUED)
        self.assertEqual(event["final_status"], lifecycle.RETIRED)
        self.assertTrue(event["terminal"])
        self.assertEqual(lifecycle.authorization_retirement_event(AUTH_ID, ledger_path=self.ledger), event)

    def test_retirement_does_not_consume(self):
        event = self._retire()
        self.assertFalse(event["authorization_consumed"])
        self.assertEqual(event["authorization_consumption_count"], 0)

    def test_retirement_does_not_create_attempt_or_namespace(self):
        event = self._retire()
        namespace = self.run_root / allocator.derive_namespace_id(EVALUATION_ID, AUTH_ID, ATTEMPT_ID)
        self.assertFalse(event["attempt_created"])
        self.assertFalse(event["namespace_created"])
        self.assertFalse(namespace.exists())
        self.assertFalse((self.run_root / "old").exists())

    def test_retired_identity_is_rejected_by_shared_validator_guard(self):
        self._retire()
        with self.assertRaisesRegex(RuntimeError, "retired"):
            lifecycle.assert_not_retired(AUTH_ID, ledger_path=self.ledger)

    def test_allocator_cannot_reserve_retired_identity(self):
        self._retire()
        with mock.patch.object(lifecycle, "EVENT_LEDGER_PATH", self.ledger):
            with self.assertRaisesRegex(RuntimeError, "retired"):
                allocator.reserve_namespace(self.run_root, EVALUATION_ID, AUTH_ID, ATTEMPT_ID)

    def test_retired_identity_cannot_return_to_active_state(self):
        event = self._retire()
        self.assertEqual(event["final_status"], lifecycle.RETIRED)
        with self.assertRaisesRegex(RuntimeError, "terminal|retired"):
            self._retire()

    def test_consumed_authorization_cannot_be_retired_as_unconsumed(self):
        self.auth.update(consumed=True, consumed_at_utc="synthetic", authorization_consumption_count=1)
        self._write_json(self.auth_path, self.auth)
        with self.assertRaisesRegex(RuntimeError, "unconsumed retirement predicate"):
            self._retire()
        self.assertFalse(self.ledger.exists())

    def test_authorization_with_existing_attempt_cannot_be_retired(self):
        self._attempt_event(cases_started=0)
        with self.assertRaisesRegex(RuntimeError, "attempt, namespace"):
            self._retire()

    def test_authorization_with_started_case_cannot_be_retired(self):
        self._attempt_event(cases_started=1)
        with self.assertRaisesRegex(RuntimeError, "attempt, namespace"):
            self._retire()

    def test_existing_namespace_cannot_be_retired(self):
        namespace = self.run_root / allocator.derive_namespace_id(EVALUATION_ID, AUTH_ID, ATTEMPT_ID)
        namespace.mkdir()
        with self.assertRaisesRegex(RuntimeError, "attempt, namespace"):
            self._retire()

    def test_arbitrary_active_authorization_requires_exact_nonreuse_determination(self):
        self._write_json(self.determination_path, {
            "old_authorization_id": AUTH_ID,
            "old_authorization_reuse_status": "UNKNOWN",
        })
        with self.assertRaisesRegex(RuntimeError, "does not bind this authorization"):
            self._retire()
        self.assertFalse(self.ledger.exists())

    def test_determination_hash_mismatch_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
            lifecycle.retire_unconsumed_authorization(
                authorization_path=self.auth_path, expected_authorization_id=AUTH_ID,
                run_root=self.run_root, ledger_path=self.ledger, lock_path=self.lock,
                contract_path=lifecycle.CONTRACT_PATH, determination_path=self.determination_path,
                determination_sha256="0" * 64,
            )

    def test_fresh_authorization_and_attempt_must_differ_from_retired_identity(self):
        self._retire()
        with self.assertRaisesRegex(RuntimeError, "retired authorization"):
            lifecycle.assert_fresh_authorization_identity(
                authorization_id=AUTH_ID, attempt_id="new-attempt", evaluation_id=EVALUATION_ID,
                run_root=self.run_root, ledger_path=self.ledger, manifest_root=self.root / "empty-manifests")
        with self.assertRaisesRegex(RuntimeError, "retired attempt"):
            lifecycle.assert_fresh_authorization_identity(
                authorization_id="synthetic-retire-auth-2", attempt_id=ATTEMPT_ID,
                evaluation_id=EVALUATION_ID, run_root=self.run_root, ledger_path=self.ledger,
                manifest_root=self.root / "empty-manifests")
        lifecycle.assert_fresh_authorization_identity(
            authorization_id="synthetic-retire-auth-2", attempt_id="synthetic-retire-attempt-2",
            evaluation_id=EVALUATION_ID, run_root=self.run_root, ledger_path=self.ledger,
            manifest_root=self.root / "empty-manifests")

    def test_fresh_identity_gets_distinct_derived_namespace(self):
        old = allocator.derive_namespace_id(EVALUATION_ID, AUTH_ID, ATTEMPT_ID)
        new = allocator.derive_namespace_id(EVALUATION_ID, "synthetic-retire-auth-2",
                                            "synthetic-retire-attempt-2")
        self.assertNotEqual(old, new)

    def test_malformed_retirement_ledger_fails_closed(self):
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        self.ledger.write_text("{bad json\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "malformed"):
            lifecycle.assert_not_retired(AUTH_ID, ledger_path=self.ledger)


if __name__ == "__main__":
    unittest.main()
