"""Create append-only Step 9.30b1 identity resolution and canonical input."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.step9_30b1_identity import (
    ADJUDICATION_REL, FAILED_AUDIT_REL, FREEZE_REL, INPUT_REL,
    REPORT_REL, RESOLUTION_REL, sha256,
)


def main():
    resolution_path, input_path = ROOT / RESOLUTION_REL, ROOT / INPUT_REL
    if resolution_path.exists() or input_path.exists():
        raise RuntimeError("append-only Step 9.30b1 outputs already exist; refusing overwrite")
    adjudication = ROOT / ADJUDICATION_REL
    freeze_path, report_path, failed_audit_path = ROOT / FREEZE_REL, ROOT / REPORT_REL, ROOT / FAILED_AUDIT_REL
    if not all(p.is_file() for p in (adjudication, freeze_path, report_path, failed_audit_path)):
        raise RuntimeError("required Step 9.30b/9.30c source artifacts missing")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    failed = json.loads(failed_audit_path.read_text(encoding="utf-8"))
    actual = sha256(adjudication)
    recorded = freeze.get("adjudication_sha256")
    requested = failed.get("requested_pinned_sha256")
    if freeze.get("validation_status") != "PASS" or actual != recorded:
        raise RuntimeError("adjudication does not match a passing Step 9.30b freeze; fail closed")
    if actual == requested:
        raise RuntimeError("failed Step 9.30c requested pin does not exhibit the stated mismatch")
    lines = [line for line in adjudication.read_text(encoding="utf-8").splitlines() if line.strip()]
    records = [json.loads(line) for line in lines]
    ids = [r.get("immutable_execution_facts", {}).get("case_id") for r in records]
    if len(records) != 40 or len(set(ids)) != 40:
        raise RuntimeError("frozen adjudication is not exactly 40 unique case records")
    sources = [ADJUDICATION_REL, FREEZE_REL, REPORT_REL, FAILED_AUDIT_REL]
    resolution = {
        "step": "9.30b1", "status": "PASS",
        "authoritative_adjudication_path": ADJUDICATION_REL,
        "authoritative_adjudication_sha256": actual,
        "step9_30b_recorded_sha256": recorded,
        "failed_step9_30c_requested_sha256": requested,
        "file_matches_step9_30b_freeze": True,
        "resolution_class": "EXTERNAL_REQUEST_PIN_ERROR",
        "case_count": 40,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_artifacts": [{"path": rel, "sha256": sha256(ROOT / rel)} for rel in sources],
        "step9_30b_freeze_modified": False,
        "adjudication_modified": False,
        "case_results_modified": False,
        "raw_traces_modified": False,
        "attempt_ledger_modified": False,
        "rubric_modified": False,
        "metric_registry_modified": False,
        "lineage_sidecar_modified": False,
        "v4_rerun": False, "model_called": False, "agent_called": False, "rag_called": False,
        "aggregation_performed": False, "overall_generated": False,
    }
    resolution_bytes = (json.dumps(resolution, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    # Exclusive creation preserves append-only semantics; if later creation
    # fails, the resolution is retained and the input can be recovered only
    # through a separate explicit append-only continuation.
    with resolution_path.open("xb") as stream:
        stream.write(resolution_bytes)
        stream.flush()
    canonical_input = {
        "step": "9.30c", "status": "CANONICAL_INPUT_READY_NOT_EXECUTED",
        "adjudication_path": ADJUDICATION_REL, "adjudication_sha256": actual,
        "identity_resolution_path": RESOLUTION_REL,
        "identity_resolution_sha256": sha256(resolution_path),
        "reviewer_type": "SINGLE_AI_REVIEWER", "case_count": 40,
        "aggregation_authorized_by_this_artifact": False,
        "aggregation_performed": False,
    }
    with input_path.open("x", encoding="utf-8") as stream:
        json.dump(canonical_input, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
    print(json.dumps({"identity_resolution_path": RESOLUTION_REL,
                      "identity_resolution_sha256": sha256(resolution_path),
                      "canonical_input_path": INPUT_REL,
                      "adjudication_sha256": actual,
                      "case_count": 40, "status": "PASS_NOT_AGGREGATED"}, indent=2))


if __name__ == "__main__":
    main()
