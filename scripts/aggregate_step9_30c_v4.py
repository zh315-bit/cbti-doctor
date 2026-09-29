"""Deterministic, offline aggregation of the frozen Step 9.30b V4 review.

This module never loads benchmark prompts or calls an Agent, model, or RAG.
The case-level output contains IDs and rubric/telemetry fields only, not prompts,
answers, evidence, or rationale text.
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.v4_adjudication_contract import (
    ASK_CATEGORIES, DIMENSIONS, TASK_TYPES, ROOT, OUT, REGISTRY_PATH,
    RUBRIC_PATH, FREEZE_PATH, sha256, validate_records,
)
from scripts.step9_30b1_identity import verify_canonical_input

ADJUDICATION_PATH = OUT / "step9_30b_v4_human_adjudication.jsonl"
ADJUDICATION_FREEZE_PATH = OUT / "step9_30b_v4_human_adjudication_freeze.json"
SIDECAR_PATH = OUT / "step9_30a2_v4_lineage_sidecar.jsonl"
EXPECTED_LINEAGE = {
    "FORMAL_LINEAGE_READY": 28,
    "DERIVED_LINEAGE_COMPLETE": 7,
    "INCOMPLETE_FORMAL_BUT_ADJUDICATABLE": 5,
}


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _mean(values):
    return round(sum(values) / len(values), 4) if values else None


def _metric(numerator, denominator, formula, source_case_ids):
    return {
        "numerator": numerator,
        "denominator": denominator,
        "formula": formula,
        "source_case_ids": sorted(source_case_ids),
        "value": round(numerator / denominator, 4) if denominator else None,
    }


def _latency(values):
    if not values:
        return {"mean_ms": None, "median_ms": None, "p90_nearest_rank_ms": None,
                "n": 0, "formula": "mean=sum(latency_ms)/n; median=statistics.median; p90=sorted[ceil(0.9*n)-1]"}
    ordered = sorted(values)
    return {"mean_ms": _mean(values), "median_ms": round(statistics.median(values), 4),
            "p90_nearest_rank_ms": ordered[math.ceil(.9 * len(ordered)) - 1], "n": len(values),
            "formula": "mean=sum(latency_ms)/n; median=statistics.median; p90=sorted[ceil(0.9*n)-1]"}


def verify_frozen_inputs():
    resolved_identity = verify_canonical_input(ROOT)
    freeze = _json(ADJUDICATION_FREEZE_PATH)
    if freeze.get("validation_status") != "PASS" or freeze.get("adjudication_sha256") != resolved_identity["adjudication_sha256"]:
        raise RuntimeError("Step 9.30b adjudication freeze or canonical identity mismatch")
    adjudication_report = OUT / "step9_30b_v4_human_adjudication_report.md"
    if sha256(adjudication_report) != freeze.get("adjudication_report_sha256"):
        raise RuntimeError("adjudication report hash mismatch")
    # The adjudication freeze's complete source manifest is authoritative.
    for item in freeze.get("adjudication_inputs", []):
        source = ROOT / item["path"]
        if not source.is_file() or sha256(source) != item["sha256"]:
            raise RuntimeError(f"frozen adjudication input mismatch: {item['path']}")
    if sha256(REGISTRY_PATH) != freeze.get("metric_registry_sha256"):
        raise RuntimeError("metric registry hash mismatch")
    if sha256(RUBRIC_PATH) != freeze.get("rubric_sha256"):
        raise RuntimeError("scoring rubric hash mismatch")
    run_freeze = _json(FREEZE_PATH)
    for item in run_freeze["artifact_files"]:
        source = ROOT / item["path"]
        if not source.is_file() or source.stat().st_size != item["byte_size"] or sha256(source) != item["sha256"]:
            raise RuntimeError(f"frozen run artifact mismatch: {item['path']}")
    if sha256(SIDECAR_PATH) != freeze.get("lineage_sidecar_sha256"):
        raise RuntimeError("lineage sidecar hash mismatch")
    return freeze, run_freeze, resolved_identity


def _case_projection(record):
    f, j = record["immutable_execution_facts"], record["reviewer_judgments"]
    attribution = j["failure_attribution"]
    return {
        "case_id": f["case_id"], "task_type": f["task_type"],
        "dimension_scores": j["dimension_scores"], "total_score": j["total_score"],
        "completion_judgment": j["completion_judgment"], "validity_judgment": j["validity_judgment"],
        "ask_quality_counts": j["ask_quality"]["counts"],
        "necessary_ask_preservation": {
            "acquired_targets": j["necessary_ask_preservation"]["acquired_targets"],
            "oracle_required_targets": j["necessary_ask_preservation"]["oracle_required_targets"],
        },
        "tool_use_appropriateness": {
            name: dict(Counter(j["tool_use_appropriateness"][name]))
            for name in ("RETRIEVE", "READ_DIARY")
        },
        "critical_failure_types": j["critical_failure"]["types"],
        "critical_failure": j["critical_failure"]["present"],
        "harmful_failure": j["harmful_failure"],
        "primary_cause": attribution["primary_cause"],
        "first_divergence": attribution["first_divergence"],
        "downstream_effects": attribution["downstream_effects"],
        "lineage_ready": f["lineage_ready"],
        "execution": {key: f[key] for key in (
            "final_status", "ASK_count", "RETRIEVE_count", "READ_DIARY_count",
            "turn_count", "step_count", "latency_ms", "tool_calls")},
    }


def aggregate_records(records, sidecar_rows):
    validate_records(records, "completed")
    if len(records) != 40:
        raise RuntimeError("expected exactly 40 adjudicated records")
    facts = [r["immutable_execution_facts"] for r in records]
    judgments = [r["reviewer_judgments"] for r in records]
    task_counts = Counter(f["task_type"] for f in facts)
    if task_counts != Counter({task: 10 for task in TASK_TYPES}):
        raise RuntimeError("task strata mismatch")
    all_totals = [j["total_score"] for j in judgments]
    all_case_ids = [f["case_id"] for f in facts]
    score_summary = {
        "overall": {"numerator": sum(all_totals), "denominator": len(all_totals),
                    "formula": "sum(case total_score)/number of adjudicated cases",
                    "source_case_ids": sorted(all_case_ids), "mean": _mean(all_totals), "scale": "0-100 descriptive; no pass threshold"},
        "dimensions": {}, "task_type_means": {},
    }
    for dimension in DIMENSIONS:
        vals = [j["dimension_scores"][dimension] for j in judgments]
        score_summary["dimensions"][dimension] = {
            "numerator": sum(vals), "denominator": len(vals),
            "formula": f"sum(case dimension_scores.{dimension})/number of adjudicated cases",
            "source_case_ids": sorted(all_case_ids), "mean": _mean(vals), "maximum": DIMENSIONS[dimension],
        }
    for task in TASK_TYPES:
        indexes = [i for i, f in enumerate(facts) if f["task_type"] == task]
        vals = [judgments[i]["total_score"] for i in indexes]
        score_summary["task_type_means"][task] = {
            "numerator": sum(vals), "denominator": len(vals),
            "formula": "sum(case total_score in task stratum)/number of adjudicated cases in task stratum",
            "source_case_ids": sorted(facts[i]["case_id"] for i in indexes), "mean": _mean(vals),
        }

    completion = {"overall": {}, "by_task_type": {}}
    for task in ("ALL", *TASK_TYPES):
        indexes = list(range(40)) if task == "ALL" else [i for i, f in enumerate(facts) if f["task_type"] == task]
        vals = [judgments[i]["completion_judgment"] for i in indexes]
        ids = [facts[i]["case_id"] for i in indexes]
        complete = sum(v == "complete" for v in vals)
        payload = {"distribution": dict(sorted(Counter(vals).items())),
                   "rate": _metric(complete, len(vals), "complete judgments / adjudicated cases", ids),
                   "validity_rate": _metric(sum(judgments[i]["validity_judgment"] for i in indexes), len(vals),
                                             "validity=true judgments / adjudicated cases", ids)}
        if task == "ALL": completion["overall"] = payload
        else: completion["by_task_type"][task] = payload

    ask_counts = Counter()
    for j in judgments: ask_counts.update(j["ask_quality"]["counts"])
    ask_total = sum(f["ASK_count"] for f in facts)
    if sum(ask_counts.values()) != ask_total:
        raise RuntimeError("frozen ASK categories do not reconcile to observed ASK total")
    low_value = ask_counts["redundant"] + ask_counts["irrelevant"]
    necessary_num = sum(j["necessary_ask_preservation"]["acquired_targets"] for j in judgments)
    necessary_den = sum(j["necessary_ask_preservation"]["oracle_required_targets"] for j in judgments)
    ask_category_metrics = {}
    for category in ASK_CATEGORIES:
        category_case_ids = [f["case_id"] for f, j in zip(facts, judgments)
                             if j["ask_quality"]["counts"][category] > 0]
        ask_category_metrics[category] = _metric(
            ask_counts[category], ask_total, f"{category} ASK events / all ASK events", category_case_ids)

    tool_counts = {kind: sum(f[f"{kind}_count"] for f in facts) for kind in ("RETRIEVE", "READ_DIARY", "ASK")}
    tool_counts["TOOL_CALL"] = sum(len(f["tool_calls"]) for f in facts)
    appropriateness = {kind: dict(sorted(Counter(
        label for j in judgments for label in j["tool_use_appropriateness"][kind]
    ).items())) for kind in ("RETRIEVE", "READ_DIARY")}
    efficiency = {}
    for label, values, formula in (
        ("turns_per_case", [f["turn_count"] for f in facts], "sum(turn_count)/n cases"),
        ("steps_per_case", [f["step_count"] for f in facts], "sum(step_count)/n cases"),
        ("tool_calls_per_case", [len(f["tool_calls"]) for f in facts], "sum(actual RETRIEVE+READ_DIARY calls)/n cases; ASK excluded"),
    ):
        efficiency[label] = {"numerator": sum(values), "denominator": len(values), "formula": formula,
                             "source_case_ids": sorted(all_case_ids), "mean": _mean(values)}
    latencies = [f["latency_ms"] for f in facts]
    efficiency["latency_ms"] = {"overall": {**_latency(latencies), "source_case_ids": sorted(all_case_ids)}, "by_task_type": {
        task: {**_latency([f["latency_ms"] for f in facts if f["task_type"] == task]),
               "source_case_ids": sorted(f["case_id"] for f in facts if f["task_type"] == task)} for task in TASK_TYPES}}

    critical_ids = sorted(f["case_id"] for f, j in zip(facts, judgments) if j["critical_failure"]["present"])
    harmful_ids = sorted(f["case_id"] for f, j in zip(facts, judgments) if j["harmful_failure"])
    primary_causes = Counter(j["failure_attribution"]["primary_cause"] for j in judgments
                             if j["failure_attribution"]["primary_cause"] is not None)
    first_divergence = Counter(j["failure_attribution"]["first_divergence"] for j in judgments
                               if j["failure_attribution"]["first_divergence"] is not None)
    downstream_effects = Counter(effect for j in judgments for effect in j["failure_attribution"]["downstream_effects"])
    root_cause_details = {
        cause: {"count": count, "case_ids": sorted(
            facts[i]["case_id"] for i, j in enumerate(judgments)
            if j["failure_attribution"]["primary_cause"] == cause)}
        for cause, count in primary_causes.items()
    }
    divergence_details = {
        layer: {"count": count, "case_ids": sorted(
            facts[i]["case_id"] for i, j in enumerate(judgments)
            if j["failure_attribution"]["first_divergence"] == layer)}
        for layer, count in first_divergence.items()
    }

    sidecar = {x["case_id"]: x for x in sidecar_rows}
    if len(sidecar) != 40 or set(sidecar) != {f["case_id"] for f in facts}:
        raise RuntimeError("lineage sidecar coverage mismatch")
    lineage = Counter(row["sidecar_lineage_status"] for row in sidecar_rows)
    lineage_metrics = {
        "FORMAL_LINEAGE_READY": sum(f["lineage_ready"] is True for f in facts),
        "DERIVED_LINEAGE_COMPLETE": lineage["COMPLETE_DERIVED"],
        "INCOMPLETE_FORMAL_BUT_ADJUDICATABLE": lineage["INCOMPLETE_FORMAL"],
        "interpretation": "Provenance metrics only; derived repairs remain derived, and incomplete formal cases remain incomplete. No score adjustment.",
    }
    if any(lineage_metrics[k] != v for k, v in EXPECTED_LINEAGE.items()):
        raise RuntimeError("lineage counts disagree with frozen adjudication status")

    return {
        "aggregation_status": "DESCRIPTIVE_SINGLE_AI_REVIEWER_AGGREGATE",
        "evaluation_id": facts[0]["evaluation_id"], "attempt_id": facts[0]["attempt_id"],
        "adjudicated_case_count": len(records), "valid_case_count": 40, "needs_review_case_count": 0,
        "task_distribution": dict(sorted(task_counts.items())),
        "scores": score_summary,
        "completion_and_validity": completion,
        "ask_quality": {
            "TOTAL_ASK_COUNT": ask_total, "NECESSARY_ASK_COUNT": ask_counts["necessary"],
            "USEFUL_OPTIONAL_ASK_COUNT": ask_counts["useful_but_optional"],
            "REDUNDANT_ASK_COUNT": ask_counts["redundant"], "IRRELEVANT_ASK_COUNT": ask_counts["irrelevant"],
            "category_counts": dict(sorted(ask_counts.items())),
            "category_rates": ask_category_metrics,
            "REDUNDANT_OR_IRRELEVANT_RATE": _metric(low_value, ask_total, "(redundant + irrelevant ASK events) / all ASK events", all_case_ids),
            "NECESSARY_ASK_PRESERVATION_RATE": _metric(necessary_num, necessary_den,
                "acquired oracle-required targets / all oracle-required targets", all_case_ids),
        },
        "tool_resource_behavior": {
            "counts": tool_counts,
            "per_case_means": {key.lower() + "_per_case": _metric(value, len(records), f"{key} actions / adjudicated cases", all_case_ids)
                               for key, value in tool_counts.items()},
            "ask_per_case": _metric(ask_total, len(records), "ASK actions / adjudicated cases", all_case_ids),
            "total_acquisition_actions_per_case": _metric(
                ask_total + tool_counts["RETRIEVE"] + tool_counts["READ_DIARY"], len(records),
                "(ASK + RETRIEVE + READ_DIARY) / adjudicated cases", all_case_ids),
            "appropriateness_judgments": appropriateness,
            "quality_note": "Tool counts are behavior telemetry, not quality scores; appropriateness remains separate reviewer judgment.",
        },
        "efficiency": efficiency,
        "failures": {
            "CRITICAL_FAILURE_COUNT": len(critical_ids), "CRITICAL_FAILURE_CASE_IDS": critical_ids,
            "HARMFUL_FAILURE_COUNT": len(harmful_ids), "HARMFUL_FAILURE_CASE_IDS": harmful_ids,
            "primary_cause_root_cause_distribution": dict(sorted(primary_causes.items())),
            "primary_cause_case_ids": root_cause_details,
            "first_divergence_layer_distribution": dict(sorted(first_divergence.items())),
            "first_divergence_case_ids": divergence_details,
            "downstream_effect_distribution": dict(sorted(downstream_effects.items())),
        },
        "lineage": lineage_metrics,
        "reviewer_limitations": {
            "reviewer_type": "SINGLE_AI_REVIEWER", "human_adjudication": False,
            "inter_rater_reliability": "NOT_MEASURED",
            "deterministic_consistency_checks": "PASS_SINGLE_REVIEWER_DETERMINISTIC_CHECKS",
            "interpretation": "Rubric scores are single-reviewer descriptive judgments; they are not human/expert review or inter-rater validated.",
        },
        "historical_comparability": {
            "status": "NOT_COMPARABLE",
            "reason": "V4 is a distinct case set and uses a single AI reviewer; the metric registry identifies V2 as non-paired development data and V3 as consumed historical held-out data. Historical scores were not loaded or compared.",
        },
        "OVERALL_PASS_THRESHOLD": "NOT_DEFINED",
        "token_usage_status": "NOT_MEASURED",
        "final_status_note": "final_status=ANSWER is execution telemetry and is not substituted for completion judgment.",
        "case_level_rows": [_case_projection(r) for r in records],
    }


def _write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    frozen, run_freeze, identity = verify_frozen_inputs()
    raw_records = _jsonl(ADJUDICATION_PATH)
    validate_records(raw_records, "completed")
    records = sorted(raw_records, key=lambda r: r["immutable_execution_facts"]["case_id"])
    data = aggregate_records(records, _jsonl(SIDECAR_PATH))
    case_rows = data.pop("case_level_rows")
    metrics_path = OUT / "step9_30c_v4_aggregate_metrics.json"
    case_path = OUT / "step9_30c_v4_case_level_summary.jsonl"
    report_path = OUT / "step9_30c_v4_aggregate_report.md"
    audit_path = OUT / "step9_30c_r1_v4_aggregation_audit.json"
    original_audit_path = OUT / "step9_30c_v4_aggregation_audit.json"
    if metrics_path.exists() or case_path.exists() or audit_path.exists():
        raise RuntimeError("Step 9.30c-r1 output exists; refusing to overwrite append-only artifacts")
    if not report_path.is_file() or "BLOCKED_FAIL_CLOSED_ADJUDICATION_PIN_MISMATCH" not in report_path.read_text(encoding="utf-8"):
        raise RuntimeError("expected original failed Step 9.30c report is absent or changed")
    prior_report = report_path.read_text(encoding="utf-8")
    prior_audit_hash = sha256(original_audit_path)
    if "## Step 9.30c-r1 retry aggregate report" in prior_report:
        raise RuntimeError("Step 9.30c-r1 report section already exists; refusing rerun")
    if resolved_hash := _json(OUT / "step9_30c_v4_aggregation_input.json").get("adjudication_sha256"):
        if resolved_hash != identity["adjudication_sha256"]:
            raise RuntimeError("canonical identity changed during aggregation setup")
    else:
        raise RuntimeError("canonical aggregation input has no adjudication SHA")
    # Verify all frozen inputs once more immediately before durable output.
    frozen_prewrite, run_prewrite, identity_prewrite = verify_frozen_inputs()
    if (frozen_prewrite != frozen or run_prewrite != run_freeze or identity_prewrite != identity
            or sha256(original_audit_path) != prior_audit_hash):
        raise RuntimeError("frozen identity changed before output persistence")
    _write_json(metrics_path, data)
    case_path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in case_rows), encoding="utf-8")
    report_append = "\n\n## Step 9.30c-r1 retry aggregate report\n\n" + _render_report(data, {}, {"outputs": {"report": str(report_path.relative_to(ROOT))}})
    with report_path.open("a", encoding="utf-8") as stream:
        stream.write(report_append)
        stream.flush()
    # Recheck frozen source identities after aggregate persistence.
    frozen_after, run_freeze_after, identity_after = verify_frozen_inputs()
    if (frozen_after != frozen or run_freeze_after != run_freeze or identity_after != identity
            or sha256(original_audit_path) != prior_audit_hash):
        raise RuntimeError("frozen source identity changed during aggregation")
    input_hashes = {
        "adjudication": sha256(ADJUDICATION_PATH),
        "case_results": next(x["sha256"] for x in run_freeze["artifact_files"] if x["path"].endswith("_case_results.jsonl")),
        "raw_traces": next(x["sha256"] for x in run_freeze["artifact_files"] if x["path"].endswith("_raw_traces.jsonl")),
        "attempts_ledger": next(x["sha256"] for x in run_freeze["artifact_files"] if x["path"].endswith("attempts.jsonl")),
        "rubric": sha256(RUBRIC_PATH), "metric_registry": sha256(REGISTRY_PATH), "lineage_sidecar": sha256(SIDECAR_PATH),
    }
    audit = {
        "step": "9.30c-r1", "status": "PASS_DETERMINISTIC_AGGREGATION",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "identity_gate": {
            "computed_adjudication_sha256": identity["adjudication_sha256"],
            "canonical_input_adjudication_sha256": identity["adjudication_sha256"],
            "step9_30b_freeze_sha256": identity["step9_30b_recorded_sha256"],
            "status": "PASS",
        },
        "adjudication_sha256_expected": frozen["adjudication_sha256"],
        "adjudication_sha256_actual": input_hashes["adjudication"],
        "adjudication_validation": "PASS_40_UNIQUE_COMPLETE_CASES_SCORE_AND_ARITHMETIC_CHECKED",
        "input_hashes_before_after_match": True, "input_hashes": input_hashes,
        "original_step9_30c_failure_audit_preserved": True,
        "original_step9_30c_failure_audit_sha256": prior_audit_hash,
        "input_manifest_verified": True, "case_summary_excludes_prompts_answers_evidence_and_rationales": True,
        "v4_rerun": False, "model_called": False, "agent_called": False, "rag_called": False,
        "adjudication_modified": False, "case_results_modified": False, "raw_traces_modified": False,
        "attempt_ledger_modified": False, "scoring_rubric_modified": False,
        "metric_registry_modified": False, "lineage_sidecar_modified": False,
        "historical_scores_loaded": False, "overall_pass_threshold_created": False,
        "outputs": {
            "metrics": {"path": str(metrics_path.relative_to(ROOT)), "sha256": sha256(metrics_path)},
            "case_summary": {"path": str(case_path.relative_to(ROOT)), "sha256": sha256(case_path), "rows": len(case_rows)},
            "report": {"path": str(report_path.relative_to(ROOT)), "sha256": sha256(report_path), "append_only": True},
            "audit": {"path": str(audit_path.relative_to(ROOT))},
        },
    }
    _write_json(audit_path, audit)
    print(json.dumps({"status": audit["status"], "scores": data["scores"],
                      "completion_and_validity": data["completion_and_validity"],
                      "ask_quality": data["ask_quality"], "tool_resource_behavior": data["tool_resource_behavior"],
                      "efficiency": data["efficiency"], "failures": data["failures"], "lineage": data["lineage"],
                      "identity_gate": audit["identity_gate"], "outputs": audit["outputs"]}, ensure_ascii=False, indent=2))


def _render_report(data, hashes, audit):
    score = data["scores"]
    completion = data["completion_and_validity"]
    ask = data["ask_quality"]
    tools = data["tool_resource_behavior"]
    eff = data["efficiency"]
    failures = data["failures"]
    lineage = data["lineage"]
    lines = [
        "# Step 9.30c — V4 Frozen Adjudication Aggregate", "",
        f"Status: **{data['aggregation_status']}**. This is deterministic aggregation of the frozen 40-case Step 9.30b adjudication; no case was rescored.", "",
        "## Observed result", "",
        f"- Overall descriptive mean: **{score['overall']['mean']}/100** ({score['overall']['numerator']}/{score['overall']['denominator']}; arithmetic mean of case totals).",
        "- Task means: " + "; ".join(f"{task} {item['mean']} (n={item['denominator']})" for task, item in score["task_type_means"].items()) + ".",
        "- Dimension means (point scale, per frozen rubric): " + "; ".join(f"{key} {item['mean']}/{item['maximum']}" for key, item in score["dimensions"].items()) + ".",
        f"- Completion: {completion['overall']['rate']['numerator']}/{completion['overall']['rate']['denominator']} = {completion['overall']['rate']['value']}; validity: {completion['overall']['validity_rate']['numerator']}/{completion['overall']['validity_rate']['denominator']} = {completion['overall']['validity_rate']['value']}. Per-task strata are in the metrics JSON.",
        f"- ASK events: {ask['TOTAL_ASK_COUNT']}; necessary {ask['NECESSARY_ASK_COUNT']}, useful optional {ask['USEFUL_OPTIONAL_ASK_COUNT']}, redundant {ask['REDUNDANT_ASK_COUNT']}, irrelevant {ask['IRRELEVANT_ASK_COUNT']}; low-value rate {ask['REDUNDANT_OR_IRRELEVANT_RATE']['value']} ({ask['REDUNDANT_OR_IRRELEVANT_RATE']['numerator']}/{ask['REDUNDANT_OR_IRRELEVANT_RATE']['denominator']}). Necessary-target preservation {ask['NECESSARY_ASK_PRESERVATION_RATE']['value']} ({ask['NECESSARY_ASK_PRESERVATION_RATE']['numerator']}/{ask['NECESSARY_ASK_PRESERVATION_RATE']['denominator']}).",
        f"- Tools/actions: RETRIEVE {tools['counts']['RETRIEVE']} ({tools['per_case_means']['retrieve_per_case']['value']}/case), READ_DIARY {tools['counts']['READ_DIARY']} ({tools['per_case_means']['read_diary_per_case']['value']}/case), ASK {tools['counts']['ASK']}, actual tool calls {tools['counts']['TOOL_CALL']} ({tools['per_case_means']['tool_call_per_case']['value']}/case). Tool counts are not quality scores; appropriateness counts are separate.",
        f"- Efficiency means: turns {eff['turns_per_case']['mean']}/case; steps {eff['steps_per_case']['mean']}/case; tool calls {eff['tool_calls_per_case']['mean']}/case. Latency mean/median/p90 nearest-rank: {eff['latency_ms']['overall']['mean_ms']}/{eff['latency_ms']['overall']['median_ms']}/{eff['latency_ms']['overall']['p90_nearest_rank_ms']} ms. Token usage: **NOT_MEASURED**.",
        f"- Critical failures: {failures['CRITICAL_FAILURE_COUNT']} {failures['CRITICAL_FAILURE_CASE_IDS']}; harmful failures: {failures['HARMFUL_FAILURE_COUNT']} {failures['HARMFUL_FAILURE_CASE_IDS']}.",
        f"- Lineage (provenance only, not score penalties): formal ready {lineage['FORMAL_LINEAGE_READY']}; derived complete {lineage['DERIVED_LINEAGE_COMPLETE']}; incomplete formal but adjudicatable {lineage['INCOMPLETE_FORMAL_BUT_ADJUDICATABLE'] }.",
        "", "## Supported interpretation", "",
        "These are descriptive results from one AI reviewer. Completion comes from the frozen completion judgment, not `final_status=ANSWER`. Failure causes and first-divergence layers are reported from frozen per-case labels; no labels were changed.",
        "", "## Not yet supported", "",
        "Reviewer type is a single AI reviewer, not human adjudication; inter-rater reliability was not measured. Deterministic consistency checks passed, but scores remain single-reviewer descriptive judgments. Historical comparison is NOT_COMPARABLE for this report; historical scores were not loaded. No overall pass threshold is defined, and no pass/fail conclusion is made.",
        "", "## Integrity", "",
        "No Agent/model/RAG call or V4 rerun occurred. Frozen source files were hash-verified before and after aggregation and were not modified:", "",
    ]
    lines.extend(f"- `{name}`: `{digest}`" for name, digest in hashes.items())
    lines += ["", f"Audit artifact: `{audit['outputs']['report']}`; aggregation audit JSON records output hashes and no-modification flags.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
