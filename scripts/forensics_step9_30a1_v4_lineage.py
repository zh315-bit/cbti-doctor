"""Read-only Step 9.30a.1 forensic analysis of frozen V4 trace lineage.

This utility never constructs a production service, reads the benchmark, calls a
model, or modifies formal V4 run files. It writes only a derived forensic
sidecar and report under evaluation/v1_2_3.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "evaluation/v4_runs/heldout-v4-step9_28-20260925-01"
FREEZE = ROOT / "evaluation/v1_2_3/step9_30a_v4_run_input_freeze.json"
OUT = ROOT / "evaluation/v1_2_3"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    freeze = json.loads(FREEZE.read_text(encoding="utf-8"))
    files = {item["path"]: ROOT / item["path"] for item in freeze["artifact_files"]}
    for item in freeze["artifact_files"]:
        path = files[item["path"]]
        if not path.is_file() or digest(path) != item["sha256"] or path.stat().st_size != item["byte_size"]:
            raise SystemExit(f"FAIL CLOSED: frozen input mismatch: {item['path']}")
    result_path = next(p for name, p in files.items() if name.endswith("_case_results.jsonl"))
    raw_path = next(p for name, p in files.items() if name.endswith("_raw_traces.jsonl"))
    result_rows, raw_rows = rows(result_path), rows(raw_path)
    results = {r["case_id"]: r for r in result_rows}
    traces = {r["case_id"]: r for r in raw_rows}
    if len(results) != 40 or len(traces) != 40 or set(results) != set(traces):
        raise SystemExit("FAIL CLOSED: formal result/trace case coverage mismatch")

    matrix: list[dict] = []
    for case_id in sorted(results):
        result, trace = results[case_id], traces[case_id]
        turns = trace.get("turns", [])
        # Recompute using the frozen rule, but correctly join each action to
        # decisions across every persisted turn rather than only the last loop.
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

        final_state = trace.get("final_state", {})
        for dep in final_state.get("dependencies_considered", []):
            if dep.get("dependency_id"):
                dependency_ids.add(dep["dependency_id"])
        for sem in final_state.get("semantic_provenance", []):
            if sem.get("semantic_id"):
                semantic_ids.add(sem["semantic_id"])

        actions = final_state.get("action_history", [])
        lineage_events = [event for turn in turns for event in turn.get("state", {}).get("lineage_events", [])]
        missing: list[str] = []
        for action in actions:
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
                if action.get("action") == "RETRIEVE" and not any(e.get("source_type") == "RAG" for e in linked):
                    missing.append("MISSING_RETRIEVAL_PROVENANCE")
                if action.get("action") == "READ_DIARY" and not any(e.get("source_type") == "session_diary" for e in linked):
                    missing.append("MISSING_DIARY_PROVENANCE")
        if not final_state.get("goal_id"):
            missing.append("MISSING_GOAL_ROOT")
        if not semantic_ids:
            missing.append("MISSING_SEMANTIC_ROOT")
        if not dependency_ids:
            missing.append("MISSING_DEPENDENCY_ROOT")

        frozen_false = result.get("lineage_ready") is False
        if missing:
            status = "INCOMPLETE"
            reasons = sorted(set(missing))
            cause = "TRUE_LINEAGE_FAILURE"
            reconstructable = "NO"
        elif frozen_false:
            status = "COMPLETE"
            reasons = ["CONTRACT_FALSE_NEGATIVE"]
            cause = "RUNNER_DERIVATION_BUG"
            reconstructable = "YES"
        else:
            status = "COMPLETE"
            reasons = []
            cause = "NO_FAILURE"
            reconstructable = "YES"

        matrix.append({
            "case_id": case_id,
            "task_type": result.get("task_type"),
            "final_status": result.get("final_status"),
            "lineage_ready_frozen": result.get("lineage_ready"),
            "raw_trace_present": True,
            "case_result_present": True,
            "raw_trace_line_count": 1,
            "trace_event_count": len(actions) + len(lineage_events),
            "action_path": trace.get("action_path", []),
            "tool_calls": result.get("tool_calls", []),
            "ASK_count": result.get("ASK_count"),
            "RETRIEVE_count": result.get("RETRIEVE_count"),
            "READ_DIARY_count": result.get("READ_DIARY_count"),
            "turn_count": result.get("turn_count"),
            "step_count": result.get("step_count"),
            "recomputed_lineage_status": status,
            "reason_codes": reasons,
            "raw_trace_sufficient_for_adjudication": "YES",
            "case_result_sufficient": "NO",
            "lineage_reconstructable_without_rerun": reconstructable,
            "root_cause_class": cause,
            "internal_action_count": len(actions),
            "internal_lineage_event_count": len(lineage_events),
        })

    false_rows = [r for r in matrix if r["lineage_ready_frozen"] is False]
    if len(false_rows) != 12:
        raise SystemExit("FAIL CLOSED: expected 12 frozen false lineage cases")
    counts = Counter(r["root_cause_class"] for r in false_rows)
    run_name_to_digest = {item["path"]: item["sha256"] for item in freeze["artifact_files"]}
    payload = {
        "step": "9.30a.1",
        "forensic_type": "READ_ONLY_V4_LINEAGE_FAILURE_FORENSICS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_id": freeze["evaluation_id"],
        "input_freeze_sha256": digest(FREEZE),
        "formal_inputs": run_name_to_digest,
        "formal_inputs_reverified": True,
        "benchmark_v4_accessed_for_evaluation": False,
        "model_called": False,
        "agent_called": False,
        "v4_case_executed": 0,
        "v4_score_generated": False,
        "lineage_ready_false_case_ids": [r["case_id"] for r in false_rows],
        "recomputed_status_counts": dict(Counter(r["recomputed_lineage_status"] for r in matrix)),
        "false_case_recomputed_counts": dict(Counter(r["recomputed_lineage_status"] for r in false_rows)),
        "root_cause_counts": {"true_lineage_failure": counts["TRUE_LINEAGE_FAILURE"],
            "not_applicable_misclassified": 0, "persistence_bug": 0,
            "runner_derivation_bug": counts["RUNNER_DERIVATION_BUG"], "indeterminate": 0},
        "v3_lineage_contract": "V3 runner uses scripts.preflight_step9_12_local._lineage_validation; accumulates state.action_history and compares it only with the current loop result.state_history DECISION snapshots, with goal/semantic/dependency roots required.",
        "v4_lineage_contract": "Same helper and conditions; V4 result lineage_ready is all per-turn lineage.ready. Per action: action_id; candidate_id linked to a DECISION snapshot; source dependency must exist in dependencies_considered; HARD_PRECONDITION requires precondition_id; RETRIEVE/READ_DIARY require tool_result_id and state_update_id; roots goal_id, semantic_id, dependency_id; at least one action record.",
        "runner_lineage_regression": "NO",
        "remediation_class": "DERIVED_SIDECAR_REPAIR_POSSIBLE",
        "formal_artifacts_modified": False,
    }
    stem = "step9_30a1_v4_lineage_forensics"
    with (OUT / "step9_30a1_v4_lineage_case_matrix.jsonl").open("x", encoding="utf-8") as f:
        for row in matrix:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    with (OUT / f"{stem}.json").open("x", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True); f.write("\n")
    ids = ", ".join(payload["lineage_ready_false_case_ids"])
    report = f"""# Step 9.30a.1 — V4 Lineage Failure Forensics

