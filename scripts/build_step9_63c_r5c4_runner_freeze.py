"""Build an offline r10 runner freeze candidate; no authorization or execution."""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.v3_runner_identity import IDENTITY_CONFIG_PATH, ROOT, load_identity_config

FREEZE_PATH = ROOT / "evaluation/v1_2_3/step9_63c_r5c5b_runner_freeze_r10.json"
PARENT_FREEZE_PATH = ROOT / "evaluation/v1_2_3/step9_63c_r5c4_runner_freeze_r9.json"
MEMBER_PATHS = (
    "scripts/run_step9_53_v3_identity_adapter.py",
    "scripts/run_step9_63_v3_formal_execution.py",
    "scripts/run_step9_35a_matched_treatment.py",
    "scripts/v3_namespace_allocator.py",
    "scripts/v3_execution_transaction.py",
    "scripts/authorization_lifecycle.py",
    "scripts/issue_step9_63a_r3_authorization.py",
    "scripts/append_only_ledger.py",
    "scripts/preflight_step9_63c_r5_mac_local.py",
    "scripts/preflight_step9_63c_current_mac_local.py",
    "scripts/v3_runner_identity.py",
    "scripts/build_step9_63c_r5c4_runner_freeze.py",
    IDENTITY_CONFIG_PATH,
    "evaluation/v1_2_3/step9_61a_v3_authorization_lifecycle_contract.json",
    "evaluation/v1_2_3/step9_63a_r1_atomic_commit_contract.json",
    "evaluation/v1_2_3/step9_58a_r1_v3_identity_contract.json",
    "evaluation/v1_2_3/step9_51_v3_development_freeze_r1.json",
    "evaluation/v1_2_3/step9_52_v3_pre_evaluation_validation.json",
    "evaluation/v1_2_3/step9_63a_r1_v3_runner_freeze_r7.json",
    "scripts/preflight_step9_62b_mac_local.py",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def nonsecret_model_configuration_matches(root: Path) -> bool:
    """Read only the two frozen non-secret model settings; never load credentials."""
    values: dict[str, str] = {}
    env_path = root / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^\s*(DEEPSEEK_MODEL|DEEPSEEK_BASE_URL)\s*=\s*(.*?)\s*$", line)
            if match:
                value = match.group(2)
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                values[match.group(1)] = value
    model = os.environ.get("DEEPSEEK_MODEL", values.get("DEEPSEEK_MODEL", "deepseek-flash"))
    base_url = os.environ.get("DEEPSEEK_BASE_URL", values.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    return model == "deepseek-flash" and base_url.rstrip("/") == "https://api.deepseek.com"


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                  ensure_ascii=False).encode("utf-8"))


