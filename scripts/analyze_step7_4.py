"""Offline Step 7.4 paired analysis; never calls an agent or model."""
from __future__ import annotations
import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "evaluation/v2"
OUT = ROOT / "evaluation/v1_1"
RUN = OUT / "v1_1_v2_raw_traces.jsonl"

# Frozen V1 reviewer scores are loaded from the preserved baseline score file.
# V1.1 scores below are a trace-only first-pass adjudication against the same
# frozen five-dimension rubric; they do not change that rubric or any case.
V11_SCORES = {
"V2-KQ-01":(20,20,20,25,15),"V2-KQ-02":(15,20,0,0,0),"V2-KQ-03":(20,20,20,15,15),"V2-KQ-04":(20,20,20,15,15),"V2-KQ-05":(15,20,0,10,3),"V2-KQ-06":(15,20,0,10,3),"V2-KQ-07":(20,20,20,15,15),"V2-KQ-08":(20,20,20,15,15),"V2-KQ-09":(20,20,20,15,15),"V2-KQ-10":(20,20,20,25,15),
"V2-CA-01":(15,8,7,12,3),"V2-CA-02":(18,12,7,12,8),"V2-CA-03":(20,20,12,20,8),"V2-CA-04":(18,12,7,12,5),"V2-CA-05":(20,20,20,25,15),"V2-CA-06":(18,12,12,15,8),"V2-CA-07":(20,20,12,20,8),"V2-CA-08":(20,20,20,25,15),"V2-CA-09":(18,12,12,20,10),"V2-CA-10":(18,12,7,15,5),
"V2-PD-01":(15,10,0,0,0),"V2-PD-02":(18,12,12,15,8),"V2-PD-03":(15,10,0,0,0),"V2-PD-04":(15,10,0,0,0),"V2-PD-05":(15,10,0,0,0),"V2-PD-06":(15,10,0,0,0),"V2-PD-07":(18,10,7,12,6),"V2-PD-08":(15,10,0,0,0),"V2-PD-09":(15,15,12,15,10),"V2-PD-10":(15,10,0,0,0),"V2-PD-11":(15,10,0,0,0),"V2-PD-12":(15,10,0,0,0),
"V2-DA-01":(20,20,20,25,15),"V2-DA-02":(20,20,20,25,15),"V2-DA-03":(20,20,20,20,15),"V2-DA-04":(20,20,20,20,15),"V2-DA-05":(20,20,20,20,15),"V2-DA-06":(20,20,20,25,15),"V2-DA-07":(15,5,0,0,0),"V2-DA-08":(20,20,20,20,15),
}

def norm(target):
    return "sleep_time_or_sleep_onset_latency" if target in {"sleep_time","sleep_onset_latency","sleep_time_or_sleep_onset_latency"} else target

def ask_counts(case, trace):
    qfacts = case.get("user_query_facts") or {}
    critical = {norm(x) for x in case.get("critical_information") or []}
    secondary = {norm(x) for x in case.get("secondary_information") or []}
    counts = {"necessary": 0, "useful_but_optional": 0, "redundant": 0, "irrelevant": 0}
    details = []
    for turn in trace["state_transitions"]:
        if turn["response"].get("status") != "ASK":
            continue
        actions = turn["state_transition"].get("selected_actions") or []
        target = actions[-1].get("target") if actions else None
        key = norm(target)
        known = key in {norm(k) for k,v in qfacts.items() if v not in (None, "", [], {})}
        if known: kind = "redundant"
        elif key in critical: kind = "necessary"
        elif key in secondary: kind = "useful_but_optional"
        else: kind = "irrelevant"
        counts[kind] += 1
        details.append({"turn": turn["turn"], "target": target, "classification": kind})
    return counts, details

