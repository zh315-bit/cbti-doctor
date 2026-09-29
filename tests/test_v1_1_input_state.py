import unittest

from adaptive_agent.facts import derive_sleep_facts, duration_between
from adaptive_agent.input_understanding import apply_understanding, extract_explicit_facts, understanding_from_mapping
from adaptive_agent.state import AdaptiveAgentState


class V11InputStateTests(unittest.TestCase):
    def test_english_and_colloquial_facts(self):
        facts, sources = extract_explicit_facts("I go to bed at 11 pm and it takes 90 minutes to fall asleep; I wake at 7 am.")
        self.assertEqual(facts["sleep_onset_latency"], 90)
        self.assertEqual(facts["bedtime"], "23:00")
        self.assertEqual(facts["wake_time"], "07:00")
        self.assertEqual(sources["bedtime"]["source_type"], "user_explicit")

    def test_range_and_approximation_are_preserved(self):
        facts, _ = extract_explicit_facts("我大约午夜上床，7到8点醒。")
        self.assertEqual(facts["bedtime"], {"uncertainty": "approximate", "value": "00:00"})
        self.assertEqual(facts["wake_time"]["uncertainty"], "range")
        self.assertIsNone(derive_sleep_facts(facts).get("time_in_bed"))

    def test_compound_facts_have_independent_slots(self):
        facts, sources = extract_explicit_facts("晚上11点上床，60分钟入睡，早上7点起床，夜里醒两次，醒着20分钟。")
        self.assertEqual(facts["nighttime_awakenings"], 2)
        self.assertEqual(facts["awake_duration"], 20)
        self.assertIn("nighttime_awakenings", sources)

    def test_correction_replaces_only_same_field(self):
        state = AdaptiveAgentState()
        apply_understanding(state, understanding_from_mapping({"facts": {}}, "我一般7点起床，入睡超过一小时。"))
        apply_understanding(state, understanding_from_mapping({"facts": {}}, "其实最近基本7点半左右起床。"))
        self.assertEqual(state.facts["wake_time"], {"uncertainty": "approximate", "value": "07:30"})
        self.assertEqual(state.facts["sleep_onset_latency"], 60)

    def test_provenance_and_missing_unknown(self):
        understanding = understanding_from_mapping({"facts": {"wake_time": "08:00"}}, "我不确定几点醒。")
        self.assertIsNone(understanding.facts["wake_time"])
        self.assertEqual(understanding.raw_facts["wake_time"], "08:00")
        self.assertEqual(understanding.fact_sources, {})

    def test_cross_midnight_deterministic_duration(self):
        self.assertEqual(duration_between("00:00", "08:00"), 480)
        self.assertEqual(duration_between("23:30", "07:00"), 450)


if __name__ == "__main__":
    unittest.main()