def verify_frozen_inputs(root: Path, identities: dict[str, Any]) -> None:
    from scripts import run_step9_53_v3_identity_adapter as adapter

    agent_sha, agent_match = adapter.current_v3_agent_identity()
    if not agent_match or agent_sha != identities["treatment_agent_sha256"]:
        raise RuntimeError("V3 Agent freeze mismatch")
    benchmark_path = root / identities["benchmark_path"]
    if sha256_file(benchmark_path) != identities["benchmark_sha256"]:
        raise RuntimeError("V4 benchmark SHA mismatch")
    manifest = json.loads((root / "evaluation/benchmarks/benchmark_v4_manifest.json").read_text())
    if (manifest.get("status") != "SEALED_NOT_EVALUATED"
            or manifest.get("case_count") != 40
            or sha256_file(root / "evaluation/benchmarks/benchmark_v4_manifest.json")
            != identities["benchmark_manifest_sha256"]):
        raise RuntimeError("V4 benchmark manifest mismatch")
    # The byte-exact sealed dataset hash is the frozen case-set/order proof;
    # its prior freeze already records the 40-case distribution and fingerprint.
    if (identities.get("case_count") != 40
            or identities.get("task_distribution") != {
                "KNOWLEDGE_QA": 10, "CAUSE_ASSESSMENT": 10,
                "PERSONALIZED_DECISION": 10, "DATA_ANALYSIS": 10}
            or len(identities.get("case_order_fingerprint_sha256", "")) != 64):
        raise RuntimeError("V4 frozen case identity metadata mismatch")
    path_hashes = {
        "scoring_rubric_sha256": "evaluation/benchmark_v1_1_scoring.md",
        "metric_registry_sha256": "evaluation/v1_2_3/step9_26_v4_metric_registry.json",
        "one_shot_rules_sha256": "evaluation/v1_2_3/step9_26_v4_one_shot_rules.md",
        "matched_protocol_sha256": "evaluation/v1_2_3/step9_34a_matched_comparison_protocol.json",
        "baseline_metric_lock_sha256": "evaluation/v1_2_3/step9_34a_baseline_metric_lock.json",
        "claim_policy_sha256": "evaluation/v1_2_3/step9_34a_claim_policy.json",
        "tool_adapter_sha256": "adaptive_agent/tools.py",
        "dependency_lock_sha256": "requirements-lock.txt",
    }
    if any(sha256_file(root / path_hashes[key]) != identities[key] for key in path_hashes):
        raise RuntimeError("frozen evaluation asset mismatch")
    harness = json.loads((root / "evaluation/v1_2_3/step9_13a_harness_freeze.json").read_text())
    scoring = json.loads((root / "evaluation/v1_2_3/step9_11_clean_freeze_manifest.json").read_text())
    for field, inventory, expected in (
        ("new_harness_files", harness, identities["harness_sha256"]),
        ("scoring_files", scoring, identities["scoring_sha256"]),
    ):
        rows = inventory[field]
        payload = "".join(f"{path}\t{digest}\n" for path, digest in sorted(rows))
        if any(sha256_file(root / path) != digest for path, digest in rows) or sha256_bytes(payload.encode()) != expected:
            raise RuntimeError(f"{field} frozen identity mismatch")
    source_rows = json.loads((root / "evaluation/v1_2_3/step9_42_treatment_v2_freeze.json").read_text())["agent_behavior_files"]
    rag_paths = {item["path"] for item in json.loads(
        (root / "evaluation/v1_2_3/step9_32_baseline_agent_freeze.json").read_text()
    )["baseline_rag_config_files"]}
    rag_rows = []
    for path, _ in source_rows:
        if path in rag_paths:
            target = root / ("rag_lib/pdfs" if path == "rag_lib/pdfs/" else path)
            if path == "rag_lib/pdfs/":
                entries = "".join(f"{sha256_file(item)}  {item.relative_to(root)}\n"
                                   for item in sorted(target.glob("*"))
                                   if item.is_file() and not item.name.startswith("._"))
                digest = sha256_bytes(entries.encode())
            else:
                digest = sha256_file(target)
            rag_rows.append([path, digest])
    rag_payload = "".join(f"{path}\t{digest}\n" for path, digest in sorted(rag_rows))
    if sha256_bytes(rag_payload.encode()) != identities["rag_configuration_fingerprint_sha256"]:
        raise RuntimeError("frozen RAG configuration identity mismatch")
    if not nonsecret_model_configuration_matches(root):
        raise RuntimeError("frozen model configuration mismatch")


