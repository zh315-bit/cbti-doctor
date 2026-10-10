from __future__ import annotations

import hashlib
import json
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import preflight_step9_63c_r5c7_mac_local as producer
from scripts import run_step9_63_v3_formal_execution as consumer


TEST_PREFLIGHT_ID = "preflight-step9_63c_r5-r5c8b-" + "a" * 32
NETWORK_PASS = {
    "SYSTEM_DNS_STATUS": "PASS",
    "PYTHON_GETADDRINFO_STATUS": "PASS",
    "DEFAULT_DIG_STATUS": "PASS",
    "GOOGLE_DNS_STATUS": "PASS",
    "CLOUDFLARE_DNS_STATUS": "PASS",
    "TCP_CONNECTION": "PASS",
    "TLS_CONNECTION": "PASS",
    "TLS_CERTIFICATE_PRESENT": True,
    "TLS_CERTIFICATE_VERIFIED": True,
    "TLS_VERSION": "TLSv1.3",
}


class Step963cR5c8bPreflightContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = producer.ROOT
        cls.authorization_file = producer.AUTH_PATH
        cls.authorization = json.loads(cls.authorization_file.read_text(encoding="utf-8"))
        # Historical producer/consumer contract fixture. A live _snapshot()
        # requires the current runner pointer, which is intentionally absent
        # while r11 is unfrozen; it is not part of this payload-contract test.
        freeze_path = cls.root / cls.authorization["runner_freeze_path"]
        assert hashlib.sha256(cls.authorization_file.read_bytes()).hexdigest() == producer.AUTH_SHA256
        assert hashlib.sha256(freeze_path.read_bytes()).hexdigest() == producer.EXPECTED_RUNNER_SHA256
        assert cls.authorization["runner_freeze_revision"] == "r10"
        assert cls.authorization["case_count"] == 40
        cls.before = {
            "runner_freeze_revision": "r10",
            "runner_freeze_sha256": producer.EXPECTED_RUNNER_SHA256,
            "authorization_sha256": producer.AUTH_SHA256,
            "evaluation_id": cls.authorization["evaluation_id"],
            "frozen_evaluation_identity_sha256": cls.authorization["frozen_evaluation_identity_sha256"],
            "case_count": 40,
            "case_order_fingerprint_sha256": cls.authorization["case_order_fingerprint_sha256"],
            "task_distribution": cls.authorization["task_distribution"],
            "historical_pin_count": 55,
            "step9_58_provenance_gap": "PRESENT_AND_DOCUMENTED",
            "identity_bindings": {key: cls.authorization[key] for key in (
                "treatment_agent_sha256", "benchmark_sha256", "harness_sha256",
                "scoring_sha256", "scoring_rubric_sha256", "metric_registry_sha256",
                "one_shot_rules_sha256", "matched_protocol_sha256",
                "model_configuration_fingerprint_sha256", "tool_adapter_sha256",
                "rag_configuration_fingerprint_sha256", "case_set_fingerprint_sha256",
                "case_order_fingerprint_sha256")},
        }
        cls.runtime = {
            "PROJECT_ROOT_MATCH": True,
            "PROJECT_VENV_MATCH": True,
            "DEEPSEEK_API_KEY_PRESENT": True,
            "DEEPSEEK_BASE_URL_HOST": "api.deepseek.com",
            "DEEPSEEK_MODEL": "deepseek-flash",
            "python_executable": str(cls.root / ".venv/bin/python"),
            "project_root": str(cls.root),
        }

    def make_fixture(self, *, network=None, preflight_id=TEST_PREFLIGHT_ID):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        temp_root = Path(tmp.name)
        with patch.object(producer, "ROOT", temp_root):
            payload = producer.build_preflight_payload(
                preflight_id, self.before, self.runtime,
                dict(NETWORK_PASS if network is None else network),
                hashlib.sha256(Path(producer.__file__).read_bytes()).hexdigest(),
            )
            target = producer.preflight_path(preflight_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(producer.serialize_payload(payload))
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        return temp_root, payload, target, digest

    def validate_fixture(self, payload, target, digest, *, preflight_id=None):
        with patch.object(consumer, "ROOT", target.parents[2]):
            consumer.validate_preflight_evidence(
                authorization=self.authorization,
                authorization_file=self.authorization_file,
                preflight=payload,
                preflight_file=target,
                preflight_id=preflight_id or payload["PREFLIGHT_ID"],
                preflight_sha256=digest,
                freeze_sha256=self.before["runner_freeze_sha256"],
            )

    def test_01_producer_generated_fixture_passes_frozen_validator(self):
        _, payload, target, digest = self.make_fixture()
        self.validate_fixture(payload, target, digest)

    def test_02_generated_preflight_id_matches_frozen_format(self):
        value = producer.new_preflight_id()
        _, payload, target, digest = self.make_fixture(preflight_id=value)
        self.validate_fixture(payload, target, digest)

    def test_03_authorization_id_binding_exact_match(self):
        _, payload, target, digest = self.make_fixture()
        self.assertEqual(payload["AUTHORIZATION_ID"], self.authorization["authorization_id"])
        self.assertEqual(payload["authorization_id"], payload["AUTHORIZATION_ID"])
        self.validate_fixture(payload, target, digest)

    def test_04_attempt_id_binding_exact_match(self):
        _, payload, target, digest = self.make_fixture()
        self.assertEqual(payload["ATTEMPT_ID"], self.authorization["attempt_id"])
        self.assertEqual(payload["attempt_id"], payload["ATTEMPT_ID"])
        self.validate_fixture(payload, target, digest)

    def test_05_namespace_id_binding_exact_match(self):
        _, payload, target, digest = self.make_fixture()
        self.assertEqual(payload["NAMESPACE_ID"],
                         self.authorization["execution_namespace"]["namespace_id"])
        self.validate_fixture(payload, target, digest)

    def test_06_runner_revision_and_hash_binding(self):
        _, payload, target, digest = self.make_fixture()
        self.assertEqual(payload["RUNNER_FREEZE_REVISION"], "r10")
        self.assertEqual(payload["RUNNER_AGGREGATE_SHA256"],
                         self.authorization["runner_freeze_sha256"])
        self.validate_fixture(payload, target, digest)

    def test_07_v3_agent_sha_binding(self):
        _, payload, target, digest = self.make_fixture()
        self.assertEqual(payload["V3_AGENT_SHA256"],
                         self.authorization["treatment_agent_sha256"])
        self.validate_fixture(payload, target, digest)

    def test_08_evaluation_identity_bindings_match_authorization(self):
        _, payload, target, digest = self.make_fixture()
        bindings = payload["identity_bindings"]
        for key in ("benchmark_sha256", "harness_sha256", "scoring_sha256",
                    "metric_registry_sha256", "one_shot_rules_sha256",
                    "matched_protocol_sha256", "treatment_agent_sha256",
                    "case_set_fingerprint_sha256", "case_order_fingerprint_sha256"):
            with self.subTest(key=key):
                self.assertEqual(bindings[key], self.authorization[key])
        self.validate_fixture(payload, target, digest)

    def test_09_success_connectivity_derives_dns_ready(self):
        self.assertTrue(producer.derive_connectivity_readiness(NETWORK_PASS)["dns_ready"])

    def test_10_success_connectivity_derives_tcp_ready(self):
        self.assertTrue(producer.derive_connectivity_readiness(NETWORK_PASS)["tcp_ready"])

    def test_11_success_connectivity_derives_tls_ready(self):
        self.assertTrue(producer.derive_connectivity_readiness(NETWORK_PASS)["tls_ready"])

    def test_12_frozen_status_field_is_accepted(self):
        _, payload, target, digest = self.make_fixture()
        self.assertEqual(payload["STEP9_63C_R5_STATUS"],
                         "PASS_R10_MAC_LOCAL_FINAL_NON_CONSUMING_PRECLEARANCE")
        self.assertEqual(payload["status"], "PASS_NON_CONSUMING_PREFLIGHT")
        self.validate_fixture(payload, target, digest)

    def test_13_ready_field_is_accepted(self):
        _, payload, target, digest = self.make_fixture()
        self.assertIs(payload["READY_FOR_SINGLE_ATOMIC_FORMAL_EXECUTION"], True)
        self.validate_fixture(payload, target, digest)

    def test_14_authorization_manifest_sha_binding_is_accepted(self):
        _, payload, target, digest = self.make_fixture()
        self.assertEqual(payload["AUTHORIZATION_MANIFEST_SHA256"],
                         hashlib.sha256(self.authorization_file.read_bytes()).hexdigest())
        self.validate_fixture(payload, target, digest)

    def test_15_wrong_preflight_id_is_rejected(self):
        _, payload, target, digest = self.make_fixture()
        with self.assertRaisesRegex(RuntimeError, "invalid preflight instance identity"):
            self.validate_fixture(payload, target, digest,
                                  preflight_id="preflight-step9_63c-r10-" + "b" * 32)

    def test_16_wrong_authorization_id_is_rejected(self):
        _, payload, target, digest = self.make_fixture()
        payload["AUTHORIZATION_ID"] = "other-auth"
        with self.assertRaisesRegex(RuntimeError, "identity or safety invariant"):
            self.validate_fixture(payload, target, digest)

    def test_17_wrong_attempt_id_is_rejected(self):
        _, payload, target, digest = self.make_fixture()
        payload["ATTEMPT_ID"] = "other-attempt"
        with self.assertRaisesRegex(RuntimeError, "identity or safety invariant"):
            self.validate_fixture(payload, target, digest)

    def test_18_wrong_namespace_id_is_rejected(self):
        _, payload, target, digest = self.make_fixture()
        payload["NAMESPACE_ID"] = "other-namespace"
        with self.assertRaisesRegex(RuntimeError, "identity or safety invariant"):
            self.validate_fixture(payload, target, digest)

    def test_19_wrong_runner_binding_is_rejected(self):
        _, payload, target, digest = self.make_fixture()
        payload["RUNNER_AGGREGATE_SHA256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "identity or safety invariant"):
            self.validate_fixture(payload, target, digest)

    def test_20_wrong_agent_binding_is_rejected(self):
        _, payload, target, digest = self.make_fixture()
        payload["V3_AGENT_SHA256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "identity or safety invariant"):
            self.validate_fixture(payload, target, digest)

    def test_21_wrong_authorization_manifest_sha_is_rejected(self):
        _, payload, target, digest = self.make_fixture()
        payload["AUTHORIZATION_MANIFEST_SHA256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "identity or safety invariant"):
            self.validate_fixture(payload, target, digest)

    def test_22_false_dns_tcp_or_tls_evidence_is_rejected(self):
        for key in ("SYSTEM_DNS_STATUS", "TCP_CONNECTION", "TLS_CONNECTION"):
            with self.subTest(key=key):
                network = dict(NETWORK_PASS)
                network[key] = "FAIL"
                _, payload, target, digest = self.make_fixture(network=network)
                with self.assertRaisesRegex(RuntimeError, "identity or safety invariant|connectivity evidence"):
                    self.validate_fixture(payload, target, digest)

    def test_23_false_certificate_evidence_is_rejected(self):
        network = dict(NETWORK_PASS)
        network["TLS_CERTIFICATE_VERIFIED"] = False
        _, payload, target, digest = self.make_fixture(network=network)
        with self.assertRaisesRegex(RuntimeError, "identity or safety invariant|connectivity evidence"):
            self.validate_fixture(payload, target, digest)

    def test_24_old_r5c7e_artifact_remains_rejected_and_unchanged(self):
        path = self.root / "evaluation/v1_2_3/step9_63c_r5c7e_preflight-step9_63c-r10-7decee88a4c8439fb3f30ffb68240b31_mac_local_final_preclearance.json"
        digest_before = hashlib.sha256(path.read_bytes()).hexdigest()
        old_payload = json.loads(path.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(RuntimeError, "invalid preflight instance identity"):
            consumer.validate_preflight_evidence(
                authorization=self.authorization,
                authorization_file=self.authorization_file,
                preflight=old_payload,
                preflight_file=path,
                preflight_id=old_payload["preflight_id"],
                preflight_sha256=digest_before,
                freeze_sha256=self.before["runner_freeze_sha256"],
            )
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest_before)

    def test_25_offline_fixture_build_does_not_probe_network(self):
        with (patch.object(socket, "getaddrinfo", side_effect=AssertionError("network used")) as dns,
              patch.object(socket, "create_connection", side_effect=AssertionError("network used")) as tcp,
              patch.object(subprocess, "run", side_effect=AssertionError("network used")) as command):
            payload = producer.build_preflight_payload(
                TEST_PREFLIGHT_ID, self.before, self.runtime, dict(NETWORK_PASS), "c" * 64)
        dns.assert_not_called()
        tcp.assert_not_called()
        command.assert_not_called()
        self.assertIs(payload["READY_FOR_SINGLE_ATOMIC_FORMAL_EXECUTION"], True)


if __name__ == "__main__":
    unittest.main()