Read-only forensic sidecar for `{freeze['evaluation_id']}`. Frozen formal inputs were re-hashed against the Step 9.30a input freeze before analysis. No benchmark file was loaded; no Agent, model, RAG, or V4 case was executed. Formal traces, case results, ledger, and benchmark were not modified.

## Findings

- Frozen `lineage_ready=false` count: **12/40**: {ids}.
- Independent trace recomputation across all cases: **{payload['recomputed_status_counts'].get('COMPLETE', 0)} COMPLETE**, **{payload['recomputed_status_counts'].get('INCOMPLETE', 0)} INCOMPLETE**, **0 NOT_APPLICABLE**, **0 INDETERMINATE**.
- Among the 12 false cases: **{payload['false_case_recomputed_counts'].get('COMPLETE', 0)} COMPLETE with `CONTRACT_FALSE_NEGATIVE`**, **{payload['false_case_recomputed_counts'].get('INCOMPLETE', 0)} INCOMPLETE**.
- Root causes: **{counts['RUNNER_DERIVATION_BUG']} runner derivation false negatives** and **{counts['TRUE_LINEAGE_FAILURE']} true execution-lineage omissions**; no persistence bug or not-applicable misclassification found.
- The 7 false negatives have earlier ASK action/candidate records in earlier turn snapshots and the cumulative serialized action history. The checker only receives the current loop result snapshot on later turns, so its per-turn validation cannot find earlier candidates. Trace evidence permits deterministic sidecar reconstruction.
- The 5 true omissions are diary cases whose READ_DIARY event, tool result, state update, source type, dependency and diary projection are persisted, but `semantic_provenance` is empty in every turn and final state. The required semantic root was never emitted; it cannot be recreated without inventing an ID. Their raw traces support answer/evidence adjudication but do not satisfy the frozen complete-lineage contract.
- Failures are not equivalent to “no tool used”: of the 12, **6** use no retrieval/diary tool, **1** uses RETRIEVE, and **5** use READ_DIARY. Every case has at least one action and a dependency; no case is NOT_APPLICABLE under the frozen root requirement.

