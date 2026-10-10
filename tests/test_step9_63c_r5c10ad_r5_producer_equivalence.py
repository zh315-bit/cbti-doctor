"""Step 9.63c-r5c10ad AR-2: equivalent-property rewrites of retired r8-era r5/r5b tests.

The r10-frozen ``scripts/preflight_step9_63c_r5_mac_local.py`` is now a compatibility
shim, so the historical r5/r5b tests targeted an API that no longer exists. Each test
below re-expresses one historical property against the r11 inventory members that now
own it: the r11 producer, the r11-only resolver (temporary-root synthetic r11 identity
only, never the repository pointer) and the formal consumer. Mapping:
``evaluation/v1_2_3/step9_63c_r5c10ad_r5_coverage_mapping.json``.
Offline only: no DNS, transport, HTTP, model, Agent, RAG or case execution.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import preflight_step9_63c_r11_mac_local as producer
from scripts import run_step9_63_v3_formal_execution as formal
from scripts import v3_runner_identity as identity

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "evaluation/v1_2_3"
LEGACY_ARTIFACT = EVIDENCE_DIR / "step9_63c_r5_mac_local_final_preclearance.json"
R11_ID = "preflight-step9_63c_r5-r11-" + "1" * 32
R11_SECOND_ID = "preflight-step9_63c_r5-r11-" + "2" * 32
R8_ID = "preflight-step9_63c_r5-r8-" + "1" * 32
AUTH_ID = "auth-synthetic-r5c10ad"
NETWORK = {
    "SYSTEM_DNS_STATUS": "PASS", "PYTHON_GETADDRINFO_STATUS": "PASS",
    "DEFAULT_DIG_STATUS": "PASS", "GOOGLE_DNS_STATUS": "PASS",
    "CLOUDFLARE_DNS_STATUS": "PASS", "TCP_CONNECTION": "PASS",
    "TLS_CONNECTION": "PASS", "TLS_CERTIFICATE_PRESENT": True,
    "TLS_CERTIFICATE_VERIFIED": True, "TLS_VERSION": "TLSv1.3",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence_listing() -> dict[str, int]:
    return {entry.name: entry.stat().st_size for entry in EVIDENCE_DIR.iterdir()}


def synthetic_authorization() -> dict:
    keys = ("treatment_agent_sha256", "benchmark_sha256", "harness_sha256",
            "scoring_sha256", "scoring_rubric_sha256", "metric_registry_sha256",
            "one_shot_rules_sha256", "matched_protocol_sha256",
            "model_configuration_fingerprint_sha256", "tool_adapter_sha256",
            "rag_configuration_fingerprint_sha256", "case_set_fingerprint_sha256",
            "case_order_fingerprint_sha256")
    auth = {key: f"{index:x}" * 64 for index, key in enumerate(keys, 1)}
    auth.update({"authorization_id": AUTH_ID, "attempt_id": "attempt-synthetic-r5c10ad",
                 "evaluation_id": "evaluation-synthetic-r5c10ad", "case_count": 40,
                 "task_distribution": {"KNOWLEDGE_QA": 10},
                 "execution_namespace": {"namespace_id": "namespace-synthetic-r5c10ad"}})
    return auth


def build_payload(target: Path, network: dict | None = None, root: Path | None = None) -> dict:
    return producer.build_preflight_payload(
        authorization=synthetic_authorization(), authorization_sha256="a" * 64,
        freeze_sha256="b" * 64, producer_sha256="c" * 64, preflight_id=R11_ID,
        target=target, prefix_length=1, prefix_sha256="d" * 64,
        connectivity=NETWORK if network is None else network, runtime={},
        root=target.parent if root is None else root)


def synthetic_r11_root(root: Path) -> None:
    """Temporary-root r11 pointer and 20-member freeze; never the repository pointer."""
    pointer = root / identity.IDENTITY_CONFIG_PATH
    pointer.parent.mkdir(parents=True)
    pointer.write_text(json.dumps({
        "artifact_type": "V3_CURRENT_RUNNER_IDENTITY_POINTER",
        "status": "FROZEN_IDENTITY_POINTER_NOT_AUTHORIZATION",
        "runner_freeze_revision": identity.EXPECTED_REVISION,
        "runner_freeze_path": identity.EXPECTED_FREEZE_PATH}), encoding="utf-8")
    members = []
    for index in range(20):
        member = root / "members" / f"member_{index:02d}.txt"
        member.parent.mkdir(exist_ok=True)
        member.write_text(f"synthetic member {index}\n", encoding="utf-8")
        members.append({"path": member.relative_to(root).as_posix(), "sha256": sha256(member)})
    rows = "".join(sorted(f"{m['path']}\t{m['sha256']}\n" for m in members))
    (root / identity.EXPECTED_FREEZE_PATH).write_text(json.dumps({
        "runner_freeze_revision": identity.EXPECTED_REVISION, "status": "FROZEN_NOT_AUTHORIZED",
        "identity_config_path": identity.IDENTITY_CONFIG_PATH,
        "identity_config_sha256": sha256(pointer), "members": members, "member_count": 20,
        "member_aggregate_sha256": hashlib.sha256(rows.encode()).hexdigest()}), encoding="utf-8")


class R11ProducerConnectivityEquivalence(unittest.TestCase):
    """r5 test_dns/tcp/tls_failure, test_certificate_missing/unverified."""

    def assert_incomplete(self, **changes):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "artifact.json"
            with self.assertRaisesRegex(RuntimeError, "PREFLIGHT_CONNECTIVITY_INCOMPLETE"):
                build_payload(target, {**NETWORK, **changes})

    def test_complete_connectivity_builds_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            payload = build_payload(Path(directory) / "artifact.json")
        self.assertTrue(payload["dns_ready"] and payload["tcp_ready"] and payload["tls_ready"])

    def test_dns_failure(self):
        for key in ("SYSTEM_DNS_STATUS", "PYTHON_GETADDRINFO_STATUS", "DEFAULT_DIG_STATUS",
                    "GOOGLE_DNS_STATUS", "CLOUDFLARE_DNS_STATUS"):
            with self.subTest(key=key):
                self.assert_incomplete(**{key: "FAIL"})

    def test_tcp_failure(self):
        self.assert_incomplete(TCP_CONNECTION="FAIL")

    def test_tls_failure(self):
        self.assert_incomplete(TLS_CONNECTION="FAIL")

    def test_certificate_missing(self):
        self.assert_incomplete(TLS_CERTIFICATE_PRESENT=False)

    def test_certificate_unverified(self):
        self.assert_incomplete(TLS_CERTIFICATE_VERIFIED=False)


class R11ResolverFreezeEquivalence(unittest.TestCase):
    """r5 test_r8_aggregate_hash_mismatch / test_r8_member_hash_mismatch."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        synthetic_r11_root(self.root)

    def test_exact_synthetic_freeze_resolves(self):
        freeze, _, resolved = identity.resolve_current_freeze(self.root)
        self.assertEqual(freeze["runner_freeze_revision"], "r11")
        self.assertEqual(resolved["runner_freeze_path"], identity.EXPECTED_FREEZE_PATH)

    def test_aggregate_hash_mismatch(self):
        path = self.root / identity.EXPECTED_FREEZE_PATH
        freeze = json.loads(path.read_text(encoding="utf-8"))
        freeze["member_aggregate_sha256"] = "0" * 64
        path.write_text(json.dumps(freeze), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "member aggregate mismatch"):
            identity.resolve_current_freeze(self.root)

    def test_member_hash_mismatch(self):
        (self.root / "members/member_07.txt").write_text("drifted\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "member mismatch: members/member_07.txt"):
            identity.resolve_current_freeze(self.root)


class R11ProducerFailClosedOutput(unittest.TestCase):
    """r5 test_fail_closed_output_hides_exception."""

    def test_fail_closed_output_hides_exception(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(identity, "resolve_current_freeze",
                          side_effect=RuntimeError("secret-sentinel-r5c10ad")), \
             patch.object(producer, "claim_invocation") as claim:
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                code = producer.main(["--authorization-file", str(Path(directory) / "auth.json")])
        self.assertEqual(code, 1)
        self.assertIn("FAIL_CLOSED", stream.getvalue())
        self.assertNotIn("secret-sentinel-r5c10ad", stream.getvalue())
        claim.assert_not_called()


class R11ProducerArtifactLifecycle(unittest.TestCase):
    """r5b T2-T5, T11-T14 against the r11 producer."""

    def test_T2_import_does_not_create_repository_artifacts(self):
        before = evidence_listing()
        legacy_before = sha256(LEGACY_ARTIFACT)
        registry_before = producer.REGISTRY_PATH.exists()
        for module in ("scripts.preflight_step9_63c_r11_mac_local",
                       "scripts.preflight_step9_63c_current_mac_local",
                       "scripts.preflight_step9_63c_r5_mac_local"):
            subprocess.run([sys.executable, "-c", f"import {module}"], cwd=ROOT, check=True,
                           capture_output=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(evidence_listing(), before)
        self.assertEqual(sha256(LEGACY_ARTIFACT), legacy_before)
        self.assertEqual(producer.REGISTRY_PATH.exists(), registry_before)

    def test_T3_offline_fixture_only_writes_temp(self):
        before = evidence_listing()
        with tempfile.TemporaryDirectory() as directory:
            target = producer.artifact_path(AUTH_ID, R11_ID, Path(directory))
            producer.write_artifact(target, build_payload(target))
            self.assertEqual(len(list(Path(directory).glob("*.json"))), 1)
        self.assertEqual(evidence_listing(), before)

    def test_T4_identity_grammar_and_authorization_scoped_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = producer.artifact_path(AUTH_ID, R11_ID, Path(directory))
            self.assertIn(AUTH_ID, path.name)
            self.assertIn(R11_ID, path.name)
            self.assertFalse(path.exists())
            for wrong in (R8_ID, "preflight-step9_63c-r10-" + "1" * 32, R11_ID + "0"):
                with self.subTest(wrong=wrong), self.assertRaisesRegex(RuntimeError, "INVALID_PREFLIGHT_ID"):
                    producer.artifact_path(AUTH_ID, wrong, Path(directory))

    def test_T5_second_id_has_distinct_path(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertNotEqual(producer.artifact_path(AUTH_ID, R11_ID, Path(directory)),
                                producer.artifact_path(AUTH_ID, R11_SECOND_ID, Path(directory)))

    def test_T11_duplicate_preflight_id_exclusive_create_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            target = producer.artifact_path(AUTH_ID, R11_ID, Path(directory))
            producer.write_artifact(target, build_payload(target))
            original = target.read_bytes()
            with self.assertRaisesRegex(RuntimeError, "PREFLIGHT_TARGET_EXISTS"):
                producer.write_artifact(target, {"status": "replacement"})
            self.assertEqual(target.read_bytes(), original)

    def test_T12_different_ids_do_not_collide(self):
        with tempfile.TemporaryDirectory() as directory:
            first = producer.artifact_path(AUTH_ID, R11_ID, Path(directory))
            second = producer.artifact_path(AUTH_ID, R11_SECOND_ID, Path(directory))
            first_sha = producer.write_artifact(first, build_payload(first))
            second_sha = producer.write_artifact(second, build_payload(second))
            self.assertTrue(first.exists() and second.exists())
            self.assertEqual((sha256(first), sha256(second)), (first_sha, second_sha))

    def test_T13_no_http_model_agent_rag_execution(self):
        for module in ("preflight_step9_63c_r11_mac_local.py", "preflight_step9_63c_current_mac_local.py"):
            source = (ROOT / "scripts" / module).read_text(encoding="utf-8")
            for forbidden in ("requests.get(", "requests.post(", "httpx.", "/chat/completions",
                              "/api/chat", "create_chat_model(", "adapter.run(",
                              "begin_and_commit(", "reserve_namespace(", "_case_result("):
                with self.subTest(module=module, forbidden=forbidden):
                    self.assertNotIn(forbidden, source)

    def test_T14_authorization_consumption_stays_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            auth_file = Path(directory) / "authorization.json"
            auth_file.write_text(json.dumps(synthetic_authorization()), encoding="utf-8")
            before = sha256(auth_file)
            payload = build_payload(Path(directory) / "artifact.json")
            self.assertEqual(sha256(auth_file), before)
        for key in ("AUTHORIZATION_CONSUMPTION_COUNT", "authorization_consumption_count",
                    "FORMAL_V4_CASE_EXECUTED", "formal_v4_case_executed"):
            self.assertEqual(payload[key], 0)
        for key in ("AUTHORIZATION_CONSUMED", "ATTEMPT_CREATED", "NAMESPACE_CREATED",
                    "NAMESPACE_RESERVED", "HTTP_REQUEST_SENT", "MODEL_INFERENCE_EXECUTED"):
            self.assertIs(payload[key], False)


class FormalConsumerBindingEquivalence(unittest.TestCase):
    """r5b test_old_fixed_path_cannot_be_substituted / test_wrong_explicit_sha_rejected /
    test_preissue_timestamp_rejected, with synthetic (non-shim) identities."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.artifacts = self.root / "evaluation/v1_2_3"
        self.artifacts.mkdir(parents=True)
        self.auth_file = self.root / "authorization.json"
        self.auth = {"authorization_id": AUTH_ID, "attempt_id": "attempt-synthetic-r5c10ad",
                     "runner_freeze_revision": "r8", "treatment_agent_sha256": "e" * 64,
                     "execution_namespace": {"namespace_id": "namespace-synthetic-r5c10ad"},
                     "issued_at_utc": "2026-10-06T14:56:37Z"}
        self.auth_file.write_text(json.dumps(self.auth), encoding="utf-8")

    def evidence(self) -> dict:
        return {
            "PREFLIGHT_ID": R8_ID,
            "STEP9_63C_R5_STATUS": "PASS_R8_MAC_LOCAL_FINAL_NON_CONSUMING_PRECLEARANCE",
            "EXECUTION_ENVIRONMENT": "MAC_LOCAL", "AUTHORIZATION_ID": AUTH_ID,
            "AUTHORIZATION_MANIFEST_SHA256": sha256(self.auth_file),
            "RUNNER_FREEZE_REVISION": "r8", "RUNNER_AGGREGATE_SHA256": "a" * 64,
            "R8_RUNNER_AGGREGATE_SHA256": "a" * 64, "V3_AGENT_SHA256": "e" * 64,
            "ATTEMPT_ID": self.auth["attempt_id"],
            "NAMESPACE_ID": self.auth["execution_namespace"]["namespace_id"],
            "AUTHORIZATION_CONSUMED": False, "AUTHORIZATION_CONSUMPTION_COUNT": 0,
            "ATTEMPT_CREATED": False, "NAMESPACE_CREATED": False, "NAMESPACE_RESERVED": False,
            "HTTP_REQUEST_SENT": False, "MODEL_INFERENCE_EXECUTED": False,
            "AGENT_EVALUATION_EXECUTED": False, "RAG_EVALUATION_EXECUTED": False,
            "FORMAL_V4_CASE_EXECUTED": 0, "READY_FOR_SINGLE_ATOMIC_FORMAL_EXECUTION": True,
            "timestamp_utc": "2026-10-06T15:12:51Z", **NETWORK,
        }

    def write(self, payload: dict, name: str | None = None) -> tuple[Path, str]:
        path = self.artifacts / (name or f"step9_63c_r5_{AUTH_ID}_{R8_ID}_mac_local_preclearance.json")
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path, sha256(path)

    def validate(self, payload: dict, path: Path, digest: str) -> None:
        with patch.object(formal, "ROOT", self.root):
            formal.validate_preflight_evidence(
                authorization=self.auth, authorization_file=self.auth_file, preflight=payload,
                preflight_file=path, preflight_id=R8_ID, preflight_sha256=digest,
                freeze_sha256="a" * 64)

    def test_valid_instance_scoped_evidence_is_accepted(self):
        payload = self.evidence()
        self.validate(payload, *self.write(payload))

    def test_old_fixed_path_cannot_be_substituted(self):
        payload = self.evidence()
        path, digest = self.write(payload, "step9_63c_r5_mac_local_final_preclearance.json")
        with self.assertRaisesRegex(RuntimeError, "path or SHA-256"):
            self.validate(payload, path, digest)

    def test_wrong_explicit_sha_rejected(self):
        payload = self.evidence()
        path, _ = self.write(payload)
        with self.assertRaisesRegex(RuntimeError, "path or SHA-256"):
            self.validate(payload, path, "0" * 64)

    def test_preissue_timestamp_rejected(self):
        payload = self.evidence()
        payload["timestamp_utc"] = "2026-10-06T14:00:00Z"
        with self.assertRaisesRegex(RuntimeError, "freshness"):
            self.validate(payload, *self.write(payload))


if __name__ == "__main__":
    unittest.main()
