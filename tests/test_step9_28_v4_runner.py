"""Offline safeguards for Step 9.28; no V4 case is ever executed here."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run_step9_28_v4_heldout as runner
from scripts import preflight_step9_12_local as shared_preflight


class V4RunnerPreparationTests(unittest.TestCase):
    def test_frozen_identities_match_before_any_formal_attempt(self):
        frozen = runner.verify_frozen_identity()
        # The Step 9.33 treatment intentionally supersedes the historical V4
        # runner's Agent pin. That runner must fail closed, not bless treatment.
        self.assertFalse(frozen["freeze_match"])
        self.assertFalse(frozen["current_agent_matches_final_freeze"])
        self.assertTrue(frozen["benchmark_v4_sha256_match"])
        self.assertTrue(frozen["harness_match"])
        self.assertTrue(frozen["scoring_match"])
        self.assertTrue(frozen["metric_registry_match"])
        self.assertTrue(frozen["one_shot_rules_match"])
        self.assertFalse(frozen["case_specific_agent_logic_found"])

    def test_unissued_template_cannot_create_a_ledger_or_read_a_case(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "v4_runs"
            matched_fixture = runner.verify_frozen_identity()
            matched_fixture["freeze_match"] = True
            with patch.object(runner, "OUT_ROOT", out), patch.object(
                runner, "verify_frozen_identity", return_value=matched_fixture
            ):
                with self.assertRaisesRegex(RuntimeError, "authorization is not issued"):
                    runner.run(runner.EVALUATION_ID, "offline-auth", "offline-attempt", runner.AUTH_TEMPLATE)
            self.assertFalse(out.exists())

    def test_local_preflight_never_calls_case_execution_path(self):
        frozen = {"freeze_match": False}
        with patch.object(runner, "verify_frozen_identity", return_value=frozen), \
             patch.object(runner, "schema_compatible", return_value=True), \
             patch.object(runner, "_case_result", side_effect=AssertionError("case execution")), \
             patch.object(shared_preflight, "_import_ready", return_value=(True, [])), \
             patch.object(shared_preflight, "_dns_ready", return_value=False):
            result = runner.local_preflight()
        self.assertEqual(result["v4_case_executed"], 0)
        self.assertFalse(result["v4_score_generated"])
        self.assertFalse(result["benchmark_v4_accessed_by_agent"])

    def test_prior_ledger_blocks_any_automatic_rerun(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            matched_fixture = runner.verify_frozen_identity()
            matched_fixture["freeze_match"] = True
            ledger = out / runner.EVALUATION_ID / "attempts.jsonl"
            ledger.parent.mkdir(parents=True)
            ledger.write_text('{"status":"FAILED_AFTER_PARTIAL_EXECUTION"}\n', encoding="utf-8")
            with patch.object(runner, "OUT_ROOT", out), patch.object(
                runner, "verify_frozen_identity", return_value=matched_fixture
            ):
                with self.assertRaisesRegex(RuntimeError, "automatic rerun is forbidden"):
                    runner.validate_authorization(runner.AUTH_TEMPLATE, runner.EVALUATION_ID, "offline-auth", "offline-attempt")

    def test_preflight_contract_accepts_equivalent_spellings_and_rejects_unsafe_state(self):
        self.assertTrue(runner.preflight_contract_valid({
            "ready_for_final_authorization": True, "benchmark_v4_accessed_by_agent": False,
        }))
        self.assertTrue(runner.preflight_contract_valid({
            "ready_for_v4_final_authorization": True, "benchmark_v4_accessed_for_evaluation": False,
        }))
        self.assertTrue(runner.preflight_contract_valid({
            "ready_for_final_authorization": True, "ready_for_v4_final_authorization": True,
            "benchmark_v4_accessed_by_agent": False, "benchmark_v4_accessed_for_evaluation": False,
        }))
        self.assertFalse(runner.preflight_contract_valid({
            "ready_for_final_authorization": True, "ready_for_v4_final_authorization": False,
            "benchmark_v4_accessed_by_agent": False,
        }))
        self.assertFalse(runner.preflight_contract_valid({
            "ready_for_final_authorization": False, "benchmark_v4_accessed_by_agent": False,
        }))
        self.assertFalse(runner.preflight_contract_valid({
            "ready_for_final_authorization": True, "benchmark_v4_accessed_by_agent": True,
        }))
        self.assertFalse(runner.preflight_contract_valid({"ready_for_final_authorization": True}))


if __name__ == "__main__":
    unittest.main()
