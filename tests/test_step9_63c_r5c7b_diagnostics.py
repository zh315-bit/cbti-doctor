from __future__ import annotations

import json
import socket
import ssl
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import preflight_step9_63c_r5c7_mac_local as preflight


def fail(exc: Exception):
    raise exc


class Step963cR5c7bDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.tracker = preflight.StageTracker()

    def test_config_exception_stage(self):
        with self.assertRaises(RuntimeError):
            preflight.run_stage(self.tracker, "CONFIG", lambda: fail(RuntimeError("bad config")))
        self.assertEqual(self.tracker.current_stage, "CONFIG")

    def test_authorization_exception_stage(self):
        with self.assertRaises(PermissionError):
            preflight.run_stage(self.tracker, "AUTHORIZATION_VALIDATION",
                                lambda: fail(PermissionError("manifest unreadable")))
        self.assertEqual(self.tracker.current_stage, "AUTHORIZATION_VALIDATION")

    def test_dns_exception_reports_system_dns_stage(self):
        from scripts import preflight_step9_63b_mac_local as transport

        with patch.object(transport, "_resolver_command", side_effect=FileNotFoundError("dscacheutil missing")):
            with self.assertRaises(FileNotFoundError):
                transport.connectivity(stage_callback=self.tracker.set)
        self.assertEqual(self.tracker.current_stage, "SYSTEM_DNS")

    def _mock_dns_success(self):
        from scripts import preflight_step9_63b_mac_local as transport

        self.enterContext(patch.object(transport, "_resolver_command", return_value=["8.8.8.8"]))
        self.enterContext(patch.object(socket, "getaddrinfo", return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]))
        return transport

    def test_tcp_exception_reports_tcp_stage(self):
        transport = self._mock_dns_success()
        self.enterContext(patch.object(socket, "create_connection", side_effect=TimeoutError("connect timeout")))
        with self.assertRaisesRegex(RuntimeError, "TRANSPORT_OR_TLS_FAILURE"):
            transport.connectivity(stage_callback=self.tracker.set)
        self.assertEqual(self.tracker.current_stage, "TCP_CONNECTION")

    def test_tls_exception_reports_tls_stage(self):
        transport = self._mock_dns_success()

        class Raw:
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return False

        class Context:
            verify_mode = ssl.CERT_REQUIRED
            check_hostname = True
            def wrap_socket(self, *_args, **_kwargs):
                raise ssl.SSLError("synthetic handshake failure")

        self.enterContext(patch.object(socket, "create_connection", return_value=Raw()))
        self.enterContext(patch.object(ssl, "create_default_context", return_value=Context()))
        with self.assertRaisesRegex(RuntimeError, "TRANSPORT_OR_TLS_FAILURE"):
            transport.connectivity(stage_callback=self.tracker.set)
        self.assertEqual(self.tracker.current_stage, "TLS_CONNECTION")

    def test_certificate_validation_stage(self):
        transport = self._mock_dns_success()

        class Raw:
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return False

        class TLS:
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return False
            def getpeercert(self):
                return {}
            def version(self):
                return "TLSv1.3"

        class Context:
            verify_mode = ssl.CERT_REQUIRED
            check_hostname = True
            def wrap_socket(self, *_args, **_kwargs):
                return TLS()

        self.enterContext(patch.object(socket, "create_connection", return_value=Raw()))
        self.enterContext(patch.object(ssl, "create_default_context", return_value=Context()))
        with self.assertRaisesRegex(RuntimeError, "TLS_CERTIFICATE_NOT_VERIFIED"):
            transport.connectivity(stage_callback=self.tracker.set)
        self.assertEqual(self.tracker.current_stage, "TLS_CERTIFICATE_VALIDATION")

    def test_artifact_serialization_exception_stage(self):
        with self.assertRaises(TypeError):
            preflight.run_stage(self.tracker, "ARTIFACT_SERIALIZATION",
                                lambda: preflight.serialize_payload({"bad": object()}))
        self.assertEqual(self.tracker.current_stage, "ARTIFACT_SERIALIZATION")

    def test_artifact_write_exception_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing-parent" / "preflight.json"
            with self.assertRaises(FileNotFoundError):
                preflight.run_stage(self.tracker, "ARTIFACT_WRITE",
                    lambda: preflight.write_serialized_exclusive(missing, b"{}\n"))
        self.assertEqual(self.tracker.current_stage, "ARTIFACT_WRITE")

    def test_secret_assignments_and_bearer_are_redacted(self):
        message = ('DEEPSEEK_API_KEY="synthetic-secret-value"; Authorization: Bearer '
                   'synthetic-bearer-token; password=hunter2; sk-syntheticlongtoken123')
        safe = preflight.sanitize_exception_message(message)
        for secret in ("synthetic-secret-value", "synthetic-bearer-token", "hunter2",
                       "sk-syntheticlongtoken123"):
            self.assertNotIn(secret, safe)
        self.assertIn("[REDACTED]", safe)

    def test_bearer_token_is_redacted(self):
        safe = preflight.sanitize_exception_message("request failed with Bearer abc.def-123")
        self.assertNotIn("abc.def-123", safe)
        self.assertIn("Bearer [REDACTED]", safe)

    def test_complete_request_headers_are_redacted(self):
        safe = preflight.sanitize_exception_message(
            "request headers={'X-Private': 'synthetic-header-value', 'Authorization': 'secret'}")
        self.assertNotIn("synthetic-header-value", safe)
        self.assertNotIn("Authorization", safe)
        self.assertIn("[REDACTED_HEADERS]", safe)

    def test_generic_failure_is_fail_closed_and_preserves_lifecycle_flags(self):
        payload = preflight.failure_payload("CONFIG", RuntimeError("synthetic failure"))
        self.assertEqual(payload["STEP9_63C_R5C7C_STATUS"], "FAIL_CLOSED_PREFLIGHT_ERROR")
        self.assertEqual(payload["FAILURE_STAGE"], "CONFIG")
        self.assertFalse(payload["READY_FOR_SINGLE_ATOMIC_FORMAL_EXECUTION"])
        self.assertFalse(payload["authorization_consumed"])
        self.assertEqual(payload["formal_v4_case_executed"], 0)
        self.assertFalse(payload["attempt_created"])
        self.assertFalse(payload["namespace_created"])
        self.assertFalse(payload["model_inference_executed"])
        self.assertFalse(payload["agent_evaluation_executed"])
        self.assertFalse(payload["rag_evaluation_executed"])
        self.assertFalse(payload["http_inference_request_sent"])
        json.dumps(payload)

    def test_unknown_stage_fails_closed_as_unknown(self):
        payload = preflight.failure_payload("UNREGISTERED", RuntimeError("failure"))
        self.assertEqual(payload["FAILURE_STAGE"], "UNKNOWN")
        self.assertFalse(payload["authorization_consumed"])
        self.assertEqual(payload["formal_v4_case_executed"], 0)


if __name__ == "__main__":
    unittest.main()
