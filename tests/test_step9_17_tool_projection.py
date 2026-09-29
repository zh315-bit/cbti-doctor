"""Synthetic Tool→State projection contract tests; no benchmark/model calls."""
import unittest
from unittest.mock import Mock

from adaptive_agent.answer_generation import LLMAnswerGenerator
from adaptive_agent.state import AdaptiveAgentState, TaskType
from adaptive_agent.state_update import apply_diary_result, apply_retrieval_result
from adaptive_agent.tools import DiaryResult, RetrievalResult


def valid_summary(**overrides):
    values = dict(facts={"summary": "记录显示作息有变化"}, available=True,
                  kind="SUMMARY_SHAPED", source_entry_count=7,
                  date_coverage=("2026-01-01", "2026-01-07"),
                  provenance={"source": "synthetic diary", "record_set": "fixture-A"},
                  summary_semantics="seven_calendar_day_descriptive_summary")
    values.update(overrides)
    return DiaryResult(**values)


def apply(result, state=None):
    state = state or AdaptiveAgentState(goal="分析睡眠日记", task_type=TaskType.DATA_ANALYSIS,
                                        goal_id="g-test", action_history=[{"action": "READ_DIARY", "action_id": "a-test"}])
    return apply_diary_result(state, result)


class ToolStateProjectionTests(unittest.TestCase):
    def test_01_consecutive_multiday_entries_project_with_counts_dates_and_lineage(self):
        entries = [{"date": f"2026-01-0{day}", "total_sleep_time": 420, "bedtime": "23:00", "wake_time": "07:00"} for day in range(1, 4)]
        state = apply(DiaryResult({"recent_sleep_pattern": entries}, True, source_entry_count=3,
                                  source_dates=tuple(x["date"] for x in entries), date_coverage=tuple(x["date"] for x in entries),
                                  provenance={"source": "synthetic", "record_set": "consecutive"}))
        p = state.diary_projection
        self.assertEqual((p["source_entry_count"], p["projected_entry_count"]), (3, 3))
        self.assertEqual(p["date_coverage"], [x["date"] for x in entries])
        self.assertEqual(p["projection_status"], "valid")
        self.assertTrue(p["tool_result_id"] and p["state_update_id"])
        self.assertEqual(state.facts["diary_derived"]["average_sleep_duration_minutes"], 420)
        self.assertEqual(state.facts["diary_derived"]["diary_day_count"], 3)

    def test_02_nonconsecutive_dates_preserved_without_filling_gaps(self):
        dates = ("2026-01-01", "2026-01-03", "2026-01-07")
        entries = [{"date": d} for d in dates]
        state = apply(DiaryResult({"entries": entries}, True, source_entry_count=3,
                                  source_dates=dates, date_coverage=dates,
                                  provenance={"source": "synthetic"}))
        self.assertEqual(state.diary_projection["date_coverage"], list(dates))
        self.assertEqual(state.facts["diary_derived"]["diary_day_count"], 3)

    def test_03_multiple_entries_same_day_preserve_cardinality_and_unique_day_count(self):
        dates = ("2026-01-01", "2026-01-01", "2026-01-02")
        entries = [{"date": d} for d in dates]
        state = apply(DiaryResult({"entries": entries}, True, source_entry_count=3,
                                  source_dates=dates, date_coverage=("2026-01-01", "2026-01-02"),
                                  provenance={"source": "synthetic"}))
        self.assertEqual(state.diary_projection["projected_entry_count"], 3)
        self.assertEqual(state.facts["diary_derived"]["diary_day_count"], 2)

    def test_04_missing_measurements_are_preserved_and_not_guessed(self):
        entries = [{"date": "2026-01-01", "total_sleep_time": None}, {"date": "2026-01-02", "total_sleep_time": 360}]
        state = apply(DiaryResult({"entries": entries}, True, source_entry_count=2,
                                  source_dates=("2026-01-01", "2026-01-02"), date_coverage=("2026-01-01", "2026-01-02"),
                                  provenance={"source": "synthetic"}))
        self.assertEqual(state.facts["recent_sleep_pattern"][0]["total_sleep_time"], None)
        self.assertEqual(state.facts["diary_derived"]["average_sleep_duration_minutes"], 360)
        self.assertEqual(state.facts["diary_derived"]["average_sleep_duration_source_entry_count"], 1)

    def test_05_range_and_approximate_clocks_are_not_collapsed_to_exact(self):
        entries = [{"date": "2026-01-01", "bedtime": {"uncertainty": "range", "low": "22:00", "high": "23:00"}},
                   {"date": "2026-01-02", "bedtime": {"uncertainty": "approximate", "value": "22:30"}}]
        state = apply(DiaryResult({"entries": entries}, True, source_entry_count=2,
                                  source_dates=("2026-01-01", "2026-01-02"), date_coverage=("2026-01-01", "2026-01-02"),
                                  provenance={"source": "synthetic"}))
        self.assertNotIn("bedtime_variation_minutes", state.facts["diary_derived"])
        self.assertEqual(state.facts["recent_sleep_pattern"], entries)

    def test_06_entry_shaped_projection_records_provenance(self):
        entry = {"date": "2026-01-01", "total_sleep_time": 400}
        state = apply(DiaryResult({"entries": [entry]}, True, source_entry_count=1,
                                  source_dates=(entry["date"],), date_coverage=(entry["date"],),
                                  provenance={"source": "synthetic", "entry_id": "e1"}))
        self.assertEqual(state.fact_sources["recent_sleep_pattern"]["payload_shape"], "ENTRY_SHAPED")
        self.assertEqual(state.fact_sources["recent_sleep_pattern"]["source_entry_count"], 1)

    def test_07_valid_summary_remains_summary_shaped(self):
        state = apply(valid_summary())
        self.assertEqual(state.diary_projection["projection_status"], "valid")
        self.assertEqual(state.diary_projection["payload_shape"], "SUMMARY_SHAPED")
        self.assertEqual(state.diary_projection["projected_entry_count"], 0)
        self.assertIn("diary_summary", state.facts)
        self.assertNotIn("recent_sleep_pattern", state.facts)

    def test_08_summary_missing_source_cardinality_is_invalid(self):
        state = apply(valid_summary(source_entry_count=None))
        self.assertEqual(state.diary_projection["projection_status"], "invalid")
        self.assertNotIn("diary_summary", state.facts)

    def test_09_summary_missing_date_coverage_is_invalid(self):
        state = apply(valid_summary(date_coverage=()))
        self.assertEqual(state.diary_projection["projection_status"], "invalid")

    def test_10_summary_missing_provenance_is_invalid(self):
        state = apply(valid_summary(provenance=None))
        self.assertEqual(state.diary_projection["projection_status"], "invalid")

    def test_11_unavailable_is_distinct_and_writes_no_facts(self):
        state = apply(DiaryResult({"entries": [{"date": "2026-01-01"}]}, False, kind="UNAVAILABLE"))
        self.assertEqual(state.diary_projection["projection_status"], "unavailable")
        self.assertEqual(state.facts, {})

    def test_12_cardinality_mismatch_is_invalid_and_writes_no_facts(self):
        state = apply(DiaryResult({"entries": [{"date": "2026-01-01"}]}, True, source_entry_count=2,
                                  source_dates=("2026-01-01", "2026-01-02"), date_coverage=("2026-01-01", "2026-01-02"),
                                  provenance={"source": "synthetic"}))
        self.assertEqual(state.diary_projection["projection_status"], "invalid")
        self.assertEqual(state.diary_projection["projected_entry_count"], 0)
        self.assertEqual(state.diary_projection["received_entry_count"], 1)
        self.assertEqual(state.facts, {})

    def test_13_invalid_diary_source_is_filtered_from_answer_context(self):
        model = Mock()
        model.invoke.return_value.content = "无法分析。"
        state = AdaptiveAgentState(goal="分析日记", task_type=TaskType.DATA_ANALYSIS,
                                   facts={"recent_sleep_pattern": [{"date": "2026-01-01", "total_sleep_time": 500}]},
                                   fact_sources={"recent_sleep_pattern": {"source_type": "diary"}},
                                   diary_projection={"projection_status": "invalid"}, answer_scope="仅描述有效日记数据。")
        LLMAnswerGenerator(model).answer(state)
        prompt = model.invoke.call_args.args[0][1][1]
        self.assertNotIn("2026-01-01", prompt)
        self.assertNotIn("500", prompt)

    def test_14_valid_projection_allows_deterministic_claims_with_traceable_source(self):
        entries = [{"date": "2026-01-01", "bedtime": "23:00", "wake_time": "07:00", "total_sleep_time": 420},
                   {"date": "2026-01-02", "bedtime": "23:30", "wake_time": "07:00", "total_sleep_time": 360}]
        state = apply(DiaryResult({"entries": entries}, True, source_entry_count=2,
                                  source_dates=("2026-01-01", "2026-01-02"), date_coverage=("2026-01-01", "2026-01-02"),
                                  provenance={"source": "synthetic"}))
        self.assertEqual(state.facts["diary_derived"]["average_sleep_duration_minutes"], 390)
        self.assertEqual(state.facts["diary_derived"]["bedtime_variation_minutes"], 30)
        self.assertEqual(state.facts["diary_derived"]["sleep_efficiency_by_day"][0]["percent"], 87.5)
        model = Mock()
        model.invoke.return_value.content = "已根据有效数据分析。"
        LLMAnswerGenerator(model).answer(state)
        self.assertTrue(any("390" in item["claim"] for item in state.claim_provenance))
        self.assertTrue(state.fact_sources["diary_derived"]["projection"]["tool_result_id"])
        answer_claim = next(item for item in state.claim_provenance if item.get("claim_type") == "deterministically-derived")
        self.assertEqual(answer_claim["projection_status"], "valid")
        self.assertTrue(answer_claim["tool_result_id"] and answer_claim["state_update_id"])

    def test_15_malformed_date_fails_closed(self):
        state = apply(DiaryResult({"entries": [{"date": "not-a-date"}]}, True, source_entry_count=1,
                                  source_dates=("not-a-date",), date_coverage=("not-a-date",),
                                  provenance={"source": "synthetic"}))
        self.assertEqual(state.diary_projection["projection_status"], "invalid")
        self.assertEqual(state.facts, {})

    def test_16_date_provenance_mismatch_fails_closed(self):
        state = apply(DiaryResult({"entries": [{"date": "2026-01-01"}]}, True, source_entry_count=1,
                                  source_dates=("2026-01-02",), date_coverage=("2026-01-02",),
                                  provenance={"source": "synthetic"}))
        self.assertEqual(state.diary_projection["projection_status"], "invalid")

    def test_17_empty_available_diary_is_valid_empty_not_fabricated(self):
        state = apply(DiaryResult({"entries": []}, True, source_entry_count=0,
                                  provenance={"source": "synthetic empty diary"}))
        self.assertEqual(state.diary_projection["projection_status"], "valid")
        self.assertEqual(state.diary_projection["projected_entry_count"], 0)
        self.assertEqual(state.facts["diary_derived"]["diary_day_count"], 0)

    def test_18_invalid_new_read_cannot_leave_stale_diary_facts(self):
        prior = {"source_type": "diary", "projection": {"projection_status": "valid"}}
        state = AdaptiveAgentState(facts={"recent_sleep_pattern": [{"date": "2026-01-01"}]},
                                   fact_sources={"recent_sleep_pattern": prior},
                                   action_history=[{"action": "READ_DIARY", "action_id": "a"}])
        apply_diary_result(state, valid_summary(source_entry_count=None))
        self.assertNotIn("recent_sleep_pattern", state.facts)

    def test_19_shared_projection_envelope_covers_retrieval(self):
        state = AdaptiveAgentState(goal_id="g", action_history=[{"action": "RETRIEVE", "action_id": "a"}])
        apply_retrieval_result(state, RetrievalResult(("supporting evidence",), True, "synthetic RAG"))
        event = state.lineage_events[-1]
        self.assertEqual(event["payload_shape"], "EVIDENCE_LIST")
        self.assertEqual(event["source_entry_count"], 1)
        self.assertEqual(event["projected_entry_count"], 1)
        self.assertTrue(event["tool_result_id"] and event["state_update_id"])
        self.assertEqual(state.evidence_sources[0]["tool_result_id"], event["tool_result_id"])

    def test_20_retrieval_answer_claim_links_to_tool_and_state_update(self):
        state = AdaptiveAgentState(goal="解释刺激控制一般原则", task_type=TaskType.KNOWLEDGE_QA,
                                   answer_scope="只解释证据支持的原则。")
        state.action_history.append({"action": "RETRIEVE", "action_id": "a"})
        apply_retrieval_result(state, RetrievalResult(("刺激控制原则资料",), True, "synthetic RAG"))
        model = Mock()
        model.invoke.return_value.content = "根据资料说明。"
        LLMAnswerGenerator(model).answer(state)
        claim = next(item for item in state.claim_provenance if item["claim_type"] == "evidence-grounded")
        self.assertTrue(claim["tool_result_id"] and claim["state_update_id"])


if __name__ == "__main__":
    unittest.main()
