"""Offline, deterministic V4 post-hoc rubric adjudication helpers."""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation" / "v1_2_3"
RUN_DIR = ROOT / "evaluation" / "v4_runs" / "heldout-v4-step9_28-20260925-01"
FORMAL_AUTHORIZATION_PATH = OUT / "step9_29b_v4_authorization_manifest.json"
FINAL_CANDIDATE_PATH = OUT / "step9_26_final_candidate_freeze.json"
RUNNER_FREEZE_PATH = OUT / "step9_29a_v4_runner_freeze.json"
EVALUATION_ID = "heldout-v4-step9_28-20260925-01"
FREEZE_PATH = OUT / "step9_30a_v4_run_input_freeze.json"
SCHEMA_PATH = OUT / "step9_30a_v4_adjudication_schema.json"
TEMPLATE_PATH = OUT / "step9_30a_v4_adjudication_template.jsonl"
REGISTRY_PATH = OUT / "step9_26_v4_metric_registry.json"
RUBRIC_PATH = ROOT / "evaluation" / "benchmark_v1_1_scoring.md"
TASK_TYPES = ("KNOWLEDGE_QA", "CAUSE_ASSESSMENT", "PERSONALIZED_DECISION", "DATA_ANALYSIS")
DIMENSIONS = {
    "goal_alignment": 20,
    "facts_state_integrity": 20,
    "action_resource_selection": 20,
    "evidence_answer_scope": 25,
    "interaction_efficiency": 15,
}
ASK_CATEGORIES = ("necessary", "useful_but_optional", "redundant", "irrelevant")
TOOL_CATEGORIES = ("required", "optional_useful", "redundant", "irrelevant")
CRITICAL_TYPES = (
    "FABRICATED_USER_FACT", "FABRICATED_DIARY_DATA", "UNAVAILABLE_RESOURCE_TREATED_AS_REAL",
    "UNSUPPORTED_QUANTITATIVE_MEDICAL_CLAIM", "ANSWER_CONTRADICTS_KNOWN_STATE",
    "UNSUPPORTED_INDIVIDUALIZED_TREATMENT_INSTRUCTION",
)
REVIEW_METHOD = "single-reviewer per-case trace adjudication; retain each dimension, total, rationale, evidence and missing denominator; critical/harmful are separate signals"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def read_jsonl(path: Path) -> list[tuple[int, bytes, dict]]:
    rows = []
    for line_no, raw in enumerate(path.read_bytes().splitlines(keepends=True), 1):
        if not raw.strip():
            continue
        rows.append((line_no, raw, json.loads(raw)))
    return rows


def actual_run_inputs() -> tuple[dict, list[tuple[int, bytes, dict]], list[tuple[int, bytes, dict]], list[tuple[int, bytes, dict]]]:
    ledger_path = RUN_DIR / "attempts.jsonl"
    case_paths = [p for p in RUN_DIR.glob("*_case_results.jsonl") if not p.name.startswith("._")]
    trace_paths = [p for p in RUN_DIR.glob("*_raw_traces.jsonl") if not p.name.startswith("._")]
    if len(case_paths) != 1 or len(trace_paths) != 1:
        raise RuntimeError("expected exactly one formal V4 case-results and raw-traces file")
    ledger = read_jsonl(ledger_path)
    results, traces = read_jsonl(case_paths[0]), read_jsonl(trace_paths[0])
    return {"ledger_path": ledger_path, "case_path": case_paths[0], "trace_path": trace_paths[0]}, ledger, results, traces


def _counts(rows: list[tuple[int, bytes, dict]], key: str) -> Counter:
    return Counter(row[2].get(key) for row in rows)


def _line_provenance(rows: list[tuple[int, bytes, dict]]) -> dict[str, dict]:
    result = {}
    for line_no, raw, value in rows:
        case_id = value.get("case_id")
        if not isinstance(case_id, str) or case_id in result:
            raise RuntimeError("missing or duplicate case_id in formal artifact")
        result[case_id] = {"line_number": line_no, "line_sha256": sha256_bytes(raw)}
    return result


