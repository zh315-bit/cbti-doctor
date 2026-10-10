"""Step 9.63c-r5c10ah: the whole activation sequence on a temporary root using ONLY the gated entries,
plus the negative rehearsals. Every refusal is checked to have written nothing."""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

import r11_activation_fixtures as fx
import r11_gated_fixtures as g
from scripts import authorization_lifecycle as lifecycle
from scripts import build_step9_63c_r11_runner_freeze as builder
from scripts import issue_step9_63c_r11_authorization as issuer
from scripts import run_step9_63_v3_formal_execution as formal

T = g.Templates("r11-gated-e2e-")


def setUpModule():
    os.environ[builder.SYNTHETIC_ROOT_ENV] = "1"
    T.build("s0", "retired", "pointer", "freeze")


def tearDownModule():
    os.environ.pop(builder.SYNTHETIC_ROOT_ENV, None)
    T.close()


def entries(root):
    """(stage name, state to start from, module, flag, token) for every write entry of the sequence."""
    return [
        ("retire", "s0", g.POINTER_MODULE, "--retire-r10", lambda r: builder.plan_retirement(r)["confirmation_token"]),
        ("pointer", "retired", g.POINTER_MODULE, "--create-pointer", lambda r: builder.POINTER_TOKEN),
        ("freeze", "pointer", g.POINTER_MODULE, "--create-freeze", lambda r: builder.plan_freeze(r)["confirmation_token"]),
        ("issue", "freeze", g.ISSUER_MODULE, "--issue", lambda r: issuer.plan_issuance(r)["confirmation_token"]),
    ]


def run(root, module, flag, token, mode="tty", env=None):
    return fx.run_cli(module, root, [flag], mode=mode, lines=[token] if token is not None else [], env=env)


class FullSequence(unittest.TestCase):
    def test_gated_sequence_ends_with_one_active_authorization_and_a_passing_gate(self):
        root, approval = g.new_flow_root(Path(T.tmp.name) / "full")
        self.assertEqual(builder.identity_status(root)["state"], "S0_NOT_ACTIVATED")
        self.assertFalse(builder.plan_identity_pointer(root)["ready"])  # AR-14 not done yet
        ledger_before = (root / builder.LEDGER_PATH).read_bytes()
        for stage, _state, module, flag, token in entries(root):
            plan_flag = {"--retire-r10": "--plan-retire", "--create-pointer": "--plan", "--create-freeze": "--plan-freeze", "--issue": "--plan"}[flag]
            code, output = fx.run_cli(module, root, [plan_flag], mode="pipe")
            self.assertEqual(code, 0, (stage, output[-600:]))  # --plan: ready
            code, output = run(root, module, flag, token(root))
            self.assertEqual(code, 0, (stage, output[-600:]))
        self.assertTrue((root / builder.LEDGER_PATH).read_bytes().startswith(ledger_before))
        self.assertTrue(builder.verify_retirement(root)["ok"])
        self.assertTrue(builder.verify_identity_pointer(root)["ok"])
        self.assertTrue(builder.verify_persisted_candidate(root)["ok"])
        self.assertTrue(issuer.verify_issuance(root)["ok"])
        self.assertEqual(fx.sha256(root / builder.EXPECTED_FREEZE_PATH), approval["freeze"]["predicted_sha256"])
        manifest = json.loads((root / builder.AUTHORIZATION_MANIFEST_PATH).read_text())
        self.assertEqual(lifecycle.active_authorizations(root), [manifest["authorization_id"]])
        self.assertEqual((manifest["authorization_id"], manifest["attempt_id"]), (approval["issuance"]["authorization_id"], approval["issuance"]["attempt_id"]))
        failures = g.with_gate(root, lambda args: formal.prepare_formal_gates(args)["precommit_failures"])
        self.assertEqual(failures, [])
        self.assertFalse((root / "evaluation/v4_runs" / manifest["execution_namespace"]["namespace_id"]).exists())

    def test_the_approval_signed_once_up_front_stays_valid_through_every_step(self):
        root, _ = g.new_flow_root(Path(T.tmp.name) / "stable")
        approval_bytes = (root / builder.APPROVAL_PATH).read_bytes()
        for stage, _state, module, flag, token in entries(root):
            self.assertEqual(run(root, module, flag, token(root))[0], 0, stage)
            self.assertEqual((root / builder.APPROVAL_PATH).read_bytes(), approval_bytes)
            self.assertEqual(builder.verify_approval(root, json.loads(approval_bytes)), [], stage)

    def test_the_real_repository_is_not_touched(self):
        ledger = fx.REPO / builder.LEDGER_PATH
        before = fx.sha256(ledger)
        g.through(Path(T.tmp.name) / "isolation", "retired")
        self.assertEqual(fx.sha256(ledger), before)
        for relative in (builder.IDENTITY_CONFIG_PATH, builder.EXPECTED_FREEZE_PATH, builder.AUTHORIZATION_MANIFEST_PATH):
            self.assertFalse((fx.REPO / relative).exists(), relative)


