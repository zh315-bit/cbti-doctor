"""Step 9.10a harness-only recursion/equivalence tests; no model or benchmark."""
from __future__ import annotations

import ast
import hashlib
import inspect
import unittest
from pathlib import Path
from unittest.mock import patch

from adaptive_agent.state import AdaptiveAgentState, TaskType
from scripts import run_step9_8_frozen_evaluation as harness
from scripts.frozen_run_guard import FrozenRunGuard, sha256


ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "evaluation/v1_2_2/step9_8_execution_attempts.jsonl"


def sample_state():
    return AdaptiveAgentState(
        goal="解释刺激控制", task_type=TaskType.KNOWLEDGE_QA,
        facts={"bedtime": "23:00"}, evidence=["synthetic evidence"],
        goal_id="goal_synthetic", state_revision=3,
        semantic_provenance=[{"semantic_id": "sem_synthetic"}],
        dependencies_considered=[{"dependency_id": "dep_synthetic"}],
        effective_requirements={"decision_fields": ()},
    )


class HarnessMinimalFixTests(unittest.TestCase):
    def test_f1_wrapped_state_view_calls_captured_original_once_without_recursion(self):
        state = sample_state()
        with patch.object(harness, "original_state_view", wraps=harness.original_state_view) as original:
            wrapped = harness.state_view(state)
        self.assertEqual(original.call_count, 1)
        self.assertEqual(wrapped["goal_id"], "goal_synthetic")

    def test_f2_state_view_preserves_original_fields_and_values(self):
        state = sample_state()
        original = harness.original_state_view(state)
        wrapped = harness.state_view(state)
        for key, value in original.items():
            self.assertIn(key, wrapped)
            self.assertEqual(wrapped[key], value)
        self.assertEqual(wrapped["goal_id"], state.goal_id)
        self.assertEqual(wrapped["state_revision"], state.state_revision)
        self.assertEqual(wrapped["lineage_events"], state.lineage_events)

    def test_f3_repeated_wrapped_calls_do_not_accumulate_patch_or_recurse(self):
        state = sample_state()
        views = [harness.state_view(state) for _ in range(5)]
        self.assertTrue(all(view == views[0] for view in views))
        self.assertIsNot(harness.original_state_view, harness.state_view)

    def test_f4_callback_audit_has_no_wrapper_to_patched_function_cycle(self):
        source = inspect.getsource(harness)
        tree = ast.parse(source)
        state_view_node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "state_view")
        calls = [node for node in ast.walk(state_view_node) if isinstance(node, ast.Call)]
        self.assertFalse(any(
            isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == "base"
            and call.func.attr == "state_view"
            for call in calls
        ))
        self.assertIn("run_guard.mark_started", source)
        self.assertIn("run_guard.mark_case_completed", source)
        self.assertNotIn("before_case(case)", inspect.getsource(harness.state_view))

    def test_f5_step9_8_history_is_read_only_and_terminal_status_is_preserved(self):
        before = hashlib.sha256(LEDGER.read_bytes()).hexdigest()
        entries = [__import__("json").loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines()]
        terminal = [entry for entry in entries if entry.get("attempt_id") == "attempt_9915d68189f343f8996fc412d4efec53"][-1]
        self.assertEqual(terminal["status"], "FAILED_AFTER_PARTIAL_EXECUTION")
        self.assertEqual(hashlib.sha256(LEDGER.read_bytes()).hexdigest(), before)

    def test_f6_new_attempt_ids_are_independent_of_consumed_step9_8_identifiers(self):
        import json, tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            benchmark = root / "benchmark.yaml"; benchmark.write_text("cases: []\n", encoding="utf-8")
            rubric = root / "rubric.md"; rubric.write_text("rubric\n", encoding="utf-8")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"benchmark": {"sha256": sha256(benchmark)},
                                             "evaluation_configuration": {"rubric_sha256": sha256(rubric)}}), encoding="utf-8")
            guard = FrozenRunGuard(ledger_path=root / "ledger.jsonl", manifest_path=manifest,
                                   benchmark_path=benchmark, rubric_path=rubric)
            attempt = guard.prepare_attempt("step9_10_future_authorization_example")
        self.assertNotEqual(attempt["attempt_id"], "attempt_9915d68189f343f8996fc412d4efec53")
        self.assertNotEqual(attempt["authorization_reference"], "step9_8_local_frozen_20260921_auth01")


if __name__ == "__main__":
    unittest.main()
