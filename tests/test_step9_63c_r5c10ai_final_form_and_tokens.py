"""Step 9.63c-r5c10ai: the final-form approval record (content hash, signing commit pin, accepted
exceptions), the retirement token built from the uuid part of the r10 id, and the complete gated
sequence on temporary roots with the final version."""
from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

import r11_activation_fixtures as fx
import r11_final_fixtures as ff
import r11_gated_fixtures as g
from scripts import authorization_lifecycle as lifecycle
from scripts import build_step9_63c_r11_runner_freeze as builder
from scripts import issue_step9_63c_r11_authorization as issuer
from scripts import run_step9_63_v3_formal_execution as formal

T = ff.FinalTemplates("r11-final-form-")
R10_UUID = "aff5c4b96bb74278a14d3fd08bf8a84e"


def setUpModule():
    os.environ[builder.SYNTHETIC_ROOT_ENV] = "1"
    T.build("s0", "retired", "pointer", "freeze", "issued")


def tearDownModule():
    os.environ.pop(builder.SYNTHETIC_ROOT_ENV, None)
    T.close()


def approval_of(root):
    return json.loads((root / builder.APPROVAL_PATH).read_text())


def failed(plan):
    return {c["name"].split()[0] for c in plan["preconditions"] if not c["ok"]}


class TokenTests(unittest.TestCase):
    def test_the_retirement_token_uses_the_uuid_part_of_the_r10_id_and_the_content_hash(self):
        root = T.clone("s0")
        approval = approval_of(root)
        token = builder.plan_retirement(root)["confirmation_token"]
        self.assertEqual(builder.R10_AUTHORIZATION_ID.rsplit("-", 1)[1], R10_UUID)
        self.assertEqual(token, f"RETIRE-R10-{R10_UUID[:12]}-{approval['content_sha256'][:12]}")
        self.assertEqual(token.split("-")[2], "aff5c4b96bb7")

    def test_the_tokens_printed_in_the_draft_equal_the_tokens_the_signed_record_demands(self):
        root = T.clone("pointer")
        approval = approval_of(root)
        self.assertEqual(approval["tokens"]["retire_r10"]["value"], f"RETIRE-R10-aff5c4b96bb7-{approval['content_sha256'][:12]}")
        self.assertEqual(approval["tokens"]["create_freeze"]["value"], builder.plan_freeze(root)["confirmation_token"])
        self.assertEqual(approval["tokens"]["create_pointer"]["value"], builder.POINTER_TOKEN)
        # the same values are in the unsigned form, i.e. they were knowable before signing (rebuilt on the untouched root)
        fresh = T.clone("s0")
        a0 = approval_of(fresh)
        draft = builder.build_approval(fresh, created_at_utc=a0["freeze"]["created_at_utc"], approval_id=a0["approval_id"],
                                       issuance=a0["issuance"], final=True)
        self.assertEqual(draft["content_sha256"], a0["content_sha256"])
        self.assertEqual(draft["tokens"]["retire_r10"]["value"], builder.plan_retirement(fresh)["confirmation_token"])

    def test_the_token_does_not_change_when_the_four_signature_fields_change(self):
        root = T.clone("s0")
        before = builder.plan_retirement(root)["confirmation_token"]
        g.rewrite_approval(root, lambda a: a.update(approver="somebody else", signed_at_utc="2027-05-05T05:05:05+00:00"))
        self.assertEqual(builder.plan_retirement(root)["confirmation_token"], before)

    def test_tokens_do_not_depend_on_the_repository_aggregate_but_the_aggregate_is_still_verified(self):
        # the checklist and runbook quote the tokens and are part of the aggregate, so the hash must not include it
        root = T.clone("s0")
        before = builder.plan_retirement(root)["confirmation_token"]
        approval = approval_of(root)
        approval["repository_aggregate"]["sha256"] = "0" * 64
        self.assertEqual(builder.approval_content_sha256(approval), approval["content_sha256"])
        g.rewrite_approval(root, lambda a: a["repository_aggregate"].update(sha256="0" * 64))
        plan = builder.plan_retirement(root)
        self.assertEqual(plan["confirmation_token"], before)
        self.assertFalse(plan["ready"])
        self.assertTrue(any("repository state changed" in c["detail"] for c in plan["preconditions"] if c["name"].startswith("RT1")))

    def test_a_token_from_another_step9_6x_authorization_id_is_refused(self):
        root = T.clone("s0")
        part = approval_of(root)["content_sha256"][:12]
        before = fx.tree_digest(root)
        for other_id in ("auth-step9_63c_r4-4b2749ce10014634ac6de155d37ec6a9", "auth-step9_63a_r3-0123456789abcdef0123456789abcdef"):
            token = f"RETIRE-R10-{other_id.rsplit('-', 1)[1][:12]}-{part}"
            code, output = g.cli(root, "--retire-r10", token=token)
            self.assertEqual(code, 2, output)
            self.assertIn("token mismatch", output)
        self.assertEqual(fx.tree_digest(root), before)

    def test_the_previous_literal_prefix_and_other_malformed_tokens_are_refused(self):
        root = T.clone("s0")
        part = approval_of(root)["content_sha256"][:12]
        right = f"RETIRE-R10-aff5c4b96bb7-{part}"
        before = fx.tree_digest(root)
        for token in (f"RETIRE-R10-auth-step9_6-{part}", right[:-1], right.upper(), right + "0", f"RETIRE-R10-aff5c4b96bb7-{'0' * 12}",
                      f"RETIRE-R10-aff5c4b96bb7-{fx.sha256(root / builder.APPROVAL_PATH)[:12]}", f"RETIRE-R10-{R10_UUID}-{part}"):
            with self.subTest(token=token):
                code, _ = g.cli(root, "--retire-r10", token=token)
                self.assertEqual(code, 2)
        self.assertEqual(fx.tree_digest(root), before)

    def test_the_freeze_token_binds_the_prediction_and_the_content_hash(self):
        root = T.clone("pointer")
        approval = approval_of(root)
        before = fx.tree_digest(root)
        for token in (f"CREATE-R11-FREEZE-{'0' * 12}-{approval['content_sha256'][:12]}",
                      f"CREATE-R11-FREEZE-{approval['freeze']['predicted_sha256'][:12]}-{'0' * 12}",
                      f"CREATE-R11-FREEZE-{approval['freeze']['predicted_sha256'][:12]}-{fx.sha256(root / builder.APPROVAL_PATH)[:12]}"):
            code, _ = g.cli(root, "--create-freeze", token=token)
            self.assertEqual(code, 2)
        self.assertEqual(fx.tree_digest(root), before)

    def test_earlier_form_approvals_keep_the_file_hash_token(self):
        root, approval = g.new_flow_root(Path(T.tmp.name) / "old-form")
        self.assertNotIn("content_sha256", approval)
        self.assertEqual(builder.approval_token_part(root, approval), fx.sha256(root / builder.APPROVAL_PATH))


