import ast
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import preflight_step9_62b_mac_local as preflight


class Step962bMacPreflightTests(unittest.TestCase):
    def test_url_host_parsing_does_not_expose_credentials_or_path(self):
        self.assertEqual(preflight.base_url_host("https://user:secret@API.DEEPSEEK.COM/v1"),
                         "api.deepseek.com")
        self.assertEqual(preflight.base_url_host("api.deepseek.com/v1"), "api.deepseek.com")

    def test_exact_task_distribution_passes_without_case_content(self):
        rows = ([{"task_type": "KNOWLEDGE_QA"}] * 10
                + [{"task_type": "CAUSE_ASSESSMENT"}] * 10
                + [{"task_type": "PERSONALIZED_DECISION"}] * 10
                + [{"task_type": "DATA_ANALYSIS"}] * 10)
        self.assertTrue(preflight.check_task_distribution(rows))

    def test_wrong_distribution_or_count_fails_closed(self):
        self.assertFalse(preflight.check_task_distribution([{"task_type": "KNOWLEDGE_QA"}] * 40))
        self.assertFalse(preflight.check_task_distribution([{"task_type": "KNOWLEDGE_QA"}] * 39))

    def test_non_deepseek_host_skips_all_connectivity(self):
        with patch.object(preflight.socket, "getaddrinfo") as resolver:
            self.assertEqual(preflight.connectivity("unexpected.example"),
                             ("NOT_RUN", "NOT_RUN", "NOT_RUN", False))
            resolver.assert_not_called()

    def test_only_exact_unconsumed_authorization_shape_passes(self):
        manifest = {
            "authorization_id": preflight.AUTH_ID,
            "attempt_id": preflight.ATTEMPT_ID,
            "authorization_status": "ISSUED_NOT_CONSUMED",
            "status": "ISSUED_NOT_EXECUTED",
            "consumed": False,
            "consumed_at_utc": None,
            "authorization_consumption_count": 0,
            "attempt_id_status": "PREBOUND_IDENTITY_ONLY_NOT_CREATED",
        }
        self.assertTrue(preflight.authorization_is_issued_unconsumed(manifest))
        for key, value in (("consumed", True), ("authorization_consumption_count", 1),
                           ("authorization_status", "RETIRED_UNCONSUMED_NON_REUSABLE"),
                           ("attempt_id", "wrong-attempt")):
            altered = {**manifest, key: value}
            self.assertFalse(preflight.authorization_is_issued_unconsumed(altered))

    def test_source_has_no_execution_or_filesystem_mutation_apis(self):
        source = Path(preflight.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertFalse(imports & {"requests", "httpx", "subprocess", "adaptive_agent", "urllib.request"})
        forbidden_calls = {"post", "put", "delete", "urlopen", "unlink", "mkdir", "write_text", "write_bytes"}
        calls = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute)}
        self.assertFalse(calls & forbidden_calls)


if __name__ == "__main__":
    unittest.main()
