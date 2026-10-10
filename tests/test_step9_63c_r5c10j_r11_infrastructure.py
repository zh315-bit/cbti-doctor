"""Offline r11 infrastructure tests; all mutable state lives in a temp root."""
from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import build_step9_63c_r11_runner_freeze as builder
from scripts import preflight_step9_63c_r11_mac_local as producer
from scripts import run_step9_63_v3_formal_execution as formal
from scripts.v3_runner_identity import resolve_current_freeze

SOURCE = Path(__file__).resolve().parents[1]
HEX = "a" * 64
AUTH_ID = "auth-synthetic-r11-001"
ATTEMPT_ID = "attempt-synthetic-r11-001"
EVALUATION_ID = "synthetic-r11-evaluation"
PREFLIGHT_ID = "preflight-step9_63c_r5-r11-" + "b" * 32
IDENTITY_KEYS = (
    "treatment_agent_sha256", "benchmark_sha256", "harness_sha256",
    "scoring_sha256", "scoring_rubric_sha256", "metric_registry_sha256",
    "one_shot_rules_sha256", "matched_protocol_sha256",
    "model_configuration_fingerprint_sha256", "tool_adapter_sha256",
    "rag_configuration_fingerprint_sha256", "case_set_fingerprint_sha256",
    "case_order_fingerprint_sha256",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@contextmanager
def synthetic_root():
    with tempfile.TemporaryDirectory(prefix="r11-infra-") as directory:
        root = Path(directory)
        paths = set(builder.MEMBER_PATHS) - {builder.IDENTITY_CONFIG_PATH}
        paths.add(builder.PARENT_PATH)
        for relpath in paths:
            target = root / relpath
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE / relpath, target)
        pointer = root / builder.IDENTITY_CONFIG_PATH
        pointer.write_text(json.dumps({
            "artifact_type": "V3_CURRENT_RUNNER_IDENTITY_POINTER",
            "status": "FROZEN_IDENTITY_POINTER_NOT_AUTHORIZATION",
            "runner_freeze_revision": "r11",
            "runner_freeze_path": builder.EXPECTED_FREEZE_PATH,
            "execution_permission": False,
        }, sort_keys=True) + "\n", encoding="utf-8")
        yield root


