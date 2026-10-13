#!/usr/bin/env python3
"""Pre-registration D3: treatment-V3 lineage provenance classification (read-only inputs).

Applies the Step 9.45a method unchanged: ``derive`` from scripts/forensics_step9_45a_treatment_v2_lineage.py
and ``classify_true_failure_dimensions`` from scripts/step9_30a2_lineage_sidecar.py are imported, not
reimplemented. Inputs are the archived V3 artifacts (SHA-verified). Outputs are exclusive-create and
are NOT part of the blind review packet. No scores are assigned.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.forensics_step9_45a_treatment_v2_lineage import derive  # noqa: E402
from scripts.step9_30a2_lineage_sidecar import classify_true_failure_dimensions  # noqa: E402

NS = "heldout-v4-treatment-v3-run-9ec9c305cc4de01e6538"
EV = "heldout-v4-step9_55a-treatment-v3-20260930-01"
ATT = "attempt-step9_63c_r11-2312daefa1364bfd83ff3948d101c765"
ARCH = ROOT / f"evaluation/v1_2_3/step9_63c_r11_run_archive/run_root/{NS}/{EV}"
RESULTS, TRACES = ARCH / f"{ATT}_case_results.jsonl", ARCH / f"{ATT}_raw_traces.jsonl"
EXPECTED = {RESULTS: "6672f3ef21a20a68776925267896ed4362832aaabc5a16c06546a6b778ef0ba8",
            TRACES: "abd307e0e64730448856c595f134d437a2130bf8ef160a680126cd0067b2a2f5"}
METHOD_SOURCES = {"scripts/forensics_step9_45a_treatment_v2_lineage.py": "4e53adde9a3e55a84c6663fc4a9b5de6a91b5012a39ba87d75f37b543594f3da",
                  "scripts/step9_30a2_lineage_sidecar.py": "e427f1a69848af8a19147c79b1cf951439c29e2393a9f13d1e62de214aafb947"}
OUT = ROOT / "evaluation/v1_2_3"
OUT_SIDECAR = OUT / "step9_63c_r11_v3_lineage_sidecar.jsonl"
OUT_SUMMARY = OUT / "step9_63c_r11_v3_lineage_forensics.json"
DIMENSIONS = ("goal_alignment", "facts_state_integrity", "action_resource_selection",
              "evidence_answer_scope", "interaction_efficiency")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_new(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o644)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def main() -> int:
    for rel, expected in METHOD_SOURCES.items():
        if sha((ROOT / rel).read_bytes()) != expected:
            raise SystemExit(f"METHOD_SOURCE_CHANGED {rel}")
    raw = {}
    for path, expected in EXPECTED.items():
        raw[path] = path.read_bytes()
        if sha(raw[path]) != expected:
            raise SystemExit(f"INPUT_SHA_MISMATCH {path.name}")
    results = [json.loads(l) for l in raw[RESULTS].splitlines() if l.strip()]
    trace_lines = {}
    for n, line in enumerate(raw[TRACES].splitlines(keepends=True), 1):
        if line.strip():
            obj = json.loads(line)
            trace_lines[obj["case_id"]] = (n, line, obj)
    if len(results) != 40 or [r["case_id"] for r in results] != list(trace_lines):
        raise SystemExit("CASE_SET_MISMATCH")

    sidecar = []
    for result in results:
        case_id = result["case_id"]
        n, line, trace = trace_lines[case_id]
        missing, graph = derive(trace)
        formal_ready = result["lineage_ready"]
        if not missing:
            recomputed, root_cause = "COMPLETE", ("NO_FAILURE" if formal_ready else "RUNNER_DERIVATION_BUG")
            status = "COMPLETE_FORMAL" if formal_ready else "COMPLETE_DERIVED"
        elif "MISSING_SEMANTIC_ROOT" in missing:
            recomputed, root_cause, status = "INCOMPLETE", "TRUE_LINEAGE_FAILURE", "INCOMPLETE_FORMAL"
        else:
            recomputed, root_cause, status = "INDETERMINATE", "INDETERMINATE", "INDETERMINATE"
        if recomputed == "COMPLETE":
            dimensions, eligibility = {d: "SCORABLE" for d in DIMENSIONS}, "FULL"
        else:
            evidence = classify_true_failure_dimensions(trace)
            dimensions, eligibility = evidence["dimensions"], evidence["eligibility"]
        if not trace.get("final_answer") and not result.get("answer"):
            eligibility = "NONE"
        sidecar.append({
            "case_id": case_id, "task_type": result["task_type"], "formal_lineage_ready": formal_ready,
            "recomputed_lineage_status": recomputed, "root_cause_class": root_cause,
            "sidecar_lineage_status": status, "lineage_reconstructed": status == "COMPLETE_DERIVED",
            "reason_codes": missing,
            "semantic_root_status": "PRESENT" if graph["semantic_root_ids"] else "MISSING_IN_FORMAL_TRACE",
            "adjudication_lineage_status": "INCOMPLETE" if status in {"INCOMPLETE_FORMAL", "INDETERMINATE"} else "COMPLETE",
            "adjudication_eligibility": eligibility, "dimension_evidence": dimensions,
            "trace_provenance": {"path": TRACES.relative_to(ROOT).as_posix(), "line_number": n, "line_sha256": sha(line)},
            "reviewer_scores_populated": False,
            "use": "provenance metadata only; no score (pre-registration D3/D4); not included in the blind review packet",
        })
    body = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in sidecar).encode("utf-8")
    write_new(OUT_SIDECAR, body)
    summary = {
        "artifact_type": "R11_TREATMENT_V3_LINEAGE_FORENSICS", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "Step 9.45a derive() + Step 9.30a2 classify_true_failure_dimensions(), imported unchanged",
        "method_sources": METHOD_SOURCES, "inputs": {p.relative_to(ROOT).as_posix(): s for p, s in EXPECTED.items()},
        "sidecar": {"path": OUT_SIDECAR.relative_to(ROOT).as_posix(), "sha256": sha(body)},
        "counts": {
            "formal_lineage_ready": dict(Counter(str(r["formal_lineage_ready"]) for r in sidecar)),
            "sidecar_lineage_status": dict(Counter(r["sidecar_lineage_status"] for r in sidecar)),
            "root_cause_class": dict(Counter(r["root_cause_class"] for r in sidecar)),
            "adjudication_eligibility": dict(Counter(r["adjudication_eligibility"] for r in sidecar)),
            "reason_codes": dict(Counter(code for r in sidecar for code in r["reason_codes"])),
        },
        "by_case": {r["case_id"]: [r["sidecar_lineage_status"], r["reason_codes"]] for r in sidecar if r["sidecar_lineage_status"] != "COMPLETE_FORMAL"},
        "not_in_blind_packet": True, "scores_assigned": False,
    }
    write_new(OUT_SUMMARY, (json.dumps(summary, ensure_ascii=False, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps(summary["counts"], indent=1)); print(json.dumps(summary["by_case"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