class ContentAndCommitTests(unittest.TestCase):
    def test_any_edit_beyond_the_four_signature_fields_is_detected(self):
        for label, mutate in (("freeze time", lambda a: a["freeze"].update(created_at_utc="2030-01-01T00:00:00+00:00")),
                              ("issuance id", lambda a: a["issuance"].update(authorization_id="auth-step9_63c_r11-" + "1" * 32)),
                              ("exception text", lambda a: a["accepted_exceptions"][0].update(text="edited")),
                              ("token format", lambda a: a["tokens"]["issue"].update(format="edited")),
                              ("removed content hash value", lambda a: a.update(content_sha256="0" * 64))):
            with self.subTest(case=label):
                root = T.clone("s0")
                g.rewrite_approval(root, mutate)
                plan = builder.plan_retirement(root)
                self.assertFalse(plan["ready"])
                self.assertIn("RT1", failed(plan))
                self.assertTrue(any("differs from the prepared draft" in c["detail"] for c in plan["preconditions"] if c["name"].startswith("RT1")))

    def test_the_four_signature_fields_may_differ(self):
        root = T.clone("s0")
        g.rewrite_approval(root, lambda a: a.update(approver="x", signed_at_utc="2030-01-01T00:00:00+00:00"))
        self.assertTrue(builder.plan_retirement(root)["ready"])

    def test_signing_requires_a_commit_and_HEAD_must_equal_it(self):
        cases = {"no commit": lambda r: g.rewrite_approval(r, lambda a: a.update(signed_at_commit=None)),
                 "malformed commit": lambda r: g.rewrite_approval(r, lambda a: a.update(signed_at_commit="abc")),
                 "other commit": lambda r: g.rewrite_approval(r, lambda a: a.update(signed_at_commit=ff.OTHER_COMMIT)),
                 "HEAD moved": lambda r: ff.set_head(r, ff.OTHER_COMMIT),
                 "no git directory": lambda r: ff.set_head(r, None)}
        for label, change in cases.items():
            with self.subTest(case=label):
                root = T.clone("s0")
                change(root)
                plan = builder.plan_retirement(root)
                self.assertFalse(plan["ready"])
                self.assertIn("RT1", failed(plan))

    def test_the_commit_pin_is_enforced_by_every_gated_entry(self):
        entries = [("retired" if False else "s0", g.POINTER_MODULE, "--retire-r10", lambda r: builder.plan_retirement(r)["confirmation_token"]),
                   ("retired", g.POINTER_MODULE, "--create-pointer", lambda r: builder.POINTER_TOKEN),
                   ("pointer", g.POINTER_MODULE, "--create-freeze", lambda r: builder.plan_freeze(r)["confirmation_token"]),
                   ("freeze", g.ISSUER_MODULE, "--issue", lambda r: issuer.plan_issuance(r)["confirmation_token"])]
        for state, module, flag, token in entries:
            with self.subTest(entry=flag):
                root = T.clone(state)
                valid = token(root)
                ff.set_head(root, ff.OTHER_COMMIT)  # somebody committed after signing
                before = fx.tree_digest(root)
                code, _ = fx.run_cli(module, root, [flag], mode="tty", lines=[valid])
                self.assertEqual(code, 2)
                self.assertEqual(fx.tree_digest(root), before)

    def test_an_unsigned_record_never_passes_the_commit_check(self):
        root, _ = ff.final_flow_root(Path(T.tmp.name) / "unsigned", sign=False)
        self.assertFalse(builder.plan_retirement(root)["ready"])

    def test_a_record_prepared_before_the_commit_pin_existed_is_unaffected(self):
        root, _ = g.new_flow_root(Path(T.tmp.name) / "old-form-2")
        self.assertTrue(builder.plan_retirement(root)["ready"])

    def test_head_commit_reads_detached_loose_and_packed_refs(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".git/refs/heads").mkdir(parents=True)
            sha = "a" * 40
            (root / ".git/HEAD").write_text(sha + "\n")
            self.assertEqual(builder.head_commit(root), sha)
            (root / ".git/HEAD").write_text("ref: refs/heads/main\n")
            self.assertIsNone(builder.head_commit(root))
            (root / ".git/refs/heads/main").write_text("b" * 40 + "\n")
            self.assertEqual(builder.head_commit(root), "b" * 40)
            (root / ".git/refs/heads/main").unlink()
            (root / ".git/packed-refs").write_text("# pack-refs\n" + "e" * 40 + " refs/heads/main\n")
            self.assertEqual(builder.head_commit(root), "e" * 40)
            (root / ".git/HEAD").write_text("zzz\n")
            self.assertIsNone(builder.head_commit(root))

    def test_head_commit_on_the_real_repository_is_a_full_sha(self):
        self.assertRegex(builder.head_commit(builder.ROOT) or "", "^[0-9a-f]{40}$")


