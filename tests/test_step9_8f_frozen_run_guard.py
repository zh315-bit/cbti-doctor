"""Focused evaluation-infrastructure tests; no model or Benchmark case runs."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.frozen_run_guard import FrozenRunGuard, sha256


class FrozenRunGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.benchmark = root / "benchmark.yaml"; self.benchmark.write_text("cases: []\n", encoding="utf-8")
        self.rubric = root / "rubric.md"; self.rubric.write_text("rubric\n", encoding="utf-8")
        self.manifest = root / "manifest.json"
        self.manifest.write_text(json.dumps({
            "benchmark": {"sha256": sha256(self.benchmark)},
            "evaluation_configuration": {"rubric_sha256": sha256(self.rubric)},
        }), encoding="utf-8")
        self.ledger = root / "attempts.jsonl"
        self.guard = FrozenRunGuard(ledger_path=self.ledger, manifest_path=self.manifest,
                                    benchmark_path=self.benchmark, rubric_path=self.rubric)

    def tearDown(self):
        self.temp.cleanup()

    def entry(self, status, *, started=0, completed=0):
        return {
            "attempt_id": f"attempt_{status}", "timestamp": "unknown", "benchmark_hash": sha256(self.benchmark),
            "scoring_hash": sha256(self.rubric), "status": status, "cases_started": started,
            "cases_completed": completed, "model_calls_started": "unknown", "first_case_id": "unknown",
            "last_completed_case_id": "unknown", "failure_stage": None, "failure_type": None,
        }

    def append(self, entry):
        with self.ledger.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry) + "\n")

    def test_manifest_existence_with_zero_cases_is_eligible_when_hashes_match(self):
        report = self.guard.preflight()
        self.assertEqual(report["frozen_inputs"], "MATCH")
        self.assertEqual(report["run_state"], "PREPARED")
        self.assertTrue(report["execution_eligible"])

    def test_benchmark_hash_mismatch_is_blocked(self):
        self.benchmark.write_text("cases: [changed]\n", encoding="utf-8")
        report = self.guard.preflight()
        self.assertEqual(report["reason"], "benchmark_hash_mismatch")
        self.assertFalse(report["execution_eligible"])

    def test_scoring_hash_mismatch_is_blocked(self):
        self.rubric.write_text("changed rubric\n", encoding="utf-8")
        report = self.guard.preflight()
        self.assertEqual(report["reason"], "scoring_hash_mismatch")
        self.assertFalse(report["execution_eligible"])

    def test_started_attempt_blocks_automatic_rerun(self):
        self.append(self.entry("STARTED", started=1))
        self.assertEqual(self.guard.preflight()["run_state"], "STARTED")
        self.assertFalse(self.guard.preflight()["execution_eligible"])

    def test_partial_execution_blocks_automatic_rerun(self):
        self.append(self.entry("FAILED_AFTER_PARTIAL_EXECUTION", started=2, completed=1))
        self.assertEqual(self.guard.preflight()["run_state"], "FAILED_AFTER_PARTIAL_EXECUTION")
        self.assertFalse(self.guard.preflight()["execution_eligible"])

    def test_completed_execution_blocks_rerun(self):
        self.append(self.entry("COMPLETED", started=40, completed=40))
        self.assertEqual(self.guard.preflight()["run_state"], "COMPLETED")
        self.assertFalse(self.guard.preflight()["execution_eligible"])

    def test_failed_before_first_case_allows_new_explicit_authorization(self):
        self.append(self.entry("FAILED_BEFORE_FIRST_CASE"))
        attempt = self.guard.prepare_attempt("manual_step_9_8f_authorization")
        self.assertEqual(attempt["status"], "PREPARED")
        self.assertEqual(attempt["cases_started"], 0)
        self.assertTrue(self.guard.preflight()["execution_eligible"])

    def test_ambiguous_ledger_state_fails_closed(self):
        self.ledger.write_text('{"status":"UNKNOWN"}\n', encoding="utf-8")
        report = self.guard.preflight()
        self.assertEqual(report["run_state"], "AMBIGUOUS")
        self.assertFalse(report["execution_eligible"])

    def test_started_is_durably_appended_before_case_completion(self):
        attempt = self.guard.prepare_attempt("manual_authorization")
        self.guard.mark_started(attempt, "synthetic-01")
        entries = [json.loads(line) for line in self.ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([entry["status"] for entry in entries], ["PREPARED", "STARTED"])
        self.assertEqual(entries[-1]["first_case_id"], "synthetic-01")
        self.assertEqual(entries[-1]["cases_completed"], 0)

    def test_hash_is_rechecked_at_prepared_to_started_boundary(self):
        attempt = self.guard.prepare_attempt("manual_authorization")
        self.benchmark.write_text("cases: [changed after preflight]\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "benchmark_hash_mismatch"):
            self.guard.mark_started(attempt, "synthetic-01")
        entries = [json.loads(line) for line in self.ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([entry["status"] for entry in entries], ["PREPARED"])

    def test_ledger_is_append_only(self):
        self.append(self.entry("FAILED_BEFORE_FIRST_CASE"))
        original = self.ledger.read_bytes()
        self.guard.prepare_attempt("manual_authorization")
        self.assertTrue(self.ledger.read_bytes().startswith(original))

    def test_ledger_never_serializes_a_secret(self):
        self.guard.prepare_attempt("manual_authorization")
        content = self.ledger.read_text(encoding="utf-8")
        self.assertNotIn("DEEPSEEK_API_KEY", content)
        self.assertNotIn("sk-", content)
        with self.assertRaises(ValueError):
            self.guard.prepare_attempt("sk-not-a-valid-authorization")

    def test_preflight_is_read_only(self):
        self.ledger.write_text(json.dumps(self.entry("FAILED_BEFORE_FIRST_CASE")) + "\n", encoding="utf-8")
        before = self.ledger.read_bytes()
        report = self.guard.preflight()
        self.assertTrue(report["execution_eligible"])
        self.assertEqual(self.ledger.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
