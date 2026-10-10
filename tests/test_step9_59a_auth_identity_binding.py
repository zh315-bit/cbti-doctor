"""Offline regressions for the current authorization-validator identity binding."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import run_step9_35a_matched_treatment as parent
from scripts import run_step9_53_v3_identity_adapter as adapter
from scripts import authorization_lifecycle as lifecycle


class AuthorizationIdentityBindingTests(unittest.TestCase):
    def setUp(self):
        self.bindings = adapter._authoritative_authorization_bindings()
        self.freeze = adapter.read_json(adapter.ROOT / adapter.V3_RUNNER_FREEZE_PATH)

    def _authorization(self, *, runner_sha=None):
        pins = self.bindings
        return {
            "status": "ISSUED_NOT_EXECUTED",
            "authorization_type": "ONE_SHOT_MATCHED_TREATMENT",
            "comparison_class": parent.COMPARISON_CLASS,
            "evaluation_id": pins["evaluation_id"],
            "authorization_id": "synthetic-step9-59a-auth",
            "attempt_id": "synthetic-step9-59a-attempt",
            "treatment_agent_sha256": pins["treatment_agent_sha256"],
            "baseline_agent_sha256": pins["baseline_agent_sha256"],
            "benchmark_sha256": pins["benchmark_sha256"],
            "benchmark_manifest_sha256": pins["benchmark_manifest_sha256"],
            "harness_sha256": pins["harness_sha256"],
            "scoring_sha256": pins["scoring_sha256"],
            "metric_registry_sha256": pins["metric_registry_sha256"],
            "one_shot_rules_sha256": pins["one_shot_rules_sha256"],
            "matched_protocol_sha256": pins["matched_protocol_sha256"],
            "baseline_metric_lock_sha256": pins["baseline_metric_lock_sha256"],
            "claim_policy_sha256": pins["claim_policy_sha256"],
            "treatment_runner_sha256": runner_sha or pins["treatment_runner_sha256"],
            "production_case_path_runner_sha256": pins["production_case_path_runner_sha256"],
            "case_count": pins["case_count"],
            "case_order_fingerprint_sha256": pins["case_order_fingerprint_sha256"],
            "max_formal_attempts": 1,
            "consumed": False,
            "consumed_at_utc": None,
            "authorization_status": "ISSUED_NOT_CONSUMED",
            "authorization_consumption_count": 0,
            "authorized_by": "synthetic unit test only",
        }

    def test_parent_validator_accepts_authoritative_r7_pins(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic-authorization.json"
            path.write_text(json.dumps(self._authorization()), encoding="utf-8")
            supplied = {key: self.bindings[key] for key in (
                "treatment_agent_sha256", "benchmark_sha256", "harness_sha256",
                "scoring_sha256", "metric_registry_sha256", "one_shot_rules_sha256",
                "matched_protocol_sha256")}
            auth, pins = parent.validate_authorization(
                path, self.bindings["evaluation_id"], auth_id := "synthetic-step9-59a-auth",
                attempt_id := "synthetic-step9-59a-attempt", supplied,
                run_root=Path(temp) / "empty-output-root", frozen=self.bindings)
            self.assertEqual(auth["authorization_id"], auth_id)
            self.assertEqual(auth["attempt_id"], attempt_id)
            self.assertEqual(pins["treatment_runner_sha256"], self.freeze["runner_sha256"])

    def test_parent_validator_rejects_r4_incompatible_authorization(self):
        stale_hashes = (
            "ace3d58005a5c4ce01aeeb17ac54a437c64e4023f7c870e12964a1a5d72b0b7e",
            "5c64ad7918703e9f2364d832963f39fbcd8bd45a7519a1771515b5d62bca4c87",
        )
        for stale_hash in stale_hashes:
            with self.subTest(stale_hash=stale_hash), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "synthetic-authorization.json"
                path.write_text(json.dumps(self._authorization(runner_sha=stale_hash)), encoding="utf-8")
                supplied = {key: self.bindings[key] for key in (
                    "treatment_agent_sha256", "benchmark_sha256", "harness_sha256",
                    "scoring_sha256", "metric_registry_sha256", "one_shot_rules_sha256",
                    "matched_protocol_sha256")}
                with self.assertRaisesRegex(RuntimeError, "authorization treatment_runner_sha256 mismatch"):
                    parent.validate_authorization(
                        path, self.bindings["evaluation_id"], "synthetic-step9-59a-auth",
                        "synthetic-step9-59a-attempt", supplied,
                        run_root=Path(temp) / "empty-output-root", frozen=self.bindings)

    def test_preflight_runner_binding_mismatch_fails_closed(self):
        stale = dict(self.bindings)
        stale["treatment_runner_sha256"] = "5c64ad7918703e9f2364d832963f39fbcd8bd45a7519a1771515b5d62bca4c87"
        with self.assertRaisesRegex(RuntimeError, "differs from current r7 freeze"):
            adapter._assert_authorization_runner_binding(
                stale, self.freeze, self.freeze["runner_sha256"])

    def test_preflight_rejects_freeze_hash_not_equal_to_current_runner(self):
        with self.assertRaisesRegex(RuntimeError, "differs from current r7 freeze"):
            adapter._assert_authorization_runner_binding(
                self.bindings, self.freeze, "0" * 64)

    def test_actual_preflight_fails_closed_on_stale_validator_runner_pin(self):
        stale = dict(self.bindings)
        stale["treatment_runner_sha256"] = "5c64ad7918703e9f2364d832963f39fbcd8bd45a7519a1771515b5d62bca4c87"
        with tempfile.TemporaryDirectory() as temp, \
             mock.patch.object(adapter, "_current_evaluation_bindings", return_value=stale):
            with self.assertRaisesRegex(RuntimeError, "differs from current r7 freeze"):
                adapter.validate_frozen_v3_identity(
                    namespace_root=Path(temp) / "future", identity_root=Path(temp))

    def test_parent_validator_rejects_retired_authorization(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            ledger = temp / "authorization_lifecycle_events.jsonl"
            ledger.write_text(json.dumps({
                "event_type": lifecycle.RETIRE_EVENT,
                "authorization_id": "synthetic-step9-59a-auth",
                "final_status": lifecycle.RETIRED,
                "authorization_consumed": False,
                "authorization_consumption_count": 0,
            }) + "\n", encoding="utf-8")
            path = temp / "authorization.json"
            path.write_text(json.dumps(self._authorization()), encoding="utf-8")
            supplied = {key: self.bindings[key] for key in (
                "treatment_agent_sha256", "benchmark_sha256", "harness_sha256",
                "scoring_sha256", "metric_registry_sha256", "one_shot_rules_sha256",
                "matched_protocol_sha256")}
            with mock.patch.object(lifecycle, "EVENT_LEDGER_PATH", ledger):
                with self.assertRaisesRegex(RuntimeError, "retired"):
                    parent.validate_authorization(
                        path, self.bindings["evaluation_id"], "synthetic-step9-59a-auth",
                        "synthetic-step9-59a-attempt", supplied,
                        run_root=temp / "empty-output-root", frozen=self.bindings)

    def test_parent_run_cannot_consume_or_create_namespace_for_retired_authorization(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            ledger = temp / "authorization_lifecycle_events.jsonl"
            ledger.write_text(json.dumps({
                "event_type": lifecycle.RETIRE_EVENT,
                "authorization_id": "synthetic-step9-59a-auth",
                "final_status": lifecycle.RETIRED,
                "authorization_consumed": False,
                "authorization_consumption_count": 0,
            }) + "\n", encoding="utf-8")
            auth_path = temp / "authorization.json"
            auth_path.write_text(json.dumps(self._authorization()), encoding="utf-8")
            supplied = {key: self.bindings[key] for key in (
                "treatment_agent_sha256", "benchmark_sha256", "harness_sha256",
                "scoring_sha256", "metric_registry_sha256", "one_shot_rules_sha256",
                "matched_protocol_sha256")}
            output_root = temp / "future-output"
            with mock.patch.object(lifecycle, "EVENT_LEDGER_PATH", ledger), \
                 mock.patch.object(parent, "OUT_ROOT", output_root):
                with self.assertRaisesRegex(RuntimeError, "retired"):
                    parent.run(
                        self.bindings["evaluation_id"], "synthetic-step9-59a-auth",
                        "synthetic-step9-59a-attempt", auth_path, supplied)
            self.assertFalse(output_root.exists())


if __name__ == "__main__":
    unittest.main()
