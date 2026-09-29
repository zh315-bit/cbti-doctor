"""Focused, read-only checks for Step 9.30a.2 derived lineage sidecar."""
from __future__ import annotations

import unittest
import json
from pathlib import Path

from scripts.step9_30a2_lineage_sidecar import (
    OUT, classify_true_failure_dimensions, load_jsonl, protocol_audit,
    FORENSIC_MATRIX, frozen_integrity_audit,
)


class Step930a2LineageSidecarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Step 9.30a.2 is a historical, freeze-bound V4 derivation. Validate
        # its immutable outputs here; do not rebuild them under the Step 9.33
        # treatment Agent or read formal V4 inputs during ordinary regression.
        cls.sidecar = load_jsonl(OUT / "step9_30a2_v4_lineage_sidecar.jsonl")
        cls.manifest = json.loads((OUT / "step9_30a2_v4_input_manifest.json").read_text(encoding="utf-8"))
        cls.audit = json.loads((OUT / "step9_30a2_v4_true_failure_adjudication_audit.json").read_text(encoding="utf-8"))

    def test_exactly_seven_trace_backed_derivation_repairs(self):
        repaired = [x for x in self.sidecar if x["sidecar_lineage_status"] == "COMPLETE_DERIVED"]
        self.assertEqual(len(repaired), 7)
        self.assertTrue(all(x["lineage_reconstructed"] for x in repaired))
        self.assertTrue(all(x["reconstruction_source"]["raw_trace_line"]["line_sha256"] for x in repaired))
        self.assertTrue(all(all(a["candidate_decision_link_present"]
                                for a in x["lineage_graph"]["action_candidate_links"]) for x in repaired))

    def test_five_true_failures_remain_formally_incomplete(self):
        incomplete = [x for x in self.sidecar if x["sidecar_lineage_status"] == "INCOMPLETE_FORMAL"]
        self.assertEqual(len(incomplete), 5)
        self.assertTrue(all(not x["lineage_reconstructed"] for x in incomplete))
        self.assertTrue(all(x["semantic_root_status"] == "MISSING_IN_FORMAL_TRACE" for x in incomplete))
        self.assertTrue(all(not x["lineage_graph"]["semantic_root_ids"] for x in incomplete))

    def test_all_sidecar_links_use_existing_trace_ids(self):
        self.assertEqual(len(self.sidecar), 40)
        for item in self.sidecar:
            self.assertTrue(item["trace_provenance"]["line_sha256"])
            self.assertTrue(all(dep["dependency_id"] for dep in item["lineage_graph"]["dependency_roots"]))
            self.assertTrue(all(a["action_id"] for a in item["lineage_graph"]["action_candidate_links"]))

    def test_sidecar_is_deterministic(self):
        again = load_jsonl(OUT / "step9_30a2_v4_lineage_sidecar.jsonl")
        self.assertEqual(self.sidecar, again)

    def test_formal_input_hashes_reverified_and_no_scores_or_aggregate(self):
        self.assertTrue(self.manifest["formal_run_inputs_reverified_against_step9_30a_freeze"])
        self.assertFalse(self.audit["formal_v4_artifacts_modified"])
        self.assertFalse(self.audit["reviewer_scores_populated"])
        self.assertFalse(self.audit["aggregate_generated"])
        self.assertFalse(self.audit["overall_generated"])
        self.assertTrue(all(x["reviewer_scores_populated"] is False for x in self.sidecar))

    def test_protocol_policy_classification_is_fail_closed_and_deterministic(self):
        expected = {"partial_adjudication_allowed": "NOT_SPECIFIED",
                    "case_exclusion_allowed": "NOT_SPECIFIED",
                    "denominator_adjustment_allowed": "NOT_SPECIFIED",
                    "missing_dimension_policy": "NOT_SPECIFIED",
                    "lineage_limited_scoring": "NOT_SPECIFIED"}
        self.assertEqual({k: protocol_audit()[k] for k in expected}, expected)
        self.assertEqual(self.audit["adjudication_readiness_class"], "READY_FULL_40")
        self.assertEqual((self.audit["full_adjudication_case_count"],
                          self.audit["partial_adjudication_case_count"],
                          self.audit["non_adjudicatable_case_count"]), (40, 0, 0))

    def test_five_dimension_audit_has_no_unscorable_dimensions(self):
        rows = load_jsonl(FORENSIC_MATRIX)
        ids = [x["case_id"] for x in rows if x["root_cause_class"] == "TRUE_LINEAGE_FAILURE"]
        self.assertEqual(len(ids), 5)
        # Evidence is loaded from immutable raw traces by the real builder. The
        # assertions here validate the reported per-case dimension classifications.
        for case_id in ids:
            dims = self.audit["true_failure_dimension_audit"][case_id]["dimensions"]
            self.assertEqual(set(dims), {"goal_alignment", "facts_state_integrity",
                                         "action_resource_selection", "evidence_answer_scope",
                                         "interaction_efficiency"})
            self.assertTrue(all(value != "UNSCORABLE_DUE_TO_MISSING_LINEAGE" for value in dims.values()))

    def test_historical_builder_freeze_does_not_match_treatment(self):
        self.assertFalse(frozen_integrity_audit()["current_agent_matches_final_freeze"])


if __name__ == "__main__":
    unittest.main()
