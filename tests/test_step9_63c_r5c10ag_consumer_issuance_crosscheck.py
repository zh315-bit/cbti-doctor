"""Step 9.63c-r5c10ag, D13-4: the consumer precommit gate cross-checks the ledger against the manifest.

Temporary roots only; the real consumer gate (prepare_formal_gates) runs against them.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import r11_activation_fixtures as fx
from scripts import build_step9_63c_r11_runner_freeze as builder
from scripts import run_step9_63_v3_formal_execution as formal

_TMP = None
_ISSUED = None
_S2 = None


def setUpModule():
    global _TMP, _ISSUED, _S2
    os.environ[builder.SYNTHETIC_ROOT_ENV] = "1"
    _TMP = tempfile.TemporaryDirectory(prefix="r11-consumer-xcheck-")
    base = Path(_TMP.name)
    _ISSUED, _ = fx.fully_issued(base / "issued")
    _S2 = _ISSUED  # the issued root is also the source for derived negative roots


def tearDownModule():
    os.environ.pop(builder.SYNTHETIC_ROOT_ENV, None)
    _TMP.cleanup()


def issued_clone() -> Path:
    target = Path(tempfile.mkdtemp(dir=_TMP.name)) / "root"
    shutil.copytree(_ISSUED, target)
    return target


def issued_index(root):
    return fx.issued_event_index(root)


class CrossCheckTests(unittest.TestCase):
    def test_positive_control_gate_passes_with_one_matching_event(self):
        failures, state = fx.gate_failures(issued_clone())
        self.assertEqual(failures, [])
        self.assertIs(state[formal.ISSUANCE_KEY], True)

    def test_missing_event_fails_closed(self):
        root = issued_clone()
        lines = fx.ledger_lines(root)
        del lines[issued_index(root)]
        fx.write_ledger(root, lines)
        failures, _ = fx.gate_failures(root)
        self.assertIn(formal.ISSUANCE_KEY, failures)

    def test_hand_written_manifest_without_issuance_is_rejected(self):
        root = issued_clone()
        lines = fx.ledger_lines(root)
        del lines[issued_index(root)]
        fx.write_ledger(root, lines)
        manifest = json.loads((root / builder.AUTHORIZATION_MANIFEST_PATH).read_text())
        (root / builder.AUTHORIZATION_MANIFEST_PATH).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        failures, _ = fx.gate_failures(root)
        self.assertIn(formal.ISSUANCE_KEY, failures)

    def test_duplicate_event_fails_closed(self):
        root = issued_clone()
        lines = fx.ledger_lines(root)
        lines.append(lines[issued_index(root)])
        fx.write_ledger(root, lines)
        failures, _ = fx.gate_failures(root)
        self.assertIn(formal.ISSUANCE_KEY, failures)

    def test_second_event_for_the_same_authorization_with_another_attempt_is_rejected(self):
        root = issued_clone()
        lines = fx.ledger_lines(root)
        event = json.loads(lines[issued_index(root)])
        event["attempt_id"] = "attempt-step9_63c_r11-" + "8" * 32
        event["lifecycle_event_id"] = "issued-" + "8" * 32
        lines.append(json.dumps(event, sort_keys=True) + "\n")
        fx.write_ledger(root, lines)
        failures, _ = fx.gate_failures(root)
        self.assertIn(formal.ISSUANCE_KEY, failures)

    def test_mismatching_fields_fail_closed(self):
        for key, value in (("authorization_manifest_sha256", "0" * 64), ("authorization_id", "auth-other"),
                           ("attempt_id", "attempt-other"), ("evaluation_id", "eval-other"),
                           ("runner_freeze_sha256", "1" * 64), ("runner_freeze_revision", "r10"),
                           ("authorization_manifest_path", "evaluation/v1_2_3/other.json"),
                           ("authorization_consumed", True), ("authorization_consumption_count", 1)):
            with self.subTest(field=key):
                root = issued_clone()
                lines = fx.ledger_lines(root)
                index = issued_index(root)
                event = json.loads(lines[index])
                event[key] = value
                lines[index] = json.dumps(event, sort_keys=True) + "\n"
                fx.write_ledger(root, lines)
                failures, _ = fx.gate_failures(root)
                self.assertIn(formal.ISSUANCE_KEY, failures)

    def test_manifest_edited_after_issuance_is_rejected(self):
        root = issued_clone()
        path = root / builder.AUTHORIZATION_MANIFEST_PATH
        path.write_bytes(path.read_bytes() + b" ")
        failures, _ = fx.gate_failures(root)
        self.assertIn(formal.ISSUANCE_KEY, failures)

    def test_another_event_reusing_the_attempt_identity_is_rejected(self):
        root = issued_clone()
        lines = fx.ledger_lines(root)
        event = json.loads(lines[issued_index(root)])
        event["authorization_id"] = "auth-step9_63c_r11-" + "9" * 32
        lines.append(json.dumps(event, sort_keys=True) + "\n")
        fx.write_ledger(root, lines)
        failures, _ = fx.gate_failures(root)
        self.assertIn(formal.ISSUANCE_KEY, failures)

    def test_unreadable_ledger_is_not_a_pass(self):
        root = issued_clone()
        with patch.object(formal.__dict__.get("lifecycle", None) or __import__("scripts.authorization_lifecycle", fromlist=["x"]),
                          "_events", side_effect=OSError("boom")):
            try:
                failures, _ = fx.gate_failures(root)
            except Exception:
                return  # raising is also fail-closed
            self.assertIn(formal.ISSUANCE_KEY, failures)

    def test_event_for_another_manifest_path_is_rejected(self):
        root = issued_clone()
        other = root / "evaluation/v1_2_3/copy_of_manifest.json"
        shutil.copyfile(root / builder.AUTHORIZATION_MANIFEST_PATH, other)
        ok, reason = formal.verify_issuance_event(root, json.loads(other.read_text()), other)
        self.assertFalse(ok)
        self.assertIn("authorization_manifest_path", reason)

    def test_precommit_key_list_is_unchanged_and_the_check_is_additive(self):
        self.assertEqual(len(formal.R11_PRECOMMIT_KEYS), 25)
        self.assertNotIn(formal.ISSUANCE_KEY, formal.R11_PRECOMMIT_KEYS)
        self.assertEqual(formal.validate_issuance_cross_check({formal.ISSUANCE_KEY: True}), [])
        self.assertEqual(formal.validate_issuance_cross_check({formal.ISSUANCE_KEY: False}), [formal.ISSUANCE_KEY])
        self.assertEqual(formal.validate_issuance_cross_check({}), [formal.ISSUANCE_KEY])
        self.assertEqual(formal.validate_issuance_cross_check({formal.ISSUANCE_KEY: "yes"}), [formal.ISSUANCE_KEY])

    def test_execute_formal_stops_before_the_adapter_when_the_check_fails(self):
        import sys
        import types
        from unittest.mock import MagicMock
        fake = types.ModuleType("scripts.run_step9_53_v3_identity_adapter")
        fake.run = MagicMock()
        args = types.SimpleNamespace(evaluation_id="e", authorization_id="a", attempt_id="t", authorization_file=Path("m"))
        scripts_pkg = __import__("scripts")
        with patch.dict(sys.modules, {"scripts.run_step9_53_v3_identity_adapter": fake}), \
                patch.object(scripts_pkg, "run_step9_53_v3_identity_adapter", fake, create=True):
            with patch.object(formal, "prepare_formal_gates", return_value={"precommit_failures": [formal.ISSUANCE_KEY], "supplied": {}}):
                with self.assertRaisesRegex(RuntimeError, formal.ISSUANCE_KEY):
                    formal.execute_formal(args)
            fake.run.assert_not_called()
            with patch.object(formal, "prepare_formal_gates", return_value={"precommit_failures": [], "supplied": {}}):
                formal.execute_formal(args)  # positive control: the adapter is reached only when nothing failed
            fake.run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