class NegativeRehearsals(unittest.TestCase):
    def assert_refused_without_writes(self, root, module, flag, token, mode="tty", env=None):
        before = fx.tree_digest(root)
        code, output = run(root, module, flag, token, mode=mode, env=env)
        self.assertEqual(code, 2, output[-800:])
        self.assertEqual(fx.tree_digest(root), before)
        return output

    def test_unsigned_approval_is_refused_at_every_entry(self):
        for stage, state, module, flag, token in entries(None):
            with self.subTest(entry=stage):
                root = T.clone(state)
                valid_token = token(root)
                g.rewrite_approval(root, lambda a: a.update(status=builder.APPROVAL_DRAFT, approver=None, signed_at_utc=None))
                self.assert_refused_without_writes(root, module, flag, valid_token)

    def test_a_wrong_token_is_refused_at_every_entry(self):
        for stage, state, module, flag, token in entries(None):
            with self.subTest(entry=stage):
                root = T.clone(state)
                self.assert_refused_without_writes(root, module, flag, token(root) + "x")
                self.assert_refused_without_writes(root, module, flag, "")

    def test_non_interactive_invocation_is_refused_at_every_entry(self):
        for stage, state, module, flag, token in entries(None):
            for mode in ("pipe", "tty-in-only", "tty-out-only"):
                with self.subTest(entry=stage, mode=mode):
                    root = T.clone(state)
                    self.assert_refused_without_writes(root, module, flag, token(root), mode=mode, env=fx.cli_env({"CI": "true"}))

    def test_a_ledger_with_a_line_appended_beforehand_is_refused(self):
        root = T.clone("s0")
        token = builder.plan_retirement(root)["confirmation_token"]
        with (root / builder.LEDGER_PATH).open("a") as stream:
            stream.write(json.dumps({"artifact_type": "AUTHORIZATION_LIFECYCLE_EVENT", "event_type": "UNAPPROVED"}) + "\n")
        self.assert_refused_without_writes(root, g.POINTER_MODULE, "--retire-r10", token)

    def test_a_freeze_prediction_that_does_not_match_is_refused(self):
        root = T.clone("pointer")
        g.rewrite_approval(root, lambda a: a["freeze"].update(predicted_sha256="f" * 64))
        token = "CREATE-R11-FREEZE-" + "f" * 12 + "-" + fx.sha256(root / builder.APPROVAL_PATH)[:12]
        self.assert_refused_without_writes(root, g.POINTER_MODULE, "--create-freeze", token)
        self.assertFalse((root / builder.EXPECTED_FREEZE_PATH).exists())

    def test_creating_the_pointer_or_freeze_without_ar14_is_refused(self):
        root = T.clone("s0")
        self.assert_refused_without_writes(root, g.POINTER_MODULE, "--create-pointer", builder.POINTER_TOKEN)
        self.assertFalse((root / builder.IDENTITY_CONFIG_PATH).exists())
        token = "CREATE-R11-FREEZE-" + json.loads((root / builder.APPROVAL_PATH).read_text())["freeze"]["predicted_sha256"][:12] + "-" + fx.sha256(root / builder.APPROVAL_PATH)[:12]
        self.assert_refused_without_writes(root, g.POINTER_MODULE, "--create-freeze", token)
        self.assertFalse((root / builder.EXPECTED_FREEZE_PATH).exists())

    def test_issuing_without_a_freeze_is_refused(self):
        root = T.clone("pointer")
        self.assert_refused_without_writes(root, g.ISSUER_MODULE, "--issue", "ISSUE-R11-AUTH-000000000000")

    def test_replaying_a_step_that_already_happened_is_refused_at_every_entry(self):
        done = {"retire": "retired", "pointer": "pointer", "freeze": "freeze"}
        for stage, _state, module, flag, token in entries(None):
            if stage not in done:
                continue
            with self.subTest(entry=stage):
                root = T.clone(done[stage])
                approval_sha = fx.sha256(root / builder.APPROVAL_PATH)
                stale = {"retire": "RETIRE-R10-auth-step9_6-" + approval_sha[:12], "pointer": builder.POINTER_TOKEN,
                         "freeze": "CREATE-R11-FREEZE-" + json.loads((root / builder.APPROVAL_PATH).read_text())["freeze"]["predicted_sha256"][:12] + "-" + approval_sha[:12]}[stage]
                before = fx.tree_digest(root)
                code, output = run(root, module, flag, stale)
                if stage == "pointer":
                    self.assertEqual(code, 0, output)  # idempotent: reports ALREADY_CREATED, writes nothing
                    self.assertIn("ALREADY_CREATED", output)
                else:
                    self.assertEqual(code, 2, output)
                self.assertEqual(fx.tree_digest(root), before)


if __name__ == "__main__":
    unittest.main()
