"""Offline transaction scanner fixtures; never touch the production journal root."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts import v3_execution_transaction as tx


class TransactionScannerRepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.journals = self.root / "transactions"
        self.journals.mkdir()
        self.runs = self.root / "runs"
        self.runs.mkdir()
        self.lock = self.root / "allocation.lock"
        self.identity = {
            "transaction_id": "tx-old", "authorization_id": "auth-old",
            "attempt_id": "attempt-old", "namespace_id": "namespace-old",
            "runner_sha256": "a" * 64, "agent_sha256": "b" * 64,
            "evaluation_identity_sha256": "c" * 64,
            "case_set_sha256": "d" * 64,
        }

    def journal(self, name="auth-old"):
        return self.journals / f"{name}.jsonl"

    def write_states(self, states=("PREPARED",), *, name="auth-old", identity=None):
        identity = identity or self.identity
        rows = []
        for sequence, state in enumerate(states, 1):
            row = {**identity, "event_type": state, "sequence": sequence}
            if state == "COMMITTED":
                row.update(commit_point=True, authorization_irreversibly_burned=True)
            rows.append(row)
        self.journal(name).write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        return rows

    def scan(self, *, authorization_id="auth-new", attempt_id="attempt-new",
             namespace_id="namespace-new", root=None):
        return tx._find_identity(root or self.journals,
            authorization_id=authorization_id, attempt_id=attempt_id,
            namespace_id=namespace_id)

    def sidecar(self, *, name="auth-old", magic=b"\x00\x05\x16\x07"):
        path = self.journals / f"._{name}.jsonl"
        path.write_bytes(magic + b"\xb0not-jsonl")
        return path

    def test_t01_valid_canonical_journal(self):
        expected = self.write_states()
        self.assertEqual(tx.read_events(self.journal()), expected)
        self.assertTrue(self.scan(authorization_id="auth-old"))
        self.assertFalse(self.scan())

    def test_t02_verified_appledouble_companion_is_excluded(self):
        self.write_states()
        self.sidecar()
        self.assertTrue(self.scan(attempt_id="attempt-old"))
        self.assertFalse(self.scan())

    def test_t03_unrelated_binary_and_finder_metadata_not_parsed(self):
        (self.journals / "unrelated.bin").write_bytes(b"\xff\xfe")
        (self.journals / ".DS_Store").write_bytes(b"\xff\xfe")
        self.assertFalse(self.scan())

    def test_t04_canonical_invalid_utf8_fails_closed(self):
        self.journal().write_bytes(b"\xff\xfe")
        with self.assertRaises(UnicodeDecodeError):
            self.scan()

    def test_t05_canonical_invalid_json_and_sequence_fail_closed(self):
        self.journal().write_text("{broken\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "corrupt"):
            self.scan()
        self.write_states(("COMMITTED",))
        with self.assertRaisesRegex(RuntimeError, "illegal transaction state"):
            self.scan()

    def test_t06_duplicate_authorization_attempt_namespace_and_transaction(self):
        self.write_states()
        self.assertTrue(self.scan(authorization_id="auth-old"))
        self.assertTrue(self.scan(attempt_id="attempt-old"))
        self.assertTrue(self.scan(namespace_id="namespace-old"))
        state = {"authorization_id": "auth-old", "attempt_id": "attempt-old",
                 "authorization_status": "ISSUED_NOT_CONSUMED", "consumed": False,
                 "authorization_consumption_count": 0}
        with self.assertRaisesRegex(RuntimeError, "already bound"):
            tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock,
                run_root=self.runs, bindings=self.identity, authorization_state=state)
        self.assertEqual([e["event_type"] for e in tx.read_events(self.journal())],
                         ["PREPARED"])

    def test_t07_historical_committed_journal_remains_valid(self):
        expected = self.write_states(("PREPARED", "COMMITTING", "COMMITTED"))
        self.assertEqual(tx.read_events(self.journal()), expected)
        self.assertEqual(tx.current_state(expected), "COMMITTED")
        self.assertFalse(self.scan())
        self.assertTrue(self.scan(authorization_id="auth-old"))

    def test_t08_burned_authorization_reducer_stays_terminal(self):
        from scripts.authorization_lifecycle import (
            BURNED_PRE_CASE, reduce_authorization_lifecycle,
        )
        self.write_states(("PREPARED", "COMMITTING", "COMMITTED"))
        namespace = self.runs / "namespace-old"
        namespace.mkdir()
        (namespace / ".namespace_allocation.json").write_text(json.dumps({
            "authorization_id": "auth-old", "attempt_id": "attempt-old",
            "namespace_id": "namespace-old", "transaction_id": "tx-old",
        }), encoding="utf-8")
        manifest = {
            "authorization_id": "auth-old", "attempt_id": "attempt-old",
            "authorization_status": "ISSUED_NOT_CONSUMED", "consumed": False,
            "authorization_consumption_count": 0,
            "execution_namespace": {"namespace_id": "namespace-old"},
            "runner_sha256": "a" * 64, "treatment_agent_sha256": "b" * 64,
            "frozen_evaluation_identity_sha256": "c" * 64,
            "case_set_fingerprint_sha256": "d" * 64,
        }
        result = reduce_authorization_lifecycle(authorization_id="auth-old",
            manifest=manifest, ledger_path=self.root / "lifecycle.jsonl",
            run_root=self.runs, transaction_root=self.journals)
        self.assertEqual(result["derived_state"], BURNED_PRE_CASE)
        self.assertFalse(result["executable"])
        self.assertFalse(result["reusable"])
        self.assertTrue(self.scan(authorization_id="auth-old"))

    def test_t09_order_never_hides_later_corruption(self):
        self.write_states(name="a-auth", identity={**self.identity,
            "authorization_id": "a-auth"})
        self.sidecar(name="a-auth")
        (self.journals / "z-auth.jsonl").write_bytes(b"\xff")
        with self.assertRaises(UnicodeDecodeError):
            self.scan(authorization_id="a-auth")

    def test_t10_orphan_wrong_magic_and_symlink_sidecars_fail_closed(self):
        sidecar = self.sidecar()
        with self.assertRaisesRegex(RuntimeError, "unrecognized"):
            self.scan()
        self.write_states()
        sidecar.write_bytes(b"BAD!metadata")
        with self.assertRaisesRegex(RuntimeError, "unrecognized"):
            self.scan()
        sidecar.unlink()
        sidecar.symlink_to(self.journal())
        with self.assertRaisesRegex(RuntimeError, "not a regular file"):
            self.scan()

    def test_t11_canonical_directory_and_symlink_fail_closed(self):
        self.journal().mkdir()
        with self.assertRaisesRegex(RuntimeError, "not a regular file"):
            self.scan()
        self.journal().rmdir()
        self.journal().symlink_to(self.root / "outside.jsonl")
        with self.assertRaisesRegex(RuntimeError, "not a regular file"):
            self.scan()

    def test_t12_root_symlink_and_nondirectory_fail_closed(self):
        link = self.root / "transactions-link"
        link.symlink_to(self.journals, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, "root symlink"):
            self.scan(root=link)
        file_root = self.root / "transactions-file"
        file_root.write_bytes(b"x")
        with self.assertRaisesRegex(RuntimeError, "not a directory"):
            self.scan(root=file_root)

    def test_t13_invalid_name_and_filename_identity_mismatch_fail_closed(self):
        self.write_states(name="auth-old")
        self.journal().rename(self.journals / "!unsafe.jsonl")
        with self.assertRaisesRegex(RuntimeError, "invalid transaction journal filename"):
            self.scan()
        (self.journals / "!unsafe.jsonl").rename(self.journal("auth-other"))
        with self.assertRaisesRegex(RuntimeError, "filename or identity mismatch"):
            self.scan()

    def test_t14_canonical_binary_and_empty_journal_fail_closed(self):
        self.journal().write_bytes(b"\xff\x00")
        with self.assertRaises(UnicodeDecodeError):
            self.scan()
        self.journal().write_bytes(b"")
        with self.assertRaisesRegex(RuntimeError, "filename or identity mismatch"):
            self.scan()

    def test_t15_mac_metadata_and_unicode_filename_boundary(self):
        self.write_states()
        self.sidecar()
        (self.journals / ".DS_Store").write_bytes(b"\xff")
        self.assertFalse(self.scan())
        (self.journals / "é.jsonl").write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "invalid transaction journal filename"):
            self.scan()

    def test_t15b_case_insensitive_alias_collision_when_supported(self):
        self.write_states()
        if not self.journal("AUTH-OLD").exists():
            self.skipTest("temporary filesystem is case-sensitive")
        other = {**self.identity, "transaction_id": "tx-new",
                 "authorization_id": "AUTH-OLD", "attempt_id": "attempt-new",
                 "namespace_id": "namespace-new"}
        state = {"authorization_id": "AUTH-OLD", "attempt_id": "attempt-new",
                 "authorization_status": "ISSUED_NOT_CONSUMED", "consumed": False,
                 "authorization_consumption_count": 0}
        with self.assertRaisesRegex(RuntimeError, "journal collision"):
            tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock,
                run_root=self.runs, bindings=other, authorization_state=state)

    def test_t16_existing_crash_state_validation_unmodified(self):
        expected = {
            (): "SAFE_TO_ABORT_UNCONSUMED",
            ("PREPARED",): "SAFE_TO_ABORT_UNCONSUMED",
            ("PREPARED", "COMMITTING"): "MUST_COMPLETE_COMMIT",
            ("PREPARED", "COMMITTING", "COMMITTED"): "COMMITTED_READY_FOR_EXECUTION",
        }
        for states, outcome in expected.items():
            with self.subTest(states=states):
                if states:
                    self.write_states(states)
                    events = tx.read_events(self.journal())
                else:
                    events = []
                self.assertEqual(tx.reconcile(events), outcome)

    def test_t17_nonfrozen_preflight_scanner_parity_for_sidecars(self):
        from scripts import preflight_step9_63c_r5c7_mac_local as producer
        view = SimpleNamespace(TRANSACTION_ROOT=self.journals,
                               read_events=tx.read_events)
        self.write_states()
        sidecar = self.sidecar()
        self.assertFalse(self.scan())
        producer._assert_no_transaction_identity_collision(view)
        sidecar.write_bytes(b"BAD!metadata")
        with self.assertRaisesRegex(RuntimeError, "unrecognized"):
            self.scan()
        with self.assertRaisesRegex(RuntimeError, "UNRECOGNIZED_TRANSACTION_SIDECAR"):
            producer._assert_no_transaction_identity_collision(view)


if __name__ == "__main__":
    unittest.main()
