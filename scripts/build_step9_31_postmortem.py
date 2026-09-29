#!/usr/bin/env python3
"""Build the read-only Step 9.31 V4 postmortem from frozen local artifacts."""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation/v1_2_3"
RUN = ROOT / "evaluation/v4_runs/heldout-v4-step9_28-20260925-01"
RESULTS = next(RUN.glob("*_case_results.jsonl"))
TRACES = next(RUN.glob("*_raw_traces.jsonl"))
ADJ = OUT / "step9_30b_v4_human_adjudication.jsonl"
METRICS = OUT / "step9_30c_v4_aggregate_metrics.json"
RUBRIC = ROOT / "evaluation/benchmark_v1_1_scoring.md"
REGISTRY = OUT / "step9_26_v4_metric_registry.json"
SIDECAR = OUT / "step9_30a2_v4_lineage_sidecar.jsonl"
ATTEMPTS = RUN / "attempts.jsonl"
BENCHMARK = ROOT / "evaluation/benchmarks/benchmark_v4_cases.yaml"
MANIFEST = ROOT / "evaluation/benchmarks/benchmark_v4_manifest.json"

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def lines(path: Path):
    for n, raw in enumerate(path.read_bytes().splitlines(keepends=True), 1):
        if raw.strip():
            yield n, raw, json.loads(raw)

def jsonl(path: Path):
    return [d for _, _, d in lines(path)]

