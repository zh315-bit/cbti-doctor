#!/usr/bin/env python3
"""Fail-closed selector for Step 9.51a non-benchmark tests."""
from __future__ import annotations

import argparse
import ast
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evaluation/v1_2_3/step9_51a_safe_test_manifest.json"
TEST_DIR = ROOT / "tests"

SAFE_ALLOWLIST = frozenset({
    "test_adaptive_foundations", "test_adaptive_loop", "test_adaptive_service",
    "test_answer_generation_grounding", "test_chat_sessions",
    "test_input_understanding_hardening", "test_model_configuration",
    "test_policy_refinement", "test_step4_regressions",
    "test_step9_10a_harness_fix", "test_step9_12b_trace_observer",
    "test_step9_16_dependency_formation", "test_step9_17_tool_projection",
    "test_step9_18_information_value_gate", "test_step9_23_state_answer_integrity",
    "test_step9_24_information_value", "test_step9_33_r1_r2_r3_repairs",
    "test_step9_35a_treatment_runner", "test_step9_42_answer_authorization",
    "test_step9_4_integration_audit", "test_step9_50_bounded_answer_contract",
    "test_step9_50_traceability_contract", "test_step9_6_effective_requirements_lineage",
    "test_step9_8f_frozen_run_guard", "test_v1_1_answer_tool_grounding",
    "test_v1_1_input_state", "test_v1_1_sufficiency_ask",
    "test_v1_2_1_preconditions", "test_v1_2_2_dependency_contract",
    "test_v1_2_information_value", "test_step9_51a_validation_boundary",
})

DENIED_REASONS = {
    "test_step9_13a_authorization_infrastructure":
        "Contains historical identity aggregation and a runner invocation; excluded as a whole.",
    "test_step9_20a_v3_runner":
        "Exercises the held-out runner.run path, even though its cases are synthetic; runner execution is out of scope.",
    "test_step9_28_v4_runner": "V4 runner execution/authorization module; prohibited.",
    "test_step9_28a_v4_local_preflight": "V4-specific preflight module; excluded from non-benchmark rerun.",
    "test_step9_30a2_lineage_sidecar": "Reads formal V4 lineage/adjudication artifacts; prohibited access boundary.",
    "test_step9_30a_v4_adjudication": "Contains V4 adjudication and aggregate_completed; prohibited.",
    "test_step9_30c_v4_aggregation": "Reads frozen V4 adjudication/sidecar and invokes aggregate_records; prohibited.",
    "test_step9_43a_treatment_identity":
        "Contains test_01a_frozen_v2_identity_preflight_passes_without_case_execution, which requires current V3 tree == frozen V2; keep V2 identity archival, not a V3 gate.",
    "test_v1_2_mechanism_validation": "Writes the historical evaluation/v1_2 trace artifact.",
    "test_v1_2_1_mechanism_validation": "Writes the historical evaluation/v1_2_1 trace artifact.",
}

RISK_FLAGS = (
    "may_access_v4", "may_execute_formal_v4", "may_access_v5", "may_aggregate", "may_adjudicate",
    "may_create_formal_attempt", "may_create_authorization",
    "may_write_formal_artifacts", "may_mutate_historical_artifacts",
)
REQUIRED_FLAGS = (
    "may_execute_agent", "may_execute_rag", "may_execute_model", "may_access_v4",
    "may_aggregate", "may_adjudicate", "may_write_formal_artifacts",
    "may_execute_formal_v4", "may_access_v5", "may_create_formal_attempt",
    "may_create_authorization", "may_mutate_historical_artifacts",
)
FORBIDDEN_CALLS = {"aggregate_records", "aggregate_completed", "adjudicate", "run_case"}


def source_test_count(path: Path) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return sum(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
               and node.name.startswith("test_") for node in ast.walk(tree))


