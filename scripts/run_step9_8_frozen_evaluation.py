"""One frozen Step 9.8 V2 development/regression run; no Agent changes."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from scripts import run_step8_9_v1_2_1 as base
from scripts.frozen_run_guard import FrozenRunGuard

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation/v1_2_2"
BENCHMARK = ROOT / "evaluation/benchmarks/benchmark_v2_cases.yaml"
RUBRIC = ROOT / "evaluation/benchmark_v1_1_scoring.md"
LEDGER = OUT / "step9_8_execution_attempts.jsonl"
MANIFEST = OUT / "step9_8b_freeze_manifest.json"
# Capture the base serializer before this module installs its trace augmentation.
# The wrapper must never resolve the patched module attribute at call time.
original_state_view = base.state_view

def guard() -> FrozenRunGuard:
    return FrozenRunGuard(ledger_path=LEDGER, manifest_path=MANIFEST,
                          benchmark_path=BENCHMARK, rubric_path=RUBRIC)


def state_view(state):
    view = original_state_view(state)
    view.update({"goal_id": state.goal_id, "state_revision": state.state_revision,
                 "semantic_provenance": state.semantic_provenance,
                 "dependencies_considered": state.dependencies_considered,
                 "dependencies_required": state.dependencies_required,
                 "dependencies_satisfied": state.dependencies_satisfied,
                 "dependencies_unavailable": state.dependencies_unavailable,
                 "base_requirements": state.base_requirements,
                 "effective_requirements": state.effective_requirements,
                 "lineage_events": state.lineage_events})
    return view


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="One authorized frozen Step 9.8 Benchmark V2 run")
    parser.add_argument("--preflight", action="store_true", help="read frozen state only; never calls a model")
    parser.add_argument("--authorization-id", help="required for a real, separately authorized attempt")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    run_guard = guard()
    report = run_guard.preflight()
    if args.preflight:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return report
    if not report["execution_eligible"]:
        raise RuntimeError(f"frozen execution is not eligible: {report['run_state']}")
    if not args.authorization_id:
        raise RuntimeError("--authorization-id is required for a real frozen execution attempt")
    attempt = run_guard.prepare_attempt(args.authorization_id)
    started = False
    completed_count = 0
    last_case_id = "unknown"
    trace_path = OUT / f"step9_8_attempt_{attempt['attempt_id']}_raw_traces.jsonl"
    attempt = {**attempt, "raw_trace_path": str(trace_path.relative_to(ROOT))}
    def before_case(case):
        nonlocal started
        if not started:
            run_guard.mark_started(attempt, case["case_id"])
            started = True

    def after_case(case, _result):
        nonlocal completed_count, last_case_id
        completed_count += 1
        last_case_id = case["case_id"]
        run_guard.mark_case_completed(attempt, last_case_id, completed_count)

    try:
        base.OUT = OUT
        base.BENCHMARK = BENCHMARK
        # The immutable Step 9.8b manifest is verified by FrozenRunGuard above.
        # Base still calls this hook before its loop, so keep that call behaviorless.
        base.write_manifest = lambda _spec: None
        base.state_view = state_view
        # Use the same production factory exported by main_flask, but import it
        # directly to avoid legacy workflow imports unrelated to Adaptive /api/chat.
        import adaptive_agent.flask_app as app_factory
        import sys
        shim = type("ProductionAppShim", (), {
            "_create_adaptive_chat_service": staticmethod(app_factory._create_adaptive_chat_service),
            "create_app": staticmethod(app_factory.create_app),
        })
        sys.modules["main_flask"] = shim
        base.main(before_case=before_case, after_case=after_case, trace_path=trace_path)
        run_guard.mark_completed(attempt, completed_count, last_case_id)
    except BaseException as error:
        if started:
            run_guard.mark_failure_after_partial_execution(attempt, completed_count, error)
        else:
            run_guard.mark_failure_before_first_case(attempt, error)
        raise


if __name__ == "__main__": main()
