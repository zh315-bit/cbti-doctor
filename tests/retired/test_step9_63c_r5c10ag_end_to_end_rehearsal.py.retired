"""Step 9.63c-r5c10ag: end-to-end activation rehearsal on a temporary root.

AR-14 -> signed approval -> pointer -> Freeze -> issuance -> consumer precommit gate.
The gate is evaluated but formal execution is never entered. Negative rehearsals show the
consumer rejecting an authorization that was not issued through the issuer.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import r11_activation_fixtures as fx
from scripts import authorization_lifecycle as lifecycle
from scripts import build_step9_63c_r11_runner_freeze as builder
from scripts import issue_step9_63c_r11_authorization as issuer
from scripts import run_step9_63_v3_formal_execution as formal

_TMP = None


def setUpModule():
    global _TMP
    os.environ[builder.SYNTHETIC_ROOT_ENV] = "1"
    _TMP = tempfile.TemporaryDirectory(prefix="r11-e2e-")


def tearDownModule():
    os.environ.pop(builder.SYNTHETIC_ROOT_ENV, None)
    _TMP.cleanup()


def fresh(name):
    return fx.build_root(Path(_TMP.name) / name)


class FullRehearsal(unittest.TestCase):
    def test_full_flow_ends_with_exactly_one_active_authorization_and_a_passing_gate(self):
        root = fresh("full")
        states = [builder.identity_status(root)["state"]]
        self.assertEqual(states[-1], "S0_NOT_ACTIVATED")
        # The gate refuses before anything is done (r10 authorization still executable, nothing issued).
        self.assertFalse(builder.plan_identity_pointer(root)["ready"])
        # AR-14 rehearsal with the frozen retirement function
        fx.retire_r10(root)
        approval = fx.sign_approval(root)
        self.assertTrue(builder.plan_identity_pointer(root)["ready"])
        # pointer (real terminal, typed token)
        code, output = fx.create_pointer(root)
        self.assertEqual(code, 0, output)
        self.assertEqual(builder.identity_status(root)["state"], "S1_POINTER_ONLY")
        self.assertTrue(builder.verify_identity_pointer(root)["ok"])
        self.assertEqual(lifecycle.active_authorizations(root), [])  # r10 retired, nothing issued
        # Freeze
        digest = fx.persist_freeze(root, approval)
        self.assertEqual(builder.identity_status(root)["state"], "S2_FREEZE_PERSISTED")
        self.assertEqual(fx.sha256(root / builder.EXPECTED_FREEZE_PATH), approval["freeze"]["predicted_sha256"])
        self.assertTrue(builder.verify_persisted_candidate(root)["ok"])
        # the consumer gate must still refuse: no authorization exists yet
        self.assertEqual(issuer.issuance_status(root)["state"], "NOT_ISSUED")
        # issuance
        plan = issuer.plan_issuance(root)
        self.assertTrue(plan["ready"], plan)
        code, output = fx.issue(root, plan["confirmation_token"])
        self.assertEqual(code, 0, output)
        status = issuer.issuance_status(root)
        self.assertEqual(status["state"], "ISSUED_RECORDED")
        verified = issuer.verify_issuance(root)
        self.assertTrue(verified["ok"], verified)
        manifest = json.loads((root / issuer.MANIFEST_RELATIVE).read_text())
        self.assertEqual(lifecycle.active_authorizations(root), [manifest["authorization_id"]])
        # consumer precommit gate passes; formal execution is never entered
        failures, state = fx.gate_failures(root)
        self.assertEqual(failures, [])
        self.assertIs(state[formal.ISSUANCE_KEY], True)
        self.assertFalse((root / "evaluation/v4_runs" / manifest["execution_namespace"]["namespace_id"]).exists())
        self.assertFalse(any(manifest["attempt_id"] in p.read_text() for p in (root / "evaluation/v4_runs").rglob("attempts.jsonl")))

    def test_the_rehearsal_never_touches_the_real_repository(self):
        ledger = fx.REPO / builder.LEDGER_PATH
        before = fx.sha256(ledger)
        root = fresh("isolation")
        fx.retire_r10(root)
        fx.sign_approval(root)
        self.assertEqual(fx.sha256(ledger), before)
        for relative in (builder.IDENTITY_CONFIG_PATH, builder.EXPECTED_FREEZE_PATH, builder.REGISTRY_PATH,
                         builder.AUTHORIZATION_MANIFEST_PATH, builder.APPROVAL_PATH):
            self.assertFalse((fx.REPO / relative).exists(), relative)


class NegativeRehearsals(unittest.TestCase):
    def issued(self, name):
        root, _ = fx.fully_issued(Path(_TMP.name) / name)
        return root

    def test_removing_the_issuance_event_makes_the_consumer_reject(self):
        root = self.issued("neg-remove")
        self.assertEqual(fx.gate_failures(root)[0], [])
        lines = fx.ledger_lines(root)
        del lines[fx.issued_event_index(root)]
        fx.write_ledger(root, lines)
        self.assertIn(formal.ISSUANCE_KEY, fx.gate_failures(root)[0])
        self.assertEqual(issuer.issuance_status(root)["state"], "ISSUED_UNRECORDED")

    def test_a_hand_written_manifest_is_rejected(self):
        root = fresh("neg-hand")
        fx.retire_r10(root)
        approval = fx.sign_approval(root)
        self.assertEqual(fx.create_pointer(root)[0], 0)
        fx.persist_freeze(root, approval)
        # A person writes the manifest by hand instead of using the issuer.
        template = json.loads((root / builder.R10_AUTHORIZATION_PATH).read_text())
        template.update(approval["issuance"] | {})
        template["authorization_id"] = approval["issuance"]["authorization_id"]
        template["attempt_id"] = approval["issuance"]["attempt_id"]
        template["runner_freeze_revision"] = "r11"
        template["runner_freeze_path"] = builder.EXPECTED_FREEZE_PATH
        template["runner_freeze_sha256"] = fx.sha256(root / builder.EXPECTED_FREEZE_PATH)
        template["execution_namespace"]["namespace_id"] = approval["issuance"]["namespace_id"]
        (root / issuer.MANIFEST_RELATIVE).write_text(json.dumps(template, indent=2, sort_keys=True) + "\n")
        self.assertEqual(issuer.issuance_status(root)["state"], "ISSUED_UNRECORDED")
        self.assertIn(formal.ISSUANCE_KEY, fx.gate_failures(root)[0])
        self.assertFalse(issuer.verify_issuance(root)["ok"])

    def test_a_duplicate_issuance_makes_the_consumer_reject(self):
        root = self.issued("neg-dup")
        self.assertEqual(fx.gate_failures(root)[0], [])
        lines = fx.ledger_lines(root)
        lines.append(lines[fx.issued_event_index(root)])
        fx.write_ledger(root, lines)
        self.assertIn(formal.ISSUANCE_KEY, fx.gate_failures(root)[0])
        self.assertEqual(issuer.issuance_status(root)["state"], "ANOMALY_DUPLICATE_EVENT")
        # and the issuer will not issue another
        self.assertFalse(issuer.plan_issuance(root)["ready"])


if __name__ == "__main__":
    unittest.main()
