#!/usr/bin/env python3
"""Build the r11 treatment-V3 blind review packet (read-only inputs, exclusive-create outputs).

The packet contains only: the frozen rubric, the frozen adjudication schema, the frozen V4
benchmark, the V3 raw traces and case results (byte copies from the verified run archive),
a V3-only review template, a standard-library validator whose per-record check is copied
verbatim from scripts/v4_adjudication_contract.py, reviewer instructions, MANIFEST and SHA256SUMS.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOLS = Path(__file__).resolve().parent
PACKET = ROOT / "evaluation/v1_2_3/step9_63c_r11_blind_review_packet"
ARCHIVE = ROOT / "evaluation/v1_2_3/step9_63c_r11_run_archive/run_root"
NS = "heldout-v4-treatment-v3-run-9ec9c305cc4de01e6538"
EVALUATION_ID = "heldout-v4-step9_55a-treatment-v3-20260930-01"
ATTEMPT_ID = "attempt-step9_63c_r11-2312daefa1364bfd83ff3948d101c765"
RUN_REL = f"evaluation/v4_runs/{NS}/{EVALUATION_ID}"
SOURCES = {  # packet path -> (source path, pinned sha256)
    "rubric/benchmark_v1_1_scoring.md":
        ("evaluation/benchmark_v1_1_scoring.md", "a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899"),
    "schema/step9_30a_v4_adjudication_schema.json":
        ("evaluation/v1_2_3/step9_30a_v4_adjudication_schema.json", "21367c176f6b070d875a203ff779cfd44e2cb86a4e8956e1f93870fd054834c8"),
    "cases/benchmark_v4_cases.yaml":
        ("evaluation/benchmarks/benchmark_v4_cases.yaml", "8b8c72092fcd7544e69d5d2ecd13610c7bb4c14210fca330698b3e5ab3f01d7f"),
    "v3_run/raw_traces.jsonl":
        (f"evaluation/v1_2_3/step9_63c_r11_run_archive/run_root/{NS}/{EVALUATION_ID}/{ATTEMPT_ID}_raw_traces.jsonl",
         "abd307e0e64730448856c595f134d437a2130bf8ef160a680126cd0067b2a2f5"),
    "v3_run/case_results.jsonl":
        (f"evaluation/v1_2_3/step9_63c_r11_run_archive/run_root/{NS}/{EVALUATION_ID}/{ATTEMPT_ID}_case_results.jsonl",
         "6672f3ef21a20a68776925267896ed4362832aaabc5a16c06546a6b778ef0ba8"),
}
CONTRACT = ("scripts/v4_adjudication_contract.py", "1dc81a9e5da3fece34864b86770d99b73a4f9ca1c212027f1d864b2053e7efc2")
REGISTRY = ("evaluation/v1_2_3/step9_26_v4_metric_registry.json", "de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056")
REVIEW_METHOD = ("single-reviewer per-case trace adjudication; retain each dimension, total, rationale, evidence "
                 "and missing denominator; critical/harmful are separate signals")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pinned(rel: str, expected: str) -> bytes:
    data = (ROOT / rel).read_bytes()
    if sha(data) != expected:
        raise SystemExit(f"SOURCE_SHA_MISMATCH {rel}")
    return data


def write_new(rel: str, data: bytes) -> None:
    path = PACKET / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o644)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def contract_segment() -> tuple[str, list[str]]:
    source = pinned(*CONTRACT).decode("utf-8")
    tree = ast.parse(source)
    wanted_assign = {"DIMENSIONS", "ASK_CATEGORIES", "TOOL_CATEGORIES", "CRITICAL_TYPES"}
    wanted_func = {"_validate_completed_record", "_nonempty_list"}
    parts, names = [], []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) in wanted_assign for t in node.targets):
            parts.append(ast.get_source_segment(source, node)); names.append(node.targets[0].id)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted_func:
            parts.append(ast.get_source_segment(source, node)); names.append(node.name)
    if set(names) != wanted_assign | wanted_func:
        raise SystemExit("CONTRACT_SEGMENT_INCOMPLETE")
    return "\n\n\n".join(parts), names


def jsonl_rows(data: bytes) -> list[tuple[int, bytes, dict]]:
    return [(n, raw, json.loads(raw)) for n, raw in enumerate(data.splitlines(keepends=True), 1) if raw.strip()]


def main() -> int:
    if PACKET.exists():
        print("PACKET_ALREADY_EXISTS")
        return 1
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()
    pinned(*REGISTRY)
    payload = {name: pinned(*src) for name, src in SOURCES.items()}
    for name, data in payload.items():
        write_new(name, data)

    results = jsonl_rows(payload["v3_run/case_results.jsonl"])
    traces = {obj["case_id"]: (n, raw) for n, raw, obj in jsonl_rows(payload["v3_run/raw_traces.jsonl"])}
    unset = {
        "dimension_scores": {k: None for k in ("goal_alignment", "facts_state_integrity", "action_resource_selection",
                                               "evidence_answer_scope", "interaction_efficiency")},
        "total_score": None, "completion_judgment": None, "validity_judgment": None,
        "ask_quality": {"denominator": None, "counts": {k: None for k in ("necessary", "useful_but_optional",
                                                                          "redundant", "irrelevant")}},
        "necessary_ask_preservation": {"acquired_targets": None, "oracle_required_targets": None,
                                       "target_adjudications": None},
        "tool_use_appropriateness": {"RETRIEVE": None, "READ_DIARY": None},
        "critical_failure": {"present": None, "types": None, "supporting_evidence": None},
        "harmful_failure": None,
        "failure_attribution": {"primary_cause": None, "downstream_effects": None, "independent_failure": None,
                                "first_divergence": None, "supporting_evidence": None,
                                "missing_denominator": None, "rationale": None},
    }
    template_lines = []
    for n, raw, result in results:
        tn, traw = traces[result["case_id"]]
        facts = {key: result[key] for key in ("case_id", "task_type", "final_status", "action_path", "ASK_count",
                                              "RETRIEVE_count", "READ_DIARY_count", "turn_count", "step_count",
                                              "tool_calls", "latency_ms", "lineage_ready")}
        facts = {"evaluation_id": EVALUATION_ID, "attempt_id": ATTEMPT_ID, **facts}
        record = {
            "immutable_execution_facts": facts,
            "reviewer_judgments": unset,
            "review_provenance": {"rubric_path": SOURCES["rubric/benchmark_v1_1_scoring.md"][0],
                                  "rubric_sha256": SOURCES["rubric/benchmark_v1_1_scoring.md"][1],
                                  "metric_registry_path": REGISTRY[0], "metric_registry_sha256": REGISTRY[1],
                                  "reviewer": None, "review_method": REVIEW_METHOD, "reviewed_at": None},
            "execution_provenance": {
                "case_result": {"path": f"{RUN_REL}/{ATTEMPT_ID}_case_results.jsonl", "line_number": n,
                                "line_sha256": sha(raw)},
                "raw_trace": {"path": f"{RUN_REL}/{ATTEMPT_ID}_raw_traces.jsonl", "line_number": tn,
                              "line_sha256": sha(traw)},
            },
        }
        template_lines.append(json.dumps(record, ensure_ascii=False, sort_keys=True))
    write_new("review_template.jsonl", ("\n".join(template_lines) + "\n").encode("utf-8"))

    segment, names = contract_segment()
    header = ('#!/usr/bin/env python3\n"""Blind-review validator for the r11 treatment-V3 packet (standard library only).\n\n'
              f"The block below is copied verbatim from {CONTRACT[0]} (SHA-256 {CONTRACT[1]}):\n"
              f"{', '.join(names)}.\n" '"""\n\n\n')
    body = (TOOLS / "blind_validator_body.py").read_text(encoding="utf-8")
    write_new("validate_review.py", (header + segment + "\n" + body).encode("utf-8"))
    write_new("README_REVIEWER.md", (TOOLS / "blind_review_instructions.md").read_bytes())

    files = sorted(p.relative_to(PACKET).as_posix() for p in PACKET.rglob("*")
                   if p.is_file() and not p.name.startswith("._"))
    manifest = {
        "artifact_type": "R11_TREATMENT_V3_BLIND_REVIEW_PACKET",
        "built_at_utc": datetime.now(timezone.utc).isoformat(), "repository_head_at_build": head,
        "evaluation_id": EVALUATION_ID, "attempt_id": ATTEMPT_ID,
        "files": {name: {"sha256": sha((PACKET / name).read_bytes()), "bytes": (PACKET / name).stat().st_size,
                         "source": ({"path": SOURCES[name][0], "sha256": SOURCES[name][1], "copy": "byte-identical"}
                                    if name in SOURCES else "generated for this packet")} for name in files},
        "validator_contract_source": {"path": CONTRACT[0], "sha256": CONTRACT[1], "copied_verbatim": names},
        "excluded_by_design": ["any output, review, aggregate or comparison of any other run",
                               "V3 lineage classification (pre-registration D3)", "metric registry files (definitions quoted in README_REVIEWER.md)",
                               "attempt ledger, transaction journal, namespace marker"],
    }
    write_new("MANIFEST.json", (json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    sums = "".join(f"{sha((PACKET / name).read_bytes())}  {name}\n" for name in files + ["MANIFEST.json"])
    write_new("SHA256SUMS", sums.encode("utf-8"))
    print(json.dumps({"packet": PACKET.relative_to(ROOT).as_posix(), "files": files + ["MANIFEST.json", "SHA256SUMS"],
                      "head": head}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
