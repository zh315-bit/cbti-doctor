"""Offline guards for the V4 local-preflight recovery only."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run_step9_28a_v4_local_preflight as recovery


class V4LocalPreflightRecoveryTests(unittest.TestCase):
    def test_dns_failure_persists_a_new_non_v4_artifact_without_smoke(self):
        frozen = {"freeze_match": True}
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            with patch.object(recovery, "OUT", out), \
                 patch.object(recovery.runner, "verify_frozen_identity", return_value=frozen), \
                 patch.object(recovery.runner, "model_configuration_match", return_value=True), \
                 patch.object(recovery.runner, "_prior_formal_attempt_exists", return_value=False), \
                 patch.object(recovery, "_import_ready", return_value=(True, [])), \
                 patch.object(recovery, "_dns_ready", return_value=False), \
                 patch.object(recovery, "_model_probe", side_effect=AssertionError("model probe")), \
                 patch.object(recovery, "_synthetic_production_smoke", side_effect=AssertionError("smoke")):
                result, artifact = recovery.run()
            stored = json.loads(artifact.read_text(encoding="utf-8"))
        self.assertFalse(result["model_endpoint_reachable"])
        self.assertEqual(result["synthetic_production_smoke"], "NOT_RUN")
        self.assertFalse(result["trace_lineage_ready"])
        self.assertEqual(result["ready_for_final_authorization"], result["ready_for_v4_final_authorization"])
        self.assertEqual(result["benchmark_v4_accessed_by_agent"], result["benchmark_v4_accessed_for_evaluation"])
        self.assertFalse(result["benchmark_v4_accessed_for_evaluation"])
        self.assertEqual(result["v4_case_executed"], 0)
        self.assertFalse(stored["ready_for_v4_final_authorization"])


if __name__ == "__main__":
    unittest.main()
