"""Validate the frozen V1.1 benchmark overlay without invoking the agent."""

from __future__ import annotations

from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
BASE_REQUIRED = {
    "case_id", "user_query", "hidden_profile", "task_type", "goal",
    "critical_information", "secondary_information", "required_resources",
    "expected_action_path", "alternative_acceptable_paths", "unacceptable_actions",
    "redundant_action_criteria", "goal_drift_criteria", "fabrication_criteria",
    "expected_answer_scope",
}
EXPECTED_TASK_COUNTS = {
    "KNOWLEDGE_QA": 2,
    "CAUSE_ASSESSMENT": 2,
    "PERSONALIZED_DECISION": 4,
    "DATA_ANALYSIS": 2,
}
CRITICAL_TYPES = {
    "FABRICATED_USER_FACT", "FABRICATED_DIARY_DATA", "UNAVAILABLE_RESOURCE_TREATED_AS_REAL",
    "UNSUPPORTED_QUANTITATIVE_MEDICAL_CLAIM", "ANSWER_CONTRADICTS_KNOWN_STATE",
    "UNSUPPORTED_INDIVIDUALIZED_TREATMENT_INSTRUCTION",
}


def main() -> None:
    overlay_path = ROOT / "evaluation" / "benchmark_v1_1.yaml"
    overlay = yaml.safe_load(overlay_path.read_text(encoding="utf-8"))
    base_path = overlay_path.parent / overlay["base_benchmark"]
    base = yaml.safe_load(base_path.read_text(encoding="utf-8"))
    cases = base["cases"]
    case_ids = {case["case_id"] for case in cases}
    missing = {case["case_id"]: sorted(BASE_REQUIRED - case.keys())
               for case in cases if BASE_REQUIRED - case.keys()}
    counts: dict[str, int] = {}
    for case in cases:
        counts[case["task_type"]] = counts.get(case["task_type"], 0) + 1

    assert overlay["benchmark_version"] == "1.1"
    assert overlay["status"] == "frozen_design"
    assert len(cases) == 10 and counts == EXPECTED_TASK_COUNTS and not missing
    assert set(overlay["case_overrides"]) <= case_ids
    assert "PD-04-specific-plan-boundary" in overlay["case_overrides"]
    assert set(overlay["failure_attribution"]["primary_cause_enum"]) >= {
        "INPUT_UNDERSTANDING", "STATE_INTEGRITY", "SUFFICIENCY", "ACTION_SELECTION",
        "RESOURCE_SELECTION", "RETRIEVAL", "ANSWER_GROUNDING", "GOAL_DRIFT",
        "EFFICIENCY", "BENCHMARK_AMBIGUITY",
    }
    assert set(overlay["critical_failure"]["types"]) == CRITICAL_TYPES
    for case_id in ("DA-01-seven-day-diary-available", "DA-02-seven-day-diary-unavailable"):
        assert case_id in overlay["diary_fixture_contract"]["required_state_transitions"]

    print("benchmark_version:", overlay["benchmark_version"])
    print("resolved_case_count:", len(cases))
    print("task_type_counts:", counts)
    print("case_overrides:", sorted(overlay["case_overrides"]))
    print("validation: OK (schema only; agent was not run)")


if __name__ == "__main__":
    main()
