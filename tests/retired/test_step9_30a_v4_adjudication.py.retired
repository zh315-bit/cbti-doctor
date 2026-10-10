"""Deterministic V4 adjudication-template, validator, and aggregation tests."""
from __future__ import annotations

import copy
import unittest

from scripts.v4_adjudication_contract import (
    DIMENSIONS, aggregate_completed,
    generate_template, validate_records,
)


def completed_copy(template: list[dict]) -> list[dict]:
    records = copy.deepcopy(template)
    for record in records:
        facts = record["immutable_execution_facts"]
        judgments = record["reviewer_judgments"]
        judgments["dimension_scores"] = {key: maximum for key, maximum in DIMENSIONS.items()}
        judgments["total_score"] = sum(judgments["dimension_scores"].values())
        judgments["completion_judgment"] = "complete"
        judgments["validity_judgment"] = True
        judgments["ask_quality"] = {"denominator": facts["ASK_count"], "counts": {
            "necessary": 0, "useful_but_optional": 0, "redundant": 0, "irrelevant": facts["ASK_count"]}}
        judgments["necessary_ask_preservation"] = {"acquired_targets": 0, "oracle_required_targets": 0,
            "target_adjudications": []}
        judgments["tool_use_appropriateness"] = {
            "RETRIEVE": ["required"] * facts["RETRIEVE_count"],
            "READ_DIARY": ["required"] * facts["READ_DIARY_count"],
        }
        judgments["critical_failure"] = {"present": False, "types": [], "supporting_evidence": []}
        judgments["harmful_failure"] = False
        judgments["failure_attribution"] = {"primary_cause": None, "downstream_effects": [],
            "independent_failure": False, "first_divergence": None, "supporting_evidence": [],
            "missing_denominator": [], "rationale": "Synthetic test-only review record."}
        record["review_provenance"]["reviewer"] = "test reviewer"
        record["review_provenance"]["reviewed_at"] = "2026-09-26T00:00:00Z"
    return records


class V4AdjudicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = generate_template()

    def _template_fails(self, mutate, message="adjudication"):
        records = copy.deepcopy(self.template)
        mutate(records)
        with self.assertRaises(Exception):
            validate_records(records, "template")

    def test_clean_template_passes_and_all_reviewer_fields_are_unset(self):
        validate_records(self.template, "template")
        self.assertTrue(all(
            all(value is None for value in record["reviewer_judgments"]["dimension_scores"].values())
            and record["reviewer_judgments"]["completion_judgment"] is None
            and record["reviewer_judgments"]["total_score"] is None
            for record in self.template
        ))

    def test_missing_case_fails(self):
        self._template_fails(lambda records: records.pop())

    def test_duplicate_case_fails(self):
        self._template_fails(lambda records: records.__setitem__(-1, copy.deepcopy(records[0])))

    def test_unknown_case_fails(self):
        self._template_fails(lambda records: records[0]["immutable_execution_facts"].__setitem__("case_id", "V4-UNKNOWN"))

    def test_modified_execution_fact_fails(self):
        self._template_fails(lambda records: records[0]["immutable_execution_facts"].__setitem__("turn_count", 999))

    def test_wrong_rubric_hash_fails(self):
        self._template_fails(lambda records: records[0]["review_provenance"].__setitem__("rubric_sha256", "0" * 64))

    def test_wrong_metric_registry_hash_fails(self):
        self._template_fails(lambda records: records[0]["review_provenance"].__setitem__("metric_registry_sha256", "0" * 64))

    def test_invalid_dimension_score_fails_completed_validation(self):
        records = completed_copy(self.template)
        records[0]["reviewer_judgments"]["dimension_scores"]["goal_alignment"] = 21
        with self.assertRaisesRegex(RuntimeError, "invalid dimension score"):
            validate_records(records, "completed")

    def test_ask_denominator_mismatch_fails_completed_validation(self):
        records = completed_copy(self.template)
        records[0]["reviewer_judgments"]["ask_quality"]["denominator"] += 1
        with self.assertRaisesRegex(RuntimeError, "ASK quality denominator"):
            validate_records(records, "completed")

    def test_ask_category_sum_mismatch_fails_completed_validation(self):
        records = completed_copy(self.template)
        records[0]["reviewer_judgments"]["ask_quality"]["counts"]["necessary"] += 1
        with self.assertRaisesRegex(RuntimeError, "ASK category counts"):
            validate_records(records, "completed")

    def test_incomplete_completed_review_fails(self):
        records = completed_copy(self.template)
        records[0]["reviewer_judgments"]["validity_judgment"] = None
        with self.assertRaisesRegex(RuntimeError, "validity judgment"):
            validate_records(records, "completed")

    def test_null_template_fails_completed_mode(self):
        with self.assertRaises(Exception):
            validate_records(self.template, "completed")

    def test_completed_template_aggregates_descriptively_without_threshold(self):
        result = aggregate_completed(completed_copy(self.template))
        self.assertEqual(result["n"], 40)
        self.assertEqual(result["overall_descriptive_score"]["mean"], 100)
        self.assertIsNone(result["single_composite_pass_threshold"])


if __name__ == "__main__":
    unittest.main()
