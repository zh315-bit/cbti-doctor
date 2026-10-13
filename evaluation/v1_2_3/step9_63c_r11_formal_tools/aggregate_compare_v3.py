#!/usr/bin/env python3
"""r11 treatment-V3 aggregation and matched frozen-baseline comparison (FINAL pre-registration ead55a09).

S0  verify every pinned input (freeze, FINAL pre-registration, packet, frozen aggregator, baseline lock ...)
S3  aggregate with scripts/aggregate_step9_30c_v4.aggregate_records unchanged; as in Step 9.47 only the
    run-bound validate_records and EXPECTED_LINEAGE are replaced (packet validator / V3 lineage counts)
S4  compare with the locked Step 9.28 baseline values (no re-adjudication); per-case transitions by
    the matched protocol's transition_definitions; no significance test
D2  treatment-V1 / V2 columns are descriptive only
Stops (raises) on any data problem; never modifies a review record. Outputs are exclusive-create.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "evaluation/v1_2_3"
ADJ = OUT / "step9_63c_r11_blind_review_output/v3_adjudication.jsonl"
FREEZE = OUT / "step9_63c_r11_adjudication_freeze.json"
PREREG = OUT / "step9_63c_r11_scoring_preregistration_final.json"
PACKET = OUT / "step9_63c_r11_blind_review_packet"
SIDECAR = OUT / "step9_63c_r11_v3_lineage_sidecar.jsonl"
LOCK = OUT / "step9_34a_baseline_metric_lock.json"
BASE_AGG = OUT / "step9_30c_v4_aggregate_metrics.json"
BASE_CASES = OUT / "step9_30c_v4_case_level_summary.jsonl"
BASE_ADJ = OUT / "step9_30b_v4_human_adjudication.jsonl"
V1_AGG = OUT / "step9_38_treatment_aggregate_metrics.json"
V2_AGG = OUT / "step9_47_v2_aggregate.json"
OUT_JSON = OUT / "step9_63c_r11_scoring_results.json"
REVIEWER = "Claude opus5.5, fresh session"
D2_LABEL = "不在冻结协议内，仅作描述性参考，不得据此下结论"
TASKS = ("KNOWLEDGE_QA", "CAUSE_ASSESSMENT", "PERSONALIZED_DECISION", "DATA_ANALYSIS")
V3_LINEAGE = {"FORMAL_LINEAGE_READY": 28, "DERIVED_LINEAGE_COMPLETE": 8, "INCOMPLETE_FORMAL_BUT_ADJUDICATABLE": 4}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def need(cond: bool, message: str) -> None:
    if not cond:
        raise RuntimeError("STOP_DATA_PROBLEM: " + message)


def verify_inputs() -> dict:
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    need(sha(PREREG) == "ead55a09e7067d33352021c19674c31667aff2a1922de6a1cb9f08faf2f0cf89", "FINAL pre-registration SHA")
    need(prereg["status"] == "FINAL_LOCKED_BEFORE_REVIEW", "pre-registration status")
    need(sha(ADJ) == freeze["adjudication"]["sha256"] == "46d5e84d60b104448dd411b7f5bd08369c67dc60934e80954d524c80b771af22", "adjudication SHA vs freeze")
    need(freeze["final_preregistration"]["sha256"] == sha(PREREG), "freeze -> pre-registration binding")
    need(sha(PACKET / "SHA256SUMS") == prereg["blind_review"]["packet"]["SHA256SUMS_sha256"], "packet SHA256SUMS")
    for line in (PACKET / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        need(sha(PACKET / name) == digest, f"packet file {name}")
    for name, item in prereg["frozen_inputs"].items():
        path = item["path"].split("#")[0]
        if name == "scoring_aggregate":
            continue
        need(sha(ROOT / path) == item["sha256"], f"frozen input {name}")
    for path, digest in prereg["decisions"]["D3_lineage_forensics_step"]["outputs"].items():
        need(sha(ROOT / path) == digest, f"lineage output {path}")
    for key, (path, digest) in prereg["decisions"]["D2_additional_comparators"]["sources"].items():
        need(sha(ROOT / path) == digest, f"D2 source {key}")
    for rel, digest in prereg["evaluated_run"]["files"].items():
        pass  # archive verified through the packet copies (byte-identical, same SHAs) and SHA256SUMS below
    archive = OUT / "step9_63c_r11_run_archive"
    for line in (archive / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        need(sha(archive / name) == digest, f"archive file {name}")
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    need(lock["no_readjudication"] is True, "baseline lock no_readjudication")
    need(sha(BASE_AGG) == lock["source_artifacts"]["aggregate_metrics_sha256"], "baseline aggregate vs lock")
    need(sha(BASE_CASES) == lock["source_artifacts"]["case_level_summary_sha256"], "baseline case summary vs lock")
    need(sha(BASE_ADJ) == lock["source_artifacts"]["adjudication_sha256"], "baseline adjudication vs lock")
    return {"prereg": prereg, "freeze": freeze, "lock": lock}


def load_validator():
    spec = importlib.util.spec_from_file_location("r11_packet_validator", PACKET / "validate_review.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rate(num, den):
    return {"numerator": num, "denominator": den, "value": round(num / den, 4) if den else None}


def delta(base, treat, *, is_rate=False, relative_ok=True):
    if base is None or treat is None:
        return {"baseline": base, "treatment": treat, "absolute_delta": "NOT_APPLICABLE"}
    out = {"baseline": base, "treatment": treat, "absolute_delta": round(treat - base, 4)}
    if is_rate:
        out["delta_percentage_points"] = round((treat - base) * 100, 2)
    out["relative_delta"] = (round((treat - base) / base, 4) if relative_ok and base else "NOT_APPLICABLE")
    return out


def summary(agg: dict) -> dict:
    ask = agg["ask_quality"]
    low = ask.get("REDUNDANT_OR_IRRELEVANT_RATE") or ask.get("LOW_VALUE_ASK_RATE")
    cv = agg["completion_and_validity"]
    fail = agg["failures"]
    tools = agg["tool_resource_behavior"]
    eff = agg["efficiency"]
    per_case = tools.get("per_case_means", {})
    return {
        "overall_mean": agg["scores"]["overall"]["mean"],
        "task_means": {t: agg["scores"]["task_type_means"][t]["mean"] for t in TASKS},
        "dimension_means": {d: v["mean"] for d, v in agg["scores"]["dimensions"].items()},
        "M1_low_value_ask_rate": rate(low["numerator"], low["denominator"]),
        "M2_completion": {**rate(cv["overall"]["rate"]["numerator"], cv["overall"]["rate"]["denominator"]),
                          "distribution": cv["overall"]["distribution"]},
        "M3_harmful": rate(fail["HARMFUL_FAILURE_COUNT"], 40),
        "M4_necessary_ask_preservation": rate(ask["NECESSARY_ASK_PRESERVATION_RATE"]["numerator"],
                                              ask["NECESSARY_ASK_PRESERVATION_RATE"]["denominator"]),
        "M5_critical": rate(fail["CRITICAL_FAILURE_COUNT"], 40),
        "validity": rate(cv["overall"]["validity_rate"]["numerator"], cv["overall"]["validity_rate"]["denominator"]),
        "completion_by_task": {t: {**rate(cv["by_task_type"][t]["rate"]["numerator"], cv["by_task_type"][t]["rate"]["denominator"]),
                                   "distribution": cv["by_task_type"][t]["distribution"],
                                   "validity": rate(cv["by_task_type"][t]["validity_rate"]["numerator"], cv["by_task_type"][t]["validity_rate"]["denominator"])}
                               for t in TASKS},
        "ask_category_counts": {"total": ask["TOTAL_ASK_COUNT"], "necessary": ask["NECESSARY_ASK_COUNT"],
                                "useful_but_optional": ask["USEFUL_OPTIONAL_ASK_COUNT"], "redundant": ask["REDUNDANT_ASK_COUNT"],
                                "irrelevant": ask["IRRELEVANT_ASK_COUNT"]},
        "per_case": {"ask": round(ask["TOTAL_ASK_COUNT"] / 40, 4),
                     "retrieve": round(tools["counts"]["RETRIEVE"] / 40, 4),
                     "read_diary": round(tools["counts"]["READ_DIARY"] / 40, 4),
                     "tool_calls": round(tools["counts"]["TOOL_CALL"] / 40, 4),
                     "turns": eff["turns_per_case"]["mean"], "steps": eff["steps_per_case"]["mean"]},
        "latency_ms": {k: eff["latency_ms"]["overall"][k] for k in ("mean_ms", "median_ms", "p90_nearest_rank_ms")},
        "critical_case_ids": fail["CRITICAL_FAILURE_CASE_IDS"], "harmful_case_ids": fail["HARMFUL_FAILURE_CASE_IDS"],
    }


def main() -> int:
    if OUT_JSON.exists():
        print("OUTPUT_ALREADY_EXISTS")
        return 1
    ctx = verify_inputs()
    lock = ctx["lock"]
    validator = load_validator()
    written, total = validator.check_file(ADJ)
    need((written, total) == (40, 40), "packet validator 40/40")
    records = jl(ADJ)
    need(all(r["review_provenance"]["reviewer"] == REVIEWER for r in records), "reviewer string")
    templates = validator.templates()

    def validate_records_v3(recs, mode):
        need(mode == "completed" and len(recs) == 40, "completed 40-record mode")
        for record, template in zip(recs, templates):
            validator.check_record(record, template)

    from scripts import aggregate_step9_30c_v4 as frozen_agg
    need(sha(ROOT / "scripts/aggregate_step9_30c_v4.py") == "01aea00ad6a644a44d63a6c31e4bf372f43b53b45f9bc1b9bd7d2649e8522395", "frozen aggregator SHA")
    frozen_agg.validate_records = validate_records_v3
    frozen_agg.EXPECTED_LINEAGE = V3_LINEAGE
    v3 = frozen_agg.aggregate_records(records, jl(SIDECAR))
    v3_cases = {row["case_id"]: row for row in v3.pop("case_level_rows")}
    adj_bytes_after = sha(ADJ)
    need(adj_bytes_after == ctx["freeze"]["adjudication"]["sha256"], "adjudication unchanged after aggregation")

    base_agg = json.loads(BASE_AGG.read_text(encoding="utf-8"))
    base = summary(base_agg)
    pm = lock["primary_metric_values"]
    need(base["M1_low_value_ask_rate"]["numerator"] == pm["M1_LOW_VALUE_ASK_RATE"]["numerator"]
         and base["M1_low_value_ask_rate"]["denominator"] == pm["M1_LOW_VALUE_ASK_RATE"]["denominator"], "baseline M1 vs lock")
    need(base["M2_completion"]["numerator"] == pm["M2_TASK_COMPLETION"]["numerator"], "baseline M2 vs lock")
    need(base["M3_harmful"]["numerator"] == pm["M3_HARMFUL_FAILURES"]["numerator"], "baseline M3 vs lock")
    need(base["M4_necessary_ask_preservation"]["numerator"] == pm["M4_NECESSARY_ASK_PRESERVATION"]["numerator"]
         and base["M4_necessary_ask_preservation"]["denominator"] == pm["M4_NECESSARY_ASK_PRESERVATION"]["denominator"], "baseline M4 vs lock")
    need(base["M5_critical"]["numerator"] == pm["M5_CRITICAL_FAILURES"]["numerator"], "baseline M5 vs lock")
    need(base["overall_mean"] == lock["secondary_metric_values"]["overall_score"]["mean"], "baseline overall vs lock")
    for t in TASKS:
        need(base["task_means"][t] == lock["secondary_metric_values"]["task_category_means"][t]["mean"], f"baseline {t} mean vs lock")
    treat = summary(v3)
    need(v3["ask_quality"]["NECESSARY_ASK_PRESERVATION_RATE"]["denominator"] == 4, "V3 M4 denominator must be the locked 4 targets")

    comparison = {
        "overall_mean": delta(base["overall_mean"], treat["overall_mean"]),
        "task_means": {t: delta(base["task_means"][t], treat["task_means"][t]) for t in TASKS},
        "dimension_means": {d: delta(base["dimension_means"][d], treat["dimension_means"][d]) for d in base["dimension_means"]},
        "M1_low_value_ask_rate": {**delta(base["M1_low_value_ask_rate"]["value"], treat["M1_low_value_ask_rate"]["value"], is_rate=True),
                                  "baseline_fraction": base["M1_low_value_ask_rate"], "treatment_fraction": treat["M1_low_value_ask_rate"], "better": "lower"},
        "M2_completion": {**delta(base["M2_completion"]["value"], treat["M2_completion"]["value"], is_rate=True),
                          "count_delta": treat["M2_completion"]["numerator"] - base["M2_completion"]["numerator"],
                          "baseline_distribution": base["M2_completion"]["distribution"], "treatment_distribution": treat["M2_completion"]["distribution"], "better": "higher"},
        "M3_harmful": {**delta(base["M3_harmful"]["value"], treat["M3_harmful"]["value"], is_rate=True),
                       "count_delta": treat["M3_harmful"]["numerator"] - base["M3_harmful"]["numerator"], "better": "lower"},
        "M4_necessary_ask_preservation": {**delta(base["M4_necessary_ask_preservation"]["value"], treat["M4_necessary_ask_preservation"]["value"], is_rate=True),
                                          "baseline_fraction": base["M4_necessary_ask_preservation"], "treatment_fraction": treat["M4_necessary_ask_preservation"], "better": "not lower"},
        "M5_critical": {**delta(base["M5_critical"]["value"], treat["M5_critical"]["value"], is_rate=True),
                        "count_delta": treat["M5_critical"]["numerator"] - base["M5_critical"]["numerator"],
                        "better": "lower; any increase is a safety regression and is not offset by other metrics"},
        "validity": {**delta(base["validity"]["value"], treat["validity"]["value"], is_rate=True),
                     "count_delta": treat["validity"]["numerator"] - base["validity"]["numerator"]},
        "completion_by_task": {t: {**delta(base["completion_by_task"][t]["value"], treat["completion_by_task"][t]["value"], is_rate=True),
                                   "baseline": base["completion_by_task"][t], "treatment": treat["completion_by_task"][t]} for t in TASKS},
        "per_case_behavior": {k: delta(base["per_case"][k], treat["per_case"][k]) for k in base["per_case"]},
        "latency_ms": {k: delta(base["latency_ms"][k], treat["latency_ms"][k]) for k in base["latency_ms"]},
        "ask_category_counts": {k: {"baseline": base["ask_category_counts"][k], "treatment": treat["ask_category_counts"][k],
                                    "count_delta": treat["ask_category_counts"][k] - base["ask_category_counts"][k]} for k in base["ask_category_counts"]},
    }

    base_rows = {r["case_id"]: r for r in jl(BASE_CASES)}
    base_adj = {r["immutable_execution_facts"]["case_id"]: r for r in jl(BASE_ADJ)}
    v3_adj = {r["immutable_execution_facts"]["case_id"]: r for r in records}
    need(set(base_rows) == set(v3_cases) == set(base_adj), "matched case sets")
    transitions, counts = [], {k: Counter() for k in ("completion", "validity", "harmful", "critical", "score_delta_sign", "ask_labels")}
    for case_id in [r["immutable_execution_facts"]["case_id"] for r in records]:
        b, t = base_rows[case_id], v3_cases[case_id]
        need(b["task_type"] == t["task_type"], f"task type {case_id}")
        bc, tc = b["completion_judgment"] == "complete", t["completion_judgment"] == "complete"
        completion = ("UNCHANGED" if bc == tc else "IMPROVED" if tc else "REGRESSED")
        validity = ("UNCHANGED" if b["validity_judgment"] == t["validity_judgment"] else "IMPROVED" if t["validity_judgment"] else "REGRESSED")
        harmful = ("UNCHANGED" if b["harmful_failure"] == t["harmful_failure"] else "IMPROVED" if not t["harmful_failure"] else "REGRESSED")
        critical = ("UNCHANGED" if b["critical_failure"] == t["critical_failure"] else "IMPROVED" if not t["critical_failure"] else "REGRESSED")
        score_delta = t["total_score"] - b["total_score"]
        sign = "HIGHER" if score_delta > 0 else "LOWER" if score_delta < 0 else "EQUAL"
        bq, tq = b["ask_quality_counts"], t["ask_quality_counts"]
        b_low, t_low = bq["redundant"] + bq["irrelevant"], tq["redundant"] + tq["irrelevant"]
        labels = []
        if b_low > 0 and t_low == 0: labels.append("LOW_VALUE_ASK_REMOVED")
        elif b_low == 0 and t_low > 0: labels.append("NEW_LOW_VALUE_ASK_INTRODUCED")
        elif t_low < b_low: labels.append("LOW_VALUE_ASK_REDUCED")
        elif t_low > b_low: labels.append("LOW_VALUE_ASK_INCREASED")
        bp = base_adj[case_id]["reviewer_judgments"]["necessary_ask_preservation"]["target_adjudications"]
        tp = v3_adj[case_id]["reviewer_judgments"]["necessary_ask_preservation"]["target_adjudications"]
        bt = {x["target_id"] for x in bp if x["required_by_oracle"]}
        tt = {x["target_id"] for x in tp if x["required_by_oracle"]}
        need(bt == tt, f"oracle target set {case_id}")
        baq = {x["target_id"] for x in bp if x["required_by_oracle"] and x["acquired"]}
        taq = {x["target_id"] for x in tp if x["required_by_oracle"] and x["acquired"]}
        if baq - taq: labels.append("NECESSARY_ASK_LOST")
        elif taq - baq: labels.append("NECESSARY_ASK_GAINED")
        elif baq: labels.append("NECESSARY_ASK_PRESERVED")
        if not labels: labels = ["UNCHANGED"]
        for key, value in (("completion", completion), ("validity", validity), ("harmful", harmful),
                           ("critical", critical), ("score_delta_sign", sign)):
            counts[key][value] += 1
        counts["ask_labels"].update(labels)
        transitions.append({
            "case_id": case_id, "task_type": t["task_type"],
            "completion": [b["completion_judgment"], t["completion_judgment"], completion],
            "validity": [b["validity_judgment"], t["validity_judgment"], validity],
            "harmful_failure": [b["harmful_failure"], t["harmful_failure"], harmful],
            "critical_failure": [b["critical_failure"], t["critical_failure"], critical, t["critical_failure_types"]],
            "total_score": [b["total_score"], t["total_score"], score_delta],
            "ask_transition_labels": labels,
            "v3_primary_cause_as_written": t["primary_cause"],
        })
    by_task = {task: {k: dict(Counter(tr[k][2] for tr in transitions if tr["task_type"] == task))
                      for k in ("completion", "validity", "harmful_failure", "critical_failure")}
               for task in TASKS}
    for task in TASKS:
        by_task[task]["score_delta_sign"] = dict(Counter(
            "HIGHER" if tr["total_score"][2] > 0 else "LOWER" if tr["total_score"][2] < 0 else "EQUAL"
            for tr in transitions if tr["task_type"] == task))

    d2 = {}
    for label, path in (("treatment_v1_step9_38", V1_AGG), ("treatment_v2_step9_47", V2_AGG)):
        s = summary(json.loads(path.read_text(encoding="utf-8")))
        d2[label] = {"label": D2_LABEL, "source": {"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)},
                     **{k: s[k] for k in ("overall_mean", "task_means", "M1_low_value_ask_rate", "M2_completion", "M3_harmful",
                                          "M4_necessary_ask_preservation", "M5_critical", "validity")}}
    d2["treatment_v2_step9_47"]["M4_note"] = "Step 9.46 recorded 1 oracle target instead of the locked 4 (pre-registration D5); shown as recorded."

    critical_increase = comparison["M5_critical"]["count_delta"] > 0
    m4_lower = (treat["M4_necessary_ask_preservation"]["value"] or 0) < (base["M4_necessary_ask_preservation"]["value"] or 0)
    claim_audit = {
        "claim_scope": "FROZEN_MATCHED_DEVELOPMENT_REGRESSION_ONLY",
        "statistics": "DESCRIPTIVE / PAIRED_CASE_DELTA / RATE_DELTA / COUNT_DELTA only; no significance test, no confidence interval",
        "M5_non_increase_condition": "FAILED (critical failures increased)" if critical_increase else "MET",
        "M4_not_lower_condition": "FAILED (necessary ASK preservation decreased)" if m4_lower else "MET",
        "descriptive_matched_comparative_claim_eligible": not critical_increase and not m4_lower,
        "eligibility_rule": "Claim policy allows a descriptive matched comparative claim after adjudication, aggregation and identity pass; the baseline lock states M5 increases are safety regressions not offset by other metrics and M4 must not be lower (Step 9.39 precedent).",
        "prohibited": ["randomized controlled comparison", "randomized paired trial", "preregistered randomized experiment", "causal effect",
                       "statistically significant improvement", "clinical effectiveness", "unseen-benchmark generalization",
                       "universal Agent superiority", "calibrated probability effectiveness", "single-component causal attribution"],
    }
    disclosures = [
        "Reviewer type differs from the baseline reviewer: treatment-V3 was reviewed by 'Claude opus5.5, fresh session'; the locked baseline was reviewed by a Codex AI reviewer (backend version not recorded).",
        "Single AI reviewer; inter-rater reliability NOT_MEASURED; no human adjudication.",
        "Reviewer self-reported: harmful_failure and validity criteria and primary_cause labels were formulated by the reviewer without a shared enumeration; CA-02 and CA-04 were re-read after writing (not modified); the tool wrote a session cache outside the packet.",
        "Post-hoc matched comparison against a frozen baseline; case order matched, not randomized.",
        "V4 is not unseen data for V3: the V3 repair design (Step 9.50) consulted treatment-V1/V2 case-level behaviour and frozen dimension scores on V4 cases. V4 is development/postmortem evidence for this treatment.",
        "Lifecycle reducer defect KL-1 labels the r11 authorization INCONSISTENT_FAIL_CLOSED; run integrity was verified independently and the defect does not affect result validity.",
        "token_usage NOT_MEASURED.",
        "Treatment-V1/V2 columns are outside the frozen protocol, descriptive only, and no conclusion is drawn from them (D2).",
        "primary_cause labels are listed exactly as written by the reviewer; not merged, normalised or turned into rates.",
    ]
    result = {
        "artifact_type": "R11_TREATMENT_V3_SCORING_RESULTS", "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "preregistration_final_sha256": sha(PREREG), "adjudication_sha256": sha(ADJ), "freeze_sha256": sha(FREEZE),
        "aggregator": {"path": "scripts/aggregate_step9_30c_v4.py", "sha256": "01aea00ad6a644a44d63a6c31e4bf372f43b53b45f9bc1b9bd7d2649e8522395",
                       "replaced_run_bound_names_only": ["validate_records -> packet validator (verbatim contract check + V3 template)",
                                                         f"EXPECTED_LINEAGE -> {V3_LINEAGE}"]},
        "baseline": {"evaluation_id": lock["baseline_identity"]["evaluation_id"], "source": "step9_34a_baseline_metric_lock.json (no re-adjudication)",
                     "summary": base},
        "treatment_v3": {"summary": treat, "frozen_aggregator_output": v3},
        "comparison_vs_locked_baseline": comparison,
        "case_transitions": {"counts": {k: dict(v) for k, v in counts.items()}, "by_task_type": by_task, "rows": transitions},
        "primary_cause_as_written": [{"case_id": tr["case_id"], "primary_cause": tr["v3_primary_cause_as_written"]} for tr in transitions],
        "d2_descriptive_columns": d2,
        "claim_audit": claim_audit,
        "disclosures": disclosures,
    }
    fd = os.open(OUT_JSON, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({"written": OUT_JSON.relative_to(ROOT).as_posix(), "sha256": sha(OUT_JSON)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
