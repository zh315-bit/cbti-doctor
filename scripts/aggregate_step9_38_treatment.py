"""Offline Step 9.38 treatment aggregation using the frozen Step 9.30c formulas."""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation/v1_2_3"
RUN = ROOT / "evaluation/v4_runs/heldout-v4-step9_34a-treatment-20260928-01"
ATTEMPT = "attempt-step9_35b-e469d82618d4c51d91d193bb439507e4"
ADJ = OUT / "step9_37_treatment_adjudication.jsonl"
ADJ_FREEZE = OUT / "step9_37_treatment_adjudication_freeze.json"
RECON = OUT / "step9_38a_metric_registry_reconciliation_r4.json"
REGISTRY = OUT / "step9_26_v4_metric_registry.json"
SIDECAR = OUT / "step9_36_treatment_lineage_sidecar.jsonl"
RESULTS = RUN / f"{ATTEMPT}_case_results.jsonl"
TRACES = RUN / f"{ATTEMPT}_raw_traces.jsonl"
LEDGER = RUN / "attempts.jsonl"
EXPECTED = {
    "reconciliation": "06587be92e733543ad0ce8eb5074a365f8a161d2569b24f21fc140e0873d4b29",
    "adjudication": "60b5c2847ffdb51c43e00351519cb910428a82eb981849dfebefb76112658047",
    "registry": "de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056",
    "results": "9c926a69f9a4dfd19c559be0cbe8a08abc0902d5728c6f0202ba048b9e67e561",
    "traces": "0a8483e4125577e860eb0a7c72c399651800eb94d45eeb9481e6b21795302fdf",
    "ledger": "fc29a97cced81605dd0ec90b3ff8de80ca85e42b898ba5a5fb90f5db09d26d2a",
    "sidecar": "62f3fc844bbabbf59df0e42122d1b570faa11fc16e74b41a0f682f15939f2c42",
}
METRICS = OUT / "step9_38_treatment_aggregate_metrics.json"
SUMMARY = OUT / "step9_38_treatment_case_summary.jsonl"
REPORT = OUT / "step9_38_treatment_aggregate_report.md"
FREEZE = OUT / "step9_38_treatment_aggregate_freeze.json"
PRIOR_FAILURE = OUT / "step9_38_treatment_aggregation_audit.json"

sys.path.insert(0, str(ROOT))
from scripts import aggregate_step9_30c_v4 as frozen_agg  # noqa: E402
from scripts import v4_adjudication_contract as contract  # noqa: E402


