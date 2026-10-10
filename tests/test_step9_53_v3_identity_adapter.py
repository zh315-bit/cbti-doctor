"""Synthetic identity tests; no benchmark, case execution, aggregation, or adjudication."""
from __future__ import annotations

import inspect
import unittest

from scripts import run_step9_53_v3_identity_adapter as adapter

V1 = "e5e4841b51ecc6bced0f342a261a356756d07b39764670d774b910b86b8625a7"
V2 = "b9e891e7cd077dd5b3c6fa72b71faad978a24226c2b5e89e0b06aabde93b51d6"
V3 = adapter.V3_AGENT_SHA256
BASELINE = adapter.BASELINE_AGENT_SHA256


def v2_contract():
    return {
        "artifact_type": "TREATMENT_V2_IDENTITY_CONTRACT_NOT_AUTHORIZATION",
        "status": "FROZEN_IDENTITY_CONTRACT_NOT_AUTHORIZATION",
        "evaluation_id": "synthetic-v2-contract-test-01", "authorization_id": None, "attempt_id": None,
        "treatment_agent_sha256": V2, "baseline_agent_sha256": BASELINE,
        "treatment_freeze_path": "evaluation/v1_2_3/step9_42_treatment_v2_freeze.json",
        "treatment_freeze_sha256": "a" * 64, "benchmark_sha256": "b" * 64,
        "benchmark_manifest_sha256": "c" * 64, "harness_sha256": "d" * 64,
        "scoring_sha256": "e" * 64, "scoring_rubric_sha256": "f" * 64,
        "metric_registry_sha256": "1" * 64, "one_shot_rules_sha256": "2" * 64,
        "matched_protocol_sha256": "3" * 64, "baseline_metric_lock_sha256": "4" * 64,
        "claim_policy_sha256": "5" * 64, "model_configuration_fingerprint_sha256": "6" * 64,
        "rag_configuration_fingerprint_sha256": "7" * 64, "tool_adapter_sha256": "8" * 64,
        "dependency_lock_sha256": "9" * 64, "comparison_class": "POST_HOC_MATCHED_FROZEN_BASELINE",
        "case_count": 40, "case_order_fingerprint_sha256": "a" * 64,
        "benchmark_path": "evaluation/benchmarks/benchmark_v4_cases.yaml",
        "max_runner_turns": 6, "agent_loop_max_steps": 4, "fresh_session_per_case": True,
    }


def v3_contract():
    return {"artifact_type": "TREATMENT_V3_IDENTITY_CONTRACT_NOT_AUTHORIZATION",
            "status": "FROZEN_IDENTITY_CONTRACT_NOT_AUTHORIZATION", "authorization_id": None,
            "attempt_id": None, "evaluation_id": adapter.EVALUATION_ID,
            "treatment_agent_sha256": V3, "baseline_agent_sha256": BASELINE}


class V3IdentityAdapterTests(unittest.TestCase):
    def test_v2_identity_accepts_v2_candidate(self):
        adapter.validate_candidate_identity(
            "TREATMENT_V2", v2_contract(),
            "evaluation/v1_2_3/step9_43a_treatment_v2_identity_contract.json", V2)

    def test_v3_identity_accepts_v3_candidate(self):
        adapter.validate_candidate_identity("TREATMENT_V3", v3_contract(),
                                            adapter.V3_CONTRACT_PATH, V3)

    def test_v2_agent_with_v3_identity_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            adapter.validate_candidate_identity("TREATMENT_V3", v3_contract(),
                                                adapter.V3_CONTRACT_PATH, V2)

    def test_v3_agent_with_v2_identity_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            adapter.validate_candidate_identity(
                "TREATMENT_V2", v2_contract(),
                "evaluation/v1_2_3/step9_43a_treatment_v2_identity_contract.json", V3)

    def test_baseline_with_v3_identity_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "baseline"):
            adapter.validate_candidate_identity("TREATMENT_V3", v3_contract(),
                                                adapter.V3_CONTRACT_PATH, BASELINE)

    def test_v1_agent_with_v3_identity_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            adapter.validate_candidate_identity("TREATMENT_V3", v3_contract(),
                                                adapter.V3_CONTRACT_PATH, V1)

    def test_runner_delegates_without_rewriting_trace_fields(self):
        source = inspect.getsource(adapter.run)
        self.assertIn("parent.run(", source)
        self.assertNotIn("answer_authorization_mode", source)
        self.assertNotIn("state_history", source)
        self.assertNotIn("final_state", source)

    def test_no_aggregate_or_adjudication_entrypoint_is_imported(self):
        source = inspect.getsource(adapter)
        self.assertNotIn("aggregate_step", source)
        self.assertNotIn("adjudicat", source.lower())
        self.assertNotIn("aggregate_records", source)


if __name__ == "__main__":
    unittest.main()
