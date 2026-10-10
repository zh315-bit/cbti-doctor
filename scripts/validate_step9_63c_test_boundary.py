#!/usr/bin/env python3
"""Versioned Step 9.63c test boundary manifest: builder and fail-closed auditor.

The Step 9.51a manifest, validator and test are pinned by the frozen development
freeze (step9_51_v3_development_freeze_r1.json) and stay byte-identical. This module
adds a new, versioned manifest covering every current ``tests/test_*.py`` module. It
reuses the pinned Step 9.51a allowlist and flag vocabulary unchanged; it never widens
the allowlist. Every module carries a risk level derived mechanically from its source.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

from scripts.validate_step9_51a_test_boundary import (
    MANIFEST as STEP9_51A_MANIFEST, REQUIRED_FLAGS, RISK_FLAGS, SAFE_ALLOWLIST, risky_call_errors,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "evaluation/v1_2_3/step9_63c_r5c10ad_test_boundary_manifest.json"
TEST_DIR = ROOT / "tests"
STEP9_51A_MANIFEST_SHA256 = "a639ab7e674227f5c676071da6a6186572138fc88d0c899a9cf3fbaa6a59169d"
RISK_LEVELS = ("LOW", "MEDIUM", "HIGH")
# Production modules that own formal identity, authorization, transactions or preflight.
HIGH_RISK_MODULES = (
    "run_step9_53_v3_identity_adapter", "run_step9_63_v3_formal_execution", "run_step9_35a_matched_treatment",
    "v3_execution_transaction", "v3_namespace_allocator", "authorization_lifecycle", "v3_runner_identity",
    "issue_step9_", "preflight_step9_", "build_step9_63c_", "run_step9_43a_treatment_v2",
    "run_step9_53", "run_step9_28_v4_heldout", "run_step9_20a", "run_step9_12_frozen_evaluation",
)
CREATE_AUTHORIZATION_CALLS = {"issue_authorization", "retire_unconsumed_authorization", "issue"}
CREATE_ATTEMPT_CALLS = {"begin_and_commit", "claim_attempt", "reserve_namespace", "claim_invocation"}
FORMAL_WRITE_CALLS = {"write_artifact", "write_preflight", "write_attestation", "write_exclusive",
                      "persist_candidate", "append_terminal_event", "initialize_registry"}


def _source_facts(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            calls.add(fn.attr if isinstance(fn, ast.Attribute) else fn.id if isinstance(fn, ast.Name) else "")
    scripts_imports = {name for name in imported if name.startswith("scripts.")}
    return {
        "high_risk_imports": sorted(n for n in scripts_imports if any(m in n for m in HIGH_RISK_MODULES)),
        "scripts_imports": sorted(scripts_imports),
        "subprocess": "subprocess" in imported,
        "reads_repository_evaluation": "evaluation/" in text,
        "calls": calls, "text": text,
    }


def derived_entry(name: str) -> dict:
    """Mechanical classification; identical input bytes always give identical output."""
    facts = _source_facts(TEST_DIR / f"{name}.py")
    if facts["high_risk_imports"] or facts["subprocess"]:
        level = "HIGH"
    elif facts["scripts_imports"] or facts["reads_repository_evaluation"]:
        level = "MEDIUM"
    else:
        level = "LOW"
    text, calls = facts["text"], facts["calls"]
    return {
        "risk_level": level,
        "risk_evidence": {"high_risk_imports": facts["high_risk_imports"], "uses_subprocess": facts["subprocess"],
                          "reads_repository_evaluation": facts["reads_repository_evaluation"]},
        "may_execute_agent": any(n.startswith("adaptive_agent") for n in _imports(text)),
        "may_execute_rag": "rag_client" in text or "rag_lib" in text,
        "may_execute_model": "create_chat_model(" in text,
        "may_access_v4": "v4_runs" in text or "benchmark_v4" in text,
        "may_aggregate": "aggregate_records" in calls or "aggregate_completed" in calls,
        "may_adjudicate": "adjudicate" in calls,
        "may_write_formal_artifacts": bool(calls & FORMAL_WRITE_CALLS),
        "may_execute_formal_v4": "execute_formal" in calls,
        "may_access_v5": "benchmark_v5" in text,
        "may_create_formal_attempt": bool(calls & CREATE_ATTEMPT_CALLS),
        "may_create_authorization": bool(calls & CREATE_AUTHORIZATION_CALLS),
        "may_mutate_historical_artifacts": False,
    }


def _imports(text: str) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def build_manifest() -> dict:
    legacy = json.loads(STEP9_51A_MANIFEST.read_text(encoding="utf-8"))
    legacy_rows = {row["module"]: row for row in legacy["modules"]}
    modules = []
    for name in sorted(p.stem for p in TEST_DIR.glob("test_*.py")):
        derived = derived_entry(name)
        if name in legacy_rows:
            row = dict(legacy_rows[name])  # Step 9.51a decisions carried over verbatim
            row["origin"] = "STEP9_51A_VERBATIM"
        else:
            row = {key: derived[key] for key in REQUIRED_FLAGS}
            row.update({"module": name, "path": f"tests/{name}.py", "allowed": False,
                        "purpose": "Added after Step 9.51a; outside the pinned safe allowlist.",
                        "reason": "Not in the pinned Step 9.51a allowlist; run only under the guarded Step 9.63c harness.",
                        "identity_scope": "PROHIBITED_OR_HISTORICAL", "origin": "STEP9_63C_DERIVED"})
        row["risk_level"] = derived["risk_level"]
        row["risk_evidence"] = derived["risk_evidence"]
        modules.append(row)
    return {
        "artifact_type": "STEP9_63C_TEST_BOUNDARY_MANIFEST", "version": 1, "step": "9.63c-r5c10ad",
        "module_pattern": "tests/test_*.py",
        "supersedes_inventory_of": {"path": str(STEP9_51A_MANIFEST.relative_to(ROOT)),
                                    "sha256": STEP9_51A_MANIFEST_SHA256, "preserved_unchanged": True},
        "allowlist_source": "SAFE_ALLOWLIST pinned in scripts/validate_step9_51a_test_boundary.py (unchanged)",
        "risk_rule": ("HIGH: imports a formal identity/authorization/transaction/preflight/freeze module or uses "
                      "subprocess; MEDIUM: imports other scripts modules or reads repository evaluation paths; LOW: otherwise."),
        "modules": modules,
    }


def audit_manifest(data: dict) -> list[str]:
    errors = []
    if hashlib.sha256(STEP9_51A_MANIFEST.read_bytes()).hexdigest() != STEP9_51A_MANIFEST_SHA256:
        errors.append("Step 9.51a manifest bytes changed")
    entries = data.get("modules")
    if not isinstance(entries, list):
        return errors + ["manifest modules must be a list"]
    by_name = {row.get("module"): row for row in entries if isinstance(row, dict)}
    if len(by_name) != len(entries):
        errors.append("manifest contains duplicate or malformed module entries")
    discovered = {p.stem for p in TEST_DIR.glob("test_*.py")}
    if set(by_name) != discovered:
        errors.append(f"manifest inventory differs from tests/test_*.py: missing={sorted(discovered - set(by_name))} "
                      f"extra={sorted(set(by_name) - discovered)}")
    allowed = {name for name, row in by_name.items() if row.get("allowed") is True}
    if allowed != SAFE_ALLOWLIST & discovered:
        errors.append("allowed module set differs from the pinned Step 9.51a allowlist")
    legacy = {row["module"]: row for row in json.loads(STEP9_51A_MANIFEST.read_text(encoding="utf-8"))["modules"]}
    for name, row in by_name.items():
        if row.get("path") != f"tests/{name}.py":
            errors.append(f"{name}: path mismatch")
        missing = [flag for flag in REQUIRED_FLAGS if not isinstance(row.get(flag), bool)]
        if missing:
            errors.append(f"{name}: missing boolean metadata {', '.join(missing)}")
        if row.get("risk_level") not in RISK_LEVELS or not isinstance(row.get("risk_evidence"), dict):
            errors.append(f"{name}: missing risk level or evidence")
        elif name in discovered and row["risk_level"] != derived_entry(name)["risk_level"]:
            errors.append(f"{name}: risk level differs from mechanical derivation")
        if not row.get("reason"):
            errors.append(f"{name}: missing reason")
        if name in legacy and any(row.get(key) != value for key, value in legacy[name].items()):
            errors.append(f"{name}: Step 9.51a decision was not carried over verbatim")
        if row.get("allowed") is True:
            risky = [flag for flag in RISK_FLAGS if row.get(flag) is True]
            if risky:
                errors.append(f"{name}: disallowed risk metadata {', '.join(risky)}")
            if name in discovered:
                errors.extend(risky_call_errors(TEST_DIR / f"{name}.py"))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create", action="store_true", help="write the manifest if it does not exist")
    args = parser.parse_args(argv)
    if args.create:
        if MANIFEST.exists():
            raise SystemExit(f"refusing to overwrite existing manifest: {MANIFEST}")
        MANIFEST.write_text(json.dumps(build_manifest(), indent=1) + "\n", encoding="utf-8")
    errors = audit_manifest(json.loads(MANIFEST.read_text(encoding="utf-8")))
    print(json.dumps({"manifest": str(MANIFEST.relative_to(ROOT)), "errors": errors}, indent=1))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