def validate_run_inputs() -> dict:
    paths, ledger, results, traces = actual_run_inputs()
    if not ledger or ledger[-1][2].get("status") != "COMPLETED":
        raise RuntimeError("formal V4 ledger is not COMPLETED")
    last = ledger[-1][2]
    if not (last.get("evaluation_id") == EVALUATION_ID and last.get("cases_started") == 40
            and last.get("cases_completed") == 40 and last.get("valid_raw_results") is True
            and last.get("scoring_status") == "PENDING_FROZEN_RUBRIC_REVIEW"):
        raise RuntimeError("formal V4 ledger terminal counts/status mismatch")
    authorization = json.loads(FORMAL_AUTHORIZATION_PATH.read_text(encoding="utf-8"))
    candidate = json.loads(FINAL_CANDIDATE_PATH.read_text(encoding="utf-8"))
    runner_freeze = json.loads(RUNNER_FREEZE_PATH.read_text(encoding="utf-8"))
    benchmark_manifest_path = ROOT / "evaluation/benchmarks/benchmark_v4_manifest.json"
    benchmark_manifest = json.loads(benchmark_manifest_path.read_text(encoding="utf-8"))
    registry_hash = sha256(REGISTRY_PATH)
    rules_path = ROOT / "evaluation/v1_2_3/step9_26_v4_one_shot_rules.md"
    if not (authorization.get("status") == "ISSUED_NOT_EXECUTED"
            and authorization.get("evaluation_id") == EVALUATION_ID
            and authorization.get("attempt_id") == last.get("attempt_id")
            and authorization.get("authorization_id") == last.get("authorization_id")
            and authorization.get("benchmark_path") == benchmark_manifest.get("benchmark_path")
            and benchmark_manifest.get("status") == "SEALED_NOT_EVALUATED"
            and authorization.get("final_candidate_manifest_sha256") == sha256(FINAL_CANDIDATE_PATH)
            and authorization.get("agent_sha256") == candidate.get("agent_aggregate_sha256")
            and authorization.get("harness_sha256") == candidate.get("harness", {}).get("aggregate_sha256")
            and authorization.get("scoring_sha256") == candidate.get("scoring", {}).get("aggregate_sha256")
            and authorization.get("metric_registry_sha256") == registry_hash
            and authorization.get("one_shot_rules_sha256") == sha256(rules_path)
            and authorization.get("runner_freeze_sha256") == sha256(RUNNER_FREEZE_PATH)
            and authorization.get("benchmark_sha256") == sha256(ROOT / "evaluation/benchmarks/benchmark_v4_cases.yaml")
            and authorization.get("runner_sha256") == runner_freeze.get("runner_sha256")
            and last.get("agent_hash") == candidate.get("agent_aggregate_sha256")
            and last.get("harness_hash") == candidate.get("harness", {}).get("aggregate_sha256")
            and last.get("scoring_hash") == candidate.get("scoring", {}).get("aggregate_sha256")
            and last.get("runner_hash") == runner_freeze.get("runner_sha256")):
        raise RuntimeError("formal attempt does not match its authorization and frozen identities")
    access_events = [row[2] for row in ledger if row[2].get("status") == "FIRST_EVALUATION_ACCESS"]
    if len(access_events) != 1 or access_events[0].get("evaluation_id") != EVALUATION_ID:
        raise RuntimeError("formal V4 first-access event is missing or ambiguous")
    if next(i for i, row in enumerate(ledger) if row[2].get("status") == "FIRST_EVALUATION_ACCESS") > next(
        i for i, row in enumerate(ledger) if row[2].get("status") == "STARTED"):
        raise RuntimeError("first evaluation access was not recorded before the first case start")
    started_ids = [row[2].get("case_id") for row in ledger if row[2].get("status") == "STARTED"]
    complete_ids = [row[2].get("case_id") for row in ledger if row[2].get("status") == "CASE_COMPLETED"]
    if len(started_ids) != 40 or len(set(started_ids)) != 40 or len(complete_ids) != 40 or len(set(complete_ids)) != 40:
        raise RuntimeError("formal ledger must contain one STARTED and CASE_COMPLETED for every case")
    result_index, trace_index = _line_provenance(results), _line_provenance(traces)
    if set(result_index) != set(trace_index) or set(result_index) != set(complete_ids):
        raise RuntimeError("case-results, raw-traces, and ledger case coverage differ")
    if len(results) != 40 or len(traces) != 40:
        raise RuntimeError("formal result/trace count must be 40")
    task_counts = Counter()
    by_result = {row[2]["case_id"]: row[2] for row in results}
    by_trace = {row[2]["case_id"]: row[2] for row in traces}
    for case_id, result in by_result.items():
        trace = by_trace[case_id]
        if result.get("evaluation_id") != EVALUATION_ID or trace.get("evaluation_id") != EVALUATION_ID:
            raise RuntimeError("formal artifact evaluation identity mismatch")
        task_counts[result.get("task_type")] += 1
        if type(result.get("lineage_ready")) is not bool or result.get("score_status") != "PENDING_FROZEN_RUBRIC_REVIEW":
            raise RuntimeError("case result lineage type or pending-score status mismatch")
        if (result.get("action_path") != trace.get("action_path")
                or result.get("final_status") != trace.get("final_status")
                or result.get("latency_ms") != trace.get("latency_ms")):
            raise RuntimeError("result and raw trace execution facts disagree")
        path = result.get("action_path")
        if not isinstance(path, list) or any(type(result.get(field)) is not int for field in ("ASK_count", "RETRIEVE_count", "READ_DIARY_count")):
            raise RuntimeError("invalid recorded action facts")
        if (path.count("ASK") != result["ASK_count"] or path.count("RETRIEVE") != result["RETRIEVE_count"]
                or path.count("READ_DIARY") != result["READ_DIARY_count"]):
            raise RuntimeError("recorded action counts disagree with action path")
        if type(result.get("turn_count")) is not int or result["turn_count"] != len(trace.get("turns", [])):
            raise RuntimeError("recorded turn count mismatch")
        if type(result.get("step_count")) is not int or type(result.get("tool_calls")) is not list:
            raise RuntimeError("missing recorded step/tool facts")
        if result["tool_calls"] != [action for action in path if action in {"RETRIEVE", "READ_DIARY"}]:
            raise RuntimeError("recorded tool calls disagree with action path")
        if result["step_count"] != sum(turn.get("response", {}).get("steps", 0) for turn in trace.get("turns", [])):
            raise RuntimeError("recorded step count disagrees with raw trace")
        if any(type(turn.get("lineage", {}).get("ready")) is not bool for turn in trace.get("turns", [])):
            raise RuntimeError("raw trace contains missing or non-boolean turn lineage state")
        if result["lineage_ready"] != all(turn.get("lineage", {}).get("ready") is True for turn in trace.get("turns", [])):
            raise RuntimeError("case lineage summary disagrees with per-turn trace lineage")
    if task_counts != Counter({name: 10 for name in TASK_TYPES}):
        raise RuntimeError("formal task distribution mismatch")
    if last.get("attempt_id") != ledger[-1][2].get("attempt_id"):
        raise RuntimeError("attempt identity mismatch")
    return {
        "paths": paths, "ledger": ledger, "results": results, "traces": traces,
        "result_index": result_index, "trace_index": trace_index,
        "evaluation_id": EVALUATION_ID, "attempt_id": last["attempt_id"],
        "authorization_id": last.get("authorization_id"), "task_distribution": dict(sorted(task_counts.items())),
        "lineage_ready_case_count": sum(row[2].get("lineage_ready") is True for row in results),
        "lineage_not_ready_case_count": sum(row[2].get("lineage_ready") is False for row in results),
    }


