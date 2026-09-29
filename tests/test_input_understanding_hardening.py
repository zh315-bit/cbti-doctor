import unittest

from adaptive_agent.input_understanding import (
    FACT_FIELDS, Understanding, apply_understanding, extract_explicit_facts,
    normalize_goal, understanding_from_mapping,
)
from adaptive_agent.state import AdaptiveAgentState


class InputUnderstandingHardeningTests(unittest.TestCase):
    def facts(self, text):
        return extract_explicit_facts(text)[0]

    def test_bedtime_variations_normalize_to_clock(self):
        self.assertEqual(self.facts("我晚上11点上床。")["bedtime"], "23:00")
        self.assertEqual(self.facts("我23:30躺下。")["bedtime"], "23:30")

    def test_cross_midnight_clock_difference_is_traceable_derived_latency(self):
        facts, sources = extract_explicit_facts("我晚上11点上床，凌晨12点睡着。")
        self.assertEqual(facts, {"bedtime": "23:00", "sleep_time": "00:00", "sleep_onset_latency": 60})
        self.assertEqual(sources["sleep_onset_latency"]["kind"], "derived")
        self.assertEqual(sources["sleep_onset_latency"]["source_fields"], ["bedtime", "sleep_time"])

    def test_explicit_latency_minutes_and_hours(self):
        self.assertEqual(self.facts("我通常需要60分钟才能睡着。")["sleep_onset_latency"], 60)
        self.assertEqual(self.facts("我大约1.5小时才入睡。")["sleep_onset_latency"], 90)

    def test_wake_time_and_total_sleep_duration(self):
        facts = self.facts("我早上7点起床，每晚睡6小时。")
        self.assertEqual(facts["wake_time"], "07:00")
        self.assertEqual(facts["total_sleep_time"], 360)

    def test_nighttime_awakenings(self):
        self.assertEqual(self.facts("我每晚醒1次。 ")["nighttime_awakenings"], 1)

    def test_recent_pattern_variations(self):
        for text in ("我已经这样两个星期了。", "最近两周都是这样。", "这个情况持续了大概14天。"):
            self.assertIn("recent_sleep_pattern", self.facts(text), text)

    def test_caffeine_language_variations(self):
        for text in ("我下午喝咖啡。", "我每天两杯咖啡。", "我午饭后一般会喝一杯咖啡。", "最近下午经常喝拿铁。"):
            self.assertIn("caffeine", self.facts(text), text)

    def test_nap_positive_and_explicit_negative(self):
        self.assertIn("nap", self.facts("我每天会午睡20分钟。"))
        self.assertIs(self.facts("我从不午睡。 ")["nap"], False)

    def test_exercise_screen_and_stress(self):
        facts = self.facts("我最近每周跑步三次，睡前总刷手机，工作压力很大。")
        self.assertTrue({"exercise", "screen_before_bed", "perceived_stress"}.issubset(facts))

    def test_multiple_explicit_facts_in_one_sentence(self):
        facts = self.facts("我晚上11点上床，60分钟才能睡着，早上7点起床，每晚醒1次。")
        self.assertEqual(facts["bedtime"], "23:00")
        self.assertEqual(facts["sleep_onset_latency"], 60)
        self.assertEqual(facts["wake_time"], "07:00")
        self.assertEqual(facts["nighttime_awakenings"], 1)

    def test_question_about_caffeine_does_not_claim_consumption(self):
        self.assertNotIn("caffeine", self.facts("咖啡会影响睡眠吗？"))

    def test_unmentioned_fields_remain_null_in_validated_mapping(self):
        understood = understanding_from_mapping({"goal": "解释刺激控制", "task_type": "KNOWLEDGE_QA", "facts": {"caffeine": "每天两杯"}}, "什么是刺激控制？")
        self.assertTrue(all(value is None for value in understood.facts.values()))
        self.assertEqual(understood.raw_facts["caffeine"], "每天两杯")

    def test_llm_raw_fact_is_not_accepted_without_textual_grounding(self):
        understood = understanding_from_mapping({"goal": "问题", "task_type": "CAUSE_ASSESSMENT", "facts": {"sleep_onset_latency": 60}}, "我最近睡不好。")
        self.assertTrue(all(value is None for value in understood.facts.values()))
        self.assertEqual(understood.raw_facts["sleep_onset_latency"], 60)

    def test_raw_and_validated_layers_remain_separate(self):
        understood = understanding_from_mapping({"goal": "问题", "task_type": "PERSONALIZED_DECISION", "facts": {"sleep_onset_latency": None}}, "我60分钟才能睡着。")
        self.assertEqual(understood.facts["sleep_onset_latency"], 60)
        self.assertIsNone(understood.raw_facts["sleep_onset_latency"])
        self.assertEqual(understood.fact_sources["sleep_onset_latency"]["kind"], "explicit")

    def test_directional_bedtime_goal_is_not_lost_when_llm_translates_it(self):
        self.assertEqual(normalize_goal("Decide whether to go to bed earlier", "他应该提前上床吗？"),
                         "判断是否应该提前上床")

    def test_second_turn_merges_one_new_fact_without_erasing_prior(self):
        state = AdaptiveAgentState(facts={"bedtime": "23:00"})
        understanding = understanding_from_mapping({"goal": None, "task_type": None, "facts": {"wake_time": "07:00"}}, "我早上7点起床。")
        apply_understanding(state, understanding)
        self.assertEqual(state.facts, {"bedtime": "23:00", "wake_time": "07:00"})
        self.assertEqual(state.fact_sources["wake_time"]["kind"], "explicit")

    def test_unknown_fields_are_not_materialized_into_agent_state(self):
        state = AdaptiveAgentState()
        apply_understanding(state, Understanding("问题", None, {}))
        self.assertEqual(state.facts, {})
        self.assertEqual(set(FACT_FIELDS) - set(state.facts), set(FACT_FIELDS))


if __name__ == "__main__":
    unittest.main()
