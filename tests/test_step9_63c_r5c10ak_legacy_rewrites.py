"""Step 9.63c-r5c10ak: five legacy tests whose property is not covered elsewhere, run on a SYNTHETIC
temporary root.

The tests (55a x4, 58a x1) exercise the identity adapter's own pre-attempt checks: the dedicated
reuse guard for the consumed Step 9.54 authorization / failed Step 9.55 attempt, "a manifest is
required", a clean future authorization passing, and the post-first-case transaction requirement.
Since r6 the adapter first asks the lifecycle reducer whether the authorization is executable, using
the reducer's DEFAULT paths. On the real repository those defaults now hold the activated r11 state,
where the tests' synthetic identities have no manifest, so the reducer fails closed before the
adapter check under test is ever reached.

Here the reducer's defaults (root, ledger, run root, transaction journals) point at a temporary root
that contains a synthetic V3 authorization manifest for each identity the test uses and an empty
ledger. The test BODIES and their expected errors are the archived originals, unchanged (the
functions are taken from the archives in tests/retired/).
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import authorization_lifecycle as lifecycle
from scripts import run_step9_53_v3_identity_adapter as adapter
from scripts import v3_execution_transaction as transaction

RETIRED = Path(__file__).resolve().parent / "retired"


def load_archived(stem: str):
    spec = importlib.util.spec_from_file_location(f"archived_{stem}", RETIRED / f"{stem}.py.retired",
                                                  loader=importlib.machinery.SourceFileLoader(f"archived_{stem}", str(RETIRED / f"{stem}.py.retired")))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A55 = load_archived("test_step9_55a_namespace_lifecycle")
A58 = load_archived("test_step9_58a_r1_namespace_allocator")


class SyntheticLifecycleRoot:
    """Points the lifecycle reducer's default paths at a temporary root with synthetic manifests."""
    IDENTITIES: tuple[tuple[str, str, str], ...] = ()

    def setUp(self):
        super().setUp()
        self._synthetic = tempfile.TemporaryDirectory(prefix="synthetic-lifecycle-")
        root = Path(self._synthetic.name).resolve()
        evaluation = root / "evaluation/v1_2_3"
        runs = root / "evaluation/v4_runs"
        evaluation.mkdir(parents=True)
        (runs / ".execution_transactions").mkdir(parents=True)
        ledger = evaluation / "authorization_lifecycle_events.jsonl"
        ledger.write_text("", encoding="utf-8")
        for number, (authorization_id, attempt_id, evaluation_id) in enumerate(self.IDENTITIES):
            (evaluation / f"step9_63c_r5c10ak_synthetic_{number}_v3_authorization_manifest.json").write_text(json.dumps({
                "artifact_type": "SYNTHETIC_TEST_AUTHORIZATION", "treatment": "TREATMENT_V3",
                "authorization_id": authorization_id, "attempt_id": attempt_id, "evaluation_id": evaluation_id,
                "status": "ISSUED_NOT_EXECUTED", "authorization_status": lifecycle.ISSUED,
                "consumed": False, "consumed_at_utc": None, "authorization_consumption_count": 0,
                "runner_freeze_revision": "synthetic"}), encoding="utf-8")
        self.synthetic_root = root
        for target, name, value in ((lifecycle, "ROOT", root), (lifecycle, "EVENT_LEDGER_PATH", ledger),
                                    (lifecycle, "RUN_ROOT", runs), (lifecycle, "LOCK_PATH", runs / ".namespace-allocation.lock"),
                                    (transaction, "RUN_ROOT", runs), (transaction, "TRANSACTION_ROOT", runs / ".execution_transactions")):
            patcher = patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self._synthetic.cleanup)

    def test_the_reducer_sees_the_synthetic_root_not_the_real_repository(self):
        for authorization_id, _, _ in self.IDENTITIES:
            result = lifecycle.reduce_authorization_lifecycle(authorization_id=authorization_id)
            self.assertEqual(result["derived_state"], lifecycle.ISSUED_EXECUTABLE, result)
        self.assertEqual(lifecycle.EVENT_LEDGER_PATH.parent.parent.parent, self.synthetic_root)


def _only(base, names):
    """A subclass of `base` that runs only `names` (the other inherited tests are switched off)."""
    attrs = {attr: None for attr in dir(base) if attr.startswith("test") and attr not in names}
    return attrs


class Rewritten55a(SyntheticLifecycleRoot, A55.NamespaceLifecycleTests):
    IDENTITIES = ((A55.AUTHORIZATION_ID, A55.ATTEMPT_ID, A55.EVALUATION_ID),
                  (adapter.CONSUMED_STEP9_54_AUTHORIZATION_ID, A55.ATTEMPT_ID, A55.EVALUATION_ID))


for _name, _value in _only(A55.NamespaceLifecycleTests, {
        "test_consumed_step954_authorization_cannot_be_reused", "test_failed_step955_attempt_cannot_be_resumed",
        "test_new_future_authorization_and_attempt_pass_preflight", "test_missing_authorization_semantic_state_fails_closed"}).items():
    setattr(Rewritten55a, _name, _value)


class Rewritten58a(SyntheticLifecycleRoot, A58.NamespaceAllocatorTests):
    IDENTITIES = ((A58.AUTHORIZATION_ID, A58.ATTEMPT_ID, A58.EVALUATION_ID),)


for _name, _value in _only(A58.NamespaceAllocatorTests, {"test_reserved_fresh_namespace_requires_transaction_for_post_first_case_guard"}).items():
    setattr(Rewritten58a, _name, _value)


class BodiesAreTheArchivedOriginals(unittest.TestCase):
    def test_the_rewritten_tests_run_the_archived_function_objects_unchanged(self):
        for cls, base, names in ((Rewritten55a, A55.NamespaceLifecycleTests, ("test_consumed_step954_authorization_cannot_be_reused", "test_failed_step955_attempt_cannot_be_resumed",
                                                                            "test_new_future_authorization_and_attempt_pass_preflight", "test_missing_authorization_semantic_state_fails_closed")),
                                 (Rewritten58a, A58.NamespaceAllocatorTests, ("test_reserved_fresh_namespace_requires_transaction_for_post_first_case_guard",))):
            for name in names:
                self.assertIs(getattr(cls, name), getattr(base, name))
        loaded = unittest.defaultTestLoader.getTestCaseNames(Rewritten55a)
        self.assertEqual(set(loaded), {"test_consumed_step954_authorization_cannot_be_reused", "test_failed_step955_attempt_cannot_be_resumed",
                                       "test_new_future_authorization_and_attempt_pass_preflight", "test_missing_authorization_semantic_state_fails_closed",
                                       "test_the_reducer_sees_the_synthetic_root_not_the_real_repository"})


if __name__ == "__main__":
    unittest.main()