def build_candidate(root: Path = ROOT) -> dict[str, Any]:
    config = load_identity_config(root)
    candidates = []
    for path in (root / "evaluation/v1_2_3").glob("step9_63c*_runner_freeze*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        revision = value.get("runner_freeze_revision")
        if isinstance(revision, str) and revision.startswith("r") and revision[1:].isdigit():
            candidates.append((int(revision[1:]), path, value))
    if not candidates:
        raise RuntimeError("no Step 9.63c runner freeze lineage found")
    latest_number, latest_path, parent = max(candidates, key=lambda item: item[0])
    next_revision = f"r{latest_number + 1}"
    if (config["runner_freeze_revision"] != next_revision
            or root / config["runner_freeze_path"] != FREEZE_PATH):
        raise RuntimeError("current runner identity pointer is not the next unused revision")
    if latest_path != PARENT_FREEZE_PATH:
        raise RuntimeError("unexpected parent runner freeze path")
    if FREEZE_PATH.exists() or FREEZE_PATH.is_symlink():
        raise RuntimeError("r10 runner freeze target already exists")
    members = [{"path": path, "sha256": sha256_file(root / path)} for path in MEMBER_PATHS]
    rows = "".join(f"{item['path']}\t{item['sha256']}\n" for item in sorted(members, key=lambda x: x["path"]))
    member_aggregate = sha256_bytes(rows.encode("utf-8"))
    identities = parent["bound_identities"]
    if canonical_sha256(identities) != parent["bound_identities_sha256"]:
        raise RuntimeError("historical frozen evaluation identity digest mismatch")
    ledger_path = root / "evaluation/v1_2_3/authorization_lifecycle_events.jsonl"
    ledger_bytes = ledger_path.read_bytes()
    prefix_length = 1161
    prefix_sha = "ca168f6939c4697a7a7bccc0b365b414d9a0e632f40de4242eb0a47e2d985285"
    if (len(ledger_bytes) < prefix_length
            or sha256_bytes(ledger_bytes[:prefix_length]) != prefix_sha):
        raise RuntimeError("append-only lifecycle historical prefix mismatch")
    from scripts.authorization_lifecycle import _events
    _events(ledger_path)
    verify_frozen_inputs(root, identities)
    freeze = {
        "artifact_type": "STEP9_63C_R5C5B_V3_RUNNER_FREEZE_NOT_AUTHORIZATION",
        "step": "9.63c-r5c5b", "runner_freeze_revision": config["runner_freeze_revision"],
        "status": "FROZEN_NOT_AUTHORIZED", "execution_permission": False,
        "supersedes_for_new_authorization_only": str(latest_path.relative_to(root)),
        "parent_runner_freeze_path": str(PARENT_FREEZE_PATH.relative_to(root)),
        "parent_runner_freeze_sha256": sha256_file(PARENT_FREEZE_PATH),
        "runner_path": MEMBER_PATHS[0], "runner_sha256": members[0]["sha256"],
        "identity_adapter_sha256": members[0]["sha256"],
        "formal_entry_runner_path": MEMBER_PATHS[1], "formal_entry_runner_sha256": members[1]["sha256"],
        "parent_runner": {"path": MEMBER_PATHS[2], "sha256": members[2]["sha256"]},
        "namespace_allocator_path": MEMBER_PATHS[3], "namespace_allocator_sha256": members[3]["sha256"],
        "transaction_module_path": MEMBER_PATHS[4], "transaction_module_sha256": members[4]["sha256"],
        "authorization_lifecycle_module_path": MEMBER_PATHS[5], "authorization_lifecycle_module_sha256": members[5]["sha256"],
        "authorization_lifecycle_contract_path": MEMBER_PATHS[13], "authorization_lifecycle_contract_sha256": members[13]["sha256"],
        "transaction_contract_path": MEMBER_PATHS[14], "transaction_contract_sha256": members[14]["sha256"],
        "identity_contract_path": MEMBER_PATHS[15], "identity_contract_sha256": members[15]["sha256"],
        "identity_config_path": IDENTITY_CONFIG_PATH,
        "identity_config_sha256": config["identity_config_sha256"],
        "v3_agent_sha256": parent["v3_agent_sha256"],
        "development_freeze_sha256": parent["development_freeze_sha256"],
        "step9_52_validation_sha256": parent["step9_52_validation_sha256"],
        "bound_identities_sha256": canonical_sha256(identities),
        "bound_identities": identities,
        "single_namespace_authority": "TRANSACTION_RESOLVED_EXECUTION_NAMESPACE",
        "namespace_contract": parent.get("namespace_contract", parent.get("parent_root_contract")),
        "transaction_commit_semantics": parent["transaction_commit_semantics"],
        "historical_lifecycle_prefix": {
            "path": "evaluation/v1_2_3/authorization_lifecycle_events.jsonl",
            "length_bytes": 1161,
            "sha256": "ca168f6939c4697a7a7bccc0b365b414d9a0e632f40de4242eb0a47e2d985285",
        },
        "members": members, "member_count": len(members),
        "member_aggregate_sha256": member_aggregate,
        "authorization_issued": False, "formal_execution_performed": False,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    return freeze


def persist_candidate(freeze: dict[str, Any], root: Path = ROOT) -> str:
    data = (json.dumps(freeze, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd = os.open(FREEZE_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    dir_fd = os.open(FREEZE_PATH.parent, os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    finally:
        os.close(dir_fd)
    return sha256_bytes(data)
