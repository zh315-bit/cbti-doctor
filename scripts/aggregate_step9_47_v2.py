"""Fail-closed, offline Step 9.47 Treatment-V2 frozen aggregation."""
from __future__ import annotations

import hashlib
import json
import math
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation/v1_2_3"
RUN = ROOT / "evaluation/v4_runs/heldout-v4-step9_43-treatment-v2-20260928-01"
EVALUATION_ID = "heldout-v4-step9_43-treatment-v2-20260928-01"
AUTHORIZATION_ID = "auth-step9_44r1-ecce3f6d87e64ace822fc46c97c18f55"
ATTEMPT_ID = "attempt-step9_44r1-cb362342ae31449aaffba8092c346864"
EXPECTED_ADJ_SHA = "38e178b68d498ca8280901e071e84787342ba460b47ec3c7e9f55f76086eb0f0"
EXPECTED_ORDER_SHA = "d930455e417935337a6e3459defbdc3ee3829b71786fbd8438ef092b62429e68"

ADJ = OUT / "step9_46_v2_adjudication.jsonl"
ADJ_FREEZE = OUT / "step9_46_v2_adjudication_freeze.json"
ADJ_AUDIT = OUT / "step9_46_v2_adjudication_audit.json"
RUN_FREEZE = OUT / "step9_45a_v2_run_input_freeze.json"
LINEAGE_AUDIT = OUT / "step9_45a_v2_lineage_forensics.json"
SIDECAR = OUT / "step9_45a_v2_lineage_sidecar.jsonl"
MATRIX = OUT / "step9_45a_v2_lineage_case_matrix.jsonl"
REGISTRY = OUT / "step9_26_v4_metric_registry.json"
RUBRIC = ROOT / "evaluation/benchmark_v1_1_scoring.md"
RESULTS = RUN / f"{ATTEMPT_ID}_case_results.jsonl"
TRACES = RUN / f"{ATTEMPT_ID}_raw_traces.jsonl"
LEDGER = RUN / "attempts.jsonl"

METRICS = OUT / "step9_47_v2_aggregate.json"
SUMMARY = OUT / "step9_47_v2_case_summary.jsonl"
REPORT = OUT / "step9_47_v2_aggregation_report.md"
FREEZE = OUT / "step9_47_v2_aggregation_freeze.json"
AUDIT = OUT / "step9_47_v2_aggregation_audit.json"

EXPECTED_HASHES = {
    "adjudication": EXPECTED_ADJ_SHA,
    "adjudication_freeze": "74c50c34bd869109d52862202245b7d7e9463928dea24e897b74e3ed85587cee",
    "adjudication_audit": "5cffe15dd810d2303c1ae91b3f13281382575ee45701fd11a7c7210c45ad5018",
    "run_input_freeze": "e150091be6e879734ec4a97b0d9e0b7f9bfd782bc640935dd165734c15b9c4f5",
    "lineage_audit": "f0a9c0f17674b9d236a2678c0a06fd40a6ef6a75eb397047ce12b24ce5353963",
    "lineage_sidecar": "92f42eb5288f2b35d00d49212d4f012c0591d7493ff2db3b88c1083f1e0e51de",
    "lineage_case_matrix": "753ac01ac8e772fdacaa7756900dfad621a88be137a0e946adcd3702349078ec",
    "case_results": "4648b8e320f535001922f13a969d1482433bfa15f88233cf9a7e70b06cafed6c",
    "raw_traces": "d7ddf2a9a47ba62a85a7d1b85f069cc9593fd8f46cc4a01c1f3c8a055698cec2",
    "attempt_ledger": "723fe40cd727db9f553049daccfa7e3cf5489ce6eabee09a7dbea66fd447626b",
    "metric_registry": "de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056",
    "scoring_rubric": "a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899",
    "frozen_aggregator": "01aea00ad6a644a44d63a6c31e4bf372f43b53b45f9bc1b9bd7d2649e8522395",
}

