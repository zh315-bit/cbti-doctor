from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import preflight_step9_63c_r5c7_mac_local as preflight


class Step963cR5c7PreflightTests(unittest.TestCase):
    def test_connectivity_pass_requires_every_transport_check(self):
        good = {key: "PASS" for key in (
            "SYSTEM_DNS_STATUS", "PYTHON_GETADDRINFO_STATUS", "DEFAULT_DIG_STATUS",
            "GOOGLE_DNS_STATUS", "CLOUDFLARE_DNS_STATUS", "TCP_CONNECTION", "TLS_CONNECTION")}
        good["TLS_CERTIFICATE_VERIFIED"] = True
        good["TLS_CERTIFICATE_PRESENT"] = True
        preflight.validate_connectivity(good)

    def test_connectivity_failure_fails_closed_for_each_gate(self):
        keys = ("SYSTEM_DNS_STATUS", "PYTHON_GETADDRINFO_STATUS", "DEFAULT_DIG_STATUS",
                "GOOGLE_DNS_STATUS", "CLOUDFLARE_DNS_STATUS", "TCP_CONNECTION", "TLS_CONNECTION")
        for key in keys:
            with self.subTest(key=key):
                value = {name: "PASS" for name in keys}
                value["TLS_CERTIFICATE_VERIFIED"] = True
                value["TLS_CERTIFICATE_PRESENT"] = True
                value[key] = "FAIL"
                with self.assertRaisesRegex(RuntimeError, "CONNECTIVITY_NOT_READY"):
                    preflight.validate_connectivity(value)

    def test_unverified_tls_certificate_fails_closed(self):
        value = {key: "PASS" for key in (
            "SYSTEM_DNS_STATUS", "PYTHON_GETADDRINFO_STATUS", "DEFAULT_DIG_STATUS",
            "GOOGLE_DNS_STATUS", "CLOUDFLARE_DNS_STATUS", "TCP_CONNECTION", "TLS_CONNECTION")}
        value["TLS_CERTIFICATE_VERIFIED"] = False
        value["TLS_CERTIFICATE_PRESENT"] = True
        with self.assertRaisesRegex(RuntimeError, "CONNECTIVITY_NOT_READY"):
            preflight.validate_connectivity(value)

    def test_missing_tls_certificate_fails_closed(self):
        value = {key: "PASS" for key in (
            "SYSTEM_DNS_STATUS", "PYTHON_GETADDRINFO_STATUS", "DEFAULT_DIG_STATUS",
            "GOOGLE_DNS_STATUS", "CLOUDFLARE_DNS_STATUS", "TCP_CONNECTION", "TLS_CONNECTION")}
        value["TLS_CERTIFICATE_PRESENT"] = False
        value["TLS_CERTIFICATE_VERIFIED"] = True
        with self.assertRaisesRegex(RuntimeError, "CONNECTIVITY_NOT_READY"):
            preflight.validate_connectivity(value)

    def test_instance_scoped_target_is_unique_and_not_legacy_fixed_path(self):
        first = preflight.new_preflight_id()
        second = preflight.new_preflight_id()
        self.assertRegex(first, r"^preflight-step9_63c_r5-r5c8b-[0-9a-f]{32}$")
        self.assertNotEqual(first, second)
        self.assertNotIn(first, {
            "preflight-step9_63c-r10-10c2f1537cc44da7b40e95a1ea819028",
            "preflight-step9_63c-r10-c0f9957584c9443fa8ef5a70b3712bed",
            "preflight-step9_63c-r10-7decee88a4c8439fb3f30ffb68240b31",
        })
        target = preflight.preflight_path(first)
        self.assertIn(first, target.name)
        self.assertIn(preflight.AUTH_ID, target.name)
        self.assertFalse(preflight.preflight_target_exists(target))

    def test_exclusive_persistence_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "unique-preflight.json"
            preflight_id = preflight.new_preflight_id()
            first_hash = preflight.write_exclusive(target, {"preflight_id": preflight_id})
            original = target.read_bytes()
            self.assertEqual(len(first_hash), 64)
            with self.assertRaisesRegex(RuntimeError, "PREFLIGHT_TARGET_EXISTS"):
                preflight.write_exclusive(target, {"status": "replacement"})
            self.assertEqual(target.read_bytes(), original)
            self.assertEqual(json.loads(target.read_text())["preflight_id"], preflight_id)


if __name__ == "__main__":
    unittest.main()