def synthetic_authorization(freeze_sha: str) -> dict:
    auth = {
        "authorization_id": AUTH_ID, "attempt_id": ATTEMPT_ID,
        "evaluation_id": EVALUATION_ID, "issued_at_utc": (
            datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        "runner_freeze_revision": "r11",
        "runner_freeze_path": builder.EXPECTED_FREEZE_PATH,
        "runner_freeze_sha256": freeze_sha,
        "execution_namespace": {"namespace_id": "synthetic-r11-namespace"},
        "case_count": 40,
        "task_distribution": formal.EXPECTED_DISTRIBUTION.copy(),
    }
    auth.update({key: HEX for key in IDENTITY_KEYS})
    return auth


def synthetic_connectivity() -> dict:
    return {**{key: "PASS" for key in (
        "SYSTEM_DNS_STATUS", "PYTHON_GETADDRINFO_STATUS", "DEFAULT_DIG_STATUS",
        "GOOGLE_DNS_STATUS", "CLOUDFLARE_DNS_STATUS", "TCP_CONNECTION",
        "TLS_CONNECTION")}, "TLS_CERTIFICATE_PRESENT": True,
        "TLS_CERTIFICATE_VERIFIED": True}


class R11InfrastructureTests(unittest.TestCase):
    def make_frozen_root(self, root: Path) -> tuple[dict, str]:
        candidate = builder.assemble_candidate(root, created_at_utc="2026-10-08T00:00:00+00:00")
        freeze_sha = builder.persist_candidate(candidate, root)
        resolved, _, _ = resolve_current_freeze(root)
        self.assertEqual(resolved, candidate)
        return candidate, freeze_sha

    def make_registry(self, root: Path, freeze_sha: str) -> tuple[Path, str]:
        path = root / "evaluation/v1_2_3/step9_63c_r11_preflight_invocations.jsonl"
        producer_sha = digest(root / producer.PRODUCER_PATH)
        producer.ensure_registry_initialized(
            registry_path=path, freeze_path=builder.EXPECTED_FREEZE_PATH,
            freeze_sha256=freeze_sha, producer_sha256=producer_sha, root=root)
        return path, producer_sha

    def make_evidence(self, root: Path, freeze_sha: str) -> tuple[dict, Path, dict, Path, str, Path, str]:
        registry, producer_sha = self.make_registry(root, freeze_sha)
        auth = synthetic_authorization(freeze_sha)
        auth_file = root / "synthetic_authorization.json"
        auth_file.write_text(json.dumps(auth), encoding="utf-8")
        preflight_id, target, prefix_len, prefix_sha = producer.claim_invocation(
            registry_path=registry, authorization=auth,
            freeze_path=builder.EXPECTED_FREEZE_PATH,
            freeze_sha256=freeze_sha, producer_sha256=producer_sha,
            preflight_id=PREFLIGHT_ID, artifact_dir=root / "evaluation/v1_2_3")
        payload = producer.build_preflight_payload(
            authorization=auth, authorization_sha256=digest(auth_file),
            freeze_sha256=freeze_sha, producer_sha256=producer_sha,
            preflight_id=preflight_id, target=target,
            prefix_length=prefix_len, prefix_sha256=prefix_sha,
            connectivity=synthetic_connectivity(), runtime={}, root=root)
        artifact_sha = producer.write_artifact(target, payload)
        producer.append_terminal_event(
            registry_path=registry, freeze_path=builder.EXPECTED_FREEZE_PATH,
            freeze_sha256=freeze_sha, producer_sha256=producer_sha,
            preflight_id=preflight_id, target=target, artifact_sha256=artifact_sha,
            root=root)
        return auth, auth_file, payload, target, artifact_sha, registry, producer_sha

    def validate(self, root: Path, auth: dict, auth_file: Path, payload: dict,
                 target: Path, artifact_sha: str, freeze_sha: str) -> None:
        with patch.object(formal, "ROOT", root):
            formal.validate_preflight_evidence(
                authorization=auth, authorization_file=auth_file,
                preflight=payload, preflight_file=target,
                preflight_id=PREFLIGHT_ID, preflight_sha256=artifact_sha,
                freeze_sha256=freeze_sha)

    def test_synthetic_r11_freeze_exact_inventory_and_r10_preserved(self):
        with synthetic_root() as root:
            parent_before = digest(root / builder.PARENT_PATH)
            candidate, _ = self.make_frozen_root(root)
            self.assertEqual(len(candidate["members"]), 20)
            self.assertEqual(parent_before, builder.PARENT_SHA256)
            self.assertEqual(digest(root / builder.PARENT_PATH), parent_before)
            self.assertEqual(candidate["preflight_producer_path"], producer.PRODUCER_PATH)
            self.assertNotEqual(candidate["formal_entry_runner_sha256"],
                                next(m["sha256"] for m in json.loads(
                                    (root / builder.PARENT_PATH).read_text())["members"]
                                     if m["path"] == "scripts/run_step9_63_v3_formal_execution.py"))

    def test_r11_pointer_missing_corrupt_and_r10_fallback_forbidden(self):
        with synthetic_root() as root:
            pointer = root / builder.IDENTITY_CONFIG_PATH
            pointer.write_text(pointer.read_text().replace('"r11"', '"r10"'))
            with self.assertRaises(RuntimeError):
                builder.assemble_candidate(root)
            pointer.unlink()
            with self.assertRaises(RuntimeError):
                resolve_current_freeze(root)

    def test_member_drift_and_corrupt_freeze_fail_closed(self):
        with synthetic_root() as root:
            path = root / "scripts/authorization_lifecycle.py"
            path.write_bytes(path.read_bytes() + b"\n# unexpected drift\n")
            with self.assertRaisesRegex(RuntimeError, "unapproved"):
                builder.assemble_candidate(root)
        with synthetic_root() as root:
            _, freeze_sha = self.make_frozen_root(root)
            auth, auth_file, payload, target, artifact_sha, _, _ = self.make_evidence(root, freeze_sha)
            freeze = root / builder.EXPECTED_FREEZE_PATH
            freeze.write_bytes(freeze.read_bytes() + b" ")
            with self.assertRaises(RuntimeError):
                self.validate(root, auth, auth_file, payload, target, artifact_sha, freeze_sha)

    def test_registry_claim_persist_and_consumer_acceptance(self):
        with synthetic_root() as root:
            _, freeze_sha = self.make_frozen_root(root)
            auth, auth_file, payload, target, sha, registry, _ = self.make_evidence(root, freeze_sha)
            self.validate(root, auth, auth_file, payload, target, sha, freeze_sha)
            self.assertEqual(len(producer.parse_registry(registry.read_bytes(),
                freeze_path=builder.EXPECTED_FREEZE_PATH, freeze_sha256=freeze_sha,
                producer_sha256=digest(root / producer.PRODUCER_PATH), root=root)["claims"]), 1)

    def test_claim_is_durable_and_failed_id_cannot_be_reused(self):
        with synthetic_root() as root:
            _, freeze_sha = self.make_frozen_root(root)
            registry, producer_sha = self.make_registry(root, freeze_sha)
            auth = synthetic_authorization(freeze_sha)
            _, target, _, _ = producer.claim_invocation(
                registry_path=registry, authorization=auth,
                freeze_path=builder.EXPECTED_FREEZE_PATH, freeze_sha256=freeze_sha,
                producer_sha256=producer_sha, preflight_id=PREFLIGHT_ID,
                artifact_dir=root / "evaluation/v1_2_3")
            self.assertFalse(target.exists())
            with self.assertRaises(RuntimeError):
                producer.claim_invocation(
                    registry_path=registry, authorization=auth,
                    freeze_path=builder.EXPECTED_FREEZE_PATH,
                    freeze_sha256=freeze_sha, producer_sha256=producer_sha,
                    preflight_id=PREFLIGHT_ID,
                    artifact_dir=root / "evaluation/v1_2_3")

    def test_concurrent_duplicate_claim_has_exactly_one_winner(self):
        with synthetic_root() as root:
            _, freeze_sha = self.make_frozen_root(root)
            registry, producer_sha = self.make_registry(root, freeze_sha)
            auth = synthetic_authorization(freeze_sha)

            def claim() -> bool:
                try:
                    producer.claim_invocation(
                        registry_path=registry, authorization=auth,
                        freeze_path=builder.EXPECTED_FREEZE_PATH,
                        freeze_sha256=freeze_sha, producer_sha256=producer_sha,
                        preflight_id=PREFLIGHT_ID,
                        artifact_dir=root / "evaluation/v1_2_3")
                    return True
                except RuntimeError:
                    return False

            with ThreadPoolExecutor(max_workers=2) as pool:
                outcomes = list(pool.map(lambda _: claim(), range(2)))
            self.assertEqual(outcomes.count(True), 1)
            self.assertEqual(outcomes.count(False), 1)
            parsed = producer.parse_registry(registry.read_bytes(),
                freeze_path=builder.EXPECTED_FREEZE_PATH,
                freeze_sha256=freeze_sha, producer_sha256=producer_sha, root=root)
            self.assertEqual(list(parsed["claims"]), [PREFLIGHT_ID])

    def test_missing_persisted_event_is_not_accepted(self):
        with synthetic_root() as root:
            _, freeze_sha = self.make_frozen_root(root)
            auth, auth_file, payload, target, sha, registry, _ = self.make_evidence(root, freeze_sha)
            registry.write_bytes(b"".join(registry.read_bytes().splitlines(keepends=True)[:2]))
            with self.assertRaises(RuntimeError):
                self.validate(root, auth, auth_file, payload, target, sha, freeze_sha)

    def test_failed_claim_is_terminal_without_artifact(self):
        with synthetic_root() as root:
            _, freeze_sha = self.make_frozen_root(root)
            registry, producer_sha = self.make_registry(root, freeze_sha)
            auth = synthetic_authorization(freeze_sha)
            _, target, _, _ = producer.claim_invocation(
                registry_path=registry, authorization=auth,
                freeze_path=builder.EXPECTED_FREEZE_PATH,
                freeze_sha256=freeze_sha, producer_sha256=producer_sha,
                preflight_id=PREFLIGHT_ID,
                artifact_dir=root / "evaluation/v1_2_3")
            producer.append_terminal_event(
                registry_path=registry, freeze_path=builder.EXPECTED_FREEZE_PATH,
                freeze_sha256=freeze_sha, producer_sha256=producer_sha,
                preflight_id=PREFLIGHT_ID, target=target,
                failure_stage="SYNTHETIC_FAILURE", root=root)
            parsed = producer.parse_registry(registry.read_bytes(),
                freeze_path=builder.EXPECTED_FREEZE_PATH,
                freeze_sha256=freeze_sha, producer_sha256=producer_sha, root=root)
            self.assertIn(PREFLIGHT_ID, parsed["failed"])
            with self.assertRaises(RuntimeError):
                producer.claim_invocation(
                    registry_path=registry, authorization=auth,
                    freeze_path=builder.EXPECTED_FREEZE_PATH,
                    freeze_sha256=freeze_sha, producer_sha256=producer_sha,
                    preflight_id=PREFLIGHT_ID,
                    artifact_dir=root / "evaluation/v1_2_3")

    def test_duplicate_persisted_event_is_fail_closed(self):
        with synthetic_root() as root:
            _, freeze_sha = self.make_frozen_root(root)
            auth, auth_file, payload, target, sha, registry, _ = self.make_evidence(root, freeze_sha)
            persisted_line = registry.read_bytes().splitlines(keepends=True)[2]
            registry.write_bytes(registry.read_bytes() + persisted_line)
            with self.assertRaises(RuntimeError):
                self.validate(root, auth, auth_file, payload, target, sha, freeze_sha)

    def test_registry_appledouble_unrelated_binary_and_corruption(self):
        with synthetic_root() as root:
            _, freeze_sha = self.make_frozen_root(root)
            registry, producer_sha = self.make_registry(root, freeze_sha)
            (registry.parent / ("._" + registry.name)).write_bytes(b"\xff\x00")
            (registry.parent / "unrelated.bin").write_bytes(b"\xff\x00")
            producer.parse_registry(registry.read_bytes(),
                freeze_path=builder.EXPECTED_FREEZE_PATH,
                freeze_sha256=freeze_sha, producer_sha256=producer_sha, root=root)
            for bad in (b"\xff\n", b"not json\n", b"{}\n"):
                with self.assertRaises(RuntimeError):
                    producer.parse_registry(registry.read_bytes() + bad,
                        freeze_path=builder.EXPECTED_FREEZE_PATH,
                        freeze_sha256=freeze_sha, producer_sha256=producer_sha, root=root)

    def test_missing_duplicate_and_tampered_claim_rejected(self):
        with synthetic_root() as root:
            _, freeze_sha = self.make_frozen_root(root)
            auth, auth_file, payload, target, sha, registry, producer_sha = self.make_evidence(root, freeze_sha)
            valid = registry.read_bytes()
            claim_line = valid.splitlines(keepends=True)[1]
            for forged in (valid + claim_line, valid.replace(producer_sha.encode(), b"0" * 64),
                           valid[:-1] + b"x\n"):
                registry.write_bytes(forged)
                with self.assertRaises(RuntimeError):
                    self.validate(root, auth, auth_file, payload, target, sha, freeze_sha)
            registry.write_bytes(valid)
            for key, value in (("preflight_id", "wrong"),
                               ("runner_freeze_revision", "r10"),
                               ("case_order_fingerprint_sha256", "0" * 64),
                               ("preflight_script_sha256", "0" * 64)):
                bad = copy.deepcopy(payload)
                bad[key] = value
                with self.assertRaises(RuntimeError):
                    self.validate(root, auth, auth_file, bad, target, sha, freeze_sha)

    def test_missing_claim_artifact_sha_and_r10_authorization_rejected(self):
        with synthetic_root() as root:
            _, freeze_sha = self.make_frozen_root(root)
            auth, auth_file, payload, target, sha, registry, producer_sha = self.make_evidence(root, freeze_sha)
            registry.write_bytes(registry.read_bytes().splitlines(keepends=True)[0])
            with self.assertRaises(RuntimeError):
                self.validate(root, auth, auth_file, payload, target, sha, freeze_sha)
            with self.assertRaises(RuntimeError):
                self.validate(root, auth, auth_file, payload, target, "0" * 64, freeze_sha)
            old = dict(auth, runner_freeze_revision="r10")
            with self.assertRaises(RuntimeError):
                self.validate(root, old, auth_file, payload, target, sha, freeze_sha)


if __name__ == "__main__":
    unittest.main()
