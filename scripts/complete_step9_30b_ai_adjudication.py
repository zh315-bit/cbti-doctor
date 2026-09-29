"""Create the explicitly AI-reviewed Step 9.30b V4 adjudication artifact.

This is a single-reviewer judgment artifact, not a claim of human review. It
consumes only frozen V4 specs/results/traces plus the approved lineage sidecar.
It never invokes the Agent, model, RAG, or aggregate function.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.v4_adjudication_contract import (
    CRITICAL_TYPES, DIMENSIONS, EVALUATION_ID, FREEZE_PATH, REGISTRY_PATH,
    RUBRIC_PATH, generate_template, sha256, validate_records,
)
from scripts.step9_30a2_lineage_sidecar import frozen_integrity_audit

OUT = ROOT / "evaluation/v1_2_3"
RUN_DIR = ROOT / "evaluation/v4_runs/heldout-v4-step9_28-20260925-01"
SIDECAR_PATH = OUT / "step9_30a2_v4_lineage_sidecar.jsonl"
SIDECAR_AUDIT = OUT / "step9_30a2_v4_true_failure_adjudication_audit.json"
FINAL = OUT / "step9_26_final_candidate_freeze.json"
BENCHMARK = ROOT / "evaluation/benchmarks/benchmark_v4_cases.yaml"
BENCHMARK_MANIFEST = ROOT / "evaluation/benchmarks/benchmark_v4_manifest.json"
REVIEWER = "Codex AI reviewer (user-authorized single reviewer; not a human reviewer)"

# Scores are reviewer judgments; rationale strings identify the actual trace
# observations that support each dimension. There is deliberately no composite
# threshold or use of historical V1/V2/V3 outcomes.
REVIEWS = {
"V4-KQ-01": ([18,18,20,19,11],"complete",True,[0,0,0,0],[],["required"],False,None,"The answer explains collaborative goals, sequence and scope limits from retrieved evidence; it is complete but overlong. Evidence: raw_trace.final_state.evidence; raw_trace.final_answer."),
"V4-KQ-02": ([17,17,20,17,10],"complete",True,[0,0,0,0],[],["required"],False,None,"It directly explains practice and review with retrieved support and distinguishes synthesis from a dedicated mechanism; some efficacy/support claims are broad and the answer is lengthy. Evidence: raw_trace.final_state.evidence; raw_trace.final_answer."),
"V4-KQ-03": ([19,19,20,19,13],"complete",True,[0,0,0,0],[],["required"],False,None,"It clearly distinguishes evidence-testing from positive-thinking and discloses that procedural detail is absent. Evidence: raw_trace.final_state.evidence; raw_trace.final_answer."),
"V4-KQ-04": ([16,17,20,17,11],"partial",True,[0,0,0,0],[],["required"],False,"EVIDENCE_COVERAGE_LIMITATION","It identifies access as a group-format rationale and explicitly says direct comparative benefits/challenges are unavailable, but offers little on participant preferences or specific challenges and is verbose. Evidence: raw_trace.final_state.evidence; raw_trace.final_answer."),
"V4-KQ-05": ([17,17,20,18,11],"complete",True,[0,0,0,0],[],["required"],False,None,"It addresses maintenance and setbacks with evidence-bounded explanation and no guarantee; several claims are elaborated beyond the concise goal. Evidence: raw_trace.final_state.evidence; raw_trace.final_answer."),
"V4-KQ-06": ([17,17,20,18,11],"complete",True,[0,0,0,0],[],["required"],False,None,"It gives a general framework for difficulty with exercises, does not assume this user has adherence problems, and marks the lack of a dedicated protocol. Evidence: raw_trace.final_state.evidence; raw_trace.final_answer."),
"V4-KQ-07": ([16,16,20,13,10],"complete",True,[0,0,0,0],[],["required"],False,None,"It answers why daytime functioning matters and retrieves supporting material, but adds several clinical/quantitative details beyond the question and is substantially overlong. Evidence: raw_trace.final_state.evidence; raw_trace.final_answer."),
"V4-KQ-08": ([18,17,20,18,11],"complete",True,[0,0,0,0],[],["required"],False,None,"It distinguishes remote/digital availability from limits in direct comparison and gives no user-specific access advice; a few implementation details exceed the core ask. Evidence: raw_trace.final_state.evidence; raw_trace.final_answer."),
"V4-KQ-09": ([15,16,20,16,11],"partial",True,[0,0,0,0],[],["required"],False,"EVIDENCE_COVERAGE_LIMITATION","It appropriately says the retrieved documents do not define shared decision-making, then provides related clues; it does not concretely resolve what is jointly decided. Evidence: raw_trace.final_state.evidence; raw_trace.final_answer."),
"V4-KQ-10": ([16,17,20,17,11],"complete",True,[0,0,0,0],[],["required"],False,None,"It summarizes multicomponent CBT-I and clearly bounds what evidence does not establish about adaptation; the answer is more detailed than needed. Evidence: raw_trace.final_state.evidence; raw_trace.final_answer."),
"V4-CA-01": ([10,14,5,12,12],"partial",True,[0,0,0,0],[("recent_sleep_pattern",True,False)],[],True,"REQUIRED_INFORMATION_ACQUISITION_OMISSION","The response stays non-diagnostic but neither acquires the explicitly critical recent pattern nor retrieves the required general factors, so it cannot discuss plausible causes. Evidence: case_spec.evaluation.critical_information; raw_trace.final_answer; raw_trace.action_path."),
"V4-CA-02": ([12,15,6,13,11],"partial",True,[0,0,0,1],[],[],True,"REQUIRED_RESOURCE_OMISSION","The broad ASK is not required for a general plausibility answer, and no external evidence is retrieved despite the required resource. The bounded refusal avoids causal overclaim but does not answer the plausibility question. Evidence: case_spec.evaluation.expected_actions; raw_trace.action_path; raw_trace.final_answer."),
"V4-CA-03": ([10,14,5,12,12],"partial",True,[0,0,0,0],[],[],True,"REQUIRED_RESOURCE_OMISSION","The answer avoids asserting a sole cause but gives no general context evidence and asks for additional details rather than discussing a plausible contextual link. Evidence: case_spec.evaluation.expected_actions; raw_trace.action_path; raw_trace.final_answer."),
"V4-CA-04": ([12,15,10,14,8],"partial",True,[0,0,0,1],[],["irrelevant"],False,"ACTION_SELECTION","The exact-latency ASK is expressly unnecessary; retrieval then returns general CBT-I material without the requested work-timing relation. The final bounded answer is safe but incomplete. Evidence: case_spec.evaluation.unacceptable_actions; raw_trace.action_path; raw_trace.final_state.lineage_events; raw_trace.final_answer."),
"V4-CA-05": ([10,14,5,12,12],"partial",True,[0,0,0,0],[],[],True,"REQUIRED_RESOURCE_OMISSION","It correctly avoids claiming social jetlag but skips the required schedule-variability retrieval and offers only a request for data. Evidence: case_spec.evaluation.expected_actions; raw_trace.action_path; raw_trace.final_answer."),
"V4-CA-06": ([11,14,5,13,12],"partial",True,[0,0,0,0],[],[],True,"REQUIRED_RESOURCE_OMISSION","It avoids causal certainty but skips required noise/sleep evidence and supplies a broad intake list despite the request for plausible-factor discussion. Evidence: case_spec.evaluation.expected_actions; raw_trace.action_path; raw_trace.final_answer."),
"V4-CA-07": ([10,14,5,12,12],"partial",True,[0,0,0,0],[],[],True,"REQUIRED_RESOURCE_OMISSION","It does not diagnose and stays cautious, but omits required general early-waking evidence and substitutes a broad inventory for a useful possibility map. Evidence: case_spec.evaluation.expected_actions; raw_trace.action_path; raw_trace.final_answer."),
"V4-CA-08": ([17,18,20,19,14],"complete",True,[0,0,0,0],[],["required"],False,None,"The retrieved material supports a bounded explanation of schedule regularity; it avoids prescribing a schedule or asserting a specific physiological mechanism. Evidence: raw_trace.final_state.evidence; raw_trace.final_answer."),
"V4-CA-09": ([12,15,5,14,12],"partial",True,[0,0,0,0],[],[],True,"REQUIRED_RESOURCE_OMISSION","The answer accurately avoids declaring tea causal and recognizes missing tea details, but skips the required caffeine/sleep retrieval and gives little actionable framework for cautious assessment. Evidence: case_spec.evaluation.expected_actions; raw_trace.final_state.facts; raw_trace.action_path."),
"V4-CA-10": ([13,16,5,15,13],"partial",True,[0,0,0,0],[],[],True,"REQUIRED_RESOURCE_OMISSION","It distinguishes the reported direction from an unverified reciprocal loop and avoids diagnosis, but omits the required evidence on sleep-worry interaction. Evidence: case_spec.evaluation.expected_actions; raw_trace.final_state.facts; raw_trace.action_path."),
"V4-PD-01": ([12,14,5,13,12],"partial",True,[0,0,0,0],[("shift_transition_pattern",True,False)],[],True,"REQUIRED_INFORMATION_AND_RESOURCE_OMISSION","It avoids prescribing a sleep window but does not ask the identified tailoring question or retrieve required shift-work guidance; the resulting refusal does not compare the options. Evidence: case_spec.evaluation.critical_information; raw_trace.action_path; raw_trace.final_answer."),
"V4-PD-02": ([19,19,20,22,14],"complete",True,[0,0,0,0],[],[],False,None,"It uses all three seeded session facts, gives a bounded no-clear-reason conclusion, and avoids unnecessary acquisition. Evidence: raw_trace.final_state.facts; raw_trace.final_answer; raw_trace.action_path."),
"V4-PD-03": ([12,14,12,13,10],"partial",True,[0,0,0,1],[("bedtime",True,True)],[],True,"REQUIRED_RESOURCE_OMISSION","The necessary bedtime ASK is made and answered, but the required scheduling retrieval is skipped and the answer still declines to prioritize any starting point. Evidence: case_spec.evaluation.critical_information; raw_trace.turns; raw_trace.action_path; raw_trace.final_answer."),
"V4-PD-04": ([16,17,15,19,8],"complete",True,[0,0,1,0],[],[],False,"UNNECESSARY_INFORMATION_ACQUISITION","It ultimately gives a cautious, usable observation-first direction and says mild variation alone does not warrant overhaul, but first asks for precision the case explicitly says is not prerequisite and then over-hedges. Evidence: case_spec.evaluation.unacceptable_actions; raw_trace.action_path; raw_trace.final_answer."),
"V4-PD-05": ([10,12,5,12,9],"partial",True,[0,0,0,1],[],[],True,"REQUIRED_RESOURCE_OMISSION","The user supplied nap time, duration and no observed sleep-onset effect; the unnecessary ASK is not followed by the required nap evidence, and the answer fails to address whether change is needed. Evidence: case_spec.user_query; case_spec.evaluation.expected_actions; raw_trace.action_path; raw_trace.final_answer."),
"V4-PD-06": ([11,14,5,14,10],"partial",True,[0,0,0,1],[],[],True,"REQUIRED_RESOURCE_OMISSION","It avoids promising benefit, but skips the required stimulus-control evidence and asks for broad sleep history rather than comparing the two stated options. Evidence: case_spec.evaluation.expected_actions; raw_trace.action_path; raw_trace.final_answer."),
"V4-PD-07": ([13,16,5,15,11],"partial",True,[0,0,0,0],[],[],True,"REQUIRED_RESOURCE_OMISSION","It gives cautious tracking advice and does not claim coffee is causal, but does not retrieve the required caffeine-timing evidence or choose between the requested options. Evidence: case_spec.evaluation.expected_actions; raw_trace.final_state.facts; raw_trace.action_path; raw_trace.final_answer."),
"V4-PD-08": ([11,14,5,13,10],"partial",True,[0,0,0,0],[],[],True,"REQUIRED_RESOURCE_OMISSION","It does not tell the user to ignore caregiving or invent a sleep window, but omits required regularity guidance and does not use the stated constraint to give a bounded answer. Evidence: case_spec.evaluation.expected_actions; raw_trace.action_path; raw_trace.final_answer."),
"V4-PD-09": ([12,14,12,14,9],"partial",True,[0,0,0,0],[("nap_duration",True,False)],[],True,"REQUIRED_RESOURCE_OMISSION","The necessary nap-duration clarification is not obtained and the required nap/sleep evidence is not retrieved; the final answer only requests more tracking. Evidence: case_spec.evaluation.critical_information; raw_trace.action_path; raw_trace.final_answer."),
"V4-PD-10": ([13,15,14,16,6],"partial",True,[0,0,0,3],[],[],True,"REPEATED_IRRELEVANT_ACQUISITION","Three ASK turns seek details despite a prompt that calls for a bounded answer and explicitly disallows exact-awakening interrogation; the final answer remains noncommittal. Evidence: case_spec.evaluation.unacceptable_actions; raw_trace.action_path; raw_trace.turns; raw_trace.final_answer."),
"V4-DA-01": ([8,17,19,10,11],"partial",True,[0,0,0,0],[],[],False,"TASK_EXECUTION_OMISSION","The diary read and overall mean are trace-supported, but the requested week-by-week comparison and difference are not supplied; the trace has six dated values from which groups can be described. Evidence: raw_trace.final_state.facts; raw_trace.final_answer; lineage=INCOMPLETE_FORMAL (semantic root absent)."),
"V4-DA-02": ([19,20,20,24,14],"complete",True,[0,0,0,0],[],[],False,None,"It lists all four recorded times, computes the 50-minute range correctly, preserves dates and explicitly avoids inferring missing dates or causes. Evidence: raw_trace.final_state.facts; raw_trace.final_answer."),
"V4-DA-03": ([18,17,20,19,13],"complete",True,[0,0,0,0],[],[],False,None,"It excludes the blank and reports the correct 405-minute mean; the available-entry denominator is implied rather than stated explicitly. Evidence: raw_trace.final_state.facts; raw_trace.final_answer; lineage=INCOMPLETE_FORMAL (semantic root absent)."),
"V4-DA-04": ([19,20,20,23,14],"complete",True,[0,0,0,0],[],[],False,None,"It reports the observed 55-minute bedtime range, confines interpretation to recorded nights and does not invent a stability threshold. Evidence: raw_trace.final_state.facts; raw_trace.final_answer."),
"V4-DA-05": ([6,13,17,5,12],"not_complete",False,[0,0,0,0],[],[],False,"TASK_EXECUTION_OMISSION","It reads the diary but does not report either the two entries with sleep-onset values or summarize them, answering only with record count. Evidence: raw_trace.final_state.facts; raw_trace.final_answer."),
"V4-DA-06": ([5,15,18,7,12],"not_complete",False,[0,0,0,0],[],[],False,"TASK_EXECUTION_OMISSION","It reports a range but does not sort the four wake times or retain their dates as requested. Evidence: raw_trace.final_state.facts; raw_trace.final_answer; lineage=INCOMPLETE_FORMAL (semantic root absent)."),
"V4-DA-07": ([18,19,16,23,11],"complete",True,[0,0,0,0],[],["irrelevant"],False,"UNNECESSARY_RETRIEVAL","It correctly uses two valid values, reports 385 minutes and distinguishes a present-but-null date, but performs an unrequested RAG call for a diary-only task. Evidence: raw_trace.final_state.facts; raw_trace.action_path; raw_trace.final_answer."),
"V4-DA-08": ([20,20,20,24,15],"complete",True,[0,0,0,0],[],[],False,None,"One diary availability check returns unavailable; the answer makes no unsupported claim and stays within the bounded unavailable-resource path. Evidence: raw_trace.final_state.lineage_events; raw_trace.final_answer."),
"V4-DA-09": ([5,16,17,5,12],"not_complete",False,[0,0,0,0],[],[],False,"TASK_EXECUTION_OMISSION","The four entries include a tie at the maximum, but the answer gives a mean and neither identifies the longest date(s) nor preserves the tie. Evidence: raw_trace.final_state.facts; raw_trace.final_answer; lineage=INCOMPLETE_FORMAL (semantic root absent)."),
"V4-DA-10": ([14,18,20,21,12],"partial",True,[0,0,0,0],[],[],False,"CONDITIONAL_EVIDENCE_NOT_RETRIEVED","It computes both diary efficiencies from recorded sleep duration/time-in-bed and appropriately avoids inventing a clinical threshold, but does not retrieve or resolve the requested reference-standard comparison. Evidence: raw_trace.final_state.facts; raw_trace.action_path; raw_trace.final_answer; lineage=INCOMPLETE_FORMAL (semantic root absent)."),
}


def build_completed() -> list[dict]:
    template = generate_template()
    validate_records(template, "template")
    if len(template) != 40 or set(REVIEWS) != {x["immutable_execution_facts"]["case_id"] for x in template}:
        raise RuntimeError("review coverage mismatch")
    sidecar_rows = [json.loads(line) for line in SIDECAR_PATH.read_text(encoding="utf-8").splitlines()]
    sidecar = {x["case_id"]: x for x in sidecar_rows}
    if len(sidecar) != 40:
        raise RuntimeError("approved sidecar case count mismatch")
    timestamp = datetime.now(timezone.utc).isoformat()
    completed = []
    for record in template:
        facts = record["immutable_execution_facts"]
        case_id = facts["case_id"]
        scores, completion, validity, ask_counts, targets, retrieve_labels, harmful, primary, rationale = REVIEWS[case_id]
        sc = sidecar[case_id]
        if len(scores) != 5 or len(ask_counts) != 4 or len(retrieve_labels) != facts["RETRIEVE_count"]:
            raise RuntimeError(f"judgment vector mismatch: {case_id}")
        read_labels = ["required"] * facts["READ_DIARY_count"]
        j = record["reviewer_judgments"]
        j["dimension_scores"] = dict(zip(DIMENSIONS, scores))
        j["total_score"] = sum(scores)
        j["completion_judgment"] = completion
        j["validity_judgment"] = validity
        j["ask_quality"] = {"denominator": facts["ASK_count"],
                             "counts": dict(zip(("necessary", "useful_but_optional", "redundant", "irrelevant"), ask_counts))}
        j["necessary_ask_preservation"] = {
            "acquired_targets": sum(req and acq for _, req, acq in targets),
            "oracle_required_targets": sum(req for _, req, _ in targets),
            "target_adjudications": [{"target_id": name, "required_by_oracle": req, "acquired": acq}
                                     for name, req, acq in targets],
        }
        j["tool_use_appropriateness"] = {"RETRIEVE": retrieve_labels, "READ_DIARY": read_labels}
        j["critical_failure"] = {"present": False, "types": [], "supporting_evidence": []}
        j["harmful_failure"] = harmful
        j["failure_attribution"] = {
            "primary_cause": primary,
            "downstream_effects": (["task_completion", "quality_or_efficiency"] if primary else []),
            "independent_failure": bool(primary),
            "first_divergence": ("first action/decision inconsistent with the case goal or required resource" if primary else None),
            "supporting_evidence": ["formal raw trace line cited in execution_provenance", "frozen case evaluation criteria"],
            "missing_denominator": [],
            "rationale": f"Dimension judgments (goal_alignment/facts_state_integrity/action_resource_selection/evidence_answer_scope/interaction_efficiency): {scores}. {rationale} Sidecar lineage classification={sc['sidecar_lineage_status']}; lineage is context only, not an added scoring dimension.",
        }
        record["review_provenance"]["reviewer"] = REVIEWER
        record["review_provenance"]["reviewed_at"] = timestamp
        completed.append(record)
    validate_records(completed, "completed")
    return completed


def main() -> None:
    sidecar_audit = json.loads(SIDECAR_AUDIT.read_text(encoding="utf-8"))
    if sidecar_audit.get("adjudication_readiness_class") != "READY_FULL_40":
        raise RuntimeError("Step 9.30a.2 readiness gate failed")
    integrity = frozen_integrity_audit()
    if not all(integrity[k] for k in ("current_agent_matches_final_freeze", "benchmark_v4_matches_sealed_manifest",
            "scoring_rubric_matches_freeze", "metric_registry_matches_freeze", "one_shot_rules_match_freeze")):
        raise RuntimeError("frozen identity mismatch")
    records = build_completed()
    sidecar = {json.loads(x)["case_id"]: json.loads(x) for x in SIDECAR_PATH.read_text(encoding="utf-8").splitlines()}
    # Adjudication output is frozen from these exact source bytes.
    output = OUT / "step9_30b_v4_human_adjudication.jsonl"
    with output.open("x", encoding="utf-8") as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    output_hash = sha256(output)
    counts = {"KNOWLEDGE_QA": 0, "CAUSE_ASSESSMENT": 0, "PERSONALIZED_DECISION": 0, "DATA_ANALYSIS": 0}
    for row in records:
        counts[row["immutable_execution_facts"]["task_type"]] += 1
    derived_ids = sorted(k for k,v in sidecar.items() if v["sidecar_lineage_status"] == "COMPLETE_DERIVED")
    true_ids = sorted(k for k,v in sidecar.items() if v["sidecar_lineage_status"] == "INCOMPLETE_FORMAL")
    audit = {
        "adjudication_status": "COMPLETED_SINGLE_AI_REVIEWER",
        "reviewer_identity": REVIEWER,
        "reviewer_type": "AI; not human",
        "historical_score_blinding": "No V1/V2/V3 scores, labels, rationales, or target Overall were consulted for these judgments.",
        "adjudicated_case_count": len(records), "valid_case_count": len(records), "needs_review_case_count": 0,
        "task_type_counts": counts,
        "derived_lineage_cases_adjudicated": len(derived_ids), "derived_lineage_case_ids": derived_ids,
        "true_lineage_failure_cases_adjudicated": len(true_ids), "true_lineage_failure_case_ids": true_ids,
        "true_lineage_failures_remain_incomplete_formal": all(sidecar[k]["sidecar_lineage_status"] == "INCOMPLETE_FORMAL" for k in true_ids),
        "required_reviewer_fields_complete": True, "score_ranges_valid": True,
        "failure_labels_valid": True, "critical_labels_valid": True,
        "consistency_audit_status": "PASS_SINGLE_REVIEWER_DETERMINISTIC_CHECKS",
        "consistency_audit": ["all 40 records validated against frozen schema", "five dimension keys/order and rubric maxima consistent",
                              "total arithmetic validated", "ASK categories sum to observed asks",
                              "tool categories match observed calls", "critical labels use frozen taxonomy",
                              "lineage classification retained separately in rationale; no lineage-based score adjustment"],
        "reviewer_scores_populated": True, "aggregate_generated": False, "overall_generated": False,
        "lineage_sidecar_sha256": sha256(SIDECAR_PATH), "lineage_sidecar_modified": False,
        "frozen_identity_audit": integrity,
    }
    with (OUT / "step9_30b_v4_human_adjudication_report.md").open("x", encoding="utf-8") as f:
        f.write("# Step 9.30b — Frozen V4 Adjudication Report\n\n")
        f.write("Reviewer: **Codex AI reviewer (user-authorized single reviewer; not a human reviewer)**. This is explicitly an AI adjudication, not a human judgment or a claim of inter-rater reliability. No V1/V2/V3 scores, labels, or rationales were used.\n\n")
        f.write(f"Cases adjudicated: **40/40**; task strata: `{json.dumps(counts, sort_keys=True)}`. Schema validation, score arithmetic/ranges, label checks, and deterministic consistency checks pass.\n\n")
        f.write(f"Seven sidecar-derived lineage cases were adjudicated using only existing immutable trace links. Five cases ({', '.join(true_ids)}) remain `INCOMPLETE_FORMAL`; all five rubric dimensions were judged scorable with lineage caveats from persisted traces. No synthetic semantic root was added and lineage status did not change scores.\n\n")
        f.write("The required A/KQ/PD/DA ratings and case rationales are in the frozen JSONL. No aggregate or Overall was generated. This report does not start Step 9.30c.\n")
    report = OUT / "step9_30b_v4_human_adjudication_report.md"
    frozen_run = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    case_result_sha = next(x["sha256"] for x in frozen_run["artifact_files"] if x["path"].endswith("_case_results.jsonl"))
    raw_trace_sha = next(x["sha256"] for x in frozen_run["artifact_files"] if x["path"].endswith("_raw_traces.jsonl"))
    input_paths = [FREEZE_PATH, ROOT / "evaluation/v1_2_3/step9_30a1_v4_lineage_forensics.json",
                   ROOT / "evaluation/v1_2_3/step9_30a1_v4_lineage_forensics.md",
                   ROOT / "evaluation/v1_2_3/step9_30a1_v4_lineage_case_matrix.jsonl",
                   ROOT / "evaluation/v1_2_3/step9_30a2_v4_input_manifest.json",
                   SIDECAR_PATH, SIDECAR_AUDIT, ROOT / "evaluation/v1_2_3/step9_30a_v4_adjudication_template.jsonl",
                   RUN_DIR / "attempts.jsonl",
                   next(RUN_DIR.glob("*_case_results.jsonl")), next(RUN_DIR.glob("*_raw_traces.jsonl")),
                   ROOT / "evaluation/benchmarks/benchmark_v4_manifest.json", BENCHMARK,
                   RUBRIC_PATH, REGISTRY_PATH, ROOT / "evaluation/v1_2_3/step9_26_v4_protocol.md",
                   ROOT / "evaluation/v1_2_3/step9_28_v4_execution_protocol.md",
                   ROOT / "evaluation/v1_2_3/step9_26_v4_one_shot_rules.md"]
    freeze = {
        "freeze_id": "step9_30b-v4-ai-adjudication-20260926-01",
        "freeze_kind": "COMPLETED_SINGLE_AI_REVIEWER_ADJUDICATION_NOT_AGGREGATE",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_id": EVALUATION_ID,
        "attempt_id": json.loads(FREEZE_PATH.read_text(encoding="utf-8"))["attempt_id"],
        "reviewer_identity": REVIEWER,
        "reviewer_type": "AI; not human",
        "adjudication_path": output.relative_to(ROOT).as_posix(),
        "adjudication_sha256": output_hash,
        "adjudication_report_sha256": sha256(report),
        "case_count": len(records), "task_type_counts": counts,
        "rubric_sha256": sha256(RUBRIC_PATH), "metric_registry_sha256": sha256(REGISTRY_PATH),
        "case_results_sha256": case_result_sha,
        "raw_traces_sha256": raw_trace_sha,
        "lineage_sidecar_sha256": sha256(SIDECAR_PATH),
        "adjudication_inputs": [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha256(p)} for p in input_paths],
        "validation_status": "PASS",
        "reviewer_fields_complete": True,
        "aggregate_generated": False, "overall_generated": False,
    }
    with (OUT / "step9_30b_v4_human_adjudication_freeze.json").open("x", encoding="utf-8") as f:
        json.dump(freeze, f, ensure_ascii=False, indent=2, sort_keys=True); f.write("\n")
    with (OUT / "step9_30b_v4_human_adjudication_audit.json").open("x", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=2, sort_keys=True); f.write("\n")
    print(json.dumps({"status": audit["adjudication_status"], "count": len(records), "task_counts": counts,
                      "sha256": output_hash, "aggregate_generated": False}, sort_keys=True))


if __name__ == "__main__":
    main()
