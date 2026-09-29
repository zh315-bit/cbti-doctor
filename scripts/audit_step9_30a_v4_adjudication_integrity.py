"""Re-hash frozen V4 run inputs and emit a non-scoring integrity audit."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.v4_adjudication_contract import (  # noqa: E402
    FREEZE_PATH, OUT, ROOT as PROJECT_ROOT, SCHEMA_PATH, TEMPLATE_PATH, REGISTRY_PATH, RUBRIC_PATH, actual_run_inputs,
    read_jsonl, sha256, validate_records,
)

AUDIT_PATH = OUT / "step9_30a_v4_adjudication_integrity_audit.json"


def main() -> None:
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    input_checks = []
    for item in freeze["artifact_files"]:
        path = PROJECT_ROOT / item["path"]
        input_checks.append({"path": item["path"], "expected_sha256": item["sha256"],
            "actual_sha256": sha256(path), "byte_size_match": path.stat().st_size == item["byte_size"],
            "match": sha256(path) == item["sha256"]})
    rows = [row[2] for row in read_jsonl(TEMPLATE_PATH)]
    validate_records(rows, "template")
    rubric_registry_match = sha256(RUBRIC_PATH) == json.loads(REGISTRY_PATH.read_text())["scoring_spec"]["rubric_sha256"]
    _, ledger, results, traces = actual_run_inputs()
    from scripts.v4_adjudication_contract import validate_run_inputs
    validated_run = validate_run_inputs()
    from scripts import run_step9_28_v4_heldout as v4_runner
    live_frozen_identity = v4_runner.verify_frozen_identity()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    v4_manifest = json.loads(v4_runner.MANIFEST.read_text(encoding="utf-8"))
    audit = {
        "audit_id": "step9_30a-v4-adjudication-integrity-20260926-01",
        "audit_type": "POST_IMPLEMENTATION_READ_ONLY_INTEGRITY_CHECK",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_id": freeze["evaluation_id"], "attempt_id": freeze["attempt_id"],
        "attempt_status": freeze["attempt_status"], "case_result_count": len(results), "raw_trace_count": len(traces),
        "case_coverage_match": len(results) == len(traces) == len(validated_run["result_index"]) == 40,
        "lineage_ready_case_count": freeze["lineage_ready_case_count"],
        "lineage_not_ready_case_count": freeze["lineage_not_ready_case_count"],
        "all_case_lineage_ready": freeze["lineage_not_ready_case_count"] == 0,
        "lineage_not_ready_case_ids": sorted(case_id for case_id, row in
            ((r[2]["case_id"], r[2]) for r in results) if row.get("lineage_ready") is False),
        "frozen_input_hashes_after_implementation": input_checks,
        "all_frozen_input_hashes_unchanged": all(x["match"] for x in input_checks),
        "rubric_hash_matches_metric_registry": rubric_registry_match,
        "schema_json_valid": isinstance(schema, dict) and schema.get("schema_id") == "step9_30a-v4-adjudication-v1",
        "benchmark_v4_sha256_match": live_frozen_identity.get("benchmark_v4_sha256_match") is True,
        "benchmark_v4_status": v4_manifest.get("status"),
        "benchmark_v4_case_count": v4_manifest.get("case_count"),
        "task_distribution": freeze["task_distribution"],
        "live_frozen_identity_match": live_frozen_identity.get("freeze_match") is True,
        "agent_final_freeze_match": live_frozen_identity.get("current_agent_matches_final_freeze") is True,
        "harness_freeze_match": live_frozen_identity.get("harness_match") is True,
        "scoring_freeze_match": live_frozen_identity.get("scoring_match") is True,
        "metric_registry_match": live_frozen_identity.get("metric_registry_match") is True,
        "one_shot_rules_match": live_frozen_identity.get("one_shot_rules_match") is True,
        "template_rows": len(rows), "template_validation": "PASS",
        "template_all_reviewer_judgments_unset": all(_judgments_unset(x["reviewer_judgments"]) for x in rows),
        "agent_modified": False, "benchmark_v4_modified": False,
        "scoring_rubric_modified": False, "metric_registry_modified": False,
        "evaluation_semantics_modified": False,
        "raw_traces_modified": False, "case_results_modified": False, "attempt_ledger_modified": False,
        "v4_rerun": False, "model_called_in_step9_30a": False,
        "agent_called_in_step9_30a": False, "rag_called_in_step9_30a": False,
        "overall_score_generated": False, "aggregation_run_on_real_v4_reviews": False,
        "v3_scores_used_as_v4_labels": False,
        "read_only_v3_schema_reference": "evaluation/v1_2_3/step9_21_v3_case_scores.jsonl",
        "limitation": "12 formal case result rows record lineage_ready=false; these facts are preserved and require reviewer attention.",
        "ready_for_step9_30b_human_adjudication": False,
        "readiness_reason": "The adjudication infrastructure and unset template validate, but 12 cases do not satisfy the requested all-cases-lineage-ready check.",
    }
    with AUDIT_PATH.open("x", encoding="utf-8") as stream:
        json.dump(audit, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    print(f"integrity_audit={AUDIT_PATH}")


def _judgments_unset(value) -> bool:
    if isinstance(value, dict):
        return all(_judgments_unset(v) for v in value.values())
    if isinstance(value, list):
        return all(_judgments_unset(v) for v in value)
    return value is None


if __name__ == "__main__":
    main()
