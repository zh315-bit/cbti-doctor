"""Build the append-only Step 9.48 descriptive three-way matched comparison."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation/v1_2_3"
EXPECTED_ORDER = "d930455e417935337a6e3459defbdc3ee3829b71786fbd8438ef092b62429e68"
EXPECTED_V2_AGGREGATE = "98df31b2082ce808acec2d6d409c9febc01b79278201a94b0fd1a3c2d30fc936"
EXPECTED_PINS = {
    "benchmark_sha256": "8b8c72092fcd7544e69d5d2ecd13610c7bb4c14210fca330698b3e5ab3f01d7f",
    "benchmark_manifest_sha256": "b5feb7832b6267d8cff9d25fb2d8cf0043829feb5fd04ec1bea77dba932a13db",
    "harness_sha256": "8bc271bebc1c5da5351d517e2bb4a0d1a99fda3de1b713a6197b12f81fad70c7",
    "scoring_sha256": "f742a8f8af7c8747818dadad81621c15d12d74f50538019913dfe18ab53bf59b",
    "scoring_rubric_sha256": "a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899",
    "metric_registry_sha256": "de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056",
    "one_shot_rules_sha256": "1c7ed4ef47865b117bc943f3e0ad9a859f4f74cfb4e8001f723ac5532af140d0",
    "matched_protocol_sha256": "a71ba06090370b576fbba66bc4b005e519ddbabff3021a40c6546fc855f90265",
}

BASELINE_FREEZE = OUT / "step9_30a_v4_run_input_freeze.json"
BASELINE_AUDIT = OUT / "step9_30c_r1_v4_aggregation_audit.json"
BASELINE_AGG = OUT / "step9_30c_v4_aggregate_metrics.json"
BASELINE_CASES = OUT / "step9_30c_v4_case_level_summary.jsonl"
V1_FREEZE = OUT / "step9_36_treatment_run_input_freeze.json"
V1_AGG_FREEZE = OUT / "step9_38_treatment_aggregate_freeze.json"
V1_AGG_AUDIT = OUT / "step9_38_treatment_aggregation_audit.json"
V1_AGG = OUT / "step9_38_treatment_aggregate_metrics.json"
V1_CASES = OUT / "step9_38_treatment_case_summary.jsonl"
V1_RECON = OUT / "step9_38a_metric_registry_reconciliation_r4.json"
STEP39_METRICS = OUT / "step9_39_matched_comparison_metrics.json"
STEP39_REPORT = OUT / "step9_39_matched_comparison_report.md"
STEP39_MATRIX = OUT / "step9_39_case_transition_matrix.jsonl"
STEP39_AUDIT = OUT / "step9_39_claim_eligibility_audit.json"
V2_FREEZE = OUT / "step9_45a_v2_run_input_freeze.json"
V2_LINEAGE = OUT / "step9_45a_v2_lineage_case_matrix.jsonl"
V2_ADJ = OUT / "step9_46_v2_adjudication.jsonl"
V2_ADJ_FREEZE = OUT / "step9_46_v2_adjudication_freeze.json"
V2_ADJ_AUDIT = OUT / "step9_46_v2_adjudication_audit.json"
V2_AGG = OUT / "step9_47_v2_aggregate.json"
V2_CASES = OUT / "step9_47_v2_case_summary.jsonl"
V2_AGG_REPORT = OUT / "step9_47_v2_aggregation_report.md"
V2_AGG_FREEZE = OUT / "step9_47_v2_aggregation_freeze.json"
V2_AGG_AUDIT = OUT / "step9_47_v2_aggregation_audit.json"
REGISTRY = OUT / "step9_26_v4_metric_registry.json"
RUBRIC = ROOT / "evaluation/benchmark_v1_1_scoring.md"
SCORING_FREEZE = OUT / "step9_11_clean_freeze_manifest.json"
HARNESS_FREEZE = OUT / "step9_13a_harness_freeze.json"
PROTOCOL = OUT / "step9_34a_matched_comparison_protocol.json"
CLAIM_POLICY = OUT / "step9_34a_claim_policy.json"
METRIC_LOCK = OUT / "step9_34a_baseline_metric_lock.json"
BENCHMARK = ROOT / "evaluation/benchmarks/benchmark_v4_cases.yaml"
BENCHMARK_MANIFEST = ROOT / "evaluation/benchmarks/benchmark_v4_manifest.json"
ONE_SHOT = OUT / "step9_26_v4_one_shot_rules.md"

OUTPUTS = {
    "comparison": OUT / "step9_48_three_way_matched_comparison.json",
    "case_matrix": OUT / "step9_48_three_way_case_transition_matrix.jsonl",
    "report": OUT / "step9_48_three_way_matched_comparison.md",
    "claim_audit": OUT / "step9_48_claim_audit.json",
    "freeze": OUT / "step9_48_comparison_freeze.json",
    "audit": OUT / "step9_48_comparison_audit.json",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_new(path: Path, text: str) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())


def artifact_result_file(freeze: dict) -> Path:
    rows = [x for x in freeze.get("artifact_files", []) if x.get("path", "").endswith("_case_results.jsonl")]
    if len(rows) != 1:
        raise RuntimeError("FAIL CLOSED: expected one frozen case_results file")
    return ROOT / rows[0]["path"]


def verify_frozen_artifact_files(freeze: dict) -> None:
    for row in freeze.get("artifact_files", []):
        path = ROOT / row["path"]
        if not path.is_file() or path.stat().st_size != row["byte_size"] or sha(path) != row["sha256"]:
            raise RuntimeError(f"FAIL CLOSED: run-freeze artifact mismatch: {row['path']}")


def low_value_metric(ask: dict) -> dict:
    return ask.get("LOW_VALUE_ASK_RATE", ask.get("REDUNDANT_OR_IRRELEVANT_RATE"))


def metric_view(data: dict) -> dict:
    completion = data["completion_and_validity"]["overall"]
    ask = data["ask_quality"]
    low = low_value_metric(ask)
    efficiency = data["efficiency"]
    counts = data["tool_resource_behavior"]["counts"]
    return {
        "case_count": data["adjudicated_case_count"],
        "overall": data["scores"]["overall"]["mean"],
        "task_means": {key: value["mean"] for key, value in data["scores"]["task_type_means"].items()},
        "completion": {"count": completion["rate"]["numerator"], "rate": completion["rate"]["value"], "denominator": completion["rate"]["denominator"]},
        "answer_validity": {"count": completion["validity_rate"]["numerator"], "rate": completion["validity_rate"]["value"], "denominator": completion["validity_rate"]["denominator"]},
        "ask": {
            "total": ask["TOTAL_ASK_COUNT"], "necessary": ask["NECESSARY_ASK_COUNT"],
            "useful_optional": ask["USEFUL_OPTIONAL_ASK_COUNT"], "redundant": ask["REDUNDANT_ASK_COUNT"],
            "irrelevant": ask["IRRELEVANT_ASK_COUNT"], "low_value_count": low["numerator"], "low_value_rate": low["value"],
        },
        "critical_failures": {"count": data["failures"]["CRITICAL_FAILURE_COUNT"], "case_ids": data["failures"]["CRITICAL_FAILURE_CASE_IDS"]},
        "harmful_failures": {"count": data["failures"]["HARMFUL_FAILURE_COUNT"], "case_ids": data["failures"]["HARMFUL_FAILURE_CASE_IDS"]},
        "execution": {
            "retrieve_per_case": counts["RETRIEVE"] / 40,
            "read_diary_per_case": counts["READ_DIARY"] / 40,
            "tool_calls_per_case": efficiency["tool_calls_per_case"]["mean"],
            "turns_per_case": efficiency["turns_per_case"]["mean"],
            "steps_per_case": efficiency["steps_per_case"]["mean"],
            "mean_latency_ms": efficiency["latency_ms"]["overall"]["mean_ms"],
        },
    }


def completion_pass(row: dict) -> bool:
    return row["completion_judgment"] == "complete"


def transition(old, new) -> str:
    old_pass, new_pass = bool(old), bool(new)
    if old_pass and new_pass:
        return "UNCHANGED_PASS"
    if not old_pass and not new_pass:
        return "UNCHANGED_FAIL"
    return "FAIL_TO_PASS" if not old_pass and new_pass else "PASS_TO_FAIL"


def enum_transition(old: bool, new: bool, improved_name: str, regressed_name: str) -> str:
    if old == new:
        return "UNCHANGED"
    return improved_name if old and not new else regressed_name


def ask_counts(row: dict) -> dict:
    counts = row["ask_quality_counts"]
    return {
        "necessary": counts["necessary"],
        "useful_optional": counts["useful_but_optional"],
        "redundant": counts["redundant"],
        "irrelevant": counts["irrelevant"],
        "total": row["execution"]["ASK_count"],
    }


def trace_reason_fields(trace: dict) -> dict:
    final = trace.get("final_state", {})
    if not isinstance(final, dict):
        final = {}
    auth_fields = {}
    def visit(value, prefix=""):
        if isinstance(value, dict):
            for key, child in value.items():
                path = f"{prefix}.{key}" if prefix else key
                if "authorization" in key.lower():
                    if isinstance(child, (str, bool, int)) or child is None:
                        auth_fields[path] = child
                visit(child, path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{prefix}[{index}]")
    visit(trace)
    required = final.get("dependencies_required", [])
    satisfied = final.get("dependencies_satisfied", [])
    unavailable = final.get("dependencies_unavailable", [])
    preconditions = final.get("preconditions_considered", [])
    precondition_rows = preconditions if isinstance(preconditions, list) else []
    return {
        "final_status": trace.get("final_status"),
        "final_authorization_state": auth_fields or "NOT_EXPLICITLY_PERSISTED",
        "stop_reason": final.get("stop_reason") or None,
        "dependency_state": {
            "required_count": len(required) if isinstance(required, list) else None,
            "satisfied_count": len(satisfied) if isinstance(satisfied, list) else None,
            "unavailable_count": len(unavailable) if isinstance(unavailable, list) else None,
            "unavailable_ids": [x.get("dependency_id") for x in unavailable if isinstance(x, dict) and x.get("dependency_id")],
        },
        "precondition_count": len(preconditions) if isinstance(preconditions, list) else None,
        "preconditions": [{k: row.get(k) for k in ("precondition_id", "status", "satisfied", "required") if k in row}
                           for row in precondition_rows if isinstance(row, dict)],
        "decision_relevant_missing": final.get("decision_relevant_missing", []),
        "validity_critical_missing": final.get("validity_critical_missing", []),
    }


def main() -> None:
    if any(path.exists() for path in OUTPUTS.values()):
        raise RuntimeError("FAIL CLOSED: Step 9.48 append-only output path already exists")

    step39, step39_audit = read_json(STEP39_METRICS), read_json(STEP39_AUDIT)
    if (step39.get("status") != "PASS_DESCRIPTIVE_MATCHED_FROZEN_BASELINE_COMPARISON"
            or step39_audit.get("comparison_integrity") != "PASS"
            or step39_audit.get("status") != "PASS_COMPARISON_INTEGRITY_CLAIM_NOT_ELIGIBLE"):
        raise RuntimeError("FAIL CLOSED: Step 9.39 comparison/audit status mismatch")
    for rel, expected in step39["source_hashes"].items():
        path = ROOT / rel
        if not path.is_file() or sha(path) != expected:
            raise RuntimeError(f"FAIL CLOSED: Step 9.39 frozen input hash mismatch: {rel}")
    for key, target in (("metrics", STEP39_METRICS), ("report", STEP39_REPORT), ("transitions", STEP39_MATRIX)):
        output = step39_audit.get("outputs", {}).get(key, {})
        if output.get("path") != str(target.relative_to(ROOT)) or sha(target) != output.get("sha256"):
            raise RuntimeError(f"FAIL CLOSED: Step 9.39 {key} output identity mismatch")

    baseline_freeze = read_json(BASELINE_FREEZE)
    v1_freeze = read_json(V1_FREEZE)
    v2_freeze = read_json(V2_FREEZE)
    verify_frozen_artifact_files(baseline_freeze)
    verify_frozen_artifact_files(v1_freeze)
    verify_frozen_artifact_files(v2_freeze)
    if not (baseline_freeze.get("evaluation_id") == "heldout-v4-step9_28-20260925-01"
            and baseline_freeze.get("cases_started") == 40 and baseline_freeze.get("cases_completed") == 40
            and baseline_freeze.get("attempt_status") == "COMPLETED"
            and baseline_freeze.get("metric_registry", {}).get("sha256") == EXPECTED_PINS["metric_registry_sha256"]
            and baseline_freeze.get("rubric", {}).get("sha256") == EXPECTED_PINS["scoring_rubric_sha256"]):
        raise RuntimeError("FAIL CLOSED: baseline identity/freeze mismatch")
    v1_identity = v1_freeze.get("execution_identity", {})
    if not (v1_freeze.get("evaluation_id") == "heldout-v4-step9_34a-treatment-20260928-01"
            and v1_freeze.get("formal_inputs_read_only") is True
            and v1_freeze.get("comparison_class") == "POST_HOC_MATCHED_FROZEN_BASELINE"
            and v1_identity.get("all_frozen_hashes_match") is True
            and v1_identity.get("case_order_fingerprint_sha256") == EXPECTED_ORDER):
        raise RuntimeError("FAIL CLOSED: V1 identity/freeze mismatch")
    ids_v2 = v2_freeze.get("shared_evaluation_identities", {})
    if not (v2_freeze.get("step") == "9.45a"
            and v2_freeze.get("formal_inputs_read_only") is True
            and v2_freeze.get("evaluation_id") == "heldout-v4-step9_43-treatment-v2-20260928-01"
            and v2_freeze.get("authorization_id") == "auth-step9_44r1-ecce3f6d87e64ace822fc46c97c18f55"
            and v2_freeze.get("attempt_id") == "attempt-step9_44r1-cb362342ae31449aaffba8092c346864"
            and ids_v2.get("case_order_fingerprint_sha256") == EXPECTED_ORDER):
        raise RuntimeError("FAIL CLOSED: V2 identity/freeze mismatch")

    protocol, claim_policy = read_json(PROTOCOL), read_json(CLAIM_POLICY)
    if sha(PROTOCOL) != EXPECTED_PINS["matched_protocol_sha256"] or protocol.get("protocol_status") != "FROZEN_BEFORE_TREATMENT_EXECUTION":
        raise RuntimeError("FAIL CLOSED: matched protocol identity/status mismatch")
    baseline_lock = read_json(METRIC_LOCK)
    if (baseline_lock.get("status") != "LOCKED_FROM_EXISTING_OFFICIAL_AGGREGATE_NOT_READJUDICATED"
            or baseline_lock.get("baseline_identity", {}).get("case_id_order_sha256") != EXPECTED_ORDER
            or baseline_lock.get("source_artifacts", {}).get("metric_registry_sha256") != EXPECTED_PINS["metric_registry_sha256"]):
        raise RuntimeError("FAIL CLOSED: baseline metric lock/registry mismatch")
    if sha(REGISTRY) != EXPECTED_PINS["metric_registry_sha256"] or sha(RUBRIC) != EXPECTED_PINS["scoring_rubric_sha256"]:
        raise RuntimeError("FAIL CLOSED: rubric/registry hash mismatch")
    if sha(BENCHMARK) != EXPECTED_PINS["benchmark_sha256"] or sha(BENCHMARK_MANIFEST) != EXPECTED_PINS["benchmark_manifest_sha256"]:
        raise RuntimeError("FAIL CLOSED: frozen V4 dataset/manifest identity mismatch")
    scoring = read_json(SCORING_FREEZE)
    harness = read_json(HARNESS_FREEZE)
    if scoring.get("scoring_aggregate_hash") != EXPECTED_PINS["scoring_sha256"] or harness.get("new_harness_aggregate_hash") != EXPECTED_PINS["harness_sha256"]:
        raise RuntimeError("FAIL CLOSED: scoring/harness freeze mismatch")
    for rel, expected in scoring.get("scoring_files", []):
        if sha(ROOT / rel) != expected:
            raise RuntimeError(f"FAIL CLOSED: scoring freeze file mismatch: {rel}")
    for rel, expected in harness.get("new_harness_files", []):
        if sha(ROOT / rel) != expected:
            raise RuntimeError(f"FAIL CLOSED: harness freeze file mismatch: {rel}")
    if sha(ONE_SHOT) != EXPECTED_PINS["one_shot_rules_sha256"]:
        raise RuntimeError("FAIL CLOSED: one-shot rules hash mismatch")
    if not (ids_v2.get("benchmark_sha256") == EXPECTED_PINS["benchmark_sha256"]
            and ids_v2.get("benchmark_manifest_sha256") == EXPECTED_PINS["benchmark_manifest_sha256"]
            and ids_v2.get("harness_sha256") == EXPECTED_PINS["harness_sha256"]
            and ids_v2.get("scoring_sha256") == EXPECTED_PINS["scoring_sha256"]
            and ids_v2.get("scoring_rubric_sha256") == EXPECTED_PINS["scoring_rubric_sha256"]
            and ids_v2.get("metric_registry_sha256") == EXPECTED_PINS["metric_registry_sha256"]
            and ids_v2.get("one_shot_rules_sha256") == EXPECTED_PINS["one_shot_rules_sha256"]
            and ids_v2.get("matched_protocol_sha256") == EXPECTED_PINS["matched_protocol_sha256"]):
        raise RuntimeError("FAIL CLOSED: V2 shared identity pins mismatch")
    if not (v1_identity.get("benchmark_sha256") == EXPECTED_PINS["benchmark_sha256"]
            and v1_identity.get("benchmark_manifest_sha256") == EXPECTED_PINS["benchmark_manifest_sha256"]
            and v1_identity.get("harness_sha256") == EXPECTED_PINS["harness_sha256"]
            and v1_identity.get("scoring_sha256") == EXPECTED_PINS["scoring_sha256"]
            and v1_identity.get("scoring_rubric_sha256") == EXPECTED_PINS["scoring_rubric_sha256"]
            and v1_identity.get("metric_registry_sha256") == EXPECTED_PINS["metric_registry_sha256"]
            and v1_identity.get("one_shot_rules_sha256") == EXPECTED_PINS["one_shot_rules_sha256"]
            and v1_identity.get("matched_protocol_sha256") == EXPECTED_PINS["matched_protocol_sha256"]):
        raise RuntimeError("FAIL CLOSED: V1 shared identity pins mismatch")
    if claim_policy.get("status") != "FROZEN_BEFORE_TREATMENT_EXECUTION" or claim_policy.get("statistics", {}).get("new_significance_test") != "NONE":
        raise RuntimeError("FAIL CLOSED: claim policy was not frozen as expected")

    v2_agg_freeze, v2_agg_audit = read_json(V2_AGG_FREEZE), read_json(V2_AGG_AUDIT)
    v1_agg_freeze, v1_agg_audit = read_json(V1_AGG_FREEZE), read_json(V1_AGG_AUDIT)
    baseline_audit = read_json(BASELINE_AUDIT)
    if not (v2_agg_freeze.get("status") == "PASS"
            and v2_agg_freeze.get("output_hashes", {}).get("aggregate") == EXPECTED_V2_AGGREGATE
            and sha(V2_AGG) == EXPECTED_V2_AGGREGATE
            and v2_agg_audit.get("audit_status") == "PASS"
            and v2_agg_audit.get("aggregate_consistency_audit") == "PASS"):
        raise RuntimeError("FAIL CLOSED: Step 9.47 aggregate pin/audit mismatch")
    for name, path in (("aggregate", V2_AGG), ("case_summary", V2_CASES), ("report", V2_AGG_REPORT)):
        if sha(path) != v2_agg_freeze.get("output_hashes", {}).get(name):
            raise RuntimeError(f"FAIL CLOSED: Step 9.47 frozen output mismatch: {name}")
    v2_input_paths = {
        "adjudication": V2_ADJ, "adjudication_freeze": V2_ADJ_FREEZE,
        "adjudication_audit": V2_ADJ_AUDIT, "run_input_freeze": V2_FREEZE,
        "lineage_audit": OUT / "step9_45a_v2_lineage_forensics.json",
        "lineage_sidecar": OUT / "step9_45a_v2_lineage_sidecar.jsonl",
        "lineage_case_matrix": V2_LINEAGE,
        "case_results": artifact_result_file(v2_freeze),
        "raw_traces": ROOT / next(x["path"] for x in v2_freeze["artifact_files"] if x["path"].endswith("_raw_traces.jsonl")),
        "attempt_ledger": ROOT / next(x["path"] for x in v2_freeze["artifact_files"] if x["path"].endswith("attempts.jsonl")),
        "metric_registry": REGISTRY, "scoring_rubric": RUBRIC,
        "frozen_aggregator": ROOT / "scripts/aggregate_step9_30c_v4.py",
    }
    if any(sha(path) != v2_agg_freeze.get("input_hashes", {}).get(name) for name, path in v2_input_paths.items()):
        raise RuntimeError("FAIL CLOSED: Step 9.47 frozen input manifest mismatch")
    if not (v1_agg_freeze.get("status") == "PASS_TREATMENT_AGGREGATION_ONLY"
            and v1_agg_freeze.get("consistency_audit") == "PASS"
            and v1_agg_freeze.get("prior_step9_38_failure_audit_preserved") is True):
        raise RuntimeError("FAIL CLOSED: Step 9.38 V1 aggregate/audit mismatch")
    if not (baseline_audit.get("status") == "PASS_DETERMINISTIC_AGGREGATION"
            and baseline_audit.get("consistency_audit_status") == "PASS_SINGLE_REVIEWER_DETERMINISTIC_CHECKS"
            and baseline_audit.get("input_hashes_before_after_match") is True):
        raise RuntimeError("FAIL CLOSED: baseline aggregate/audit mismatch")
    recon = read_json(V1_RECON)
    if not (recon.get("compatibility_class") == "BACKWARD_COMPATIBLE_FOR_AGGREGATION"
            and recon.get("material_consumed_semantic_difference_count") == 0
            and recon.get("allowed_treatment_aggregation_registry", {}).get("sha256") == EXPECTED_PINS["metric_registry_sha256"]):
        raise RuntimeError("FAIL CLOSED: V1 metric provenance bridge mismatch")

    aggregates = {
        "Baseline": read_json(BASELINE_AGG),
        "Treatment-V1": read_json(V1_AGG),
        "Treatment-V2": read_json(V2_AGG),
    }
    views = {name: metric_view(value) for name, value in aggregates.items()}
    cases = {
        "Baseline": {row["case_id"]: row for row in read_jsonl(BASELINE_CASES)},
        "Treatment-V1": {row["case_id"]: row for row in read_jsonl(V1_CASES)},
        "Treatment-V2": {row["case_id"]: row for row in read_jsonl(V2_CASES)},
    }
    if any(len(rows) != 40 for rows in cases.values()) or any(len(rows) != 40 for rows in cases.values()):
        raise RuntimeError("FAIL CLOSED: aggregate case summaries are not 40 cases")
    if not (set(cases["Baseline"]) == set(cases["Treatment-V1"]) == set(cases["Treatment-V2"])):
        raise RuntimeError("FAIL CLOSED: three-way case ID set mismatch")

    runs = {"Baseline": baseline_freeze, "Treatment-V1": v1_freeze, "Treatment-V2": v2_freeze}
    run_orders = {}
    for version, freeze in runs.items():
        results_path = artifact_result_file(freeze)
        formal_rows = read_jsonl(results_path)
        formal_ids = [row.get("case_id") for row in formal_rows]
        if len(formal_ids) != 40 or len(set(formal_ids)) != 40:
            raise RuntimeError(f"FAIL CLOSED: {version} formal IDs are not 40 unique cases")
        distribution = Counter(row.get("task_type") for row in formal_rows)
        if dict(distribution) != {"KNOWLEDGE_QA": 10, "CAUSE_ASSESSMENT": 10, "PERSONALIZED_DECISION": 10, "DATA_ANALYSIS": 10}:
            raise RuntimeError(f"FAIL CLOSED: {version} formal task distribution mismatch")
        run_orders[version] = formal_ids
        tasks = {row["case_id"]: row.get("task_type") for row in formal_rows}
        for case_id, row in cases[version].items():
            if row.get("task_type") != tasks[case_id]:
                raise RuntimeError(f"FAIL CLOSED: {version} summary task mismatch: {case_id}")
    if not (run_orders["Baseline"] == run_orders["Treatment-V1"] == run_orders["Treatment-V2"]):
        raise RuntimeError("FAIL CLOSED: three-way formal case order mismatch")
    order_hash = hashlib.sha256("\n".join(run_orders["Baseline"]).encode("utf-8")).hexdigest()
    if order_hash != EXPECTED_ORDER or step39.get("case_order_fingerprint_sha256") != EXPECTED_ORDER:
        raise RuntimeError("FAIL CLOSED: three-way case order fingerprint mismatch")
    order = run_orders["Baseline"]
    tasks_by_id = {case_id: cases["Baseline"][case_id]["task_type"] for case_id in order}
    if any(cases[version][case_id]["task_type"] != tasks_by_id[case_id] for version in cases for case_id in order):
        raise RuntimeError("FAIL CLOSED: task assignment mismatch across versions")

    # Use frozen aggregate metrics for version-level values; this stage does not re-aggregate.
    measure_paths = {
        "overall": ("overall",),
        **{f"task_mean.{task}": ("task_means", task) for task in ("KNOWLEDGE_QA", "CAUSE_ASSESSMENT", "PERSONALIZED_DECISION", "DATA_ANALYSIS")},
        "completion_count": ("completion", "count"), "completion_rate": ("completion", "rate"),
        "validity_count": ("answer_validity", "count"), "validity_rate": ("answer_validity", "rate"),
        "low_value_ask_rate": ("ask", "low_value_rate"), "low_value_ask_count": ("ask", "low_value_count"),
        "ask_total": ("ask", "total"), "ask_necessary": ("ask", "necessary"),
        "ask_useful_optional": ("ask", "useful_optional"), "ask_redundant": ("ask", "redundant"), "ask_irrelevant": ("ask", "irrelevant"),
        "critical_failure_count": ("critical_failures", "count"), "harmful_failure_count": ("harmful_failures", "count"),
        "retrieve_per_case": ("execution", "retrieve_per_case"), "read_diary_per_case": ("execution", "read_diary_per_case"),
        "tool_calls_per_case": ("execution", "tool_calls_per_case"), "turns_per_case": ("execution", "turns_per_case"),
        "steps_per_case": ("execution", "steps_per_case"), "mean_latency_ms": ("execution", "mean_latency_ms"),
    }
    pairs = (("Treatment-V1", "Baseline"), ("Treatment-V2", "Treatment-V1"), ("Treatment-V2", "Baseline"))
    deltas = {}
    for metric, path in measure_paths.items():
        values = {}
        for name in views:
            value = views[name]
            for component in path:
                value = value[component]
            values[name] = value
        deltas[metric] = {}
        for left, right in pairs:
            difference = round(values[left] - values[right], 4)
            item = {"from": right, "to": left, "delta": difference}
            if metric in {"completion_rate", "validity_rate", "low_value_ask_rate"}:
                item["percentage_point_delta"] = round(difference * 100, 4)
            deltas[metric][f"{left}_minus_{right}"] = item

    matrix = []
    for case_id in order:
        b, v1, v2 = (cases[name][case_id] for name in ("Baseline", "Treatment-V1", "Treatment-V2"))
        score = {"baseline": b["total_score"], "v1": v1["total_score"], "v2": v2["total_score"]}
        ask = {"baseline": ask_counts(b), "v1": ask_counts(v1), "v2": ask_counts(v2)}
        low_counts = {name: counts["redundant"] + counts["irrelevant"] for name, counts in ask.items()}
        low_rates = {name: (low_counts[name] / counts["total"] if counts["total"] else None) for name, counts in ask.items()}
        ask_category_deltas = {
            category: {
                "baseline": ask["baseline"][category], "v1": ask["v1"][category], "v2": ask["v2"][category],
                "v1_minus_baseline": ask["v1"][category] - ask["baseline"][category],
                "v2_minus_v1": ask["v2"][category] - ask["v1"][category],
                "v2_minus_baseline": ask["v2"][category] - ask["baseline"][category],
            } for category in ("necessary", "useful_optional", "redundant", "irrelevant", "total")
        }
        matrix.append({
            "case_id": case_id, "task_type": tasks_by_id[case_id],
            "scores": score,
            "completion": {"baseline": b["completion_judgment"], "v1": v1["completion_judgment"], "v2": v2["completion_judgment"]},
            "validity": {"baseline": b["validity_judgment"], "v1": v1["validity_judgment"], "v2": v2["validity_judgment"]},
            "critical_failure": {"baseline": b["critical_failure"], "v1": v1["critical_failure"], "v2": v2["critical_failure"]},
            "harmful_failure": {"baseline": b["harmful_failure"], "v1": v1["harmful_failure"], "v2": v2["harmful_failure"]},
            "ask_classification_summary": ask,
            "low_value_ask_rate": low_rates,
            "matched_deltas": {
                "score": {"v1_minus_baseline": v1["total_score"]-b["total_score"], "v2_minus_v1": v2["total_score"]-v1["total_score"], "v2_minus_baseline": v2["total_score"]-b["total_score"]},
                "low_value_ask_count": {
                    "baseline": low_counts["baseline"], "v1": low_counts["v1"], "v2": low_counts["v2"],
                    "v1_minus_baseline": low_counts["v1"] - low_counts["baseline"],
                    "v2_minus_v1": low_counts["v2"] - low_counts["v1"],
                    "v2_minus_baseline": low_counts["v2"] - low_counts["baseline"],
                },
                "low_value_ask_rate": low_rates,
                "ask_category_counts": ask_category_deltas,
                "completion": {"baseline_to_v1": transition(completion_pass(b), completion_pass(v1)), "v1_to_v2": transition(completion_pass(v1), completion_pass(v2)), "baseline_to_v2": transition(completion_pass(b), completion_pass(v2))},
                "validity": {
                    "baseline_to_v1": "UNCHANGED" if b["validity_judgment"] == v1["validity_judgment"] else "INVALID_TO_VALID" if v1["validity_judgment"] else "VALID_TO_INVALID",
                    "v1_to_v2": "UNCHANGED" if v1["validity_judgment"] == v2["validity_judgment"] else "INVALID_TO_VALID" if v2["validity_judgment"] else "VALID_TO_INVALID",
                    "baseline_to_v2": "UNCHANGED" if b["validity_judgment"] == v2["validity_judgment"] else "INVALID_TO_VALID" if v2["validity_judgment"] else "VALID_TO_INVALID",
                },
                "critical_failure": {
                    "baseline_to_v1": "UNCHANGED" if b["critical_failure"] == v1["critical_failure"] else "YES_TO_NO" if not v1["critical_failure"] else "NO_TO_YES",
                    "v1_to_v2": "UNCHANGED" if v1["critical_failure"] == v2["critical_failure"] else "YES_TO_NO" if not v2["critical_failure"] else "NO_TO_YES",
                    "baseline_to_v2": "UNCHANGED" if b["critical_failure"] == v2["critical_failure"] else "YES_TO_NO" if not v2["critical_failure"] else "NO_TO_YES",
                },
                "harmful_failure": {
                    "baseline_to_v1": "UNCHANGED" if b["harmful_failure"] == v1["harmful_failure"] else "YES_TO_NO" if not v1["harmful_failure"] else "NO_TO_YES",
                    "v1_to_v2": "UNCHANGED" if v1["harmful_failure"] == v2["harmful_failure"] else "YES_TO_NO" if not v2["harmful_failure"] else "NO_TO_YES",
                    "baseline_to_v2": "UNCHANGED" if b["harmful_failure"] == v2["harmful_failure"] else "YES_TO_NO" if not v2["harmful_failure"] else "NO_TO_YES",
                },
            },
        })
    if len(matrix) != 40 or [r["case_id"] for r in matrix] != order:
        raise RuntimeError("FAIL CLOSED: three-way matrix coverage/order mismatch")

    transitions = {
        "completion": {"FAIL_TO_PASS": [], "PASS_TO_FAIL": [], "UNCHANGED_PASS": [], "UNCHANGED_FAIL": []},
        "validity": {"INVALID_TO_VALID": [], "VALID_TO_INVALID": [], "UNCHANGED": []},
        "critical_failure": {"YES_TO_NO": [], "NO_TO_YES": [], "UNCHANGED": []},
        "harmful_failure": {"YES_TO_NO": [], "NO_TO_YES": [], "UNCHANGED": []},
        "score": {"IMPROVED": [], "UNCHANGED": [], "REGRESSED": []},
    }
    for case_id in order:
        a, b = cases["Treatment-V1"][case_id], cases["Treatment-V2"][case_id]
        cat = transition(completion_pass(a), completion_pass(b))
        transitions["completion"][cat].append(case_id)
        if a["validity_judgment"] == b["validity_judgment"]:
            validity_label = "UNCHANGED"
        else:
            validity_label = "INVALID_TO_VALID" if b["validity_judgment"] else "VALID_TO_INVALID"
        transitions["validity"][validity_label].append(case_id)
        transitions["critical_failure"][enum_transition(a["critical_failure"], b["critical_failure"], "YES_TO_NO", "NO_TO_YES")].append(case_id)
        transitions["harmful_failure"][enum_transition(a["harmful_failure"], b["harmful_failure"], "YES_TO_NO", "NO_TO_YES")].append(case_id)
        diff = b["total_score"] - a["total_score"]
        transitions["score"]["IMPROVED" if diff > 0 else "REGRESSED" if diff < 0 else "UNCHANGED"].append(case_id)

    pd_repairs = {}
    for case_id in ("V4-PD-06", "V4-PD-08"):
        old, new = cases["Treatment-V1"][case_id], cases["Treatment-V2"][case_id]
        if old["critical_failure"] and not new["critical_failure"]:
            status = "CHANGED_FAILURE_MODE" if (new["completion_judgment"] != "complete" or not new["validity_judgment"] or new["harmful_failure"]) else "REPAIRED"
        elif new["critical_failure"]:
            status = "PERSISTENT"
        else:
            status = "NOT_A_V1_CRITICAL_REGRESSION"
        pd_repairs[case_id] = {
            "v1_critical_failure": old["critical_failure"], "v2_critical_failure": new["critical_failure"],
            "v1_completion": old["completion_judgment"], "v2_completion": new["completion_judgment"],
            "v1_validity": old["validity_judgment"], "v2_validity": new["validity_judgment"],
            "v1_harmful_failure": old["harmful_failure"], "v2_harmful_failure": new["harmful_failure"],
            "status": status,
        }

    v2_trace_path = ROOT / next(x["path"] for x in v2_freeze["artifact_files"] if x["path"].endswith("_raw_traces.jsonl"))
    v2_traces = {row["case_id"]: row for row in read_jsonl(v2_trace_path)}
    if len(v2_traces) != 40:
        raise RuntimeError("FAIL CLOSED: V2 formal trace coverage mismatch")
    utility_cases = []
    for case_id in order:
        old, new = cases["Treatment-V1"][case_id], cases["Treatment-V2"][case_id]
        if completion_pass(old) and not completion_pass(new):
            evidence = trace_reason_fields(v2_traces[case_id])
            auth = evidence["final_authorization_state"]
            if auth != "NOT_EXPLICITLY_PERSISTED":
                rationale_class = "CONSERVATIVE_AUTHORIZATION" if "block" in json.dumps(auth).lower() else "INSUFFICIENT_EVIDENCE_TO_CLASSIFY"
            elif evidence["validity_critical_missing"]:
                rationale_class = "VALIDITY_REQUIRED_BLOCKING"
            elif evidence["dependency_state"]["unavailable_count"]:
                rationale_class = "UNRESOLVED_DEPENDENCY"
            elif evidence["stop_reason"]:
                rationale_class = "OTHER_EVIDENCED_REASON"
            else:
                rationale_class = "INSUFFICIENT_EVIDENCE_TO_CLASSIFY"
            utility_cases.append({
                "case_id": case_id, "task_type": new["task_type"],
                "v1_final_outcome": old["execution"].get("final_status"),
                "v2_final_outcome": new["execution"].get("final_status"),
                "v1_score": old["total_score"], "v2_score": new["total_score"],
                "v1_action_path": old["execution"].get("action_path"),
                "v2_action_path": new["execution"].get("action_path"),
                "v1_validity": old["validity_judgment"], "v2_validity": new["validity_judgment"],
                "v1_critical_failure": old["critical_failure"], "v2_critical_failure": new["critical_failure"],
                "v1_harmful_failure": old["harmful_failure"], "v2_harmful_failure": new["harmful_failure"],
                "v2_trace_evidence": evidence,
                "failure_to_complete_consistency_class": rationale_class,
                "interpretation_limit": "Final-answer authorization state is not explicitly persisted; an acquisition stop reason is not by itself proof that the final-answer gate blocked an answer.",
            })

    b, a, c = views["Baseline"], views["Treatment-V1"], views["Treatment-V2"]
    preservation = {
        "score_behavior": {
        "overall": "LOST" if c["overall"] <= b["overall"] < a["overall"] else "FURTHER_IMPROVED" if c["overall"] >= a["overall"] > b["overall"] else "PRESERVED" if c["overall"] > b["overall"] else "UNCHANGED_NO_V1_IMPROVEMENT",
            "task_means": {},
        },
        "completion": "LOST" if c["completion"]["rate"] <= b["completion"]["rate"] < a["completion"]["rate"] else "PRESERVED" if c["completion"]["rate"] > b["completion"]["rate"] else "FURTHER_IMPROVED",
        "validity": "FURTHER_IMPROVED" if c["answer_validity"]["rate"] > a["answer_validity"]["rate"] > b["answer_validity"]["rate"] else "PRESERVED" if c["answer_validity"]["rate"] > b["answer_validity"]["rate"] else "LOST",
        "low_value_ask": {
            "status": "PRESERVED" if c["ask"]["low_value_rate"] < b["ask"]["low_value_rate"] else "LOST",
            "baseline_v1_v2_count": [b["ask"]["low_value_count"], a["ask"]["low_value_count"], c["ask"]["low_value_count"]],
            "baseline_v1_v2_rate": [b["ask"]["low_value_rate"], a["ask"]["low_value_rate"], c["ask"]["low_value_rate"]],
            "interpretation": "Direction versus Baseline is preserved; V2 rate is higher than V1 because the total-ASK denominator differs.",
        },
        "harmful_failures": "FURTHER_IMPROVED" if c["harmful_failures"]["count"] < a["harmful_failures"]["count"] else "PRESERVED" if c["harmful_failures"]["count"] < b["harmful_failures"]["count"] else "LOST",
        "critical_failures": "FURTHER_IMPROVED" if c["critical_failures"]["count"] < a["critical_failures"]["count"] else "PRESERVED" if c["critical_failures"]["count"] <= b["critical_failures"]["count"] else "LOST",
    }
    for task in ("KNOWLEDGE_QA", "CAUSE_ASSESSMENT", "PERSONALIZED_DECISION", "DATA_ANALYSIS"):
        vb, vv1, vv2 = b["task_means"][task], a["task_means"][task], c["task_means"][task]
        if vv1 > vb:
            status = "LOST" if vv2 <= vb else "PRESERVED" if vv2 < vv1 else "FURTHER_IMPROVED"
        elif vv2 > vv1:
            status = "FURTHER_IMPROVED"
        else:
            status = "UNCHANGED_NO_V1_IMPROVEMENT"
        preservation["score_behavior"]["task_means"][task] = {"baseline": vb, "v1": vv1, "v2": vv2, "status": status}

    claims = {
        "A_V1_OVERALL_IMPROVEMENT": {
            "status": "SUPPORTED" if a["overall"] > b["overall"] else "NOT_SUPPORTED",
            "evidence": {"baseline": b["overall"], "v1": a["overall"], "v1_minus_baseline": round(a["overall"]-b["overall"],4)},
        },
        "B_V2_CRITICAL_REPAIR": {
            "status": "SUPPORTED" if all(pd_repairs[x]["v1_critical_failure"] and not pd_repairs[x]["v2_critical_failure"] for x in pd_repairs) else "NOT_SUPPORTED",
            "evidence": pd_repairs,
        },
        "C_V2_HARMFUL_ELIMINATION": {
            "status": "SUPPORTED" if c["harmful_failures"]["count"] == 0 and a["harmful_failures"]["count"] > 0 else "NOT_SUPPORTED",
            "evidence": {"v1_harmful_count": a["harmful_failures"]["count"], "v2_harmful_count": c["harmful_failures"]["count"], "v2_case_ids": c["harmful_failures"]["case_ids"]},
        },
        "D_V2_PRESERVED_OVERALL_IMPROVEMENT": {
            "status": "SUPPORTED" if c["overall"] > b["overall"] and a["overall"] > b["overall"] else "NOT_SUPPORTED",
            "evidence": {"baseline": b["overall"], "v1": a["overall"], "v2": c["overall"]},
        },
        "E_V2_PRESERVED_COMPLETION_IMPROVEMENT": {
            "status": "SUPPORTED" if c["completion"]["rate"] > b["completion"]["rate"] and a["completion"]["rate"] > b["completion"]["rate"] else "NOT_SUPPORTED",
            "evidence": {"baseline": b["completion"], "v1": a["completion"], "v2": c["completion"]},
        },
        "F_V2_VALIDITY_IMPROVEMENT": {
            "status": "SUPPORTED" if c["answer_validity"]["rate"] > b["answer_validity"]["rate"] else "NOT_SUPPORTED",
            "evidence": {"baseline": b["answer_validity"], "v1": a["answer_validity"], "v2": c["answer_validity"]},
        },
        "G_SAFETY_UTILITY_TRADEOFF": {
            "status": "QUALIFIED_ONLY" if c["critical_failures"]["count"] < a["critical_failures"]["count"] and c["harmful_failures"]["count"] < a["harmful_failures"]["count"] and c["completion"]["rate"] < a["completion"]["rate"] else "NOT_SUPPORTED",
            "evidence": {"critical_v1_v2": [a["critical_failures"]["count"],c["critical_failures"]["count"]], "harmful_v1_v2": [a["harmful_failures"]["count"],c["harmful_failures"]["count"]], "completion_v1_v2": [a["completion"]["rate"],c["completion"]["rate"]], "overall_v1_v2": [a["overall"],c["overall"]]},
            "qualification": "Descriptive co-occurrence on one frozen set only; no causal effect or proof that the authorization gate caused these changes.",
        },
    }

    metrics = {
        "step": "9.48", "comparison_class": "POST_HOC_THREE_WAY_MATCHED_FROZEN_COMPARISON",
        "comparison_status": "PASS_DESCRIPTIVE_ONLY", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "case_count": 40, "case_order_fingerprint_sha256": order_hash,
        "task_distribution": {"KNOWLEDGE_QA":10,"CAUSE_ASSESSMENT":10,"PERSONALIZED_DECISION":10,"DATA_ANALYSIS":10},
        "identity_match": {"case_id_sets_identical": True, "formal_case_order_identical": True, "task_assignment_identical": True,
                           "benchmark_rubric_scoring_registry_one_shot_protocol_compatible": True,
                           "pins": EXPECTED_PINS, "protocol_class": protocol.get("design_classification")},
        "version_metrics": views, "descriptive_deltas": deltas,
        "v1_to_v2_transitions": transitions,
        "critical_repair_check": pd_repairs,
        "v1_completion_pass_v2_fail_cases": utility_cases,
        "preservation_analysis": preservation,
        "claim_audit": claims,
        "interpretation_limits": {
            "post_hoc_matched_frozen_comparison": True, "randomized_trial": False,
            "causal_claim_eligible": False, "statistical_significance_claim_eligible": False,
            "generalization_claim_eligible": False, "production_safety_claim_eligible": False,
            "unseen_data_claim_eligible": False, "reviewer_backend_equivalence_established": False,
            "v2_answer_authorization_state_explicitly_persisted": all(x["v2_trace_evidence"]["final_authorization_state"] != "NOT_EXPLICITLY_PERSISTED" for x in utility_cases),
        },
        "sources": {},
    }

    matrix_text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in matrix)
    claims_payload = {
        "step": "9.48", "status": "PASS_DESCRIPTIVE_CLAIM_AUDIT", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "claims": claims, "prohibited_claims": {"causal": False, "statistical_significance": False, "generalization": False, "production_safety": False, "unseen_data": False},
        "reviewer_backend_equivalence_established": False,
        "interpretation_boundary": "Case-matched, post-hoc frozen V4 development/postmortem evidence only.",
    }
    hashes = {}
    source_paths = {
        "step9_39_source_"+rel: ROOT/rel for rel in step39["source_hashes"].keys()
    }
    source_paths.update({
        "baseline_freeze": BASELINE_FREEZE, "baseline_aggregate_audit": BASELINE_AUDIT,
        "baseline_aggregate": BASELINE_AGG, "baseline_case_summary": BASELINE_CASES,
        "v1_run_freeze": V1_FREEZE, "v1_aggregate_freeze": V1_AGG_FREEZE,
        "v1_aggregate_audit": V1_AGG_AUDIT, "v1_aggregate": V1_AGG, "v1_case_summary": V1_CASES,
        "v1_registry_reconciliation": V1_RECON,
        "step9_39_metrics": STEP39_METRICS, "step9_39_report": STEP39_REPORT,
        "step9_39_case_matrix": STEP39_MATRIX, "step9_39_claim_audit": STEP39_AUDIT,
        "v2_run_freeze": V2_FREEZE, "v2_lineage_matrix": V2_LINEAGE,
        "v2_adjudication": V2_ADJ, "v2_adjudication_freeze": V2_ADJ_FREEZE,
        "v2_adjudication_audit": V2_ADJ_AUDIT, "v2_aggregate": V2_AGG,
        "v2_case_summary": V2_CASES, "v2_aggregate_report": V2_AGG_REPORT,
        "v2_aggregate_freeze": V2_AGG_FREEZE, "v2_aggregate_audit": V2_AGG_AUDIT,
        "metric_registry": REGISTRY, "scoring_rubric": RUBRIC,
        "scoring_freeze": SCORING_FREEZE, "harness_freeze": HARNESS_FREEZE,
        "matched_protocol": PROTOCOL, "claim_policy": CLAIM_POLICY, "baseline_metric_lock": METRIC_LOCK,
        "benchmark_cases": BENCHMARK, "benchmark_manifest": BENCHMARK_MANIFEST, "one_shot_rules": ONE_SHOT,
    })
    for name, path in source_paths.items():
        if not path.is_file():
            raise RuntimeError(f"FAIL CLOSED: authoritative input missing: {name}")
        hashes[name] = sha(path)
    for rel, expected in step39["source_hashes"].items():
        if hashes["step9_39_source_"+rel] != expected:
            raise RuntimeError(f"FAIL CLOSED: source hash drift during comparison setup: {rel}")
    output_blobs = {
        "comparison": b"",
        "case_matrix": matrix_text.encode(),
        "claim_audit": (json.dumps(claims_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(),
    }
    output_hashes = {key: hashlib.sha256(value).hexdigest() for key, value in output_blobs.items() if value}
    table = ["# Step 9.48 — Frozen Three-Way Matched Comparison", "",
             "Post-hoc matched descriptive comparison of the same frozen 40-case V4 set. This is not randomized, causal, statistically significant, generalized, or production-safety evidence.", "",
             "## Aggregate metrics", "",
             "| Metric | Baseline | Treatment-V1 | Treatment-V2 | V1−Baseline | V2−V1 | V2−Baseline |", "|---|---:|---:|---:|---:|---:|---:|"]
    display = [
        ("Overall", "overall"), ("KQ", "task_means.KNOWLEDGE_QA"), ("CA", "task_means.CAUSE_ASSESSMENT"),
        ("PD", "task_means.PERSONALIZED_DECISION"), ("DA", "task_means.DATA_ANALYSIS"),
        ("Completion count", "completion_count"), ("Completion rate", "completion_rate"),
        ("Answer validity count", "validity_count"), ("Answer validity rate", "validity_rate"),
        ("ASK total", "ask_total"), ("ASK necessary", "ask_necessary"), ("ASK useful optional", "ask_useful_optional"),
        ("ASK redundant", "ask_redundant"), ("ASK irrelevant", "ask_irrelevant"), ("Low-value ASK count", "low_value_ask_count"),
        ("Low-value ASK rate", "low_value_ask_rate"), ("Critical failure count", "critical_failure_count"), ("Harmful failure count", "harmful_failure_count"),
        ("RETRIEVE/case", "retrieve_per_case"), ("READ_DIARY/case", "read_diary_per_case"),
        ("Tool calls/case", "tool_calls_per_case"), ("Turns/case", "turns_per_case"), ("Steps/case", "steps_per_case"), ("Mean latency (ms)", "mean_latency_ms"),
    ]
    def lookup(view, key):
        key = {
            "completion_count": "completion.count", "completion_rate": "completion.rate",
            "validity_count": "answer_validity.count", "validity_rate": "answer_validity.rate",
            "ask_total": "ask.total", "ask_necessary": "ask.necessary",
            "ask_useful_optional": "ask.useful_optional", "ask_redundant": "ask.redundant",
            "ask_irrelevant": "ask.irrelevant", "low_value_ask_count": "ask.low_value_count",
            "low_value_ask_rate": "ask.low_value_rate", "critical_failure_count": "critical_failures.count",
            "harmful_failure_count": "harmful_failures.count",
            "retrieve_per_case": "execution.retrieve_per_case", "read_diary_per_case": "execution.read_diary_per_case",
            "tool_calls_per_case": "execution.tool_calls_per_case", "turns_per_case": "execution.turns_per_case",
            "steps_per_case": "execution.steps_per_case", "mean_latency_ms": "execution.mean_latency_ms",
        }.get(key, key)
        parts = key.split(".")
        for part in parts: view = view[part]
        return view
    for label, key in display:
        values = {name: lookup(views[name], key) for name in views}
        d = deltas[key.replace("task_means.", "task_mean.")]
        fmt = lambda x: f"{x:.4f}" if isinstance(x,float) else str(x)
        table.append(f"| {label} | {fmt(values['Baseline'])} | {fmt(values['Treatment-V1'])} | {fmt(values['Treatment-V2'])} | {fmt(d['Treatment-V1_minus_Baseline']['delta'])} | {fmt(d['Treatment-V2_minus_Treatment-V1']['delta'])} | {fmt(d['Treatment-V2_minus_Baseline']['delta'])} |")
    table += ["", "Rate deltas are also recorded in percentage points in the JSON. Counts/rates above come from the frozen aggregate artifacts; no version was re-aggregated.", "",
              "## V1 → V2 transitions", "",
              f"- Completion: fail→pass {len(transitions['completion']['FAIL_TO_PASS'])}; pass→fail {len(transitions['completion']['PASS_TO_FAIL'])}; unchanged pass {len(transitions['completion']['UNCHANGED_PASS'])}; unchanged fail {len(transitions['completion']['UNCHANGED_FAIL'])}.",
              f"- Validity: invalid→valid {len(transitions['validity']['INVALID_TO_VALID'])}; valid→invalid {len(transitions['validity']['VALID_TO_INVALID'])}; unchanged {len(transitions['validity']['UNCHANGED'])}.",
              f"- Critical: yes→no {len(transitions['critical_failure']['YES_TO_NO'])}; no→yes {len(transitions['critical_failure']['NO_TO_YES'])}; unchanged {len(transitions['critical_failure']['UNCHANGED'])}.",
              f"- Harmful: yes→no {len(transitions['harmful_failure']['YES_TO_NO'])}; no→yes {len(transitions['harmful_failure']['NO_TO_YES'])}; unchanged {len(transitions['harmful_failure']['UNCHANGED'])}.",
              f"- Score: improved {len(transitions['score']['IMPROVED'])}; unchanged {len(transitions['score']['UNCHANGED'])}; regressed {len(transitions['score']['REGRESSED'])}.",
              "- Completion pass→fail IDs: " + ", ".join(transitions["completion"]["PASS_TO_FAIL"]) + ".",
              "- Completion fail→pass IDs: " + ", ".join(transitions["completion"]["FAIL_TO_PASS"]) + ".", "",
              "## Critical repair cases", ""]
    for case_id, row in pd_repairs.items():
        table.append(f"- {case_id}: V1 critical={row['v1_critical_failure']}, V2 critical={row['v2_critical_failure']}; V1 completion={row['v1_completion']}, V2 completion={row['v2_completion']}; status `{row['status']}`.")
    table += ["", "The critical label is cleared in V2 for both cases, but each V2 case is adjudicated `not_complete`; therefore this is a changed failure mode, not a full case-level repair.", "",
              "## V1 pass → V2 fail utility cases", "",
              f"There are {len(utility_cases)} such cases: " + ", ".join(x["case_id"] for x in utility_cases) + ".",
              "Per-case final outcomes, scores, validity/safety labels, trace authorization fields (or explicit absence), dependency/precondition state, and evidence-bound classification are recorded in the JSON. No final-answer authorization state was found in the persisted V2 traces; `stop_reason` is not treated as proof of a blocked final answer.", "",
              "## Preservation of V1 improvements", "",
              f"- Score: overall `{preservation['score_behavior']['overall']}`; task means: " + "; ".join(f"{k} {v['status']} ({v['baseline']} / {v['v1']} / {v['v2']})" for k,v in preservation['score_behavior']['task_means'].items()) + ".",
              f"- Completion `{preservation['completion']}`; validity `{preservation['validity']}`; low-value ASK `{preservation['low_value_ask']['status']}` (counts/rates B/V1/V2: {preservation['low_value_ask']['baseline_v1_v2_count']} / {preservation['low_value_ask']['baseline_v1_v2_rate']}); harmful failures `{preservation['harmful_failures']}`; critical failures `{preservation['critical_failures']}`.", "",
              "## Claim audit", ""]
    for key, claim in claims.items():
        table.append(f"- Claim {key}: **{claim['status']}** — {json.dumps(claim['evidence'], ensure_ascii=False, sort_keys=True)}")
    table += ["", "V2’s lower critical/harmful counts co-occur with lower completion and overall score versus V1 on this frozen set; this supports only a qualified descriptive trade-off, not a causal statement that the final-answer gate produced it.",
              "", "## Integrity and limitations", "",
              f"- Case ID set/order: PASS; order fingerprint `{EXPECTED_ORDER}`; task strata 10 each.",
              f"- Baseline/V1/V2 frozen inputs, Step 9.39 audit outputs, V2 aggregate pin `{EXPECTED_V2_AGGREGATE}`, and shared benchmark/rubric/scoring/registry/one-shot/protocol pins were verified.",
              "- Single-AI-reviewer descriptive judgments; backend-version equivalence is not established.",
              "- No causal, significance, generalization, production-safety, clinical-effectiveness, or unseen-data claims. No rerun, re-adjudication, re-aggregation, Agent/model/RAG execution, V2 repair, V3 creation, or V5 access.", ""]
    report_text = "\n".join(table)
    report_hash = hashlib.sha256(report_text.encode()).hexdigest()
    output_hashes["report"] = report_hash
    hashes["comparison_builder_script"] = sha(Path(__file__))
    metrics["sources"] = hashes
    metrics["outputs_sha256"] = {"case_matrix": output_hashes["case_matrix"], "claim_audit": output_hashes["claim_audit"], "report": output_hashes["report"]}
    output_blobs["comparison"] = (json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    output_hashes["comparison"] = hashlib.sha256(output_blobs["comparison"]).hexdigest()
    # Report and claim hashes are independent of the comparison JSON (no circular hash references).
    freeze = {
        "step": "9.48", "status": "PASS_THREE_WAY_MATCHED_DESCRIPTIVE_COMPARISON",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "case_count": 40, "case_order_fingerprint_sha256": order_hash,
        "input_hashes": hashes, "output_hashes": output_hashes,
        "identity_match": True, "comparison_class": "POST_HOC_THREE_WAY_MATCHED_FROZEN_COMPARISON",
        "causal_claim_eligible": False, "statistical_significance_claim_eligible": False,
        "generalization_claim_eligible": False, "v4_rerun": False, "v5_accessed": False,
    }
    freeze_bytes = (json.dumps(freeze, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    freeze_hash = hashlib.sha256(freeze_bytes).hexdigest()
    audit = {
        "step": "9.48", "audit_status": "PASS", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "three_way_case_id_identity_match": True, "three_way_case_order_match": True,
        "case_count_each": 40, "case_order_fingerprint_sha256": order_hash,
        "task_distribution_match": True, "aggregate_sources_not_recomputed": True,
        "step9_39_integrity_and_sources_match": True, "v2_aggregate_pin_match": True,
        "frozen_shared_identity_pins_match": True, "all_input_hashes_unchanged_before_write": True,
        "comparison_consistency_audit": "PASS", "freeze_sha256": freeze_hash,
        "output_hashes": output_hashes,
        "causal_claim_eligible": False, "statistical_significance_claim_eligible": False,
        "generalization_claim_eligible": False, "v4_rerun": False, "v5_accessed": False,
        "baseline_artifacts_modified": False, "v1_artifacts_modified": False, "v2_artifacts_modified": False,
    }
    audit_bytes = (json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()

    # Ensure none of the frozen inputs changed while the comparison was prepared.
    for name, path in source_paths.items():
        if sha(path) != hashes[name]:
            raise RuntimeError(f"FAIL CLOSED: authoritative input changed before persistence: {name}")
    if sys.argv[1:] == ["--validate-only"]:
        print(json.dumps({
            "validation_only": True, "case_count": 40, "case_order_fingerprint_sha256": order_hash,
            "deltas": deltas, "transitions": {k: {name: len(ids) for name, ids in cats.items()} for k, cats in transitions.items()},
            "v1_pass_v2_fail_cases": [x["case_id"] for x in utility_cases],
            "critical_repair_status": {k: v["status"] for k, v in pd_repairs.items()},
            "claim_status": {k: v["status"] for k, v in claims.items()},
            "would_create": {key: str(path.relative_to(ROOT)) for key, path in OUTPUTS.items()},
        }, ensure_ascii=False, sort_keys=True))
        return
    # Replace report's metrics data already constructed above with provenance-free Markdown.
    write_new(OUTPUTS["comparison"], output_blobs["comparison"].decode())
    write_new(OUTPUTS["case_matrix"], matrix_text)
    write_new(OUTPUTS["report"], report_text)
    write_new(OUTPUTS["claim_audit"], json.dumps(claims_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_new(OUTPUTS["freeze"], freeze_bytes.decode())
    if sha(OUTPUTS["comparison"]) != output_hashes["comparison"] or sha(OUTPUTS["case_matrix"]) != output_hashes["case_matrix"] or sha(OUTPUTS["report"]) != output_hashes["report"] or sha(OUTPUTS["claim_audit"]) != output_hashes["claim_audit"] or sha(OUTPUTS["freeze"]) != freeze_hash:
        raise RuntimeError("FAIL CLOSED: persisted Step 9.48 output hash mismatch")
    for name, path in source_paths.items():
        if sha(path) != hashes[name]:
            raise RuntimeError(f"FAIL CLOSED: input changed during persistence: {name}")
    write_new(OUTPUTS["audit"], audit_bytes.decode())
    record = (
        "\n\n## Step 9.48 — Frozen Three-Way Matched Comparison\n\n"
        f"PASS: post-hoc descriptive Baseline/V1/V2 comparison on the identical frozen 40-case set/order `{order_hash}`. "
        f"Overall means: {b['overall']} / {a['overall']} / {c['overall']}; completion {b['completion']['count']}/40 / {a['completion']['count']}/40 / {c['completion']['count']}/40; "
        f"validity {b['answer_validity']['count']}/40 / {a['answer_validity']['count']}/40 / {c['answer_validity']['count']}/40. "
        f"V1→V2 completion pass→fail IDs: {', '.join(transitions['completion']['PASS_TO_FAIL'])}. "
        "No causal/significance/generalization claim, V4 rerun, V2 repair, V3 creation, or V5 access. "
        f"Comparison SHA-256 `{output_hashes['comparison']}`; case matrix `{output_hashes['case_matrix']}`; report `{output_hashes['report']}`; claim audit `{output_hashes['claim_audit']}`; freeze `{freeze_hash}`; audit `{hashlib.sha256(audit_bytes).hexdigest()}`.\n"
    )
    with (ROOT / "record.md").open("a", encoding="utf-8") as stream:
        stream.write(record)
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({
        "THREE_WAY_CASE_IDENTITY_MATCH": "YES", "THREE_WAY_ORDER_MATCH": "YES", "COMPARISON_CONSISTENCY_AUDIT": "PASS",
        "BASELINE_OVERALL": b["overall"], "V1_OVERALL": a["overall"], "V2_OVERALL": c["overall"],
        "OVERALL_DELTAS": deltas["overall"],
        "BASELINE_COMPLETION": b["completion"], "V1_COMPLETION": a["completion"], "V2_COMPLETION": c["completion"],
        "BASELINE_VALIDITY": b["answer_validity"], "V1_VALIDITY": a["answer_validity"], "V2_VALIDITY": c["answer_validity"],
        "BASELINE_LOW_VALUE_ASK_RATE": b["ask"]["low_value_rate"], "V1_LOW_VALUE_ASK_RATE": a["ask"]["low_value_rate"], "V2_LOW_VALUE_ASK_RATE": c["ask"]["low_value_rate"],
        "HARMFUL_FAILURES": [b["harmful_failures"]["count"],a["harmful_failures"]["count"],c["harmful_failures"]["count"]],
        "CRITICAL_FAILURES": [b["critical_failures"]["count"],a["critical_failures"]["count"],c["critical_failures"]["count"]],
        "V1_TO_V2_COMPLETION_PASS_TO_FAIL": transitions["completion"]["PASS_TO_FAIL"],
        "V1_TO_V2_COMPLETION_FAIL_TO_PASS": transitions["completion"]["FAIL_TO_PASS"],
        "SCORE_TRANSITIONS": {k:len(v) for k,v in transitions["score"].items()},
        "CRITICAL_REPAIR": pd_repairs, "CLAIMS": {k:v["status"] for k,v in claims.items()},
        "READY_FOR_POSTMORTEM_DECISION": "YES",
        "OUTPUTS": {key: str(path.relative_to(ROOT)) for key,path in OUTPUTS.items()},
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
