import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.aggregate_step9_30c_v4 import (
    ADJUDICATION_PATH, SIDECAR_PATH, aggregate_records,
)
from scripts.step9_30b1_identity import (
    ADJUDICATION_REL, FAILED_AUDIT_REL, FREEZE_REL, INPUT_REL, REPORT_REL,
    RESOLUTION_REL, verify_canonical_input,
)


class Step930cAggregationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = [json.loads(line) for line in ADJUDICATION_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
        cls.sidecar = [json.loads(line) for line in SIDECAR_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_frozen_adjudication_aggregates_deterministically(self):
        first = aggregate_records(self.records, self.sidecar)
        second = aggregate_records(self.records, self.sidecar)
        self.assertEqual(first, second)
        self.assertEqual(first["adjudicated_case_count"], 40)
        self.assertEqual(first["OVERALL_PASS_THRESHOLD"], "NOT_DEFINED")
        self.assertEqual(first["reviewer_limitations"]["reviewer_type"], "SINGLE_AI_REVIEWER")

    def test_strata_and_lineage_are_reported_without_reclassification(self):
        result = aggregate_records(self.records, self.sidecar)
        self.assertEqual(result["task_distribution"], {
            "CAUSE_ASSESSMENT": 10, "DATA_ANALYSIS": 10,
            "KNOWLEDGE_QA": 10, "PERSONALIZED_DECISION": 10,
        })
        self.assertEqual(result["lineage"]["FORMAL_LINEAGE_READY"], 28)
        self.assertEqual(result["lineage"]["DERIVED_LINEAGE_COMPLETE"], 7)
        self.assertEqual(result["lineage"]["INCOMPLETE_FORMAL_BUT_ADJUDICATABLE"], 5)

    def test_case_projection_excludes_case_content_and_rationales(self):
        row = aggregate_records(self.records, self.sidecar)["case_level_rows"][0]
        forbidden = {"prompt", "input", "answer", "raw_trace", "evidence", "rationale"}
        self.assertTrue(forbidden.isdisjoint(row))
        self.assertTrue(forbidden.isdisjoint(row["execution"]))

    def test_final_answer_status_does_not_define_completion(self):
        result = aggregate_records(self.records, self.sidecar)
        judged_complete = sum(r["reviewer_judgments"]["completion_judgment"] == "complete" for r in self.records)
        answer_status = sum(r["immutable_execution_facts"]["final_status"] == "ANSWER" for r in self.records)
        self.assertEqual(result["completion_and_validity"]["overall"]["rate"]["numerator"], judged_complete)
        self.assertNotEqual(judged_complete, answer_status)


class Step930b1IdentityGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.adjudication_path = self.root / ADJUDICATION_REL
        self.adjudication_path.parent.mkdir(parents=True, exist_ok=True)
        self.adjudication_path.write_bytes(b'{"case_id":"fixture"}\n')
        self.freeze_path = self.root / FREEZE_REL
        self.freeze_path.parent.mkdir(parents=True, exist_ok=True)
        self.authoritative = hashlib.sha256(self.adjudication_path.read_bytes()).hexdigest()
        self.freeze_path.write_text(json.dumps({"validation_status": "PASS", "case_count": 40,
                                               "adjudication_sha256": self.authoritative}), encoding="utf-8")
        for rel_path in (FAILED_AUDIT_REL, REPORT_REL):
            source = self.root / rel_path
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("fixture-source", encoding="utf-8")
        source_paths = (ADJUDICATION_REL, FREEZE_REL, REPORT_REL, FAILED_AUDIT_REL)
        self.resolution_path = self.root / RESOLUTION_REL
        self.resolution_path.write_text(json.dumps({
            "status": "PASS", "resolution_class": "EXTERNAL_REQUEST_PIN_ERROR",
            "authoritative_adjudication_path": ADJUDICATION_REL,
            "authoritative_adjudication_sha256": self.authoritative, "case_count": 40,
            "source_artifacts": [{"path": p, "sha256": hashlib.sha256((self.root / p).read_bytes()).hexdigest()} for p in source_paths],
        }), encoding="utf-8")
        resolution_sha = hashlib.sha256(self.resolution_path.read_bytes()).hexdigest()
        self.input_path = self.root / INPUT_REL
        self.input_path.parent.mkdir(parents=True, exist_ok=True)
        self.input_path.write_text(json.dumps({
            "status": "CANONICAL_INPUT_READY_NOT_EXECUTED",
            "aggregation_authorized_by_this_artifact": False,
            "identity_resolution_path": RESOLUTION_REL,
            "identity_resolution_sha256": resolution_sha,
            "adjudication_path": ADJUDICATION_REL,
            "adjudication_sha256": self.authoritative,
            "case_count": 40, "reviewer_type": "SINGLE_AI_REVIEWER",
        }), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_correct_authoritative_sha_passes(self):
        checked = verify_canonical_input(self.root)
        self.assertEqual(checked["adjudication_sha256"], self.authoritative)

    def test_wrong_requested_sha_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "external/requested pin mismatch"):
            verify_canonical_input(self.root, requested_sha256="0" * 64)

    def test_adjudication_mutation_fails_closed(self):
        self.adjudication_path.write_bytes(b'{"case_id":"mutated"}\n')
        with self.assertRaisesRegex(RuntimeError, "file and Step 9.30b freeze hash mismatch"):
            verify_canonical_input(self.root)

    def test_freeze_hash_mutation_fails_closed(self):
        self.freeze_path.write_text(json.dumps({"validation_status": "PASS", "case_count": 40,
                                               "adjudication_sha256": "0" * 64}), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "file and Step 9.30b freeze hash mismatch"):
            verify_canonical_input(self.root)

    def test_missing_resolution_fails_closed(self):
        self.resolution_path.unlink()
        with self.assertRaisesRegex(RuntimeError, "identity resolution artifact missing"):
            verify_canonical_input(self.root)

    def test_alternative_adjudication_path_cannot_be_substituted(self):
        data = json.loads(self.input_path.read_text(encoding="utf-8"))
        data["adjudication_path"] = "evaluation/other.jsonl"
        self.input_path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "substitute a different adjudication path"):
            verify_canonical_input(self.root)


if __name__ == "__main__":
    unittest.main()