class AcceptedExceptionTests(unittest.TestCase):
    def test_ar15_is_recorded_as_an_accepted_exception_in_every_draft(self):
        for final in (False, True):
            root, approval = ff.final_flow_root(Path(T.tmp.name) / f"exc{final}") if final else g.new_flow_root(Path(T.tmp.name) / "exc-old")
            [exception] = approval["accepted_exceptions"]
            self.assertEqual((exception["id"], exception["state"]), ("AR-15", "CONTENT_INTEGRITY_UNPROVEN"))
            self.assertIn("CONTENT_INTEGRITY_UNPROVEN", exception["text"])
            self.assertIn("Signing this record means accepting that", exception["text"])

    def test_the_final_form_pins_the_exception_through_the_content_hash(self):
        root = T.clone("s0")
        approval = approval_of(root)
        approval["accepted_exceptions"] = []
        self.assertNotEqual(builder.approval_content_sha256(approval), approval_of(root)["content_sha256"])


class FinalFormSequence(unittest.TestCase):
    def test_the_complete_gated_sequence_with_the_final_form(self):
        root, approval = ff.final_flow_root(Path(T.tmp.name) / "full")
        raw = (root / builder.APPROVAL_PATH).read_bytes()
        steps = [("retire", g.POINTER_MODULE, "--retire-r10", lambda r: builder.plan_retirement(r)["confirmation_token"]),
                 ("pointer", g.POINTER_MODULE, "--create-pointer", lambda r: builder.POINTER_TOKEN),
                 ("freeze", g.POINTER_MODULE, "--create-freeze", lambda r: builder.plan_freeze(r)["confirmation_token"]),
                 ("issue", g.ISSUER_MODULE, "--issue", lambda r: issuer.plan_issuance(r)["confirmation_token"])]
        for name, module, flag, token in steps:
            code, output = fx.run_cli(module, root, [flag], mode="tty", lines=[token(root)])
            self.assertEqual(code, 0, (name, output[-500:]))
            self.assertEqual((root / builder.APPROVAL_PATH).read_bytes(), raw)
        self.assertTrue(builder.verify_retirement(root)["ok"])
        self.assertTrue(builder.verify_persisted_candidate(root)["ok"])
        self.assertTrue(issuer.verify_issuance(root)["ok"])
        manifest = json.loads((root / builder.AUTHORIZATION_MANIFEST_PATH).read_text())
        self.assertEqual(lifecycle.active_authorizations(root), [manifest["authorization_id"]])
        self.assertEqual(fx.sha256(root / builder.EXPECTED_FREEZE_PATH), approval["freeze"]["predicted_sha256"])
        failures = g.with_gate(root, lambda args: formal.prepare_formal_gates(args)["precommit_failures"])
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