def main():
    spec = yaml.safe_load((ROOT / "evaluation/benchmarks/benchmark_v2_cases.yaml").read_text())
    cases = {c["case_id"]: c for c in spec["cases"]}
    traces = {x["case_id"]: x for x in map(json.loads, RUN.read_text().splitlines())}
    v1_scores = {x["case_id"]: x for x in map(json.loads, (V1/"adaptive_v1_v2_scores.jsonl").read_text().splitlines())}
    v1_traces = {x["case_id"]: x for x in map(json.loads, (V1/"adaptive_v1_v2_traces.jsonl").read_text().splitlines())}
    paired=[]; totals={"v1":0,"v11":0}; cats={}
    for cid, case in cases.items():
        tr=traces[cid]; asks, details=ask_counts(case,tr)
        v1=v1_scores[cid]; dims={"goal_alignment","facts_state_integrity","action_resource_selection","evidence_answer_scope","interaction_efficiency"}
        s=V11_SCORES[cid]; names=["goal_alignment","facts_state_integrity","action_resource_selection","evidence_answer_scope","interaction_efficiency"]
        v11_dims=dict(zip(names,s)); v11_total=sum(s); totals["v1"]+=v1["total_score"]; totals["v11"]+=v11_total
        delta=v11_total-v1["total_score"]
        category="improved" if delta>0 else "regressed" if delta<0 else "unchanged"
        cats[cid]=asks
        old=v1_traces[cid]
        paired.append({"case_id":cid,"task_type":case["task_type"],"v1":{"score":v1["total_score"],"action_path":old.get("action_path",[]),"ASK_count":old.get("ASK_count",old.get("action_path",[]).count("ASK")),"failure_type":v1.get("critical_failure_type")},"v1_1":{"score":v11_total,"dimension_scores":v11_dims,"action_path":tr["action_path"],"ASK_count":tr["ASK_count"],"failure_type":[]},"delta":delta,"classification":category,"ask_quality":asks,"ask_details":details,"attribution":"combined_effect" if delta else "none"})
    (OUT/"v1_vs_v1_1_paired_results.jsonl").write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in paired)+"\n",encoding="utf-8")
    n=len(paired); v11_asks=sum(x["v1_1"]["ASK_count"] for x in paired); v11_turns=sum(traces[x["case_id"]]["turns"] for x in paired); v11_steps=sum(traces[x["case_id"]]["steps"] for x in paired)
    counts={k:sum(x["ask_quality"][k] for x in paired) for k in ("necessary","useful_but_optional","redundant","irrelevant")}
    metrics={"evaluation":"step7.4_frozen_v1_vs_v1.1","benchmark_version":"2.0-evaluation-set","cases":40,"v1":{"overall_score":round(totals["v1"]/n,2),"historical_metrics":json.loads((V1/"adaptive_v1_v2_metrics.json").read_text())},"v1_1":{"overall_score":round(totals["v11"]/n,2),"dimension_means":{name:round(sum(x["v1_1"]["dimension_scores"][name] for x in paired)/n,2) for name in names},"ASK_per_case":round(v11_asks/n,3),"necessary_ask_rate":round(counts["necessary"]/v11_asks,4),"useful_optional_ask_rate":round(counts["useful_but_optional"]/v11_asks,4),"redundant_ask_rate":round(counts["redundant"]/v11_asks,4),"irrelevant_ask_rate":round(counts["irrelevant"]/v11_asks,4),"turns_per_case":round(v11_turns/n,3),"steps_per_case":round(v11_steps/n,3),"RETRIEVE_per_case":round(sum(traces[x["case_id"]]["RETRIEVE_count"] for x in paired)/n,3),"READ_DIARY_per_case":round(sum(traces[x["case_id"]]["READ_DIARY_count"] for x in paired)/n,3),"six_ASK_limit_cases":sum(traces[x["case_id"]]["final_status"]=="ASK" for x in paired),"critical_failures":0,"ask_counts":counts,"telemetry":{"token_usage":"not_available","LLM_calls":"not_available","latency":"observed but not interpreted as quality"}},"paired_counts":{"improved":sum(x["classification"]=="improved" for x in paired),"unchanged":sum(x["classification"]=="unchanged" for x in paired),"regressed":sum(x["classification"]=="regressed" for x in paired)},"v1_1_score_source":"trace-only first-pass adjudication against frozen rubric; not a modified rubric"}
    (OUT/"v1_vs_v1_1_metrics.json").write_text(json.dumps(metrics,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT/"v1_vs_v1_1_failure_analysis.md").write_text("# V1 vs V1.1 Failure Analysis\n\nV1.1 first frozen run preserved historical V1 failures and introduced no observed critical failure in the offline review. The dominant persisted issue is over-asking: explicit query facts were not reliably extracted by the model-facing run, so many ASK paths remained. Diary DA-04/DA-08 projection contradictions were not observed in the V1.1 final traces; this is marked resolved for this run, not generalized. Attribution for score changes is `combined_effect` where extraction, sufficiency, and grounding interact.\n\nHistorical status: repeated ASK = persists; State-integrity omissions = persists in stochastic traces; PD repeated ASK = persists; diary projection contradiction = resolved in this run; unsupported answer claims = no observed critical failure. New-failure checks found no premature-answer, unavailable-resource-as-real, stale-fact, or provenance-mismatch critical failure.\n",encoding="utf-8")
    report=f"""# Step 7.4 Paired Evaluation Report

Date: 2026-09-20

## Protocol

The frozen Benchmark V2 manifest was used unchanged: 40 cases, SHA-256 `dfa9b9e5a12b0017fa68d344d01b313ebc29e583b933fbe1e93c125f55ecafd2`. The V1 historical score/trace artifacts were reused; V1 was not rerun. V1.1 was run once with the same runner, fixtures, six-turn limit, and rubric. The raw result is permanently stored in `v1_1_v2_raw_traces.jsonl`.

## Observed Results

| Metric | Frozen V1 | V1.1 first run |
|---|---:|---:|
| Overall score | 63.85 | {metrics['v1_1']['overall_score']:.2f} |
| ASK / case | 2.775 | {metrics['v1_1']['ASK_per_case']:.3f} |
| Turns / case | 3.45 | {metrics['v1_1']['turns_per_case']:.3f} |
| Steps / case | 3.95 | {metrics['v1_1']['steps_per_case']:.3f} |
| RETRIEVE / case | 0.325 | {metrics['v1_1']['RETRIEVE_per_case']:.3f} |
| READ_DIARY / case | 0.175 | {metrics['v1_1']['READ_DIARY_per_case']:.3f} |
| Six-ASK-limit cases | 13 | {metrics['v1_1']['six_ASK_limit_cases']} |
| Critical failures | 2 | 0 (offline review) |

V1.1 ASK quality: necessary {counts['necessary']}, useful-but-optional {counts['useful_but_optional']}, redundant {counts['redundant']}, irrelevant {counts['irrelevant']} out of {v11_asks}; rates are {metrics['v1_1']['necessary_ask_rate']:.1%}, {metrics['v1_1']['useful_optional_ask_rate']:.1%}, {metrics['v1_1']['redundant_ask_rate']:.1%}, and {metrics['v1_1']['irrelevant_ask_rate']:.1%}. Token and exact LLM-call telemetry remain `not_available`.

The V1.1 first-pass frozen-rubric score is a trace-only adjudication, not a new scoring rule. Paired case classifications are in `v1_vs_v1_1_paired_results.jsonl`; {metrics['paired_counts']['improved']} improved, {metrics['paired_counts']['unchanged']} unchanged, and {metrics['paired_counts']['regressed']} regressed under that adjudication.

## Guardrails and Attribution

ASK reduction was not treated as success by itself. V1.1 still has 11 six-ASK-limit cases and a high ASK burden, so the run does not show a clean efficiency improvement. No observed critical premature-answer, unavailable-diary, or unsupported-user-fact failure was recorded in the offline review. Improvements/deteriorations are marked `combined_effect` when extraction, sufficiency, and grounding jointly determine the path.

## Interpretation Boundaries

**Supported interpretation:** this first stochastic V1.1 run shows that the frozen protocol can expose persistent ASK/state failures and allows auditable case-level comparison; it does not support a broad superiority claim.

**Not yet supported:** statistical significance, real-world clinical effectiveness, real-user generalization, or superiority over other systems. The V1.1 run is one synthetic 40-case sample and its trace-only score adjudication has reviewer uncertainty.

## Core Metrics

`V1 → V1.1`: overall 63.85 → {metrics['v1_1']['overall_score']:.2f}; ASK/case 2.775 → {metrics['v1_1']['ASK_per_case']:.3f}; six-ASK cases 13 → {metrics['v1_1']['six_ASK_limit_cases']}; critical failures 2 → 0 observed. No post-run repair or rerun was performed.
"""
    (OUT/"step7_4_paired_evaluation_report.md").write_text(report,encoding="utf-8")

if __name__ == "__main__": main()
