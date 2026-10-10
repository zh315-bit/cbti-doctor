"""Offline attempt-namespace tests; no benchmark cases or production services."""
from __future__ import annotations

import inspect
import hashlib
import json
import sys
import tempfile
import threading
import types
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import run_step9_35a_matched_treatment as parent
from scripts import v3_execution_transaction as tx
from scripts.v3_namespace_allocator import derive_namespace_id, reserve_namespace


class NamespaceBoundaryTests(unittest.TestCase):
    EVAL = "synthetic-eval"
    AUTH = "synthetic-auth"
    ATTEMPT = "synthetic-attempt"
    TXN = "synthetic-txn"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runs = self.root / "runs"
        self.runs.mkdir()
        self.journals = self.runs / ".execution_transactions"
        self.lock = self.runs / ".namespace-allocation.lock"
        self.ns = derive_namespace_id(self.EVAL, self.AUTH, self.ATTEMPT)
        self.bindings = {
            "transaction_id": self.TXN, "authorization_id": self.AUTH,
            "attempt_id": self.ATTEMPT, "namespace_id": self.ns,
            "runner_sha256": "a" * 64, "agent_sha256": "b" * 64,
            "evaluation_identity_sha256": "c" * 64, "case_set_sha256": "d" * 64,
        }
        self.auth_state = {
            "authorization_id": self.AUTH, "attempt_id": self.ATTEMPT,
            "authorization_status": "ISSUED_NOT_CONSUMED", "consumed": False,
            "authorization_consumption_count": 0,
        }

    def commit(self, bindings=None):
        return tx.begin_and_commit(
            transaction_root=self.journals, lock_path=self.lock, run_root=self.runs,
            bindings=bindings or self.bindings, authorization_state=self.auth_state)

    def reserve(self):
        with patch.object(tx, "TRANSACTION_ROOT", self.journals):
            return reserve_namespace(self.runs, self.EVAL, self.AUTH, self.ATTEMPT,
                                     transaction_id=self.TXN)

    def root_guard(self, path=None, **identities):
        with patch.object(tx, "RUN_ROOT", self.runs):
            return parent.assert_transaction_execution_root(
                path if path is not None else self.runs / self.ns,
                identities.get("evaluation_id", self.EVAL),
                identities.get("authorization_id", self.AUTH),
                identities.get("attempt_id", self.ATTEMPT),
                identities.get("transaction_id", self.TXN))

    def test_t1_historical_global_root_is_not_false_collision(self):
        (self.runs / self.EVAL).mkdir()
        self.commit()
        _, fresh = self.reserve()
        self.assertEqual(self.root_guard(fresh), fresh)
        self.assertFalse((fresh / self.EVAL).exists())

    def test_t2_same_attempt_reuse_fails_closed(self):
        self.commit()
        self.reserve()
        with self.assertRaises(RuntimeError):
            self.reserve()

    def test_t3_same_namespace_reuse_fails_closed(self):
        (self.runs / self.ns).mkdir()
        with self.assertRaisesRegex(RuntimeError, "namespace collision"):
            self.commit()

    def test_t4_same_authorization_cannot_commit_twice(self):
        self.commit()
        with self.assertRaises(RuntimeError):
            self.commit()

    def test_t5_concurrent_same_attempt_one_winner(self):
        barrier = threading.Barrier(2)

        def contender(_):
            barrier.wait()
            try:
                self.commit()
                return "WIN"
            except RuntimeError:
                return "REJECT"

        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(contender, range(2))), ["WIN", "REJECT"])

    def test_t6_distinct_attempts_get_distinct_roots(self):
        (self.runs / self.EVAL).mkdir()
        barrier = threading.Barrier(2)

        def contender(index):
            auth = f"synthetic-auth-{index}"
            attempt = f"synthetic-attempt-{index}"
            namespace = derive_namespace_id(self.EVAL, auth, attempt)
            bindings = {**self.bindings, "transaction_id": f"synthetic-txn-{index}",
                        "authorization_id": auth, "attempt_id": attempt,
                        "namespace_id": namespace}
            state = {**self.auth_state, "authorization_id": auth, "attempt_id": attempt}
            barrier.wait()
            tx.begin_and_commit(transaction_root=self.journals, lock_path=self.lock,
                                run_root=self.runs, bindings=bindings, authorization_state=state)
            allocated, root = reserve_namespace(self.runs, self.EVAL, auth, attempt)
            self.assertEqual(allocated, namespace)
            return root

        with ThreadPoolExecutor(max_workers=2) as pool:
            roots = list(pool.map(contender, (1, 2)))
        self.assertEqual(len(set(roots)), 2)
        self.assertTrue(all(root.is_dir() for root in roots))

    def test_t7_committed_zero_cases_cannot_reuse(self):
        self.commit()
        self.assertEqual(tx.reconcile(tx.read_events(self.journals / f"{self.AUTH}.jsonl")),
                         "COMMITTED_READY_FOR_EXECUTION")
        with self.assertRaises(RuntimeError):
            self.commit()

    def test_t8_existing_current_case_directory_no_overwrite(self):
        self.commit()
        _, root = self.reserve()
        output = root / self.EVAL
        output.mkdir()
        with self.assertRaises(FileExistsError):
            output.mkdir(exist_ok=False)

    def test_t9_crash_after_reservation_preserves_identity(self):
        self.commit()
        self.reserve()
        self.assertEqual(tx.reconcile(tx.read_events(self.journals / f"{self.AUTH}.jsonl")),
                         "COMMITTED_READY_FOR_EXECUTION")
        with self.assertRaises(RuntimeError):
            self.reserve()

    def test_t10_crash_after_commit_before_case_burns_identity(self):
        self.commit()
        journal = self.journals / f"{self.AUTH}.jsonl"
        self.assertFalse(any(event["event_type"] == "CASE_STARTED"
                             for event in tx.read_events(journal)))
        with self.assertRaises(RuntimeError):
            self.commit()

    def test_t11_parent_and_transaction_roots_must_match(self):
        self.commit()
        self.reserve()
        with self.assertRaisesRegex(RuntimeError, "differs"):
            self.root_guard(self.runs)
        with self.assertRaisesRegex(RuntimeError, "ownership"):
            self.root_guard(transaction_id="foreign-txn")
        self.assertEqual(self.root_guard(), self.runs / self.ns)

    def test_t12_no_default_global_root_on_formal_path(self):
        from scripts import run_step9_53_v3_identity_adapter as adapter

        source = inspect.getsource(parent.run)
        self.assertIn("run_root=execution_root", source)
        self.assertIn("out = execution_root / evaluation_id", source)
        self.assertNotIn("out = OUT_ROOT / evaluation_id", source)
        self.assertIn("execution_root=candidate_root", inspect.getsource(adapter.run))
        with self.assertRaisesRegex(RuntimeError, "explicit transaction-resolved root"):
            parent.run(self.EVAL, self.AUTH, self.ATTEMPT, self.root / "absent.json",
                       {}, transaction_id=self.TXN)

    def test_original_failure_parent_validator_reaches_pre_case_sentinel(self):
        (self.runs / self.EVAL).mkdir()
        freeze = json.loads((parent.FREEZE_DIR / "step9_63a_r1_v3_runner_freeze_r7.json").read_text())
        cases = [{"case_id": f"synthetic-{index:03d}", "user_query": "synthetic",
                  "task_type": "KNOWLEDGE_QA", "diary_facts": [], "follow_up_facts": []}
                 for index in range(1, 41)]
        synthetic_benchmark = self.root / "synthetic_cases.json"
        synthetic_benchmark.write_text(json.dumps({"cases": cases}), encoding="utf-8")
        case_order_sha = parent.case_order_fingerprint([case["case_id"] for case in cases])
        pins = {**freeze["bound_identities"], "evaluation_id": self.EVAL,
                "all_frozen_hashes_match": True,
                "treatment_runner_sha256": self.bindings["runner_sha256"]}
        pins["benchmark_sha256"] = hashlib.sha256(synthetic_benchmark.read_bytes()).hexdigest()
        pins["case_order_fingerprint_sha256"] = case_order_sha
        self.bindings["agent_sha256"] = pins["treatment_agent_sha256"]
        self.bindings["evaluation_identity_sha256"] = freeze["bound_identities_sha256"]
        self.bindings["case_set_sha256"] = case_order_sha
        self.commit()
        _, fresh = self.reserve()
        auth = {key: pins[key] for key in (
            "treatment_agent_sha256", "baseline_agent_sha256", "benchmark_sha256",
            "benchmark_manifest_sha256", "harness_sha256", "scoring_sha256",
            "metric_registry_sha256", "one_shot_rules_sha256", "matched_protocol_sha256",
            "baseline_metric_lock_sha256", "claim_policy_sha256",
            "production_case_path_runner_sha256", "case_order_fingerprint_sha256")}
        auth.update({"status": "ISSUED_NOT_EXECUTED", "authorization_type": "ONE_SHOT_MATCHED_TREATMENT",
                     "comparison_class": parent.COMPARISON_CLASS, "evaluation_id": self.EVAL,
                     "authorization_id": self.AUTH, "attempt_id": self.ATTEMPT,
                     "treatment_runner_sha256": pins["treatment_runner_sha256"],
                     "case_count": 40, "max_formal_attempts": 1, "consumed": False,
                     "consumed_at_utc": None, "authorization_status": "ISSUED_NOT_CONSUMED",
                     "authorization_consumption_count": 0, "authorized_by": "synthetic-reviewer"})
        auth_path = self.root / "synthetic-auth.json"
        auth_path.write_text(json.dumps(auth))
        supplied = {key: pins[key] for key in parent.supplied_hash_keys()}
        with patch.object(tx, "RUN_ROOT", self.runs), \
             patch.object(tx, "TRANSACTION_ROOT", self.journals), \
             patch.object(tx, "LOCK_PATH", self.lock), \
             patch("scripts.authorization_lifecycle.assert_not_retired"), \
             patch("scripts.authorization_lifecycle.lifecycle_lock", return_value=nullcontext()), \
             patch.object(parent, "CURRENT_V3_FREEZE_NAME", "step9_63a_r1_v3_runner_freeze_r7.json"), \
             patch.object(parent, "current_v3_freeze",
                          return_value={"bound_identities_sha256": freeze["bound_identities_sha256"]}), \
             patch.object(parent, "BENCHMARK", synthetic_benchmark):
            parent.validate_authorization(auth_path, self.EVAL, self.AUTH, self.ATTEMPT,
                                          supplied, run_root=fresh, frozen=pins,
                                          transaction_id=self.TXN)
            fake_flask = types.ModuleType("adaptive_agent.flask_app")
            fake_flask._create_adaptive_chat_service = lambda: SimpleNamespace(recorder=None)
            fake_flask.create_app = lambda service: SimpleNamespace(config={})
            fake_yaml = types.ModuleType("yaml")
            fake_yaml.safe_load = lambda source: json.loads(source)
            with patch.object(parent, "current_frozen_bindings", return_value=pins), \
                 patch.dict(sys.modules, {"adaptive_agent.flask_app": fake_flask}), \
                 patch.dict(sys.modules, {"yaml": fake_yaml}), \
                 patch("scripts.run_step9_28_v4_heldout._case_result",
                       side_effect=RuntimeError("CASE_EXECUTION_REACHED")):
                with self.assertRaisesRegex(RuntimeError, "CASE_EXECUTION_REACHED"):
                    parent.run(self.EVAL, self.AUTH, self.ATTEMPT, auth_path, supplied,
                               transaction_id=self.TXN, execution_root=fresh)
        events = tx.read_events(self.journals / f"{self.AUTH}.jsonl")
        self.assertEqual(sum(event["event_type"] == "CASE_STARTED" for event in events), 1)
        self.assertTrue((fresh / self.EVAL / "attempts.jsonl").is_file())


if __name__ == "__main__":
    unittest.main()
