"""Offline checks for the Step 9.13a preflight capture and run guard."""
from __future__ import annotations

import io
import hashlib
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from scripts import preflight_step9_12_local as local
from scripts import run_step9_12_frozen_evaluation as runner


class AuthorizationInfrastructureTests(unittest.TestCase):
    def test_capture_persists_only_real_result_fields_without_key(self):
        result = {
            "evaluation_id": runner.EVALUATION_ID,
            "frozen_identity": {
                "agent_aggregate_hash": "agent", "harness_aggregate_hash": "harness",
                "benchmark_hash": "benchmark", "scoring_aggregate_hash": "scoring",
                "scoring_hash": "rubric", "frozen_identity_match": True,
            },
            "credential_present": True, "dns_ready": True, "https_ready": True,
            "model_endpoint_reachable": True, "synthetic_production_smoke": "PASS",
            "trace_lineage_ready": True, "ready_for_authorized_run": True,
            "benchmark_v2_executed": False, "benchmark_v3_accessed": False,
            "secret_sentinel": "never-persist-this-key",
        }
        with tempfile.TemporaryDirectory() as directory:
            first = local._capture_local_result(result, Path(directory))
            second = local._capture_local_result(result, Path(directory))
            artifact = json.loads(first.read_text(encoding="utf-8"))
            self.assertNotEqual(first, second)
            self.assertEqual(artifact["preflight_type"], "LOCAL_REAL_PREFLIGHT")
            self.assertEqual(artifact["evaluation_id"], runner.EVALUATION_ID)
            self.assertEqual(artifact["frozen_hashes"]["harness_aggregate"], "harness")
            self.assertTrue(artifact["ready_for_authorized_run"])
            self.assertNotIn("never-persist-this-key", first.read_text(encoding="utf-8"))
            datetime.fromisoformat(artifact["timestamp"])

    def test_capture_does_not_upgrade_failed_preflight(self):
        failed = {
            "evaluation_id": runner.EVALUATION_ID,
            "frozen_identity": {}, "credential_present": False, "dns_ready": False,
            "https_ready": False, "model_endpoint_reachable": False,
            "synthetic_production_smoke": "NOT_RUN", "trace_lineage_ready": False,
            "ready_for_authorized_run": False, "benchmark_v2_executed": False,
            "benchmark_v3_accessed": False,
        }
        with tempfile.TemporaryDirectory() as directory:
            artifact = json.loads(local._capture_local_result(failed, Path(directory)).read_text())
        self.assertFalse(artifact["ready_for_authorized_run"])
        self.assertEqual(artifact["synthetic_production_smoke"], "NOT_RUN")

    def test_local_main_capture_uses_existing_readiness_result(self):
        frozen = {"frozen_identity_match": True}
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(local, "verify_frozen_identity", return_value=frozen), \
             patch.object(local, "_import_ready", return_value=(True, [])), \
             patch.object(local, "_dns_ready", return_value=True), \
             patch.object(local, "_https_ready", return_value=True), \
             patch.object(local, "_model_probe", return_value=(True, "synthetic", 1.0, None)), \
             patch.object(local, "_smoke", return_value=("PASS", {"lineage_created": True})), \
             patch.object(local, "CAPTURE_DIR", Path(directory)), \
             patch.dict(local.os.environ, {"DEEPSEEK_API_KEY": "secret-sentinel"}):
            output = io.StringIO()
            with redirect_stdout(output):
                local.main(["--capture"])
            payload = json.loads(output.getvalue())
            artifact = json.loads(Path(payload["local_preflight_artifact"]).read_text())
        self.assertTrue(payload["ready_for_authorized_run"])
        self.assertTrue(artifact["ready_for_authorized_run"])
        self.assertNotIn("secret-sentinel", json.dumps(artifact))

    def test_historical_freezes_remain_intact_runner_stays_bound_to_step9_11(self):
        status = runner.verify_frozen_identity()
        historical = json.loads(runner.MANIFEST.read_text(encoding="utf-8"))
        step17_path = runner.OUT / "step9_17a_post_step9_17_candidate_freeze.json"
        step17 = json.loads(step17_path.read_text(encoding="utf-8"))
        candidate_path = runner.OUT / "step9_18_candidate_freeze.json"
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        current_path = runner.OUT / "step9_23a_candidate_freeze.json"
        current = json.loads(current_path.read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256(runner.MANIFEST.read_bytes()).hexdigest(),
                         step17["parent_historical_manifest_sha256"])
        historical_agent_aggregate = runner._aggregate(historical["agent_behavior_files"])
        self.assertEqual(historical_agent_aggregate, historical["agent_behavior_aggregate_hash"])
        self.assertEqual(step17["parent_historical_agent_aggregate_hash"], historical_agent_aggregate)
        self.assertNotEqual(status["agent_freeze_match"], True)
        self.assertTrue(status["benchmark_freeze_match"])
        self.assertTrue(status["scoring_freeze_match"])
        self.assertTrue(status["harness_freeze_match"])
        # The original clean-evaluation runner remains bound to Step 9.11 and
        # must fail closed for this newer candidate identity.
        self.assertFalse(status["frozen_identity_match"])
        historical_rows = dict(historical["agent_behavior_files"])
        step17_changed = dict(step17["changed_agent_files"])
        expected_step17_changed = {
            "adaptive_agent/dependency_resolver.py", "adaptive_agent/candidates.py",
            "adaptive_agent/answer_generation.py", "adaptive_agent/state.py",
            "adaptive_agent/state_update.py", "adaptive_agent/tools.py",
        }
        self.assertEqual(set(step17_changed), expected_step17_changed)
        step17_rows = {**historical_rows, **step17_changed}
        self.assertEqual(runner._aggregate(sorted(step17_rows.items())), step17["current_agent_aggregate_hash"])
        self.assertNotEqual(runner._aggregate(sorted(step17_rows.items())), candidate["agent_aggregate_hash"])
        self.assertEqual(candidate["parent_step9_17_candidate_aggregate_hash"], step17["current_agent_aggregate_hash"])
        # Step 9.23 remains an immutable historical candidate. Step 9.24 is an
        # authorized later divergence, so its source hashes must not be asserted
        # against the current worktree; the original runner stays bound to 9.11.
        self.assertEqual(current["authorized_divergence"]["step"], "9.23")
        self.assertEqual(current["effective_agent_file_count"], len(candidate["agent_behavior_files"]))
        self.assertTrue(all(len(digest) == 64 for _, digest in current["authorized_divergence"]["changed_agent_files"]))
        self.assertEqual(current["parent_candidate_agent_aggregate_hash"], candidate["agent_aggregate_hash"])
        self.assertEqual(status["benchmark_v2_cases"], 40)

    def test_step9_24_candidate_freeze_matches_authorized_inventory(self):
        step18 = json.loads((runner.OUT / "step9_18_candidate_freeze.json").read_text(encoding="utf-8"))
        step23 = json.loads((runner.OUT / "step9_23a_candidate_freeze.json").read_text(encoding="utf-8"))
        step24_path = runner.OUT / "step9_24_candidate_freeze.json"
        step24 = json.loads(step24_path.read_text(encoding="utf-8"))

        self.assertEqual(step24["parent_candidate_agent_aggregate_hash"], step23["agent_aggregate_hash"])
        self.assertEqual(step24["authorized_divergence"]["step"], "9.24")
        self.assertEqual(step24["effective_agent_file_count"], 26)
        self.assertEqual(step24["inherited_evaluation_identity"]["benchmark_v2_sha256"], step18["benchmark_hash"])
        self.assertEqual(step24["inherited_evaluation_identity"]["scoring_sha256"], step18["scoring_hash"])
        self.assertEqual(step24["inherited_evaluation_identity"]["harness_sha256"], step18["harness_hash"])

        # The frozen inventory itself remains intact; its old "matches current
        # source" assertion is superseded because Step 9.33 authorizes a later
        # treatment divergence. Current source must not be mislabeled Step 9.24.
        rows = dict(step18["agent_behavior_files"])
        rows.update(dict(step23["authorized_divergence"]["changed_agent_files"]))
        rows.update(dict(step24["authorized_divergence"]["changed_agent_files"]))
        self.assertEqual(len(rows), 26)
        aggregate = runner._aggregate(sorted(rows.items()))
        self.assertEqual(aggregate, step24["agent_aggregate_hash"])
        actual_current = runner._aggregate(sorted(
            (path, runner._actual_hash(path, digest)) for path, digest in rows.items()
        ))
        self.assertNotEqual(actual_current, step24["agent_aggregate_hash"])
        self.assertFalse(step24["benchmark_v2_rerun"])
        self.assertFalse(step24["benchmark_v3_accessed"])
        self.assertFalse(step24["case_specific_logic_present"])

    def test_changed_harness_hash_fails_closed(self):
        original = json.loads(runner.HARNESS_FREEZE.read_text(encoding="utf-8"))
        original["new_harness_files"][0][1] = "0" * 64
        with tempfile.TemporaryDirectory() as directory:
            altered = Path(directory) / "altered_freeze.json"
            altered.write_text(json.dumps(original), encoding="utf-8")
            with patch.object(runner, "HARNESS_FREEZE", altered):
                status = runner.verify_frozen_identity()
        self.assertFalse(status["harness_freeze_match"])
        self.assertFalse(status["frozen_identity_match"])

    def test_evaluation_id_is_required_and_mismatch_stops_before_preflight(self):
        with patch.object(runner, "preflight") as preflight, redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                runner.main(["--preflight"])
            with self.assertRaises(SystemExit):
                runner.main(["--evaluation-id", "wrong", "--preflight"])
            preflight.assert_not_called()

    def test_matching_evaluation_id_allows_read_only_runner_preflight(self):
        expected = {"evaluation_id": runner.EVALUATION_ID, "execution_eligible": True}
        with patch.object(runner, "preflight", return_value=expected) as preflight, \
             patch.object(runner, "run") as run:
            output = io.StringIO()
            with redirect_stdout(output):
                runner.main(["--evaluation-id", runner.EVALUATION_ID, "--preflight"])
            self.assertEqual(json.loads(output.getvalue()), expected)
            preflight.assert_called_once_with()
            run.assert_not_called()

    def test_attempt_guard_blocks_started_and_reused_authorization(self):
        used_authorization = runner.EVALUATION_ID + "-used"
        started = [{"attempt_id": "a", "authorization_id": used_authorization, "status": "STARTED", "cases_started": 1}]
        eligible_identity = {"evaluation_id": runner.EVALUATION_ID, "frozen_identity_match": True}
        with patch.object(runner, "verify_frozen_identity", return_value=eligible_identity), \
             patch.object(runner, "_attempts", return_value=started):
            self.assertFalse(runner.preflight()["execution_eligible"])
        prior_failed = [
            {"attempt_id": "a", "authorization_id": used_authorization, "status": "PREPARED", "cases_started": 0},
            {"attempt_id": "a", "authorization_id": used_authorization, "status": "FAILED_BEFORE_FIRST_CASE", "cases_started": 0},
        ]
        with patch.object(runner, "verify_frozen_identity", return_value=eligible_identity), \
             patch.object(runner, "_attempts", return_value=prior_failed), \
             patch.object(runner, "_append") as append, \
             patch.object(runner.base, "main", side_effect=AssertionError("runner must not start")) as base_main:
            self.assertTrue(runner.preflight()["execution_eligible"])
            with self.assertRaisesRegex(ValueError, "already been used"):
                runner.run(runner.EVALUATION_ID, used_authorization)
            append.assert_not_called()
            base_main.assert_not_called()


if __name__ == "__main__":
    unittest.main()
