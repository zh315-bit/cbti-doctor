"""Offline authorization-contract tests; no benchmark case is loaded or run."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import run_step9_35a_matched_treatment as runner


class MatchedTreatmentAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.pins = {
            "all_frozen_hashes_match": True,
            "evaluation_id": "heldout-v4-step9_34a-treatment-20260928-01",
            "comparison_class": runner.COMPARISON_CLASS,
            "treatment_agent_sha256": "a" * 64,
            "baseline_agent_sha256": "b" * 64,
            "benchmark_sha256": "c" * 64,
            "benchmark_manifest_sha256": "d" * 64,
            "harness_sha256": "e" * 64,
            "scoring_sha256": "f" * 64,
            "metric_registry_sha256": "1" * 64,
            "one_shot_rules_sha256": "2" * 64,
            "matched_protocol_sha256": "3" * 64,
            "baseline_metric_lock_sha256": "4" * 64,
            "claim_policy_sha256": "5" * 64,
            "treatment_runner_sha256": "6" * 64,
            "production_case_path_runner_sha256": "8" * 64,
            "case_count": 40,
            "case_order_fingerprint_sha256": "7" * 64,
        }
        self.auth_id = "test-auth-unique"
        self.attempt_id = "test-attempt-unique"
        self.auth = {
            "status": "ISSUED_NOT_EXECUTED",
            "authorization_type": "ONE_SHOT_MATCHED_TREATMENT",
            "comparison_class": runner.COMPARISON_CLASS,
            "evaluation_id": self.pins["evaluation_id"],
            "authorization_id": self.auth_id,
            "attempt_id": self.attempt_id,
            "treatment_agent_sha256": self.pins["treatment_agent_sha256"],
            "baseline_agent_sha256": self.pins["baseline_agent_sha256"],
            "benchmark_sha256": self.pins["benchmark_sha256"],
            "benchmark_manifest_sha256": self.pins["benchmark_manifest_sha256"],
            "harness_sha256": self.pins["harness_sha256"],
            "scoring_sha256": self.pins["scoring_sha256"],
            "metric_registry_sha256": self.pins["metric_registry_sha256"],
            "one_shot_rules_sha256": self.pins["one_shot_rules_sha256"],
            "matched_protocol_sha256": self.pins["matched_protocol_sha256"],
            "baseline_metric_lock_sha256": self.pins["baseline_metric_lock_sha256"],
            "claim_policy_sha256": self.pins["claim_policy_sha256"],
            "treatment_runner_sha256": self.pins["treatment_runner_sha256"],
            "production_case_path_runner_sha256": self.pins["production_case_path_runner_sha256"],
            "case_count": 40,
            "case_order_fingerprint_sha256": self.pins["case_order_fingerprint_sha256"],
            "max_formal_attempts": 1,
            "consumed": False,
            "consumed_at_utc": None,
            "authorized_by": "offline-test-fixture",
            # Deliberately no randomized-preregistration prerequisite.
        }
        self.auth_path = self.root / "authorization.json"
        self._write_auth()
        self.supplied = {key: self.pins[key] for key in (
            "treatment_agent_sha256", "benchmark_sha256", "harness_sha256",
            "scoring_sha256", "metric_registry_sha256", "one_shot_rules_sha256",
            "matched_protocol_sha256",
        )}

    def tearDown(self):
        self.tempdir.cleanup()

    def _write_auth(self):
        self.auth_path.write_text(json.dumps(self.auth), encoding="utf-8")

    def _validate(self):
        return runner.validate_authorization(
            self.auth_path, self.pins["evaluation_id"], self.auth_id,
            self.attempt_id, self.supplied, run_root=self.root / "runs", frozen=self.pins,
        )

    def test_01_correct_matched_treatment_contract_accepted(self):
        auth, pins = self._validate()
        self.assertEqual(auth["comparison_class"], runner.COMPARISON_CLASS)
        self.assertIs(pins, self.pins)

    def test_02_wrong_treatment_agent_sha_rejected(self):
        self.supplied["treatment_agent_sha256"] = "9" * 64
        with self.assertRaisesRegex(RuntimeError, "treatment_agent_sha256"):
            self._validate()

    def test_03_baseline_agent_supplied_as_treatment_rejected(self):
        self.supplied["treatment_agent_sha256"] = self.pins["baseline_agent_sha256"]
        with self.assertRaisesRegex(RuntimeError, "treatment_agent_sha256"):
            self._validate()

    def test_04_wrong_benchmark_sha_rejected(self):
        self.supplied["benchmark_sha256"] = "9" * 64
        with self.assertRaisesRegex(RuntimeError, "benchmark_sha256"):
            self._validate()

    def test_05_wrong_harness_sha_rejected(self):
        self.supplied["harness_sha256"] = "9" * 64
        with self.assertRaisesRegex(RuntimeError, "harness_sha256"):
            self._validate()

    def test_06_wrong_scoring_sha_rejected(self):
        self.supplied["scoring_sha256"] = "9" * 64
        with self.assertRaisesRegex(RuntimeError, "scoring_sha256"):
            self._validate()

    def test_07_wrong_metric_registry_sha_rejected(self):
        self.supplied["metric_registry_sha256"] = "9" * 64
        with self.assertRaisesRegex(RuntimeError, "metric_registry_sha256"):
            self._validate()

    def test_08_wrong_one_shot_rules_sha_rejected(self):
        self.supplied["one_shot_rules_sha256"] = "9" * 64
        with self.assertRaisesRegex(RuntimeError, "one_shot_rules_sha256"):
            self._validate()

    def test_09_wrong_matched_protocol_sha_rejected(self):
        self.supplied["matched_protocol_sha256"] = "9" * 64
        with self.assertRaisesRegex(RuntimeError, "matched_protocol_sha256"):
            self._validate()

    def test_10_wrong_comparison_class_rejected(self):
        self.auth["comparison_class"] = "PREREGISTERED_RANDOMIZED_PAIRED"
        self._write_auth()
        with self.assertRaisesRegex(RuntimeError, "comparison_class"):
            self._validate()

    def test_synthetic_exact_case_set_and_order_accepted(self):
        case_ids = [f"case-{number:02d}" for number in range(40)]
        fingerprint = runner.case_order_fingerprint(case_ids)
        self.assertTrue(runner.verify_case_order(case_ids, 40, fingerprint))

    def test_11_wrong_case_set_rejected(self):
        case_ids = [f"case-{number:02d}" for number in range(40)]
        case_ids[-1] = "different-case"
        self.assertFalse(runner.verify_case_order(
            case_ids, 40, runner.case_order_fingerprint([f"case-{number:02d}" for number in range(40)])
        ))

    def test_12_wrong_case_order_rejected(self):
        case_ids = [f"case-{number:02d}" for number in range(40)]
        case_ids[0], case_ids[1] = case_ids[1], case_ids[0]
        self.assertFalse(runner.verify_case_order(
            case_ids, 40, runner.case_order_fingerprint([f"case-{number:02d}" for number in range(40)])
        ))

    def test_13_duplicate_authorization_rejected(self):
        run = self.root / "runs" / "prior-evaluation"
        run.mkdir(parents=True)
        (run / "attempts.jsonl").write_text(json.dumps({
            "authorization_id": self.auth_id, "attempt_id": "another-attempt"
        }) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "duplicate authorization"):
            self._validate()

    def test_14_duplicate_attempt_rejected(self):
        run = self.root / "runs" / "prior-evaluation"
        run.mkdir(parents=True)
        (run / "attempts.jsonl").write_text(json.dumps({
            "authorization_id": "another-auth", "attempt_id": self.attempt_id
        }) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "duplicate authorization"):
            self._validate()

    def test_15_output_collision_rejected(self):
        (self.root / "runs" / self.pins["evaluation_id"]).mkdir(parents=True)
        with self.assertRaisesRegex(RuntimeError, "namespace collision"):
            self._validate()

    def test_16_missing_authorization_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "authorization file is missing"):
            runner.validate_authorization(
                self.root / "missing.json", self.pins["evaluation_id"], self.auth_id,
                self.attempt_id, self.supplied, run_root=self.root / "runs", frozen=self.pins,
            )

    def test_17_unissued_authorization_rejected(self):
        self.auth["status"] = "DISABLED_NOT_ISSUED"
        self._write_auth()
        with self.assertRaisesRegex(RuntimeError, "authorization status mismatch"):
            self._validate()

    def test_18_randomized_preregistration_is_not_required(self):
        auth, _ = self._validate()
        self.assertEqual(auth["comparison_class"], "POST_HOC_MATCHED_FROZEN_BASELINE")
        self.assertNotIn("preregistered_randomized_comparison", auth)

    def test_consumed_authorization_rejected(self):
        self.auth["consumed"] = True
        self._write_auth()
        with self.assertRaisesRegex(RuntimeError, "consumed"):
            self._validate()

    def test_invalid_frozen_identity_rejected_before_authorization(self):
        self.pins["all_frozen_hashes_match"] = False
        with self.assertRaisesRegex(RuntimeError, "frozen artifact"):
            self._validate()


if __name__ == "__main__":
    unittest.main()