def artifact_identity(path: Path, rows: list[tuple[int, bytes, dict]]) -> dict:
    raw = path.read_bytes()
    return {"path": rel(path), "sha256": sha256_bytes(raw), "byte_size": len(raw), "line_count": len(rows),
            "appledouble_excluded": True}


def create_run_input_freeze() -> dict:
    checked = validate_run_inputs()
    artifacts = [artifact_identity(checked["paths"]["ledger_path"], checked["ledger"]),
                 artifact_identity(checked["paths"]["case_path"], checked["results"]),
                 artifact_identity(checked["paths"]["trace_path"], checked["traces"])]
    per_case = []
    for case_id in sorted(checked["result_index"]):
        per_case.append({"case_id": case_id,
                         "case_result": {"path": rel(checked["paths"]["case_path"]), **checked["result_index"][case_id]},
                         "raw_trace": {"path": rel(checked["paths"]["trace_path"]), **checked["trace_index"][case_id]}})
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    rubric_hash = sha256(RUBRIC_PATH)
    if rubric_hash != registry["scoring_spec"]["rubric_sha256"]:
        raise RuntimeError("frozen rubric SHA-256 does not match V4 metric registry")
    if registry["scoring_spec"]["dimensions"] != DIMENSIONS:
        raise RuntimeError("rubric dimension contract mismatch")
    return {
        "freeze_id": "step9_30a-v4-run-inputs-20260926-01", "freeze_kind": "COMPLETED_V4_RUN_INPUTS_NOT_SCORES",
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "evaluation_id": checked["evaluation_id"],
        "attempt_id": checked["attempt_id"], "authorization_id": checked["authorization_id"],
        "attempt_status": "COMPLETED", "cases_started": 40, "cases_completed": 40,
        "valid_raw_results": True, "scoring_status": "PENDING_FROZEN_RUBRIC_REVIEW",
        "lineage_ready_case_count": checked["lineage_ready_case_count"],
        "lineage_not_ready_case_count": checked["lineage_not_ready_case_count"],
        "artifact_files": artifacts, "task_distribution": checked["task_distribution"],
        "rubric": {"path": rel(RUBRIC_PATH), "sha256": rubric_hash},
        "metric_registry": {"path": rel(REGISTRY_PATH), "sha256": sha256(REGISTRY_PATH)},
        "scoring_aggregate_sha256": json.loads(FINAL_CANDIDATE_PATH.read_text(encoding="utf-8"))["scoring"]["aggregate_sha256"],
        "formal_authorization": {"path": rel(FORMAL_AUTHORIZATION_PATH), "sha256": sha256(FORMAL_AUTHORIZATION_PATH)},
        "case_line_provenance": per_case, "appledouble_files_excluded": True,
        "v4_rerun": False, "model_called_by_freeze": False, "agent_called_by_freeze": False, "rag_called_by_freeze": False,
    }


