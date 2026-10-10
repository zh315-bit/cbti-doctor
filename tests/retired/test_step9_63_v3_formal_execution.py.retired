"""Synthetic-only tests for Step 9.63's fail-closed pre-execution gate."""
import ast
import unittest
from pathlib import Path

from scripts import run_step9_63_v3_formal_execution as runner


def eligible_state():
    state = {name: True for name in (
        "project_root_match", "python_runtime_match", "r6_freeze_match", "runner_sha_match",
        "agent_match", "frozen_identities_match", "lifecycle_contract_match",
        "authorization_id_match", "authorization_status_issued_unconsumed",
        "authorization_consumption_count_zero", "exactly_one_active_authorization",
        "active_authorization_is_bound_id", "old_authorization_retired",
        "old_authorization_non_executable", "attempt_id_match", "attempt_absent",
        "namespace_id_match", "namespace_absent", "case_set_match", "case_order_match",
        "task_distribution_match", "historical_integrity_match", "provenance_gap_preserved",
        "fresh_connectivity_pass", "atomic_commit_protocol_match",
        "crash_reconciliation_protocol_match",
    )}
    state.update(authorization_consumption_count=0, active_authorization_count=1,
                 case_count=40, task_distribution=runner.EXPECTED_DISTRIBUTION.copy(),
                 step9_58_provenance_gap=runner.HISTORICAL_GAP)
    return state


class Step963PrecommitTests(unittest.TestCase):
    def test_01_valid_issued_unconsumed_fixture_passes(self):
        self.assertEqual(runner.validate_precommit(eligible_state()), [])

    def test_02_already_consumed_fails(self):
        s = eligible_state(); s["authorization_status_issued_unconsumed"] = False
        self.assertIn("authorization_status_issued_unconsumed", runner.validate_precommit(s))

    def test_03_retired_authorization_fails(self):
        s = eligible_state(); s["old_authorization_retired"] = False
        self.assertIn("old_authorization_retired", runner.validate_precommit(s))

    def test_04_wrong_authorization_fails(self):
        s = eligible_state(); s["authorization_id_match"] = False
        self.assertIn("authorization_id_match", runner.validate_precommit(s))

    def test_05_runner_hash_mismatch_fails(self):
        s = eligible_state(); s["runner_sha_match"] = False
        self.assertIn("runner_sha_match", runner.validate_precommit(s))

    def test_06_agent_identity_mismatch_fails(self):
        s = eligible_state(); s["agent_match"] = False
        self.assertIn("agent_match", runner.validate_precommit(s))

    def test_07_frozen_identity_mismatch_fails(self):
        s = eligible_state(); s["frozen_identities_match"] = False
        self.assertIn("frozen_identities_match", runner.validate_precommit(s))

    def test_08_case_set_mismatch_fails(self):
        s = eligible_state(); s["case_set_match"] = False
        self.assertIn("case_set_match", runner.validate_precommit(s))

    def test_09_case_order_mismatch_fails(self):
        s = eligible_state(); s["case_order_match"] = False
        self.assertIn("case_order_match", runner.validate_precommit(s))

    def test_10_namespace_collision_fails(self):
        s = eligible_state(); s["namespace_absent"] = False
        self.assertIn("namespace_absent", runner.validate_precommit(s))

    def test_11_attempt_collision_fails(self):
        s = eligible_state(); s["attempt_absent"] = False
        self.assertIn("attempt_absent", runner.validate_precommit(s))

    def test_12_multiple_active_authorizations_fail(self):
        s = eligible_state(); s["active_authorization_count"] = 2
        self.assertIn("active_authorization_count", runner.validate_precommit(s))

    def test_13_connectivity_failure_fails(self):
        s = eligible_state(); s["fresh_connectivity_pass"] = False
        self.assertIn("fresh_connectivity_pass", runner.validate_precommit(s))

    def test_14_precommit_failure_does_not_mutate_consumption(self):
        s = eligible_state(); s["r6_freeze_match"] = False
        before = s["authorization_consumption_count"]
        self.assertTrue(runner.validate_precommit(s))
        self.assertEqual(s["authorization_consumption_count"], before)

    def test_15_second_invocation_after_consumption_fails(self):
        s = eligible_state(); s["authorization_consumption_count"] = 1
        s["authorization_consumption_count_zero"] = False
        self.assertIn("authorization_consumption_count", runner.validate_precommit(s))

    def test_16_partial_commit_is_detectable_and_burned(self):
        self.assertEqual(runner.classify_commit_state(consumed_event=True,
            attempt_ledger=False, namespace_reservation=True), "PARTIAL_COMMIT_FAIL_CLOSED_BURNED")

    def test_17_partial_trace_is_preserved_without_resume(self):
        self.assertEqual(runner.partial_trace_policy(traces_exist=True, attempt_completed=False),
                         "PRESERVE_APPEND_ONLY_NO_RESUME_OR_RERUN")

    def test_18_historical_hash_mismatch_fails(self):
        s = eligible_state(); s["historical_integrity_match"] = False
        self.assertIn("historical_integrity_match", runner.validate_precommit(s))

    def test_19_provenance_gap_must_remain_documented(self):
        s = eligible_state(); s["step9_58_provenance_gap"] = "REPAIRED"
        self.assertIn("step9_58_provenance_gap", runner.validate_precommit(s))

    def test_20_build_import_has_no_execution_or_network_calls(self):
        source = Path(runner.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        forbidden = {"urlopen", "create_connection", "getaddrinfo", "run_case", "create_app",
                     "_create_adaptive_chat_service", "load_dotenv"}
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        self.assertFalse(forbidden & names)
        self.assertIn("--execute-formal-v4", source)
        self.assertFalse(any("authorization_lifecycle_events.jsonl" in p.name
                             for p in Path(runner.ROOT / "evaluation/v4_runs").glob("*")))

    def test_atomic_and_crash_contract_are_mandatory(self):
        s = eligible_state(); s["atomic_commit_protocol_match"] = False
        failures = runner.validate_precommit(s)
        self.assertIn("atomic_commit_protocol_match", failures)
        s = eligible_state(); s["crash_reconciliation_protocol_match"] = False
        self.assertIn("crash_reconciliation_protocol_match", runner.validate_precommit(s))

    def test_commit_state_only_accepts_complete_tuple(self):
        self.assertEqual(runner.classify_commit_state(consumed_event=True,
            attempt_ledger=True, namespace_reservation=True), "COMMITTED_EXACTLY_ONCE")

    def test_no_effect_commit_state_is_not_consumed(self):
        self.assertEqual(runner.classify_commit_state(consumed_event=False,
            attempt_ledger=False, namespace_reservation=False), "PRE_COMMIT_UNCONSUMED")


if __name__ == "__main__":
    unittest.main()