SOURCE_PATHS = {
    "adjudication": ADJ, "adjudication_freeze": ADJ_FREEZE,
    "adjudication_audit": ADJ_AUDIT, "run_input_freeze": RUN_FREEZE,
    "lineage_audit": LINEAGE_AUDIT, "lineage_sidecar": SIDECAR,
    "lineage_case_matrix": MATRIX, "case_results": RESULTS,
    "raw_traces": TRACES, "attempt_ledger": LEDGER,
    "metric_registry": REGISTRY, "scoring_rubric": RUBRIC,
    "frozen_aggregator": ROOT / "scripts/aggregate_step9_30c_v4.py",
}

import sys
sys.path.insert(0, str(ROOT))
from scripts import aggregate_step9_30c_v4 as frozen_agg  # noqa: E402
from scripts import v4_adjudication_contract as contract  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def durable_new(path: Path, payload: bytes):
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def verify_sources():
    for label, path in SOURCE_PATHS.items():
        if not path.is_file() or sha(path) != EXPECTED_HASHES[label]:
            raise RuntimeError(f"FAIL CLOSED: frozen {label} identity mismatch")
    adj_freeze, adj_audit = read_json(ADJ_FREEZE), read_json(ADJ_AUDIT)
    run_freeze, lineage_audit = read_json(RUN_FREEZE), read_json(LINEAGE_AUDIT)
    if not (adj_freeze.get("validation_status") == "PASS"
            and adj_freeze.get("adjudication_sha256") == EXPECTED_ADJ_SHA
            and adj_freeze.get("case_count") == 40
            and adj_freeze.get("evaluation_id") == EVALUATION_ID
            and adj_freeze.get("attempt_id") == ATTEMPT_ID
            and adj_freeze.get("reviewer_type") == "SINGLE_AI_REVIEWER"):
        raise RuntimeError("FAIL CLOSED: Step 9.46 freeze identity/eligibility mismatch")
    if not (adj_audit.get("status") == "PASS"
            and adj_audit.get("adjudicated_case_count") == 40
            and adj_audit.get("required_reviewer_fields_complete") is True
            and adj_audit.get("score_ranges_valid") is True
            and adj_audit.get("ask_classifications_complete") is True
            and adj_audit.get("critical_failure_case_ids") == []
            and adj_audit.get("harmful_failure_case_ids") == []
            and adj_audit.get("adjudication_sha256") == EXPECTED_ADJ_SHA):
        raise RuntimeError("FAIL CLOSED: Step 9.46 consistency audit mismatch")
    if not (run_freeze.get("evaluation_id") == EVALUATION_ID
            and run_freeze.get("attempt_id") == ATTEMPT_ID
            and run_freeze.get("authorization_id") == AUTHORIZATION_ID
            and run_freeze.get("shared_evaluation_identities", {}).get("case_order_fingerprint_sha256") == EXPECTED_ORDER_SHA):
        raise RuntimeError("FAIL CLOSED: formal V2 run identity/order pin mismatch")
    for item in run_freeze.get("artifact_files", []):
        path = ROOT / item["path"]
        if not path.is_file() or path.stat().st_size != item["byte_size"] or sha(path) != item["sha256"]:
            raise RuntimeError(f"FAIL CLOSED: formal frozen artifact mismatch: {item['path']}")
    if not (lineage_audit.get("step") == "9.45a"
            and lineage_audit.get("evaluation_id") == EVALUATION_ID
            and lineage_audit.get("attempt_id") == ATTEMPT_ID
            and lineage_audit.get("case_result_count") == 40
            and lineage_audit.get("raw_trace_count") == 40
            and lineage_audit.get("case_order_fingerprint_sha256") == EXPECTED_ORDER_SHA
            and lineage_audit.get("no_scoring") is True
            and lineage_audit.get("no_aggregate") is True):
        raise RuntimeError("FAIL CLOSED: lineage audit identity/status mismatch")
    return adj_freeze, adj_audit, run_freeze, lineage_audit


