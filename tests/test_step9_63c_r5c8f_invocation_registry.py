from __future__ import annotations

import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from scripts import preflight_step9_63c_r5c7_mac_local as producer


class PreflightInvocationRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        directory = self.root / "evaluation/v1_2_3"
        directory.mkdir(parents=True)
        self.registry = directory / "invocations.jsonl"
        self.genesis = json.dumps(producer.REGISTRY_GENESIS, sort_keys=True, separators=(",", ":")) + "\n"
        self.registry.write_text(self.genesis, encoding="utf-8")
        self.preflight_id = "preflight-step9_63c_r5-r5c8b-" + "a" * 32
        root_patch = patch.object(producer, "ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)

    def claim(self, preflight_id=None):
        with patch.object(producer, "new_preflight_id", return_value=preflight_id or self.preflight_id):
            return producer.claim_new_preflight_invocation(registry_path=self.registry)

    def test_fresh_invocation_with_missing_target_is_claimed(self):
        preflight_id, target = self.claim()
        self.assertEqual(preflight_id, self.preflight_id)
        self.assertFalse(target.exists())
        self.assertTrue(producer.historical_invocation_id_exists(preflight_id, registry_path=self.registry))
        self.assertTrue(self.registry.read_text().startswith(self.genesis))
        self.assertEqual(len(self.registry.read_text().splitlines()), 2)

    def test_unclaimed_fresh_id_is_not_historical(self):
        self.assertFalse(producer.historical_invocation_id_exists(self.preflight_id,
                                                                  registry_path=self.registry))

    def test_historical_invocation_id_fails_closed(self):
        self.claim()
        with self.assertRaisesRegex(RuntimeError, "HISTORICAL_INVOCATION_ID_COLLISION"):
            self.claim()

    def test_historical_id_with_missing_target_still_fails_closed(self):
        _, target = self.claim()
        self.assertFalse(target.exists())
        with self.assertRaisesRegex(RuntimeError, "HISTORICAL_INVOCATION_ID_COLLISION"):
            self.claim()
        self.assertFalse(target.exists())

    def test_existing_target_fails_closed_without_overwrite(self):
        target = producer.preflight_path(self.preflight_id)
        target.write_bytes(b"historical artifact")
        with self.assertRaisesRegex(RuntimeError, "PREFLIGHT_TARGET_EXISTS"):
            self.claim()
        self.assertEqual(target.read_bytes(), b"historical artifact")
        self.assertEqual(self.registry.read_text(), self.genesis)

    def test_failed_invocation_without_artifact_remains_claimed(self):
        _, target = self.claim()
        self.assertFalse(target.exists())
        with self.assertRaisesRegex(RuntimeError, "HISTORICAL_INVOCATION_ID_COLLISION"):
            self.claim()
        self.assertEqual(len(self.registry.read_text().splitlines()), 2)

    def test_malformed_history_fails_closed(self):
        self.registry.write_text(self.genesis + "{bad json}\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "INVOCATION_REGISTRY_INVALID"):
            self.claim()

    def test_unreadable_or_missing_history_fails_closed(self):
        self.registry.unlink()
        with self.assertRaisesRegex(RuntimeError, "INVOCATION_REGISTRY_UNREADABLE"):
            self.claim()

    def test_permission_denied_history_fails_closed(self):
        with patch.object(producer.os, "open", side_effect=PermissionError("synthetic denied")):
            with self.assertRaisesRegex(RuntimeError, "INVOCATION_REGISTRY_UNREADABLE"):
                self.claim()

    def test_duplicate_history_entries_fail_closed(self):
        self.claim()
        row = self.registry.read_text().splitlines()[-1] + "\n"
        with self.registry.open("a", encoding="utf-8") as stream:
            stream.write(row)
        with self.assertRaisesRegex(RuntimeError, "INVOCATION_REGISTRY_INVALID"):
            self.claim("preflight-step9_63c_r5-r5c8b-" + "b" * 32)

    def test_truncated_history_fails_closed(self):
        self.registry.write_text(self.genesis + '{"event_type":"PREFLIGHT_INVOCATION_CLAIMED"',
                                 encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "INVOCATION_REGISTRY_INVALID"):
            self.claim()

    def test_malformed_candidate_id_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "INVALID_PREFLIGHT_INVOCATION_ID"):
            self.claim("../unsafe")
        self.assertEqual(self.registry.read_text(), self.genesis)

    def test_registry_symlink_fails_closed(self):
        real = self.registry.with_name("real.jsonl")
        self.registry.rename(real)
        self.registry.symlink_to(real)
        with self.assertRaisesRegex(RuntimeError, "INVOCATION_REGISTRY_UNREADABLE"):
            self.claim()

    def test_claim_contains_no_secret_and_does_not_create_execution_state(self):
        secret = "sk-SYNTHETIC_NOT_REAL_KEY_012345"
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": secret}):
            _, target = self.claim()
        raw = self.registry.read_bytes()
        self.assertNotIn(secret.encode(), raw)
        self.assertNotIn(b"DEEPSEEK_API_KEY", raw)
        self.assertFalse(target.exists())
        self.assertFalse((self.root / "evaluation/v4_runs").exists())

    def test_append_failure_preserves_visible_claim(self):
        with patch.object(producer.os, "fsync", side_effect=OSError("synthetic fsync failure")):
            with self.assertRaisesRegex(OSError, "synthetic fsync failure"):
                self.claim()
        self.assertTrue(producer.historical_invocation_id_exists(self.preflight_id,
                                                                  registry_path=self.registry))

    def test_concurrent_same_id_has_exactly_one_claim(self):
        with patch.object(producer, "new_preflight_id", return_value=self.preflight_id):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(producer.claim_new_preflight_invocation,
                                       registry_path=self.registry) for _ in range(2)]
                outcomes = []
                for future in futures:
                    try:
                        outcomes.append(future.result())
                    except RuntimeError as exc:
                        outcomes.append(str(exc))
        self.assertEqual(sum(isinstance(item, tuple) for item in outcomes), 1)
        self.assertIn("HISTORICAL_INVOCATION_ID_COLLISION", outcomes)
        self.assertEqual(len(self.registry.read_text().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