def write_json(path: Path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

def write_jsonl(path: Path, rows):
    path.write_text("".join(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in rows))

def clip(value, limit=1800):
    s = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return s if len(s) <= limit else s[:limit] + "…[truncated]"

INPUTS = {
    "formal_case_results": RESULTS,
    "formal_raw_traces": TRACES,
    "step9_30b_adjudication": ADJ,
    "step9_30c_aggregate_metrics": METRICS,
    "frozen_rubric": RUBRIC,
    "frozen_metric_registry": REGISTRY,
    "lineage_sidecar": SIDECAR,
    "attempt_ledger": ATTEMPTS,
    "benchmark_v4_dataset": BENCHMARK,
    "benchmark_v4_manifest": MANIFEST,
}
input_manifest = {k: {"path": str(p.relative_to(ROOT)), "sha256": sha(p), "bytes": p.stat().st_size}
                 for k, p in INPUTS.items()}

adjs = {d["immutable_execution_facts"]["case_id"]: d for d in jsonl(ADJ)}
metrics = json.loads(METRICS.read_text())
trace_rows = list(lines(TRACES))
result_rows = list(lines(RESULTS))
traces = {d["case_id"]: (n, raw, d) for n, raw, d in trace_rows}
results = {d["case_id"]: (n, raw, d) for n, raw, d in result_rows}
assert len(adjs) == len(traces) == len(results) == 40

ASK_META = {
    "V4-CA-02": ("HARD_PRECONDITION_OVERRIDES_INFORMATION_VALUE", "DEPENDENCY_FORMATION", "The timing question is emitted by an unsatisfied VALIDITY_STATE hard precondition even though its own counterfactual/value assessment says plausible answers do not alter direction or scope."),
    "V4-CA-04": ("HARD_PRECONDITION_OVERRIDES_INFORMATION_VALUE", "DEPENDENCY_FORMATION", "Same forced timing precondition; the subsequent retrieval does not repair the unnecessary initial ASK."),
    "V4-PD-03": ("HARD_PRECONDITION_OVERRIDES_INFORMATION_VALUE", "DEPENDENCY_FORMATION", "The forced target is latency although the user asks which schedule anchor to change and supplies a fixed leave time."),
    "V4-PD-04": ("HARD_PRECONDITION_OVERRIDES_INFORMATION_VALUE", "DEPENDENCY_FORMATION", "The forced latency precondition persists despite the bounded answer being possible; adjudication calls the ASK redundant."),
    "V4-PD-05": ("INPUT_FACT_NOT_PROJECTED_TO_STATE", "INPUT_UNDERSTANDING_STATE", "The user had already supplied nap timing, approximate duration, and no perceived sleep-onset effect, while the state facts are empty and the same details are requested."),
    "V4-PD-06": ("HARD_PRECONDITION_OVERRIDES_INFORMATION_VALUE", "DEPENDENCY_FORMATION", "The generic sleep-onset latency precondition forces acquisition before evaluating the requested comparison; no evidence retrieval follows."),
    "V4-PD-10": ("INPUT_FACT_AND_UNANSWERABLE_TARGET_STATE_NOT_REPRESENTED", "INPUT_UNDERSTANDING_STATE", "Explicit stable schedule/sleep adequacy facts are absent from state; after each unknown response the next optional target is still asked, with no declined/unavailable target state."),
}

ask_rows = []
for cid, (root_cause, layer, rationale) in ASK_META.items():
    tn, traw, trace = traces[cid]
    adj = adjs[cid]
    j = adj["reviewer_judgments"]
    actions_seen = 0
    for turn_num, turn in enumerate(trace.get("turns", []), 1):
        state = turn.get("state", {})
        hist = state.get("action_history", [])
        # In each persisted turn, the current new action is the last action in history.
        current = hist[-1] if hist and hist[-1].get("action") == "ASK" else None
        if current is None:
            continue
        actions_seen += 1
        candidate_id = current.get("selected_candidate_id")
        candidate = next((c for c in state.get("candidate_actions", []) if c.get("candidate_id") == candidate_id), None)
        if candidate is None:
            # Candidate history may only retain the active candidate; identify it by action and target.
            candidate = next((c for c in state.get("candidate_actions", []) if c.get("action") == "ASK" and c.get("target") == current.get("target")), None)
        labels = j.get("ask_quality", {}).get("counts", {})
        label = next((k for k, v in labels.items() if v), "unavailable")
        users = trace.get("user_turns", [])
        ask_rows.append({
            "case_id": cid, "task_type": adj["immutable_execution_facts"]["task_type"],
            "ask_event_index_in_case": actions_seen, "turn": turn_num,
            "question_asked": (candidate or {}).get("question"), "target": current.get("target"),
            "user_turns_visible_before_or_at_ask": users[:turn_num],
            "known_facts_before_ask": state.get("facts", {}),
            "missing_facts_before_ask": state.get("decision_relevant_missing", state.get("critical_missing", [])),
            "candidate_actions": state.get("candidate_actions", []),
            "dependency_state": state.get("dependencies_required", []),
            "precondition_state": state.get("preconditions_considered", []),
            "information_value_judgment": state.get("information_estimates", {}),
            "eventual_action_path": adj["immutable_execution_facts"]["action_path"],
            "reviewer_ask_classification": label,
            "first_divergence_layer": layer, "postmortem_root_cause": root_cause,
            "postmortem_evidence": rationale,
            "trace_provenance": {"path": str(TRACES.relative_to(ROOT)), "line_number": tn, "line_sha256": hashlib.sha256(traw).hexdigest()},
            "adjudication_provenance": adj["execution_provenance"],
        })

harmful_layers = {
    "V4-CA-01": "REQUIREMENTS_DEPENDENCY_FORMATION",
    "V4-CA-02": "DEPENDENCY_FORMATION",
    "V4-CA-03": "CANDIDATE_GENERATION_DECISION_POLICY",
    "V4-CA-05": "CANDIDATE_GENERATION_DECISION_POLICY",
    "V4-CA-06": "CANDIDATE_GENERATION_DECISION_POLICY",
    "V4-CA-07": "CANDIDATE_GENERATION_DECISION_POLICY",
    "V4-CA-09": "CANDIDATE_GENERATION_DECISION_POLICY",
    "V4-CA-10": "CANDIDATE_GENERATION_DECISION_POLICY",
    "V4-PD-01": "REQUIREMENTS_DEPENDENCY_FORMATION",
    "V4-PD-03": "DEPENDENCY_FORMATION",
    "V4-PD-05": "INPUT_UNDERSTANDING_STATE",
    "V4-PD-06": "DEPENDENCY_FORMATION",
    "V4-PD-07": "CANDIDATE_GENERATION_DECISION_POLICY",
    "V4-PD-08": "CANDIDATE_GENERATION_DECISION_POLICY",
    "V4-PD-09": "REQUIREMENTS_DEPENDENCY_FORMATION",
    "V4-PD-10": "INPUT_UNDERSTANDING_STATE_AND_ACQUISITION_LOOP",
}

def explain_harm(cause, trace, state):
    path = trace.get("action_path", [])
    tools = [x for x in path if x in ("RETRIEVE", "READ_DIARY")]
    if cause == "TASK_EXECUTION_OMISSION":
        return "The frozen reviewer found the requested diary operation was not completed despite READ_DIARY returning; the first divergence is the answer/task-completion contract after tool-result projection."
    if cause == "EVIDENCE_COVERAGE_LIMITATION":
        return "The frozen reviewer found answer scope/coverage incomplete after evidence acquisition; this is downstream synthesis/coverage, not an observed unsafe claim."
    if cause == "REPEATED_IRRELEVANT_ACQUISITION":
        return "Repeated ASK actions continued after earlier unknown responses; state does not represent an unavailable/declined target and does not stop equivalent optional acquisition."
    if "INFORMATION" in cause:
        return "The frozen rubric requires user-specific information and/or evidence acquisition not present in the action path; state/requirements and acquisition planning fail to make the needed information actionable."
    if "RESOURCE" in cause or "EVIDENCE" in cause or "CONDITIONAL" in cause:
        return "No required evidence resource was actually invoked before a bounded answer; user-information incompleteness appears to suppress the independent evidence path in these traces."
    return "The frozen adjudication indicates an action-selection error; see trace state and rationale for the case-specific first divergence."

harm_rows = []
for cid, adj in adjs.items():
    j = adj["reviewer_judgments"]
    if not j["harmful_failure"]:
        continue
    tn, traw, trace = traces[cid]
    rn, rraw, result = results[cid]
    state = trace.get("final_state", {})
    cause = j["failure_attribution"]["primary_cause"]
    action_path = trace.get("action_path", [])
    harm_rows.append({
        "case_id": cid, "task_type": adj["immutable_execution_facts"]["task_type"],
        "score": j["total_score"], "harmful_label": True,
        "frozen_primary_cause": cause, "frozen_rationale": j["failure_attribution"]["rationale"],
        "observable_failure": explain_harm(cause, trace, state),
        "first_incorrect_decision": (state.get("action_history") or [{}])[0],
        "first_divergence_layer_postmortem": harmful_layers[cid],
        "available_state_at_final_trace": {k: state.get(k) for k in ("goal", "facts", "critical_missing", "decision_missing", "decision_relevant_missing", "required_resources", "dependencies_required", "dependencies_satisfied", "candidate_actions", "evidence_sufficiency", "user_info_sufficiency", "evidence", "action_history") if k in state},
        "action_path": action_path, "actual_tool_calls": adj["immutable_execution_facts"].get("tool_calls", []),
        "tool_result_projection_summary": {"diary_projection_present": bool(state.get("diary_projection")), "evidence_items": len(state.get("evidence") or []), "resource_status": state.get("resource_status")},
        "answer_behavior_summary": explain_harm(cause, trace, state),
        "avoidable_using_already_available_evidence": "YES_WITH_AVAILABLE_STATE_OR_PRODUCTION_RESOURCE_PATH" if not any(x in cause for x in ("EVIDENCE_COVERAGE_LIMITATION",)) else "PARTIALLY; further evidence coverage would be required",
        "validity": j["validity_judgment"], "completion": j["completion_judgment"],
        "trace_provenance": {"path": str(TRACES.relative_to(ROOT)), "line_number": tn, "line_sha256": hashlib.sha256(traw).hexdigest()},
        "case_result_provenance": {"path": str(RESULTS.relative_to(ROOT)), "line_number": rn, "line_sha256": hashlib.sha256(rraw).hexdigest()},
        "adjudication_provenance": adj["execution_provenance"],
    })

assert len(ask_rows) == 9, f"expected 9 ASK events, got {len(ask_rows)}"
assert len(harm_rows) == 16, f"expected 16 harmful cases, got {len(harm_rows)}"

ask_roots = Counter(r["postmortem_root_cause"] for r in ask_rows)
ask_layers = Counter(r["first_divergence_layer"] for r in ask_rows)
completion = Counter()
completion_causes = Counter()
task_cause = defaultdict(Counter)
layer_counts = Counter()
harm_layer_counts = Counter()
for cid, adj in adjs.items():
    j = adj["reviewer_judgments"]
    valid = j["validity_judgment"]
    complete = j["completion_judgment"] == "complete"
    category = "VALID_AND_COMPLETE" if valid and complete else "VALID_BUT_INCOMPLETE" if valid else "INVALID_BUT_COMPLETE" if complete else "INVALID_AND_INCOMPLETE"
    completion[category] += 1
    if not complete:
        cause = j["failure_attribution"]["primary_cause"]
        completion_causes[cause] += 1
        task_cause[adj["immutable_execution_facts"]["task_type"]][cause] += 1
        layer = harmful_layers.get(cid)
        if not layer:
            if cause == "TASK_EXECUTION_OMISSION": layer = "ANSWER_GENERATION_TASK_EXECUTION"
            elif cause == "EVIDENCE_COVERAGE_LIMITATION": layer = "ANSWER_GENERATION_EVIDENCE_SYNTHESIS"
            elif cause == "CONDITIONAL_EVIDENCE_NOT_RETRIEVED": layer = "CANDIDATE_GENERATION_DECISION_POLICY"
            elif cause in ("ACTION_SELECTION", "UNNECESSARY_INFORMATION_ACQUISITION", "UNNECESSARY_RETRIEVAL"): layer = "DECISION_POLICY_INFORMATION_VALUE"
            elif "INFORMATION" in cause: layer = "REQUIREMENTS_DEPENDENCY_FORMATION"
            else: layer = "CANDIDATE_GENERATION_DECISION_POLICY"
        layer_counts[layer] += 1
for r in harm_rows: harm_layer_counts[r["first_divergence_layer_postmortem"]] += 1

repair = [
 {"repair_id":"R1_EVIDENCE_PATH_INDEPENDENT_OF_PERSONAL_FACT_COMPLETENESS","target_layer":"Requirements / dependency formation → Candidate generation","observed_failures_addressed":["required evidence omitted while facts are incomplete","premature bounded answer"],"case_count_affected":15,"harmful_failure_count_affected":15,"ask_failure_count_affected":0,"mechanism_hypothesis":"Represent user-fact dependencies and external-evidence dependencies independently; missing personal facts should bound personalization but must not suppress useful general evidence acquisition.","expected_behavior_change":"When a task has a meaningful evidence requirement, retrieve general evidence even if personal facts remain incomplete, then answer within the evidence and personalization boundary.","regression_risk":"May increase unnecessary/irrelevant retrieval or evidence-led overreach; require retrieval appropriateness and claim-grounding checks.","how_to_test_without_v4":"Structured unit tests for mixed independent dependencies; synthetic production-path cases with partial facts; measure retrieval precision, evidence-to-claim lineage, boundedness, and completion; no V4 fixtures/wording."},
 {"repair_id":"R2_VALUE_GATED_PRECONDITION_AND_SAFE_FALLBACK","target_layer":"Dependency formation / Information value / Decision policy","observed_failures_addressed":["hard precondition forces low-value ASK","ASK prevents immediate bounded answer or evidence path"],"case_count_affected":5,"harmful_failure_count_affected":3,"ask_failure_count_affected":5,"mechanism_hypothesis":"A hard precondition should force ASK only when no safe fallback exists and plausible answers can change direction, next action, or necessary answer scope; otherwise keep a bounded path and evaluate independent resources.","expected_behavior_change":"Suppress irrelevant forced ASK while preserving genuinely necessary acquisition and its safety boundary.","regression_risk":"Could suppress a genuinely necessary clarification or cause unsupported personalization if the counterfactual gate is too permissive.","how_to_test_without_v4":"Counterfactual matrix with necessary, useful, irrelevant, refused, and unknown fields; adversarially vary answer direction; assert necessary-ASK preservation and no decision without critical data."},
 {"repair_id":"R3_ASSERTED_FACT_AND_UNAVAILABLE_TARGET_STATE","target_layer":"Input Understanding / State / interaction loop","observed_failures_addressed":["explicit user facts omitted from state","same or adjacent optional questions repeated after unknown response"],"case_count_affected":2,"harmful_failure_count_affected":2,"ask_failure_count_affected":4,"mechanism_hypothesis":"State projection should retain semantically asserted facts with source/confidence, and represent asked/unknown/declined/unavailable targets so the acquisition loop does not re-ask or substitute equivalent low-value targets without new rationale.","expected_behavior_change":"Use facts already in the conversation, avoid repeat acquisition after unknown/refusal, and proceed with bounded answer or another independent useful action.","regression_risk":"False fact extraction, overgeneralized equivalence among distinct targets, or prematurely treating an unknown as permanently declined.","how_to_test_without_v4":"Synthetic paraphrase and contradiction suite; multi-turn unknown/refusal tests; inspect provenance and ask-target state transitions; no V4 examples."},
 {"repair_id":"R4_ANSWER_TASK_CONTRACT_AFTER_TOOL_PROJECTION","target_layer":"Tool Result Projection → Answer Context → Answer Generation","observed_failures_addressed":["diary data read but requested operation omitted","evidence retrieved but scope/coverage not synthesized"],"case_count_affected":6,"harmful_failure_count_affected":0,"ask_failure_count_affected":0,"mechanism_hypothesis":"Carry an explicit task/output contract through tool projection and validate that the answer performs the requested operation using available tool results before stopping.","expected_behavior_change":"Complete supported calculations/comparisons and state limitations only for genuinely unavailable portions.","regression_risk":"Could fabricate missing data or overstate answers if validation rewards completion without evidence constraints.","how_to_test_without_v4":"Synthetic arithmetic and evidence-synthesis tasks with known tool outputs; assert requested fields, provenance, and abstention only on unavailable items."},
]

matrix = {
 "schema_version":"step9_31_architecture_failure_map.v1", "source":"frozen V4 trace + frozen Step 9.30b single-AI-reviewer labels; postmortem layer mappings are analyst inferences",
 "failure_count_by_architecture_layer_for_incomplete_cases":dict(layer_counts),
 "harmful_failure_count_by_architecture_layer":dict(harm_layer_counts),
 "ask_failure_count_by_architecture_layer":dict(ask_layers),
 "ask_root_cause_counts":dict(ask_roots),
 "task_type_x_frozen_primary_cause_counts":{k:dict(v) for k,v in task_cause.items()},
 "task_type_summary":{
   "KNOWLEDGE_QA":{"mean":82.2,"complete":8,"incomplete":2,"primary_pattern":"retrieval generally succeeds; two evidence-scope/coverage-limited partial answers; not enough evidence for causal inference"},
   "CAUSE_ASSESSMENT":{"mean":59.1,"complete":1,"incomplete":9,"harmful":8,"primary_pattern":"eight harmful omissions (information/evidence), plus one action-selection miss; generic evidence path commonly absent; forced ASK can be a competing first action"},
   "PERSONALIZED_DECISION":{"mean":62.6,"complete":2,"incomplete":8,"harmful":8,"primary_pattern":"personal facts are selectively not projected or are treated as globally required; evidence and fact acquisition are not planned independently; one repeated-ASK loop"},
   "DATA_ANALYSIS":{"mean":78.1,"complete":5,"incomplete":5,"harmful":0,"primary_pattern":"READ_DIARY works, but four requested task operations are omitted after projection; one conditional evidence action is missing"}},
 "failure_taxonomy":{"architecture_level":"dependency/state separation and state projection recurrently fail before action selection; answer-task-contract gaps are a separate downstream class","policy_decision":"forced hard-precondition ASK overrides low information value; candidate gate may require high user-info sufficiency before retrieval","evidence_grounding":"CA/PD harmed traces show no RETRIEVE; the result is evidence omission, not evidence misuse in those cases","answer_generation":"four DA task-execution omissions occur after READ_DIARY; KQ has two coverage-limited partial cases","evaluation_reviewer_artifact":"labels and scores are single-AI-reviewer descriptive judgments, with no IIR; frozen low-value denominator is all 9 observed ASK events, while Step 9.25 optional-ASK controlled gate denominator was 3 candidates entering that gate. Step 9.25 local mechanism tests do not cover natural-language extraction/state projection, production mult-turn path, or end-to-end evidence selection. Thus 0/3 in the isolated gate and 9/9 in V4 are different populations, not contradictory replications."},
 "completion_vs_validity":{"valid_and_complete":completion["VALID_AND_COMPLETE"],"valid_but_incomplete":completion["VALID_BUT_INCOMPLETE"],"invalid_and_incomplete":completion["INVALID_AND_INCOMPLETE"],"invalid_but_complete":completion["INVALID_BUT_COMPLETE"],"validity_rate":0.925,"completion_rate":0.4,"completion_loss_primary_causes":dict(completion_causes),"interpretation":"Validity primarily captures bounded/non-overclaiming behavior; completion requires performing the requested information acquisition, evidence retrieval, or analysis. The 21 valid-but-incomplete answers stayed within safety bounds but stopped short of the task; 3 incomplete DA cases were also invalid."},
 "repair_candidates_ranked":repair,
 "top_repair_targets":[r["repair_id"] for r in repair[:3]],
 "paired_evaluation_hypotheses":[
   {"id":"H1","hypothesis":"New version reduces redundant-or-irrelevant ASK events per all ASK events under the same frozen annotation protocol.","guardrail":"necessary-ASK preservation must not decrease; separately report ASK count and event denominator."},
   {"id":"H2","hypothesis":"New version improves task completion, especially in CA and PD strata, without using ANSWER terminal status as a completion proxy."},
   {"id":"H3","hypothesis":"New version reduces harmful-failure count and the evidence/information-omission mechanisms identified here."},
   {"id":"H4","hypothesis":"Necessary ASK target acquisition is non-inferior and critical failure count does not increase."},
   {"id":"H5","hypothesis":"Where personal facts are incomplete but a general evidence dependency exists, independent retrieval and evidence-to-answer lineage increase without reducing factual boundedness."},
   {"id":"H6","hypothesis":"Explicit-fact recall improves and repeated acquisition after unknown/unavailable responses decreases."},
   {"id":"H7","hypothesis":"After successful diary/tool projection, completion of the requested analytic operation improves while unsupported calculations remain absent."}
 ],
 "contamination_boundary":"From this postmortem onward V4 is DEVELOPMENT / POSTMORTEM EVIDENCE. Any Agent changes informed by Step 9.31 make V4 non-unseen for that Agent. V4 may be used for regression/paired mechanism analysis; generalization claims for a new Agent require a newly sealed V5.",
 "limitations":["The Step 9.30b reviewer was a single AI reviewer; inter-rater reliability was not measured.","Architecture first-divergence layer assignments and repair estimates are postmortem inferences over frozen traces, not independently adjudicated labels.","No pass threshold is defined; historical comparison is NOT_COMPARABLE.","No V4 execution, model/Agent/RAG invocation, or rescoring occurred in Step 9.31."],
}

def result_row(cid): return results[cid]

postmortem = {
 "schema_version":"step9_31_v4_postmortem.v1", "created_at_utc":datetime.now(timezone.utc).isoformat(),
 "status":"READ_ONLY_POSTMORTEM", "input_manifest":input_manifest,
 "authoritative_aggregate_summary":{"case_count":40,"overall":70.5,"task_means":{"KNOWLEDGE_QA":82.2,"CAUSE_ASSESSMENT":59.1,"PERSONALIZED_DECISION":62.6,"DATA_ANALYSIS":78.1},"validity_rate":0.925,"completion_rate":0.4,"ask_events":9,"harmful_failures":16,"critical_failures":0,"lineage":{"formal_ready":28,"derived_complete":7,"incomplete_formal_adjudicatable":5},"reviewer_type":"SINGLE_AI_REVIEWER","inter_rater_reliability":"NOT_MEASURED","pass_threshold":"NOT_DEFINED","historical_comparability":"NOT_COMPARABLE"},
 "ask_event_count":len(ask_rows),"ask_root_cause_counts":dict(ask_roots),"ask_first_divergence_layer_counts":dict(ask_layers),
 "harmful_failure_count":len(harm_rows),"harmful_primary_cause_counts":dict(Counter(r["frozen_primary_cause"] for r in harm_rows)),
 "completion_validity_cross_tab":matrix["completion_vs_validity"],
 "controlled_test_reconciliation":matrix["failure_taxonomy"]["evaluation_reviewer_artifact"],
 "architecture_failure_map_path":"evaluation/v1_2_3/step9_31_architecture_failure_map.json",
 "repair_hypotheses_path":"evaluation/v1_2_3/step9_31_repair_hypotheses.json",
 "integrity":{"AGENT_MODIFIED":"NO","BENCHMARK_V4_MODIFIED":"NO","ADJUDICATION_MODIFIED":"NO","SCORING_MODIFIED":"NO","METRIC_REGISTRY_MODIFIED":"NO","V4_RERUN":"NO","MODEL_CALLED":"NO","AGENT_CALLED":"NO","RAG_CALLED":"NO"}
}

write_jsonl(OUT/"step9_31_ask_failure_matrix.jsonl", ask_rows)
write_jsonl(OUT/"step9_31_harmful_failure_matrix.jsonl", harm_rows)
write_json(OUT/"step9_31_architecture_failure_map.json", matrix)
write_json(OUT/"step9_31_repair_hypotheses.json", {"ranked_repair_candidates":repair,"paired_evaluation_hypotheses":matrix["paired_evaluation_hypotheses"],"contamination_boundary":matrix["contamination_boundary"]})
write_json(OUT/"step9_31_v4_postmortem.json", postmortem)

md = f'''# Step 9.31 — V4 Postmortem & Architecture-Level Failure Taxonomy\n\nStatus: **READ_ONLY_POSTMORTEM**. This analysis consumes frozen Step 9.30c-r1 metrics, Step 9.30b adjudication, formal case results/raw traces, rubric, Metric Registry, and lineage sidecar. No Agent/model/RAG call, V4 rerun, or rescoring occurred. Input paths and SHA-256 digests are embedded in `step9_31_v4_postmortem.json`.\n\n## Result in brief\n\n- 40 cases; descriptive overall 70.5. By task: KQ 82.2, CA 59.1, PD 62.6, DA 78.1.\n- Validity 37/40 (92.5%); completion 16/40 (40.0%). Cross-tab: {completion["VALID_AND_COMPLETE"]} valid+complete, {completion["VALID_BUT_INCOMPLETE"]} valid but incomplete, {completion["INVALID_AND_INCOMPLETE"]} invalid and incomplete, {completion["INVALID_BUT_COMPLETE"]} invalid but complete.\n- All 9 ASK events were low-value per the frozen reviewer: 8 irrelevant and 1 redundant. Event-level root cause counts: {dict(ask_roots)}. First divergence: {dict(ask_layers)}.\n- Harmful failures: 16; frozen cause counts: {dict(Counter(r["frozen_primary_cause"] for r in harm_rows))}. Critical failures: 0.\n\n## ASK mechanism and controlled-test discrepancy\n\nFive ASK events ({', '.join(r['case_id'] for r in ask_rows if r['first_divergence_layer']=='DEPENDENCY_FORMATION')}) arose from a generic validity-state dependency/forced precondition: the hard gate forced an ASK despite a bounded fallback or an unhelpful target. Four events were tied to state projection/input-understanding issues: one question repeated facts already stated (PD-05), and three asks in PD-10 followed explicit adequate/stable facts missing from state plus no persistent “unknown/unavailable/asked” target state. The full event-level evidence and raw-line digests are in `step9_31_ask_failure_matrix.jsonl`.\n\nStep 9.25’s mechanism tests passed local structured scenarios, but the low-value optional-ASK denominator was 3 candidates that entered that gate (0 low-value among those), not all production-path ASK events. It did not cover end-to-end natural-language fact extraction, state projection, multi-turn unknown handling, or production evidence selection. V4’s 9/9 denominator covers observed ASK events across the held-out traces. These results therefore concern different populations and different pipeline layers; they are not logically contradictory. The controlled test is narrower evidence, not a generalization proof.\n\n## Harmful failures and task weakness\n\nCA’s 8/10 harmful outcomes mostly share omitted user information and/or external evidence before bounded answers; PD’s 8/10 harmful outcomes include omitted information/resources, wrong forced acquisition, known-fact loss, and a repeated-ASK loop. The traces show no actual RETRIEVE in the harmful CA/PD cases. This is consistent with an upstream dependency/candidate-policy interaction: incomplete user facts can make the system stop at a bounded answer rather than independently retrieving general evidence. This remains an architecture-level inference from traces, not a new frozen reviewer label.\n\nKQ is strongest (8 complete; 2 evidence-coverage partial) and all ten cases retrieve; DA is 5/10 complete, with diary reads present in all ten, but four harmful task-execution omissions occurred after diary data projection. Thus CA/PD weakness is not simply “the model cannot answer”: their trace bottleneck is acquisition planning and fact/dependency handling; DA’s separate weakness is task completion after tool results; KQ’s residual weakness is evidence coverage/synthesis. Task × frozen cause and inferred architecture mappings are in `step9_31_architecture_failure_map.json`.\n\n## Validity vs completion\n\nValidity (37/40) measures bounded/defensible behavior; completion (16/40) requires doing the requested acquisition, evidence retrieval, or analysis. Twenty-one cases are valid but incomplete: safe limitations were often stated, but a requested action/result was omitted. Three DA cases were both invalid and incomplete. Completion root labels are preserved as adjudicated: {dict(completion_causes)}. `final_status=ANSWER` was not used as a completion proxy.\n\n## Ranked architecture repair candidates\n\n1. **{repair[0]['repair_id']}** — decouple external evidence needs from personal-fact completeness. Addresses an estimated 15 omission cases (all harmful in this postmortem grouping); main risk is irrelevant retrieval/overreach.\n2. **{repair[1]['repair_id']}** — require information-value and safe-fallback checks before hard-precondition ASK; preserve truly necessary clarification. Addresses 5 ASK events and 4 harmful cases; main risk is suppressing necessary ASK.\n3. **{repair[2]['repair_id']}** — project asserted facts and retain unknown/unavailable target state. Addresses 4 ASK events and 2 harmful cases in two cases; main risk is erroneous extraction or overbroad target equivalence.\n\nR4, answer-task contract after tool projection, is retained as a fourth candidate (six completion cases including two non-harmful evidence-coverage cases) but is outside the top three under the requested CA/PD/harmful/ASK common-upstream prioritization. See repair JSON for test plans and risks. These counts are hypotheses about addressable cases, not guaranteed treatment effects.\n\n## Paired hypotheses and contamination boundary\n\nPreregistered directional hypotheses (no numeric targets): reduce low-value ASK rate, improve completion and reduce harmful failures, preserve necessary ASK and critical-failure safety, increase independent evidence retrieval/grounding when personal facts are incomplete, improve explicit-fact retention and stop repeated asks after unknown/unavailable responses, and improve requested diary task completion without unsupported calculations. Exact denominators and frozen adjudication protocol must be held constant in later paired evaluation.\n\nFrom this point, V4 is **DEVELOPMENT / POSTMORTEM EVIDENCE**. Any Agent changes informed by Step 9.31 make V4 non-unseen for that Agent. V4 may support regression or paired mechanism analysis; a new sealed V5 is required for a new Agent’s held-out generalization claim.\n\n## Limitations and integrity\n\nStep 9.30b was a single AI reviewer; IIR was not measured. Layer attribution is an analyst inference, not independently adjudicated. No pass threshold is defined and historical comparability is NOT_COMPARABLE. Frozen inputs were only read; all Step 9.31 output artifacts are additive. Agent, benchmark, adjudication, scoring, and metric registry were not modified; V4 was not rerun; no model, Agent, or RAG was called.\n'''
(OUT/"step9_31_v4_postmortem.md").write_text(md)

# Re-hash the frozen inputs after analysis to detect accidental changes.
post_hashes = {k: sha(p) for k, p in INPUTS.items()}
assert all(post_hashes[k] == v["sha256"] for k, v in input_manifest.items()), "frozen input changed during postmortem"
postmortem["post_analysis_input_hashes"] = post_hashes
write_json(OUT/"step9_31_v4_postmortem.json", postmortem)
print(json.dumps({"ask_events":len(ask_rows),"ask_roots":dict(ask_roots),"harmful_cases":len(harm_rows),"harmful_roots":dict(Counter(r["frozen_primary_cause"] for r in harm_rows)),"completion_cross_tab":dict(completion),"input_hashes_unchanged":True}, ensure_ascii=False))