def validate_records_v2(records, mode):
    if mode != "completed" or len(records) != 40:
        raise RuntimeError("FAIL CLOSED: only the frozen 40-row Step 9.46 adjudication is accepted")
    for row in records:
        facts, j = row["immutable_execution_facts"], row["reviewer_judgments"]
        scores = j.get("dimension_scores")
        if not isinstance(scores, dict) or set(scores) != set(contract.DIMENSIONS):
            raise RuntimeError("FAIL CLOSED: frozen dimension scores are incomplete")
        if any(type(scores[k]) is not int or not 0 <= scores[k] <= maximum
               for k, maximum in contract.DIMENSIONS.items()):
            raise RuntimeError("FAIL CLOSED: frozen dimension score is out of range")
        if type(j.get("total_score")) is not int or j["total_score"] != sum(scores.values()):
            raise RuntimeError("FAIL CLOSED: frozen total does not equal dimension sum")
        if j.get("completion_judgment") not in {"complete", "partial", "not_complete"} or type(j.get("validity_judgment")) is not bool:
            raise RuntimeError("FAIL CLOSED: completion/answer validity judgment is malformed")
        ask = j.get("ask_quality", {})
        counts = ask.get("counts", {})
        if (ask.get("denominator") != facts.get("ASK_count")
                or set(counts) != set(contract.ASK_CATEGORIES)
                or any(type(counts[k]) is not int or counts[k] < 0 for k in contract.ASK_CATEGORIES)
                or sum(counts.values()) != facts.get("ASK_count")):
            raise RuntimeError("FAIL CLOSED: ASK adjudication does not reconcile to immutable facts")
        necessary = j.get("necessary_ask_preservation", {})
        target_rows = necessary.get("target_adjudications")
        if (not isinstance(target_rows, list)
                or any(not isinstance(x, dict) or not {"target_id", "classification"}.issubset(x)
                       or not isinstance(x["target_id"], str) or not x["target_id"]
                       or x["classification"] not in contract.ASK_CATEGORIES for x in target_rows)
                or len({x["target_id"] for x in target_rows}) != len(target_rows)
                or type(necessary.get("acquired_targets")) is not int
                or type(necessary.get("oracle_required_targets")) is not int
                or not 0 <= necessary["acquired_targets"] <= necessary["oracle_required_targets"]):
            raise RuntimeError("FAIL CLOSED: Step 9.46 target-preservation adjudication malformed")
        for tool in ("RETRIEVE", "READ_DIARY"):
            values = j.get("tool_use_appropriateness", {}).get(tool)
            if not isinstance(values, list) or len(values) != facts.get(f"{tool}_count") or any(x not in contract.TOOL_CATEGORIES for x in values):
                raise RuntimeError(f"FAIL CLOSED: {tool} appropriateness judgments do not match facts")
        critical = j.get("critical_failure", {})
        if type(critical.get("present")) is not bool or not isinstance(critical.get("types"), list) or critical["present"] != bool(critical["types"]):
            raise RuntimeError("FAIL CLOSED: critical-failure judgment malformed")
        if type(j.get("harmful_failure")) is not bool:
            raise RuntimeError("FAIL CLOSED: harmful-failure judgment malformed")
        if not isinstance(j.get("failure_attribution"), dict):
            raise RuntimeError("FAIL CLOSED: failure attribution is missing")


