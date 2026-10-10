"""Step 9.63c-r5c10ah, D-B: the gated Freeze-creation entry (--plan-freeze / --verify-freeze / --create-freeze)."""
from __future__ import annotations

import json
import os
import shutil
import stat
import unittest
from pathlib import Path
from unittest.mock import patch

import r11_activation_fixtures as fx
import r11_gated_fixtures as g
from scripts import build_step9_63c_r11_runner_freeze as builder

T = g.Templates("r11-freeze-entry-")


def setUpModule():
    os.environ[builder.SYNTHETIC_ROOT_ENV] = "1"
    T.build("s0", "retired", "pointer", "freeze")


def tearDownModule():
    os.environ.pop(builder.SYNTHETIC_ROOT_ENV, None)
    T.close()


def failed(plan):
    return {c["name"].split()[0] for c in plan["preconditions"] if not c["ok"]}


class PlanTests(unittest.TestCase):
    def test_ready_after_ar14_and_the_pointer_and_writes_nothing(self):
        root = T.clone("pointer")
        before = fx.tree_digest(root)
        plan = builder.plan_freeze(root)
        self.assertTrue(plan["ready"], [c for c in plan["preconditions"] if not c["ok"]])
        self.assertEqual(fx.tree_digest(root), before)
        approval = json.loads((root / builder.APPROVAL_PATH).read_text())
        self.assertEqual(plan["confirmation_token"], "CREATE-R11-FREEZE-" + approval["freeze"]["predicted_sha256"][:12] + "-" + fx.sha256(root / builder.APPROVAL_PATH)[:12])

    def test_skipping_ar14_is_refused_even_when_a_canonical_pointer_is_present(self):
        root = T.clone("s0")
        (root / builder.IDENTITY_CONFIG_PATH).write_bytes(builder.canonical_pointer_bytes())
        record = {"pointer_sha256": builder.POINTER_SHA256, "approval_record_sha256": fx.sha256(root / builder.APPROVAL_PATH)}
        (root / builder.POINTER_CREATION_RECORD_PATH).write_text(json.dumps(record))
        plan = builder.plan_freeze(root)
        self.assertFalse(plan["ready"])
        self.assertIn("FZ2", failed(plan))

    def test_without_the_pointer_the_freeze_cannot_be_created(self):
        root = T.clone("retired")
        plan = builder.plan_freeze(root)
        self.assertFalse(plan["ready"])
        self.assertIn("FZ3", failed(plan))

    def test_fz3_pointer_variants(self):
        for label, change in (("non canonical", lambda r: (r / builder.IDENTITY_CONFIG_PATH).write_bytes(builder.canonical_pointer_bytes() + b" ")),
                              ("no record", lambda r: (r / builder.POINTER_CREATION_RECORD_PATH).unlink()),
                              ("record for another approval", lambda r: (r / builder.POINTER_CREATION_RECORD_PATH).write_text(json.dumps({"pointer_sha256": builder.POINTER_SHA256, "approval_record_sha256": "0" * 64})))):
            with self.subTest(case=label):
                root = T.clone("pointer")
                change(root)
                plan = builder.plan_freeze(root)
                self.assertFalse(plan["ready"])

    def test_fz1_unsigned_or_drifted_approval(self):
        for label, mutate in (("unsigned", lambda a: a.update(status=builder.APPROVAL_DRAFT, approver=None, signed_at_utc=None)),
                              ("pin drift", lambda a: a["named_pins"]["consumer"].update(sha256="0" * 64)),
                              ("aggregate", lambda a: a["repository_aggregate"].update(sha256="0" * 64))):
            with self.subTest(case=label):
                root = T.clone("pointer")
                g.rewrite_approval(root, mutate)
                self.assertIn("FZ1", failed(builder.plan_freeze(root)))

    def test_fz1_a_stray_file_after_signing_breaks_the_stable_aggregate(self):
        root = T.clone("pointer")
        (root / "scripts/stray.py").write_text("x = 1\n")
        self.assertIn("FZ1", failed(builder.plan_freeze(root)))

    def test_fz4_an_existing_freeze_blocks(self):
        root = T.clone("freeze")
        self.assertIn("FZ4", failed(builder.plan_freeze(root)))

    def test_fz5_a_wrong_predicted_sha_or_size_or_time_blocks(self):
        for label, mutate in (("sha", lambda a: a["freeze"].update(predicted_sha256="0" * 64)),
                              ("size", lambda a: a["freeze"].update(predicted_size=1)),
                              ("created_at", lambda a: a["freeze"].update(created_at_utc="2026-02-02T00:00:00+00:00"))):
            with self.subTest(case=label):
                root = T.clone("pointer")
                g.rewrite_approval(root, mutate)
                plan = builder.plan_freeze(root)
                self.assertFalse(plan["ready"])
                self.assertIn("FZ5", failed(plan))

    def test_fz5_a_member_changed_after_signing_blocks(self):
        root = T.clone("pointer")
        target = root / "scripts/v3_namespace_allocator.py"
        target.write_bytes(target.read_bytes() + b"\n#")
        plan = builder.plan_freeze(root)
        self.assertFalse(plan["ready"])

    def test_fz6_historical_pins(self):
        root = T.clone("pointer")
        pinned = root / "evaluation/v1_2_3/step9_61a_v3_runner_freeze_r6.json"
        pinned.write_bytes(pinned.read_bytes() + b" ")
        self.assertFalse(builder.plan_freeze(root)["ready"])

    def test_fz6_holds_on_its_own_when_the_aggregate_is_resigned(self):
        root = T.clone("pointer")
        pinned = root / "evaluation/v1_2_3/step9_61a_v3_runner_freeze_r6.json"
        pinned.write_bytes(pinned.read_bytes() + b" ")
        g.rewrite_approval(root, lambda a: a["repository_aggregate"].update(sha256=builder.stable_aggregate(root)["sha256"]))
        plan = builder.plan_freeze(root)
        self.assertNotIn("FZ1", failed(plan))
        self.assertIn("FZ6", failed(plan))

    def test_fz7_synthetic_switch(self):
        root = T.clone("pointer")
        with patch.dict(os.environ):
            os.environ.pop(builder.SYNTHETIC_ROOT_ENV, None)
            self.assertIn("FZ7", failed(builder.plan_freeze(root)))

    def test_read_only_modes_never_write(self):
        for flag in ("--plan-freeze", "--verify-freeze"):
            with self.subTest(flag=flag):
                root = T.clone("pointer")
                before = fx.tree_digest(root)
                g.cli(root, flag, mode="pipe")
                self.assertEqual(fx.tree_digest(root), before)
        code, output = g.cli(T.clone("pointer"), "--plan-freeze", mode="pipe")
        self.assertEqual(code, 0, output)
        self.assertNotIn("_data", output)


