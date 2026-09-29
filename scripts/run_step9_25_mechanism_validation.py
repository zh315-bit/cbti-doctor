"""Run synthetic Step 9.25 mechanism checks without model or benchmark access."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evaluation" / "v1_2_3"
FREEZE_PATH = OUT / "step9_24_candidate_freeze.json"
CASES_PATH = OUT / "step9_25_mechanism_cases.yaml"

sys.path.insert(0, str(ROOT))
from adaptive_agent.acquisition_gate import gate_acquisition_candidates  # noqa: E402
from adaptive_agent.candidates import generate_candidates  # noqa: E402
from adaptive_agent.dependency_resolver import DependencyResolver  # noqa: E402
from adaptive_agent.policy import HeuristicDecisionPolicy  # noqa: E402
from adaptive_agent.requirements import RequirementSet, synchronize_requirements  # noqa: E402
from adaptive_agent.state import ActionCandidate, AdaptiveAgentState, TaskType  # noqa: E402
from adaptive_agent.sufficiency import SufficiencyEstimator  # noqa: E402


def _hash(path: str, expected: str) -> str:
    if path.startswith("runtime:"):
        return expected
    if path == "rag_lib/pdfs/":
        entries = []
        for item in sorted((ROOT / "rag_lib" / "pdfs").glob("*")):
            if item.is_file() and not item.name.startswith("._"):
                entries.append(f"{hashlib.sha256(item.read_bytes()).hexdigest()}  {item.relative_to(ROOT)}\n")
        return hashlib.sha256("".join(entries).encode()).hexdigest()
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def verify_freeze() -> dict:
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    source18 = json.loads((OUT / "step9_18_candidate_freeze.json").read_text(encoding="utf-8"))
    source23 = json.loads((OUT / "step9_23a_candidate_freeze.json").read_text(encoding="utf-8"))
    rows = dict(source18["agent_behavior_files"])
    rows.update(dict(source23["authorized_divergence"]["changed_agent_files"]))
    rows.update(dict(freeze["authorized_divergence"]["changed_agent_files"]))
    aggregate = hashlib.sha256("".join(f"{key}\t{value}\n" for key, value in sorted(rows.items())).encode()).hexdigest()
    return {
        "freeze_id": freeze["freeze_id"],
        "inventory_count": len(rows),
        "inventory_matches_manifest": len(rows) == freeze["effective_agent_file_count"] and aggregate == freeze["agent_aggregate_hash"],
        "all_inventory_files_match": all(_hash(path, digest) == digest for path, digest in rows.items()),
        "benchmark_v2_rerun": False,
        "benchmark_v3_accessed": False,
    }


def _candidate(spec: dict) -> ActionCandidate:
    return ActionCandidate(
        action=spec["action"], target=spec.get("target"), query=spec.get("query"),
        expected_benefit=spec.get("expected_benefit", "LOW"), cost=spec.get("cost", "LOW"),
        rationale=spec.get("rationale", "synthetic validation candidate"),
        origin=spec.get("origin", "OPTIONAL_ACQUISITION"),
        source_precondition_id=spec.get("source_precondition_id"),
    )


def run_case(spec: dict) -> dict:
    req_data = spec.get("requirements", {})
    requirements = RequirementSet(
        tuple(req_data.get("critical", ())), tuple(req_data.get("secondary", ())),
        bool(req_data.get("evidence_required", False)), resources=tuple(req_data.get("resources", ())),
        decision_fields=tuple(req_data["decision_fields"]) if "decision_fields" in req_data else None,
    )
    diary = spec.get("diary", {})
    state = AdaptiveAgentState(
        goal=spec["goal"], task_type=TaskType(spec["task_type"]), facts=spec.get("facts", {}),
        goal_id=f"synthetic_{spec['case_id'].lower().replace('-', '_')}",
        action_history=spec.get("action_history", []),
        available_diary=bool(diary.get("available", False)),
        diary_available=diary.get("available"), diary_authorized=diary.get("authorized"),
        resource_status={"sleep_diary": diary.get("status", "unread")} if diary else {},
    )
    estimator = SufficiencyEstimator()
    estimator.update(state, requirements)
    dependencies = DependencyResolver().resolve(state, requirements)
    state.dependencies_considered = [item.to_dict() for item in dependencies]
    requirements = synchronize_requirements(requirements, state, dependencies)
    estimator.update(state, requirements)

    if "candidate_overrides" in spec:
        raw_candidates = [_candidate(item) for item in spec["candidate_overrides"]]
    else:
        raw_candidates = generate_candidates(state, requirements)
    candidates = gate_acquisition_candidates(state, requirements, raw_candidates)
    state.candidate_actions = candidates
    selected = HeuristicDecisionPolicy().choose(state)
    observed_action = selected.action
    expected_action = spec["expected_action"]
    acquisition_record = next((item for item in state.acquisition_decisions
                               if item.get("target") == spec.get("missing_target")), None)
    if acquisition_record is None and selected.target == spec.get("missing_target"):
        acquisition_record = {"accepted": selected.gate_decision != "REJECT",
                              "gate_decision": selected.gate_decision or "PRECONDITION",
                              "expected_information_gain": selected.information_value or selected.expected_benefit,
                              "reason": selected.gate_reason or selected.rationale}
    return {
        "case_id": spec["case_id"], "group": spec["group"], "pair_id": spec.get("pair_id"),
        "expected_action": expected_action, "observed_action": observed_action,
        "expected_value": spec.get("expected_value"),
        "observed_value": acquisition_record.get("expected_information_gain") if acquisition_record else None,
        "expected_gate": spec.get("expected_gate"),
        "observed_gate": acquisition_record.get("gate_decision") if acquisition_record else None,
        "selected_target": selected.target,
        "selected_origin": selected.origin,
        "action_path": [observed_action],
        "dependencies": [item.to_dict() for item in dependencies],
        "preconditions": state.preconditions_considered,
        "acquisition_decisions": state.acquisition_decisions,
        "rejected_information": state.rejected_information,
        "stop_reason": state.stop_reason,
        "match": observed_action == expected_action
                 and (spec.get("expected_value") is None or acquisition_record is None
                      or acquisition_record.get("expected_information_gain") == spec.get("expected_value"))
                 and (spec.get("expected_gate") is None or acquisition_record is None
                      or acquisition_record.get("gate_decision") == spec.get("expected_gate")),
        "rationale": spec["rationale"],
    }


def main() -> int:
    freeze_audit = verify_freeze()
    if not freeze_audit["inventory_matches_manifest"] or not freeze_audit["all_inventory_files_match"]:
        print(json.dumps({"freeze_audit": freeze_audit, "status": "BLOCKED_FREEZE_MISMATCH"}, indent=2))
        return 2
    cases = yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))["cases"]
    results = [run_case(case) for case in cases]
    pairs: dict[str, list[dict]] = {}
    for result in results:
        if result["pair_id"]:
            pairs.setdefault(result["pair_id"], []).append(result)
    counterfactual_pairs = []
    for pair_id, pair_results in sorted(pairs.items()):
        counterfactual_pairs.append({"pair_id": pair_id, "cases": pair_results,
                                     "action_differs": len({item["observed_action"] for item in pair_results}) > 1,
                                     "interpretation": "同一 caffeine target 在描述 goal 与决策 goal 下的价值/行动差异"})
    hard_case_ids = {item["case_id"] for item in cases if item.get("expected_origin") == "HARD_PRECONDITION"}
    low_ask_records = [(case, record) for case in results if case["case_id"] not in hard_case_ids
                       for record in case["acquisition_decisions"]
                       if record.get("action") == "ASK" and record.get("expected_information_gain") in {"LOW", "NONE"}]
    necessary_asks = [item for item in cases if item.get("expected_origin") == "HARD_PRECONDITION"
                      and item["expected_action"] == "ASK"]
    necessary = [item for item in cases if item.get("expected_origin") == "HARD_PRECONDITION"
                 and item["expected_action"] in {"ASK", "RETRIEVE", "READ_DIARY"}]
    result_by_id = {item["case_id"]: item for item in results}
    low_suppressed = sum(not record.get("accepted") for _, record in low_ask_records)
    low_value_ask_accepted = sum(bool(record.get("accepted")) for _, record in low_ask_records)
    necessary_preserved = sum(result_by_id[item["case_id"]]["observed_action"] == item["expected_action"] for item in necessary)
    necessary_ask_preserved = sum(result_by_id[item["case_id"]]["observed_action"] == "ASK" for item in necessary_asks)
    decision_relevant_asks = [item for item in cases if item["expected_action"] == "ASK"]
    decision_relevant_asks_preserved = sum(result_by_id[item["case_id"]]["observed_action"] == "ASK" for item in decision_relevant_asks)
    expected_retrieve = [item for item in cases if item["expected_action"] == "RETRIEVE"]
    expected_diary = [item for item in cases if item["expected_action"] == "READ_DIARY"]
    metrics = {
        "case_count": len(results), "passed": sum(item["match"] for item in results),
        "failed": sum(not item["match"] for item in results),
        "low_value_ask_suppression_rate": low_suppressed / len(low_ask_records) if low_ask_records else None,
        "low_value_ask_candidate_count": len(low_ask_records),
        "low_value_ask_accepted_total": low_value_ask_accepted,
        "low_value_ask_per_case": low_value_ask_accepted / len(results),
        "necessary_ask_preservation_rate": necessary_ask_preserved / len(necessary_asks) if necessary_asks else None,
        "necessary_ask_case_count": len(necessary_asks),
        "decision_relevant_ask_preservation_rate": decision_relevant_asks_preserved / len(decision_relevant_asks) if decision_relevant_asks else None,
        "decision_relevant_ask_case_count": len(decision_relevant_asks),
        "hard_precondition_acquisition_preservation_rate": necessary_preserved / len(necessary) if necessary else None,
        "hard_precondition_acquisition_case_count": len(necessary),
        "under_acquisition_failures": sum(result_by_id[item["case_id"]]["observed_action"] != item["expected_action"] for item in cases if item["expected_action"] in {"ASK", "RETRIEVE", "READ_DIARY"}),
        "hard_precondition_violations": sum(item.get("expected_origin") == "HARD_PRECONDITION" and item["observed_action"] != item["expected_action"] for item in results),
        "retrieve_required_preservation_rate": sum(result_by_id[item["case_id"]]["observed_action"] == "RETRIEVE" for item in expected_retrieve) / len(expected_retrieve) if expected_retrieve else None,
        "read_diary_required_preservation_rate": sum(result_by_id[item["case_id"]]["observed_action"] == "READ_DIARY" for item in expected_diary) / len(expected_diary) if expected_diary else None,
        "ask_per_case": sum(item["observed_action"] == "ASK" for item in results) / len(results),
        "planned_retrieve_actions": sum(item["observed_action"] == "RETRIEVE" for item in results),
        "planned_read_diary_actions": sum(item["observed_action"] == "READ_DIARY" for item in results),
        "planned_tool_actions_per_case": sum(item["observed_action"] in {"RETRIEVE", "READ_DIARY"} for item in results) / len(results),
        "tool_calls_per_case": "NOT_MEASURED; tool actions are selected, not executed",
        "pre_p2_baseline_available": False,
        "pre_p2_mechanism_improvement": "NOT_MEASURED",
        "steps_turns_latency_tokens": "NOT_MEASURED; one synthetic decision evaluation per case, no loop/API/model timing",
    }
    payload = {"freeze_audit": freeze_audit, "metrics": metrics, "cases": results,
               "counterfactual_pairs": counterfactual_pairs,
               "agent_modified": False, "benchmark_v3_rerun": False,
               "v3_results_modified": False, "model_called": False}
    (OUT / "step9_25_mechanism_results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "step9_25_counterfactual_pairs.json").write_text(json.dumps(counterfactual_pairs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"freeze_audit": freeze_audit, "metrics": metrics}, ensure_ascii=False, indent=2))
    return 0 if metrics["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