def main():
    targets = [METRICS, SUMMARY, REPORT, FREEZE, AUDIT]
    if any(path.exists() for path in targets):
        raise RuntimeError("FAIL CLOSED: Step 9.47 append-only output already exists")
    original_aggregator_hash = sha(ROOT / "scripts/aggregate_step9_30c_v4.py")
    if original_aggregator_hash != EXPECTED_HASHES["frozen_aggregator"]:
        raise RuntimeError("FAIL CLOSED: frozen aggregation implementation changed")
    adj_freeze, adj_audit, run_freeze, lineage_audit = verify_sources()

    records, sidecar = read_jsonl(ADJ), read_jsonl(SIDECAR)
    results, traces, matrix, ledger = map(read_jsonl, (RESULTS, TRACES, MATRIX, LEDGER))
    if len(records) != 40 or len(sidecar) != 40 or len(results) != 40 or len(traces) != 40 or len(matrix) != 40:
        raise RuntimeError("FAIL CLOSED: frozen 40-case coverage mismatch")
    get_case_id = lambda row: row["immutable_execution_facts"]["case_id"]
    ids = [get_case_id(row) for row in records]
    source_orders = [ids, [r["case_id"] for r in sidecar], [r["case_id"] for r in results],
                     [r["case_id"] for r in traces], [r["case_id"] for r in matrix]]
    if any(len(set(order)) != 40 for order in source_orders) or any(order != ids for order in source_orders[1:]):
        raise RuntimeError("FAIL CLOSED: case IDs are not unique and identically ordered across frozen inputs")
    order_hash = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
    if order_hash != EXPECTED_ORDER_SHA:
        raise RuntimeError("FAIL CLOSED: adjudication case order fingerprint mismatch")
    task_counts = Counter(row["immutable_execution_facts"]["task_type"] for row in records)
    expected_tasks = {name: 10 for name in contract.TASK_TYPES}
    if dict(task_counts) != expected_tasks or dict(adj_freeze["task_distribution"]) != expected_tasks:
        raise RuntimeError("FAIL CLOSED: task distribution mismatch")
    if len(ledger) != 86 or ledger[-1].get("status") != "COMPLETED":
        raise RuntimeError("FAIL CLOSED: formal attempt ledger is not completed as frozen")
    completion_events = [e for e in ledger if e.get("attempt_id") == ATTEMPT_ID and e.get("status") == "COMPLETED"]
    if len(completion_events) != 1 or completion_events[0].get("cases_started") != 40 or completion_events[0].get("cases_completed") != 40:
        raise RuntimeError("FAIL CLOSED: formal attempt completion identity mismatch")
    results_by_id, traces_by_id = ({r["case_id"]: r for r in results}, {r["case_id"]: r for r in traces})
    result_lines, trace_lines = RESULTS.read_bytes().splitlines(keepends=True), TRACES.read_bytes().splitlines(keepends=True)
    for index, record in enumerate(records):
        facts = record["immutable_execution_facts"]
        case_id = facts["case_id"]
        result, trace = results_by_id[case_id], traces_by_id[case_id]
        if facts.get("evaluation_id") != EVALUATION_ID or facts.get("attempt_id") != ATTEMPT_ID:
            raise RuntimeError(f"FAIL CLOSED: adjudication execution identity mismatch for {case_id}")
        for key in ("evaluation_id", "case_id", "task_type", "final_status", "action_path", "ASK_count",
                    "RETRIEVE_count", "READ_DIARY_count", "turn_count", "step_count", "tool_calls", "latency_ms", "lineage_ready"):
            if result.get(key) != facts.get(key):
                raise RuntimeError(f"FAIL CLOSED: formal result facts mismatch for {case_id}/{key}")
        if trace.get("evaluation_id") != EVALUATION_ID or trace.get("case_id") != case_id:
            raise RuntimeError(f"FAIL CLOSED: raw trace identity mismatch for {case_id}")
        provenance = record["execution_provenance"]
        for kind, source, lines in (("case_result", RESULTS, result_lines), ("raw_trace", TRACES, trace_lines)):
            ref = provenance[kind]
            if ref.get("path") != str(source.relative_to(ROOT)) or ref.get("line_number") != index + 1:
                raise RuntimeError(f"FAIL CLOSED: per-case provenance location mismatch for {case_id}/{kind}")
            if hashlib.sha256(lines[index].rstrip(b"\r\n")).hexdigest() != ref.get("line_sha256"):
                raise RuntimeError(f"FAIL CLOSED: per-case provenance hash mismatch for {case_id}/{kind}")
        review = record["review_provenance"]
        if (review.get("rubric_path") != str(RUBRIC.relative_to(ROOT))
                or review.get("rubric_sha256") != EXPECTED_HASHES["scoring_rubric"]
                or review.get("metric_registry_path") != str(REGISTRY.relative_to(ROOT))
                or review.get("metric_registry_sha256") != EXPECTED_HASHES["metric_registry"]
                or review.get("reviewer") != "Codex AI reviewer (user-authorized single reviewer; not a human reviewer)"
                or "single-AI-reviewer" not in review.get("review_method", "")):
            raise RuntimeError(f"FAIL CLOSED: reviewer/registry provenance mismatch for {case_id}")
    frozen_agg.validate_records = validate_records_v2
    frozen_agg.EXPECTED_LINEAGE = {
        "FORMAL_LINEAGE_READY": 27,
        "DERIVED_LINEAGE_COMPLETE": 8,
        "INCOMPLETE_FORMAL_BUT_ADJUDICATABLE": 5,
    }
    data = frozen_agg.aggregate_records(records, sidecar)
    case_rows = data.pop("case_level_rows")
    data["ask_quality"].pop("category_rates", None)
    data["ask_quality"]["LOW_VALUE_ASK_RATE"] = data["ask_quality"].pop("REDUNDANT_OR_IRRELEVANT_RATE")
    data["tool_resource_behavior"].pop("ask_per_case", None)
    # This is intentionally a V2-only descriptive aggregate: comparison fields are omitted.
    data.pop("historical_comparability", None)
    data["token_usage_status"] = "NOT_MEASURED"
    data["aggregation_provenance"] = {
        "metric_registry_path": str(REGISTRY.relative_to(ROOT)),
        "metric_registry_sha256": EXPECTED_HASHES["metric_registry"],
        "scoring_rubric_path": str(RUBRIC.relative_to(ROOT)),
        "scoring_rubric_sha256": EXPECTED_HASHES["scoring_rubric"],
        "comparison_generated": False,
    }
    if (data["adjudicated_case_count"] != 40 or data["valid_case_count"] != 40
            or data["needs_review_case_count"] != 0 or data["task_distribution"] != dict(sorted(task_counts.items()))):
        raise RuntimeError("FAIL CLOSED: aggregate coverage/validity consistency failure")
    ask = data["ask_quality"]
    if sum(ask["category_counts"].values()) != ask["TOTAL_ASK_COUNT"]:
        raise RuntimeError("FAIL CLOSED: ASK categories do not sum to observed ASK count")
    if ask["LOW_VALUE_ASK_RATE"]["numerator"] != ask["REDUNDANT_ASK_COUNT"] + ask["IRRELEVANT_ASK_COUNT"]:
        raise RuntimeError("FAIL CLOSED: low-value ASK numerator mismatch")
    if data["failures"]["CRITICAL_FAILURE_COUNT"] != len(data["failures"]["CRITICAL_FAILURE_CASE_IDS"]):
        raise RuntimeError("FAIL CLOSED: critical failure IDs/count mismatch")
    if data["failures"]["HARMFUL_FAILURE_COUNT"] != len(data["failures"]["HARMFUL_FAILURE_CASE_IDS"]):
        raise RuntimeError("FAIL CLOSED: harmful failure IDs/count mismatch")
    if data["lineage"]["FORMAL_LINEAGE_READY"] != 27 or data["lineage"]["DERIVED_LINEAGE_COMPLETE"] != 8 or data["lineage"]["INCOMPLETE_FORMAL_BUT_ADJUDICATABLE"] != 5:
        raise RuntimeError("FAIL CLOSED: lineage counts mismatch")

    input_hashes = {label: sha(path) for label, path in SOURCE_PATHS.items()}
    metric_bytes = (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    summary_bytes = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in case_rows).encode()
    outputs_pre = {
        "aggregate": hashlib.sha256(metric_bytes).hexdigest(),
        "case_summary": hashlib.sha256(summary_bytes).hexdigest(),
    }
    report_lines = [
        "# Step 9.47 — Treatment-V2 Frozen Aggregation", "",
        "Status: PASS — offline descriptive aggregation of the frozen Step 9.46 adjudication; no rerun or re-adjudication.",
        "Scope: Treatment-V2 only. No Baseline/V1/V2 comparison, delta, significance, causal, or generalization claim was computed.",
        f"", f"- Cases: {data['adjudicated_case_count']}; task strata: " + "; ".join(f"{k} {v}" for k, v in data["task_distribution"].items()) + ".",
        f"- Overall descriptive mean: {data['scores']['overall']['mean']}/100 (n=40).",
        "- Task means: " + "; ".join(f"{k} {v['mean']} (n={v['denominator']})" for k, v in data["scores"]["task_type_means"].items()) + ".",
        "- Dimension means: " + "; ".join(f"{k} {v['mean']}/{v['maximum']}" for k, v in data["scores"]["dimensions"].items()) + ".",
        f"- Completion: {data['completion_and_validity']['overall']['rate']['numerator']}/40; answer validity: {data['completion_and_validity']['overall']['validity_rate']['numerator']}/40.",
        f"- ASK categories: {ask['category_counts']}; low-value {ask['LOW_VALUE_ASK_RATE']['numerator']}/{ask['LOW_VALUE_ASK_RATE']['denominator']} (denominator: all ASK events).",
        f"- Execution: RETRIEVE {data['tool_resource_behavior']['counts']['RETRIEVE']}; READ_DIARY {data['tool_resource_behavior']['counts']['READ_DIARY']}; actual tool calls {data['tool_resource_behavior']['counts']['TOOL_CALL']}; turns {data['efficiency']['turns_per_case']['numerator']}; steps {data['efficiency']['steps_per_case']['numerator']}; mean latency {data['efficiency']['latency_ms']['overall']['mean_ms']} ms.",
        f"- Token usage: {data['token_usage_status']}; reviewer: SINGLE_AI_REVIEWER (not human), IRR NOT_MEASURED.",
        f"- Failures: critical {data['failures']['CRITICAL_FAILURE_COUNT']}; harmful {data['failures']['HARMFUL_FAILURE_COUNT']}.",
        f"- Lineage provenance only: formal ready 27; derived complete 8; true incomplete adjudicatable 5; indeterminate 0. No lineage score penalty.",
        "- No V2 rerun; no model/Agent/RAG execution; no V5 access.", "", "## Integrity", "",
        f"- Frozen inputs were verified before and after persistence; adjudication SHA-256 `{EXPECTED_ADJ_SHA}`.",
        f"- Case-order SHA-256 `{EXPECTED_ORDER_SHA}`; aggregation consistency audit PASS.",
        "- Input hashes:",
    ] + [f"  - {key}: `{value}`" for key, value in sorted(input_hashes.items())]
    report_bytes = ("\n".join(report_lines) + "\n").encode()
    output_hashes = {**outputs_pre, "report": hashlib.sha256(report_bytes).hexdigest()}
    for name, path in SOURCE_PATHS.items():
        if sha(path) != input_hashes[name]:
            raise RuntimeError(f"FAIL CLOSED: input changed before persistence: {name}")
    durable_new(METRICS, metric_bytes)
    durable_new(SUMMARY, summary_bytes)
    durable_new(REPORT, report_bytes)
    freeze = {
        "step": "9.47", "freeze_type": "TREATMENT_V2_FROZEN_AGGREGATION_ONLY",
        "status": "PASS", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_id": EVALUATION_ID, "authorization_id": AUTHORIZATION_ID, "attempt_id": ATTEMPT_ID,
        "case_count": 40, "task_distribution": dict(sorted(task_counts.items())),
        "input_hashes": input_hashes, "output_hashes": output_hashes,
        "metric_registry_path": str(REGISTRY.relative_to(ROOT)),
        "metric_registry_sha256": EXPECTED_HASHES["metric_registry"],
        "aggregation_semantics_source": "scripts/aggregate_step9_30c_v4.py",
        "aggregation_semantics_source_sha256": EXPECTED_HASHES["frozen_aggregator"],
        "consistency_audit": "PASS", "lineage_is_provenance_only": True,
        "baseline_v1_v2_comparison_generated": False,
        "v2_rerun": False, "model_called_for_case_execution": False,
        "agent_called": False, "rag_called": False, "v5_accessed": False,
        "source_artifacts_modified": False,
    }
    freeze_bytes = (json.dumps(freeze, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    durable_new(FREEZE, freeze_bytes)
    freeze_hash = sha(FREEZE)
    for key, path in (("aggregate", METRICS), ("case_summary", SUMMARY), ("report", REPORT)):
        if sha(path) != output_hashes[key]:
            raise RuntimeError(f"FAIL CLOSED: persisted output hash mismatch: {key}")
    for name, path in SOURCE_PATHS.items():
        if sha(path) != input_hashes[name]:
            raise RuntimeError(f"FAIL CLOSED: source modified during persistence: {name}")
    audit = {
        "step": "9.47", "audit_status": "PASS", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_id": EVALUATION_ID, "attempt_id": ATTEMPT_ID,
        "case_count_consumed": 40, "unique_case_ids": 40,
        "case_order_fingerprint_sha256": order_hash,
        "task_distribution": dict(sorted(task_counts.items())),
        "ask_category_sum_matches_total": True, "failure_counts_match_ids": True,
        "completion_and_validity_reconciled": True, "lineage_counts_reconciled": True,
        "all_frozen_input_hashes_unchanged": True, "all_outputs_hash_verified": True,
        "aggregate_consistency_audit": "PASS", "freeze_sha256": freeze_hash,
        "outputs": {"aggregate": output_hashes["aggregate"], "case_summary": output_hashes["case_summary"], "report": output_hashes["report"]},
        "baseline_v1_v2_comparison_generated": False, "v2_rerun": False,
        "model_called_for_case_execution": False, "agent_called": False, "rag_called": False, "v5_accessed": False,
    }
    audit_bytes = (json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    durable_new(AUDIT, audit_bytes)
    record = (
        "\n\n## Step 9.47 — Treatment-V2 Frozen Aggregation\n\n"
        f"PASS: offline aggregation of the frozen 40-case V2 adjudication; overall descriptive mean {data['scores']['overall']['mean']}. "
        "V2-only; no Baseline/V1/V2 comparison, rerun, model/Agent/RAG execution, or V5 access. "
        f"Aggregate SHA-256 `{output_hashes['aggregate']}`; case summary `{output_hashes['case_summary']}`; "
        f"report `{output_hashes['report']}`; freeze `{freeze_hash}`; audit `{sha(AUDIT)}`. "
        "All frozen input hashes remained unchanged; aggregate consistency audit PASS.\n"
    )
    with (ROOT / "record.md").open("a", encoding="utf-8") as stream:
        stream.write(record)
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({
        "AGGREGATED_CASE_COUNT": 40,
        "TREATMENT_V2_OVERALL": data["scores"]["overall"]["mean"],
        "KQ_MEAN": data["scores"]["task_type_means"]["KNOWLEDGE_QA"]["mean"],
        "CA_MEAN": data["scores"]["task_type_means"]["CAUSE_ASSESSMENT"]["mean"],
        "PD_MEAN": data["scores"]["task_type_means"]["PERSONALIZED_DECISION"]["mean"],
        "DA_MEAN": data["scores"]["task_type_means"]["DATA_ANALYSIS"]["mean"],
        "DIMENSION_MEANS": {k: v["mean"] for k, v in data["scores"]["dimensions"].items()},
        "TASK_COMPLETION_COUNT": data["completion_and_validity"]["overall"]["rate"]["numerator"],
        "TASK_COMPLETION_RATE": data["completion_and_validity"]["overall"]["rate"]["value"],
        "VALID_ANSWER_COUNT": data["completion_and_validity"]["overall"]["validity_rate"]["numerator"],
        "ANSWER_VALIDITY_RATE": data["completion_and_validity"]["overall"]["validity_rate"]["value"],
        "ASK_TOTAL": ask["TOTAL_ASK_COUNT"], "ASK_NECESSARY": ask["NECESSARY_ASK_COUNT"],
        "ASK_USEFUL_OPTIONAL": ask["USEFUL_OPTIONAL_ASK_COUNT"], "ASK_REDUNDANT": ask["REDUNDANT_ASK_COUNT"],
        "ASK_IRRELEVANT": ask["IRRELEVANT_ASK_COUNT"], "LOW_VALUE_ASK_COUNT": ask["LOW_VALUE_ASK_RATE"]["numerator"],
        "LOW_VALUE_ASK_RATE": ask["LOW_VALUE_ASK_RATE"]["value"],
        "RETRIEVE_TOTAL": data["tool_resource_behavior"]["counts"]["RETRIEVE"],
        "READ_DIARY_TOTAL": data["tool_resource_behavior"]["counts"]["READ_DIARY"],
        "TOOL_CALL_TOTAL": data["tool_resource_behavior"]["counts"]["TOOL_CALL"],
        "TURN_TOTAL": data["efficiency"]["turns_per_case"]["numerator"],
        "STEP_TOTAL": data["efficiency"]["steps_per_case"]["numerator"],
        "MEAN_RETRIEVE_PER_CASE": data["tool_resource_behavior"]["per_case_means"]["retrieve_per_case"]["value"],
        "MEAN_READ_DIARY_PER_CASE": data["tool_resource_behavior"]["per_case_means"]["read_diary_per_case"]["value"],
        "MEAN_TOOL_CALLS_PER_CASE": data["efficiency"]["tool_calls_per_case"]["mean"],
        "MEAN_TURNS_PER_CASE": data["efficiency"]["turns_per_case"]["mean"],
        "MEAN_STEPS_PER_CASE": data["efficiency"]["steps_per_case"]["mean"],
        "MEAN_LATENCY_MS": data["efficiency"]["latency_ms"]["overall"]["mean_ms"],
        "TOKEN_USAGE": "NOT_MEASURED",
        "CRITICAL_FAILURE_COUNT": data["failures"]["CRITICAL_FAILURE_COUNT"],
        "CRITICAL_FAILURE_CASE_IDS": data["failures"]["CRITICAL_FAILURE_CASE_IDS"],
        "HARMFUL_FAILURE_COUNT": data["failures"]["HARMFUL_FAILURE_COUNT"],
        "HARMFUL_FAILURE_CASE_IDS": data["failures"]["HARMFUL_FAILURE_CASE_IDS"],
        "FORMAL_LINEAGE_READY_COUNT": 27, "DERIVED_COMPLETE_COUNT": 8,
        "TRUE_INCOMPLETE_ADJUDICATABLE_COUNT": 5, "INDETERMINATE_COUNT": 0,
        "AGGREGATE_CONSISTENCY_AUDIT": "PASS",
        "TREATMENT_V2_AGGREGATE_SHA256": output_hashes["aggregate"],
        "freeze_sha256": freeze_hash, "audit_sha256": sha(AUDIT),
        "BASELINE_V1_V2_COMPARISON_GENERATED": "NO",
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
