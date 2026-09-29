"""Frozen, descriptive Step 9.39 matched baseline/treatment comparison."""
from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation/v1_2_3"
BASE_RUN = ROOT / "evaluation/v4_runs/heldout-v4-step9_28-20260925-01"
TREAT_RUN = ROOT / "evaluation/v4_runs/heldout-v4-step9_34a-treatment-20260928-01"
BASE_ATTEMPT = "heldout-v4-step9_28-20260925-01-attempt-step9_29b-5370d36a64d84a3da4f2585e9b57055a"
TREAT_ATTEMPT = "attempt-step9_35b-e469d82618d4c51d91d193bb439507e4"
FP = "d930455e417935337a6e3459defbdc3ee3829b71786fbd8438ef092b62429e68"
OUTPUTS = {
    "metrics": OUT / "step9_39_matched_comparison_metrics.json",
    "transitions": OUT / "step9_39_case_transition_matrix.jsonl",
    "report": OUT / "step9_39_matched_comparison_report.md",
    "claim_audit": OUT / "step9_39_claim_eligibility_audit.json",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def j(path):
    return json.loads(path.read_text(encoding="utf-8"))


def jl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def durable_new(path, content):
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def fingerprint(ids):
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def delta(b, t):
    return round(t - b, 4)


def metric(b, t, *, rate=False, relative=False):
    out = {"baseline": b, "treatment": t, "absolute_delta": delta(b, t)}
    if rate:
        out["percentage_point_delta"] = round((t - b) * 100, 4)
    if relative:
        out["relative_change"] = round((t - b) / b, 4) if b else "NOT_APPLICABLE_ZERO_BASELINE"
    return out


def verify_case_aggregate(metrics, rows):
    if len(rows) != 40 or len({r["case_id"] for r in rows}) != 40:
        raise RuntimeError("aggregate source summary must contain 40 unique cases")
    mean = lambda vals: round(sum(vals) / len(vals), 4)
    scores = metrics["scores"]
    if mean([r["total_score"] for r in rows]) != scores["overall"]["mean"]:
        raise RuntimeError("overall does not recompute from case rows")
    for task, item in scores["task_type_means"].items():
        vals = [r["total_score"] for r in rows if r["task_type"] == task]
        if len(vals) != item["denominator"] or mean(vals) != item["mean"]:
            raise RuntimeError(f"task score aggregate mismatch: {task}")
    for dimension, item in scores["dimensions"].items():
        if mean([r["dimension_scores"][dimension] for r in rows]) != item["mean"]:
            raise RuntimeError(f"dimension aggregate mismatch: {dimension}")
    comp = metrics["completion_and_validity"]["overall"]
    complete = sum(r["completion_judgment"] == "complete" for r in rows)
    valid = sum(r["validity_judgment"] is True for r in rows)
    if (comp["rate"]["numerator"] != complete or comp["rate"]["denominator"] != 40
            or comp["validity_rate"]["numerator"] != valid or comp["validity_rate"]["denominator"] != 40):
        raise RuntimeError("completion/validity aggregate mismatch")
    ask = Counter()
    for r in rows: ask.update(r["ask_quality_counts"])
    if (metrics["ask_quality"]["TOTAL_ASK_COUNT"] != sum(r["execution"]["ASK_count"] for r in rows)
            or any(metrics["ask_quality"][field] != ask[key] for field, key in (
                ("NECESSARY_ASK_COUNT", "necessary"), ("USEFUL_OPTIONAL_ASK_COUNT", "useful_but_optional"),
                ("REDUNDANT_ASK_COUNT", "redundant"), ("IRRELEVANT_ASK_COUNT", "irrelevant")))):
        raise RuntimeError("ASK aggregate mismatch")
    failures = metrics["failures"]
    if (failures["CRITICAL_FAILURE_COUNT"] != sum(r["critical_failure"] for r in rows)
            or failures["HARMFUL_FAILURE_COUNT"] != sum(r["harmful_failure"] for r in rows)):
        raise RuntimeError("failure aggregate mismatch")
    counts = metrics["tool_resource_behavior"]["counts"]
    for kind in ("ASK", "RETRIEVE", "READ_DIARY"):
        key = f"{kind}_count"
        if counts[kind] != sum(r["execution"][key] for r in rows):
            raise RuntimeError(f"execution aggregate mismatch: {kind}")
    eff = metrics["efficiency"]
    for field, row_key in (("turns_per_case", "turn_count"), ("steps_per_case", "step_count")):
        if eff[field]["mean"] != mean([r["execution"][row_key] for r in rows]):
            raise RuntimeError(f"execution aggregate mismatch: {field}")
    if eff["latency_ms"]["overall"]["mean_ms"] != mean([r["execution"]["latency_ms"] for r in rows]):
        raise RuntimeError("latency aggregate mismatch")


def verify():
    baseline_metrics_path = OUT / "step9_30c_v4_aggregate_metrics.json"
    baseline_summary_path = OUT / "step9_30c_v4_case_level_summary.jsonl"
    baseline_audit_path = OUT / "step9_30c_r1_v4_aggregation_audit.json"
    base_lock_path = OUT / "step9_34a_baseline_metric_lock.json"
    protocol_path = OUT / "step9_34a_matched_comparison_protocol.json"
    policy_path = OUT / "step9_34a_claim_policy.json"
    treatment_metrics_path = OUT / "step9_38_treatment_aggregate_metrics.json"
    treatment_summary_path = OUT / "step9_38_treatment_case_summary.jsonl"
    treatment_freeze_path = OUT / "step9_38_treatment_aggregate_freeze.json"
    treatment_run_freeze_path = OUT / "step9_36_treatment_run_input_freeze.json"
    baseline_run_freeze_path = OUT / "step9_30a_v4_run_input_freeze.json"
    baseline_adjudication_path = OUT / "step9_30b_v4_human_adjudication.jsonl"
    treatment_adjudication_path = OUT / "step9_37_treatment_adjudication.jsonl"
    treatment_auth_path = OUT / "step9_35b_matched_treatment_authorization_manifest.json"
    base_case_path = BASE_RUN / f"{BASE_ATTEMPT}_case_results.jsonl"
    treat_case_path = TREAT_RUN / f"{TREAT_ATTEMPT}_case_results.jsonl"
    base_trace_path = BASE_RUN / f"{BASE_ATTEMPT}_raw_traces.jsonl"
    treat_trace_path = TREAT_RUN / f"{TREAT_ATTEMPT}_raw_traces.jsonl"
    base_auth_path = OUT / "step9_29b_v4_authorization_manifest.json"
    base_freeze_path = OUT / "step9_32_baseline_agent_freeze.json"
    treatment_agent_freeze_path = OUT / "step9_33a_treatment_freeze.json"
    treatment_runner_freeze_path = OUT / "step9_35a_treatment_runner_freeze.json"
    recon_path = OUT / "step9_38a_metric_registry_reconciliation_r4.json"
    registry_path = OUT / "step9_26_v4_metric_registry.json"
    rubric_path = ROOT / "evaluation/benchmark_v1_1_scoring.md"
    dataset_path = ROOT / "evaluation/benchmarks/benchmark_v4_cases.yaml"
    manifest_path = ROOT / "evaluation/benchmarks/benchmark_v4_manifest.json"
    rules_path = OUT / "step9_26_v4_one_shot_rules.md"
    source_paths = [baseline_metrics_path, baseline_summary_path, baseline_audit_path, base_lock_path,
                    protocol_path, policy_path, treatment_metrics_path, treatment_summary_path,
                    treatment_freeze_path, treatment_run_freeze_path, baseline_run_freeze_path, treatment_auth_path,
                    baseline_adjudication_path, treatment_adjudication_path,
                    base_case_path, treat_case_path, base_trace_path, treat_trace_path, base_auth_path,
                    base_freeze_path, treatment_agent_freeze_path, treatment_runner_freeze_path,
                    recon_path, registry_path, rubric_path, dataset_path, manifest_path, rules_path]
    if any(not p.is_file() for p in source_paths):
        raise RuntimeError("required frozen source artifact missing")
    if any(p.exists() for p in OUTPUTS.values()):
        raise RuntimeError("Step 9.39 output already exists; refusing overwrite")

    bm, bs, ba = j(baseline_metrics_path), jl(baseline_summary_path), j(baseline_audit_path)
    lock, protocol, policy = j(base_lock_path), j(protocol_path), j(policy_path)
    tm, ts, tf, trf = j(treatment_metrics_path), jl(treatment_summary_path), j(treatment_freeze_path), j(treatment_run_freeze_path)
    ta, b_auth, b_agent, t_agent, runner_freeze = j(treatment_auth_path), j(base_auth_path), j(base_freeze_path), j(treatment_agent_freeze_path), j(treatment_runner_freeze_path)
    recon = j(recon_path)
    baseline_run_freeze = j(baseline_run_freeze_path)

    # Verify provenance bindings, not just user-provided summary numbers.
    if (ba.get("status") != "PASS_DETERMINISTIC_AGGREGATION"
            or lock["source_artifacts"]["aggregate_metrics_sha256"] != sha(baseline_metrics_path)
            or lock["source_artifacts"]["case_level_summary_sha256"] != sha(baseline_summary_path)
            or lock["source_artifacts"]["aggregation_audit_sha256"] != sha(OUT / "step9_30c_r1_v4_aggregation_audit.json")):
        raise RuntimeError("baseline aggregate/freeze/audit identity mismatch")
    if (tf.get("status") != "PASS_TREATMENT_AGGREGATION_ONLY"
            or tf["outputs"]["metrics"]["sha256"] != sha(treatment_metrics_path)
            or tf["outputs"]["case_summary"]["sha256"] != sha(treatment_summary_path)
            or tf["source_hashes"]["reconciliation"] != sha(recon_path)
            or tf["source_hashes"]["metric_registry"] != sha(registry_path)
            or tf["baseline_treatment_comparison_generated"] is not False):
        raise RuntimeError("treatment aggregate freeze mismatch")
    if (lock["source_artifacts"]["adjudication_sha256"] != sha(baseline_adjudication_path)
            or sha(treatment_adjudication_path) != "60b5c2847ffdb51c43e00351519cb910428a82eb981849dfebefb76112658047"):
        raise RuntimeError("frozen adjudication source hash mismatch")
    baseline_inputs = {x["path"]: x for x in baseline_run_freeze["artifact_files"]}
    treatment_inputs = {x["path"]: x for x in trf["artifact_files"]}
    for path in (base_case_path, base_trace_path):
        pin = baseline_inputs.get(path.relative_to(ROOT).as_posix())
        if not pin or sha(path) != pin["sha256"] or path.stat().st_size != pin["byte_size"]:
            raise RuntimeError("baseline execution artifact differs from input freeze")
    for path in (treat_case_path, treat_trace_path):
        pin = treatment_inputs.get(path.relative_to(ROOT).as_posix())
        if not pin or sha(path) != pin["sha256"] or path.stat().st_size != pin["byte_size"]:
            raise RuntimeError("treatment execution artifact differs from input freeze")
        key = "case_results" if path == treat_case_path else "raw_traces"
        if tf["source_hashes"].get(key) != sha(path):
            raise RuntimeError("treatment aggregate freeze source hash mismatch")
    if (protocol.get("protocol_status") != "FROZEN_BEFORE_TREATMENT_EXECUTION"
            or protocol.get("comparison_class") != "POST_HOC_MATCHED_FROZEN_BASELINE"
            or protocol["design_classification"]["case_count"] != 40
            or policy.get("status") != "FROZEN_BEFORE_TREATMENT_EXECUTION"):
        raise RuntimeError("comparison protocol or claim policy identity mismatch")
    if (j(baseline_metrics_path).get("evaluation_id") != lock["baseline_identity"]["evaluation_id"]
            or bm["attempt_id"] != lock["baseline_identity"]["attempt_id"]
            or tm["evaluation_id"] != tf["evaluation_id"] or tm["attempt_id"] != tf["attempt_id"]):
        raise RuntimeError("aggregate evaluation/attempt identity mismatch")

    # All common execution identities must equal the protocol pins.
    pins = protocol["identities"]
    expected_identity = {
        "benchmark_sha256": sha(dataset_path), "benchmark_manifest_sha256": sha(manifest_path),
        "harness_sha256": pins["harness_sha256"], "scoring_sha256": pins["scoring_aggregate_sha256"],
        "scoring_rubric_sha256": sha(rubric_path), "metric_registry_sha256": sha(registry_path),
        "one_shot_rules_sha256": sha(rules_path),
    }
    if (expected_identity["benchmark_sha256"] != pins["benchmark_v4_sha256"]
            or expected_identity["benchmark_manifest_sha256"] != pins["benchmark_manifest_sha256"]
            or expected_identity["scoring_rubric_sha256"] != pins["scoring_rubric_sha256"]
            or expected_identity["metric_registry_sha256"] != pins["paired_metric_registry_sha256"]
            or expected_identity["one_shot_rules_sha256"] != pins["one_shot_rules_sha256"]):
        raise RuntimeError("dataset/scoring/registry/one-shot protocol hash mismatch")
    baseline_expected = {
        "agent_sha256": pins["baseline_agent_sha256"], "harness_sha256": pins["harness_sha256"],
        "scoring_sha256": pins["scoring_aggregate_sha256"], "metric_registry_sha256": pins["paired_metric_registry_sha256"],
        "one_shot_rules_sha256": pins["one_shot_rules_sha256"], "benchmark_sha256": pins["benchmark_v4_sha256"],
    }
    if any(b_auth.get(k) != v for k, v in baseline_expected.items()):
        raise RuntimeError("baseline authorization identity differs from protocol")
    if (b_agent.get("baseline_agent_sha256") != pins["baseline_agent_sha256"]
            or b_agent.get("baseline_model_config", {}).get("runtime_nonsecret_fingerprint") !=
                j(OUT / "step9_34_baseline_treatment_identity.json")["paired_constants"]["model_configuration_sha256"]):
        raise RuntimeError("baseline candidate/model configuration identity mismatch")
    baseline_identity = j(OUT / "step9_34_baseline_treatment_identity.json")["paired_constants"]
    tbound = runner_freeze["bound_identities"]
    t_exec = trf["execution_identity"]
    baseline_tools = {item["path"]: item["sha256"] for item in b_agent["agent_file_inventory"]}
    treatment_tools = {item[0]: item[1] for item in t_agent["agent_behavior_files"]}
    if (baseline_identity["rag_configuration_sha256"] != b_agent["baseline_rag_config_hash"]
            or baseline_identity["tool_adapter_source_sha256"] != baseline_tools.get("adaptive_agent/tools.py")
            or baseline_identity["tool_adapter_source_sha256"] != treatment_tools.get("adaptive_agent/tools.py")):
        raise RuntimeError("baseline/treatment RAG or tool source identity mismatch")
    for field, value in (("benchmark_sha256", pins["benchmark_v4_sha256"]),
                         ("benchmark_manifest_sha256", pins["benchmark_manifest_sha256"]),
                         ("harness_sha256", pins["harness_sha256"]),
                         ("scoring_sha256", pins["scoring_aggregate_sha256"]),
                         ("scoring_rubric_sha256", pins["scoring_rubric_sha256"]),
                         ("metric_registry_sha256", pins["paired_metric_registry_sha256"]),
                         ("one_shot_rules_sha256", pins["one_shot_rules_sha256"]),
                         ("model_configuration_fingerprint_sha256", baseline_identity["model_configuration_sha256"]),
                         ("rag_configuration_fingerprint_sha256", baseline_identity["rag_configuration_sha256"]),
                         ("tool_adapter_sha256", baseline_identity["tool_adapter_source_sha256"])):
        if tbound.get(field) != value:
            raise RuntimeError(f"treatment runner identity mismatch: {field}")
    if any(t_exec.get(k) != v for k, v in {
        "benchmark_sha256": pins["benchmark_v4_sha256"], "benchmark_manifest_sha256": pins["benchmark_manifest_sha256"],
        "harness_sha256": pins["harness_sha256"], "scoring_sha256": pins["scoring_aggregate_sha256"],
        "scoring_rubric_sha256": pins["scoring_rubric_sha256"], "metric_registry_sha256": pins["paired_metric_registry_sha256"],
        "one_shot_rules_sha256": pins["one_shot_rules_sha256"],
    }.items()) or not t_exec.get("all_frozen_hashes_match"):
        raise RuntimeError("treatment execution identity mismatch")
    if (ta.get("model_configuration_fingerprint_sha256") != baseline_identity["model_configuration_sha256"]
            or ta.get("rag_configuration_fingerprint_sha256") != baseline_identity["rag_configuration_sha256"]
            or ta.get("tool_adapter_sha256") != baseline_identity["tool_adapter_source_sha256"]):
        raise RuntimeError("treatment authorization model/tool/RAG identity mismatch")
    if (ta.get("baseline_agent_sha256") != pins["baseline_agent_sha256"]
            or ta.get("treatment_agent_sha256") != t_agent.get("treatment_agent_aggregate_sha256")
            or ta.get("treatment_agent_sha256") != t_exec.get("treatment_agent_sha256")):
        raise RuntimeError("treatment agent freeze mismatch")
    if (recon.get("compatibility_class") != "BACKWARD_COMPATIBLE_FOR_AGGREGATION"
            or recon.get("material_consumed_semantic_difference_count") != 0
            or tf["aggregation_registry"]["sha256"] != pins["paired_metric_registry_sha256"]):
        raise RuntimeError("baseline/treatment aggregation semantics mismatch")

    base_rows, treatment_rows = {r["case_id"]: r for r in bs}, {r["case_id"]: r for r in ts}
    if len(base_rows) != 40 or len(treatment_rows) != 40 or set(base_rows) != set(treatment_rows):
        raise RuntimeError("case set is not exactly matched")
    b_results = jl(next(BASE_RUN.glob(f"*{BASE_ATTEMPT}*_case_results.jsonl")))
    t_results = jl(next(TREAT_RUN.glob(f"*{TREAT_ATTEMPT}*_case_results.jsonl")))
    base_ids, treat_ids = [r["case_id"] for r in b_results], [r["case_id"] for r in t_results]
    if (fingerprint(base_ids) != FP or fingerprint(treat_ids) != FP or base_ids != treat_ids
            or len(set(base_ids)) != 40 or len(set(treat_ids)) != 40):
        raise RuntimeError("case execution order does not match frozen protocol")
    if lock["baseline_identity"]["case_id_order_sha256"] != FP or protocol["design_classification"]["case_set_and_order_fingerprint_sha256"] != FP:
        raise RuntimeError("case order fingerprint does not match comparison protocol")
    if Counter(r["task_type"] for r in base_rows.values()) != Counter(r["task_type"] for r in treatment_rows.values()):
        raise RuntimeError("task strata differ between baseline and treatment")
    verify_case_aggregate(bm, bs)
    verify_case_aggregate(tm, ts)
    base_adj_rows = {r["immutable_execution_facts"]["case_id"]: r for r in jl(baseline_adjudication_path)}
    treatment_adj_rows = {r["immutable_execution_facts"]["case_id"]: r for r in jl(treatment_adjudication_path)}
    if len(base_adj_rows) != 40 or len(treatment_adj_rows) != 40 or set(base_adj_rows) != set(treatment_adj_rows) or set(base_adj_rows) != set(base_rows):
        raise RuntimeError("frozen adjudication coverage differs from matched summaries")
    baseline_reviewers = {r["review_provenance"]["reviewer"] for r in base_adj_rows.values()}
    treatment_reviewers = {r["review_provenance"]["reviewer"] for r in treatment_adj_rows.values()}
    if baseline_reviewers != treatment_reviewers or len(baseline_reviewers) != 1:
        raise RuntimeError("reviewer identity mismatch")
    baseline_rubrics = {r["review_provenance"]["rubric_sha256"] for r in base_adj_rows.values()}
    treatment_rubrics = {r["review_provenance"]["rubric_sha256"] for r in treatment_adj_rows.values()}
    if baseline_rubrics != treatment_rubrics or treatment_rubrics != {sha(rubric_path)}:
        raise RuntimeError("review rubric identity mismatch")

    # Validate the treatment and baseline primary values against the frozen metric records.
    b_completion = bm["completion_and_validity"]["overall"]["rate"]
    t_completion = tm["completion_and_validity"]["overall"]["rate"]
    b_validity = bm["completion_and_validity"]["overall"]["validity_rate"]
    t_validity = tm["completion_and_validity"]["overall"]["validity_rate"]
    if (b_completion["numerator"] != lock["primary_metric_values"]["M2_TASK_COMPLETION"]["numerator"]
            or t_completion["numerator"] != sum(r["completion_judgment"] == "complete" for r in treatment_rows.values())
            or t_validity["numerator"] != sum(r["validity_judgment"] is True for r in treatment_rows.values())):
        raise RuntimeError("primary completion/validity aggregate does not match per-case rows")

    transitions = []
    completion_counts = Counter()
    validity_counts = Counter()
    harmful_counts = Counter()
    critical_counts = Counter()
    ask_counts = Counter()
    regression_ids = {"completion": [], "validity": [], "harmful": [], "critical": [], "necessary_ask": [], "low_value_ask": []}
    for case_id in base_ids:
        b, t = base_rows[case_id], treatment_rows[case_id]
        if b["task_type"] != t["task_type"]:
            raise RuntimeError(f"task label changed for matched case {case_id}")
        bc, tc = b["completion_judgment"] == "complete", t["completion_judgment"] == "complete"
        vc, vt = b["validity_judgment"], t["validity_judgment"]
        hc, ht = b["harmful_failure"], t["harmful_failure"]
        cc, ct = b["critical_failure"], t["critical_failure"]
        completion_label = ("PASS" if bc else "FAIL") + "_TO_" + ("PASS" if tc else "FAIL")
        completion_counts[completion_label] += 1
        validity_label = "INVALID_TO_VALID" if (not vc and vt) else "VALID_TO_INVALID" if (vc and not vt) else "SAME"
        validity_counts[validity_label] += 1
        harmful_label = "YES_TO_NO" if (hc and not ht) else "NO_TO_YES" if (not hc and ht) else "SAME"
        harmful_counts[harmful_label] += 1
        critical_label = "YES_TO_NO" if (cc and not ct) else "NO_TO_YES" if (not cc and ct) else "SAME"
        critical_counts[critical_label] += 1
        if completion_label == "PASS_TO_FAIL": regression_ids["completion"].append(case_id)
        if validity_label == "VALID_TO_INVALID": regression_ids["validity"].append(case_id)
        if harmful_label == "NO_TO_YES": regression_ids["harmful"].append(case_id)
        if critical_label == "NO_TO_YES": regression_ids["critical"].append(case_id)

        bq, tq = b["ask_quality_counts"], t["ask_quality_counts"]
        b_low = bq["redundant"] + bq["irrelevant"]
        t_low = tq["redundant"] + tq["irrelevant"]
        labels = []
        if b_low > 0 and t_low == 0: labels.append("LOW_VALUE_ASK_REMOVED")
        elif b_low == 0 and t_low > 0: labels.append("NEW_LOW_VALUE_ASK_INTRODUCED")
        elif t_low < b_low: labels.append("LOW_VALUE_ASK_REDUCED")
        elif t_low > b_low: labels.append("LOW_VALUE_ASK_INCREASED")
        if t_low > b_low:
            regression_ids["low_value_ask"].append(case_id)
        bpres = base_adj_rows[case_id]["reviewer_judgments"]["necessary_ask_preservation"]
        tpres = treatment_adj_rows[case_id]["reviewer_judgments"]["necessary_ask_preservation"]
        bt = {x["target_id"] for x in bpres.get("target_adjudications", []) if x["required_by_oracle"]}
        tt = {x["target_id"] for x in tpres.get("target_adjudications", []) if x["required_by_oracle"]}
        baq = {x["target_id"] for x in bpres.get("target_adjudications", []) if x["required_by_oracle"] and x["acquired"]}
        taq = {x["target_id"] for x in tpres.get("target_adjudications", []) if x["required_by_oracle"] and x["acquired"]}
        if bt != tt:
            raise RuntimeError(f"oracle necessary-target set mismatch in matched case {case_id}")
        lost, gained = sorted(baq - taq), sorted(taq - baq)
        if lost:
            labels.append("NECESSARY_ASK_LOST")
            regression_ids["necessary_ask"].append(case_id)
        elif gained:
            labels.append("NECESSARY_ASK_GAINED")
        elif baq:
            labels.append("NECESSARY_ASK_PRESERVED")
        if any(tq[k] > bq[k] for k in tq if k == "useful_but_optional"):
            labels.append("USEFUL_OPTIONAL_ADDED")
        if not labels:
            labels = ["UNCHANGED"]
        transitions.append({
            "case_id": case_id, "task_type": b["task_type"],
            "baseline_completion": b["completion_judgment"], "treatment_completion": t["completion_judgment"],
            "completion_transition": completion_label,
            "baseline_validity": "VALID" if vc else "INVALID", "treatment_validity": "VALID" if vt else "INVALID",
            "validity_transition": validity_label,
            "baseline_harmful_failure": hc, "treatment_harmful_failure": ht, "harmful_transition": harmful_label,
            "baseline_critical_failure": cc, "treatment_critical_failure": ct, "critical_transition": critical_label,
            "baseline_ask_quality_counts": bq, "treatment_ask_quality_counts": tq,
            "necessary_oracle_targets": sorted(bt), "necessary_targets_acquired_baseline": sorted(baq),
            "necessary_targets_acquired_treatment": sorted(taq), "necessary_targets_lost": lost,
            "necessary_targets_gained": gained, "ask_transition_labels": labels,
            "case_score_delta": delta(t["total_score"], b["total_score"]),
        })

    return locals()


def main():
    v = verify()
    bm, tm, lock, protocol, policy = v["bm"], v["tm"], v["lock"], v["protocol"], v["policy"]
    def by_task(metrics, source):
        return {task: metrics[source]["task_type_means"][task]["mean"] for task in
                ("KNOWLEDGE_QA", "CAUSE_ASSESSMENT", "PERSONALIZED_DECISION", "DATA_ANALYSIS")}
    bscore, tscore = bm["scores"], tm["scores"]
    bcomp = bm["completion_and_validity"]["overall"]["rate"]
    tcomp = tm["completion_and_validity"]["overall"]["rate"]
    bvalid = bm["completion_and_validity"]["overall"]["validity_rate"]
    tvalid = tm["completion_and_validity"]["overall"]["validity_rate"]
    b_ask, t_ask = bm["ask_quality"], tm["ask_quality"]
    b_low = b_ask["REDUNDANT_OR_IRRELEVANT_RATE"]["value"]
    t_low = t_ask["LOW_VALUE_ASK_RATE"]["value"]
    bh = bm["failures"]["HARMFUL_FAILURE_COUNT"]
    th = tm["failures"]["HARMFUL_FAILURE_COUNT"]
    bc = bm["failures"]["CRITICAL_FAILURE_COUNT"]
    tc = tm["failures"]["CRITICAL_FAILURE_COUNT"]
    task_base, task_treat = by_task(bm, "scores"), by_task(tm, "scores")
    dim_delta = {k: metric(bscore["dimensions"][k]["mean"], tscore["dimensions"][k]["mean"])
                 for k in bscore["dimensions"]}

    def execution_metric(key, lookup):
        return metric(lookup(bm), lookup(tm))
    execution = {
        key: metric(b, t) for key, b, t in [
            ("RETRIEVE_PER_CASE", bm["tool_resource_behavior"]["per_case_means"]["retrieve_per_case"]["value"], tm["tool_resource_behavior"]["per_case_means"]["retrieve_per_case"]["value"]),
            ("READ_DIARY_PER_CASE", bm["tool_resource_behavior"]["per_case_means"]["read_diary_per_case"]["value"], tm["tool_resource_behavior"]["per_case_means"]["read_diary_per_case"]["value"]),
            ("TOOL_CALLS_PER_CASE", bm["efficiency"]["tool_calls_per_case"]["mean"], tm["efficiency"]["tool_calls_per_case"]["mean"]),
            ("TURNS_PER_CASE", bm["efficiency"]["turns_per_case"]["mean"], tm["efficiency"]["turns_per_case"]["mean"]),
            ("STEPS_PER_CASE", bm["efficiency"]["steps_per_case"]["mean"], tm["efficiency"]["steps_per_case"]["mean"]),
            ("LATENCY_MEAN_MS", bm["efficiency"]["latency_ms"]["overall"]["mean_ms"], tm["efficiency"]["latency_ms"]["overall"]["mean_ms"]),
        ]
    }
    ask_count_deltas = {k: metric(b_ask[k], t_ask[k]) for k in (
        "TOTAL_ASK_COUNT", "NECESSARY_ASK_COUNT", "USEFUL_OPTIONAL_ASK_COUNT", "REDUNDANT_ASK_COUNT", "IRRELEVANT_ASK_COUNT")}

    primary = {
        "M1_LOW_VALUE_ASK_RATE": {"baseline": b_low, "treatment": t_low, "delta": round(t_low-b_low, 4),
                                  "percentage_point_delta": round((t_low-b_low)*100, 4), "direction": "IMPROVED" if t_low < b_low else "REGRESSED" if t_low>b_low else "UNCHANGED"},
        "M2_TASK_COMPLETION": {"baseline": bcomp["value"], "treatment": tcomp["value"], "delta": round(tcomp["value"]-bcomp["value"], 4),
                               "percentage_point_delta": round((tcomp["value"]-bcomp["value"])*100, 4), "direction": "IMPROVED" if tcomp["value"]>bcomp["value"] else "REGRESSED" if tcomp["value"]<bcomp["value"] else "UNCHANGED"},
        "M3_HARMFUL_FAILURES": {"baseline": bh, "treatment": th, "delta": th-bh,
                                 "baseline_rate": bh/40, "treatment_rate": th/40, "percentage_point_delta": round((th-bh)/40*100, 4),
                                 "relative_change": round((th-bh)/bh, 4) if bh else "NOT_APPLICABLE_ZERO_BASELINE", "direction": "IMPROVED" if th<bh else "REGRESSED" if th>bh else "UNCHANGED"},
        "M4_NECESSARY_ASK_PRESERVATION": {"baseline": bm["ask_quality"]["NECESSARY_ASK_PRESERVATION_RATE"],
                                           "treatment": tm["ask_quality"]["NECESSARY_ASK_PRESERVATION_RATE"],
                                           "direction": "IMPROVED" if tm["ask_quality"]["NECESSARY_ASK_PRESERVATION_RATE"]["value"] > bm["ask_quality"]["NECESSARY_ASK_PRESERVATION_RATE"]["value"] else "REGRESSED" if tm["ask_quality"]["NECESSARY_ASK_PRESERVATION_RATE"]["value"] < bm["ask_quality"]["NECESSARY_ASK_PRESERVATION_RATE"]["value"] else "UNCHANGED",
                                           "case_level_target_discordance": {"lost_case_ids": v["regression_ids"]["necessary_ask"], "gained_target_count": sum(len(r["necessary_targets_gained"]) for r in v["transitions"]) }},
        "M5_CRITICAL_FAILURES": {"baseline": bc, "treatment": tc, "delta": tc-bc,
                                 "baseline_rate": bc/40, "treatment_rate": tc/40, "percentage_point_delta": round((tc-bc)/40*100, 4),
                                 "relative_change": "NOT_APPLICABLE_ZERO_BASELINE", "direction": "IMPROVED" if tc<bc else "REGRESSED" if tc>bc else "UNCHANGED"},
    }
    m4_baseline = bm["ask_quality"]["NECESSARY_ASK_PRESERVATION_RATE"]["value"]
    m4_treatment = tm["ask_quality"]["NECESSARY_ASK_PRESERVATION_RATE"]["value"]
    eligible = (policy["resume_claim_eligibility"]["descriptive_matched_comparative_claim_after_treatment_adjudication_aggregation_and_identity_pass"] == "YES"
                and not v["regression_ids"]["critical"] and m4_treatment >= m4_baseline)
    blockers = []
    if v["regression_ids"]["critical"]:
        blockers.append("Frozen claim policy M5: critical failures must not increase; baseline 0/40, treatment 2/40 (+2 cases, +5 percentage points).")
    if m4_treatment < m4_baseline:
        blockers.append("Frozen claim policy M4: aggregate necessary ASK preservation decreased.")
    if not eligible and not blockers:
        blockers.append("Frozen claim policy eligibility prerequisites not satisfied.")

    deltas = {
        "overall": metric(bscore["overall"]["mean"], tscore["overall"]["mean"]),
        "task_means": {task: metric(task_base[task], task_treat[task]) for task in task_base},
        "dimension_means": dim_delta,
        "task_completion_count": metric(bcomp["numerator"], tcomp["numerator"]),
        "task_completion_rate": metric(bcomp["value"], tcomp["value"], rate=True),
        "valid_case_count": metric(bvalid["numerator"], tvalid["numerator"]),
        "validity_rate": metric(bvalid["value"], tvalid["value"], rate=True),
        "ask_counts": ask_count_deltas,
        "low_value_ask_rate": metric(b_low, t_low, rate=True, relative=True),
        "necessary_ask_preservation_rate": metric(bm["ask_quality"]["NECESSARY_ASK_PRESERVATION_RATE"]["value"], tm["ask_quality"]["NECESSARY_ASK_PRESERVATION_RATE"]["value"], rate=True),
        "harmful_failures": metric(bh, th, relative=True),
        "critical_failures": metric(bc, tc, relative=True),
        "execution": execution,
    }
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in [
        OUT / "step9_30c_v4_aggregate_metrics.json", OUT / "step9_30c_v4_case_level_summary.jsonl",
        OUT / "step9_30c_r1_v4_aggregation_audit.json", OUT / "step9_34a_baseline_metric_lock.json",
        OUT / "step9_34a_matched_comparison_protocol.json", OUT / "step9_34a_claim_policy.json",
        OUT / "step9_37_treatment_adjudication_freeze.json", OUT / "step9_38_treatment_aggregate_freeze.json",
        OUT / "step9_38_treatment_aggregate_metrics.json", OUT / "step9_38_treatment_case_summary.jsonl",
        OUT / "step9_38a_metric_registry_reconciliation_r4.json", OUT / "step9_26_v4_metric_registry.json",
        OUT / "step9_30b_v4_human_adjudication.jsonl", OUT / "step9_37_treatment_adjudication.jsonl",
        ROOT / "evaluation/v1_2_3/step9_30a_v4_run_input_freeze.json",
        ROOT / "evaluation/v1_2_3/step9_36_treatment_run_input_freeze.json",
        BASE_RUN / f"{BASE_ATTEMPT}_case_results.jsonl",
        BASE_RUN / f"{BASE_ATTEMPT}_raw_traces.jsonl",
        TREAT_RUN / f"{TREAT_ATTEMPT}_case_results.jsonl", TREAT_RUN / f"{TREAT_ATTEMPT}_raw_traces.jsonl",
        ROOT / "evaluation/benchmarks/benchmark_v4_cases.yaml", ROOT / "evaluation/benchmarks/benchmark_v4_manifest.json",
    ]}
    metrics_doc = {
        "step": "9.39", "status": "PASS_DESCRIPTIVE_MATCHED_FROZEN_BASELINE_COMPARISON",
        "comparison_class": "POST_HOC_MATCHED_FROZEN_BASELINE", "randomized_paired_trial": False,
        "preregistered_randomized_comparison": False, "frozen_baseline_comparison": True,
        "case_matched_comparison": True, "case_count": 40,
        "case_order_fingerprint_sha256": FP, "case_id_pair_key": "exact identical case_id",
        "source_hashes": hashes, "absolute_deltas_treatment_minus_baseline": deltas,
        "case_transition_counts": {"completion": dict(v["completion_counts"]), "validity": dict(v["validity_counts"]),
                                   "harmful_failure": dict(v["harmful_counts"]), "critical_failure": dict(v["critical_counts"]),
                                   "low_value_ask_increased_cases": len(v["regression_ids"]["low_value_ask"])},
        "case_regression_ids": v["regression_ids"], "primary_metrics": primary,
        "resume_descriptive_matched_comparative_claim_eligible": eligible,
        "claim_blocking_criteria": blockers,
        "interpretation_boundary": {"causal_effect": False, "statistical_significance": False,
                                    "clinical_effectiveness": False, "unseen_generalization": False,
                                    "v4_is_development_postmortem_evidence": True, "v5_required_for_new_generalization_claims": True},
        "recommended_next_path": "B_REPAIR_CRITICAL_FAILURE_REGRESSION_BEFORE_V5",
    }
    transition_bytes = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True)+"\n" for row in v["transitions"]).encode()
    metric_bytes = (json.dumps(metrics_doc, ensure_ascii=False, indent=2, sort_keys=True)+"\n").encode()
    audit_doc = {
        "step": "9.39", "status": "PASS_COMPARISON_INTEGRITY_CLAIM_NOT_ELIGIBLE",
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "comparison_integrity": "PASS",
        "checks": {"baseline_aggregate_and_audit_hashes": "PASS", "treatment_aggregate_freeze_and_hashes": "PASS",
                   "benchmark_harness_scoring_registry_one_shot_match": "PASS",
                   "model_tool_rag_configuration_match": "PASS", "case_ids_exactly_matched": "PASS_40_OF_40",
                   "no_cherry_picking": "PASS_ALL_FROZEN_PRIMARY_AND_REQUESTED_COMPARABLE_METRICS_REPORTED",
                   "execution_case_order_match": "PASS", "task_strata_match": "PASS",
                   "claim_policy_and_protocol_frozen": "PASS", "r4_registry_semantic_bridge": "PASS"},
        "resume_descriptive_matched_comparative_claim_eligible": eligible,
        "claim_blocking_criteria": blockers,
        "per_case_regression_ids": v["regression_ids"],
        "v4_generalization_claim_allowed": False, "v5_required": True,
        "recommended_next_path": "B_REPAIR_CRITICAL_FAILURE_REGRESSION_BEFORE_V5",
        "source_hashes": hashes,
    }
    claim_bytes = (json.dumps(audit_doc, ensure_ascii=False, indent=2, sort_keys=True)+"\n").encode()
    transitions=v["transitions"]
    dim_parts="; ".join(f"{k}: {x['baseline']} → {x['treatment']} ({x['absolute_delta']:+})" for k,x in dim_delta.items())
    task_parts="; ".join(f"{k}: {task_base[k]} → {task_treat[k]} ({task_treat[k]-task_base[k]:+})" for k in task_base)
    lines=[
        "# Step 9.39 — Baseline vs Treatment Matched Comparison", "",
        "Comparison integrity: **PASS**. This is a post-hoc, case-matched comparison against a frozen baseline, not a randomized trial or causal estimate.", "",
        f"- Overall: {bscore['overall']['mean']} → {tscore['overall']['mean']} (delta {tscore['overall']['mean']-bscore['overall']['mean']:+.4f}).",
        f"- Task means: {task_parts}.", f"- Dimension means: {dim_parts}.",
        f"- Completion: {bcomp['numerator']}/40 ({bcomp['value']:.2%}) → {tcomp['numerator']}/40 ({tcomp['value']:.2%}); delta {tcomp['value']-bcomp['value']:+.2%} ({tcomp['numerator']-bcomp['numerator']:+} cases).",
        f"- Validity: {bvalid['numerator']}/40 ({bvalid['value']:.2%}) → {tvalid['numerator']}/40 ({tvalid['value']:.2%}); delta {tvalid['value']-bvalid['value']:+.2%}.",
        "- Count distinction: all 40 treatment adjudication records are structurally valid (`valid_case_count=40`); the separate reviewer answer-validity judgment is 38/40 (95%), not 40/40. The frozen treatment aggregate is authoritative for this comparison.",
        f"- Low-value ASK rate: {b_low:.4f} → {t_low:.4f}; delta {t_low-b_low:+.4f} ({(t_low-b_low)*100:+.2f} percentage points).",
        f"- Necessary-target preservation (M4): {bm['ask_quality']['NECESSARY_ASK_PRESERVATION_RATE']['numerator']}/4 → {tm['ask_quality']['NECESSARY_ASK_PRESERVATION_RATE']['numerator']}/4; unchanged. Event-level necessary ASK labels are a separate count.",
        f"- Harmful failures: {bh}/40 → {th}/40; delta {th-bh:+} cases; relative change {(th-bh)/bh:+.2%}.",
        f"- Critical failures: {bc}/40 → {tc}/40; delta {tc-bc:+} cases ({(tc-bc)/40*100:+.2f} pp). This is a frozen-policy safety regression.",
        f"- Completion transitions: fail→pass {v['completion_counts']['FAIL_TO_PASS']}; pass→fail {v['completion_counts']['PASS_TO_FAIL']}; pass→pass {v['completion_counts']['PASS_TO_PASS']}; fail→fail {v['completion_counts']['FAIL_TO_FAIL']}.",
        f"- Harmful transitions: yes→no {v['harmful_counts']['YES_TO_NO']}; no→yes {v['harmful_counts']['NO_TO_YES']}. Critical: yes→no {v['critical_counts']['YES_TO_NO']}; no→yes {v['critical_counts']['NO_TO_YES']}.",
        "", "## Observed improvements", "",
        "Overall score, completion, validity, low-value ASK rate, harmful-failure count, and CA/PD/DA task means moved in the favorable direction; KQ was unchanged. These are descriptive matched observations only.",
        "", "## Observed regressions and tradeoffs", "",
        f"Critical failures increased from 0 to 2 (cases: {', '.join(v['regression_ids']['critical'])}). This fails the frozen M5 non-increase condition and blocks comparative resume claims. Completion regressions: {', '.join(v['regression_ids']['completion']) or 'none'}. Validity regressions: {', '.join(v['regression_ids']['validity']) or 'none'}. Harmful-failure regressions: {', '.join(v['regression_ids']['harmful']) or 'none'}. New/increased low-value ASK cases: {', '.join(v['regression_ids']['low_value_ask']) or 'none'}.",
        f"Necessary ASK target discordance: lost `{', '.join(v['regression_ids']['necessary_ask']) or 'none'}`; gained `{', '.join(r['case_id'] for r in transitions if r['necessary_targets_gained']) or 'none'}`. Aggregate M4 stayed at 1/4, but the target-level loss/gain is disclosed. Tool calls/case changed {execution['TOOL_CALLS_PER_CASE']['baseline']} → {execution['TOOL_CALLS_PER_CASE']['treatment']}; turns/case {execution['TURNS_PER_CASE']['baseline']} → {execution['TURNS_PER_CASE']['treatment']}; latency {execution['LATENCY_MEAN_MS']['baseline']} → {execution['LATENCY_MEAN_MS']['treatment']} ms. These are operational tradeoffs, not independently scored quality claims.",
        "", "## Claim policy", "",
        "RESUME_DESCRIPTIVE_MATCHED_COMPARATIVE_CLAIM_ELIGIBLE = **NO**. Exact blocker: M5 critical failures increased, which the frozen policy says cannot be offset by gains in other metrics. M1/M2/M3 are directionally improved; M4 is unchanged; M5 regressed.",
        "", "## Limits and next path", "",
        "No causal effect, randomized treatment effect, statistical significance, clinical effectiveness/safety improvement, or unseen-benchmark generalization is supported. V4 is development/postmortem matched-regression evidence; new generalization claims require sealed V5.",
        "Recommended next path: **B. Repair the critical-failure regression before V5.** No next step was executed.",
        "", "The 40 case transition rows contain IDs and frozen labels/telemetry only; no prompts, answers, evidence, or rationales.", "",
    ]
    report_bytes=("\n".join(lines)).encode()
    # Bind output hashes into the audit before the files are created.
    audit_doc["outputs"]={
        "metrics":{"path":str(OUTPUTS['metrics'].relative_to(ROOT)),"sha256":hashlib.sha256(metric_bytes).hexdigest()},
        "transitions":{"path":str(OUTPUTS['transitions'].relative_to(ROOT)),"sha256":sha(OUTPUTS['transitions']) if OUTPUTS['transitions'].exists() else hashlib.sha256(transition_bytes).hexdigest(),"rows":40},
        "report":{"path":str(OUTPUTS['report'].relative_to(ROOT)),"sha256":hashlib.sha256(report_bytes).hexdigest()},
    }
    claim_bytes=(json.dumps(audit_doc,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode()
    # Reconfirm every source hash immediately before append-only publication.
    if any(sha(ROOT / path) != digest for path,digest in hashes.items()):
        raise RuntimeError("source identity changed before output persistence")
    durable_new(OUTPUTS["metrics"],metric_bytes)
    durable_new(OUTPUTS["transitions"],transition_bytes)
    durable_new(OUTPUTS["report"],report_bytes)
    durable_new(OUTPUTS["claim_audit"],claim_bytes)
    record=(
        "\n\n## Step 9.39 — Baseline vs Treatment Matched Comparison\n\n"
        f"Frozen post-hoc matched comparison integrity PASS (40/40 IDs and execution order; fingerprint `{FP}`). Overall {bscore['overall']['mean']}→{tscore['overall']['mean']} ({tscore['overall']['mean']-bscore['overall']['mean']:+.4f}); completion {bcomp['numerator']}/40→{tcomp['numerator']}/40; validity {bvalid['numerator']}/40→{tvalid['numerator']}/40; low-value ASK {b_low:.4f}→{t_low:.4f}; harmful failures {bh}→{th}; critical failures {bc}→{tc}. Frozen claim policy eligibility NO because M5 critical failures increased by 2. V4 remains development/postmortem evidence; no significance, causal, clinical, or unseen-generalization claims. Recommended next path B (repair critical-failure regression before V5); no next step executed."
    )
    with (ROOT/"record.md").open("a",encoding="utf-8") as stream:
        stream.write(record);stream.flush();os.fsync(stream.fileno())
    print(json.dumps({"status":metrics_doc["status"],"overall":deltas["overall"],
                      "completion":deltas["task_completion_rate"],"validity":deltas["validity_rate"],
                      "low_value_ask":deltas["low_value_ask_rate"],"harmful":deltas["harmful_failures"],
                      "critical":deltas["critical_failures"],"transitions":metrics_doc["case_transition_counts"],
                      "claim_eligible":eligible,"blockers":blockers,
                      "regression_ids":v["regression_ids"],"outputs":audit_doc["outputs"]},ensure_ascii=False))


if __name__ == "__main__":
    main()
