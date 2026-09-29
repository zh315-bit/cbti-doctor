"""Synthetic-only tests for Step 9.43a identity and authorization contracts."""
from __future__ import annotations

import unittest

from scripts import run_step9_43a_treatment_v2 as adapter


V1 = "e5e4841b51ecc6bced0f342a261a356756d07b39764670d774b910b86b8625a7"
V2 = "b9e891e7cd077dd5b3c6fa72b71faad978a24226c2b5e89e0b06aabde93b51d6"
BASELINE = "4e2bffea0d7eaa9299074a960df84a1806b3ae9d4930662929abc58ca5b2ae79"


class TreatmentIdentityContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = {
            "artifact_type": "TREATMENT_V2_IDENTITY_CONTRACT_NOT_AUTHORIZATION",
            "status": "FROZEN_IDENTITY_CONTRACT_NOT_AUTHORIZATION",
            "evaluation_id": "heldout-v4-step9_43a-treatment-v2-test-01",
            "authorization_id": None,
            "attempt_id": None,
            "treatment_agent_sha256": V2,
            "baseline_agent_sha256": BASELINE,
            "treatment_freeze_path": "evaluation/v1_2_3/step9_42_treatment_v2_freeze.json",
            "treatment_freeze_sha256": "a" * 64,
            "benchmark_sha256": "c" * 64,
            "benchmark_manifest_sha256": "d" * 64,
            "harness_sha256": "f" * 64,
            "scoring_sha256": "1" * 64,
            "scoring_rubric_sha256": "2" * 64,
            "metric_registry_sha256": "3" * 64,
            "one_shot_rules_sha256": "5" * 64,
            "matched_protocol_sha256": "6" * 64,
            "baseline_metric_lock_sha256": "7" * 64,
            "claim_policy_sha256": "8" * 64,
            "model_configuration_fingerprint_sha256": "9" * 64,
            "rag_configuration_fingerprint_sha256": "a" * 64,
            "tool_adapter_sha256": "b" * 64,
            "dependency_lock_sha256": "c" * 64,
            "comparison_class": "POST_HOC_MATCHED_FROZEN_BASELINE",
            "case_count": 40,
            "case_order_fingerprint_sha256": "d" * 64,
            "benchmark_path": "evaluation/benchmarks/benchmark_v4_cases.yaml",
            "max_runner_turns": 6,
            "agent_loop_max_steps": 4,
            "fresh_session_per_case": True,
        }
        self.path = "evaluation/v1_2_3/step9_43a_treatment_v2_identity_contract.json"
        self.auth = {
            "status": "ISSUED_NOT_EXECUTED",
            "authorization_type": "ONE_SHOT_MATCHED_TREATMENT",
            "evaluation_id": self.contract["evaluation_id"],
            "authorization_id": "auth-1", "attempt_id": "attempt-1",
            "consumed": False, "consumed_at_utc": None,
            "max_formal_attempts": 1, "authorized_by": "synthetic-test",
            "identity_contract_path": self.path, "identity_contract_sha256": "e" * 64,
            "treatment_runner_sha256": "f" * 64, "treatment_runner_freeze_sha256": "0" * 64,
            "case_count": self.contract["case_count"],
        }
        for name in ("treatment_freeze_path", "treatment_freeze_sha256", "treatment_agent_sha256",
                     "comparison_class", "benchmark_sha256", "harness_sha256", "scoring_sha256",
                     "metric_registry_sha256", "one_shot_rules_sha256", "matched_protocol_sha256",
                     "case_order_fingerprint_sha256", "baseline_agent_sha256", "benchmark_path",
                     "benchmark_manifest_sha256", "scoring_rubric_sha256", "baseline_metric_lock_sha256",
                     "claim_policy_sha256", "model_configuration_fingerprint_sha256",
                     "rag_configuration_fingerprint_sha256", "tool_adapter_sha256", "dependency_lock_sha256",
                     "max_runner_turns", "agent_loop_max_steps", "fresh_session_per_case"):
            self.auth[name] = self.contract[name]
        self.supplied = {name: self.contract[name] for name in (
            "treatment_agent_sha256", "benchmark_sha256", "harness_sha256", "scoring_sha256",
            "metric_registry_sha256", "one_shot_rules_sha256", "matched_protocol_sha256")}

    def validate_auth(self):
        adapter.validate_authorization_bindings(
            self.contract, self.auth, evaluation_id=self.contract["evaluation_id"],
            authorization_id="auth-1", attempt_id="attempt-1", supplied=self.supplied,
            contract_path=self.path, contract_sha256="e" * 64, runner_sha256="f" * 64,
            runner_freeze_sha256="0" * 64)

    def test_01_v2_contract_accepts_exact_v2_agent(self):
        adapter.validate_contract_shape(self.contract, {self.path}, self.path)
        adapter.validate_agent_identity(self.contract, V2)

    def test_01a_frozen_v2_identity_preflight_passes_without_case_execution(self):
        contract_path = adapter.FREEZE_DIR / "step9_43a_treatment_v2_identity_contract.json"
        contract, freeze, runtime = adapter.load_verified_identity(contract_path)
        self.assertEqual(contract["treatment_agent_sha256"],
                         "b9e891e7cd077dd5b3c6fa72b71faad978a24226c2b5e89e0b06aabde93b51d6")
        self.assertEqual(freeze["repair_class"], "INFRASTRUCTURE_IDENTITY_COMPATIBILITY_ONLY")
        self.assertEqual(runtime["pins"]["case_count"], 40)

    def test_02_v2_contract_rejects_v1_agent(self):
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            adapter.validate_agent_identity(self.contract, V1)

    def test_03_v2_contract_rejects_baseline_agent(self):
        with self.assertRaisesRegex(RuntimeError, "does not match|baseline"):
            adapter.validate_agent_identity(self.contract, BASELINE)

    def test_04_v1_contract_accepts_v1_identity_explicitly(self):
        legacy = dict(self.contract, treatment_agent_sha256=V1,
                      artifact_type="EXPLICIT_HISTORICAL_TREATMENT_V1_IDENTITY_CONTRACT_NOT_AUTHORIZATION",
                      treatment_freeze_path="evaluation/v1_2_3/step9_33a_treatment_freeze.json")
        legacy_path = "evaluation/v1_2_3/step9_43a_treatment_v1_identity_contract.json"
        adapter.validate_contract_shape(legacy, {legacy_path}, legacy_path)
        adapter.validate_agent_identity(legacy, V1)

    def test_04a_v1_contract_rejects_v2_agent(self):
        legacy = dict(self.contract, treatment_agent_sha256=V1)
        with self.assertRaises(RuntimeError):
            adapter.validate_agent_identity(legacy, V2)

    def test_05_wrong_freeze_hash_rejected(self):
        self.contract["treatment_freeze_sha256"] = "not-a-hash"
        with self.assertRaisesRegex(RuntimeError, "hash"):
            adapter.validate_contract_shape(self.contract, {self.path}, self.path)

    def test_06_missing_freeze_reference_rejected(self):
        self.contract.pop("treatment_freeze_path")
        with self.assertRaisesRegex(RuntimeError, "missing required"):
            adapter.validate_contract_shape(self.contract, {self.path}, self.path)

    def test_07_wrong_benchmark_rejected(self):
        self.supplied["benchmark_sha256"] = "x" * 64
        with self.assertRaisesRegex(RuntimeError, "supplied benchmark_sha256"):
            self.validate_auth()

    def test_08_wrong_harness_rejected(self):
        self.supplied["harness_sha256"] = "x" * 64
        with self.assertRaisesRegex(RuntimeError, "supplied harness_sha256"):
            self.validate_auth()

    def test_09_wrong_scoring_rejected(self):
        self.supplied["scoring_sha256"] = "x" * 64
        with self.assertRaisesRegex(RuntimeError, "supplied scoring_sha256"):
            self.validate_auth()

    def test_10_wrong_metric_registry_rejected(self):
        self.supplied["metric_registry_sha256"] = "x" * 64
        with self.assertRaisesRegex(RuntimeError, "supplied metric_registry_sha256"):
            self.validate_auth()

    def test_11_wrong_one_shot_rules_rejected(self):
        self.supplied["one_shot_rules_sha256"] = "x" * 64
        with self.assertRaisesRegex(RuntimeError, "supplied one_shot_rules_sha256"):
            self.validate_auth()

    def test_12_wrong_protocol_rejected(self):
        self.supplied["matched_protocol_sha256"] = "x" * 64
        with self.assertRaisesRegex(RuntimeError, "supplied matched_protocol_sha256"):
            self.validate_auth()

    def test_13_wrong_case_order_rejected(self):
        self.auth["case_order_fingerprint_sha256"] = "x" * 64
        with self.assertRaisesRegex(RuntimeError, "case_order_fingerprint_sha256 mismatch"):
            self.validate_auth()

    def test_14_missing_authorization_rejected(self):
        self.auth["authorization_id"] = None
        with self.assertRaisesRegex(RuntimeError, "authorization_id"):
            self.validate_auth()

    def test_15_unissued_authorization_rejected(self):
        self.auth["status"] = "DISABLED_NOT_ISSUED"
        with self.assertRaisesRegex(RuntimeError, "not issued"):
            self.validate_auth()

    def test_16_duplicate_attempt_identity_not_reusable(self):
        with self.assertRaisesRegex(RuntimeError, "attempt_id"):
            adapter.validate_authorization_bindings(
                self.contract, self.auth, evaluation_id=self.contract["evaluation_id"],
                authorization_id="auth-1", attempt_id="", supplied=self.supplied,
                contract_path=self.path, contract_sha256="e" * 64, runner_sha256="f" * 64,
                runner_freeze_sha256="0" * 64)

    def test_17_output_collision_checked_by_frozen_parent_runner(self):
        from scripts.run_step9_35a_matched_treatment import validate_authorization
        self.assertTrue(callable(validate_authorization))  # Occupied namespace is exercised by the parent suite.

    def test_18_mutable_latest_alias_rejected(self):
        bad = dict(self.contract, treatment_freeze_path="latest")
        with self.assertRaisesRegex(RuntimeError, "mutable"):
            adapter.validate_contract_shape(bad, {self.path}, self.path)

    def test_19_absent_semantic_identity_rejected(self):
        bad = dict(self.contract)
        bad.pop("matched_protocol_sha256")
        with self.assertRaisesRegex(RuntimeError, "missing required"):
            adapter.validate_contract_shape(bad, {self.path}, self.path)

    def test_20_no_fallback_to_v1_when_contract_missing(self):
        with self.assertRaisesRegex(RuntimeError, "unknown"):
            adapter.validate_contract_shape(self.contract, {self.path}, "latest")

    def test_21_supplied_protocol_mismatch_rejected(self):
        self.supplied["matched_protocol_sha256"] = "f" * 64
        with self.assertRaisesRegex(RuntimeError, "supplied matched_protocol_sha256"):
            self.validate_auth()

    def test_22_wrong_freeze_reference_in_authorization_rejected(self):
        self.auth["treatment_freeze_path"] = "latest"
        with self.assertRaisesRegex(RuntimeError, "treatment_freeze_path mismatch"):
            self.validate_auth()

    def test_23_wrong_runner_identity_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "treatment_runner_sha256 mismatch"):
            adapter.validate_authorization_bindings(
                self.contract, self.auth, evaluation_id=self.contract["evaluation_id"],
                authorization_id="auth-1", attempt_id="attempt-1", supplied=self.supplied,
                contract_path=self.path, contract_sha256="e" * 64, runner_sha256="0" * 64,
                runner_freeze_sha256="0" * 64)

    def test_24_wrong_evaluation_namespace_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "evaluation_id"):
            adapter.validate_authorization_bindings(
                self.contract, self.auth, evaluation_id="other-eval", authorization_id="auth-1",
                attempt_id="attempt-1", supplied=self.supplied, contract_path=self.path,
                contract_sha256="e" * 64, runner_sha256="f" * 64, runner_freeze_sha256="0" * 64)


if __name__ == "__main__":
    unittest.main()
