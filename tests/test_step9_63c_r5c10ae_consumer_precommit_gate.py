"""Step 9.63c-r5c10ae AR-17: r11 formal consumer precommit gate.

Every precommit fact is computed by ``collect_r11_precommit_state`` from real,
read-only checks and evaluated by ``validate_precommit(state, R11_PRECOMMIT_KEYS)``
inside ``prepare_formal_gates`` before ``execute_formal`` imports the identity
adapter or calls ``adapter.run()`` (the first side effect).

Fixtures are temporary roots holding byte copies of the real historical pins,
lifecycle contract/module, ledger and v4 attempt/marker/journal evidence, plus a
synthetic r11 pointer/freeze/authorization. The repository pointer is never created.
Only the identity adapter is replaced, and only through the explicit
``adapter_module`` parameter that formal execution never passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run_step9_63_v3_formal_execution as formal
from scripts import v3_runner_identity as identity
from scripts.preflight_step9_62b_mac_local import SUPPLEMENTAL_HISTORICAL_PINS
from scripts.v3_namespace_allocator import derive_namespace_id

REPO = Path(__file__).resolve().parents[1]
AGENT = "0" * 63 + "a"
AUTH_ID = "auth-step9_63c_r5c10ae-synthetic"
ATTEMPT_ID = "attempt-step9_63c_r5c10ae-synthetic"
EVALUATION_ID = "heldout-v4-step9_55a-treatment-v3-20260930-01"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def listing(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): sha256(p) for p in sorted(root.rglob("*")) if p.is_file()}


class R11PrecommitFixture:
    """Temporary root reproducing every input of collect_r11_precommit_state."""

    def __init__(self, root: Path):
        self.root = root
        inventory = json.loads((REPO / formal.HISTORICAL_INVENTORY_PATH).read_text(encoding="utf-8"))
        transaction_contract = "evaluation/v1_2_3/step9_63a_r1_atomic_commit_contract.json"
        copies = {formal.HISTORICAL_INVENTORY_PATH, formal.LIFECYCLE_LEDGER_PATH, transaction_contract,
                  "scripts/authorization_lifecycle.py", *SUPPLEMENTAL_HISTORICAL_PINS,
                  *(pin["path"] for pin in inventory["historical_pins"].values())}
        runs = REPO / "evaluation/v4_runs"
        copies |= {p.relative_to(REPO).as_posix() for pattern in ("attempts.jsonl", ".namespace_allocation.json")
                   for p in runs.rglob(pattern) if not p.name.startswith("._")}
        copies |= {p.relative_to(REPO).as_posix() for p in (runs / ".execution_transactions").glob("*.jsonl")
                   if not p.name.startswith("._")}
        for rel in sorted(copies):
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / rel, root / rel)
        contract = "evaluation/v1_2_3/step9_61a_v3_authorization_lifecycle_contract.json"
        pointer = root / identity.IDENTITY_CONFIG_PATH
        pointer.write_text(json.dumps({
            "artifact_type": "V3_CURRENT_RUNNER_IDENTITY_POINTER",
            "status": "FROZEN_IDENTITY_POINTER_NOT_AUTHORIZATION",
            "runner_freeze_revision": "r11", "runner_freeze_path": identity.EXPECTED_FREEZE_PATH}))
        self.identity = {"runner_freeze_revision": "r11", "runner_freeze_path": identity.EXPECTED_FREEZE_PATH,
                         "identity_config_sha256": sha256(pointer)}
        bound = {"case_order_fingerprint_sha256": "d" * 64, "case_count": 40,
                 "task_distribution": dict(formal.EXPECTED_DISTRIBUTION)}
        self.freeze = {
            "runner_freeze_revision": "r11", "status": "FROZEN_NOT_AUTHORIZED",
            "formal_entry_runner_sha256": sha256(Path(formal.__file__)), "v3_agent_sha256": AGENT,
            "bound_identities": bound, "bound_identities_sha256": "e" * 64,
            "authorization_lifecycle_contract_path": contract,
            "authorization_lifecycle_contract_sha256": sha256(root / contract),
            "authorization_lifecycle_module_path": "scripts/authorization_lifecycle.py",
            "authorization_lifecycle_module_sha256": sha256(root / "scripts/authorization_lifecycle.py"),
            "transaction_contract_path": transaction_contract,
            "transaction_contract_sha256": sha256(root / transaction_contract),
        }
        self.freeze_path = root / identity.EXPECTED_FREEZE_PATH
        self.freeze_path.write_text(json.dumps(self.freeze))
        self.authorization = {
            "authorization_id": AUTH_ID, "attempt_id": ATTEMPT_ID, "evaluation_id": EVALUATION_ID,
            "treatment": "TREATMENT_V3", "status": "ISSUED_NOT_EXECUTED",
            "authorization_status": "ISSUED_NOT_CONSUMED", "consumed": False,
            "authorization_consumption_count": 0, "runner_freeze_revision": "r11",
            "runner_freeze_path": identity.EXPECTED_FREEZE_PATH, "runner_freeze_sha256": sha256(self.freeze_path),
            "treatment_agent_sha256": AGENT, "frozen_evaluation_identity_sha256": "e" * 64,
            "case_set_fingerprint_sha256": "d" * 64, "case_order_fingerprint_sha256": "d" * 64,
            "case_count": 40, "task_distribution": dict(formal.EXPECTED_DISTRIBUTION),
            "execution_namespace": {"namespace_id": derive_namespace_id(EVALUATION_ID, AUTH_ID, ATTEMPT_ID)},
        }
        self.auth_path = root / "evaluation/v1_2_3/step9_63c_r5c10ae_synthetic_v3_authorization_manifest.json"
        self.write_authorization()
        self.adapter = types.SimpleNamespace(
            current_v3_agent_identity=lambda: (AGENT, True),
            _authoritative_authorization_bindings=lambda: {"all_frozen_hashes_match": True})
        self.preflight = {"dns_ready": True, "tcp_ready": True, "tls_ready": True}
        self.preflight_validated = True

    def write_authorization(self) -> None:
        self.auth_path.write_text(json.dumps(self.authorization))

    def collect(self, adapter="stub") -> dict:
        args = argparse.Namespace(authorization_id=AUTH_ID, attempt_id=ATTEMPT_ID,
                                  authorization_file=self.auth_path)
        with patch.object(formal, "EXPECTED_PROJECT_ROOT", self.root), \
             patch.object(formal, "EXPECTED_PYTHON", Path(formal.sys.executable)):
            return formal.collect_r11_precommit_state(
                args=args, authorization=self.authorization, preflight=self.preflight,
                freeze=self.freeze, freeze_path=self.freeze_path, identity=self.identity,
                preflight_validated=self.preflight_validated, root=self.root,
                adapter_module=self.adapter if adapter == "stub" else adapter)

    def failures(self, **kwargs) -> list[str]:
        return formal.validate_precommit(self.collect(**kwargs), formal.R11_PRECOMMIT_KEYS)


class ConsumerPrecommitGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fx = R11PrecommitFixture(Path(self.temp.name).resolve())
        self.repo_evidence = listing(REPO / "evaluation/v1_2_3")

    def assert_rejected(self, expected: set[str], **kwargs) -> None:
        before = listing(self.fx.root)
        failures = self.fx.failures(**kwargs)
        self.assertTrue(expected <= set(failures), failures)
        self.assertEqual(listing(self.fx.root), before)          # the gate writes nothing
        self.assertEqual(listing(REPO / "evaluation/v1_2_3"), self.repo_evidence)

    # -- positive control: every check can pass on a consistent fixture ------------
    def test_00_consistent_fixture_passes_every_r11_precommit_check(self):
        state = self.fx.collect()
        self.assertEqual(state["checks_not_executed"], [], state["check_errors"])
        self.assertEqual(formal.validate_precommit(state, formal.R11_PRECOMMIT_KEYS), [])
        self.assertEqual(state["active_authorizations"], [AUTH_ID])
        self.assertTrue(all(row["executable"] is False for row in state["superseded_authorizations"]))

    # -- gap G2: 55 historical pins ------------------------------------------------------
    def test_real_repository_historical_pins_verify_55(self):
        self.assertEqual(formal.verify_historical_pins(REPO), 55)

    def test_historical_pin_mismatch_rejected(self):
        pin = self.fx.root / "evaluation/v1_2_3/step9_61a_v3_runner_freeze_r6.json"
        pin.write_bytes(pin.read_bytes() + b" ")
        self.assert_rejected({"historical_integrity_match"})

    def test_inventory_pin_mismatch_rejected(self):
        # The 34 inventory pins and the 20 supplemental pins are checked by separate code.
        inventory = json.loads((self.fx.root / formal.HISTORICAL_INVENTORY_PATH).read_text(encoding="utf-8"))
        supplemental = set(SUPPLEMENTAL_HISTORICAL_PINS)
        relpath = next(pin["path"] for pin in inventory["historical_pins"].values()
                       if pin["path"] not in supplemental)
        target = self.fx.root / relpath
        target.write_bytes(target.read_bytes() + b" ")
        self.assert_rejected({"historical_integrity_match"})
        self.assertIn(relpath, self.fx.collect()["check_errors"]["historical_integrity_match"])

    def test_historical_pin_count_54_rejected(self):
        # Exact analogue of the retired r5 test that fed 54 pins to the gate: dropping one
        # inventory pin leaves every remaining hash valid but the count at 54, not 55.
        path = self.fx.root / formal.HISTORICAL_INVENTORY_PATH
        inventory = json.loads(path.read_text(encoding="utf-8"))
        inventory["historical_pins"].pop(next(iter(inventory["historical_pins"])))
        path.write_text(json.dumps(inventory), encoding="utf-8")
        self.assert_rejected({"historical_integrity_match"})
        self.assertIn("54 != 55", self.fx.collect()["check_errors"]["historical_integrity_match"])

    def test_ledger_prefix_tamper_rejected(self):
        ledger = self.fx.root / formal.LIFECYCLE_LEDGER_PATH
        data = bytearray(ledger.read_bytes()); data[10] ^= 1
        ledger.write_bytes(bytes(data))
        self.assert_rejected({"historical_integrity_match"})

    def test_missing_historical_inventory_is_not_executed_and_rejected(self):
        (self.fx.root / formal.HISTORICAL_INVENTORY_PATH).unlink()
        self.assert_rejected({"historical_integrity_match", "check_not_executed:historical_integrity_match"})

    # -- gap G3: exactly one active authorization, recounted by the consumer -------------
    def test_second_active_authorization_rejected(self):
        second = dict(self.fx.authorization, authorization_id=AUTH_ID + "-2", attempt_id=ATTEMPT_ID + "-2")
        (self.fx.root / "evaluation/v1_2_3/step9_63c_r5c10ae_second_v3_authorization_manifest.json"
         ).write_text(json.dumps(second))
        self.assert_rejected({"exactly_one_active_authorization", "active_authorization_is_bound_id"})

    def test_retired_bound_authorization_rejected(self):
        # The frozen lifecycle.active_authorizations() always reads the repository ledger
        # (no ledger parameter), so a retirement written only to this temporary ledger is
        # seen by the consumer's explicit-ledger reducer check, which must reject it.
        ledger = self.fx.root / formal.LIFECYCLE_LEDGER_PATH
        with ledger.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"authorization_id": AUTH_ID,
                                     "event_type": "AUTHORIZATION_RETIRED_UNCONSUMED_NON_REUSABLE",
                                     "final_status": "RETIRED_UNCONSUMED_NON_REUSABLE",
                                     "authorization_consumed": False,
                                     "authorization_consumption_count": 0}) + "\n")
        self.assert_rejected({"authorization_lifecycle_executable"})

    # -- G7: superseded authorizations must not be executable ---------------------------
    def test_executable_superseded_authorization_rejected(self):
        old = dict(self.fx.authorization, authorization_id="auth-superseded-r10", attempt_id="attempt-superseded",
                   runner_freeze_revision="r10")
        (self.fx.root / "evaluation/v1_2_3/step9_63c_r5c10ae_superseded_v3_authorization_manifest.json"
         ).write_text(json.dumps(old))
        self.assert_rejected({"old_authorization_retired", "old_authorization_non_executable"})

    def test_real_r10_authorization_blocks_r11_until_retired(self):
        name = "evaluation/v1_2_3/step9_63c_r5c6_r10_v3_authorization_manifest.json"
        shutil.copyfile(REPO / name, self.fx.root / name)
        self.assert_rejected({"old_authorization_retired", "old_authorization_non_executable"})

    # -- identity-adapter facts ----------------------------------------------------------
    def test_agent_mismatch_rejected(self):
        self.fx.adapter.current_v3_agent_identity = lambda: ("f" * 64, True)
        self.assert_rejected({"agent_match"})

    def test_frozen_identity_mismatch_rejected(self):
        self.fx.adapter._authoritative_authorization_bindings = lambda: {"all_frozen_hashes_match": False}
        self.assert_rejected({"frozen_identities_match"})

    def test_unavailable_identity_adapter_fails_closed(self):
        # adapter_module=None imports the real frozen adapter, which refuses without a
        # formal r11 pointer: those checks are recorded as not executed and fail.
        self.assert_rejected({"agent_match", "frozen_identities_match",
                              "check_not_executed:agent_match",
                              "check_not_executed:frozen_identities_match"}, adapter=None)

    # -- authorization and namespace facts -----------------------------------------------
    def test_consumed_or_counted_authorization_rejected(self):
        self.fx.authorization.update(consumed=True, authorization_consumption_count=1)
        self.fx.write_authorization()
        self.assert_rejected({"authorization_status_issued_unconsumed",
                              "authorization_consumption_count_zero", "authorization_consumption_count"})

    def test_existing_attempt_rejected(self):
        ledger = self.fx.root / "evaluation/v4_runs/synthetic-prior/attempts.jsonl"
        ledger.parent.mkdir(parents=True)
        ledger.write_text(json.dumps({"attempt_id": ATTEMPT_ID, "authorization_id": "other"}) + "\n")
        self.assert_rejected({"attempt_absent"})

    def test_existing_namespace_rejected(self):
        (self.fx.root / "evaluation/v4_runs" / self.fx.authorization["execution_namespace"]["namespace_id"]).mkdir()
        self.assert_rejected({"namespace_absent"})

    def test_namespace_binding_mismatch_rejected(self):
        self.fx.authorization["execution_namespace"] = {"namespace_id": "heldout-v4-other"}
        self.assert_rejected({"namespace_id_match"})

    def test_case_and_evaluation_identity_mismatch_rejected(self):
        self.fx.authorization.update(case_order_fingerprint_sha256="1" * 64, case_set_fingerprint_sha256="1" * 64,
                                     frozen_evaluation_identity_sha256="1" * 64, task_distribution={"KNOWLEDGE_QA": 40})
        self.assert_rejected({"case_order_match", "case_set_match", "evaluation_identity_match",
                              "task_distribution_match", "task_distribution"})

    # -- freeze, contract, environment, connectivity -------------------------------------
    def test_formal_entry_or_freeze_binding_mismatch_rejected(self):
        self.fx.freeze["formal_entry_runner_sha256"] = "0" * 64
        self.assert_rejected({"runner_freeze_match"})

    def test_lifecycle_contract_tamper_rejected(self):
        contract = self.fx.root / self.fx.freeze["authorization_lifecycle_contract_path"]
        contract.write_bytes(contract.read_bytes() + b" ")
        self.assert_rejected({"lifecycle_contract_match"})

    def test_atomic_commit_contract_tamper_rejected(self):
        contract = self.fx.root / self.fx.freeze["transaction_contract_path"]
        contract.write_bytes(contract.read_bytes() + b" ")
        self.assert_rejected({"atomic_commit_protocol_match", "crash_reconciliation_protocol_match"})

    def test_unvalidated_preflight_rejected(self):
        self.fx.preflight_validated = False
        self.assert_rejected({"fresh_connectivity_pass"})

    def test_wrong_project_root_or_runtime_rejected(self):
        args = argparse.Namespace(authorization_id=AUTH_ID, attempt_id=ATTEMPT_ID,
                                  authorization_file=self.fx.auth_path)
        state = formal.collect_r11_precommit_state(
            args=args, authorization=self.fx.authorization, preflight=self.fx.preflight,
            freeze=self.fx.freeze, freeze_path=self.fx.freeze_path, identity=self.fx.identity,
            preflight_validated=True, root=self.fx.root, adapter_module=self.fx.adapter)
        failures = formal.validate_precommit(state, formal.R11_PRECOMMIT_KEYS)
        self.assertIn("project_root_match", failures)

    # -- validate_precommit semantics ------------------------------------------------------
    def test_missing_key_or_unexecuted_check_fails(self):
        state = self.fx.collect()
        for key in formal.R11_PRECOMMIT_KEYS:
            with self.subTest(key=key):
                broken = dict(state); broken.pop(key)
                self.assertIn(key, formal.validate_precommit(broken, formal.R11_PRECOMMIT_KEYS))
        self.assertIn("check_not_executed:x", formal.validate_precommit(
            dict(state, checks_not_executed=["x"]), formal.R11_PRECOMMIT_KEYS))

    def test_legacy_default_keys_unchanged(self):
        self.assertEqual(len(formal.LEGACY_PRECOMMIT_KEYS), 24)
        self.assertIn("r6_freeze_match", formal.validate_precommit({}))


class ExecuteFormalOrderingTests(unittest.TestCase):
    """execute_formal never reaches the adapter when any precommit check fails."""

    def test_precommit_failure_raises_before_adapter(self):
        gates = {"precommit_failures": ["historical_integrity_match"], "supplied": {}}
        with patch.object(formal, "prepare_formal_gates", return_value=gates):
            import sys
            before = set(sys.modules)
            with self.assertRaisesRegex(RuntimeError, "precommit gate failed closed: historical_integrity_match"):
                formal.execute_formal(argparse.Namespace())
            self.assertNotIn("scripts.run_step9_53_v3_identity_adapter", set(sys.modules) - before)

    def test_gate_runs_before_adapter_import_and_run(self):
        import inspect
        source = inspect.getsource(formal.execute_formal)
        self.assertLess(source.index("prepare_formal_gates("), source.index("run_step9_53_v3_identity_adapter"))
        self.assertLess(source.index("if gates[\"precommit_failures\"]"), source.index("adapter.run("))
        gate_source = inspect.getsource(formal.prepare_formal_gates)
        self.assertIn("validate_precommit(state, R11_PRECOMMIT_KEYS)", gate_source)
        self.assertNotIn("adapter.run(", gate_source)

    def test_main_audit_reports_real_precommit_result(self):
        import contextlib, io
        stream = io.StringIO()
        with patch.object(formal, "audit_current_runner_non_consuming", return_value={"mode": "AUDIT"}), \
             contextlib.redirect_stdout(stream):
            self.assertEqual(formal.main(["--audit-only"]), 0)
        out = json.loads(stream.getvalue())
        self.assertEqual(out["precommit_failures"], ["precommit_not_evaluated:authorization_and_preflight_required"])
        self.assertIs(out["ready_for_controlled_execution"], False)
        self.assertNotIn("atomic_commit_implemented", out)


if __name__ == "__main__":
    unittest.main()