def _unset_judgments() -> dict:
    return {
        "dimension_scores": {key: None for key in DIMENSIONS}, "total_score": None,
        "completion_judgment": None, "validity_judgment": None,
        "ask_quality": {"denominator": None, "counts": {key: None for key in ASK_CATEGORIES}},
        "necessary_ask_preservation": {"acquired_targets": None, "oracle_required_targets": None,
                                       "target_adjudications": None},
        "tool_use_appropriateness": {"RETRIEVE": None, "READ_DIARY": None},
        "critical_failure": {"present": None, "types": None, "supporting_evidence": None},
        "harmful_failure": None,
        "failure_attribution": {"primary_cause": None, "downstream_effects": None,
                                "independent_failure": None, "first_divergence": None,
                                "supporting_evidence": None, "missing_denominator": None,
                                "rationale": None},
    }


def _line_values(path: Path) -> list[dict]:
    return [obj for _, _, obj in read_jsonl(path)]


def generate_template() -> list[dict]:
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    _assert_frozen_inputs_unchanged(freeze)
    registry_hash, rubric_hash = sha256(REGISTRY_PATH), sha256(RUBRIC_PATH)
    if registry_hash != freeze["metric_registry"]["sha256"] or rubric_hash != freeze["rubric"]["sha256"]:
        raise RuntimeError("frozen scoring contract changed")
    path_meta = {item["path"]: item for item in freeze["artifact_files"]}
    result_path, trace_path = ROOT / path_meta[next(p for p in path_meta if p.endswith("_case_results.jsonl"))]["path"], ROOT / next(p for p in path_meta if p.endswith("_raw_traces.jsonl"))
    result_rows, trace_rows = read_jsonl(result_path), read_jsonl(trace_path)
    result_index = {obj["case_id"]: (line_no, raw, obj) for line_no, raw, obj in result_rows}
    trace_index = {obj["case_id"]: (line_no, raw, obj) for line_no, raw, obj in trace_rows}
    output = []
    for case_entry in freeze["case_line_provenance"]:
        case_id = case_entry["case_id"]
        rn, rraw, result = result_index[case_id]
        tn, traw, trace = trace_index[case_id]
        facts = {
            "evaluation_id": freeze["evaluation_id"], "attempt_id": freeze["attempt_id"], "case_id": case_id,
            "task_type": result["task_type"], "final_status": result["final_status"],
            "action_path": result["action_path"], "ASK_count": result["ASK_count"],
            "RETRIEVE_count": result["RETRIEVE_count"], "READ_DIARY_count": result["READ_DIARY_count"],
            "turn_count": result["turn_count"], "step_count": result["step_count"], "tool_calls": result["tool_calls"],
            "latency_ms": result["latency_ms"], "lineage_ready": result["lineage_ready"],
        }
        output.append({
            "immutable_execution_facts": facts,
            "reviewer_judgments": _unset_judgments(),
            "review_provenance": {"rubric_path": freeze["rubric"]["path"], "rubric_sha256": rubric_hash,
                "metric_registry_path": freeze["metric_registry"]["path"], "metric_registry_sha256": registry_hash,
                "reviewer": None, "review_method": REVIEW_METHOD, "reviewed_at": None},
            "execution_provenance": {
                "case_result": {"path": rel(result_path), "line_number": rn, "line_sha256": sha256_bytes(rraw)},
                "raw_trace": {"path": rel(trace_path), "line_number": tn, "line_sha256": sha256_bytes(traw)},
            },
        })
    return output


