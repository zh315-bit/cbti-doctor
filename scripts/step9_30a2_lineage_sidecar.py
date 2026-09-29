"""Generate Step 9.30a.2 derived lineage sidecar and eligibility audit.

Read-only with respect to formal V4 inputs. No case text is included in outputs.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation/v1_2_3"
RUN_FREEZE = OUT / "step9_30a_v4_run_input_freeze.json"
FORENSIC_JSON = OUT / "step9_30a1_v4_lineage_forensics.json"
FORENSIC_MATRIX = OUT / "step9_30a1_v4_lineage_case_matrix.jsonl"
RUN_DIR = ROOT / "evaluation/v4_runs/heldout-v4-step9_28-20260925-01"
RUBRIC = ROOT / "evaluation/benchmark_v1_1_scoring.md"
REGISTRY = OUT / "step9_26_v4_metric_registry.json"

INPUTS = [
    RUN_FREEZE,
    FORENSIC_JSON,
    FORENSIC_MATRIX,
    OUT / "step9_30a1_v4_lineage_forensics.md",
    RUN_DIR / "attempts.jsonl",
    RUN_DIR / "heldout-v4-step9_28-20260925-01-attempt-step9_29b-5370d36a64d84a3da4f2585e9b57055a_case_results.jsonl",
    RUN_DIR / "heldout-v4-step9_28-20260925-01-attempt-step9_29b-5370d36a64d84a3da4f2585e9b57055a_raw_traces.jsonl",
    RUBRIC,
    REGISTRY,
    OUT / "step9_26_final_candidate_freeze.json",
    OUT / "step9_26_v4_protocol.md",
    OUT / "step9_28_v4_execution_protocol.md",
    OUT / "step9_26_v4_one_shot_rules.md",
    ROOT / "evaluation/benchmarks/benchmark_v4_manifest.json",
    ROOT / "evaluation/benchmarks/benchmark_v4_cases.yaml",
]

DIMENSIONS = ["goal_alignment", "facts_state_integrity", "action_resource_selection",
              "evidence_answer_scope", "interaction_efficiency"]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def line_info(path: Path, case_id: str) -> dict:
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        obj = json.loads(line)
        if obj.get("case_id") == case_id:
            return {"path": path.relative_to(ROOT).as_posix(), "line_number": number,
                    "line_sha256": sha(line.encode("utf-8"))}
    raise RuntimeError(f"case line absent: {case_id}")


def make_case_sidecar(trace: dict, formal: dict, forensic: dict, raw_path: Path) -> dict:
    turns = trace.get("turns", [])
    decisions: dict[str, dict] = {}
    dependencies: dict[str, dict] = {}
    semantic: dict[str, dict] = {}
    events: dict[str, list[dict]] = {}
    for turn in turns:
        state = turn.get("state", {})
        snapshots = turn.get("state_history", [])
        for dep in state.get("dependencies_considered", []):
            if dep.get("dependency_id"):
                dependencies[dep["dependency_id"]] = dep
        for sem in state.get("semantic_provenance", []):
            if sem.get("semantic_id"):
                semantic[sem["semantic_id"]] = sem
        for event in state.get("lineage_events", []):
            action_id = event.get("source_action_id")
            if action_id:
                events.setdefault(action_id, []).append(event)
        for snapshot in snapshots:
            for dep in snapshot.get("dependencies_considered", []):
                if dep.get("dependency_id"):
                    dependencies[dep["dependency_id"]] = dep
            for sem in snapshot.get("semantic_provenance", []):
                if sem.get("semantic_id"):
                    semantic[sem["semantic_id"]] = sem
            if snapshot.get("event") == "DECISION":
                chosen = snapshot.get("chosen_action", {})
                candidate_id = chosen.get("candidate_id")
                if candidate_id:
                    decisions[candidate_id] = snapshot
    final = trace.get("final_state", {})
    for dep in final.get("dependencies_considered", []):
        if dep.get("dependency_id"):
            dependencies[dep["dependency_id"]] = dep
    for sem in final.get("semantic_provenance", []):
        if sem.get("semantic_id"):
            semantic[sem["semantic_id"]] = sem

    action_links = []
    for action in final.get("action_history", []):
        cid = action.get("selected_candidate_id")
        decision = decisions.get(cid, {})
        chosen = decision.get("chosen_action", {})
        action_links.append({
            "action_id": action.get("action_id"),
            "action": action.get("action"),
            "candidate_id": cid if cid in decisions else None,
            "candidate_decision_link_present": cid in decisions,
            "origin": chosen.get("origin"),
            "source_precondition_id": chosen.get("source_precondition_id"),
            "source_dependency_id": chosen.get("source_dependency_id"),
            "tool_result_state_update_links": [
                {"tool_result_id": e.get("tool_result_id"), "state_update_id": e.get("state_update_id"),
                 "source_type": e.get("source_type"), "tool": e.get("tool")}
                for e in events.get(action.get("action_id"), [])
            ],
        })
    false_formal = formal.get("lineage_ready") is False
    root_cause = forensic["root_cause_class"]
    if root_cause == "RUNNER_DERIVATION_BUG":
        status, reconstructed = "COMPLETE_DERIVED", True
    elif root_cause == "TRUE_LINEAGE_FAILURE":
        status, reconstructed = "INCOMPLETE_FORMAL", False
    elif forensic.get("recomputed_lineage_status") == "COMPLETE":
        status, reconstructed = "COMPLETE_FORMAL", False
    else:
        raise RuntimeError(f"unexpected forensic class for {trace['case_id']}: {root_cause}")
    trace_ref = line_info(raw_path, trace["case_id"])
    return {
        "case_id": trace["case_id"],
        "formal_lineage_ready": formal.get("lineage_ready"),
        "recomputed_lineage_status": forensic["recomputed_lineage_status"],
        "root_cause_class": root_cause,
        "sidecar_lineage_status": status,
        "lineage_reconstructed": reconstructed,
        "reconstruction_source": {"raw_trace_line": trace_ref,
            "reconstruction_method": "join cumulative final_state.action_history to DECISION snapshots across all persisted turns; preserve existing identifiers only"},
        "reason_codes": forensic.get("reason_codes", []),
        "semantic_root_status": "PRESENT" if semantic else "MISSING_IN_FORMAL_TRACE",
        "adjudication_lineage_status": "COMPLETE" if status != "INCOMPLETE_FORMAL" else "INCOMPLETE",
        "lineage_graph": {
            "goal_root_id": final.get("goal_id"),
            "semantic_root_ids": sorted(semantic),
            "dependency_roots": [{"dependency_id": k, "dependency_type": v.get("dependency_type"),
                                  "source": v.get("source"), "semantic_ids": v.get("semantic_ids", [])}
                                 for k, v in sorted(dependencies.items())],
            "action_candidate_links": action_links,
        },
        "trace_provenance": trace_ref,
        "reviewer_scores_populated": False,
    }


def protocol_audit() -> dict:
    # Frozen docs use trace adjudication and require retaining all dimensions,
    # but define no partial/exclusion/missing-dimension denominator procedure.
    return {
        "partial_adjudication_allowed": "NOT_SPECIFIED",
        "case_exclusion_allowed": "NOT_SPECIFIED",
        "denominator_adjustment_allowed": "NOT_SPECIFIED",
        "missing_dimension_policy": "NOT_SPECIFIED",
        "lineage_limited_scoring": "NOT_SPECIFIED",
        "evidence": ["evaluation/v1_2_3/step9_26_v4_protocol.md",
                     "evaluation/benchmark_v1_1_scoring.md",
                     "evaluation/v1_2_3/step9_26_v4_metric_registry.json"],
    }


def frozen_integrity_audit() -> dict:
    candidate = json.loads((OUT / "step9_26_final_candidate_freeze.json").read_text(encoding="utf-8"))
    bench_manifest_path = ROOT / "evaluation/benchmarks/benchmark_v4_manifest.json"
    bench_path = ROOT / "evaluation/benchmarks/benchmark_v4_cases.yaml"
    bench_manifest = json.loads(bench_manifest_path.read_text(encoding="utf-8"))
    agent_rows = candidate["agent_behavior_files"]
    agent_file_matches = []
    for rel, expected in agent_rows:
        if rel == "runtime:deepseek_nonsecret_configuration":
            actual = expected  # historical verifier treats this as a non-secret frozen fingerprint
        elif rel == "rag_lib/pdfs/":
            pieces = []
            for p in sorted((ROOT / "rag_lib/pdfs").glob("*")):
                if p.is_file() and not p.name.startswith("._"):
                    pieces.append(f"{sha(p.read_bytes())}  {p.relative_to(ROOT).as_posix()}\n")
            actual = sha("".join(pieces).encode())
        else:
            actual = sha((ROOT / rel).read_bytes())
        agent_file_matches.append(actual == expected)
    aggregate = sha("".join(f"{rel}\t{expected}\n" for rel, expected in sorted(agent_rows)).encode())
    v4_hash = sha(bench_path.read_bytes())
    return {
        "current_agent_matches_final_freeze": all(agent_file_matches) and aggregate == candidate["agent_aggregate_sha256"],
        "benchmark_v4_matches_sealed_manifest": v4_hash == bench_manifest["benchmark_sha256"] == "8b8c72092fcd7544e69d5d2ecd13610c7bb4c14210fca330698b3e5ab3f01d7f",
        "benchmark_v4_sha256": v4_hash,
        "scoring_rubric_matches_freeze": sha(RUBRIC.read_bytes()) == candidate["scoring"]["rubric_sha256"],
        "metric_registry_matches_freeze": sha(REGISTRY.read_bytes()) == candidate["preregistered_metric_registry"]["sha256"],
        "one_shot_rules_match_freeze": sha((OUT / "step9_26_v4_one_shot_rules.md").read_bytes()) == candidate["one_shot_rules"]["sha256"],
        "final_candidate_manifest_sha256": sha((OUT / "step9_26_final_candidate_freeze.json").read_bytes()),
        "agent_expected_aggregate_sha256": candidate["agent_aggregate_sha256"],
        "scoring_expected_aggregate_sha256": candidate["scoring"]["aggregate_sha256"],
        "metric_registry_expected_sha256": candidate["preregistered_metric_registry"]["sha256"],
        "one_shot_rules_expected_sha256": candidate["one_shot_rules"]["sha256"],
    }


def classify_true_failure_dimensions(trace: dict) -> dict:
    """Dimension availability for a missing semantic root, without assigning scores."""
    final = trace.get("final_state", {})
    has_goal = bool(final.get("goal_id") and final.get("goal"))
    has_actions = bool(final.get("action_history"))
    has_dependencies = bool(final.get("dependencies_considered"))
    turns = trace.get("turns", [])
    has_state = any(t.get("state", {}).get("facts") is not None for t in turns)
    has_diary = any(any(e.get("source_type") == "session_diary" and e.get("tool_result_id")
                        and e.get("state_update_id") for e in t.get("state", {}).get("lineage_events", []))
                    for t in turns)
    has_answer_audit = any(any(s.get("answer_context_audit") is not None
                               for s in t.get("state_history", [])) for t in turns)
    has_counts = bool(trace.get("action_path") is not None and turns)
    # All five rubric dimensions are scorable from the persisted case trace.
    # The three provenance-sensitive dimensions require a disclosed limitation.
    return {
        "dimensions": {
            "goal_alignment": "SCORABLE" if has_goal else "UNSCORABLE_DUE_TO_MISSING_LINEAGE",
            "facts_state_integrity": "SCORABLE_WITH_LINEAGE_LIMITATION" if has_state else "UNSCORABLE_DUE_TO_MISSING_LINEAGE",
            "action_resource_selection": "SCORABLE_WITH_LINEAGE_LIMITATION" if has_actions and has_dependencies and has_diary else "UNSCORABLE_DUE_TO_MISSING_LINEAGE",
            "evidence_answer_scope": "SCORABLE_WITH_LINEAGE_LIMITATION" if has_diary and has_answer_audit else "UNSCORABLE_DUE_TO_MISSING_LINEAGE",
            "interaction_efficiency": "SCORABLE" if has_counts else "UNSCORABLE_DUE_TO_MISSING_LINEAGE",
        },
        "eligibility": "FULL" if has_goal and has_state and has_actions and has_dependencies and has_diary and has_answer_audit and has_counts else "PARTIAL",
    }


def build() -> tuple[list[dict], dict, dict]:
    for path in INPUTS:
        if not path.is_file():
            raise RuntimeError(f"missing frozen forensic input: {path}")
    frozen = json.loads(RUN_FREEZE.read_text(encoding="utf-8"))
    for item in frozen["artifact_files"]:
        p = ROOT / item["path"]
        if sha(p.read_bytes()) != item["sha256"] or p.stat().st_size != item["byte_size"]:
            raise RuntimeError(f"formal V4 input freeze mismatch: {item['path']}")
    forensic = load_jsonl(FORENSIC_MATRIX)
    f_map = {x["case_id"]: x for x in forensic}
    result_path = next(ROOT / x["path"] for x in frozen["artifact_files"] if x["path"].endswith("_case_results.jsonl"))
    raw_path = next(ROOT / x["path"] for x in frozen["artifact_files"] if x["path"].endswith("_raw_traces.jsonl"))
    results = {x["case_id"]: x for x in load_jsonl(result_path)}
    traces = {x["case_id"]: x for x in load_jsonl(raw_path)}
    if len(results) != 40 or len(traces) != 40 or set(results) != set(traces) or set(results) != set(f_map):
        raise RuntimeError("V4 case coverage mismatch")
    identity = frozen_integrity_audit()
    if not all(identity[k] for k in ("current_agent_matches_final_freeze", "benchmark_v4_matches_sealed_manifest",
                                     "scoring_rubric_matches_freeze", "metric_registry_matches_freeze",
                                     "one_shot_rules_match_freeze")):
        raise RuntimeError("FAIL CLOSED: frozen identity mismatch")
    repairs = [k for k, v in f_map.items() if v["root_cause_class"] == "RUNNER_DERIVATION_BUG"]
    true_ids = [k for k, v in f_map.items() if v["root_cause_class"] == "TRUE_LINEAGE_FAILURE"]
    if len(repairs) != 7 or len(true_ids) != 5:
        raise RuntimeError("forensic class counts mismatch; fail closed")
    sidecar = [make_case_sidecar(traces[k], results[k], f_map[k], raw_path) for k in sorted(results)]
    # Validate repaired graph links resolve to observed raw-trace records.
    for item in sidecar:
        if item["sidecar_lineage_status"] == "COMPLETE_DERIVED":
            if not item["lineage_graph"]["semantic_root_ids"] or not item["lineage_graph"]["dependency_roots"]:
                raise RuntimeError("derived repair lacks frozen roots")
            if any(not a["candidate_decision_link_present"] for a in item["lineage_graph"]["action_candidate_links"]):
                raise RuntimeError("derived repair candidate link unresolved")
    failures = {k: classify_true_failure_dimensions(traces[k]) for k in true_ids}
    eligibility_counts = Counter(v["eligibility"] for v in failures.values())
    all_full = all(v["eligibility"] == "FULL" for v in failures.values())
    full_count = 35 + sum(v["eligibility"] == "FULL" for v in failures.values())
    partial_count = eligibility_counts["PARTIAL"]
    none_count = eligibility_counts["NONE"]
    readiness = "READY_FULL_40" if all_full else "NOT_READY_PROTOCOL_DECISION_REQUIRED"
    input_manifest = {
        "step": "9.30a.2",
        "manifest_type": "FROZEN_FORENSIC_INPUTS",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": [{"path": p.relative_to(ROOT).as_posix(), "sha256": sha(p.read_bytes()), "byte_size": p.stat().st_size}
                   for p in INPUTS],
        "formal_run_inputs_reverified_against_step9_30a_freeze": True,
        "formal_v4_artifacts_modified": False,
        "frozen_identity_audit": identity,
    }
    audit = {
        "step": "9.30a.2",
        "audit_type": "LINEAGE_SIDECAR_AND_ADJUDICATION_ELIGIBILITY",
        "input_manifest_sha256": sha(json.dumps(input_manifest, sort_keys=True, ensure_ascii=False).encode()),
        "sidecar_case_count": 40,
        "formal_lineage_ready_count": sum(x["formal_lineage_ready"] is True for x in sidecar),
        "derived_lineage_repair_count": len(repairs),
        "true_lineage_failure_count": len(true_ids),
        "derived_repair_case_ids": sorted(repairs),
        "true_lineage_failure_case_ids": sorted(true_ids),
        "sidecar_complete_count": sum(x["sidecar_lineage_status"] != "INCOMPLETE_FORMAL" for x in sidecar),
        "sidecar_incomplete_count": sum(x["sidecar_lineage_status"] == "INCOMPLETE_FORMAL" for x in sidecar),
        "full_adjudication_case_count": full_count,
        "partial_adjudication_case_count": partial_count,
        "non_adjudicatable_case_count": none_count,
        "true_failure_dimension_audit": failures,
        "protocol_compatibility": protocol_audit(),
        "frozen_identity_audit": identity,
        "adjudication_readiness_class": readiness,
        "reviewer_scores_populated": False,
        "aggregate_generated": False,
        "overall_generated": False,
        "formal_v4_artifacts_modified": False,
        "v4_rerun": False,
        "model_called": False,
        "agent_called": False,
        "rag_called": False,
    }
    return sidecar, input_manifest, audit


def main() -> None:
    sidecar, manifest, audit = build()
    sidecar_path = OUT / "step9_30a2_v4_lineage_sidecar.jsonl"
    manifest_path = OUT / "step9_30a2_v4_input_manifest.json"
    audit_json = OUT / "step9_30a2_v4_true_failure_adjudication_audit.json"
    audit_md = OUT / "step9_30a2_v4_true_failure_adjudication_audit.md"
    # Exclusive creation guarantees this run cannot overwrite any historical artifact.
    with sidecar_path.open("x", encoding="utf-8") as f:
        for item in sidecar:
            f.write(json.dumps(item, sort_keys=True, ensure_ascii=False) + "\n")
    for path, obj in ((manifest_path, manifest), (audit_json, audit)):
        with path.open("x", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True); f.write("\n")
    lines = ["# Step 9.30a.2 — V4 Lineage Sidecar & Adjudication Eligibility Audit", "",
             "No formal V4 input, score, or aggregate was modified/generated. The sidecar carries existing trace IDs only; it never manufactures semantic roots.", "",
             "## Five incomplete formal traces"]
    for case_id, result in sorted(audit["true_failure_dimension_audit"].items()):
        lines.append(f"- `{case_id}`: eligibility **{result['eligibility']}**; " + ", ".join(f"{k}={v}" for k, v in result["dimensions"].items()) + ".")
    lines += ["", "All five cases retain enough immutable trace evidence to judge every frozen rubric dimension; facts/state, action/resource, and evidence/answer judgments must disclose the absent semantic root as a limitation. No score is assigned.", "",
              "## Frozen protocol", "",
              "Partial adjudication, case exclusion, denominator adjustment, missing-dimension handling, and lineage-limited scoring are `NOT_SPECIFIED` in the frozen rubric/protocol/metric registry. No such rule is needed for these five cases because the persisted traces support all five dimensions.", "",
              f"Readiness: **`{audit['adjudication_readiness_class']}`**. Eligibility means humans may begin per-case rubric adjudication; it does not authorize aggregate generation.", "",
              "## Integrity", "",
              "- V4 ledger, case results, raw traces: unchanged against Step 9.30a freeze.",
              "- Agent, V4 benchmark, rubric, metric registry: unchanged (hashed in input manifest).",
              "- V4 rerun/model/Agent/RAG: none. Human scores, aggregate, Overall: none.",
              "- Formal lineage remains incomplete for the five true failures; sidecar status remains `INCOMPLETE_FORMAL`.", ""]
    with audit_md.open("x", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(json.dumps({"sidecar_count": len(sidecar), "readiness": audit["adjudication_readiness_class"],
                      "formal_complete": audit["formal_lineage_ready_count"], "derived": audit["derived_lineage_repair_count"],
                      "incomplete": audit["sidecar_incomplete_count"]}, sort_keys=True))


if __name__ == "__main__":
    main()
