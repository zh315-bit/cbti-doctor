"""Offline synthetic production-wiring checks. Never opens the sealed case set."""
from __future__ import annotations

import inspect
import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from scripts import authorization_lifecycle as lifecycle
from scripts import run_step9_35a_matched_treatment as parent
from scripts import run_step9_63_v3_formal_execution as entry
from scripts import v3_execution_transaction as tx


class ProductionWiringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.runs = self.root / "runs"
        self.runs.mkdir()
        self.journals = self.runs / ".execution_transactions"
        self.lock = self.runs / ".namespace-allocation.lock"
        self.bindings = {
            "transaction_id": "synthetic-tx", "authorization_id": "synthetic-auth",
            "attempt_id": "synthetic-attempt", "namespace_id": "synthetic-namespace",
            "runner_sha256": "a" * 64, "agent_sha256": "b" * 64,
            "evaluation_identity_sha256": "c" * 64, "case_set_sha256": "d" * 64,
        }
        self.auth = {"authorization_id": "synthetic-auth", "attempt_id": "synthetic-attempt",
                     "authorization_status": "ISSUED_NOT_CONSUMED", "consumed": False,
                     "authorization_consumption_count": 0}

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self):
        return tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock,
            run_root=self.runs, bindings=self.bindings, authorization_state=self.auth)

    def test_entry_dispatches_to_actual_v3_adapter(self):
        self.assertIn("adapter.run(", inspect.getsource(entry.execute_formal))

    def test_adapter_commits_before_namespace_and_parent(self):
        from scripts import run_step9_53_v3_identity_adapter as adapter
        source = inspect.getsource(adapter.run)
        self.assertLess(source.index("begin_and_commit("), source.index("reserve_namespace("))
        self.assertLess(source.index("reserve_namespace("), source.index("parent.run("))

    def test_parent_mandates_transaction(self):
        with self.assertRaisesRegex(RuntimeError, "requires committed transaction"):
            parent.run("synthetic-eval", "synthetic-auth", "synthetic-attempt",
                       self.root / "auth.json", {}, transaction_id=None)

    def test_parent_attempt_ledger_contains_transaction_id(self):
        source = inspect.getsource(parent.run)
        self.assertIn('"transaction_id": transaction_id', source)
        self.assertLess(source.index("claim_attempt("), source.index("out.mkdir("))

    def test_parent_case_start_gates_production_case_call(self):
        source = inspect.getsource(parent.run)
        self.assertLess(source.index("append_case_started("), source.index("_case_result("))
        self.assertLess(source.index("require_committed("), source.index("_create_adaptive_chat_service()"))

    def test_authorization_validator_checks_transaction(self):
        self.assertIn("require_committed(", inspect.getsource(parent.validate_authorization))

    def reduce(self, ledger, journals):
        """Reducer result with the synthetic issuance manifest supplied explicitly."""
        return lifecycle.reduce_authorization_lifecycle(
            authorization_id="synthetic-auth", manifest=self.auth, ledger_path=ledger,
            run_root=self.runs, transaction_root=journals)

    def test_lifecycle_rejects_committed_authorization(self):
        # Step 9.63c-r5c10ad AR-3: the frozen reducer reports every rejection as a
        # derived state; it no longer surfaces the transaction message ("already bound").
        empty = self.root / "empty-events.jsonl"
        self.assertEqual(self.reduce(empty, self.journals)["derived_state"],
                         lifecycle.ISSUED_EXECUTABLE)  # control: rejection below is caused by the commit
        self.commit()
        with self.assertRaisesRegex(RuntimeError, "not executable: INCONSISTENT_FAIL_CLOSED"):
            lifecycle.assert_executable_authorization("synthetic-auth",
                ledger_path=empty, transaction_root=self.journals)
        committed = self.reduce(empty, self.journals)
        self.assertIs(committed["executable"], False)
        self.assertNotEqual(committed["derived_state"], lifecycle.ISSUED_EXECUTABLE)

    def test_lifecycle_rejects_prepared_authorization(self):
        self.journals.mkdir()
        tx._append(self.journals / "synthetic-auth.jsonl",
            {**self.bindings, "event_type": "PREPARED", "sequence": 1}, create=True)
        with self.assertRaises(RuntimeError):
            lifecycle.assert_executable_authorization("synthetic-auth",
                ledger_path=self.root / "empty-events.jsonl", transaction_root=self.journals)

    def test_retired_authorization_rejected(self):
        ledger = self.root / "retirement.jsonl"
        ledger.write_text(json.dumps({"authorization_id": "synthetic-auth",
            "event_type": lifecycle.RETIRE_EVENT, "final_status": lifecycle.RETIRED,
            "authorization_consumed": False, "authorization_consumption_count": 0}) + "\n")
        # Step 9.63c-r5c10ad AR-3: assert the reducer's derived state, not a message.
        empty = self.root / "empty-events.jsonl"
        self.assertEqual(self.reduce(empty, self.journals)["derived_state"],
                         lifecycle.ISSUED_EXECUTABLE)  # control: rejection below is caused by retirement
        with self.assertRaisesRegex(RuntimeError, "not executable: INCONSISTENT_FAIL_CLOSED"):
            lifecycle.assert_executable_authorization("synthetic-auth", ledger_path=ledger,
                transaction_root=self.journals)
        retired = self.reduce(ledger, self.journals)
        self.assertEqual(retired["derived_state"], lifecycle.RETIRED_STATE)
        self.assertIs(retired["executable"], False)

    def test_second_transaction_rejected(self):
        self.commit()
        with self.assertRaises(RuntimeError):
            self.commit()
        events = tx.read_events(self.journals / "synthetic-auth.jsonl")
        self.assertEqual(sum(e["event_type"] == "COMMITTED" for e in events), 1)

    def test_claim_once_and_no_resume(self):
        self.commit()
        kwargs = dict(transaction_root=self.journals, lock_path=self.lock,
            authorization_id="synthetic-auth", transaction_id="synthetic-tx",
            expected_bindings={"attempt_id": "synthetic-attempt"})
        tx.claim_attempt(**kwargs)
        with self.assertRaisesRegex(RuntimeError, "already claimed"):
            tx.claim_attempt(**kwargs)
        self.assertEqual(tx.reconcile(tx.read_events(self.journals / "synthetic-auth.jsonl")),
                         "COMMITTED_ATTEMPT_CLAIMED_NO_AUTO_RESUME")

    def test_prepared_cannot_claim_attempt(self):
        self.journals.mkdir()
        tx._append(self.journals / "synthetic-auth.jsonl",
            {**self.bindings, "event_type": "PREPARED", "sequence": 1}, create=True)
        with self.assertRaisesRegex(RuntimeError, "requires committed"):
            tx.claim_attempt(transaction_root=self.journals, lock_path=self.lock,
                authorization_id="synthetic-auth", transaction_id="synthetic-tx",
                expected_bindings={})

    def test_committing_cannot_claim_attempt(self):
        self.journals.mkdir()
        journal = self.journals / "synthetic-auth.jsonl"
        tx._append(journal, {**self.bindings, "event_type": "PREPARED", "sequence": 1}, create=True)
        tx._append(journal, {**self.bindings, "event_type": "COMMITTING", "sequence": 2})
        with self.assertRaisesRegex(RuntimeError, "requires committed"):
            tx.claim_attempt(transaction_root=self.journals, lock_path=self.lock,
                authorization_id="synthetic-auth", transaction_id="synthetic-tx",
                expected_bindings={})

    def test_mismatched_bindings_fail_before_attempt(self):
        self.commit()
        for field in ("attempt_id", "namespace_id", "runner_sha256", "agent_sha256",
                      "evaluation_identity_sha256", "case_set_sha256"):
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, "mismatch"):
                tx.claim_attempt(transaction_root=self.journals, lock_path=self.lock,
                    authorization_id="synthetic-auth", transaction_id="synthetic-tx",
                    expected_bindings={field: "wrong"})

    def test_mismatched_authorization_fails_before_attempt(self):
        self.commit()
        with self.assertRaises(RuntimeError):
            tx.claim_attempt(transaction_root=self.journals, lock_path=self.lock,
                authorization_id="wrong-auth", transaction_id="synthetic-tx",
                expected_bindings={})

    def test_case_start_requires_claim(self):
        self.commit()
        with self.assertRaisesRegex(RuntimeError, "claimed attempt"):
            tx.append_case_started(transaction_root=self.journals, lock_path=self.lock,
                authorization_id="synthetic-auth", transaction_id="synthetic-tx",
                case_id="case-1", ordinal=1)

    def test_case_start_once_after_claim(self):
        self.commit()
        tx.claim_attempt(transaction_root=self.journals, lock_path=self.lock,
            authorization_id="synthetic-auth", transaction_id="synthetic-tx",
            expected_bindings={})
        kwargs = dict(transaction_root=self.journals, lock_path=self.lock,
            authorization_id="synthetic-auth", transaction_id="synthetic-tx",
            case_id="case-1", ordinal=1)
        tx.append_case_started(**kwargs)
        with self.assertRaisesRegex(RuntimeError, "already started"):
            tx.append_case_started(**kwargs)

    def test_reconcile_uses_same_production_module(self):
        source = inspect.getsource(entry.main)
        self.assertIn("reconcile_journal", source)
        self.assertIn("v3_execution_transaction", source)

    def test_namespace_allocator_uses_committed_transaction(self):
        from scripts import v3_namespace_allocator as allocator
        source = inspect.getsource(allocator.reserve_namespace)
        self.assertIn("require_committed(", source)
        self.assertIn('"transaction_id": transaction_id', source)

    def test_audit_only_does_not_call_execution(self):
        source = inspect.getsource(entry.audit_current_runner_non_consuming)
        self.assertNotIn("execute_formal(", source)
        self.assertNotIn("adapter.run(", source)

    def test_import_side_effect_free(self):
        self.assertFalse(self.journals.exists())
        self.assertFalse(self.lock.exists())

    def test_adapter_actual_dispatch_orders_commit_reserve_parent(self):
        from scripts import run_step9_53_v3_identity_adapter as adapter
        from scripts import v3_namespace_allocator as allocator
        evaluation_id = adapter.EVALUATION_ID
        namespace_id = allocator.derive_namespace_id(evaluation_id, "synthetic-auth", "synthetic-attempt")
        auth_path = self.root / "auth.json"
        auth_path.write_text(json.dumps(self.auth), encoding="utf-8")
        calls = []
        pins = {"treatment_runner_sha256": "a" * 64,
                "treatment_agent_sha256": "b" * 64,
                "case_order_fingerprint_sha256": "d" * 64}

        def commit(**kwargs):
            calls.append("commit")
            self.assertEqual(kwargs["bindings"]["namespace_id"], namespace_id)
            self.assertEqual(kwargs["authorization_state"], self.auth)
            return {"event_type": "COMMITTED"}

        def reserve(*args, **kwargs):
            calls.append("reserve")
            self.assertTrue(kwargs["transaction_id"].startswith("txn-v3-"))
            return namespace_id, self.runs / namespace_id

        def run_parent(*args, **kwargs):
            calls.append("parent")
            self.assertTrue(kwargs["transaction_id"].startswith("txn-v3-"))
            self.assertEqual(kwargs["execution_root"], self.runs / namespace_id)

        with patch.object(adapter, "GLOBAL_OUT_ROOT", self.runs), \
             patch.object(adapter, "validate_frozen_v3_identity", return_value={}), \
             patch.object(adapter, "_authoritative_authorization_bindings", return_value=pins), \
             patch.object(adapter, "read_json", side_effect=lambda path: self.auth if path == auth_path else {"bound_identities_sha256": "c" * 64}), \
             patch.object(parent, "validate_authorization", return_value=(self.auth, pins)), \
             patch.object(tx, "begin_and_commit", side_effect=commit), \
             patch.object(allocator, "reserve_namespace", side_effect=reserve), \
             patch.object(parent, "run", side_effect=run_parent):
            adapter.run(evaluation_id=evaluation_id, authorization_id="synthetic-auth",
                attempt_id="synthetic-attempt", authorization_file=auth_path, supplied={})
        self.assertEqual(calls, ["commit", "reserve", "parent"])

    def test_real_parent_rejects_prepared_before_agent_boundary(self):
        from scripts.v3_namespace_allocator import derive_namespace_id

        self.journals.mkdir()
        tx._append(self.journals / "synthetic-auth.jsonl",
            {**self.bindings,
             "namespace_id": derive_namespace_id("synthetic-eval", "synthetic-auth", "synthetic-attempt"),
             "event_type": "PREPARED", "sequence": 1}, create=True)
        with patch.object(tx, "TRANSACTION_ROOT", self.journals), \
             patch.object(parent, "validate_authorization", return_value=({}, {
                 "treatment_runner_sha256": "a" * 64,
                 "treatment_agent_sha256": "b" * 64,
                 "case_order_fingerprint_sha256": "d" * 64,
             })), \
             patch.object(parent, "read_json", return_value={"bound_identities_sha256": "c" * 64}), \
             patch.object(parent, "OUT_ROOT", self.runs):
            with self.assertRaisesRegex(RuntimeError, "requires committed"):
                parent.run("synthetic-eval", "synthetic-auth", "synthetic-attempt",
                           self.root / "auth.json", {}, transaction_id="synthetic-tx",
                           execution_root=self.runs)
        self.assertEqual(list(self.runs.glob("*/attempts.jsonl")), [])

    def test_old_r6_authorization_rejected_at_r7_namespace_gate(self):
        from scripts import run_step9_53_v3_identity_adapter as adapter
        old = adapter.ROOT / "evaluation/v1_2_3/step9_62_v3_authorization_manifest.json"
        authorization = adapter.read_json(old)
        namespace = self.runs / "synthetic-fresh-namespace"
        with self.assertRaisesRegex(RuntimeError, "retired|future attempt"):
            adapter._validate_namespace_lifecycle(
                run_root=namespace, evaluation_id=authorization["evaluation_id"],
                phase=adapter.PRE_ATTEMPT,
                authorization_id=authorization["authorization_id"],
                attempt_id=authorization["attempt_id"], authorization_file=old,
                treatment_agent_sha256=adapter.V3_AGENT_SHA256,
                runner_sha256="a" * 64, benchmark_sha256="b" * 64,
                case_count=40, case_order_fingerprint_sha256="c" * 64,
                identity_root=self.runs)

    def test_commit_marker_mutation_fails_closed(self):
        self.commit()
        journal = self.journals / "synthetic-auth.jsonl"
        rows = journal.read_text(encoding="utf-8").splitlines()
        last = json.loads(rows[-1])
        last["commit_point"] = False
        journal.write_text("\n".join(rows[:-1] + [json.dumps(last)]) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "burn marker"):
            tx.require_committed(transaction_root=self.journals,
                authorization_id="synthetic-auth", attempt_id="synthetic-attempt",
                namespace_id="synthetic-namespace")

    def test_case_start_binding_mismatch_prevents_append(self):
        self.commit()
        tx.claim_attempt(transaction_root=self.journals, lock_path=self.lock,
            authorization_id="synthetic-auth", transaction_id="synthetic-tx",
            expected_bindings={})
        journal = self.journals / "synthetic-auth.jsonl"
        before = journal.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
            tx.append_case_started(transaction_root=self.journals, lock_path=self.lock,
                authorization_id="synthetic-auth", transaction_id="synthetic-tx",
                case_id="case-1", ordinal=1,
                expected_bindings={"runner_sha256": "wrong"})
        self.assertEqual(journal.read_bytes(), before)

    def test_revalidation_under_lock_rejects_changed_authorization(self):
        changed = {**self.auth, "authorization_consumption_count": 1}
        with self.assertRaisesRegex(RuntimeError, "not ISSUED"):
            tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock,
                run_root=self.runs, bindings=self.bindings, authorization_state=self.auth,
                revalidate_under_lock=lambda: changed)
        self.assertFalse((self.journals / "synthetic-auth.jsonl").exists())

    def test_physical_namespace_collision_before_commit(self):
        (self.runs / "synthetic-namespace").mkdir()
        with self.assertRaisesRegex(RuntimeError, "namespace collision"):
            self.commit()

    def test_historical_attempt_collision_before_commit(self):
        prior = self.runs / "prior"
        prior.mkdir()
        (prior / "attempts.jsonl").write_text(json.dumps({
            "authorization_id": "other", "attempt_id": "synthetic-attempt"}) + "\n")
        with self.assertRaisesRegex(RuntimeError, "attempt collision"):
            self.commit()

    def test_two_production_commit_contenders_only_one_wins(self):
        barrier = threading.Barrier(2)

        def contender():
            barrier.wait()
            try:
                self.commit()
                return "COMMITTED"
            except RuntimeError:
                return "REJECTED"

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: contender(), range(2)))
        self.assertEqual(outcomes.count("COMMITTED"), 1)
        self.assertEqual(outcomes.count("REJECTED"), 1)

    def test_crash_after_namespace_projection_keeps_commit_authoritative(self):
        self.commit()
        container = self.runs / "synthetic-namespace"
        container.mkdir()
        (container / ".namespace_allocation.json").write_text(json.dumps({
            "authorization_id": "synthetic-auth", "attempt_id": "synthetic-attempt",
            "transaction_id": "synthetic-tx"}) + "\n")
        self.assertEqual(tx.reconcile(tx.read_events(self.journals / "synthetic-auth.jsonl")),
                         "COMMITTED_READY_FOR_EXECUTION")
        with self.assertRaises(RuntimeError):
            self.commit()

    def test_crash_after_attempt_projection_keeps_claim_burned(self):
        self.commit()
        tx.claim_attempt(transaction_root=self.journals, lock_path=self.lock,
            authorization_id="synthetic-auth", transaction_id="synthetic-tx",
            expected_bindings={})
        container = self.runs / "synthetic-namespace"
        container.mkdir()
        (container / "attempts.jsonl").write_text(json.dumps({
            "authorization_id": "synthetic-auth", "attempt_id": "synthetic-attempt",
            "transaction_id": "synthetic-tx", "status": "AUTHORIZATION_CONSUMED"}) + "\n")
        self.assertEqual(tx.reconcile(tx.read_events(self.journals / "synthetic-auth.jsonl")),
                         "COMMITTED_ATTEMPT_CLAIMED_NO_AUTO_RESUME")
        with self.assertRaises(RuntimeError):
            self.commit()

    def test_crash_after_case_projection_preserves_partial_trace(self):
        self.commit()
        tx.claim_attempt(transaction_root=self.journals, lock_path=self.lock,
            authorization_id="synthetic-auth", transaction_id="synthetic-tx",
            expected_bindings={})
        tx.append_case_started(transaction_root=self.journals, lock_path=self.lock,
            authorization_id="synthetic-auth", transaction_id="synthetic-tx",
            case_id="synthetic-case", ordinal=1)
        container = self.runs / "synthetic-namespace"
        container.mkdir()
        trace = container / "synthetic-attempt_raw_traces.jsonl"
        trace.write_text('{"synthetic":true}\n')
        before = trace.read_bytes()
        self.assertEqual(tx.reconcile(tx.read_events(self.journals / "synthetic-auth.jsonl")),
                         "COMMITTED_EXECUTION_ALREADY_STARTED")
        self.assertEqual(trace.read_bytes(), before)
        with self.assertRaises(RuntimeError):
            self.commit()


if __name__ == "__main__":
    unittest.main()
