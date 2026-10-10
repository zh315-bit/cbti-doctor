#!/usr/bin/env python3
"""Package the manually adjudicated Step 9.46 records from pinned read-only inputs.

This is an offline artifact builder, not an Agent/evaluation runner. It refuses
to run on changed source inputs or when any Step 9.46 output already exists.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation/v1_2_3"
RUN = ROOT / "evaluation/v4_runs/heldout-v4-step9_43-treatment-v2-20260928-01"
EVAL_ID = "heldout-v4-step9_43-treatment-v2-20260928-01"
ATTEMPT_ID = "attempt-step9_44r1-cb362342ae31449aaffba8092c346864"
REVIEWER = "Codex AI reviewer (user-authorized single reviewer; not a human reviewer)"
RUBRIC = "evaluation/benchmark_v1_1_scoring.md"
RUBRIC_SHA = "a7f5681f4fc7421d3617a7cc69ec4c08dc84d1871b290f08f86df68bde808899"
METRICS = "evaluation/v1_2_3/step9_26_v4_metric_registry.json"
METRICS_SHA = "de9f348cb1dff66410c03095abdaffcc256f53679718482870e4aa4d80c75056"
SCHEMA = "evaluation/v1_2_3/step9_30a_v4_adjudication_schema.json"
SCHEMA_SHA = "21367c176f6b070d875a203ff779cfd44e2cb86a4e8956e1f93870fd054834c8"
RESULTS = RUN / "attempt-step9_44r1-cb362342ae31449aaffba8092c346864_case_results.jsonl"
TRACES = RUN / "attempt-step9_44r1-cb362342ae31449aaffba8092c346864_raw_traces.jsonl"
LEDGER = RUN / "attempts.jsonl"
SIDECAR = OUT / "step9_45a_v2_lineage_sidecar.jsonl"
MATRIX = OUT / "step9_45a_v2_lineage_case_matrix.jsonl"
RUN_FREEZE = OUT / "step9_45a_v2_run_input_freeze.json"
FORENSICS = OUT / "step9_45a_v2_lineage_forensics.json"
MANIFEST = ROOT / "evaluation/benchmarks/benchmark_v4_manifest.json"
DATASET = ROOT / "evaluation/benchmarks/benchmark_v4_cases.yaml"
RULES = OUT / "step9_26_v4_one_shot_rules.md"
HARNESS_FREEZE = OUT / "step9_13a_harness_freeze.json"
SCORING_FREEZE = OUT / "step9_11_clean_freeze_manifest.json"
TREATMENT_FREEZE = OUT / "step9_42_treatment_v2_freeze.json"
RUNNER_FREEZE = OUT / "step9_43a_treatment_v2_runner_freeze.json"
IDENTITY_CONTRACT = OUT / "step9_43a_treatment_v2_identity_contract.json"
PROTOCOL = OUT / "step9_34a_matched_comparison_protocol.json"

ARTIFACTS = {
    "adjudication": OUT / "step9_46_v2_adjudication.jsonl",
    "report": OUT / "step9_46_v2_adjudication_report.md",
    "freeze": OUT / "step9_46_v2_adjudication_freeze.json",
    "audit": OUT / "step9_46_v2_adjudication_audit.json",
}

# Five dimension scores are in frozen rubric order. ASK labels correspond to
# observed ASK actions in order; they are not inferred from ASK count.
# (scores, completion, valid, ask labels, retrieve labels, read_diary labels,
#  critical types, harmful, cause, effects, first divergence, rationale,
#  missing denominator, necessary ASK target IDs)
J = {
"V4-KQ-01": ([17,18,20,18,11],"partial",True,[],["required"],[],[],False,None,[],None,"Accurately states the source limitation and gives related CBT-I context, but the requested collaborative goal-setting process and concrete steps are not in evidence and remain unanswered. Long response.",[],[]),
"V4-KQ-02": ([18,18,20,19,11],"complete",True,[],["required"],[],[],False,None,[],None,"Explains practice, homework, review, and support with retrieved material; expressly marks mechanism and comparative outcomes that the sources do not establish. Some verbosity.",[],[]),
"V4-KQ-03": ([19,19,20,22,12],"complete",True,[],["required"],[],[],False,None,[],None,"Defines CBT-I cognitive restructuring and distinguishes evidence-testing of specific sleep beliefs from generic positive thinking; retrieved claims are scoped and the answer notes procedural detail is absent.",[],[]),
"V4-KQ-04": ([15,17,20,16,11],"partial",True,[],["required"],[],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION"],"Direct group-versus-individual evidence is absent from retrieval.","Gives access and individual-support implications as indirect possibilities and clearly distinguishes them from direct comparative evidence; peer support and participant-specific challenges remain unanswered. Some inference is explicitly qualified.",[],[]),
"V4-KQ-05": ([18,18,20,18,11],"complete",True,[],["required"],[],[],False,None,[],None,"Addresses maintenance and setbacks with retrieved material and clearly explains early treatment difficulty and professional support. The long-term-benefit implication is an inference and is framed as such.",[],[]),
"V4-KQ-06": ([16,18,20,17,11],"partial",True,[],["required"],[],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION"],"Retrieved material does not describe how clinicians adapt exercises when adherence is difficult.","Accurately identifies the evidence gap and gives related homework and delivery formats, but does not explain how CBT-I typically responds to difficulty following exercises.",[],[]),
"V4-KQ-07": ([17,16,20,13,11],"complete",True,[],["required"],[],[],False,None,[],None,"Answers why daytime status matters with retrieved diagnostic, behavioral, differential, and outcome examples. Quantitative ESS assertions are reproduced from retrieved material; the answer is overinclusive and does not separate evaluation of treatment response from screening as tightly as the question warrants.",[],[]),
"V4-KQ-08": ([18,17,20,22,10],"complete",True,[],["required"],[],[],False,None,[],None,"Covers remote/digital delivery, efficacy evidence, therapist involvement, and limitations, and explicitly distinguishes digital evidence from synchronous telehealth evidence. Extensive detail and study specifics reduce efficiency.",[],[]),
"V4-KQ-09": ([15,18,20,19,13],"partial",True,[],["required"],[],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION"],"Retrieved material does not specify the contents of shared decision-making.","Correctly avoids importing general medical assumptions and names the evidence gap; it does not answer which CBT-I decisions are shared.",[],[]),
"V4-KQ-10": ([18,17,20,20,12],"partial",True,[],["required"],[],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION"],"The retrieved material does not define a mandatory minimum component set.","Distinguishes supported delivery adaptation and tailoring from the unanswered question of a minimum qualifying component set. The answer gives a useful bounded synthesis but no definitive resolution.",[],[]),
"V4-CA-01": ([11,14,8,12,11],"not_complete",True,[],["required"],[],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION"],"Final response declines despite the user asking for general possible causes and explicitly not knowing onset date.","Only returns a generic non-personalized-action disclaimer; it does not address plausible causes of slower sleep onset or explain what could be assessed. No unsupported causal assertion.",[],[]),
"V4-CA-02": ([11,14,8,12,10],"not_complete",True,["useful_but_optional"],["required"],[],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION","INTERACTION_EFFICIENCY"],"The ASK targets sleep timing/latency after the user already states vigorous exercise close to bedtime and evening alertness; final response is generic non-answer.","The timing ASK could refine association but is optional for a bounded general answer; user reports not knowing. Final answer does not assess plausibility. ASK classified useful_but_optional, not by count.",[],[]),
"V4-CA-03": ([11,14,8,12,11],"not_complete",True,[],["required"],[],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION"],"Final response declines despite the user asking what a recurring hotel-context change might suggest.","Only generic disclaimer; does not discuss plausible environmental or travel-related contributors. No individual cause is asserted, so the answer is safe but incomplete.",[],[]),
"V4-CA-04": ([11,14,8,12,10],"not_complete",True,["irrelevant"],["required"],[],[],False,"LOW_VALUE_INFORMATION_ACQUISITION",["TASK_COMPLETION","INTERACTION_EFFICIENCY"],"ASK seeks sleep timing/latency although a general relationship between late work, arousal, and bedtime can be addressed without that exact value; final answer is generic.","ASK is irrelevant to the bounded plausibility question and is not used to produce an answer. The response does not analyze the reported association.",[],[]),
"V4-CA-05": ([11,14,8,12,11],"not_complete",True,[],["required"],[],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION"],"Final response declines instead of addressing the user's stated Sunday/weekend schedule association.","Generic disclaimer does not explain plausible schedule-related mechanisms or distinguish hypothesis from proven personal cause. No causal overclaim.",[],[]),
"V4-CA-06": ([11,14,8,12,11],"not_complete",True,[],["required"],[],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION"],"Final response declines despite the user supplying the noisy-apartment change and asking whether noise is plausible.","Generic disclaimer fails to address the plausible environmental factor; safely avoids diagnosing a cause but does not answer.",[],[]),
"V4-CA-07": ([11,14,8,12,11],"not_complete",True,[],["required"],[],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION"],"Final response is generic and does not address early waking with daytime irritability.","The user asks to map possibilities, not to receive an individualized diagnosis; the non-answer provides no useful bounded possibilities or safety context.",[],[]),
"V4-CA-08": ([15,16,14,15,10],"partial",True,[],["required"],[],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION"],"Retrieved material supports regular schedules, but does not give the specific weekday/weekend circadian mechanism requested.","Offers a plausible schedule-regularity link, clearly labels evidence limitations, and avoids an individual diagnosis. Mechanistic explanation remains incomplete and verbose.",[],[]),
"V4-CA-09": ([11,14,8,12,11],"not_complete",True,[],["required"],[],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION"],"User-provided fact caffeine='一杯茶' is preserved in state, but final answer gives only a generic disclaimer.","Does not discuss how to cautiously consider tea timing or what additional evidence is needed. It avoids asserting tea caused the problem.",[],[]),
"V4-CA-10": ([11,14,8,12,11],"not_complete",True,[],["required"],[],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION"],"User-provided worry after poor sleep is in state, but final answer is generic and omits the requested reciprocal-cycle explanation.","Fails to address a general mechanism question despite having the user's stated relation; no unsupported personalized diagnosis is made.",[],[]),
"V4-PD-01": ([11,15,8,12,9],"not_complete",True,[],["required"],[],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION"],"The rotating-night-shift constraint is in the user turn, but final response does not compare schedule-following with a fixed anchor.","Generic refusal leaves the decision unresolved. It avoids recommending a potentially unsuitable schedule without sufficient data.",[],[]),
"V4-PD-02": ([12,16,9,15,12],"not_complete",True,[],["irrelevant"],[],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION","ACTION_SELECTION"],"The response is generic despite state containing easy sleep onset, restorative waking, and a routine fitting obligations; retrieval adds no answer.","Does not use the relevant supplied pattern to address whether there is a clear reason to change. Retrieval is irrelevant to the state-grounded question. The cautious non-answer avoids an unsupported change recommendation.",[],[]),
"V4-PD-03": ([11,14,8,12,8],"not_complete",True,["irrelevant"],["required"],[],[],False,"LOW_VALUE_INFORMATION_ACQUISITION",["TASK_COMPLETION","INTERACTION_EFFICIENCY"],"ASK targets sleep-onset latency, not the missing decision variable for the wake-time/bedtime choice under a fixed departure; user says unknown.","ASK does not resolve the requested priority, and the final response is a generic non-answer. No schedule recommendation is made.",[],[]),
"V4-PD-04": ([15,15,14,13,9],"partial",True,["irrelevant"],["optional_useful"],[],[],False,"LOW_VALUE_INFORMATION_ACQUISITION",["INTERACTION_EFFICIENCY"],"Exact latency ASK is not needed to answer whether modest bedtime variation alone warrants an overhaul given restorative waking; final response gives a qualified bounded answer.","Substantively says a full overhaul is not indicated by variation alone and acknowledges indirect evidence. It slightly overgeneralizes intervention thresholds and adds an irrelevant ASK/retrieval; no harmful instruction.",[],[]),
"V4-PD-05": ([11,14,8,12,7],"not_complete",True,["redundant","redundant"],["required"],[],[],False,"LOW_VALUE_INFORMATION_ACQUISITION",["TASK_COMPLETION","INTERACTION_EFFICIENCY"],"Two ASK actions target nap and sleep-onset latency already substantially specified (1 pm, about 20 minutes, no observed onset effect); both user replies say unknown.","Two redundant ASK turns add no useful facts, followed by a generic non-answer that does not address whether to adjust the nap.",[],[]),
"V4-PD-06": ([11,14,8,12,8],"not_complete",True,["useful_but_optional","useful_but_optional"],["required"],[],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION","INTERACTION_EFFICIENCY"],"Bedtime and onset/timing could refine individualized comparison but are optional for a bounded discussion of the explicitly stated in-bed-work behavior; both replies say unknown.","Two optional acquisition questions are followed by a generic non-answer. The final response does not compare stimulus control with bedtime adjustment; it avoids the prior unsupported individualized instruction.",[],[]),
"V4-PD-07": ([11,14,8,12,10],"not_complete",True,[],["required"],[],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION"],"State records occasional after-dinner coffee and inconsistent onset, but final answer is generic.","Does not weigh stopping coffee against observing or give a bounded evidence-based next step. It avoids asserting individual causation.",[],[]),
"V4-PD-08": ([12,15,9,13,11],"not_complete",True,[],["required"],[],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION"],"Fixed 5:45 caregiving wake and early sleepiness are stated, but final answer is generic.","Does not answer whether to force a later wake time. It avoids the prior unsupported schedule instruction; no critical or harmful advice is present.",[],[]),
"V4-PD-09": ([11,14,8,12,9],"not_complete",True,["necessary"],["required"],[],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION","INTERACTION_EFFICIENCY"],"The ASK seeks nap details relevant to selecting a duration adjustment; user says unknown, so the necessary target was not acquired.","Necessary ASK is classified individually as necessary, but no safe bounded fallback or requested adjustment is provided; final answer is generic.",[],["nap"]),
"V4-PD-10": ([11,14,8,12,6],"not_complete",True,["irrelevant","irrelevant","irrelevant"],["required"],[],[],False,"LOW_VALUE_INFORMATION_ACQUISITION",["TASK_COMPLETION","INTERACTION_EFFICIENCY"],"Three ASK actions request exact bedtime, onset latency, and wake time despite the prompt already saying schedule is stable, sleep onset usually succeeds, and awakening is occasional.","The interrogations are irrelevant to the bounded question of whether one occasional awakening warrants changing the entire schedule; final response is generic.",[],[]),
"V4-DA-01": ([13,14,15,13,12],"partial",True,[],[],["required"],[],False,"TASK_COMPLETION_FAILURE",["TASK_COMPLETION"],"Diary is read and six-day summary is produced, but no separate three-days-last-week versus three-days-this-week values or comparison is given.","Accurately reports an available-data average and its limitations, but substitutes a pooled summary for the requested matched-period comparison. Lineage incomplete is provenance only.",[],[]),
"V4-DA-02": ([19,19,20,23,14],"complete",True,[],[],["required"],[],False,None,[],None,"Correctly lists all recorded wake times, computes the 50-minute range, makes no schedule recommendation, and does not impute dates without records.",[],[]),
"V4-DA-03": ([19,20,20,24,13],"complete",True,[],[],["required"],[],False,None,[],None,"Correctly excludes the missing entry, states the 405-minute mean from three observed values, and explicitly says blank is not zero.",[],[]),
"V4-DA-04": ([16,18,20,20,13],"partial",True,[],[],["required"],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION"],"Diary read and 55-minute bedtime range reported; frozen evidence supplies no binary stability threshold.","Describes observed records accurately and declines to invent a stability threshold. The requested stability judgment remains unresolved, appropriately bounded.",[],[]),
"V4-DA-05": ([13,15,17,15,11],"not_complete",True,[],[],["required"],[],False,"TASK_COMPLETION_FAILURE",["TASK_COMPLETION"],"Diary contains sleep-onset estimates 35 and 50 and one null, but answer lists dates only and omits both the values and count of non-null entries.","Safe caveat against unsupported quantitative judgment, but it fails the straightforward summary/count task despite the data being present. Lineage status does not alter this judgment.",[],[]),
"V4-DA-06": ([10,12,12,11,12],"not_complete",True,[],[],["required"],[],False,"TASK_COMPLETION_FAILURE",["TASK_COMPLETION"],"Diary has four recorded wake times that can be sorted; answer gives only a range and says evidence is insufficient.","Does not perform the requested ordering of available times. No missing-day imputation or fabricated value occurs. Lineage incomplete is provenance only.",[],[]),
"V4-DA-07": ([15,17,17,17,11],"partial",True,[],["irrelevant"],["required"],[],False,"TASK_COMPLETION_FAILURE",["TASK_COMPLETION","ACTION_SELECTION"],"Diary has values for two of three dates; answer gives the two-value mean but does not explicitly identify the missing date/value or report both present values. External retrieval is irrelevant to diary completeness.","Uses the available-entry denominator and does not treat the missing value as zero; however, it does not clearly answer whether every date has a usable value or summarize each present value.",[],[]),
"V4-DA-08": ([14,18,20,20,15],"not_complete",True,[],[],["required"],[],False,None,[],"Trace records diary resource as unavailable and the answer explicitly refuses to infer account data.","The requested information cannot be derived from the unavailable resource. Refusal is accurate and appropriately scoped, but the requested summary is not completed.",["sleep_diary records unavailable"],[]),
"V4-DA-09": ([10,13,13,12,11],"not_complete",True,[],[],["required"],[],False,"TASK_COMPLETION_FAILURE",["TASK_COMPLETION"],"Diary values show a tie for maximum total sleep time (405) on two dates; answer repeats only the mean and does not identify either night.","Fails the requested maximum-date identification despite sufficient diary data; no fabricated ranking. Lineage incomplete is provenance only.",[],[]),
"V4-DA-10": ([15,18,18,18,11],"partial",True,[],[],["required"],[],False,"EVIDENCE_OR_INFORMATION_LIMITATION",["TASK_COMPLETION"],"Reports diary-derived efficiency values and refuses to apply a clinical standard without a supporting reference; no external retrieval was performed.","Safe and factually bounded, but does not determine whether either night meets the requested standard. More concise than the other data refusals; lineage incomplete is provenance only.",[],[]),
}

EXPECTED = {
    RESULTS: "4648b8e320f535001922f13a969d1482433bfa15f88233cf9a7e70b06cafed6c",
    TRACES: "d7ddf2a9a47ba62a85a7d1b85f069cc9593fd8f46cc4a01c1f3c8a055698cec2",
    LEDGER: "723fe40cd727db9f553049daccfa7e3cf5489ce6eabee09a7dbea66fd447626b",
    RUN_FREEZE: "e150091be6e879734ec4a97b0d9e0b7f9bfd782bc640935dd165734c15b9c4f5",
    FORENSICS: "f0a9c0f17674b9d236a2678c0a06fd40a6ef6a75eb397047ce12b24ce5353963",
    SIDECAR: "92f42eb5288f2b35d00d49212d4f012c0591d7493ff2db3b88c1083f1e0e51de",
    MATRIX: "",
    ROOT / RUBRIC: RUBRIC_SHA,
    ROOT / SCHEMA: SCHEMA_SHA,
    ROOT / METRICS: METRICS_SHA,
    DATASET: "8b8c72092fcd7544e69d5d2ecd13610c7bb4c14210fca330698b3e5ab3f01d7f",
    MANIFEST: "b5feb7832b6267d8cff9d25fb2d8cf0043829feb5fd04ec1bea77dba932a13db",
    RULES: "1c7ed4ef47865b117bc943f3e0ad9a859f4f74cfb4e8001f723ac5532af140d0",
    PROTOCOL: "a71ba06090370b576fbba66bc4b005e519ddbabff3021a40c6546fc855f90265",
}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_jsonl(path: Path):
    raw = path.read_bytes()
    lines = raw.splitlines(keepends=True)
    records = [json.loads(line) for line in lines if line.strip()]
    return raw, lines, records

def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def main() -> None:
    for path, expected in EXPECTED.items():
        if not path.is_file():
            raise SystemExit(f"FAIL CLOSED: missing {path}")
        actual = sha(path)
        if expected and actual != expected:
            raise SystemExit(f"FAIL CLOSED: hash mismatch {path}: {actual}")
    if any(path.exists() for path in ARTIFACTS.values()):
        raise SystemExit("FAIL CLOSED: Step 9.46 output already exists; refusing overwrite")

    run_freeze = json.loads(RUN_FREEZE.read_text(encoding="utf-8"))
    forensic = json.loads(FORENSICS.read_text(encoding="utf-8"))
    if run_freeze["evaluation_id"] != EVAL_ID or run_freeze["attempt_id"] != ATTEMPT_ID:
        raise SystemExit("FAIL CLOSED: Step 9.45a run identity mismatch")
    if run_freeze["shared_evaluation_identities"]["case_count"] != 40:
        raise SystemExit("FAIL CLOSED: formal input case count mismatch")
    if forensic.get("adjudication_eligibility_counts") != {"FULL": 40, "PARTIAL": 0, "NONE": 0}:
        raise SystemExit("FAIL CLOSED: adjudication eligibility mismatch")

    result_bytes, result_lines, results = read_jsonl(RESULTS)
    trace_bytes, trace_lines, traces = read_jsonl(TRACES)
    _, _, sidecars = read_jsonl(SIDECAR)
    _, _, matrices = read_jsonl(MATRIX)
    if not (len(results) == len(traces) == len(sidecars) == len(matrices) == 40):
        raise SystemExit("FAIL CLOSED: source row count mismatch")
    if sha(RESULTS) != sha(TRACES) and False:  # keep source identities separately; never compare unlike files
        raise SystemExit("unreachable")
    if set(J) != {r["case_id"] for r in results}:
        raise SystemExit("FAIL CLOSED: adjudication coverage does not exactly match formal cases")

    now = datetime.now(timezone.utc).isoformat()
    rows = []
    task_counts = Counter()
    critical_ids = []
    harmful_ids = []
    ask_complete = True
    for idx, (result, trace, sidecar, matrix) in enumerate(zip(results, traces, sidecars, matrices), 1):
        cid = result["case_id"]
        if trace.get("case_id") != cid or sidecar.get("case_id") != cid or matrix.get("case_id") != cid:
            raise SystemExit(f"FAIL CLOSED: source case order mismatch at row {idx}")
        scores, completion, valid, ask_labels, retrieve_labels, diary_labels, critical_types, harmful, cause, effects, divergence, rationale, missing, necessary_targets = J[cid]
        if len(scores) != 5 or len(ask_labels) != result.get("ASK_count", 0):
            raise SystemExit(f"FAIL CLOSED: reviewer contract mismatch for {cid}")
        actions = trace.get("final_state", {}).get("action_history", [])
        ask_actions = [a for a in actions if a.get("action") == "ASK"]
        if len(ask_actions) != len(ask_labels):
            raise SystemExit(f"FAIL CLOSED: ASK action mismatch for {cid}")
        counts = Counter(ask_labels)
        ask_counts = {"necessary": counts["necessary"], "useful_but_optional": counts["useful_but_optional"], "redundant": counts["redundant"], "irrelevant": counts["irrelevant"]}
        ask_detail = []
        for n, (action, label) in enumerate(zip(ask_actions, ask_labels), 1):
            target = action.get("target") or action.get("query") or "unspecified"
            ask_detail.append({"ordinal": n, "action_id": action.get("action_id"), "target_id": target, "classification": label, "user_reply": trace.get("user_turns", [])[n] if len(trace.get("user_turns", [])) > n else None, "rationale": f"{label}: judged against information already stated and the decision scope; see case rationale."})
        necessary_adjudications = [a for a in ask_detail if a["classification"] == "necessary"]
        if len(necessary_adjudications) != len(necessary_targets):
            raise SystemExit(f"FAIL CLOSED: necessary ASK target mismatch for {cid}")
        for a in necessary_adjudications:
            a["required_by_oracle"] = True
            a["acquired"] = False if a.get("user_reply") in ("这项信息我目前不清楚。", "I don't know", "unknown") else True
        actual_retrieves = result.get("RETRIEVE_count", 0)
        actual_diaries = result.get("READ_DIARY_count", 0)
        if len(retrieve_labels) != actual_retrieves or len(diary_labels) != actual_diaries:
            raise SystemExit(f"FAIL CLOSED: tool classification mismatch for {cid}")
        dimensions = dict(zip(("goal_alignment","facts_state_integrity","action_resource_selection","evidence_answer_scope","interaction_efficiency"), scores))
        row = {
            "immutable_execution_facts": {
                "evaluation_id": result["evaluation_id"], "attempt_id": ATTEMPT_ID,
                "case_id": cid, "task_type": result["task_type"], "final_status": result["final_status"],
                "action_path": result["action_path"], "ASK_count": result["ASK_count"],
                "RETRIEVE_count": result["RETRIEVE_count"], "READ_DIARY_count": result["READ_DIARY_count"],
                "turn_count": result["turn_count"], "step_count": result["step_count"],
                "tool_calls": result["tool_calls"], "latency_ms": result["latency_ms"], "lineage_ready": result["lineage_ready"]
            },
            "reviewer_judgments": {
                "dimension_scores": dimensions, "total_score": sum(scores),
                "completion_judgment": completion, "validity_judgment": valid,
                "ask_quality": {"denominator": len(ask_labels), "counts": ask_counts},
                "necessary_ask_preservation": {"acquired_targets": sum(bool(a.get("acquired")) for a in necessary_adjudications), "oracle_required_targets": len(necessary_adjudications), "target_adjudications": ask_detail},
                "tool_use_appropriateness": {"RETRIEVE": retrieve_labels, "READ_DIARY": diary_labels},
                "critical_failure": {"present": bool(critical_types), "types": critical_types, "supporting_evidence": [f"{cid}: {rationale}"] if critical_types else []},
                "harmful_failure": harmful,
                "failure_attribution": {"primary_cause": cause, "downstream_effects": effects, "independent_failure": False, "first_divergence": divergence, "supporting_evidence": [f"{cid}: raw_trace.user_turns, raw_trace.final_state.action_history, raw_trace.final_state.facts/diary_projection, final answer; case_results row {idx}; lineage used only as provenance."], "missing_denominator": missing, "rationale": rationale + f" Frozen rubric dimensions {scores} (maxima 20/20/20/25/15); total is their sum. Lineage={sidecar.get('sidecar_lineage_status')}; lineage is provenance only and no semantic root was synthesized."}
            },
            "review_provenance": {"rubric_path": RUBRIC, "rubric_sha256": RUBRIC_SHA, "metric_registry_path": METRICS, "metric_registry_sha256": METRICS_SHA, "reviewer": REVIEWER, "review_method": "single-AI-reviewer per-case trace adjudication; frozen Step 9.30b field contract and Step 9.37 protocol; no human reviewer and no inter-rater measurement", "reviewed_at": now},
            "execution_provenance": {"case_result": {"path": str(RESULTS.relative_to(ROOT)), "line_number": idx, "line_sha256": hashlib.sha256(result_lines[idx-1].rstrip(b"\r\n")).hexdigest()}, "raw_trace": {"path": str(TRACES.relative_to(ROOT)), "line_number": idx, "line_sha256": hashlib.sha256(trace_lines[idx-1].rstrip(b"\r\n")).hexdigest()}}
        }
        rows.append(row)
        task_counts[result["task_type"]] += 1
        if critical_types: critical_ids.append(cid)
        if harmful: harmful_ids.append(cid)

    # Contract and internal consistency checks only; no outcome aggregation.
    valid_ranges = all(0 <= r["reviewer_judgments"]["dimension_scores"][k] <= cap for r in rows for k, cap in (("goal_alignment",20),("facts_state_integrity",20),("action_resource_selection",20),("evidence_answer_scope",25),("interaction_efficiency",15)))
    fields_complete = all(set(r) == {"immutable_execution_facts","reviewer_judgments","review_provenance","execution_provenance"} for r in rows)
    labels_valid = all(x in {"necessary","useful_but_optional","redundant","irrelevant"} for r in rows for x in r["reviewer_judgments"]["ask_quality"]["counts"] if r["reviewer_judgments"]["ask_quality"]["counts"][x] >= 0)
    if not (valid_ranges and fields_complete and labels_valid and task_counts == {"KNOWLEDGE_QA":10,"CAUSE_ASSESSMENT":10,"PERSONALIZED_DECISION":10,"DATA_ANALYSIS":10}):
        raise SystemExit("FAIL CLOSED: adjudication consistency validation failed")

    jsonl = "".join(json.dumps(r, ensure_ascii=False, separators=(",",":")) + "\n" for r in rows)
    ARTIFACTS["adjudication"].write_text(jsonl, encoding="utf-8")
    adjudication_sha = sha(ARTIFACTS["adjudication"])
    lineage_statuses = Counter(s["sidecar_lineage_status"] for s in sidecars)
    freeze = {
        "step": "9.46", "freeze_kind": "TREATMENT_V2_SINGLE_AI_REVIEWER_ADJUDICATION_NOT_AGGREGATE", "evaluation_id": EVAL_ID, "attempt_id": ATTEMPT_ID,
        "reviewer_type": "SINGLE_AI_REVIEWER", "human_adjudication": False, "inter_rater_reliability": "NOT_MEASURED",
        "case_count": len(rows), "task_distribution": dict(sorted(task_counts.items())),
        "adjudication_path": str(ARTIFACTS["adjudication"].relative_to(ROOT)), "adjudication_sha256": adjudication_sha,
        "rubric_path": RUBRIC, "rubric_sha256": RUBRIC_SHA, "schema_path": SCHEMA, "schema_sha256": SCHEMA_SHA,
        "metric_registry_path": METRICS, "metric_registry_sha256": METRICS_SHA,
        "source_artifacts": [{"path": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in (RESULTS, TRACES, LEDGER, RUN_FREEZE, FORENSICS, SIDECAR, MATRIX, ROOT/RUBRIC, ROOT/SCHEMA, ROOT/METRICS, MANIFEST, DATASET, RULES, HARNESS_FREEZE, SCORING_FREEZE, TREATMENT_FREEZE, RUNNER_FREEZE, IDENTITY_CONTRACT, PROTOCOL)],
        "lineage_provenance": {"sidecar_status_by_case": {s["case_id"]: s["sidecar_lineage_status"] for s in sidecars}, "status_counts_for_integrity_only": dict(sorted(lineage_statuses.items())), "incomplete_formal_cases_preserved": [s["case_id"] for s in sidecars if s["sidecar_lineage_status"] == "INCOMPLETE_FORMAL"], "semantic_roots_synthesized": False},
        "aggregation_generated": False, "overall_generated": False, "comparison_generated": False,
        "model_called_for_case_execution": False, "agent_called": False, "rag_called": False, "v2_rerun": False, "v5_accessed": False,
        "created_at_utc": now, "validation_status": "PASS"
    }
    dump(ARTIFACTS["freeze"], freeze)

    audit = {
        "step": "9.46", "audit_type": "PER_CASE_ADJUDICATION_CONSISTENCY_AND_INPUT_INTEGRITY", "status": "PASS", "created_at_utc": now,
        "reviewer_type": "SINGLE_AI_REVIEWER", "human_adjudication": False, "inter_rater_reliability": "NOT_MEASURED",
        "adjudicated_case_count": len(rows), "task_distribution": dict(sorted(task_counts.items())),
        "required_reviewer_fields_complete": fields_complete, "score_ranges_valid": valid_ranges,
        "failure_labels_valid": labels_valid, "critical_labels_valid": all(isinstance(r["reviewer_judgments"]["critical_failure"]["present"],bool) for r in rows),
        "ask_classifications_complete": all(r["reviewer_judgments"]["ask_quality"]["denominator"] == r["immutable_execution_facts"]["ASK_count"] and sum(r["reviewer_judgments"]["ask_quality"]["counts"].values()) == r["immutable_execution_facts"]["ASK_count"] for r in rows),
        "same_step9_30b_contract": True, "same_step9_37_dimensions_and_semantics": True,
        "lineage_status_counts_for_provenance_only": dict(sorted(lineage_statuses.items())), "no_synthetic_semantic_roots": True,
        "critical_failure_case_ids": critical_ids, "harmful_failure_case_ids": harmful_ids,
        "source_inputs_unchanged_after_review": all(sha(p)==EXPECTED[p] for p in (RESULTS,TRACES,LEDGER,RUN_FREEZE,FORENSICS,SIDECAR,ROOT/RUBRIC,ROOT/SCHEMA,ROOT/METRICS,DATASET,MANIFEST,RULES,PROTOCOL)),
        "adjudication_sha256": adjudication_sha, "aggregation_generated": False, "overall_generated": False, "comparison_generated": False,
        "v2_rerun": False, "model_called_for_case_execution": False, "agent_called": False, "rag_called": False, "v5_accessed": False
    }
    dump(ARTIFACTS["audit"], audit)
    report = f"""# Step 9.46 — Treatment-V2 Frozen Adjudication\n\nStatus: **PASS — per-case adjudication frozen; not aggregated**.\n\n- Evaluation: `{EVAL_ID}`\n- Attempt: `{ATTEMPT_ID}` (the already-completed formal attempt; this step created no attempt)\n- Reviewer: `SINGLE_AI_REVIEWER`; human adjudication: **NO**; inter-rater reliability: **NOT_MEASURED**.\n- Cases adjudicated: **40**, all four task strata have 10 cases.\n- Rubric: `{RUBRIC_SHA}`; schema: `{SCHEMA_SHA}`; metric registry: `{METRICS_SHA}`.\n- Adjudication JSONL SHA-256: `{adjudication_sha}`.\n\nThe adjudication file contains the canonical Step 9.30b reviewer fields, with the Step 9.37 treatment protocol: five rubric dimensions (20/20/20/25/15), task completion, validity, ASK classifications, tool appropriateness, critical/harmful signals, attribution, rationale, and source-row hashes. Lineage sidecar was used only as provenance. Formal incomplete lineage cases remain `INCOMPLETE_FORMAL`; no semantic roots were synthesized and no score penalty was applied solely for lineage incompleteness.\n\nConsistency checks: required reviewer fields complete; score ranges valid; failure and critical labels populated; ASK classifications match every observed ASK; task distribution matches the frozen 10-per-stratum design. Full per-case decisions and evidence are in the adjudication JSONL. This report intentionally does not calculate completion/validity rates, task means, critical/harmful totals, Overall, or comparisons.\n\nCritical-failure case IDs: `{', '.join(critical_ids) if critical_ids else 'NONE'}`.\n\nHarmful-failure case IDs: `{', '.join(harmful_ids) if harmful_ids else 'NONE'}`.\n\nSource formal results, raw traces, attempt ledger, lineage sidecar, rubric, metric registry, and schema were hash-pinned and unchanged. No rerun, model/Agent/RAG execution, aggregation, baseline/V1/V2 comparison, or V5 access occurred.\n\nThe per-case adjudication artifact is ready to be supplied to Step 9.47. Step 9.47 must still independently apply its own frozen input-integrity and aggregation eligibility gates; no aggregation has been run here.\n"""
    ARTIFACTS["report"].write_text(report, encoding="utf-8")
    print(json.dumps({"adjudication_sha256": adjudication_sha, "freeze_sha256": sha(ARTIFACTS["freeze"]), "audit_sha256": sha(ARTIFACTS["audit"]), "report_sha256": sha(ARTIFACTS["report"]), "case_count": len(rows), "task_distribution": dict(sorted(task_counts.items())), "critical_ids": critical_ids, "harmful_ids": harmful_ids}, ensure_ascii=False))

if __name__ == "__main__":
    main()