class GateTests(unittest.TestCase):
    def test_in_process_without_a_terminal_is_refused(self):
        root = T.clone("pointer")
        before = fx.tree_digest(root)
        with patch.object(builder, "interactive_terminal", return_value=False), self.assertRaises(PermissionError):
            builder.create_freeze(root)
        self.assertEqual(fx.tree_digest(root), before)

    def test_pipes_and_half_terminals_are_refused_with_the_right_token(self):
        for mode in ("pipe", "tty-in-only", "tty-out-only"):
            with self.subTest(mode=mode):
                root = T.clone("pointer")
                token = g.freeze_token(root)
                before = fx.tree_digest(root)
                code, output = g.cli(root, "--create-freeze", token=token, mode=mode)
                self.assertEqual(code, 2, output)
                self.assertEqual(fx.tree_digest(root), before)

    def test_wrong_tokens_are_refused(self):
        right = g.freeze_token(T.clone("pointer"))
        for token in ("", "yes", right[:-1], right.lower(), right + "x", "CREATE-R11-FREEZE-" + "0" * 12 + right[right.rindex("-"):],
                      right[:right.rindex("-")] + "-" + "0" * 12, builder.POINTER_TOKEN):
            with self.subTest(token=token):
                root = T.clone("pointer")
                before = fx.tree_digest(root)
                code, output = g.cli(root, "--create-freeze", token=token)
                self.assertEqual(code, 2, output)
                self.assertIn("token mismatch", output)
                self.assertEqual(fx.tree_digest(root), before)

    def test_unsigned_approval_cannot_create_the_freeze(self):
        root = T.clone("pointer")
        g.rewrite_approval(root, lambda a: a.update(status=builder.APPROVAL_DRAFT, approver=None, signed_at_utc=None))
        before = fx.tree_digest(root)
        code, _ = g.cli(root, "--create-freeze", token="CREATE-R11-FREEZE-000000000000-000000000000")
        self.assertEqual(code, 2)
        self.assertEqual(fx.tree_digest(root), before)

    def test_a_wrong_prediction_is_refused_with_the_right_token_and_nothing_is_written(self):
        root = T.clone("pointer")
        g.rewrite_approval(root, lambda a: a["freeze"].update(predicted_sha256="0" * 64))
        before = fx.tree_digest(root)
        code, output = g.cli(root, "--create-freeze", token=g.freeze_token(root))
        self.assertEqual(code, 2, output)
        self.assertEqual(fx.tree_digest(root), before)

    def test_skipping_ar14_via_the_cli_writes_nothing(self):
        root = T.clone("s0")
        (root / builder.IDENTITY_CONFIG_PATH).write_bytes(builder.canonical_pointer_bytes())
        (root / builder.POINTER_CREATION_RECORD_PATH).write_text(json.dumps({"pointer_sha256": builder.POINTER_SHA256, "approval_record_sha256": fx.sha256(root / builder.APPROVAL_PATH)}))
        before = fx.tree_digest(root)
        code, output = g.cli(root, "--create-freeze", token=g.freeze_token(root))
        self.assertEqual(code, 2, output)
        self.assertEqual(fx.tree_digest(root), before)
        self.assertFalse((root / builder.EXPECTED_FREEZE_PATH).exists())

    def test_non_production_root_without_the_switch_is_refused(self):
        root = T.clone("pointer")
        before = fx.tree_digest(root)
        env = {k: v for k, v in fx.cli_env().items() if k != builder.SYNTHETIC_ROOT_ENV}
        code, _ = g.cli(root, "--create-freeze", token=g.freeze_token(root), env=env)
        self.assertEqual(code, 2)
        self.assertEqual(fx.tree_digest(root), before)

    def test_a_second_run_is_refused(self):
        root = T.clone("freeze")
        before = fx.tree_digest(root)
        code, _ = g.cli(root, "--create-freeze", token="CREATE-R11-FREEZE-000000000000-000000000000")
        self.assertEqual(code, 2)
        self.assertEqual(fx.tree_digest(root), before)