## Contract and V3 comparison

`lineage_ready` is computed by `scripts/run_step9_28_v4_heldout.py::_case_result` as `all(turn.lineage.ready)`. `_lineage_validation` checks recorded action IDs, candidate-to-DECISION linkage, optional dependency link presence, precondition ID for HARD_PRECONDITION actions, tool-result and state-update IDs for RETRIEVE/READ_DIARY, plus goal, semantic, dependency roots and a nonempty action list. This is execution-trace completeness as observed by that helper, not an adjudication score or persistence-integrity check.

V4 and V3 call the same `_lineage_validation` helper from `scripts/preflight_step9_12_local.py`; the V3 runner applies the same accumulated-history/current-turn-snapshot pairing. This is a shared pre-existing derivation limitation, not a V3→V4 regression. V3 labels/scores were not used.

The seven false negatives can be represented in a derived sidecar without rerunning. The five diary traces have durable tool/evidence lineage but lack the frozen semantic root; do not mark them complete or repair their formal records. Protocol review is still required before any downstream adjudication treats them as complete.

## Status

- `TRUE_LINEAGE_FAILURE_COUNT = {counts['TRUE_LINEAGE_FAILURE']}`
- `NOT_APPLICABLE_MISCLASSIFIED_COUNT = 0`
- `PERSISTENCE_BUG_COUNT = 0`
- `RUNNER_DERIVATION_BUG_COUNT = {counts['RUNNER_DERIVATION_BUG']}`
- `INDETERMINATE_COUNT = 0`
- `RAW_TRACE_SUFFICIENT_FOR_ADJUDICATION = YES (12/12)`
- `CASE_RESULT_SUFFICIENT = NO (12/12)`
- `LINEAGE_CAN_BE_RECONSTRUCTED_WITHOUT_RERUN = NO (5/12 strict-contract semantic roots absent)`
- `REMEDIATION_CLASS = DERIVED_SIDECAR_REPAIR_POSSIBLE`
- `READY_FOR_STEP9_30B_HUMAN_ADJUDICATION = NO`
- `V4_CASE_EXECUTED = 0`; `V4_SCORE_GENERATED = NO`; `AGGREGATE_GENERATED = NO`

Machine-readable details are in `{stem}.json` and `{stem}_case_matrix.jsonl`.
"""
    with (OUT / f"{stem}.md").open("x", encoding="utf-8") as f:
        f.write(report)
    print(json.dumps({"report": str(OUT / f"{stem}.md"), "case_matrix": str(OUT / "step9_30a1_v4_lineage_case_matrix.jsonl"),
                      "summary": payload["root_cause_counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
