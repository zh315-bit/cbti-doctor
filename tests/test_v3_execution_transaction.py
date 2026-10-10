"""Synthetic filesystem tests for the Step 9.63a transaction journal."""
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scripts import v3_execution_transaction as tx

_BEGIN_AND_COMMIT = tx.begin_and_commit


class ExecutionTransactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.journals = self.root / "transactions"
        self.runs = self.root / "runs"
        self.runs.mkdir()
        self.lock = self.root / ".lock"
        self.bindings = {
            "transaction_id": "synthetic-tx-1", "authorization_id": "synthetic-auth-1",
            "attempt_id": "synthetic-attempt-1", "namespace_id": "synthetic-namespace-1",
            "runner_sha256": "a" * 64, "agent_sha256": "b" * 64,
            "evaluation_identity_sha256": "c" * 64, "case_set_sha256": "d" * 64,
        }
        self._original_begin = tx.begin_and_commit
        def synthetic_begin(*, transaction_root, lock_path, bindings, authorization_state=None):
            if authorization_state is None:
                authorization_state = {"authorization_id": bindings["authorization_id"],
                    "attempt_id": bindings["attempt_id"], "authorization_status": "ISSUED_NOT_CONSUMED",
                    "consumed": False, "authorization_consumption_count": 0}
            return _BEGIN_AND_COMMIT(transaction_root=transaction_root, lock_path=lock_path,
                run_root=self.runs,
                bindings=bindings, authorization_state=authorization_state)
        tx.begin_and_commit = synthetic_begin

    def tearDown(self):
        tx.begin_and_commit = self._original_begin
        self.tmp.cleanup()

    def _path(self):
        return self.journals / "synthetic-auth-1.jsonl"

    def _commit(self, bindings=None):
        return tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock,
                                   bindings=bindings or self.bindings)

    def _claim(self):
        return tx.claim_attempt(transaction_root=self.journals, lock_path=self.lock,
            authorization_id="synthetic-auth-1", transaction_id="synthetic-tx-1",
            expected_bindings={"attempt_id": "synthetic-attempt-1"})

    def test_01_prepared_is_durable(self):
        self.journals.mkdir()
        event = {**self.bindings, "event_type": "PREPARED", "sequence": 1, "created_at": "t"}
        tx._append(self._path(), event, create=True)
        self.assertEqual(tx.current_state(tx.read_events(self._path())), "PREPARED")

    def test_02_prepared_to_committing_to_committed(self):
        result = tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock,
                                     bindings=self.bindings)
        self.assertEqual(result["event_type"], "COMMITTED")
        self.assertEqual([e["event_type"] for e in tx.read_events(self._path())],
                         ["PREPARED", "COMMITTING", "COMMITTED"])

    def test_03_illegal_backward_transition_rejected(self):
        events = [{"event_type": state, "sequence": n,
                   **({"commit_point": True, "authorization_irreversibly_burned": True}
                      if state == "COMMITTED" else {})}
                  for n, state in enumerate(("PREPARED", "COMMITTING", "COMMITTED", "PREPARED"), 1)]
        with self.assertRaisesRegex(RuntimeError, "illegal"):
            tx._validate_events(events)

    def test_04_duplicate_transaction_for_authorization_rejected(self):
        tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock, bindings=self.bindings)
        with self.assertRaisesRegex(RuntimeError, "already bound"):
            tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock, bindings=self.bindings)

    def test_05_duplicate_attempt_binding_rejected(self):
        tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock, bindings=self.bindings)
        other = {**self.bindings, "transaction_id": "synthetic-tx-2",
                 "authorization_id": "synthetic-auth-2"}
        with self.assertRaisesRegex(RuntimeError, "already bound"):
            tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock, bindings=other)

    def test_06_duplicate_namespace_binding_rejected(self):
        tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock, bindings=self.bindings)
        other = {**self.bindings, "transaction_id": "synthetic-tx-2",
                 "authorization_id": "synthetic-auth-2", "attempt_id": "synthetic-attempt-2"}
        with self.assertRaisesRegex(RuntimeError, "already bound"):
            tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock, bindings=other)

    def test_07_concurrent_contenders_only_one_commits(self):
        barrier = threading.Barrier(2)
        def contender():
            barrier.wait()
            try:
                tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock,
                                    bindings=self.bindings)
                return "COMMITTED"
            except RuntimeError:
                return "REJECTED"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: contender(), range(2)))
        self.assertEqual(results.count("COMMITTED"), 1)
        self.assertEqual(sum(e["event_type"] == "COMMITTED" for e in tx.read_events(self._path())), 1)

    def test_08_crash_before_prepared_is_unconsumed(self):
        self.assertEqual(tx.reconcile([]), "SAFE_TO_ABORT_UNCONSUMED")

    def test_09_crash_after_prepared_is_abortable(self):
        self._write_state(("PREPARED",))
        self.assertEqual(tx.reconcile(tx.read_events(self._path())), "SAFE_TO_ABORT_UNCONSUMED")

    def test_10_crash_after_committing_requires_commit_completion(self):
        self._write_state(("PREPARED", "COMMITTING"))
        self.assertEqual(tx.reconcile(tx.read_events(self._path())), "MUST_COMPLETE_COMMIT")

    def test_11_reconciliation_persists_abort(self):
        self._write_state(("PREPARED",))
        tx.reconcile_journal(transaction_root=self.journals, lock_path=self.lock,
                             authorization_id="synthetic-auth-1")
        self.assertEqual(tx.current_state(tx.read_events(self._path())), "ABORTED_UNCONSUMED")

    def test_12_reconciliation_completes_committing(self):
        self._write_state(("PREPARED", "COMMITTING"))
        tx.reconcile_journal(transaction_root=self.journals, lock_path=self.lock,
                             authorization_id="synthetic-auth-1")
        self.assertEqual(tx.current_state(tx.read_events(self._path())), "COMMITTED")

    def test_13_crash_after_authorization_projection_is_not_authoritative(self):
        self._write_state(("PREPARED", "COMMITTING"))
        self.assertEqual(tx.reconcile(tx.read_events(self._path())), "MUST_COMPLETE_COMMIT")

    def test_14_crash_after_attempt_projection_is_not_authoritative(self):
        self._write_state(("PREPARED", "COMMITTING"))
        self.assertEqual(tx.reconcile(tx.read_events(self._path())), "MUST_COMPLETE_COMMIT")

    def test_15_crash_after_namespace_projection_is_not_authoritative(self):
        self._write_state(("PREPARED", "COMMITTING"))
        self.assertEqual(tx.reconcile(tx.read_events(self._path())), "MUST_COMPLETE_COMMIT")

    def test_16_crash_before_final_commit_marker_requires_completion(self):
        self._write_state(("PREPARED", "COMMITTING"))
        self.assertEqual(tx.reconcile(tx.read_events(self._path())), "MUST_COMPLETE_COMMIT")

    def test_17_committed_reconciles_to_execution_ready(self):
        tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock, bindings=self.bindings)
        self.assertEqual(tx.reconcile(tx.read_events(self._path())), "COMMITTED_READY_FOR_EXECUTION")

    def test_18_case_start_rejected_without_commit(self):
        self._write_state(("PREPARED",))
        with self.assertRaisesRegex(RuntimeError, "requires exact COMMITTED"):
            tx.append_case_started(transaction_root=self.journals, lock_path=self.lock,
                authorization_id="synthetic-auth-1", transaction_id="synthetic-tx-1",
                case_id="case-1", ordinal=1)

    def test_19_case_start_allowed_only_after_commit(self):
        tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock, bindings=self.bindings)
        self._claim()
        tx.append_case_started(transaction_root=self.journals, lock_path=self.lock,
            authorization_id="synthetic-auth-1", transaction_id="synthetic-tx-1",
            case_id="case-1", ordinal=1)
        self.assertEqual(tx.reconcile(tx.read_events(self._path())),
                         "COMMITTED_EXECUTION_ALREADY_STARTED")

    def test_20_committed_binding_mismatch_rejected(self):
        tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock, bindings=self.bindings)
        with self.assertRaisesRegex(RuntimeError, "binding mismatch"):
            tx.require_committed(transaction_root=self.journals, authorization_id="synthetic-auth-1",
                attempt_id="wrong-attempt", namespace_id="synthetic-namespace-1")

    def test_21_retired_and_consumed_states_are_not_accepted_as_bindings(self):
        for state in ("RETIRED_UNCONSUMED_NON_REUSABLE", "CONSUMED"):
            with self.subTest(state=state), self.assertRaisesRegex(RuntimeError, "not ISSUED"):
                tx.validate_authorization_state({"authorization_status": state})

    def test_22_corrupt_partial_append_fails_closed(self):
        self.journals.mkdir()
        self._path().write_text('{"event_type":"COMMIT', encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "corrupt"):
            tx.read_events(self._path())

    def test_23_partial_trace_is_preserved_without_resume(self):
        self._write_state(("PREPARED", "COMMITTING", "COMMITTED"))
        self._claim()
        with self._path().open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({**self.bindings, "event_type": "CASE_STARTED",
                                     "ordinal": 1, "case_id": "case-1"}) + "\n")
        self.assertEqual(tx.reconcile(tx.read_events(self._path())),
                         "COMMITTED_EXECUTION_ALREADY_STARTED")

    def test_24_no_automatic_rerun_for_duplicate_case(self):
        tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock, bindings=self.bindings)
        self._claim()
        tx.append_case_started(transaction_root=self.journals, lock_path=self.lock,
            authorization_id="synthetic-auth-1", transaction_id="synthetic-tx-1",
            case_id="case-1", ordinal=1)
        with self.assertRaisesRegex(RuntimeError, "already started"):
            tx.append_case_started(transaction_root=self.journals, lock_path=self.lock,
                authorization_id="synthetic-auth-1", transaction_id="synthetic-tx-1",
                case_id="case-1", ordinal=1)

    def test_25_commit_binds_required_execution_identities(self):
        tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock, bindings=self.bindings)
        event = tx.require_committed(transaction_root=self.journals,
            authorization_id="synthetic-auth-1", attempt_id="synthetic-attempt-1",
            namespace_id="synthetic-namespace-1")
        self.assertEqual(event["agent_sha256"], "b" * 64)
        self.assertEqual(event["case_set_sha256"], "d" * 64)

    def test_26_import_has_no_filesystem_side_effect(self):
        self.assertFalse(self.journals.exists())
        self.assertFalse(self.lock.exists())

    def test_27_journal_uses_fsync_durability_declaration(self):
        result = tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock,
                                     bindings=self.bindings)
        self.assertEqual(result["durability"], "file_and_parent_directory_fsync")

    def test_28_committed_authorization_cannot_start_second_transaction(self):
        tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock, bindings=self.bindings)
        with self.assertRaises(RuntimeError):
            tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock, bindings=self.bindings)

    def test_29_reconciliation_is_deterministic(self):
        self._write_state(("PREPARED", "COMMITTING"))
        events = tx.read_events(self._path())
        self.assertEqual(tx.reconcile(events), tx.reconcile(events))

    def test_30_terminal_abort_cannot_become_committed(self):
        self._write_state(("PREPARED",))
        tx.reconcile_journal(transaction_root=self.journals, lock_path=self.lock,
                             authorization_id="synthetic-auth-1")
        with self.assertRaisesRegex(RuntimeError, "already bound"):
            tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock,
                                bindings=self.bindings)

    def test_31_preexisting_physical_namespace_collision_rejected(self):
        (self.runs / "synthetic-namespace-1").mkdir()
        with self.assertRaisesRegex(RuntimeError, "namespace collision"):
            self._commit()

    def test_32_prior_attempt_identity_collision_rejected(self):
        ledger_dir = self.runs / "prior"
        ledger_dir.mkdir()
        (ledger_dir / "attempts.jsonl").write_text(json.dumps({
            "authorization_id": "unrelated-auth", "attempt_id": "synthetic-attempt-1"}) + "\n",
            encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "attempt collision"):
            self._commit()

    def _write_state(self, states):
        self.journals.mkdir(exist_ok=True)
        base = {**self.bindings, "created_at": "synthetic-time"}
        for seq, state in enumerate(states, 1):
            tx._append(self._path(), {**base, "event_type": state, "sequence": seq,
                                    **({"commit_point": True,
                                        "authorization_irreversibly_burned": True}
                                       if state == "COMMITTED" else {})},
                       create=seq == 1)


if __name__ == "__main__":
    unittest.main()
