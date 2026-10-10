"""Step 9.63c-r5c10ah, H3 extension: before --issue writes the manifest it proves that the manifest
equals the plan, byte for byte, apart from issued_at_utc. Also covers the manifest write-time
readback (the former r5c10ag readback test was superseded by this proof firing first)."""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import r11_activation_fixtures as fx
import r11_gated_fixtures as g
from scripts import build_step9_63c_r11_runner_freeze as builder
from scripts import issue_step9_63c_r11_authorization as issuer

T = g.Templates("r11-plan-proof-")


def setUpModule():
    os.environ[builder.SYNTHETIC_ROOT_ENV] = "1"
    T.build("s0", "freeze")


def tearDownModule():
    os.environ.pop(builder.SYNTHETIC_ROOT_ENV, None)
    T.close()


def issue_in_process(root):
    with patch.object(builder, "interactive_terminal", return_value=True), patch.object(builder, "confirm_with_token", return_value=None):
        return issuer.issue_authorization(root)


class ProofTests(unittest.TestCase):
    def target(self, root):
        return root / builder.AUTHORIZATION_MANIFEST_PATH

    def preview_bytes(self, root, issued_at="2030-01-01T00:00:00+00:00"):
        plan = issuer.plan_issuance(root)
        return issuer.manifest_bytes({**plan["manifest_preview"], "issued_at_utc": issued_at})

    def test_a_manifest_that_differs_only_in_the_issue_time_is_accepted(self):
        root = T.clone("freeze")
        builder._verify_manifest_matches_plan(self.target(root), self.preview_bytes(root, "2031-02-03T04:05:06+00:00"))

    def test_any_other_difference_is_refused(self):
        root = T.clone("freeze")
        good = json.loads(self.preview_bytes(root))
        mutations = {"changed value": lambda m: m.update(consumption_limit=2),
                     "changed identity": lambda m: m.update(authorization_id="auth-step9_63c_r11-" + "1" * 32),
                     "changed freeze sha": lambda m: m.update(runner_freeze_sha256="0" * 64),
                     "extra key": lambda m: m.update(extra_key=True),
                     "removed key": lambda m: m.pop("consumed"),
                     "consumed": lambda m: m.update(consumed=True)}
        for label, mutate in mutations.items():
            with self.subTest(case=label):
                changed = json.loads(json.dumps(good))
                mutate(changed)
                with self.assertRaisesRegex(RuntimeError, "MANIFEST_DIFFERS_FROM_PLAN"):
                    builder._verify_manifest_matches_plan(self.target(root), issuer.manifest_bytes(changed))

    def test_a_byte_level_difference_in_the_serialization_is_refused(self):
        root = T.clone("freeze")
        data = self.preview_bytes(root)
        for label, variant in (("trailing space", data.rstrip(b"\n") + b" \n"), ("no newline", data.rstrip(b"\n")),
                               ("compact", (json.dumps(json.loads(data)) + "\n").encode()),
                               ("sorted keys", (json.dumps(json.loads(data), indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode())):
            with self.subTest(case=label):
                with self.assertRaisesRegex(RuntimeError, "MANIFEST_DIFFERS_FROM_PLAN"):
                    builder._verify_manifest_matches_plan(self.target(root), variant)

    def test_data_that_is_not_a_manifest_object_is_refused(self):
        root = T.clone("freeze")
        for data in (b"[]\n", b'{"issued_at_utc": 5}\n', b"{}\n"):
            with self.subTest(data=data):
                with self.assertRaisesRegex(RuntimeError, "MANIFEST_DIFFERS_FROM_PLAN"):
                    builder._verify_manifest_matches_plan(self.target(root), data)

    def test_other_targets_are_not_affected(self):
        builder._verify_manifest_matches_plan(Path("/tmp/not-a-manifest.json"), b"anything")  # no exception: not the manifest

    def test_a_plan_that_cannot_be_made_refuses_the_write(self):
        root = T.clone("s0")  # no pointer or Freeze: the plan has no manifest preview
        with self.assertRaisesRegex(RuntimeError, "MANIFEST_DIFFERS_FROM_PLAN"):
            builder._verify_manifest_matches_plan(self.target(root), b"{}\n")

    def test_issue_is_refused_when_the_manifest_to_write_differs_from_the_plan(self):
        root = T.clone("freeze")
        real = issuer.build_manifest
        calls = {"n": 0}

        def drifting(**kwargs):
            calls["n"] += 1
            manifest = real(**kwargs)
            if calls["n"] == 1:  # the plan whose preview becomes the data to write; the proof then plans afresh (call 2)
                manifest["consumption_limit"] = 99
            return manifest
        ledger = (root / builder.LEDGER_PATH).read_bytes()
        before = fx.tree_digest(root)
        with patch.object(issuer, "build_manifest", side_effect=drifting):
            with self.assertRaisesRegex(RuntimeError, "MANIFEST_DIFFERS_FROM_PLAN"):
                issue_in_process(root)
        self.assertFalse(self.target(root).exists())
        self.assertEqual((root / builder.LEDGER_PATH).read_bytes(), ledger)
        after = fx.tree_digest(root)
        self.assertEqual({p for p in after if before.get(p) != after.get(p) and not p.endswith(".lock")}, set())

    def test_a_normal_issue_passes_the_proof(self):
        root = T.clone("freeze")
        self.assertEqual(issue_in_process(root)["result"], "ISSUED")
        self.assertTrue(issuer.verify_issuance(root)["ok"])

    def test_the_proof_runs_before_any_byte_is_written(self):
        root = T.clone("freeze")
        with patch.object(builder.os, "open", side_effect=AssertionError("must not open the target")):
            with self.assertRaisesRegex(RuntimeError, "MANIFEST_DIFFERS_FROM_PLAN"):
                builder._write_exclusive(self.target(root), b"{}\n")

    def test_issue_through_the_cli_with_a_manifest_that_drifts_writes_nothing(self):
        root = T.clone("freeze")
        token = issuer.plan_issuance(root)["confirmation_token"]
        before = fx.tree_digest(root)
        # a hand-placed manifest makes the target exist; the issuer must refuse before the proof is even reached
        (root / builder.AUTHORIZATION_MANIFEST_PATH).write_text("{}")
        code, _ = fx.run_cli(fx.ISSUER_MODULE, root, ["--issue"], mode="tty", lines=[token])
        self.assertEqual(code, 2)
        self.assertEqual((root / builder.AUTHORIZATION_MANIFEST_PATH).read_text(), "{}")

    def test_a_manifest_that_reads_back_differently_stops_before_any_event(self):
        # The write itself is corrupted (after the proof passed), which only the readback can see.
        root = T.clone("freeze")
        real_fdopen = os.fdopen

        class Corrupting:
            def __init__(self, handle):
                self.handle = handle

            def __enter__(self):
                self.handle.__enter__()
                return self

            def __exit__(self, *exc):
                return self.handle.__exit__(*exc)

            def write(self, data):
                return self.handle.write(data[:-1] + b" ")

            def flush(self):
                return self.handle.flush()

            def fileno(self):
                return self.handle.fileno()

        def fake(fd, mode="r", *args, **kwargs):
            handle = real_fdopen(fd, mode, *args, **kwargs)
            return Corrupting(handle) if "b" in mode else handle
        ledger = (root / builder.LEDGER_PATH).read_bytes()
        with patch.object(builder.os, "fdopen", fake):
            with self.assertRaisesRegex(RuntimeError, "MANIFEST_READBACK_MISMATCH"):
                issue_in_process(root)
        self.assertEqual((root / builder.LEDGER_PATH).read_bytes(), ledger)
        self.assertTrue(self.target(root).exists())  # kept for a person to inspect, never deleted


if __name__ == "__main__":
    unittest.main()
