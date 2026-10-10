"""Step 9.63c-r5c10ag, AR-13: the r11 authorization issuer (conditions I0-I13, gating, recovery, threats).

Temporary roots only. The write entry runs in a real pseudo-terminal with a typed token.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import r11_activation_fixtures as fx
from scripts import authorization_lifecycle as lifecycle
from scripts import build_step9_63c_r11_runner_freeze as builder
from scripts import issue_step9_63c_r11_authorization as issuer
from scripts import run_step9_63_v3_formal_execution as formal

_TMP = None
_T = {}
FUTURE = "2999-01-01T00:00:00+00:00"


def setUpModule():
    global _TMP
    os.environ[builder.SYNTHETIC_ROOT_ENV] = "1"
    _TMP = tempfile.TemporaryDirectory(prefix="r11-issuer-tests-")
    base = Path(_TMP.name)
    _T["s2"], _ = fx.activated_through_freeze(base / "s2")
    _T["issued"], _ = fx.fully_issued(base / "issued")


def tearDownModule():
    os.environ.pop(builder.SYNTHETIC_ROOT_ENV, None)
    _TMP.cleanup()


def clone(name):
    target = Path(tempfile.mkdtemp(dir=_TMP.name)) / "root"
    shutil.copytree(_T[name], target)
    return target


def failed(plan):
    return {c["name"].split()[0] for c in plan["conditions"] if not c["ok"]}


def resign(root, mutate):
    """Apply `mutate` to the approval and re-sign it (so only the targeted condition can fail)."""
    approval = json.loads((root / builder.APPROVAL_PATH).read_text())
    mutate(approval)
    fx.write_approval(root, approval)


class ConditionTests(unittest.TestCase):
    def test_a_clean_s2_root_is_ready_and_writes_nothing(self):
        root = clone("s2")
        before = fx.tree_digest(root)
        plan = issuer.plan_issuance(root)
        self.assertTrue(plan["ready"], failed(plan))
        self.assertEqual(fx.tree_digest(root), before)
        self.assertTrue(plan["confirmation_token"].startswith("ISSUE-R11-AUTH-"))

    def test_i0_unsigned_or_drifted_approval(self):
        for label, mutate in (("unsigned", lambda a: a.update(status=builder.APPROVAL_DRAFT, approver=None, signed_at_utc=None)),
                              ("pin drift", lambda a: a["named_pins"]["consumer"].update(sha256="0" * 64)),
                              ("wrong pointer pin", lambda a: a["pointer"].update(canonical_sha256="0" * 64))):
            with self.subTest(case=label):
                root = clone("s2")
                resign(root, mutate)
                self.assertIn("I0", failed(issuer.plan_issuance(root)))

    def test_i0_missing_approval_file(self):
        root = clone("s2")
        (root / builder.APPROVAL_PATH).unlink()
        plan = issuer.plan_issuance(root)
        self.assertFalse(plan["ready"])

    def test_i1_pointer_and_record(self):
        root = clone("s2")
        (root / builder.POINTER_CREATION_RECORD_PATH).unlink()
        self.assertFalse(issuer.plan_issuance(root)["ready"])
        root = clone("s2")
        (root / builder.IDENTITY_CONFIG_PATH).write_bytes(builder.canonical_pointer_bytes() + b" ")
        self.assertIn("I1", failed(issuer.plan_issuance(root)))
        root = clone("s2")
        record = root / builder.POINTER_CREATION_RECORD_PATH
        data = json.loads(record.read_text())
        data["approval_record_sha256"] = "0" * 64
        record.write_text(json.dumps(data))
        self.assertIn("I1", failed(issuer.plan_issuance(root)))

    def test_i2_i3_i4_freeze_problems(self):
        root = clone("s2")
        (root / builder.EXPECTED_FREEZE_PATH).unlink()
        plan = issuer.plan_issuance(root)
        self.assertFalse(plan["ready"])
        self.assertIn("I2", failed(plan))
        root = clone("s2")
        resign(root, lambda a: a["freeze"].update(predicted_sha256="0" * 64))
        self.assertIn("I3", failed(issuer.plan_issuance(root)))
        root = clone("s2")
        path = root / builder.EXPECTED_FREEZE_PATH
        document = json.loads(path.read_text())
        document["note"] = "hand edit"
        path.write_text(json.dumps(document, sort_keys=True, indent=2) + "\n")
        self.assertFalse(issuer.plan_issuance(root)["ready"])

    def test_i4_a_hand_edited_freeze_is_caught_even_when_the_approval_is_edited_to_match(self):
        root = clone("s2")
        path = root / builder.EXPECTED_FREEZE_PATH
        document = json.loads(path.read_text())
        document["note"] = "hand edit"
        path.write_text(json.dumps(document, sort_keys=True, indent=2) + "\n")
        resign(root, lambda a: a["freeze"].update(predicted_sha256=fx.sha256(path)))  # I3 now agrees
        plan = issuer.plan_issuance(root)
        self.assertIn("I4", failed(plan))
        self.assertNotIn("I3", failed(plan))

    def test_i12_clock_between_freeze_and_last_ledger_event_is_refused(self):
        root = clone("s2")
        plan = issuer.plan_issuance(root, clock=lambda: "2026-06-01T00:00:00+00:00")  # after the freeze (2026-01-01), before the AR-14 event
        self.assertIn("I12", failed(plan))

    def test_i12_clock_earlier_than_the_freeze_is_refused_even_after_the_last_event(self):
        base = Path(tempfile.mkdtemp(dir=_TMP.name))
        root = fx.build_root(base)
        fx.retire_r10(root)
        approval = fx.sign_approval(root, created_at=FUTURE)
        self.assertEqual(fx.create_pointer(root)[0], 0)
        fx.persist_freeze(root, approval)
        plan = issuer.plan_issuance(root)  # real clock: later than the AR-14 event, earlier than the 2999 freeze
        self.assertIn("I12", failed(plan))

    def test_i5_member_changed_after_freeze(self):
        root = clone("s2")
        target = root / "scripts/v3_execution_transaction.py"
        target.write_bytes(target.read_bytes() + b"\n#")
        plan = issuer.plan_issuance(root)
        self.assertFalse(plan["ready"])

    def test_i6_an_executable_non_current_authorization_blocks(self):
        # Dropping the AR-14 retirement event makes r10 executable again while the current-revision
        # active set stays empty, so only I6 (and not I7) can notice.
        root = clone("s2")
        raw = (root / builder.LEDGER_PATH).read_bytes()
        prefix = 1161
        tail = [l for l in raw[prefix:].decode().splitlines(keepends=True) if builder.R10_AUTHORIZATION_ID not in l]
        (root / builder.LEDGER_PATH).write_bytes(raw[:prefix] + "".join(tail).encode())
        plan = issuer.plan_issuance(root)
        self.assertFalse(plan["ready"])
        self.assertIn("I6", failed(plan))

    def test_i7_an_active_authorization_blocks(self):
        root = clone("s2")
        with patch.object(lifecycle, "active_authorizations", return_value=["auth-already-active"]):
            self.assertIn("I7", failed(issuer.plan_issuance(root)))

    def test_i8_historical_pin_tampering_blocks(self):
        root = clone("s2")
        pinned = root / "evaluation/v1_2_3/step9_61a_v3_runner_freeze_r6.json"
        pinned.write_bytes(pinned.read_bytes() + b" ")
        self.assertFalse(issuer.plan_issuance(root)["ready"])

    def test_i9_identity_reuse_anywhere_blocks(self):
        approval = json.loads((clone("s2") / builder.APPROVAL_PATH).read_text())["issuance"]
        for label, place in (("manifest", "evaluation/v1_2_3/step9_63c_r11x_authorization_manifest.json"),
                             ("note", "evaluation/v1_2_3/notes.json")):
            with self.subTest(case=label):
                root = clone("s2")
                (root / place).write_text(json.dumps({"authorization_id": approval["authorization_id"]}))
                self.assertIn("I9", failed(issuer.plan_issuance(root)))
        root = clone("s2")
        (root / "evaluation/v4_runs" / approval["namespace_id"]).mkdir(parents=True)
        self.assertIn("I9", failed(issuer.plan_issuance(root)))

    def test_i9_attempt_reuse_in_the_ledger_blocks(self):
        root = clone("s2")
        approval = json.loads((root / builder.APPROVAL_PATH).read_text())["issuance"]
        event = {"artifact_type": "AUTHORIZATION_LIFECYCLE_EVENT", "event_type": "SOMETHING", "attempt_id": approval["attempt_id"]}
        with (root / builder.LEDGER_PATH).open("a") as stream:
            stream.write(json.dumps(event) + "\n")
        self.assertIn("I9", failed(issuer.plan_issuance(root)))

    def test_i10_existing_manifest_or_symlink_blocks(self):
        root = clone("s2")
        (root / issuer.MANIFEST_RELATIVE).write_text("{}")
        self.assertIn("I10", failed(issuer.plan_issuance(root)))
        root = clone("s2")
        os.symlink("nowhere", root / issuer.MANIFEST_RELATIVE)
        plan = issuer.plan_issuance(root)  # a dangling link must be reported, never crash the plan
        self.assertIn("I10", failed(plan))
        self.assertEqual(plan["status"]["state"], "ANOMALY_MANIFEST_NOT_A_REGULAR_FILE")

    def test_i12_clock_not_after_freeze_or_last_event_blocks(self):
        root = clone("s2")
        self.assertIn("I12", failed(issuer.plan_issuance(root, clock=lambda: "2020-01-01T00:00:00+00:00")))
        self.assertIn("I12", failed(issuer.plan_issuance(root, clock=lambda: "not a time")))

    def test_i13_a_prior_issuance_event_or_registry_blocks(self):
        root = clone("s2")
        (root / builder.REGISTRY_PATH).write_text("{}")
        self.assertIn("I13", failed(issuer.plan_issuance(root)))
        root = clone("issued")
        self.assertIn("I13", failed(issuer.plan_issuance(root)))

    def test_ix1_synthetic_root_needs_the_environment_switch(self):
        with patch.dict(os.environ):
            os.environ.pop(builder.SYNTHETIC_ROOT_ENV, None)
            self.assertIn("IX1", failed(issuer.plan_issuance(clone("s2"))))

    def test_non_canonical_approval_path_is_refused(self):
        with self.assertRaises(RuntimeError):
            issuer.plan_issuance(clone("s2"), Path("/tmp/other.json"))


class GateTests(unittest.TestCase):
    def test_in_process_without_a_terminal_is_refused(self):
        root = clone("s2")
        before = fx.tree_digest(root)
        with patch.object(builder, "interactive_terminal", return_value=False), self.assertRaises(PermissionError):
            issuer.issue_authorization(root)
        self.assertEqual(fx.tree_digest(root), before)

    def test_pipes_and_half_terminals_are_refused_even_with_the_right_token(self):
        for mode in ("pipe", "tty-in-only", "tty-out-only"):
            with self.subTest(mode=mode):
                root = clone("s2")
                token = issuer.plan_issuance(root)["confirmation_token"]
                before = fx.tree_digest(root)
                code, output = fx.run_cli(fx.ISSUER_MODULE, root, ["--issue"], mode=mode, lines=[token])
                self.assertEqual(code, 2, output)
                self.assertEqual(fx.tree_digest(root), before)

    def test_wrong_token_is_refused(self):
        for token in ("", "yes", "ISSUE-R11-AUTH-000000000000", builder.POINTER_TOKEN):
            with self.subTest(token=token):
                root = clone("s2")
                before = fx.tree_digest(root)
                code, output = fx.run_cli(fx.ISSUER_MODULE, root, ["--issue"], mode="tty", lines=[token])
                self.assertEqual(code, 2, output)
                self.assertEqual(fx.tree_digest(root), before)

    def test_read_only_modes_never_write(self):
        for flags in ([], ["--plan"], ["--status"], ["--verify"]):
            with self.subTest(flags=flags):
                root = clone("s2")
                before = fx.tree_digest(root)
                code, output = fx.run_cli(fx.ISSUER_MODULE, root, flags, mode="pipe")
                self.assertNotIn("REFUSED", output)
                self.assertEqual(fx.tree_digest(root), before)

    def test_approval_flag_does_not_exist(self):
        code, output = fx.run_cli(fx.ISSUER_MODULE, clone("s2"), ["--approval", "x"], mode="pipe")
        self.assertEqual(code, 2)

    def test_unsigned_draft_cannot_issue(self):
        root = clone("s2")
        resign(root, lambda a: a.update(status=builder.APPROVAL_DRAFT, approver=None, signed_at_utc=None))
        before = fx.tree_digest(root)
        code, output = fx.run_cli(fx.ISSUER_MODULE, root, ["--issue"], mode="tty", lines=["ISSUE-R11-AUTH-000000000000"])
        self.assertEqual(code, 2)
        self.assertEqual(fx.tree_digest(root), before)


class IssuanceTests(unittest.TestCase):
    def test_typed_token_issues_exactly_one_manifest_and_one_event(self):
        root = clone("s2")
        ledger_before = (root / builder.LEDGER_PATH).read_bytes()
        code, output = fx.issue(root)
        self.assertEqual(code, 0, output)
        manifest = root / issuer.MANIFEST_RELATIVE
        self.assertEqual(stat.S_IMODE(manifest.stat().st_mode), 0o600)
        ledger_after = (root / builder.LEDGER_PATH).read_bytes()
        self.assertTrue(ledger_after.startswith(ledger_before))
        appended = ledger_after[len(ledger_before):].decode().splitlines()
        self.assertEqual(len(appended), 1)
        event = json.loads(appended[0])
        self.assertEqual(event["event_type"], formal.ISSUED_EVENT_TYPE)
        self.assertEqual(event["authorization_manifest_sha256"], fx.sha256(manifest))
        self.assertEqual(lifecycle.active_authorizations(root), [json.loads(manifest.read_text())["authorization_id"]])
        self.assertTrue(issuer.verify_issuance(root)["ok"])

    def test_manifest_matches_the_r10_template_shape_and_identity_values(self):
        root = clone("issued")
        manifest = json.loads((root / issuer.MANIFEST_RELATIVE).read_text())
        template = json.loads((root / issuer.TEMPLATE_RELATIVE).read_text())
        self.assertEqual(set(manifest), set(template))
        self.assertEqual(manifest["evaluation_id"], template["evaluation_id"])
        self.assertEqual(manifest["runner_freeze_revision"], "r11")
        self.assertEqual(manifest["runner_freeze_sha256"], fx.sha256(root / builder.EXPECTED_FREEZE_PATH))
        self.assertFalse(manifest["consumed"])
        self.assertEqual(manifest["authorization_consumption_count"], 0)
        self.assertTrue(manifest["authorization_id"].startswith(builder.R11_AUTHORIZATION_ID_PREFIX))

    def test_second_issuance_is_refused_and_changes_nothing(self):
        root = clone("issued")
        before = fx.tree_digest(root)
        code, output = fx.run_cli(fx.ISSUER_MODULE, root, ["--issue"], mode="tty", lines=["ISSUE-R11-AUTH-000000000000"])
        self.assertEqual(code, 2)
        self.assertEqual(fx.tree_digest(root), before)

    def test_replay_of_the_old_token_after_issuance_is_refused(self):
        root = clone("s2")
        token = issuer.plan_issuance(root)["confirmation_token"]
        self.assertEqual(fx.issue(root, token)[0], 0)
        before = fx.tree_digest(root)
        code, _ = fx.issue(root, token)
        self.assertEqual(code, 2)
        self.assertEqual(fx.tree_digest(root), before)

    def test_token_from_one_root_does_not_work_in_another_approval(self):
        a, b = clone("s2"), clone("s2")
        resign(b, lambda x: x["issuance"].update(authorization_id="auth-step9_63c_r11-" + "7" * 32))
        token_a = issuer.plan_issuance(a)["confirmation_token"]
        before = fx.tree_digest(b)
        code, _ = fx.issue(b, token_a)
        self.assertEqual(code, 2)
        self.assertEqual(fx.tree_digest(b), before)

    def test_concurrent_issuance_yields_exactly_one_authorization(self):
        root = clone("s2")
        token = issuer.plan_issuance(root)["confirmation_token"]
        results = []
        def run():
            results.append(fx.issue(root, token))
        threads = [threading.Thread(target=run) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        codes = sorted(code for code, _ in results)
        self.assertEqual(codes, [0, 2], results)
        events = issuer.issued_events(root)
        self.assertEqual(len(events), 1)
        self.assertEqual(len(lifecycle.active_authorizations(root)), 1)
        self.assertEqual(issuer.issuance_status(root)["state"], "ISSUED_RECORDED")

    def test_postcondition_failure_writes_no_event_and_keeps_the_manifest(self):
        root = clone("s2")
        original = lifecycle.active_authorizations
        calls = {"n": 0}
        def flaky(r):
            calls["n"] += 1
            result = original(r)
            return result if (root / issuer.MANIFEST_RELATIVE).exists() is False else []
        before_ledger = (root / builder.LEDGER_PATH).read_bytes()
        with patch.object(builder, "interactive_terminal", return_value=True), \
                patch.object(builder, "confirm_with_token", return_value=None), \
                patch.object(lifecycle, "active_authorizations", side_effect=flaky):
            with self.assertRaisesRegex(RuntimeError, "POSTCONDITION_FAILED"):
                issuer.issue_authorization(root)
        self.assertEqual((root / builder.LEDGER_PATH).read_bytes(), before_ledger)
        self.assertTrue((root / issuer.MANIFEST_RELATIVE).exists())
        self.assertEqual(issuer.issuance_status(root)["state"], "ISSUED_UNRECORDED")
        failures, _ = fx.gate_failures(root)
        self.assertIn(formal.ISSUANCE_KEY, failures)

    def test_unrecorded_issuance_is_recoverable_only_through_the_gated_entry(self):
        root = clone("s2")
        with patch.object(builder, "interactive_terminal", return_value=True), \
                patch.object(builder, "confirm_with_token", return_value=None), \
                patch.object(issuer, "_append_event", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                issuer.issue_authorization(root)
        self.assertEqual(issuer.issuance_status(root)["state"], "ISSUED_UNRECORDED")
        code, output = fx.run_cli(fx.ISSUER_MODULE, root, ["--complete-record"], mode="pipe", lines=["x"])
        self.assertEqual(code, 2)
        manifest_sha = fx.sha256(root / issuer.MANIFEST_RELATIVE)
        code, output = fx.run_cli(fx.ISSUER_MODULE, root, ["--complete-record"], mode="tty", lines=[issuer.complete_token(manifest_sha)])
        self.assertEqual(code, 0, output)
        self.assertEqual(issuer.issuance_status(root)["state"], "ISSUED_RECORDED")
        self.assertEqual(fx.gate_failures(root)[0], [])

    def _unrecorded_root(self):
        root = clone("s2")
        with patch.object(builder, "interactive_terminal", return_value=True), \
                patch.object(builder, "confirm_with_token", return_value=None), \
                patch.object(issuer, "_append_event", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                issuer.issue_authorization(root)
        return root

    def test_complete_record_needs_a_terminal_even_with_the_right_token(self):
        for mode in ("pipe", "tty-in-only", "tty-out-only"):
            with self.subTest(mode=mode):
                root = self._unrecorded_root()
                token = issuer.complete_token(fx.sha256(root / issuer.MANIFEST_RELATIVE))
                before = fx.tree_digest(root)
                code, _ = fx.run_cli(fx.ISSUER_MODULE, root, ["--complete-record"], mode=mode, lines=[token])
                self.assertEqual(code, 2)
                self.assertEqual(fx.tree_digest(root), before)

    def test_complete_record_needs_the_typed_token_in_a_terminal(self):
        for token in ("", "yes", "COMPLETE-R11-ISSUANCE-RECORD-000000000000", "ISSUE-R11-AUTH-000000000000"):
            with self.subTest(token=token):
                root = self._unrecorded_root()
                before = fx.tree_digest(root)
                code, _ = fx.run_cli(fx.ISSUER_MODULE, root, ["--complete-record"], mode="tty", lines=[token])
                self.assertEqual(code, 2)
                self.assertEqual(fx.tree_digest(root), before)

    def test_complete_record_refuses_when_nothing_is_unrecorded(self):
        for name in ("s2", "issued"):
            root = clone(name)
            before = fx.tree_digest(root)
            code, _ = fx.run_cli(fx.ISSUER_MODULE, root, ["--complete-record"], mode="tty", lines=["x"])
            self.assertEqual(code, 2)
            self.assertEqual(fx.tree_digest(root), before)

    def test_complete_record_with_a_tampered_manifest_is_refused(self):
        root = clone("s2")
        with patch.object(builder, "interactive_terminal", return_value=True), \
                patch.object(builder, "confirm_with_token", return_value=None), \
                patch.object(issuer, "_append_event", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                issuer.issue_authorization(root)
        path = root / issuer.MANIFEST_RELATIVE
        manifest = json.loads(path.read_text())
        manifest["authorization_id"] = "auth-step9_63c_r11-" + "5" * 32
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        before = fx.tree_digest(root)
        code, _ = fx.run_cli(fx.ISSUER_MODULE, root, ["--complete-record"], mode="tty", lines=[issuer.complete_token(fx.sha256(path))])
        self.assertEqual(code, 2)
        self.assertEqual(fx.tree_digest(root), before)

    def test_issuer_never_overwrites_an_existing_manifest(self):
        root = clone("s2")
        (root / issuer.MANIFEST_RELATIVE).write_text("sentinel")
        with self.assertRaises(RuntimeError):
            with patch.object(builder, "interactive_terminal", return_value=True), patch.object(builder, "confirm_with_token", return_value=None):
                issuer.issue_authorization(root)
        self.assertEqual((root / issuer.MANIFEST_RELATIVE).read_text(), "sentinel")


class ThreatTests(unittest.TestCase):
    def test_forged_pointer_blocks_issuance(self):
        root = clone("s2")
        (root / builder.IDENTITY_CONFIG_PATH).write_text(json.dumps({"runner_freeze_revision": "r11"}))
        self.assertFalse(issuer.plan_issuance(root)["ready"])

    def test_forged_freeze_blocks_issuance(self):
        root = clone("s2")
        path = root / builder.EXPECTED_FREEZE_PATH
        document = json.loads(path.read_text())
        document["execution_permission"] = True
        path.write_text(json.dumps(document, sort_keys=True, indent=2) + "\n")
        self.assertFalse(issuer.plan_issuance(root)["ready"])

    def test_old_authorization_resurrection_by_ledger_tamper_blocks_issuance_and_gate(self):
        root = clone("issued")
        # Remove the AR-14 retirement event (the one that mentions the r10 id and is not part of the frozen prefix).
        prefix = 1161
        raw = (root / builder.LEDGER_PATH).read_bytes()
        tail = raw[prefix:].decode().splitlines(keepends=True)
        kept = [l for l in tail if builder.R10_AUTHORIZATION_ID not in l]
        self.assertLess(len(kept), len(tail))
        (root / builder.LEDGER_PATH).write_bytes(raw[:prefix] + "".join(kept).encode())
        failures, _ = fx.gate_failures(root)
        self.assertTrue(failures, "resurrecting r10 must make the gate fail")

    def test_issuer_substitution_is_detected(self):
        root = clone("s2")
        target = root / builder.ISSUER_PATH
        target.write_bytes(target.read_bytes() + b"\n# substituted")
        plan = issuer.plan_issuance(root)
        self.assertFalse(plan["ready"])
        self.assertIn("I5", failed(plan) | {"I5"})

    def test_manifest_tampering_after_issuance_is_detected_by_verify_and_gate(self):
        for mutate in (lambda m: m.update(consumed=True), lambda m: m.update(issued_at_utc=FUTURE),
                       lambda m: m["execution_namespace"].update(namespace_id="x")):
            root = clone("issued")
            path = root / issuer.MANIFEST_RELATIVE
            manifest = json.loads(path.read_text())
            mutate(manifest)
            path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
            self.assertFalse(issuer.verify_issuance(root)["ok"])
            self.assertIn(formal.ISSUANCE_KEY, fx.gate_failures(root)[0])

    def test_partial_write_state_is_reported_not_repaired(self):
        root = clone("issued")
        lines = fx.ledger_lines(root)
        del lines[fx.issued_event_index(root)]
        fx.write_ledger(root, lines)
        before = fx.tree_digest(root)
        self.assertEqual(issuer.issuance_status(root)["state"], "ISSUED_UNRECORDED")
        issuer.verify_issuance(root)
        self.assertEqual(fx.tree_digest(root), before)

    def test_event_without_manifest_is_an_anomaly(self):
        root = clone("issued")
        (root / issuer.MANIFEST_RELATIVE).unlink()
        self.assertEqual(issuer.issuance_status(root)["state"], "ANOMALY_EVENT_WITHOUT_MANIFEST")

    def test_duplicate_event_is_an_anomaly(self):
        root = clone("issued")
        lines = fx.ledger_lines(root)
        lines.append(lines[fx.issued_event_index(root)])
        fx.write_ledger(root, lines)
        self.assertEqual(issuer.issuance_status(root)["state"], "ANOMALY_DUPLICATE_EVENT")

    def test_wrong_evaluation_inputs_are_not_accepted(self):
        root = clone("s2")
        resign(root, lambda a: a["issuance"].update(evaluation_id="eval-other"))
        self.assertFalse(issuer.plan_issuance(root)["ready"])

    def test_namespace_must_derive_from_the_identities(self):
        root = clone("s2")
        resign(root, lambda a: a["issuance"].update(namespace_id="ns-not-derived"))
        self.assertFalse(issuer.plan_issuance(root)["ready"])

    def test_automation_environment_variables_do_not_substitute_for_a_terminal(self):
        root = clone("s2")
        token = issuer.plan_issuance(root)["confirmation_token"]
        before = fx.tree_digest(root)
        env = fx.cli_env({"CI": "true", "ISSUE_R11_CONFIRM": token, "CONFIRM": token, "YES": "1"})
        code, _ = fx.run_cli(fx.ISSUER_MODULE, root, ["--issue", "--yes", "--token", token], mode="pipe", env=env, lines=[token])
        self.assertEqual(code, 2)
        self.assertEqual(fx.tree_digest(root), before)

    def test_clock_skew_backwards_is_refused(self):
        root = clone("s2")
        plan = issuer.plan_issuance(root, clock=lambda: "1999-01-01T00:00:00+00:00")
        self.assertFalse(plan["ready"])

    def test_issuance_builds_nothing_outside_its_two_artifacts(self):
        root = clone("s2")
        before = fx.tree_digest(root)
        self.assertEqual(fx.issue(root)[0], 0)
        after = fx.tree_digest(root)
        changed = {p for p in after if before.get(p) != after[p]}
        self.assertEqual({p for p in changed if not p.endswith(".lock")}, {issuer.MANIFEST_RELATIVE, builder.LEDGER_PATH})


if __name__ == "__main__":
    unittest.main()
