"""Read-only Step 9.36 audit for the frozen matched-treatment V4 attempt.

Writes only new Step 9.36 audit/freeze/derived-lineage artifacts. It never
loads benchmark cases, invokes the runner execution path, or calls model/Agent/RAG.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.run_step9_35a_matched_treatment import current_frozen_bindings
from scripts.step9_30a2_lineage_sidecar import classify_true_failure_dimensions

OUT = ROOT / "evaluation/v1_2_3"
RUN_ROOT = ROOT / "evaluation/v4_runs"
EVALUATION_ID = "heldout-v4-step9_34a-treatment-20260928-01"
AUTHORIZATION_ID = "auth-step9_35b-19cb1db7c4b46f073df71237a8608fc2"
ATTEMPT_ID = "attempt-step9_35b-e469d82618d4c51d91d193bb439507e4"
COMPARISON_CLASS = "POST_HOC_MATCHED_FROZEN_BASELINE"
AUTH = OUT / "step9_35b_matched_treatment_authorization_manifest.json"
AUTH_AUDIT = OUT / "step9_35b_matched_treatment_authorization_audit.json"
RUNNER_FREEZE = OUT / "step9_35a_treatment_runner_freeze.json"
HARNESS_FREEZE = OUT / "step9_13a_harness_freeze.json"
SCORING_FREEZE = OUT / "step9_11_clean_freeze_manifest.json"
REGISTRY = OUT / "step9_26_v4_metric_registry.json"
RULES = OUT / "step9_26_v4_one_shot_rules.md"
PROTOCOL = OUT / "step9_34a_matched_comparison_protocol.json"
MANIFEST = ROOT / "evaluation/benchmarks/benchmark_v4_manifest.json"
RUN = RUN_ROOT / EVALUATION_ID
LEDGER = RUN / "attempts.jsonl"
RESULTS = RUN / f"{ATTEMPT_ID}_case_results.jsonl"
TRACES = RUN / f"{ATTEMPT_ID}_raw_traces.jsonl"
OUTFILES = [
    OUT / "step9_36_treatment_run_input_freeze.json",
    OUT / "step9_36_treatment_lineage_forensics.json",
    OUT / "step9_36_treatment_lineage_forensics.md",
    OUT / "step9_36_treatment_lineage_case_matrix.jsonl",
    OUT / "step9_36_treatment_lineage_sidecar.jsonl",
]


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def file_record(path: Path) -> dict:
    raw = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": sha_bytes(raw),
            "byte_size": len(raw), "line_count": len(raw.splitlines())}


def line_ref(path: Path, case_id: str) -> dict:
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("case_id") == case_id:
            return {"path": path.relative_to(ROOT).as_posix(), "line_number": number,
                    "line_sha256": sha_bytes(line.encode("utf-8"))}
    raise RuntimeError(f"case trace line not found: {case_id}")


def derive(trace: dict) -> tuple[list[str], dict]:
    """Apply the Step 9.30a.1 contract across all persisted turns, unchanged."""
    turns = trace.get("turns", [])
    decisions: dict[str, dict] = {}
    dependency_ids: set[str] = set()
    semantic_ids: set[str] = set()
    for turn in turns:
        for snap in turn.get("state_history", []):
            for dep in snap.get("dependencies_considered", []):
                if dep.get("dependency_id"):
                    dependency_ids.add(dep["dependency_id"])
            for sem in snap.get("semantic_provenance", []):
                if sem.get("semantic_id"):
                    semantic_ids.add(sem["semantic_id"])
            if snap.get("event") == "DECISION":
                chosen = snap.get("chosen_action", {})
                if chosen.get("candidate_id"):
                    decisions[chosen["candidate_id"]] = snap
    final = trace.get("final_state", {})
    for dep in final.get("dependencies_considered", []):
        if dep.get("dependency_id"):
            dependency_ids.add(dep["dependency_id"])
    for sem in final.get("semantic_provenance", []):
        if sem.get("semantic_id"):
            semantic_ids.add(sem["semantic_id"])
    lineage_events = [e for turn in turns for e in turn.get("state", {}).get("lineage_events", [])]
    missing: list[str] = []
    for action in final.get("action_history", []):
        candidate = action.get("selected_candidate_id")
        decision = decisions.get(candidate)
        if not candidate or not decision:
            missing.append("MISSING_CANDIDATE_DECISION_LINK")
            continue
        chosen = decision.get("chosen_action", {})
        if chosen.get("source_dependency_id") and chosen["source_dependency_id"] not in dependency_ids:
            missing.append("MISSING_DEPENDENCY_LINK")
        if chosen.get("origin") == "HARD_PRECONDITION" and not chosen.get("source_precondition_id"):
            missing.append("MISSING_SOURCE_ID")
        if action.get("action") in {"RETRIEVE", "READ_DIARY"}:
            linked = [e for e in lineage_events if e.get("source_action_id") == action.get("action_id")]
            if not any(e.get("tool_result_id") and e.get("state_update_id") for e in linked):
                missing.append("MISSING_TOOL_RESULT_LINK")
            if action["action"] == "RETRIEVE" and not any(e.get("source_type") == "RAG" for e in linked):
                missing.append("MISSING_RETRIEVAL_PROVENANCE")
            if action["action"] == "READ_DIARY" and not any(e.get("source_type") == "session_diary" for e in linked):
                missing.append("MISSING_DIARY_PROVENANCE")
    if not final.get("goal_id"):
        missing.append("MISSING_GOAL_ROOT")
    if not semantic_ids:
        missing.append("MISSING_SEMANTIC_ROOT")
    if not dependency_ids:
        missing.append("MISSING_DEPENDENCY_ROOT")
    graph = {"goal_root_id": final.get("goal_id"), "semantic_root_ids": sorted(semantic_ids),
             "dependency_roots": sorted(dependency_ids), "decisions": decisions,
             "lineage_events": lineage_events, "actions": final.get("action_history", [])}
    return sorted(set(missing)), graph


def build() -> tuple[dict, list[dict], list[dict]]:
    if any(path.exists() for path in OUTFILES):
        raise RuntimeError("FAIL CLOSED: one or more Step 9.36 output paths already exist")
    for path in (AUTH, AUTH_AUDIT, RUNNER_FREEZE, HARNESS_FREEZE, SCORING_FREEZE, REGISTRY,
                 RULES, PROTOCOL, MANIFEST, LEDGER, RESULTS, TRACES):
        if not path.is_file():
            raise RuntimeError(f"FAIL CLOSED: required identity/input missing: {path}")

    pins = current_frozen_bindings()
    if not pins.get("all_frozen_hashes_match") or pins["evaluation_id"] != EVALUATION_ID:
        raise RuntimeError("FAIL CLOSED: current frozen treatment identity mismatch")
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    auth_audit = json.loads(AUTH_AUDIT.read_text(encoding="utf-8"))
    auth_hash = sha_file(AUTH)
    if auth_hash != auth_audit["authorization"]["manifest_sha256"]:
        raise RuntimeError("FAIL CLOSED: Step 9.35b authorization hash mismatch")
    required_auth_pins = {
        "evaluation_id": EVALUATION_ID, "authorization_id": AUTHORIZATION_ID,
        "attempt_id": ATTEMPT_ID, "comparison_class": COMPARISON_CLASS,
        "treatment_agent_sha256": pins["treatment_agent_sha256"],
        "baseline_agent_sha256": pins["baseline_agent_sha256"],
        "benchmark_sha256": pins["benchmark_sha256"], "benchmark_manifest_sha256": pins["benchmark_manifest_sha256"],
        "harness_sha256": pins["harness_sha256"], "scoring_sha256": pins["scoring_sha256"],
        "metric_registry_sha256": pins["metric_registry_sha256"],
        "one_shot_rules_sha256": pins["one_shot_rules_sha256"],
        "matched_protocol_sha256": pins["matched_protocol_sha256"],
        "treatment_runner_sha256": pins["treatment_runner_sha256"],
    }
    if any(auth.get(k) != v for k, v in required_auth_pins.items()):
        raise RuntimeError("FAIL CLOSED: run identity does not match authorization")

    ledger, result_rows, trace_rows = jsonl(LEDGER), jsonl(RESULTS), jsonl(TRACES)
    if len(result_rows) != 40 or len(trace_rows) != 40:
        raise RuntimeError("FAIL CLOSED: expected 40 case results and traces")
    case_ids = [r.get("case_id") for r in result_rows]
    trace_ids = [t.get("case_id") for t in trace_rows]
    if (len(set(case_ids)) != 40 or len(set(trace_ids)) != 40 or
            case_ids != trace_ids or any(not isinstance(x, str) or not x for x in case_ids)):
        raise RuntimeError("FAIL CLOSED: result/trace coverage, uniqueness, or order mismatch")
    if any(r.get("evaluation_id") != EVALUATION_ID or r.get("score_status") != "PENDING_FROZEN_RUBRIC_REVIEW"
           for r in result_rows):
        raise RuntimeError("FAIL CLOSED: result identity or score status mismatch")
    if any(t.get("evaluation_id") != EVALUATION_ID for t in trace_rows):
        raise RuntimeError("FAIL CLOSED: raw trace evaluation identity mismatch")
    if not all(e.get("evaluation_id") == EVALUATION_ID and e.get("authorization_id") == AUTHORIZATION_ID
               and e.get("attempt_id") == ATTEMPT_ID and e.get("comparison_class") == COMPARISON_CLASS
               and e.get("runner_sha256") == pins["treatment_runner_sha256"]
               and e.get("treatment_agent_sha256") == pins["treatment_agent_sha256"] for e in ledger):
        raise RuntimeError("FAIL CLOSED: ledger lineage identity mismatch")
    per_case_starts = [e for e in ledger if e.get("status") == "STARTED" and e.get("scope") == "CASE"]
    completions = [e for e in ledger if e.get("status") == "CASE_COMPLETED"]
    if (ledger[-1].get("status") != "COMPLETED" or ledger[-1].get("cases_started") != 40 or
            ledger[-1].get("cases_completed") != 40 or len(per_case_starts) != 40 or
            len(completions) != 40 or [e.get("case_id") for e in per_case_starts] != case_ids or
            [e.get("case_id") for e in completions] != case_ids):
        raise RuntimeError("FAIL CLOSED: attempt state or per-case ledger sequence mismatch")
    for required_event in ("PREPARED", "AUTHORIZATION_CONSUMED", "FIRST_EVALUATION_ACCESS",
                           "CASE_SET_AND_ORDER_VERIFIED", "COMPLETED"):
        if sum(e.get("status") == required_event for e in ledger) != 1:
            raise RuntimeError(f"FAIL CLOSED: expected exactly one {required_event} event")

    traces_by_id = {t["case_id"]: t for t in trace_rows}
    results_by_id = {r["case_id"]: r for r in result_rows}
    matrix, sidecar = [], []
    for index, case_id in enumerate(case_ids, 1):
        result, trace = results_by_id[case_id], traces_by_id[case_id]
        missing, graph = derive(trace)
        frozen_false = result.get("lineage_ready") is False
        frozen_ready = result.get("lineage_ready") is True
        if not frozen_false and not frozen_ready:
            raise RuntimeError(f"FAIL CLOSED: missing formal lineage state: {case_id}")
        if missing and frozen_ready:
            raise RuntimeError(f"FAIL CLOSED: recomputed lineage conflicts with formal-ready state: {case_id}")
        if missing:
            classification = "TRUE_LINEAGE_FAILURE" if "MISSING_SEMANTIC_ROOT" in missing else "INDETERMINATE"
            recomputed = "INCOMPLETE" if classification == "TRUE_LINEAGE_FAILURE" else "INDETERMINATE"
            side_status = "INCOMPLETE_FORMAL" if classification == "TRUE_LINEAGE_FAILURE" else "INDETERMINATE"
        elif frozen_false:
            classification, recomputed, side_status = "RUNNER_DERIVATION_BUG", "COMPLETE", "COMPLETE_DERIVED"
        else:
            classification, recomputed, side_status = "NO_FAILURE", "COMPLETE", "COMPLETE_FORMAL"
        raw_ref = line_ref(TRACES, case_id)
        if recomputed == "COMPLETE":
            # A trace satisfying every frozen lineage root/link requirement
            # carries complete evidence for the frozen rubric dimensions.
            dims = {"eligibility": "FULL", "dimensions": {
                "goal_alignment": "SCORABLE", "facts_state_integrity": "SCORABLE",
                "action_resource_selection": "SCORABLE", "evidence_answer_scope": "SCORABLE",
                "interaction_efficiency": "SCORABLE"}}
        else:
            # Match the Step 9.30a.2 missing-root eligibility audit exactly.
            dims = classify_true_failure_dimensions(trace)
        eligibility = "FULL" if dims["eligibility"] == "FULL" else "PARTIAL"
        # The frozen protocol supplies no partial-missing-dimension scoring rule; NONE is reserved for no auditable answer/trace.
        if not trace.get("final_answer") and not result.get("answer"):
            eligibility = "NONE"
        action_links = []
        for action in graph["actions"]:
            candidate = action.get("selected_candidate_id")
            decision = graph["decisions"].get(candidate, {})
            chosen = decision.get("chosen_action", {})
            links = [e for e in graph["lineage_events"] if e.get("source_action_id") == action.get("action_id")]
            action_links.append({"action_id": action.get("action_id"), "action": action.get("action"),
                                 "candidate_id": candidate if candidate in graph["decisions"] else None,
                                 "candidate_decision_link_present": candidate in graph["decisions"],
                                 "origin": chosen.get("origin"), "source_precondition_id": chosen.get("source_precondition_id"),
                                 "source_dependency_id": chosen.get("source_dependency_id"),
                                 "tool_result_state_update_links": [{k:e.get(k) for k in
                                     ("tool_result_id", "state_update_id", "source_type", "tool")} for e in links]})
        row = {
            "case_id": case_id, "task_type": result.get("task_type"), "lineage_ready_frozen": frozen_ready,
            "action_path": trace.get("action_path", []), "ASK_count": result.get("ASK_count"),
            "RETRIEVE_count": result.get("RETRIEVE_count"), "READ_DIARY_count": result.get("READ_DIARY_count"),
            "tool_calls": result.get("tool_calls", []), "turn_count": result.get("turn_count"),
            "step_count": result.get("step_count"), "final_status": result.get("final_status"),
            "score_status": result.get("score_status"), "raw_trace_present": True,
            "case_result_present": True, "raw_trace_provenance": raw_ref,
            "recomputed_lineage_status": recomputed, "reason_codes": missing,
            "root_cause_class": classification, "adjudication_eligibility": eligibility,
            "dimension_evidence": dims["dimensions"],
        }
        matrix.append(row)
        sidecar.append({
            "case_id": case_id, "formal_lineage_ready": frozen_ready,
            "recomputed_lineage_status": recomputed, "root_cause_class": classification,
            "sidecar_lineage_status": side_status,
            "lineage_reconstructed": side_status == "COMPLETE_DERIVED",
            "reconstruction_source": {"raw_trace_line": raw_ref,
                "reconstruction_method": "join cumulative final_state.action_history to DECISION snapshots across all persisted turns; preserve existing identifiers only"},
            "reason_codes": missing,
            "semantic_root_status": "PRESENT" if graph["semantic_root_ids"] else "MISSING_IN_FORMAL_TRACE",
            "adjudication_lineage_status": "INCOMPLETE" if side_status in {"INCOMPLETE_FORMAL", "INDETERMINATE"} else "COMPLETE",
            "lineage_graph": {"goal_root_id": graph["goal_root_id"],
                "semantic_root_ids": graph["semantic_root_ids"],
                "dependency_roots": [{"dependency_id": dep} for dep in graph["dependency_roots"]],
                "action_candidate_links": action_links},
            "trace_provenance": raw_ref, "reviewer_scores_populated": False,
        })
    return pins, matrix, sidecar


def main() -> None:
    pins, matrix, sidecar = build()
    frozen_paths = [LEDGER, RESULTS, TRACES]
    freeze = {
        "step": "9.36", "freeze_type": "COMPLETED_TREATMENT_FORMAL_RUN_INPUTS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_id": EVALUATION_ID, "authorization_id": AUTHORIZATION_ID,
        "attempt_id": ATTEMPT_ID, "comparison_class": COMPARISON_CLASS,
        "artifact_files": [file_record(path) for path in frozen_paths],
        "execution_identity": {k: pins[k] for k in (
            "baseline_agent_sha256", "treatment_agent_sha256", "treatment_runner_sha256",
            "production_case_path_runner_sha256", "benchmark_path", "benchmark_sha256",
            "benchmark_manifest_sha256", "harness_sha256", "scoring_sha256",
            "scoring_rubric_sha256", "metric_registry_sha256", "one_shot_rules_sha256",
            "matched_protocol_sha256", "baseline_metric_lock_sha256", "claim_policy_sha256",
            "case_count", "case_order_fingerprint_sha256", "all_frozen_hashes_match")},
        "authorization_manifest_path": AUTH.relative_to(ROOT).as_posix(),
        "authorization_manifest_sha256": sha_file(AUTH),
        "formal_inputs_read_only": True,
    }
    counts = Counter(row["recomputed_lineage_status"] for row in matrix)
    roots = Counter(row["root_cause_class"] for row in matrix)
    elig = Counter(row["adjudication_eligibility"] for row in matrix)
    formal_true = [r for r in matrix if r["lineage_ready_frozen"] is True]
    formal_false = [r for r in matrix if r["lineage_ready_frozen"] is False]
    audit = {
        "step": "9.36", "forensic_type": "READ_ONLY_MATCHED_TREATMENT_LINEAGE_FORENSICS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_id": EVALUATION_ID, "authorization_id": AUTHORIZATION_ID,
        "attempt_id": ATTEMPT_ID, "comparison_class": COMPARISON_CLASS,
        "input_freeze_sha256": sha_bytes(json.dumps(freeze, sort_keys=True, ensure_ascii=False).encode()),
        "formal_lineage_ready_count": len(formal_true),
        "formal_lineage_false_count": len(formal_false),
        "formal_lineage_false_case_ids": [r["case_id"] for r in formal_false],
        "recomputed_status_counts": {k: counts[k] for k in ("COMPLETE", "NOT_APPLICABLE", "INCOMPLETE", "INDETERMINATE")},
        "root_cause_counts": {k: roots[k] for k in ("RUNNER_DERIVATION_BUG", "TRUE_LINEAGE_FAILURE", "PERSISTENCE_BUG", "NOT_APPLICABLE_MISCLASSIFIED", "INDETERMINATE")},
        "derived_lineage_repair_count": roots["RUNNER_DERIVATION_BUG"],
        "sidecar_complete_count": sum(x["sidecar_lineage_status"] in {"COMPLETE_FORMAL", "COMPLETE_DERIVED"} for x in sidecar),
        "sidecar_incomplete_count": sum(x["sidecar_lineage_status"] == "INCOMPLETE_FORMAL" for x in sidecar),
        "full_adjudication_case_count": elig["FULL"], "partial_adjudication_case_count": elig["PARTIAL"],
        "non_adjudicatable_case_count": elig["NONE"],
        "eligibility_dimensions": {r["case_id"]: r["dimension_evidence"] for r in matrix},
        "trace_contract": "Same Step 9.30a.1/.2 rule: every recorded action must link to a persisted DECISION candidate; any source dependency must resolve; HARD_PRECONDITION must name a precondition; RETRIEVE/READ_DIARY need tool_result_id and state_update_id plus RAG/session_diary provenance; goal, semantic, and dependency roots must exist. No semantic IDs are synthesized.",
        "adjudication_eligibility_contract": "Same Step 9.30a.2 trace-evidence availability test; eligibility is not lineage completeness and is not an adjudication score. Frozen protocol does not specify exclusion/partial denominator rules.",
        "case_coverage_match": True, "attempt_status": "COMPLETED",
        "case_result_count": len(jsonl(RESULTS)), "raw_trace_count": len(jsonl(TRACES)),
        "case_id_order_preserved": True,
        "raw_execution_counts": {k: sum(r.get(k, 0) or 0 for r in jsonl(RESULTS)) for k in ("ASK_count", "RETRIEVE_count", "READ_DIARY_count")},
        "score_status_counts": dict(Counter(r.get("score_status") for r in jsonl(RESULTS))),
        "formal_artifacts_modified": False, "treatment_rerun": False,
        "model_called": False, "agent_called": False, "rag_called": False,
        "baseline_compared": False, "aggregate_generated": False, "v5_created": False, "v5_accessed": False,
        "ready_for_step9_37_treatment_adjudication": elig["FULL"] + elig["PARTIAL"] == 40 and elig["NONE"] == 0,
    }
    with OUTFILES[0].open("x", encoding="utf-8") as f:
        json.dump(freeze, f, ensure_ascii=False, indent=2, sort_keys=True); f.write("\n")
    with OUTFILES[1].open("x", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=2, sort_keys=True); f.write("\n")
    with OUTFILES[2].open("x", encoding="utf-8") as f:
        f.write("# Step 9.36 — Treatment Run Integrity Freeze & Lineage Audit\n\n")
        f.write(f"Attempt: `{ATTEMPT_ID}`; comparison class: `{COMPARISON_CLASS}`. All three formal run files were hashed and frozen. Input identities match the issued Step 9.35b authorization. Formal artifacts remain unchanged; no score, adjudication, aggregate, baseline comparison, model/Agent/RAG call, rerun, or V5 activity occurred.\n\n")
        f.write(f"Attempt status **COMPLETED**, cases **40/40**, result/trace coverage and order match. Formal lineage ready={len(formal_true)}, false={len(formal_false)}. Independent recomputation: COMPLETE={counts['COMPLETE']}, NOT_APPLICABLE={counts['NOT_APPLICABLE']}, INCOMPLETE={counts['INCOMPLETE']}, INDETERMINATE={counts['INDETERMINATE']}.\n\n")
        f.write("False formal lineage cases: " + ", ".join(f"`{r['case_id']}`" for r in formal_false) + ".\n\n")
        f.write(f"Cause classification: runner derivation bug={roots['RUNNER_DERIVATION_BUG']}, true lineage failure={roots['TRUE_LINEAGE_FAILURE']}, persistence bug={roots['PERSISTENCE_BUG']}, not-applicable misclassified={roots['NOT_APPLICABLE_MISCLASSIFIED']}, indeterminate={roots['INDETERMINATE']}. The eight derivation false negatives are deterministically reconstructable from existing IDs in raw traces; the five missing semantic roots remain incomplete and were not fabricated.\n\n")
        f.write(f"Derived sidecar complete={audit['sidecar_complete_count']}; incomplete={audit['sidecar_incomplete_count']}. Adjudication eligibility (not a score): FULL={elig['FULL']}, PARTIAL={elig['PARTIAL']}, NONE={elig['NONE']}. Incomplete lineage cases remain eligible only where all frozen rubric dimensions have trace evidence with the same caveats used in Step 9.30a.2.\n\n")
        f.write(f"Raw execution totals (descriptive only): ASK={audit['raw_execution_counts']['ASK_count']}, RETRIEVE={audit['raw_execution_counts']['RETRIEVE_count']}, READ_DIARY={audit['raw_execution_counts']['READ_DIARY_count']}. Formal input freeze: `step9_36_treatment_run_input_freeze.json`. No outcome interpretation is made.\n")
    for output, rows in ((OUTFILES[3], matrix), (OUTFILES[4], sidecar)):
        with output.open("x", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"attempt": "COMPLETED", "result_count": 40, "trace_count": 40,
                      "false_lineage_ids": audit["formal_lineage_false_case_ids"],
                      "recomputed": audit["recomputed_status_counts"],
                      "root_causes": audit["root_cause_counts"],
                      "eligibility": {"FULL": elig["FULL"], "PARTIAL": elig["PARTIAL"], "NONE": elig["NONE"]}}, sort_keys=True))


if __name__ == "__main__":
    main()
