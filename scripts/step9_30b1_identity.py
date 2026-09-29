"""Fail-closed resolution of the frozen Step 9.30b adjudication identity."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ADJUDICATION_REL = "evaluation/v1_2_3/step9_30b_v4_human_adjudication.jsonl"
FREEZE_REL = "evaluation/v1_2_3/step9_30b_v4_human_adjudication_freeze.json"
REPORT_REL = "evaluation/v1_2_3/step9_30b_v4_human_adjudication_report.md"
FAILED_AUDIT_REL = "evaluation/v1_2_3/step9_30c_v4_aggregation_audit.json"
RESOLUTION_REL = "evaluation/v1_2_3/step9_30b1_v4_adjudication_identity_resolution.json"
INPUT_REL = "evaluation/v1_2_3/step9_30c_v4_aggregation_input.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_canonical_input(root: Path, *, requested_sha256: str | None = None) -> dict:
    """Validate canonical path, resolution, current bytes and Step 9.30b freeze.

    The optional requested_sha256 exists to test fail-closed handling of an
    external pin; production aggregation must use the canonical input only.
    """
    input_path = root / INPUT_REL
    resolution_path = root / RESOLUTION_REL
    if not resolution_path.is_file():
        raise RuntimeError("identity resolution artifact missing")
    if not input_path.is_file():
        raise RuntimeError("canonical aggregation input missing")
    resolution = read_json(resolution_path)
    canonical = read_json(input_path)
    if resolution.get("status") != "PASS" or resolution.get("resolution_class") != "EXTERNAL_REQUEST_PIN_ERROR":
        raise RuntimeError("identity resolution is not a passing external pin resolution")
    if canonical.get("status") != "CANONICAL_INPUT_READY_NOT_EXECUTED" or canonical.get("aggregation_authorized_by_this_artifact") is not False:
        raise RuntimeError("canonical input is not a non-executing identity binding")
    if canonical.get("identity_resolution_path") != RESOLUTION_REL:
        raise RuntimeError("canonical input points to a different identity resolution")
    if canonical.get("identity_resolution_sha256") != sha256(resolution_path):
        raise RuntimeError("identity resolution hash mismatch")
    if canonical.get("adjudication_path") != ADJUDICATION_REL or resolution.get("authoritative_adjudication_path") != ADJUDICATION_REL:
        raise RuntimeError("aggregation cannot substitute a different adjudication path")
    adjudication_path = root / ADJUDICATION_REL
    freeze_path = root / FREEZE_REL
    if not adjudication_path.is_file() or not freeze_path.is_file():
        raise RuntimeError("adjudication or Step 9.30b freeze missing")
    actual_hash = sha256(adjudication_path)
    freeze = read_json(freeze_path)
    recorded_hash = freeze.get("adjudication_sha256")
    if freeze.get("validation_status") != "PASS" or freeze.get("case_count") != 40 or actual_hash != recorded_hash:
        raise RuntimeError("adjudication file and Step 9.30b freeze hash mismatch")
    if actual_hash != resolution.get("authoritative_adjudication_sha256"):
        raise RuntimeError("adjudication hash differs from identity resolution")
    if actual_hash != canonical.get("adjudication_sha256"):
        raise RuntimeError("canonical adjudication pin mismatch")
    if requested_sha256 is not None and requested_sha256 != actual_hash:
        raise RuntimeError("external/requested pin mismatch; fail closed")
    if canonical.get("case_count") != 40 or resolution.get("case_count") != 40:
        raise RuntimeError("resolved adjudication case count mismatch")
    if canonical.get("reviewer_type") != "SINGLE_AI_REVIEWER":
        raise RuntimeError("reviewer identity mismatch")
    source_artifacts = resolution.get("source_artifacts")
    expected_sources = {ADJUDICATION_REL, FREEZE_REL, REPORT_REL, FAILED_AUDIT_REL}
    if not isinstance(source_artifacts, list) or {x.get("path") for x in source_artifacts} != expected_sources:
        raise RuntimeError("identity resolution source manifest is incomplete or ambiguous")
    for source in source_artifacts:
        path = root / source["path"]
        if not path.is_file() or sha256(path) != source.get("sha256"):
            raise RuntimeError("identity resolution source artifact hash mismatch")
    return {"adjudication_path": ADJUDICATION_REL, "adjudication_sha256": actual_hash,
            "step9_30b_recorded_sha256": recorded_hash, "case_count": 40,
            "reviewer_type": "SINGLE_AI_REVIEWER"}
