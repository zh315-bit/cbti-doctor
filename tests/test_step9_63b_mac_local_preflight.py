"""Offline checks for the non-consuming Step 9.63b preflight package."""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class MacLocalPreflightTests(unittest.TestCase):
    def test_dns_parser_accepts_only_public_ip_addresses(self):
        from scripts import preflight_step9_63b_mac_local as preflight

        self.assertEqual(preflight._addresses("alias.example.\n3.173.21.63\n127.0.0.1\n"),
                         ["3.173.21.63"])
        self.assertEqual(preflight._addresses("name: api.deepseek.com\nip_address: 3.173.21.63\n",
                                               system=True), ["3.173.21.63"])

    def test_failed_dns_never_opens_transport(self):
        from scripts import preflight_step9_63b_mac_local as preflight

        with patch.object(preflight, "_resolver_command", return_value=[]), \
             patch.object(preflight.socket, "getaddrinfo", return_value=[]), \
             patch.object(preflight.socket, "create_connection") as connect:
            with self.assertRaisesRegex(RuntimeError, "DNS_NOT_READY"):
                preflight.connectivity()
            connect.assert_not_called()

    def test_preflight_rechecks_execution_state_after_transport(self):
        from scripts import preflight_step9_63b_mac_local as preflight

        with tempfile.TemporaryDirectory() as directory, \
             patch.object(preflight, "ARTIFACT", Path(directory) / "attestation.json"), \
             patch.object(preflight, "_runtime_and_config", return_value={"PROJECT_ROOT_MATCH": True}), \
             patch.object(preflight, "_execution_state", side_effect=[{"ok": 1}, {"ok": 1}]) as state, \
             patch.object(preflight, "connectivity", return_value={"TLS_CONNECTION": "PASS"}) as network:
            result = preflight.run_preflight()
        self.assertEqual(result["status"], "PASS_NON_CONSUMING_PREFLIGHT")
        self.assertFalse(result["authorization_consumed"])
        self.assertFalse(result["attempt_created"])
        self.assertFalse(result["namespace_created"])
        self.assertEqual(state.call_count, 2)
        network.assert_called_once()

    def test_state_change_fails_closed(self):
        from scripts import preflight_step9_63b_mac_local as preflight

        with tempfile.TemporaryDirectory() as directory, \
             patch.object(preflight, "ARTIFACT", Path(directory) / "attestation.json"), \
             patch.object(preflight, "_runtime_and_config", return_value={}), \
             patch.object(preflight, "_execution_state", side_effect=[{"count": 0}, {"count": 1}]), \
             patch.object(preflight, "connectivity", return_value={}):
            with self.assertRaisesRegex(RuntimeError, "PRE_POST_STATE_MISMATCH"):
                preflight.run_preflight()

    def test_existing_attestation_fails_before_network(self):
        from scripts import preflight_step9_63b_mac_local as preflight

        with tempfile.TemporaryDirectory() as directory:
            existing = Path(directory) / "attestation.json"
            existing.write_text("historical", encoding="utf-8")
            with patch.object(preflight, "ARTIFACT", existing), \
                 patch.object(preflight, "connectivity") as network:
                with self.assertRaisesRegex(RuntimeError, "PREFLIGHT_ARTIFACT_EXISTS"):
                    preflight.run_preflight()
                network.assert_not_called()
            self.assertEqual(existing.read_text(encoding="utf-8"), "historical")

    def test_attestation_exclusive_create(self):
        from scripts import preflight_step9_63b_mac_local as preflight

        with tempfile.TemporaryDirectory() as directory, \
             patch.object(preflight, "ARTIFACT", Path(directory) / "attestation.json"):
            payload = {"status": "PASS_NON_CONSUMING_PREFLIGHT", "consumed": False}
            digest = preflight._write_attestation(payload)
            self.assertEqual(len(digest), 64)
            self.assertEqual(json.loads(preflight.ARTIFACT.read_text()), payload)
            with self.assertRaises(FileExistsError):
                preflight._write_attestation(payload)

    def test_failure_prints_no_exception_or_secret(self):
        from scripts import preflight_step9_63b_mac_local as preflight

        with patch.object(preflight, "run_preflight", side_effect=RuntimeError("secret-sentinel")):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(preflight.main(), 1)
            self.assertNotIn("secret-sentinel", output.getvalue())
            self.assertIn("FAIL_CLOSED", output.getvalue())

    def test_real_script_has_no_formal_execution_entrypoint(self):
        from scripts import preflight_step9_63b_mac_local as preflight

        source = Path(preflight.__file__).read_text(encoding="utf-8")
        for forbidden in ("execute_formal(", "adapter.run(", "begin_and_commit(",
                          "reserve_namespace(", "create_chat_model(", "requests.get(",
                          "requests.post(", "/chat/completions", "/api/chat"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
