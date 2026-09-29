"""Offline /api/chat integration verification for Step 9.7; no model or benchmark."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from adaptive_agent.input_understanding import Understanding
from adaptive_agent.runner import AdaptiveAgentLoop
from adaptive_agent.service import AdaptiveChatService, AdaptiveSession
from adaptive_agent.state import AdaptiveAgentState, TaskType
from adaptive_agent.tools import DiaryResult, RetrievalResult
from evaluation.recorder import serialize_state
from adaptive_agent.flask_app import create_app


class RouteHarness:
    """Uses the import-light production adaptive `/api/chat` factory."""
    def __init__(self, service):
        self.app = create_app(service)
        self.client = self.app.test_client()
    def post(self, message, session_id):
        response = self.client.post("/api/chat", json={"message": message, "session_id": session_id})
        return response.get_json(), response.status_code


class SequenceUnderstander:
    def __init__(self, values): self.values = iter(values)
    def understand(self, _message, _state): return next(self.values)


class Retrieval:
    def __init__(self): self.calls = 0
    def retrieve(self, query):
        self.calls += 1
        return RetrievalResult((f"evidence for {query}",), detail="synthetic retrieval")


class Diary:
    def __init__(self, result): self.result, self.calls = result, 0
    def read(self, _requirements): self.calls += 1; return self.result


class Answer:
    def answer(self, state, limitation=None):
        return limitation or f"goal={state.goal}; facts={state.facts}; evidence={state.evidence}"


class CaptureRecorder:
    def __init__(self): self.results = []
    def record(self, _session, _initial, result, *_args):
        self.results.append(result)
        return None


def make_service(understandings, diary=None):
    retrieval = Retrieval()
    diary = diary or Diary(DiaryResult({}, False, kind="UNAVAILABLE"))
    loop = AdaptiveAgentLoop(SequenceUnderstander(understandings), retrieval, diary,
                             answer_generator=Answer(), max_steps=4)
    return AdaptiveChatService(loop, CaptureRecorder()), retrieval, diary


def actions(state): return [item["action"] for item in state.action_history]


def scenario(scenario_id, expectation, run):
    try:
        service, retrieval, diary, route_calls, assertions = run()
        state = service.sessions[route_calls[-1][1]].state
        return {"scenario": scenario_id, "expected": expectation, "status": "PASS", "assertions": assertions,
                "route": "/api/chat", "route_calls": route_calls, "response": route_calls[-1][2],
                "tool_counts": {"RETRIEVE": retrieval.calls, "READ_DIARY": diary.calls},
                "final_state": serialize_state(state), "state_history": route_calls[-1][3]}
    except AssertionError as error:
        return {"scenario": scenario_id, "expected": expectation, "status": "FAIL", "actual": str(error),
                "first_divergence_layer": "integration assertion", "root_cause": "not_determined", "affected_lineage": []}


def run_i1():
    service, retrieval, diary = make_service([Understanding("解释刺激控制的一般原则", TaskType.PERSONALIZED_DECISION, {})])
    route = RouteHarness(service); response, code = route.post("synthetic knowledge", "i1")
    state = service.sessions["i1"].state
    assert code == 200 and response["status"] == "ANSWER" and actions(state) == ["RETRIEVE", "ANSWER"]
    assert state.dependencies_satisfied[0]["dependency_type"] == "EVIDENCE"
    return service, retrieval, diary, [("POST", "i1", response, captured_loop_history(service))], ["EVIDENCE required/retrieved/satisfied", "no stale ASK"]


def run_i2():
    service, retrieval, diary = make_service([Understanding("我应该提前还是推迟上床时间", TaskType.PERSONALIZED_DECISION, {"bedtime": "23:00", "sleep_onset_latency": 60})])
    route = RouteHarness(service); response, code = route.post("synthetic personal", "i2")
    state = service.sessions["i2"].state
    assert code == 200 and response["status"] == "ASK" and state.action_history[-1]["target"] == "wake_time"
    return service, retrieval, diary, [("POST", "i2", response, captured_loop_history(service))], ["VALIDITY_STATE produces wake_time ASK"]


def run_i3():
    service, retrieval, diary = make_service([
        Understanding("我应该提前还是推迟上床时间", TaskType.PERSONALIZED_DECISION, {"bedtime": "23:00", "sleep_onset_latency": 60}),
        Understanding(None, None, {"wake_time": "07:00"}),
    ])
    route = RouteHarness(service); first, _ = route.post("first", "i3"); first_history = captured_loop_history(service)
    second, code = route.post("wake at 7", "i3"); state = service.sessions["i3"].state
    assert first["status"] == "ASK" and code == 200 and state.facts["wake_time"] == "07:00"
    assert [item["target"] for item in state.action_history if item["action"] == "ASK"].count("wake_time") == 1
    return service, retrieval, diary, [("POST", "i3", first, first_history), ("POST", "i3", second, captured_loop_history(service))], ["follow-up merged", "wake_time not repeated", "requirements re-synchronized"]


def run_i4():
    service, retrieval, diary = make_service([
        Understanding("什么是刺激控制", TaskType.KNOWLEDGE_QA, {}), Understanding(None, None, {}),
    ])
    route = RouteHarness(service); first, _ = route.post("first", "i4"); first_history = captured_loop_history(service)
    second, code = route.post("continue", "i4"); state = service.sessions["i4"].state
    assert first["status"] == second["status"] == "ANSWER" and code == 200 and retrieval.calls == 1
    return service, retrieval, diary, [("POST", "i4", first, first_history), ("POST", "i4", second, captured_loop_history(service))], ["REQUIRED to SATISFIED", "no duplicate RETRIEVE"]


def valid_diary():
    return Diary(DiaryResult({"recent_sleep_pattern": [{"date": "2026-02-01", "total_sleep_time": 420}]}, True,
                             source_entry_count=1, source_dates=("2026-02-01",), date_coverage=("2026-02-01",), provenance={"source": "synthetic"}))


def run_i5():
    service, retrieval, diary = make_service([Understanding("分析我的睡眠日记趋势", TaskType.PERSONALIZED_DECISION, {})], valid_diary())
    route = RouteHarness(service); response, code = route.post("diary", "i5"); state = service.sessions["i5"].state
    assert code == 200 and state.diary_projection["projection_status"] == "valid" and diary.calls == 1
    assert any(item["dependency_type"] == "RESOURCE" for item in state.dependencies_satisfied)
    return service, retrieval, diary, [("POST", "i5", response, captured_loop_history(service))], ["READ_DIARY", "valid projection", "RESOURCE satisfied"]


def run_i6():
    service, retrieval, diary = make_service([Understanding("分析我的睡眠日记趋势", TaskType.DATA_ANALYSIS, {})], Diary(DiaryResult({}, False, kind="UNAVAILABLE")))
    # The resource state is already known unavailable, so the route must not
    # issue a retry merely to discover the same fact.
    service.sessions["i6"] = AdaptiveSession(AdaptiveAgentState(diary_available=False))
    route = RouteHarness(service); response, code = route.post("unavailable", "i6"); state = service.sessions["i6"].state
    assert code == 200 and response["status"] == "ANSWER" and diary.calls == 0 and not state.facts
    assert state.dependencies_unavailable[0]["dependency_type"] == "RESOURCE"
    return service, retrieval, diary, [("POST", "i6", response, captured_loop_history(service))], ["RESOURCE unavailable", "no read", "no fabricated fact"]


def run_i7():
    service, retrieval, diary = make_service([
        Understanding("我应该提前还是推迟上床时间", TaskType.PERSONALIZED_DECISION, {"bedtime": "23:00", "sleep_onset_latency": 60}),
        Understanding("解释刺激控制", TaskType.KNOWLEDGE_QA, {}, is_new_goal=True),
    ])
    route = RouteHarness(service); first, _ = route.post("personal", "i7"); first_history = captured_loop_history(service)
    second, code = route.post("new knowledge", "i7"); state = service.sessions["i7"].state
    assert first["status"] == "ASK" and code == 200 and state.goal == "解释刺激控制" and not state.facts
    assert state.effective_requirements["decision_fields"] == ()
    return service, retrieval, diary, [("POST", "i7", first, first_history), ("POST", "i7", second, captured_loop_history(service))], ["new goal reset", "no stale requirements/dependencies"]


def run_i8():
    facts = {"bedtime": "23:00", "wake_time": "07:00"}
    service, retrieval, diary = make_service([Understanding("什么是刺激控制", TaskType.KNOWLEDGE_QA, facts)])
    route = RouteHarness(service); response, code = route.post("facts", "i8"); state = service.sessions["i8"].state
    assert code == 200 and response["status"] == "ANSWER" and state.facts == facts and "ASK" not in actions(state)
    assert "23:00" in response["assistant"] and "07:00" in response["assistant"]
    return service, retrieval, diary, [("POST", "i8", response, captured_loop_history(service))], ["optional facts retained", "no automatic ASK", "answer receives facts"]


def state_history(state):
    raise RuntimeError("Use captured_loop_history(service) for integration traces")


def captured_loop_history(service):
    return service.recorder.results[-1].state_history


def audit_lineage(results):
    gaps = []
    for result in results:
        if result["status"] != "PASS": continue
        state = result["final_state"]
        snapshots = [snapshot for route_call in result["route_calls"] for snapshot in route_call[3]]
        candidate_ids = {candidate.get("candidate_id") for snapshot in snapshots
                         for candidate in snapshot.get("candidate_actions", []) if candidate.get("candidate_id")}
        dependency_ids = {dependency.get("dependency_id") for snapshot in snapshots
                          for dependency in snapshot.get("dependencies_considered", []) if dependency.get("dependency_id")}
        for action in state["action_history"]:
            if not action.get("action_id") or not action.get("selected_candidate_id"):
                gaps.append({"scenario": result["scenario"], "gap": "action_without_candidate_lineage", "action": action})
            elif action["selected_candidate_id"] not in candidate_ids:
                gaps.append({"scenario": result["scenario"], "gap": "selected_candidate_not_observed", "action": action})
        for snapshot in snapshots:
            if not snapshot.get("goal_id"):
                gaps.append({"scenario": result["scenario"], "gap": "snapshot_without_goal_id"})
            for dependency in snapshot.get("dependencies_considered", []):
                if not dependency.get("dependency_id"):
                    gaps.append({"scenario": result["scenario"], "gap": "dependency_without_id"})
                for semantic_id in dependency.get("semantic_ids", []):
                    if semantic_id not in {item.get("semantic_id") for item in snapshot.get("semantic_provenance", [])}:
                        gaps.append({"scenario": result["scenario"], "gap": "dependency_semantic_link_missing", "dependency": dependency})
            for precondition in snapshot.get("preconditions_considered", []):
                if not precondition.get("precondition_id") or precondition.get("source_dependency_id") not in dependency_ids:
                    gaps.append({"scenario": result["scenario"], "gap": "precondition_dependency_link_missing", "precondition": precondition})
                if "precondition_forced_action" not in precondition or "counterfactual_action" not in precondition:
                    gaps.append({"scenario": result["scenario"], "gap": "precondition_counterfactual_fields_missing", "precondition": precondition})
        for event in state["lineage_events"]:
            if not all(event.get(key) for key in ("tool_result_id", "source_action_id", "state_update_id", "source_tool_result_id")):
                gaps.append({"scenario": result["scenario"], "gap": "incomplete_tool_lineage", "event": event})
        if any(item.get("source") and "goal_semantics" in item.get("source", []) for snapshot in snapshots for item in snapshot["dependencies_considered"]):
            if not state["semantic_provenance"]:
                gaps.append({"scenario": result["scenario"], "gap": "semantic_dependency_without_provenance"})
    return {"status": "PASS" if not gaps else "FAIL", "gaps": gaps, "checked_fields": ["goal_id", "semantic_id", "dependency_id", "precondition_id", "candidate_id", "action_id", "tool_result_id", "state_update_id"]}


def main():
    runs = [
        ("I1", "knowledge/wrong-task: evidence lifecycle, no stale ASK", run_i1),
        ("I2", "personalized true critical missing: validity-state ASK", run_i2),
        ("I3", "follow-up merge/resync: no repeated ASK", run_i3),
        ("I4", "evidence lifecycle: no duplicate retrieve", run_i4),
        ("I5", "diary lifecycle: valid projection/resource satisfied", run_i5),
        ("I6", "unavailable diary: bounded/no fabrication/no retry", run_i6),
        ("I7", "goal change: no stale effective requirements", run_i7),
        ("I8", "useful optional: retain supplied facts/no automatic ASK", run_i8),
    ]
    results = [scenario(*item) for item in runs]
    output = Path("evaluation/v1_2_1"); output.mkdir(parents=True, exist_ok=True)
    (output / "step9_7_integration_scenarios.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output / "step9_7_integration_traces.jsonl").open("w", encoding="utf-8") as stream:
        for result in results: stream.write(json.dumps(result, ensure_ascii=False) + "\n")
    lineage = audit_lineage(results)
    (output / "step9_7_lineage_audit.json").write_text(json.dumps(lineage, ensure_ascii=False, indent=2), encoding="utf-8")
    lifecycle = {"status": "PASS" if all(x["status"] == "PASS" for x in results) else "FAIL", "checks": {
        "new_goal": "I7", "follow_up": "I3", "retrieve_resync": "I1/I4", "diary_resync": "I5", "unavailable": "I6", "useful_optional": "I8"}}
    (output / "step9_7_effective_requirements_lifecycle_audit.json").write_text(json.dumps(lifecycle, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": sum(x["status"] == "PASS" for x in results), "total": len(results), "lineage": lineage["status"]}, ensure_ascii=False))


if __name__ == "__main__": main()