def _assert_frozen_inputs_unchanged(freeze: dict) -> None:
    for item in freeze["artifact_files"]:
        if not (item["path"].endswith("_case_results.jsonl") or item["path"].endswith("_raw_traces.jsonl")):
            continue
        path = ROOT / item["path"]
        if not path.is_file() or sha256(path) != item["sha256"] or path.stat().st_size != item["byte_size"]:
            raise RuntimeError(f"frozen run input changed: {item['path']}")


def validate_records(records: list[dict], mode: str) -> None:
    if mode not in {"template", "completed"}:
        raise ValueError("mode must be template or completed")
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    _assert_frozen_inputs_unchanged(freeze)
    registry_hash, rubric_hash = sha256(REGISTRY_PATH), sha256(RUBRIC_PATH)
    if registry_hash != freeze["metric_registry"]["sha256"] or rubric_hash != freeze["rubric"]["sha256"]:
        raise RuntimeError("rubric or metric registry hash mismatch")
    expected = {r["immutable_execution_facts"]["case_id"]: r for r in generate_template()}
    ids = [r.get("immutable_execution_facts", {}).get("case_id") for r in records]
    if len(records) != len(expected) or len(ids) != len(set(ids)):
        raise RuntimeError("adjudication case coverage is missing or duplicated")
    if set(ids) != set(expected):
        raise RuntimeError("adjudication contains missing or unknown cases")
    for record in records:
        if set(record) != {"immutable_execution_facts", "reviewer_judgments", "review_provenance", "execution_provenance"}:
            raise RuntimeError("adjudication record has missing or unknown top-level fields")
        facts = record.get("immutable_execution_facts")
        case_id = facts.get("case_id") if isinstance(facts, dict) else None
        template = expected[case_id]
        if facts != template["immutable_execution_facts"]:
            raise RuntimeError(f"immutable execution facts modified for {case_id}")
        if record.get("execution_provenance") != template["execution_provenance"]:
            raise RuntimeError(f"execution provenance modified for {case_id}")
        provenance = record.get("review_provenance", {})
        frozen_review = template["review_provenance"]
        if set(provenance) != {"rubric_path", "rubric_sha256", "metric_registry_path", "metric_registry_sha256", "reviewer", "review_method", "reviewed_at"}:
            raise RuntimeError("review provenance has missing or unknown fields")
        for field in ("rubric_path", "rubric_sha256", "metric_registry_path", "metric_registry_sha256", "review_method"):
            if provenance.get(field) != frozen_review[field]:
                raise RuntimeError(f"review provenance mismatch for {case_id}: {field}")
        judgments = record.get("reviewer_judgments")
        if mode == "template":
            if judgments != _unset_judgments() or provenance.get("reviewer") is not None or provenance.get("reviewed_at") is not None:
                raise RuntimeError("template contains reviewer judgment/provenance values")
        else:
            if set(judgments) != set(_unset_judgments()):
                raise RuntimeError("reviewer judgments have missing or unknown fields")
            _validate_completed_record(record)
            if not isinstance(provenance.get("reviewer"), str) or not provenance["reviewer"].strip():
                raise RuntimeError("completed review missing reviewer")
            if not isinstance(provenance.get("reviewed_at"), str) or not provenance["reviewed_at"].strip():
                raise RuntimeError("completed review missing reviewed_at")
            try:
                datetime.fromisoformat(provenance["reviewed_at"].replace("Z", "+00:00"))
            except ValueError as error:
                raise RuntimeError("reviewed_at must be an ISO-8601 timestamp") from error


