"""Offline-only r8 preflight tests. No DNS, transport, HTTP, model, or cases.

Step 9.63c-r5c10ad AR-2: 17 methods that targeted the removed r8-era API of the now
shim-only r5 producer were retired (archived verbatim in
tests/retired/test_step9_63c_r5_mac_local_preflight.py.retired) or rewritten in
tests/test_step9_63c_r5c10ad_r5_producer_equivalence.py. Remaining methods are either
identity-dependent (RC1, kept fail-closed). The last two UNCOVERED methods
(test_multiple_active_authorizations, test_historical_pin_mismatch) were retired in Step
9.63c-r5c10af (archived verbatim in the .retired file) and are covered by the r5c10ae
consumer gate tests; see evaluation/v1_2_3/step9_63c_r5c10af_r5_coverage_mapping.json.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import preflight_step9_63c_r5_mac_local as preflight


GOOD_NETWORK = {
    "SYSTEM_DNS_STATUS": "PASS", "PYTHON_GETADDRINFO_STATUS": "PASS",
    "DEFAULT_DIG_STATUS": "PASS", "GOOGLE_DNS_STATUS": "PASS",
    "CLOUDFLARE_DNS_STATUS": "PASS", "TCP_CONNECTION": "PASS",
    "TLS_CONNECTION": "PASS", "TLS_CERTIFICATE_PRESENT": True,
    "TLS_CERTIFICATE_VERIFIED": True, "TLS_VERSION": "TLSv1.3",
}
TEST_PREFLIGHT_ID = "preflight-step9_63c_r5-r8-" + "1" * 32


class R8MacLocalPreflightTests(unittest.TestCase):
    def _config_failure(self, values, reason):
        from scripts import preflight_step9_63b_mac_local as transport
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text("# synthetic only\n", encoding="utf-8")
            fake_python = root / ".venv/bin/python"
            with patch.object(transport, "ROOT", root), \
                 patch.object(transport, "EXPECTED_ROOT", root), \
                 patch.object(transport, "EXPECTED_PYTHON", fake_python), \
                 patch.object(transport.sys, "platform", "darwin"), \
                 patch.object(transport.sys, "executable", str(fake_python)), \
                 patch.object(transport.sys, "prefix", str(root / ".venv")), \
                 patch.object(transport.Path, "cwd", return_value=root), \
                 patch.object(transport.importlib, "import_module"), \
                 patch.object(transport, "load_dotenv"), \
                 patch.object(transport.os, "getenv", side_effect=lambda key, default="": values.get(key, default)):
                with self.assertRaisesRegex(RuntimeError, reason):
                    transport._runtime_and_config()

    def test_missing_api_key(self):
        self._config_failure({}, "API_KEY_MISSING")

    def test_wrong_deepseek_host(self):
        self._config_failure({"DEEPSEEK_API_KEY": "synthetic", "DEEPSEEK_BASE_URL": "https://example.com"},
                             "MODEL_BASE_URL_MISMATCH")

    def test_wrong_model(self):
        self._config_failure({"DEEPSEEK_API_KEY": "synthetic", "DEEPSEEK_MODEL": "other-model"},
                             "MODEL_PROFILE_MISMATCH")

    def test_accidental_http_model_agent_rag_execution_guard(self):
        source = Path(preflight.__file__).read_text(encoding="utf-8")
        for forbidden in ("requests.get(", "requests.post(", "httpx.", "/chat/completions",
                          "/api/chat", "create_chat_model(", "adapter.run(",
                          "begin_and_commit(", "reserve_namespace(", "_case_result("):
            self.assertNotIn(forbidden, source)

if __name__ == "__main__":
    unittest.main()