class WriteTests(unittest.TestCase):
    def test_success_writes_the_predicted_freeze_exclusively(self):
        root = T.clone("pointer")
        before = fx.tree_digest(root)
        g.do_freeze(root)
        approval = json.loads((root / builder.APPROVAL_PATH).read_text())
        target = root / builder.EXPECTED_FREEZE_PATH
        self.assertEqual(fx.sha256(target), approval["freeze"]["predicted_sha256"])
        self.assertEqual(target.stat().st_size, approval["freeze"]["predicted_size"])
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
        after = fx.tree_digest(root)
        self.assertEqual({p for p in after if before.get(p) != after[p] and not p.endswith(".lock")}, {builder.EXPECTED_FREEZE_PATH})
        self.assertTrue(builder.verify_persisted_candidate(root)["ok"])
        self.assertEqual(builder.identity_status(root)["state"], "S2_FREEZE_PERSISTED")

    def test_a_disk_sha_that_differs_from_the_prediction_is_reported_and_nothing_is_deleted(self):
        root = T.clone("pointer")
        real = builder._write_exclusive

        def corrupt(path, data):
            real(path, data[:-1] + b" ")
        with patch.object(builder, "interactive_terminal", return_value=True), patch.object(builder, "confirm_with_token", return_value=None), \
                patch.object(builder, "_write_exclusive", side_effect=corrupt):
            with self.assertRaisesRegex(RuntimeError, "FREEZE_SHA_MISMATCH.*Recovery"):
                builder.create_freeze(root)
        self.assertTrue((root / builder.EXPECTED_FREEZE_PATH).exists())
        self.assertEqual(builder.identity_status(root)["state"], "ANOMALY_FREEZE_NOT_REPRODUCIBLE")

    def test_the_exclusive_write_never_replaces_an_existing_file(self):
        root = T.clone("pointer")
        (root / builder.EXPECTED_FREEZE_PATH).write_text("sentinel")
        with patch.object(builder, "interactive_terminal", return_value=True), patch.object(builder, "confirm_with_token", return_value=None):
            with self.assertRaises(RuntimeError):
                builder.create_freeze(root)
        self.assertEqual((root / builder.EXPECTED_FREEZE_PATH).read_text(), "sentinel")

    def test_a_change_between_confirmation_and_write_is_caught_by_the_recheck(self):
        root = T.clone("pointer")

        def sneaky(*args, **kwargs):
            (root / builder.REGISTRY_PATH).write_text("appeared after the confirmation")
        with patch.object(builder, "interactive_terminal", return_value=True), patch.object(builder, "confirm_with_token", side_effect=sneaky):
            with self.assertRaisesRegex(RuntimeError, "after taking the lock"):
                builder.create_freeze(root)
        self.assertFalse((root / builder.EXPECTED_FREEZE_PATH).exists())

    def test_the_library_persist_function_is_not_used(self):
        root = T.clone("pointer")
        with patch.object(builder, "interactive_terminal", return_value=True), patch.object(builder, "confirm_with_token", return_value=None), \
                patch.object(builder, "persist_candidate", side_effect=AssertionError("must not be used")):
            self.assertEqual(builder.create_freeze(root)["result"], "CREATED")


if __name__ == "__main__":
    unittest.main()