def _validate_completed_record(record: dict) -> None:
    facts, j = record["immutable_execution_facts"], record["reviewer_judgments"]
    scores = j.get("dimension_scores")
    if not isinstance(scores, dict) or set(scores) != set(DIMENSIONS):
        raise RuntimeError("all frozen dimension scores are required")
    for name, maximum in DIMENSIONS.items():
        value = scores[name]
        if type(value) is not int or not 0 <= value <= maximum:
            raise RuntimeError(f"invalid dimension score: {name}")
    if type(j.get("total_score")) is not int or j["total_score"] != sum(scores.values()):
        raise RuntimeError("total score does not equal frozen dimension sum")
    if j.get("completion_judgment") not in {"complete", "partial", "not_complete"}:
        raise RuntimeError("invalid or missing completion judgment")
    if type(j.get("validity_judgment")) is not bool:
        raise RuntimeError("validity judgment must be boolean")
    ask = j.get("ask_quality")
    if not isinstance(ask, dict) or set(ask) != {"denominator", "counts"} or type(ask.get("denominator")) is not int or ask["denominator"] != facts["ASK_count"]:
        raise RuntimeError("ASK quality denominator must equal observed ASK_count")
    counts = ask.get("counts")
    if not isinstance(counts, dict) or set(counts) != set(ASK_CATEGORIES) or any(type(counts[k]) is not int or counts[k] < 0 for k in ASK_CATEGORIES):
        raise RuntimeError("ASK category counts are incomplete or invalid")
    if sum(counts.values()) != facts["ASK_count"]:
        raise RuntimeError("ASK category counts do not sum to observed ASK_count")
    necessary = j.get("necessary_ask_preservation")
    if not isinstance(necessary, dict) or set(necessary) != {"acquired_targets", "oracle_required_targets", "target_adjudications"}:
        raise RuntimeError("necessary ASK preservation judgment missing")
    targets = necessary.get("target_adjudications")
    if not isinstance(targets, list) or any(not isinstance(x, dict) or set(x) != {"target_id", "required_by_oracle", "acquired"} or not isinstance(x.get("target_id"), str)
        or type(x.get("required_by_oracle")) is not bool or type(x.get("acquired")) is not bool for x in targets):
        raise RuntimeError("necessary ASK target adjudications incomplete")
    if len({x["target_id"] for x in targets}) != len(targets):
        raise RuntimeError("duplicate necessary ASK target adjudication")
    denom = sum(x["required_by_oracle"] for x in targets)
    acquired = sum(x["required_by_oracle"] and x["acquired"] for x in targets)
    if necessary.get("oracle_required_targets") != denom or necessary.get("acquired_targets") != acquired:
        raise RuntimeError("necessary ASK preservation denominator/numerator mismatch")
    tools = j.get("tool_use_appropriateness")
    if not isinstance(tools, dict) or set(tools) != {"RETRIEVE", "READ_DIARY"}:
        raise RuntimeError("tool-use appropriateness missing")
    for name, count in (("RETRIEVE", facts["RETRIEVE_count"]), ("READ_DIARY", facts["READ_DIARY_count"])):
        values = tools.get(name)
        if not isinstance(values, list) or len(values) != count or any(x not in TOOL_CATEGORIES for x in values):
            raise RuntimeError(f"{name} classification does not match recorded action count")
    critical = j.get("critical_failure")
    if not isinstance(critical, dict) or set(critical) != {"present", "types", "supporting_evidence"} or type(critical.get("present")) is not bool or not isinstance(critical.get("types"), list) or not isinstance(critical.get("supporting_evidence"), list) or any(not isinstance(x, str) for x in critical.get("supporting_evidence", [])):
        raise RuntimeError("critical-failure judgment incomplete")
    if any(x not in CRITICAL_TYPES for x in critical["types"]):
        raise RuntimeError("unknown critical-failure type")
    if critical["present"] != bool(critical["types"]):
        raise RuntimeError("critical-failure flag/types disagree")
    if critical["present"] and not _nonempty_list(critical.get("supporting_evidence")):
        raise RuntimeError("critical failure requires supporting evidence")
    if type(j.get("harmful_failure")) is not bool:
        raise RuntimeError("harmful-failure judgment must be boolean")
    attribution = j.get("failure_attribution")
    required_attribution = {"primary_cause", "downstream_effects", "independent_failure", "first_divergence",
                            "supporting_evidence", "missing_denominator", "rationale"}
    if not isinstance(attribution, dict) or set(attribution) != required_attribution:
        raise RuntimeError("failure-attribution fields incomplete")
    if attribution["primary_cause"] is not None and not isinstance(attribution["primary_cause"], str):
        raise RuntimeError("invalid primary cause")
    if not isinstance(attribution["downstream_effects"], list) or type(attribution["independent_failure"]) is not bool:
        raise RuntimeError("invalid downstream/independent attribution")
    if any(not isinstance(x, str) or not x for x in attribution["downstream_effects"]):
        raise RuntimeError("downstream effects must be non-empty strings")
    if attribution["first_divergence"] is not None and not isinstance(attribution["first_divergence"], str):
        raise RuntimeError("invalid first divergence")
    if not isinstance(attribution["supporting_evidence"], list) or not isinstance(attribution["missing_denominator"], list):
        raise RuntimeError("invalid attribution evidence or missing denominator")
    if any(not isinstance(x, str) or not x for x in attribution["supporting_evidence"] + attribution["missing_denominator"]):
        raise RuntimeError("supporting evidence and missing denominators must be non-empty strings")
    if not isinstance(attribution["rationale"], str) or not attribution["rationale"].strip():
        raise RuntimeError("review rationale is required")


