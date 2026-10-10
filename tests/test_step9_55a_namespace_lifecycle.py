"""Synthetic lifecycle tests; these fixtures contain no benchmark cases."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import run_step9_53_v3_identity_adapter as adapter
from scripts import v3_execution_transaction as transaction


EVALUATION_ID = "synthetic-step9-55a-evaluation"
AUTHORIZATION_ID = "synthetic-step9-55a-authorization"
ATTEMPT_ID = "synthetic-step9-55a-attempt"
AGENT_SHA = "agent-sha"
RUNNER_SHA = "runner-sha"
BENCHMARK_SHA = "benchmark-sha"
ORDER_SHA = "order-sha"
TRANSACTION_ID = "synthetic-step9-55a-transaction"
HISTORICAL_R7_FREEZE = "evaluation/v1_2_3/step9_63a_r1_v3_runner_freeze_r7.json"


def _manifest(path: Path, *, evaluation_id=EVALUATION_ID,
              authorization_id=AUTHORIZATION_ID, attempt_id=ATTEMPT_ID):
    path.write_text(json.dumps({
        "evaluation_id": evaluation_id,
        "authorization_id": authorization_id,
        "attempt_id": attempt_id,
        "status": "ISSUED_NOT_EXECUTED",
        "runner_freeze_revision": "r7",
        "runner_freeze_sha256": adapter.sha256_file(adapter.ROOT / HISTORICAL_R7_FREEZE),
        "consumed": False,
        "consumed_at_utc": None,
    }), encoding="utf-8")
    return path


def _check(root: Path, phase, *, auth=None, attempt=None,
           auth_file=None):
    with mock.patch.object(adapter, "V3_RUNNER_FREEZE_PATH", HISTORICAL_R7_FREEZE), \
         mock.patch.object(adapter, "RUNNER_FREEZE_REVISION", "r7"), \
         mock.patch.object(transaction, "require_committed", return_value={"commit_point": True}), \
         mock.patch.object(adapter, "_assert_identity_unused_in_other_ledgers"), \
         mock.patch("scripts.authorization_lifecycle.assert_not_retired"):
        return adapter._validate_namespace_lifecycle(
        run_root=root,
        evaluation_id=EVALUATION_ID,
        phase=phase,
        authorization_id=auth,
        attempt_id=attempt,
        authorization_file=auth_file,
        treatment_agent_sha256=AGENT_SHA,
        runner_sha256=RUNNER_SHA,
        benchmark_sha256=BENCHMARK_SHA,
        case_count=40,
        case_order_fingerprint_sha256=ORDER_SHA,
        transaction_id=TRANSACTION_ID if phase == adapter.POST_ATTEMPT_CREATION_PRE_FIRST_CASE else None,
        )


def _parent_namespace(root: Path, *, auth=AUTHORIZATION_ID,
                      attempt=ATTEMPT_ID, extra_event=None):
    namespace = root / EVALUATION_ID
    namespace.mkdir(parents=True)
    statuses = ["PREPARED", "AUTHORIZATION_CONSUMED", "FIRST_EVALUATION_ACCESS",
                "CASE_SET_AND_ORDER_VERIFIED"]
    events = []
    for status in statuses:
        event = {
            "evaluation_id": EVALUATION_ID,
            "authorization_id": auth,
            "attempt_id": attempt,
            "transaction_id": TRANSACTION_ID,
            "treatment_agent_sha256": AGENT_SHA,
            "runner_sha256": RUNNER_SHA,
            "cases_started": 0,
            "cases_completed": 0,
            "status": status,
        }
        if status == "FIRST_EVALUATION_ACCESS":
            event.update(dataset_sha256=BENCHMARK_SHA,
                         case_order_fingerprint_sha256=ORDER_SHA)
        if status == "CASE_SET_AND_ORDER_VERIFIED":
            event.update(case_count=40, case_order_fingerprint_sha256=ORDER_SHA)
        events.append(event)
    if extra_event:
        events.append(extra_event)
    (namespace / "attempts.jsonl").write_text(
        "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
    (root / ".namespace_allocation.json").write_text(json.dumps({
        "evaluation_id": EVALUATION_ID, "authorization_id": auth,
        "attempt_id": attempt, "transaction_id": TRANSACTION_ID,
        "namespace_id": root.name,
    }))
    return namespace


class NamespaceLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_namespace_absent_before_attempt_passes(self):
        result = _check(self.root, adapter.PRE_ATTEMPT)
        self.assertTrue(result["namespace_isolated_for_phase"])

    def test_unrelated_namespace_before_attempt_fails_closed(self):
        (self.root / EVALUATION_ID).mkdir()
        with self.assertRaisesRegex(RuntimeError, "namespace already exists"):
            _check(self.root, adapter.PRE_ATTEMPT)

    def test_parent_created_exact_attempt_before_case_passes(self):
        namespace = _parent_namespace(self.root)
        manifest = _manifest(self.root / "authorization.json")
        result = _check(self.root, adapter.POST_ATTEMPT_CREATION_PRE_FIRST_CASE,
                        auth=AUTHORIZATION_ID, attempt=ATTEMPT_ID,
                        auth_file=manifest)
        self.assertTrue(result["current_attempt_exact"])
        self.assertTrue(result["zero_case_counters"])
        self.assertEqual([path.name for path in namespace.iterdir()], ["attempts.jsonl"])

    def test_namespace_for_different_attempt_or_authorization_fails_closed(self):
        for field, value in (("attempt_id", "other-attempt"),
                             ("authorization_id", "other-authorization")):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                kwargs = {field: value}
                _parent_namespace(root, auth=kwargs.get("authorization_id", AUTHORIZATION_ID),
                                  attempt=kwargs.get("attempt_id", ATTEMPT_ID))
                manifest = _manifest(root / "authorization.json",
                                     authorization_id=kwargs.get("authorization_id", AUTHORIZATION_ID),
                                     attempt_id=kwargs.get("attempt_id", ATTEMPT_ID))
                with self.assertRaisesRegex(RuntimeError, "identity/lifecycle mismatch|ledger identity|reservation does not bind"):
                    _check(root, adapter.POST_ATTEMPT_CREATION_PRE_FIRST_CASE,
                           auth=AUTHORIZATION_ID, attempt=ATTEMPT_ID,
                           auth_file=manifest)

    def test_prior_case_result_or_raw_trace_fails_closed(self):
        for filename in ("prior_case_results.jsonl", "prior_raw_traces.jsonl"):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                namespace = _parent_namespace(root)
                (namespace / filename).write_text("synthetic\n", encoding="utf-8")
                manifest = _manifest(root / "authorization.json")
                with self.assertRaisesRegex(RuntimeError, "unexpected or prior output"):
                    _check(root, adapter.POST_ATTEMPT_CREATION_PRE_FIRST_CASE,
                           auth=AUTHORIZATION_ID, attempt=ATTEMPT_ID,
                           auth_file=manifest)

    def test_nonzero_started_counter_fails_closed(self):
        namespace = _parent_namespace(self.root)
        ledger = namespace / "attempts.jsonl"
        events = [json.loads(line) for line in ledger.read_text().splitlines()]
        events[0]["cases_started"] = 1
        ledger.write_text("".join(json.dumps(event) + "\n" for event in events))
        manifest = _manifest(self.root / "authorization.json")
        with self.assertRaisesRegex(RuntimeError, "case counter mismatch"):
            _check(self.root, adapter.POST_ATTEMPT_CREATION_PRE_FIRST_CASE,
                   auth=AUTHORIZATION_ID, attempt=ATTEMPT_ID,
                   auth_file=manifest)

    def test_completed_attempt_fails_closed(self):
        _parent_namespace(self.root, extra_event={"status": "COMPLETED"})
        manifest = _manifest(self.root / "authorization.json")
        with self.assertRaisesRegex(RuntimeError, "exactly at the pre-first-case"):
            _check(self.root, adapter.POST_ATTEMPT_CREATION_PRE_FIRST_CASE,
                   auth=AUTHORIZATION_ID, attempt=ATTEMPT_ID,
                   auth_file=manifest)

    def test_consumed_step954_authorization_cannot_be_reused(self):
        with self.assertRaisesRegex(RuntimeError, "cannot be reused"):
            _check(self.root, adapter.PRE_ATTEMPT,
                   auth=adapter.CONSUMED_STEP9_54_AUTHORIZATION_ID,
                   attempt=ATTEMPT_ID)

    def test_failed_step955_attempt_cannot_be_resumed(self):
        with self.assertRaisesRegex(RuntimeError, "cannot be reused"):
            _check(self.root, adapter.PRE_ATTEMPT,
                   auth=AUTHORIZATION_ID,
                   attempt=adapter.FAILED_STEP9_55_ATTEMPT_ID)

    def test_new_future_authorization_and_attempt_pass_preflight(self):
        manifest = _manifest(self.root / "authorization.json")
        result = _check(self.root, adapter.PRE_ATTEMPT, auth=AUTHORIZATION_ID,
                        attempt=ATTEMPT_ID, auth_file=manifest)
        self.assertTrue(result["namespace_isolated_for_phase"])
        self.assertTrue(result["authorization_lifecycle_valid"])

    def test_missing_authorization_semantic_state_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, "manifest is required"):
            _check(self.root, adapter.PRE_ATTEMPT, auth=AUTHORIZATION_ID,
                   attempt=ATTEMPT_ID)

    def test_parent_callback_is_pre_then_post_create(self):
        from scripts import run_step9_35a_matched_treatment as parent

        phases = []

        def record_validation(**kwargs):
            phases.append(kwargs["lifecycle_phase"])
            return {"all_frozen_hashes_match": True}

        def synthetic_parent_run(*args, **kwargs):
            parent.current_frozen_bindings()
            parent.current_frozen_bindings()
            parent.current_frozen_bindings()

        auth_path = _manifest(self.root / "synthetic-authorization.json",
                              evaluation_id=adapter.EVALUATION_ID)
        original_read_json = adapter.read_json

        def synthetic_read_json(path):
            if path == adapter.ROOT / adapter.V3_RUNNER_FREEZE_PATH:
                return {"bound_identities_sha256": "c" * 64}
            return original_read_json(path)

        with mock.patch.object(adapter, "validate_frozen_v3_identity", record_validation), \
             mock.patch.object(adapter, "_current_evaluation_bindings",
                               return_value={"all_frozen_hashes_match": True}), \
             mock.patch.object(adapter, "_authoritative_authorization_bindings",
                               return_value={"all_frozen_hashes_match": True,
                                             "treatment_runner_sha256": RUNNER_SHA,
                                             "treatment_agent_sha256": AGENT_SHA,
                                             "case_order_fingerprint_sha256": ORDER_SHA}), \
             mock.patch.object(adapter, "GLOBAL_OUT_ROOT", self.root), \
             mock.patch.object(adapter, "OUT_ROOT", self.root), \
             mock.patch.object(adapter, "read_json", side_effect=synthetic_read_json), \
             mock.patch.object(adapter, "resolve_current_freeze",
                               return_value=({"bound_identities_sha256": "c" * 64},
                                             adapter.ROOT / adapter.V3_RUNNER_FREEZE_PATH,
                                             {"runner_freeze_revision": adapter.RUNNER_FREEZE_REVISION,
                                              "runner_freeze_path": adapter.V3_RUNNER_FREEZE_PATH})), \
             mock.patch.object(transaction, "begin_and_commit",
                               side_effect=lambda **kwargs: kwargs["revalidate_under_lock"]()), \
             mock.patch.object(parent, "validate_authorization", return_value=({}, {})), \
             mock.patch.object(parent, "current_v3_freeze", return_value={"bound_identities_sha256": "c" * 64}), \
             mock.patch("scripts.v3_namespace_allocator.derive_namespace_id",
                        return_value="synthetic-namespace"), \
             mock.patch("scripts.v3_namespace_allocator.reserve_namespace",
                        return_value=("synthetic-namespace", self.root / "synthetic-namespace")), \
             mock.patch.object(parent, "run", synthetic_parent_run):
            adapter.run(
                evaluation_id=adapter.EVALUATION_ID,
                authorization_id=AUTHORIZATION_ID,
                attempt_id=ATTEMPT_ID,
                authorization_file=auth_path,
                supplied={},
            )
        self.assertEqual(phases, [
            adapter.PRE_ATTEMPT,
            adapter.PRE_ATTEMPT,
            adapter.PRE_ATTEMPT,
            adapter.PRE_ATTEMPT,
            adapter.POST_ATTEMPT_CREATION_PRE_FIRST_CASE,
        ])
