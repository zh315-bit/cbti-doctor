"""Offline tests for the prepared V3 wrapper; never open a V3 benchmark."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from adaptive_agent import flask_app
from scripts import preflight_step9_12_local as prior_preflight
from scripts import run_step9_20_v3_heldout as runner


class V3RunnerPreparationTests(unittest.TestCase):
    def test_v3_runner_remains_bound_to_historical_agent_identity(self):
        frozen = runner.verify_frozen_identity()
        # Step 9.23 created a new development candidate. The original V3
        # runner must continue rejecting it rather than accepting a new Agent.
        self.assertFalse(frozen["freeze_match"])
        self.assertFalse(frozen["agent_match"])
        self.assertTrue(frozen["harness_match"])
        self.assertTrue(frozen["scoring_match"])

    def test_unissued_template_cannot_start_an_attempt(self):
        template = runner.FREEZE_DIR / "step9_20a_v3_authorization_template.json"
        # Prove both that the old V3 identity rejects the new candidate and
        # that an unissued authorization remains rejected if hashes match.
        with patch.object(runner, "model_configuration_match", return_value=True):
            with self.assertRaisesRegex(RuntimeError, "frozen identity mismatch"):
                runner.validate_authorization(template, runner.EVALUATION_ID, "synthetic-auth", "synthetic-attempt")
        matching_freeze = {"freeze_match": True, "agent_hash": "a", "harness_hash": "h",
                           "scoring_hash": "s", "runner_sha256": "r"}
        with patch.object(runner, "verify_frozen_identity", return_value=matching_freeze), \
             patch.object(runner, "model_configuration_match", return_value=True):
            with self.assertRaisesRegex(RuntimeError, "authorization is not issued"):
                runner.validate_authorization(template, runner.EVALUATION_ID, "synthetic-auth", "synthetic-attempt")

    def test_local_preflight_does_not_probe_model_without_credential(self):
        with patch("dotenv.load_dotenv"), patch.dict("os.environ", {"DEEPSEEK_API_KEY": ""}), \
             patch.object(prior_preflight, "_import_ready", return_value=(True, [])), \
             patch.object(prior_preflight, "_dns_ready", return_value=False), \
             patch.object(prior_preflight, "_model_probe", side_effect=AssertionError("model called")), \
             patch.object(prior_preflight, "_smoke", side_effect=AssertionError("smoke called")):
            result = runner.local_preflight()
        self.assertFalse(result["credential_present"])
        self.assertEqual(result["synthetic_production_smoke"], "NOT_RUN")
        self.assertFalse(result["ready_for_authorization"])
        self.assertFalse(result["benchmark_v3_accessed"])

    def test_first_access_is_durable_before_synthetic_fixture_read_and_second_run_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "synthetic").mkdir()
            source = root / "synthetic" / "fixture.yaml"
            source.write_text(
                "cases:\n  - case_id: SYNTHETIC-ONLY\n    user_query: test\n"
                "    task_type: KNOWLEDGE_QA\n    diary_facts: {availability: unavailable, facts: {}}\n"
                "    follow_up_facts: {}\n", encoding="utf-8",
            )
            out = root / "outputs"
            auth = {"benchmark_path": "synthetic/fixture.yaml", "authorized_by": "offline-test"}
            frozen = {"freeze_match": True, "agent_hash": "a", "harness_hash": "h",
                      "runner_sha256": "r", "scoring_hash": "s"}
            original_read = Path.read_bytes

            def guarded_read(path):
                if path == source:
                    ledger = (out / runner.EVALUATION_ID / "attempts.jsonl").read_text(encoding="utf-8")
                    self.assertIn('"status": "V3_FIRST_ACCESS"', ledger)
                    self.assertNotIn('"status": "STARTED"', ledger)
                return original_read(path)

            with patch.object(runner, "ROOT", root), patch.object(runner, "OUT_ROOT", out), \
                 patch.object(runner, "validate_authorization", return_value=(auth, frozen)), \
                 patch.object(runner, "verify_frozen_identity", return_value=frozen), \
                 patch.object(runner, "model_configuration_match", return_value=True), \
                 patch.object(runner, "_case_result", return_value=(
                     {"case_id": "SYNTHETIC-ONLY"},
                     {"case_id": "SYNTHETIC-ONLY", "score_status": "PENDING_FROZEN_RUBRIC_REVIEW"})), \
                 patch.object(flask_app, "_create_adaptive_chat_service", return_value=SimpleNamespace()), \
                 patch.object(flask_app, "create_app", return_value=SimpleNamespace(config={})), \
                 patch.object(Path, "read_bytes", guarded_read):
                runner.run(runner.EVALUATION_ID, "synthetic-auth", "synthetic-attempt", root / "auth.json")
                with self.assertRaisesRegex(RuntimeError, "ledger already exists"):
                    runner.run(runner.EVALUATION_ID, "synthetic-auth", "synthetic-attempt", root / "auth.json")

            output_dir = out / runner.EVALUATION_ID
            events = [json.loads(line) for line in (output_dir / "attempts.jsonl").read_text().splitlines()]
            self.assertEqual([item["status"] for item in events], [
                "PREPARED", "V3_FIRST_ACCESS", "V3_SOURCE_HASHED", "STARTED", "CASE_COMPLETED", "COMPLETED",
            ])
            self.assertEqual(len((output_dir / "synthetic-attempt_raw_traces.jsonl").read_text().splitlines()), 1)
            self.assertEqual(len((output_dir / "synthetic-attempt_case_results.jsonl").read_text().splitlines()), 1)

    def test_case_exception_is_preserved_and_cannot_be_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "synthetic").mkdir()
            (root / "synthetic" / "fixture.yaml").write_text(
                "cases:\n  - case_id: SYNTHETIC-FAILURE\n    user_query: test\n"
                "    task_type: KNOWLEDGE_QA\n    diary_facts: {}\n    follow_up_facts: {}\n",
                encoding="utf-8",
            )
            frozen = {"freeze_match": True, "agent_hash": "a", "harness_hash": "h",
                      "runner_sha256": "r", "scoring_hash": "s"}
            with patch.object(runner, "ROOT", root), patch.object(runner, "OUT_ROOT", root / "outputs"), \
                 patch.object(runner, "validate_authorization", return_value=(
                     {"benchmark_path": "synthetic/fixture.yaml", "authorized_by": "offline-test"}, frozen)), \
                 patch.object(runner, "verify_frozen_identity", return_value=frozen), \
                 patch.object(runner, "model_configuration_match", return_value=True), \
                 patch.object(runner, "_case_result", side_effect=RuntimeError("synthetic failure")), \
                 patch.object(flask_app, "_create_adaptive_chat_service", return_value=SimpleNamespace()), \
                 patch.object(flask_app, "create_app", return_value=SimpleNamespace(config={})):
                with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
                    runner.run(runner.EVALUATION_ID, "synthetic-auth", "synthetic-attempt", root / "auth.json")
                with self.assertRaisesRegex(RuntimeError, "ledger already exists"):
                    runner.run(runner.EVALUATION_ID, "synthetic-auth", "synthetic-attempt", root / "auth.json")
            events = [json.loads(line) for line in
                      (root / "outputs" / runner.EVALUATION_ID / "attempts.jsonl").read_text().splitlines()]
            self.assertEqual(events[-1]["status"], "FAILED_AFTER_PARTIAL_EXECUTION")
            self.assertEqual(events[-1]["cases_started"], 1)
            self.assertEqual(events[-1]["cases_completed"], 0)


if __name__ == "__main__":
    unittest.main()
