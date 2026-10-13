#!/usr/bin/env python3
"""Reviewer-sensitivity arm B: build a neutral blind review packet for the Step 9.28 run.

Same structure, rubric, schema, benchmark and validator logic as the V3 blind packet. The only
byte change to the run files is the top-level "evaluation_id" value, replaced by a neutral ID; the
mapping (original <-> neutral, per-line hashes) is written OUTSIDE the packet. Instructions and
validator are produced from the V3 sources by literal text substitutions that change only paths,
titles and examples, never a review rule. Exclusive-create outputs; inputs read-only.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOLS = Path(__file__).resolve().parent
OUT = ROOT / "evaluation/v1_2_3"
PACKET = OUT / "step9_63c_r11_baseline_blind_packet"
MAPPING = OUT / "step9_63c_r11_baseline_blind_mapping.json"
V3_PACKET = OUT / "step9_63c_r11_blind_review_packet"
RUN_FREEZE = OUT / "step9_30a_v4_run_input_freeze.json"
ORIG_EVAL = "heldout-v4-step9_28-20260925-01"
ORIG_ATTEMPT = "heldout-v4-step9_28-20260925-01-attempt-step9_29b-5370d36a64d84a3da4f2585e9b57055a"
RUN_DIR = f"evaluation/v4_runs/{ORIG_EVAL}"
NEUTRAL_EVAL = "blind-review-run-01"
NEUTRAL_ATTEMPT = "blind-review-attempt-01"
FIELD_OLD = f'"evaluation_id": "{ORIG_EVAL}"'
FIELD_NEW = f'"evaluation_id": "{NEUTRAL_EVAL}"'
SHARED = {  # copied byte-identical from the V3 packet (which itself copied the frozen files)
    "rubric/benchmark_v1_1_scoring.md": "a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899",
    "schema/step9_30a_v4_adjudication_schema.json": "21367c176f6b070d875a203ff779cfd44e2cb86a4e8956e1f93870fd054834c8",
    "cases/benchmark_v4_cases.yaml": "8b8c72092fcd7544e69d5d2ecd13610c7bb4c14210fca330698b3e5ab3f01d7f",
}
CONTRACT = ("scripts/v4_adjudication_contract.py", "1dc81a9e5da3fece34864b86770d99b73a4f9ca1c212027f1d864b2053e7efc2")
REGISTRY = ("evaluation/v1_2_3/step9_26_v4_metric_registry.json", "de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056")
RUBRIC_REL = "evaluation/benchmark_v1_1_scoring.md"
REVIEW_METHOD = ("single-reviewer per-case trace adjudication; retain each dimension, total, rationale, evidence "
                 "and missing denominator; critical/harmful are separate signals")
# Instruction substitutions: (old, new). Each must occur; none changes a review rule.
README_SUBS = [
    ("# 盲审说明：treatment-V3 逐案评审（Step 9.63c-r11）", "# 盲审说明：逐案评审"),
    ("本说明是 FINAL 预注册的一部分；", "本说明是评审预注册的一部分；"),
    ("`v3_run/", "`run/"),
    ("output/v3_adjudication.jsonl", "output/adjudication.jsonl"),
    ('例如 `"Codex AI reviewer (<model id / version>)"`，或 `"Claude (<model id>), fresh session"`',
     '例如 `"<评审者名称> (<model id / version>), fresh session"`'),
    ("依据：预注册决定 D4，以及冻结对照协议中的 lineage 规则", "依据：评审预注册，以及冻结对照协议中的 lineage 规则"),
    ("（预注册决定 D4）", "（评审预注册）"),
    ("（预注册决定 D6）", "（评审预注册）"),
]
VALIDATOR_SUBS = [
    ('RAW = PACKET / "v3_run/raw_traces.jsonl"', 'RAW = PACKET / "run/raw_traces.jsonl"'),
    ('RESULTS = PACKET / "v3_run/case_results.jsonl"', 'RESULTS = PACKET / "run/case_results.jsonl"'),
    ("# Packet-specific checks (r11 FINAL pre-registration). Standard library only.", "# Packet-specific checks. Standard library only."),
]
BANNED = [r"(?i)baseline", r"基线", r"9\.28", r"9_28", r"step9_2[89]", r"step9_29b", r"(?<![0-9a-f])29b(?![0-9a-f])", r"(?i)codex", r"(?i)\bv3\b", r"(?i)v3_",
          r"(?i)(?<!INDIVIDUALIZED_)treatment", r"(?i)\br11\b", r"heldout-v4-step9", r"5370d36a64d84a3da4f2585e9b57055a", r"4e2bffea0d7eaa9299074a960df84a1806b3ae9d4930662929abc58ca5b2ae79", r"7c9d4ba6c7b649e69a64f9b9e68175db", r"(?<![0-9a-f])20260925(?![0-9a-f])"]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_new(rel: str, data: bytes) -> None:
    path = PACKET / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o644)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def substitute(text: str, subs) -> str:
    for old, new in subs:
        if old not in text:
            raise SystemExit(f"SUBSTITUTION_SOURCE_MISSING: {old[:60]}")
        text = text.replace(old, new)
    return text


def banned_hits(text: str) -> list[str]:
    return [p for p in BANNED if re.search(p, text)]


def main() -> int:
    if PACKET.exists() or MAPPING.exists():
        print("ALREADY_EXISTS")
        return 1
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    freeze = json.loads(RUN_FREEZE.read_text(encoding="utf-8"))
    pinned = {item["path"]: item["sha256"] for item in freeze["artifact_files"]}
    originals = {}
    for kind in ("case_results", "raw_traces"):
        rel = f"{RUN_DIR}/{ORIG_ATTEMPT}_{kind}.jsonl"
        data = (ROOT / rel).read_bytes()
        if pinned.get(rel) != sha(data):
            raise SystemExit(f"BASELINE_RUN_FILE_SHA_MISMATCH {rel}")
        originals[kind] = (rel, data)

    neutral = {}
    line_map = {}
    for kind, (rel, data) in originals.items():
        text = data.decode("utf-8")
        if text.count(FIELD_OLD) != 40 or text.count(ORIG_EVAL) != 40:
            raise SystemExit(f"UNEXPECTED_IDENTIFIER_COUNT {kind}")
        new = text.replace(FIELD_OLD, FIELD_NEW).encode("utf-8")
        if ORIG_EVAL in new.decode("utf-8"):
            raise SystemExit("IDENTIFIER_REMAINS")
        neutral[kind] = new
        olds, news = data.splitlines(keepends=True), new.splitlines(keepends=True)
        if len(olds) != len(news):
            raise SystemExit("LINE_COUNT_CHANGED")
        for n, (o, w) in enumerate(zip(olds, news), 1):
            if not o.strip():
                continue
            obj_o, obj_w = json.loads(o), json.loads(w)
            obj_w["evaluation_id"] = obj_o["evaluation_id"]
            if obj_o != obj_w:
                raise SystemExit(f"CONTENT_CHANGED_BEYOND_IDENTIFIER {kind}:{n}")
            line_map.setdefault(obj_o["case_id"], {})[kind] = {
                "line_number": n, "original_line_sha256": sha(o), "neutral_line_sha256": sha(w)}

    for name, digest in SHARED.items():
        data = (V3_PACKET / name).read_bytes()
        if sha(data) != digest:
            raise SystemExit(f"SHARED_FILE_SHA_MISMATCH {name}")
        write_new(name, data)
    write_new("run/raw_traces.jsonl", neutral["raw_traces"])
    write_new("run/case_results.jsonl", neutral["case_results"])

    results = [(n, raw, json.loads(raw)) for n, raw in enumerate(neutral["case_results"].splitlines(keepends=True), 1) if raw.strip()]
    traces = {json.loads(raw)["case_id"]: (n, raw) for n, raw in enumerate(neutral["raw_traces"].splitlines(keepends=True), 1) if raw.strip()}
    v3_template = [json.loads(line) for line in (V3_PACKET / "review_template.jsonl").read_text(encoding="utf-8").splitlines()]
    unset = v3_template[0]["reviewer_judgments"]
    if [t["immutable_execution_facts"]["case_id"] for t in v3_template] != [r["case_id"] for _, _, r in results]:
        raise SystemExit("CASE_ORDER_DIFFERS_FROM_V3_TEMPLATE")
    lines = []
    for n, raw, result in results:
        tn, traw = traces[result["case_id"]]
        facts = {"evaluation_id": NEUTRAL_EVAL, "attempt_id": NEUTRAL_ATTEMPT,
                 **{k: result[k] for k in ("case_id", "task_type", "final_status", "action_path", "ASK_count", "RETRIEVE_count",
                                           "READ_DIARY_count", "turn_count", "step_count", "tool_calls", "latency_ms", "lineage_ready")}}
        lines.append(json.dumps({
            "immutable_execution_facts": facts, "reviewer_judgments": unset,
            "review_provenance": {"rubric_path": RUBRIC_REL, "rubric_sha256": SHARED["rubric/benchmark_v1_1_scoring.md"],
                                  "metric_registry_path": REGISTRY[0], "metric_registry_sha256": REGISTRY[1],
                                  "reviewer": None, "review_method": REVIEW_METHOD, "reviewed_at": None},
            "execution_provenance": {"case_result": {"path": "run/case_results.jsonl", "line_number": n, "line_sha256": sha(raw)},
                                     "raw_trace": {"path": "run/raw_traces.jsonl", "line_number": tn, "line_sha256": sha(traw)}},
        }, ensure_ascii=False, sort_keys=True))
    write_new("review_template.jsonl", ("\n".join(lines) + "\n").encode("utf-8"))

    v3_validator = (V3_PACKET / "validate_review.py").read_text(encoding="utf-8")
    header_end = v3_validator.index('"""\n\n\n') + len('"""\n\n\n')
    header = ('#!/usr/bin/env python3\n"""Blind-review validator (standard library only).\n\n'
              f"The block below is copied verbatim from {CONTRACT[0]} (SHA-256 {CONTRACT[1]}).\n" '"""\n\n\n')
    validator = header + substitute(v3_validator[header_end:], VALIDATOR_SUBS)
    # The check logic must be identical: same AST for every function, ignoring the changed path constants.
    def functions(src):
        return {n.name: ast.dump(n) for n in ast.parse(src).body if isinstance(n, ast.FunctionDef)}
    if functions(validator) != functions(v3_validator):
        raise SystemExit("VALIDATOR_LOGIC_DIFFERS")
    write_new("validate_review.py", validator.encode("utf-8"))
    readme = substitute((V3_PACKET / "README_REVIEWER.md").read_text(encoding="utf-8"), README_SUBS)
    write_new("README_REVIEWER.md", readme.encode("utf-8"))

    for name in ("README_REVIEWER.md", "review_template.jsonl", "validate_review.py"):
        hits = banned_hits((PACKET / name).read_text(encoding="utf-8"))
        if hits:
            raise SystemExit(f"BANNED_IDENTIFIER_IN_{name}: {hits}")

    files = sorted(p.relative_to(PACKET).as_posix() for p in PACKET.rglob("*") if p.is_file() and not p.name.startswith("._"))
    manifest = {
        "artifact_type": "BLIND_REVIEW_PACKET",
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_id": NEUTRAL_EVAL, "attempt_id": NEUTRAL_ATTEMPT,
        "files": {name: {"sha256": sha((PACKET / name).read_bytes()), "bytes": (PACKET / name).stat().st_size} for name in files},
        "validator_contract_source": {"path": CONTRACT[0], "sha256": CONTRACT[1]},
        "note": "Run identity is neutral; provenance is held outside this packet.",
    }
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n"
    if banned_hits(manifest_text):
        raise SystemExit("BANNED_IDENTIFIER_IN_MANIFEST")
    write_new("MANIFEST.json", manifest_text.encode("utf-8"))
    sums = "".join(f"{sha((PACKET / name).read_bytes())}  {name}\n" for name in files + ["MANIFEST.json"])
    write_new("SHA256SUMS", sums.encode("utf-8"))

    mapping = {
        "artifact_type": "R11_REVIEWER_SENSITIVITY_B_IDENTITY_MAPPING", "keep_outside_packet": True,
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "repository_head_at_build": head,
        "packet": {"path": PACKET.relative_to(ROOT).as_posix(), "SHA256SUMS_sha256": sha((PACKET / "SHA256SUMS").read_bytes())},
        "neutral_to_original": {NEUTRAL_EVAL: ORIG_EVAL, NEUTRAL_ATTEMPT: ORIG_ATTEMPT},
        "original_files": {kind: {"path": rel, "sha256": sha(data), "pinned_by": RUN_FREEZE.relative_to(ROOT).as_posix()}
                           for kind, (rel, data) in originals.items()},
        "packet_files": {f"run/{kind}.jsonl": sha(neutral[kind]) for kind in neutral},
        "byte_change": f"only the top-level field {FIELD_OLD} -> {FIELD_NEW} (40 lines per file); every other byte identical (verified per line)",
        "per_case_lines": line_map,
        "shared_files_copied_from_v3_packet": SHARED,
        "readme_substitutions": README_SUBS, "validator_substitutions": VALIDATOR_SUBS,
        "validator_logic_identical_to_v3_packet": True,
    }
    fd = os.open(MAPPING, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(json.dumps(mapping, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"packet": PACKET.relative_to(ROOT).as_posix(), "files": files + ["MANIFEST.json", "SHA256SUMS"],
                      "SHA256SUMS_sha256": mapping["packet"]["SHA256SUMS_sha256"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