def sha(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def durable_new(path: Path, data: bytes):
    with path.open("xb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def verify_inputs():
    paths = {
        "reconciliation": RECON, "adjudication": ADJ, "registry": REGISTRY,
        "results": RESULTS, "traces": TRACES, "ledger": LEDGER, "sidecar": SIDECAR,
    }
    for name, path in paths.items():
        if not path.is_file() or sha(path) != EXPECTED[name]:
            raise RuntimeError(f"frozen {name} identity mismatch")
    rec = read_json(RECON)
    if not (rec["compatibility_class"] == "BACKWARD_COMPATIBLE_FOR_AGGREGATION"
            and rec["baseline_aggregation_dependencies_verified"] is True
            and rec["treatment_adjudication_dependency_map"]["treatment_adjudication_dependencies_verified"] is True
            and rec["material_consumed_semantic_difference_count"] == 0
            and rec["allowed_treatment_aggregation_registry"] == {
                "path": "evaluation/v1_2_3/step9_26_v4_metric_registry.json", "sha256": EXPECTED["registry"]}
            and rec["treatment_adjudication_provenance_registry"]["sha256"] ==
                "a44f8959b1683775b3f8f956f7f990572faa5c204ae5da3fa1201245c56755ab"):
        raise RuntimeError("Step 9.38a r4 provenance bridge does not authorize this aggregation")
    freeze = read_json(ADJ_FREEZE)
    if (freeze.get("validation_status") != "PASS" or freeze.get("adjudication_sha256") != EXPECTED["adjudication"]
            or freeze.get("case_count") != 40 or freeze.get("fully_adjudication_eligible_cases") != 40
            or freeze.get("metric_registry_sha256") != "a44f8959b1683775b3f8f956f7f990572faa5c204ae5da3fa1201245c56755ab"
            or freeze.get("needs_review_case_count", 0) != 0):
        raise RuntimeError("Step 9.37 freeze identity/eligibility mismatch")
    results, traces, records, sidecar = map(read_jsonl, (RESULTS, TRACES, ADJ, SIDECAR))
    ledger = read_jsonl(LEDGER)
    if (not ledger or ledger[-1].get("status") != "COMPLETED"
            or ledger[-1].get("attempt_id") != ATTEMPT
            or ledger[-1].get("cases_started") != 40 or ledger[-1].get("cases_completed") != 40):
        raise RuntimeError("treatment attempt ledger mismatch")
    indexes = []
    for rows, label in ((results, "results"), (traces, "traces"), (records, "adjudication"), (sidecar, "sidecar")):
        ids = [r.get("case_id") if label != "adjudication" else r["immutable_execution_facts"].get("case_id") for r in rows]
        if len(rows) != 40 or len(set(ids)) != 40:
            raise RuntimeError(f"{label} coverage is not exactly 40 unique cases")
        indexes.append(dict(zip(ids, rows)))
    result_by_id, trace_by_id, adj_by_id, side_by_id = indexes
    if not (set(result_by_id) == set(trace_by_id) == set(adj_by_id) == set(side_by_id)):
        raise RuntimeError("case IDs differ across adjudication/results/traces/lineage")
    task_counts = Counter()
    for case_id, record in adj_by_id.items():
        facts = record["immutable_execution_facts"]
        result, trace = result_by_id[case_id], trace_by_id[case_id]
        if facts.get("attempt_id") != ATTEMPT or any(result.get(k) != facts.get(k) for k in (
            "evaluation_id", "case_id", "task_type", "final_status", "action_path",
            "ASK_count", "RETRIEVE_count", "READ_DIARY_count", "turn_count", "step_count",
            "tool_calls", "latency_ms", "lineage_ready")):
            raise RuntimeError(f"adjudicated execution facts mismatch for {case_id}")
        if trace.get("evaluation_id") != facts["evaluation_id"] or trace.get("case_id") != case_id:
            raise RuntimeError(f"raw trace identity mismatch for {case_id}")
        prov = record["execution_provenance"]
        for kind, source in (("case_result", RESULTS), ("raw_trace", TRACES)):
            p = prov[kind]
            rows = source.read_bytes().splitlines(keepends=True)
            raw = rows[p["line_number"] - 1]
            if p["path"] != str(source.relative_to(ROOT)) or contract.sha256_bytes(raw) != p["line_sha256"]:
                raise RuntimeError(f"line-level execution provenance mismatch for {case_id}/{kind}")
        review = record["review_provenance"]
        if (set(review) != {"rubric_path", "rubric_sha256", "metric_registry_path", "metric_registry_sha256",
                            "reviewer", "review_method", "reviewed_at"}
                or review.get("rubric_path") != "evaluation/benchmark_v1_1_scoring.md"
                or review.get("rubric_sha256") != freeze["rubric_sha256"]
                or review.get("metric_registry_path") != "evaluation/v1_2_3/step9_19_metric_registry.json"
                or review.get("metric_registry_sha256") != freeze["metric_registry_sha256"]
                or review.get("reviewer") != freeze["reviewer_identity"]
                or not isinstance(review.get("review_method"), str)
                or not isinstance(review.get("reviewed_at"), str)):
            raise RuntimeError("Step 9.37 historical reviewer provenance unexpectedly changed")
        contract._validate_completed_record(record)
        task_counts[facts["task_type"]] += 1
    expected_tasks = {t: 10 for t in contract.TASK_TYPES}
    if dict(task_counts) != expected_tasks:
        raise RuntimeError("treatment task distribution mismatch")
    if any(r.get("evaluation_id") != freeze["evaluation_id"] for r in results):
        raise RuntimeError("treatment evaluation/attempt identity mismatch")
    if any(t.get("evaluation_id") != freeze["evaluation_id"] for t in traces):
        raise RuntimeError("raw trace evaluation identity mismatch")
    return rec, freeze, records, sidecar, results, traces, ledger, task_counts


def custom_treatment_validator(records, mode):
    if mode != "completed" or len(records) != 40:
        raise RuntimeError("only the verified 40-row treatment adjudication is accepted")
    for row in records:
        contract._validate_completed_record(row)


def main():
    targets = [METRICS, SUMMARY, REPORT, FREEZE]
    if any(p.exists() for p in targets):
        raise RuntimeError("Step 9.38 output path already exists; refusing overwrite")
    prior_failure_hash = sha(PRIOR_FAILURE)
    rec, adjudication_freeze, records, sidecar, results, traces, ledger, task_counts = verify_inputs()
    original_agg_hash = sha(ROOT / "scripts/aggregate_step9_30c_v4.py")
    baseline_audit = read_json(OUT / "step9_30c_r1_v4_aggregation_audit.json")
    if original_agg_hash != baseline_audit.get("aggregator_sha256_at_final_audit"):
        raise RuntimeError("frozen Step 9.30c aggregation implementation hash mismatch")
    # The only compatibility adaptation is the treatment-specific contract validator
    # and its adjudicated provenance counts; all arithmetic stays in the frozen function.
    frozen_agg.validate_records = custom_treatment_validator
    frozen_agg.EXPECTED_LINEAGE = {
        "FORMAL_LINEAGE_READY": 27,
        "DERIVED_LINEAGE_COMPLETE": 8,
        "INCOMPLETE_FORMAL_BUT_ADJUDICATABLE": 5,
    }
    data = frozen_agg.aggregate_records(records, sidecar)
    rows = data.pop("case_level_rows")
    data["ask_quality"].pop("category_rates", None)
    data["ask_quality"]["LOW_VALUE_ASK_RATE"] = data["ask_quality"]["REDUNDANT_OR_IRRELEVANT_RATE"]
    data["tool_resource_behavior"].pop("ask_per_case", None)
    data["token_usage_status"] = "NOT_MEASURED"
    if (data["adjudicated_case_count"] != 40 or data["task_distribution"] != task_counts
            or data["valid_case_count"] != 40 or data["needs_review_case_count"] != 0):
        raise RuntimeError("aggregate consistency audit failed")
    for dimension, maximum in contract.DIMENSIONS.items():
        value = data["scores"]["dimensions"][dimension]["mean"]
        if not 0 <= value <= maximum:
            raise RuntimeError(f"dimension mean out of range: {dimension}")
    if data["ask_quality"]["TOTAL_ASK_COUNT"] != sum(r["immutable_execution_facts"]["ASK_count"] for r in records):
        raise RuntimeError("ASK total does not match observed execution count")
    if (data["lineage"]["FORMAL_LINEAGE_READY"] != 27
            or data["lineage"]["DERIVED_LINEAGE_COMPLETE"] != 8
            or data["lineage"]["INCOMPLETE_FORMAL_BUT_ADJUDICATABLE"] != 5):
        raise RuntimeError("lineage provenance counts mismatch")

    source_hashes = {
        "reconciliation": sha(RECON), "adjudication": sha(ADJ), "adjudication_freeze": sha(ADJ_FREEZE),
        "metric_registry": sha(REGISTRY), "case_results": sha(RESULTS), "raw_traces": sha(TRACES),
        "attempt_ledger": sha(LEDGER), "lineage_sidecar": sha(SIDECAR),
        "scoring_rubric": sha(ROOT / "evaluation/benchmark_v1_1_scoring.md"),
        "frozen_aggregator": original_agg_hash,
        "prior_fail_closed_audit": prior_failure_hash,
    }
    data["aggregation_provenance"] = {
        "aggregation_registry_path": str(REGISTRY.relative_to(ROOT)),
        "aggregation_registry_sha256": source_hashes["metric_registry"],
        "registry_provenance_bridge_path": str(RECON.relative_to(ROOT)),
        "registry_provenance_bridge_sha256": source_hashes["reconciliation"],
        "baseline_treatment_comparison_generated": False,
    }
    metrics_bytes = (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    summary_bytes = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows).encode()
    report_lines = [
        "# Step 9.38 — Frozen Treatment Aggregation (Retry)", "",
        "Status: PASS — deterministic offline aggregation of the frozen Step 9.37 treatment adjudication. No case was rerun or rescored.", "",
        f"- Treatment overall descriptive mean: {data['scores']['overall']['mean']}/100 (n=40).",
        "- Task means: " + "; ".join(f"{k} {v['mean']} (n={v['denominator']})" for k, v in data['scores']['task_type_means'].items()) + ".",
        "- Dimension means: " + "; ".join(f"{k} {v['mean']}/{v['maximum']}" for k, v in data['scores']['dimensions'].items()) + ".",
        f"- Completion: {data['completion_and_validity']['overall']['rate']['numerator']}/40; validity: {data['completion_and_validity']['overall']['validity_rate']['numerator']}/40.",
        f"- ASK events: {data['ask_quality']['TOTAL_ASK_COUNT']}; low-value ASK rate {data['ask_quality']['LOW_VALUE_ASK_RATE']['value']} ({data['ask_quality']['LOW_VALUE_ASK_RATE']['numerator']}/{data['ask_quality']['LOW_VALUE_ASK_RATE']['denominator']}; denominator is all ASK events).",
        f"- Execution means: retrieve {data['tool_resource_behavior']['per_case_means']['retrieve_per_case']['value']}/case; read diary {data['tool_resource_behavior']['per_case_means']['read_diary_per_case']['value']}/case; tool calls {data['efficiency']['tool_calls_per_case']['mean']}/case; turns {data['efficiency']['turns_per_case']['mean']}/case; steps {data['efficiency']['steps_per_case']['mean']}/case; mean latency {data['efficiency']['latency_ms']['overall']['mean_ms']} ms.",
        f"- Token usage: {data['token_usage_status']}. Critical failures: {data['failures']['CRITICAL_FAILURE_COUNT']}; harmful failures: {data['failures']['HARMFUL_FAILURE_COUNT']}.",
        f"- Lineage (provenance only, no score effect): formal ready {data['lineage']['FORMAL_LINEAGE_READY']}; derived complete {data['lineage']['DERIVED_LINEAGE_COMPLETE']}; incomplete formal but adjudicatable {data['lineage']['INCOMPLETE_FORMAL_BUT_ADJUDICATABLE']}; denominator 40.",
        "- Reviewer: single AI reviewer, not human; inter-rater reliability not measured.",
        "- No baseline-treatment deltas, improvement percentages, significance claims, resume claims, or V5 access were generated.", "",
        "## Integrity", "",
        "Step 9.38a r4 is the append-only provenance bridge: compatibility is aggregation-compatible, not byte identity. Aggregation definitions came only from the Step 9.26 registry; Step 9.37 historical Step 9.19 provenance remains unchanged.",
        "The Step 9.38 fail-closed audit remains preserved. No Agent, model, RAG, treatment rerun, or source artifact modification occurred.", "",
        "Source identities:", "",
    ] + [f"- {k}: `{v}`" for k, v in source_hashes.items()]
    report_bytes = ("\n".join(report_lines) + "\n").encode()
    output_hashes = {
        "metrics": __import__("hashlib").sha256(metrics_bytes).hexdigest(),
        "case_summary": __import__("hashlib").sha256(summary_bytes).hexdigest(),
        "report": __import__("hashlib").sha256(report_bytes).hexdigest(),
    }
    # Revalidate source identities immediately before publishing durable outputs.
    verify_inputs()
    if sha(PRIOR_FAILURE) != prior_failure_hash or sha(ROOT / "scripts/aggregate_step9_30c_v4.py") != original_agg_hash:
        raise RuntimeError("source identity changed before persistence")
    durable_new(METRICS, metrics_bytes)
    durable_new(SUMMARY, summary_bytes)
    durable_new(REPORT, report_bytes)
    freeze = {
        "step": "9.38", "status": "PASS_TREATMENT_AGGREGATION_ONLY",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_id": adjudication_freeze["evaluation_id"], "attempt_id": ATTEMPT,
        "adjudication_case_count": 40, "valid_case_count": 40, "needs_review_case_count": 0,
        "task_distribution": dict(sorted(task_counts.items())),
        "aggregation_registry": {"path": str(REGISTRY.relative_to(ROOT)), "sha256": source_hashes["metric_registry"]},
        "registry_reconciliation": {"path": str(RECON.relative_to(ROOT)), "sha256": source_hashes["reconciliation"],
                                    "compatibility_class": rec["compatibility_class"],
                                    "material_consumed_semantic_difference_count": 0},
        "source_hashes": source_hashes,
        "outputs": {
            "metrics": {"path": str(METRICS.relative_to(ROOT)), "sha256": output_hashes["metrics"]},
            "case_summary": {"path": str(SUMMARY.relative_to(ROOT)), "sha256": output_hashes["case_summary"], "rows": 40},
            "report": {"path": str(REPORT.relative_to(ROOT)), "sha256": output_hashes["report"]},
        },
        "consistency_audit": "PASS", "ask_denominator": "all ASK events",
        "lineage_is_provenance_only": True, "baseline_treatment_comparison_generated": False,
        "treatment_rerun": False, "model_called_for_case_execution": False,
        "agent_called": False, "rag_called": False, "v5_accessed": False,
        "source_artifacts_modified": False, "prior_step9_38_failure_audit_preserved": True,
    }
    durable_new(FREEZE, (json.dumps(freeze, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode())
    record_entry = (
        "\n\n## Step 9.38 — Frozen Treatment Aggregation Retry\n\n"
        f"Offline aggregation PASS for the frozen Step 9.37 treatment adjudication (40/40; task strata 10 each). "
        f"Overall descriptive mean {data['scores']['overall']['mean']}; no baseline-treatment comparison was generated. "
        f"Step 9.38a r4 reconciliation SHA-256 `{source_hashes['reconciliation']}` bridges Step 9.37's unchanged Step 9.19 reviewer provenance to the Step 9.26 aggregation registry (SHA-256 `{source_hashes['metric_registry']}`); this is semantic compatibility, not registry byte identity. "
        f"Metrics SHA-256 `{output_hashes['metrics']}`, case summary SHA-256 `{output_hashes['case_summary']}`, report SHA-256 `{output_hashes['report']}`. "
        "Original fail-closed Step 9.38 audit preserved. No rerun/model/Agent/RAG, no V5 access, and no source artifacts modified."
    )
    with (ROOT / "record.md").open("a", encoding="utf-8") as f:
        f.write(record_entry)
        f.flush()
        os.fsync(f.fileno())
    print(json.dumps({"status": freeze["status"], "overall": data["scores"]["overall"],
                      "task_means": data["scores"]["task_type_means"],
                      "dimensions": data["scores"]["dimensions"],
                      "completion": data["completion_and_validity"]["overall"],
                      "ask_quality": data["ask_quality"], "execution": data["efficiency"],
                      "failures": data["failures"], "lineage": data["lineage"],
                      "outputs": freeze["outputs"], "baseline_comparison": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