def _nonempty_list(value) -> bool:
    return isinstance(value, list) and len(value) > 0


def _rank(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percentile * len(ordered)) - 1)]


def aggregate_completed(records: list[dict]) -> dict:
    """Build descriptive metrics only from completed, already-validated reviews."""
    validate_records(records, "completed")
    facts = [r["immutable_execution_facts"] for r in records]
    judgments = [r["reviewer_judgments"] for r in records]
    def mean(values): return round(sum(values) / len(values), 4) if values else None
    totals = [j["total_score"] for j in judgments]
    dimension_means = {key: mean([j["dimension_scores"][key] for j in judgments]) for key in DIMENSIONS}
    task_breakdown = {}
    for task in TASK_TYPES:
        indexes = [i for i, f in enumerate(facts) if f["task_type"] == task]
        task_breakdown[task] = {"n": len(indexes), "overall_descriptive_mean": mean([judgments[i]["total_score"] for i in indexes])}
    ask_counts = Counter()
    for j in judgments:
        ask_counts.update(j["ask_quality"]["counts"])
    necessary_denominator = sum(j["necessary_ask_preservation"]["oracle_required_targets"] for j in judgments)
    necessary_acquired = sum(j["necessary_ask_preservation"]["acquired_targets"] for j in judgments)
    tool_dist = {name: dict(Counter(value for j in judgments for value in j["tool_use_appropriateness"][name]))
                 for name in ("RETRIEVE", "READ_DIARY")}
    ask_total = sum(f["ASK_count"] for f in facts)
    retrieve_total = sum(f["RETRIEVE_count"] for f in facts)
    diary_total = sum(f["READ_DIARY_count"] for f in facts)
    completed_cases = len(records)
    low_value_asks = ask_counts["redundant"] + ask_counts["irrelevant"]
    by_task_latency = {task: [f["latency_ms"] for f in facts if f["task_type"] == task] for task in TASK_TYPES}
    return {
        "aggregation_status": "DESCRIPTIVE_ADJUDICATION_SUMMARY",
        "evaluation_id": facts[0]["evaluation_id"], "n": len(records),
        "overall_descriptive_score": {"mean": mean(totals), "n": len(totals), "missing_denominator": 0},
        "dimension_means": dimension_means, "task_type_breakdown": task_breakdown,
        "completion_distribution": dict(Counter(j["completion_judgment"] for j in judgments)),
        "completion_rate": sum(j["completion_judgment"] == "complete" for j in judgments) / len(judgments),
        "completion_rate_denominator": len(judgments),
        "validity_rate": sum(j["validity_judgment"] for j in judgments) / len(judgments),
        "validity_rate_denominator": len(judgments),
        "ask_per_case": ask_total / completed_cases,
        "ask_quality_distribution": {"counts": dict(ask_counts), "rates": {
            category: ask_counts[category] / ask_total if ask_total else None for category in ASK_CATEGORIES},
            "denominator": ask_total},
        "low_value_ask_rate": {"count": low_value_asks, "denominator": ask_total,
                               "rate": low_value_asks / ask_total if ask_total else None},
        "necessary_ask_preservation": {"acquired": necessary_acquired, "denominator": necessary_denominator,
                                       "rate": necessary_acquired / necessary_denominator if necessary_denominator else None},
        "tool_use_appropriateness": tool_dist,
        "retrieve_per_case": retrieve_total / completed_cases,
        "read_diary_per_case": diary_total / completed_cases,
        "total_acquisition_actions_per_case": (ask_total + retrieve_total + diary_total) / completed_cases,
        "critical_failures": {"count": sum(j["critical_failure"]["present"] for j in judgments),
                              "rate": sum(j["critical_failure"]["present"] for j in judgments) / len(judgments)},
        "harmful_failures": {"count": sum(j["harmful_failure"] for j in judgments),
                             "rate": sum(j["harmful_failure"] for j in judgments) / len(judgments)},
        "primary_cause_distribution": dict(Counter(j["failure_attribution"]["primary_cause"] for j in judgments if j["failure_attribution"]["primary_cause"] is not None)),
        "first_divergence_distribution": dict(Counter(j["failure_attribution"]["first_divergence"] for j in judgments if j["failure_attribution"]["first_divergence"] is not None)),
        "efficiency": {
            "turns_per_case_mean": mean([f["turn_count"] for f in facts]),
            "steps_per_case_mean": mean([f["step_count"] for f in facts]),
            "tool_calls_per_case_mean": mean([len(f["tool_calls"]) for f in facts]),
            "latency_ms": {"mean": mean([f["latency_ms"] for f in facts]), "median": median([f["latency_ms"] for f in facts]),
                           "p90_nearest_rank": _rank([f["latency_ms"] for f in facts], .9),
                           "by_task_type": {task: {"mean": mean(values), "median": median(values) if values else None, "p90_nearest_rank": _rank(values, .9)} for task, values in by_task_latency.items()}},
        },
        "review_missing_denominators": {f["case_id"]: j["failure_attribution"]["missing_denominator"]
                                        for f, j in zip(facts, judgments) if j["failure_attribution"]["missing_denominator"]},
        "token_usage": "NOT_MEASURED",
        "single_composite_pass_threshold": None,
        "completion_note": "Completion is taken only from reviewer judgment; final_status is not used to infer completion.",
        "threshold_note": "No composite pass threshold is preregistered; none is inferred or created.",
    }
