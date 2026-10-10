"""Isolated synthetic tests for V3 namespace derivation and reservation."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import unittest

from scripts import v3_namespace_allocator as allocator


EVALUATION_ID = "synthetic-frozen-v3-evaluation"
AUTHORIZATION_ID = "synthetic-authorization-1"
ATTEMPT_ID = "synthetic-attempt-1"


class NamespaceAllocatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_fresh_derived_namespace_is_absent_and_unique(self):
        first = allocator.derive_namespace_id(EVALUATION_ID, AUTHORIZATION_ID, ATTEMPT_ID)
        second = allocator.derive_namespace_id(EVALUATION_ID, AUTHORIZATION_ID, "synthetic-attempt-2")
        self.assertNotEqual(first, second)
        self.assertFalse((self.root / first).exists())
        allocator.validate_namespace_id(first, EVALUATION_ID)

    def test_old_occupied_and_failed_namespaces_are_forbidden(self):
        for name in (allocator.OCCUPIED_EVALUATION_ID, allocator.FAILED_EVALUATION_ID):
            with self.subTest(name=name), self.assertRaisesRegex(RuntimeError, "reserved or unsafe"):
                allocator.validate_namespace_id(name, EVALUATION_ID)

    def test_identity_cannot_reserve_a_second_namespace(self):
        namespace_id, container = allocator.reserve_namespace(
            self.root, EVALUATION_ID, AUTHORIZATION_ID, ATTEMPT_ID)
        marker = json.loads((container / allocator.MARKER).read_text(encoding="utf-8"))
        self.assertEqual(marker["namespace_id"], namespace_id)
        self.assertEqual(marker["attempt_id"], ATTEMPT_ID)
        with self.assertRaisesRegex(RuntimeError, "already allocated"):
            allocator.reserve_namespace(self.root, EVALUATION_ID, AUTHORIZATION_ID, ATTEMPT_ID)

    def test_authorization_cannot_be_rebound_to_another_attempt(self):
        allocator.reserve_namespace(self.root, EVALUATION_ID, AUTHORIZATION_ID, ATTEMPT_ID)
        with self.assertRaisesRegex(RuntimeError, "already allocated"):
            allocator.reserve_namespace(self.root, EVALUATION_ID, AUTHORIZATION_ID, "synthetic-attempt-2")

    def test_parallel_duplicate_allocation_has_one_winner(self):
        def allocate():
            try:
                return allocator.reserve_namespace(self.root, EVALUATION_ID,
                                                  AUTHORIZATION_ID, ATTEMPT_ID)[0]
            except RuntimeError:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: allocate(), range(2)))
        self.assertEqual(sum(value is not None for value in outcomes), 1)
        self.assertEqual(len(list(self.root.glob("*/" + allocator.MARKER))), 1)

    def test_historical_ledger_identity_cannot_be_reallocated(self):
        old = self.root / "historical-run"
        old.mkdir()
        (old / "attempts.jsonl").write_text(json.dumps({
            "authorization_id": AUTHORIZATION_ID,
            "attempt_id": "unrelated-old-attempt",
        }) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "already allocated"):
            allocator.reserve_namespace(self.root, EVALUATION_ID,
                                        AUTHORIZATION_ID, ATTEMPT_ID)

    def test_nested_historical_ledger_without_marker_cannot_be_reallocated(self):
        old = self.root / "derived-old" / EVALUATION_ID
        old.mkdir(parents=True)
        (old / "attempts.jsonl").write_text(json.dumps({
            "authorization_id": AUTHORIZATION_ID,
            "attempt_id": "nested-historical-attempt",
        }) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "already allocated"):
            allocator.reserve_namespace(self.root, EVALUATION_ID,
                                        AUTHORIZATION_ID, ATTEMPT_ID)

    def test_allocation_marker_corruption_fails_closed(self):
        container = self.root / "historical-run"
        container.mkdir()
        (container / allocator.MARKER).write_text("{broken", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "malformed namespace allocation"):
            allocator.reserve_namespace(self.root, EVALUATION_ID,
                                        AUTHORIZATION_ID, ATTEMPT_ID)

    def test_reserved_fresh_namespace_requires_transaction_for_post_first_case_guard(self):
        from scripts import run_step9_53_v3_identity_adapter as adapter

        namespace_id = allocator.derive_namespace_id(EVALUATION_ID, AUTHORIZATION_ID, ATTEMPT_ID)
        namespace_root = self.root / namespace_id
        auth_file = self.root / "authorization.json"
        auth_file.write_text(json.dumps({
            "evaluation_id": EVALUATION_ID,
            "authorization_id": AUTHORIZATION_ID,
            "attempt_id": ATTEMPT_ID,
            "status": "ISSUED_NOT_EXECUTED",
            "runner_freeze_revision": adapter.RUNNER_FREEZE_REVISION,
            "runner_freeze_sha256": adapter.sha256_file(adapter.ROOT / adapter.V3_RUNNER_FREEZE_PATH),
            "consumed": False,
            "consumed_at_utc": None,
        }), encoding="utf-8")
        common = {
            "run_root": namespace_root,
            "evaluation_id": EVALUATION_ID,
            "authorization_id": AUTHORIZATION_ID,
            "attempt_id": ATTEMPT_ID,
            "authorization_file": auth_file,
            "treatment_agent_sha256": "agent-sha",
            "runner_sha256": "runner-sha",
            "benchmark_sha256": "benchmark-sha",
            "case_count": 40,
            "case_order_fingerprint_sha256": "order-sha",
            "identity_root": self.root,
        }
        before = adapter._validate_namespace_lifecycle(phase=adapter.PRE_ATTEMPT, **common)
        self.assertTrue(before["namespace_isolated_for_phase"])
        allocator.reserve_namespace(self.root, EVALUATION_ID, AUTHORIZATION_ID, ATTEMPT_ID)
        before_reserved = adapter._validate_namespace_lifecycle(phase=adapter.PRE_ATTEMPT, **common)
        self.assertTrue(before_reserved["namespace_isolated_for_phase"])

        (namespace_root / EVALUATION_ID).mkdir()
        with self.assertRaisesRegex(RuntimeError, "requires transaction identity"):
            adapter._validate_namespace_lifecycle(
                phase=adapter.POST_ATTEMPT_CREATION_PRE_FIRST_CASE, **common)


if __name__ == "__main__":
    unittest.main()