def risky_call_errors(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    errors = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else fn.id if isinstance(fn, ast.Name) else ""
        if name in FORBIDDEN_CALLS or (name == "run" and isinstance(fn, ast.Attribute)):
            errors.append(f"{path.relative_to(ROOT)}:{node.lineno}: blocked call {name}()")
    return errors


def audit_manifest(data: dict) -> tuple[list[dict], list[str]]:
    errors: list[str] = []
    entries = data.get("modules")
    if not isinstance(entries, list):
        return [], ["manifest modules must be a list"]
    by_name = {entry.get("module"): entry for entry in entries if isinstance(entry, dict)}
    if len(by_name) != len(entries):
        errors.append("manifest contains duplicate or malformed module entries")
    discovered = {p.stem for p in TEST_DIR.glob("test_*.py")}
    if set(by_name) != discovered:
        errors.append("manifest module inventory does not exactly match tests/test_*.py")
    allowed = {name for name, item in by_name.items() if item.get("allowed") is True}
    if allowed != SAFE_ALLOWLIST:
        errors.append("manifest allowed module set differs from pinned Step 9.51a allowlist")
    for name, item in by_name.items():
        path = TEST_DIR / f"{name}.py"
        if not path.is_file():
            errors.append(f"missing module file: {name}")
            continue
        if item.get("path") != f"tests/{name}.py":
            errors.append(f"{name}: repository-relative path mismatch")
        missing = [field for field in REQUIRED_FLAGS if not isinstance(item.get(field), bool)]
        if missing:
            errors.append(f"{name}: missing boolean metadata {', '.join(missing)}")
        if item.get("allowed") is True:
            if item.get("reason") in (None, "") or item.get("identity_scope") not in {
                "SYNTHETIC_ONLY", "UNIT_ONLY", "TEMPORARY_FIXTURES_ONLY", "V3_DEVELOPMENT_ONLY"
            }:
                errors.append(f"{name}: missing safe scope/reason")
            risky = [field for field in RISK_FLAGS if item.get(field) is True]
            if risky:
                errors.append(f"{name}: disallowed risk metadata {', '.join(risky)}")
            errors.extend(risky_call_errors(path))
        elif name not in DENIED_REASONS or not item.get("reason"):
            errors.append(f"{name}: denied module has no reviewed exclusion reason")
    return [by_name[name] for name in sorted(allowed) if name in by_name], errors


def create_manifest() -> None:
    if MANIFEST.exists():
        raise RuntimeError(f"refusing to overwrite existing manifest: {MANIFEST}")
    discovered = sorted(p.stem for p in TEST_DIR.glob("test_*.py"))
    entries = []
    for name in discovered:
        allowed = name in SAFE_ALLOWLIST
        if allowed:
            purpose = "Synthetic/unit regression; no formal benchmark result path."
            if name == "test_step9_50_bounded_answer_contract": purpose = "Step 9.50 synthetic bounded-answer authorization contract (30 cases)."
            elif name == "test_step9_50_traceability_contract": purpose = "Step 9.50 synthetic trace lineage and invariant contract."
            elif name in {"test_step9_10a_harness_fix", "test_step9_8f_frozen_run_guard", "test_step9_35a_treatment_runner"}:
                purpose = "Exactly-once/authorization guard tests use TemporaryDirectory fixtures only; no formal attempt is created."
            elif name == "test_step9_42_answer_authorization": purpose = "Step 9.41/9.42 synthetic safety regression; mocked retrieval only."
            elif name in {"test_answer_generation_grounding", "test_v1_1_answer_tool_grounding"}:
                purpose = "Answer-generation/grounding unit tests; local synthetic fixtures and mocked adapters."
            identity_scope = ("TEMPORARY_FIXTURES_ONLY" if name in {
                "test_step9_10a_harness_fix", "test_step9_8f_frozen_run_guard", "test_step9_35a_treatment_runner"
            } else "V3_DEVELOPMENT_ONLY" if name in {
                "test_step9_50_bounded_answer_contract", "test_step9_50_traceability_contract",
                "test_step9_51a_validation_boundary"
            } else "SYNTHETIC_ONLY" if name in {
                "test_adaptive_loop", "test_adaptive_service", "test_step9_4_integration_audit",
                "test_step9_6_effective_requirements_lineage", "test_step9_42_answer_authorization"
            } else "UNIT_ONLY")
            may_execute_agent = name in {
                "test_adaptive_loop", "test_adaptive_service", "test_step9_4_integration_audit",
                "test_step9_6_effective_requirements_lineage", "test_step9_42_answer_authorization"
            }
            reason = "Explicit non-benchmark allowlist; audited test inputs are synthetic, local, or temporary."
        else:
            purpose = "Excluded from Step 9.51a safe rerun."
            identity_scope = "PROHIBITED_OR_HISTORICAL"
            may_execute_agent = name in {"test_step9_20a_v3_runner", "test_step9_28_v4_runner"}
            reason = DENIED_REASONS[name]
        entries.append({
            "module": name, "path": f"tests/{name}.py", "purpose": purpose,
            "allowed": allowed, "reason": reason,
            "may_execute_agent": may_execute_agent, "may_execute_rag": False,
            "may_execute_model": False, "may_access_v4": name in {
                "test_step9_28_v4_runner", "test_step9_28a_v4_local_preflight",
                "test_step9_30a2_lineage_sidecar", "test_step9_30a_v4_adjudication",
                "test_step9_30c_v4_aggregation"
            },
            "may_aggregate": name in {"test_step9_13a_authorization_infrastructure",
                                      "test_step9_30a_v4_adjudication", "test_step9_30c_v4_aggregation"},
            "may_adjudicate": name in {"test_step9_30a2_lineage_sidecar", "test_step9_30a_v4_adjudication"},
            "may_write_formal_artifacts": name in {"test_v1_2_mechanism_validation",
                                                    "test_v1_2_1_mechanism_validation"},
            "may_execute_formal_v4": name in {"test_step9_28_v4_runner", "test_step9_30a_v4_adjudication",
                                                "test_step9_30c_v4_aggregation"},
            "may_access_v5": False,
            "may_create_formal_attempt": name in {"test_step9_13a_authorization_infrastructure",
                                                  "test_step9_20a_v3_runner", "test_step9_28_v4_runner"},
            "may_create_authorization": False,
            "may_mutate_historical_artifacts": name in {"test_v1_2_mechanism_validation",
                                                        "test_v1_2_1_mechanism_validation"},
            "identity_scope": identity_scope,
        })
    data = {"artifact_type": "STEP9_51A_EXPLICIT_NON_BENCHMARK_TEST_MANIFEST",
            "step": "9.51a", "module_pattern": "tests/test_*.py",
            "allowlist_is_pinned_in_guard": True, "modules": entries}
    with MANIFEST.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def dry_run(allowed: list[dict], data: dict) -> int:
    excluded = [item for item in data["modules"] if not item["allowed"]]
    count = sum(source_test_count(TEST_DIR / f"{item['module']}.py") for item in allowed)
    print(f"SAFE_TEST_MODULE_COUNT = {len(allowed)}")
    print(f"SAFE_TEST_CASE_COUNT_IF_DISCOVERABLE = {count}")
    print("SAFE_TEST_MODULES = " + ", ".join(item["module"] for item in allowed))
    print(f"EXCLUDED_TEST_MODULES = {len(excluded)}")
    for item in excluded:
        print(f"EXCLUDED {item['module']}: {item['reason']}")
    print("STEP9_30A_SELECTED = NO")
    print("STEP9_30C_SELECTED = NO")
    print("FORMAL_V4_TEST_SELECTED = NO")
    print("AGGREGATION_TEST_SELECTED = NO")
    print("ADJUDICATION_TEST_SELECTED = NO")
    print("V5_TEST_SELECTED = NO")
    print("TEST_SELECTION_AUDIT = PASS")
    return count


def run_tests(allowed: list[dict]) -> unittest.result.TestResult:
    sys.path[:0] = [str(ROOT), str(TEST_DIR)]
    suite = unittest.TestSuite()
    loader = unittest.defaultTestLoader
    for item in allowed:
        suite.addTests(loader.loadTestsFromName(item["module"]))
    return unittest.TextTestRunner(verbosity=2).run(suite)


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--create-manifest", action="store_true")
    action.add_argument("--dry-run", action="store_true")
    action.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.create_manifest:
        create_manifest()
        print(f"Created {MANIFEST.relative_to(ROOT)} (exclusive create).")
        return 0
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    allowed, errors = audit_manifest(data)
    if errors:
        for error in errors:
            print(f"FAIL CLOSED: {error}", file=sys.stderr)
        return 2
    count = dry_run(allowed, data)
    if not args.run:
        return 0
    result = run_tests(allowed)
    print(f"TOTAL_SAFE_TESTS = {result.testsRun}")
    print(f"PASS = {result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)}")
    print(f"FAIL = {len(result.failures)}")
    print(f"ERROR = {len(result.errors)}")
    print(f"SKIP = {len(result.skipped)}")
    if result.testsRun != count:
        print("FAIL CLOSED: runtime test count differs from AST dry-run count", file=sys.stderr)
        return 3
    return 0 if not result.failures and not result.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
