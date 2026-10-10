"""Step 9.63c-r5c10ah: tests that SUPERSEDE the retired r5c10ae pin and gate tests.

They state the same properties against the current reviewed bytes and the current consumer:
 * the builder's pins equal the reviewed constants and the files' current bytes;
 * the consumer's real precommit gate passes on a correctly issued root, fails closed when a
   historical pin is tampered with, and execute_formal then stops before the adapter.
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path

import r11_activation_fixtures as fx
import r11_gated_fixtures as g
from scripts import build_step9_63c_r11_runner_freeze as builder
from scripts import run_step9_63_v3_formal_execution as formal

REPO = fx.REPO
REVIEWED = {
    "scripts/v3_execution_transaction.py": "f0e74a49d152053b5455951c507edb8f7849a9e4708835711e5975a82e690e91",
    "scripts/v3_runner_identity.py": "a0f5670d3834d5f91391b41a33fbac669d6162587bc620e9bd3acf202aa3c6a5",
    "scripts/run_step9_63_v3_formal_execution.py": "362eb4467fdadd29edc056ecf7b446f2cab99a2d3c407d350b4e91494c5b9528",
}
REVIEWED_ISSUER = "scripts/issue_step9_63c_r11_authorization.py", "f41763f5c82e04360b3d9bcf694e6d05a6fcfa42ae8d71ada29be4ab204e32ab"
T = g.Templates("r11-superseding-")


def setUpModule():
    os.environ[builder.SYNTHETIC_ROOT_ENV] = "1"
    T.build("issued")


def tearDownModule():
    os.environ.pop(builder.SYNTHETIC_ROOT_ENV, None)
    T.close()


class BuilderPinTests(unittest.TestCase):
    """Supersedes r5c10ae BuilderPinTests.test_pins_equal_reviewed_constants_and_current_bytes."""

    def test_pins_equal_reviewed_constants_and_current_bytes(self):
        self.assertEqual(builder.CHANGED_SHA256, REVIEWED)
        self.assertEqual(set(builder.CHANGED_SHA256), builder.CHANGED)
        for relpath, pin in builder.CHANGED_SHA256.items():
            with self.subTest(relpath=relpath):
                self.assertEqual(fx.sha256(REPO / relpath), pin)

    def test_the_issuer_pin_equals_the_reviewed_constant_and_the_current_bytes(self):
        path, sha = REVIEWED_ISSUER
        self.assertEqual(builder.ISSUER_SHA256, sha)
        self.assertEqual(fx.sha256(REPO / path), sha)
        self.assertEqual(builder.ISSUER_PATH, path)


class ConsumerGateTests(unittest.TestCase):
    """Supersedes r5c10ae ExecuteFormalOrderingTests.test_prepare_formal_gates_reports_real_precommit_failures."""

    def test_the_real_gate_passes_on_a_correctly_issued_root(self):
        root = T.clone("issued")
        failures = g.with_gate(root, lambda args: formal.prepare_formal_gates(args)["precommit_failures"])
        self.assertEqual(failures, [])

    def test_a_tampered_historical_pin_fails_closed_and_execute_formal_stops_before_the_adapter(self):
        root = T.clone("issued")
        pin = root / "evaluation/v1_2_3/step9_61a_v3_runner_freeze_r6.json"
        pin.write_bytes(pin.read_bytes() + b" ")
        failures = g.with_gate(root, lambda args: formal.prepare_formal_gates(args)["precommit_failures"])
        self.assertIn("historical_integrity_match", failures)
        with self.assertRaisesRegex(RuntimeError, "precommit gate failed closed: .*historical_integrity_match"):
            g.with_gate(root, formal.execute_formal)

    def test_a_missing_issuance_event_fails_closed_through_the_same_path(self):
        root = T.clone("issued")
        lines = fx.ledger_lines(root)
        del lines[fx.issued_event_index(root)]
        fx.write_ledger(root, lines)
        failures = g.with_gate(root, lambda args: formal.prepare_formal_gates(args)["precommit_failures"])
        self.assertIn(formal.ISSUANCE_KEY, failures)
        with self.assertRaisesRegex(RuntimeError, "precommit gate failed closed"):
            g.with_gate(root, formal.execute_formal)


if __name__ == "__main__":
    unittest.main()
