"""Step 9.63c-r5c10ag, AR-12: r11 identity pointer creation, verification and approval records.

Temporary roots only. The write entry is exercised in a real pseudo-terminal with a typed
token; every refusal is asserted to leave the root byte-for-byte unchanged.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import r11_activation_fixtures as fx
from scripts import build_step9_63c_r11_runner_freeze as builder
from scripts import v3_runner_identity as resolver

_TMP: tempfile.TemporaryDirectory | None = None
_TEMPLATES: dict[str, Path] = {}


def setUpModule():
    global _TMP
    os.environ[builder.SYNTHETIC_ROOT_ENV] = "1"
    _TMP = tempfile.TemporaryDirectory(prefix="r11-pointer-tests-")
    base = Path(_TMP.name)
    s0 = fx.build_root(base / "s0")
    _TEMPLATES["s0"] = s0
    ready = Path(shutil.copytree(s0, base / "ready"))
    fx.retire_r10(ready)
    fx.sign_approval(ready)
    _TEMPLATES["ready"] = ready
    s1 = Path(shutil.copytree(ready, base / "s1"))
    code, output = fx.create_pointer(s1)
    assert code == 0, output
    _TEMPLATES["s1"] = s1
    s2 = Path(shutil.copytree(s1, base / "s2"))
    fx.persist_freeze(s2, json.loads((s2 / builder.APPROVAL_PATH).read_text()))
    _TEMPLATES["s2"] = s2


def tearDownModule():
    os.environ.pop(builder.SYNTHETIC_ROOT_ENV, None)
    if _TMP:
        _TMP.cleanup()


def clone(name: str) -> Path:
    target = Path(tempfile.mkdtemp(dir=_TMP.name)) / "root"
    shutil.copytree(_TEMPLATES[name], target)
    return target


def failed(plan: dict) -> set[str]:
    return {c["name"].split()[0] for c in plan["preconditions"] if not c["ok"]}


class CanonicalPointerTests(unittest.TestCase):
    def test_canonical_bytes_are_389_bytes_with_the_approved_sha(self):
        data = builder.canonical_pointer_bytes()
        self.assertEqual(len(data), 389)
        self.assertEqual(hashlib.sha256(data).hexdigest(), "4e077781faeecee57da02f37d1d3ad8cdc9dfa895d3eb72b1b4ab1f1d3f696fe")
        self.assertEqual((builder.POINTER_SIZE, builder.POINTER_SHA256), (389, hashlib.sha256(data).hexdigest()))

    def test_canonical_form_is_utf8_sorted_indent2_single_trailing_newline(self):
        data = builder.canonical_pointer_bytes()
        text = data.decode("utf-8")
        self.assertTrue(text.endswith("}\n") and not text.endswith("\n\n"))
        self.assertNotIn("\r", text)
        parsed = json.loads(text)
        self.assertEqual(text, json.dumps(parsed, indent=2, sort_keys=True) + "\n")
        self.assertEqual(list(parsed), sorted(parsed))
        self.assertTrue(all(line.startswith("  ") for line in text.splitlines()[1:-1]))

    def test_pointer_agrees_with_resolver_constants(self):
        parsed = json.loads(builder.canonical_pointer_bytes())
        self.assertEqual((parsed["runner_freeze_revision"], parsed["runner_freeze_path"]),
                         (resolver.EXPECTED_REVISION, resolver.EXPECTED_FREEZE_PATH))
        self.assertEqual(builder.IDENTITY_CONFIG_PATH, resolver.IDENTITY_CONFIG_PATH)
        self.assertFalse(parsed["execution_permission"])

    def test_pointer_keeps_the_r10_field_set_and_the_resolver_accepts_it(self):
        r10 = json.loads((fx.REPO / "evaluation/v1_2_3/step9_63c_r5c4_current_runner_identity.json").read_text())
        self.assertEqual(set(json.loads(builder.canonical_pointer_bytes())), set(r10))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / resolver.IDENTITY_CONFIG_PATH).parent.mkdir(parents=True)
            (root / resolver.IDENTITY_CONFIG_PATH).write_bytes(builder.canonical_pointer_bytes())
            self.assertEqual(resolver.load_identity_config(root)["runner_freeze_revision"], "r11")

    def test_a_pointer_that_differs_by_one_byte_is_not_canonical(self):
        for mutate in (lambda d: d + b" ", lambda d: d.replace(b"r11", b"r10", 1), lambda d: d[:-1], lambda d: d.replace(b"  ", b"\t", 1)):
            with self.subTest(mutate=mutate):
                self.assertNotEqual(hashlib.sha256(mutate(builder.canonical_pointer_bytes())).hexdigest(), builder.POINTER_SHA256)


class PointerPreconditionTests(unittest.TestCase):
    def test_plan_is_ready_after_ar14_and_a_signed_approval(self):
        plan = builder.plan_identity_pointer(clone("ready"))
        self.assertTrue(plan["ready"], failed(plan))
        self.assertEqual(plan["confirmation_token"], "CREATE-R11-POINTER-4e077781faee")
        self.assertTrue(plan["writes_nothing"])

    def test_s0_without_ar14_or_approval_is_not_ready(self):
        plan = builder.plan_identity_pointer(clone("s0"))
        self.assertFalse(plan["ready"])
        self.assertTrue({"PP2", "PP4"} <= failed(plan) | {c["name"].split()[0] for c in plan["preconditions"] if not c["ok"]} or not plan["ready"])

    def test_pp1_every_existing_activation_artifact_blocks_creation(self):
        for relative in (builder.IDENTITY_CONFIG_PATH, builder.EXPECTED_FREEZE_PATH, builder.REGISTRY_PATH,
                         builder.AUTHORIZATION_MANIFEST_PATH, builder.POINTER_CREATION_RECORD_PATH):
            with self.subTest(artifact=relative):
                root = clone("ready")
                (root / relative).write_text("x")
                plan = builder.plan_identity_pointer(root, root / builder.APPROVAL_PATH)
                self.assertFalse(plan["ready"])
                self.assertIn("PP1", failed(plan))

    def test_pp1_a_symlink_in_the_pointer_place_blocks_creation(self):
        root = clone("ready")
        os.symlink(root / "evaluation/v1_2_3/step9_52_v3_pre_evaluation_validation.json", root / builder.IDENTITY_CONFIG_PATH)
        self.assertIn("PP1", failed(builder.plan_identity_pointer(root)))

    def test_pp2_unsigned_or_incomplete_approval_is_rejected(self):
        for label, change in (("draft", {"status": builder.APPROVAL_DRAFT}), ("no approver", {"approver": None}),
                              ("no signing time", {"signed_at_utc": "not a time"}),
                              ("wrong schema", {"schema_version": 2}), ("wrong type", {"artifact_type": "OTHER"})):
            with self.subTest(case=label):
                root = clone("ready")
                approval = json.loads((root / builder.APPROVAL_PATH).read_text())
                approval.update(change)
                fx.write_approval(root, approval)
                plan = builder.plan_identity_pointer(root)
                self.assertFalse(plan["ready"])
                self.assertIn("PP2", failed(plan))

    def test_pp2_every_class_of_pin_drift_is_rejected(self):
        def alter_member(root, approval):
            (root / "scripts/v3_namespace_allocator.py").write_bytes((root / "scripts/v3_namespace_allocator.py").read_bytes() + b"\n#")
        def alter_named(root, approval):
            approval["named_pins"]["consumer"]["sha256"] = "0" * 64
        def alter_pointer(root, approval):
            approval["pointer"]["canonical_sha256"] = "0" * 64
        def alter_pointer_size(root, approval):
            approval["pointer"]["canonical_size"] = 388
        def alter_member_list(root, approval):
            approval["members"].pop(next(iter(approval["members"])))
        def alter_r10(root, approval):
            approval["historical"]["r10_freeze_manifest"]["sha256"] = "0" * 64
        def alter_aggregate_by_file(root, approval):
            (root / "evaluation/v1_2_3/stray_file.txt").write_text("changed after approval")
        def alter_aggregate_value(root, approval):
            approval["repository_aggregate"]["sha256"] = "0" * 64
        def alter_prediction(root, approval):
            approval["freeze"]["predicted_sha256"] = "not-a-sha"
        for mutate in (alter_member, alter_named, alter_pointer, alter_pointer_size, alter_member_list, alter_r10,
                       alter_aggregate_by_file, alter_aggregate_value, alter_prediction):
            with self.subTest(mutation=mutate.__name__):
                root = clone("ready")
                approval = json.loads((root / builder.APPROVAL_PATH).read_text())
                mutate(root, approval)
                fx.write_approval(root, approval)
                plan = builder.plan_identity_pointer(root)
                self.assertFalse(plan["ready"])
                self.assertIn("PP2", failed(plan))

    def test_pp2_the_approval_record_and_its_draft_do_not_perturb_the_aggregate_pin(self):
        root = clone("ready")
        shutil.copyfile(root / builder.APPROVAL_PATH, root / builder.APPROVAL_DRAFT_PATH)
        self.assertTrue(builder.plan_identity_pointer(root)["ready"])

    def test_pp4_ar14_not_done_blocks_creation(self):
        root = clone("ready")
        ledger = fx.ledger_lines(root)
        fx.write_ledger(root, ledger[:-1])  # drop the r10 retirement event; the frozen prefix is untouched
        approval = json.loads((root / builder.APPROVAL_PATH).read_text())
        approval["repository_aggregate"]["sha256"] = builder.repository_aggregate(root)["sha256"]
        fx.write_approval(root, approval)
        plan = builder.plan_identity_pointer(root)
        self.assertFalse(plan["ready"])
        self.assertIn("PP4", failed(plan))

    def test_pp5_an_executable_superseded_authorization_blocks_creation(self):
        root = clone("ready")
        r10 = json.loads((root / builder.R10_AUTHORIZATION_PATH).read_text())
        from scripts.v3_namespace_allocator import derive_namespace_id
        r10.update(authorization_id="auth-step9_63c_r10x-" + "1" * 32, attempt_id="attempt-step9_63c_r10x-" + "2" * 32)
        r10["execution_namespace"]["namespace_id"] = derive_namespace_id(r10["evaluation_id"], r10["authorization_id"], r10["attempt_id"])
        (root / "evaluation/v1_2_3/step9_63c_r10x_v3_authorization_manifest.json").write_text(json.dumps(r10))
        approval = json.loads((root / builder.APPROVAL_PATH).read_text())
        approval["repository_aggregate"]["sha256"] = builder.repository_aggregate(root)["sha256"]
        fx.write_approval(root, approval)
        self.assertIn("PP5", failed(builder.plan_identity_pointer(root)))

    def test_pp6_historical_pin_tampering_blocks_creation(self):
        root = clone("ready")
        pinned = root / "evaluation/v1_2_3/step9_61a_v3_runner_freeze_r6.json"
        pinned.write_bytes(pinned.read_bytes() + b" ")
        self.assertIn("PP6", failed(builder.plan_identity_pointer(root)))

    def test_pp6_ledger_prefix_tampering_blocks_creation(self):
        root = clone("ready")
        data = bytearray((root / builder.LEDGER_PATH).read_bytes())
        data[20] ^= 1
        (root / builder.LEDGER_PATH).write_bytes(bytes(data))
        self.assertIn("PP6", failed(builder.plan_identity_pointer(root)))

    def test_pp7_an_r11_transaction_journal_blocks_creation(self):
        root = clone("ready")
        journals = root / builder.TRANSACTION_RELATIVE
        journals.mkdir(parents=True, exist_ok=True)
        (journals / f"{builder.R11_AUTHORIZATION_ID_PREFIX}{'3' * 32}.jsonl").write_text("{}\n")
        self.assertIn("PP7", failed(builder.plan_identity_pointer(root)))

    def test_pp9_a_synthetic_root_requires_the_explicit_environment_switch(self):
        with patch.dict(os.environ):
            os.environ.pop(builder.SYNTHETIC_ROOT_ENV, None)
            self.assertIn("PP9", failed(builder.plan_identity_pointer(clone("ready"))))

    def test_plan_status_and_verify_never_write(self):
        root = clone("ready")
        before = fx.tree_digest(root)
        builder.plan_identity_pointer(root)
        builder.identity_status(root)
        builder.verify_identity_pointer(root)
        builder.verify_persisted_candidate(root)
        self.assertEqual(fx.tree_digest(root), before)


class PointerWriteGateTests(unittest.TestCase):
    def assert_refused_without_writes(self, root, code, output):
        before = None
        self.assertEqual(code, 2, output)
        self.assertIn("REFUSED", output)

    def test_in_process_call_without_a_terminal_is_refused(self):
        root = clone("ready")
        before = fx.tree_digest(root)
        with patch.object(builder, "interactive_terminal", return_value=False), self.assertRaises(PermissionError):
            builder.create_identity_pointer(root)
        self.assertEqual(fx.tree_digest(root), before)

    def test_real_detection_stdin_stdout_pipes_are_refused_even_with_the_right_token(self):
        root = clone("ready")
        before = fx.tree_digest(root)
        code, output = fx.run_cli(fx.POINTER_MODULE, root, ["--create-pointer"], mode="pipe", lines=[builder.POINTER_TOKEN])
        self.assertEqual(code, 2, output)
        self.assertIn("interactive terminal", output)
        self.assertEqual(fx.tree_digest(root), before)

    def test_terminal_on_stdin_only_or_stdout_only_is_refused(self):
        for mode in ("tty-in-only", "tty-out-only"):
            with self.subTest(mode=mode):
                root = clone("ready")
                before = fx.tree_digest(root)
                code, output = fx.run_cli(fx.POINTER_MODULE, root, ["--create-pointer"], mode=mode, lines=[builder.POINTER_TOKEN])
                self.assertEqual(code, 2, output)
                self.assertEqual(fx.tree_digest(root), before)

    def test_wrong_empty_or_partial_token_is_refused(self):
        for token in ("", "yes", builder.POINTER_TOKEN[:-1], builder.POINTER_TOKEN.lower(), "CREATE-R11-POINTER-000000000000"):
            with self.subTest(token=token):
                root = clone("ready")
                before = fx.tree_digest(root)
                code, output = fx.run_cli(fx.POINTER_MODULE, root, ["--create-pointer"], mode="tty", lines=[token])
                self.assertEqual(code, 2, output)
                self.assertIn("confirmation token mismatch", output)
                self.assertEqual(fx.tree_digest(root), before)

    def test_typed_token_creates_exactly_the_canonical_pointer_and_a_record(self):
        root = clone("ready")
        code, output = fx.run_cli(fx.POINTER_MODULE, root, ["--create-pointer"], mode="tty", lines=[builder.POINTER_TOKEN])
        self.assertEqual(code, 0, output)
        pointer = root / builder.IDENTITY_CONFIG_PATH
        self.assertEqual(pointer.read_bytes(), builder.canonical_pointer_bytes())
        self.assertEqual(stat.S_IMODE(pointer.stat().st_mode), 0o600)
        record = json.loads((root / builder.POINTER_CREATION_RECORD_PATH).read_text())
        self.assertEqual((record["pointer_sha256"], record["interactive_terminal"], record["synthetic_root"]), (builder.POINTER_SHA256, True, True))
        self.assertEqual(record["approval_record_sha256"], fx.sha256(root / builder.APPROVAL_PATH))
        self.assertEqual(record["tool_sha256"], fx.sha256(fx.REPO / builder.BUILDER_PATH))
        self.assertEqual(builder.identity_status(root)["state"], "S1_POINTER_ONLY")
        added = set(fx.tree_digest(root)) - set(fx.tree_digest(_TEMPLATES["ready"]))
        self.assertEqual(added, {builder.IDENTITY_CONFIG_PATH, builder.POINTER_CREATION_RECORD_PATH, "evaluation/v4_runs/.namespace-allocation.lock"} & added | added)
        self.assertEqual({p for p in added if not p.endswith(".lock")}, {builder.IDENTITY_CONFIG_PATH, builder.POINTER_CREATION_RECORD_PATH})

    def test_second_run_is_idempotent_and_writes_nothing(self):
        root = clone("s1")
        before = fx.tree_digest(root)
        code, output = fx.run_cli(fx.POINTER_MODULE, root, ["--create-pointer"], mode="tty", lines=[builder.POINTER_TOKEN])
        self.assertEqual(code, 0, output)
        self.assertIn("ALREADY_CREATED", output)
        self.assertEqual(fx.tree_digest(root), before)

    def test_a_missing_record_is_completed_without_touching_the_pointer(self):
        root = clone("s1")
        pointer = root / builder.IDENTITY_CONFIG_PATH
        before_stat = (pointer.stat().st_mtime_ns, pointer.stat().st_ino)
        (root / builder.POINTER_CREATION_RECORD_PATH).unlink()
        code, output = fx.run_cli(fx.POINTER_MODULE, root, ["--create-pointer"], mode="tty", lines=[builder.POINTER_TOKEN])
        self.assertEqual(code, 0, output)
        self.assertIn("RECORD_COMPLETED", output)
        self.assertEqual((pointer.stat().st_mtime_ns, pointer.stat().st_ino), before_stat)
        self.assertEqual(pointer.read_bytes(), builder.canonical_pointer_bytes())

    def test_an_existing_non_canonical_pointer_is_never_overwritten(self):
        root = clone("ready")
        pointer = root / builder.IDENTITY_CONFIG_PATH
        pointer.write_text("{\"partial\": ")
        before = fx.tree_digest(root)
        code, output = fx.run_cli(fx.POINTER_MODULE, root, ["--create-pointer"], mode="tty", lines=[builder.POINTER_TOKEN])
        self.assertEqual(code, 2, output)
        self.assertEqual(fx.tree_digest(root), before)
        self.assertEqual(pointer.read_text(), "{\"partial\": ")

    def test_write_environment_requires_the_synthetic_switch_for_a_non_production_root(self):
        root = clone("ready")
        with patch.object(builder, "interactive_terminal", return_value=True), patch.dict(os.environ):
            os.environ.pop(builder.SYNTHETIC_ROOT_ENV, None)
            with self.assertRaisesRegex(PermissionError, builder.SYNTHETIC_ROOT_ENV):
                builder.require_write_environment(root, "test action")
            os.environ[builder.SYNTHETIC_ROOT_ENV] = "1"
            builder.require_write_environment(root, "test action")  # positive control

    def test_exclusive_create_primitive_refuses_to_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "x"
            target.write_bytes(b"original")
            with self.assertRaises(FileExistsError):
                builder._write_exclusive(target, b"replacement")
            self.assertEqual(target.read_bytes(), b"original")

    def test_a_pointer_that_reads_back_differently_is_reported_and_never_deleted(self):
        root = clone("ready")
        real = builder._write_exclusive

        def corrupt(path, data):
            real(path, data[:-1] + b" ")
        with patch.object(builder, "interactive_terminal", return_value=True), \
                patch.object(builder, "confirm_with_token", return_value=None), \
                patch.object(builder, "_write_exclusive", side_effect=corrupt):
            with self.assertRaisesRegex(RuntimeError, "POINTER_READBACK_MISMATCH"):
                builder.create_identity_pointer(root)
        self.assertTrue((root / builder.IDENTITY_CONFIG_PATH).exists())  # nothing is deleted automatically
        self.assertFalse((root / builder.POINTER_CREATION_RECORD_PATH).exists())
        self.assertEqual(builder.identity_status(root)["state"], "ANOMALY_POINTER_NOT_CANONICAL")

    def test_non_production_root_without_the_switch_is_refused(self):
        root = clone("ready")
        before = fx.tree_digest(root)
        env = {k: v for k, v in fx.cli_env().items() if k != builder.SYNTHETIC_ROOT_ENV}
        code, output = fx.run_cli(fx.POINTER_MODULE, root, ["--create-pointer"], mode="tty", lines=[builder.POINTER_TOKEN], env=env)
        self.assertEqual(code, 2, output)
        self.assertEqual(fx.tree_digest(root), before)

    def test_an_unsigned_draft_approval_cannot_authorize_creation(self):
        root = clone("ready")
        approval = json.loads((root / builder.APPROVAL_PATH).read_text())
        approval.update(status=builder.APPROVAL_DRAFT, approver=None, signed_at_utc=None)
        fx.write_approval(root, approval)
        before = fx.tree_digest(root)
        code, output = fx.run_cli(fx.POINTER_MODULE, root, ["--create-pointer"], mode="tty", lines=[builder.POINTER_TOKEN])
        self.assertEqual(code, 2, output)
        self.assertEqual(fx.tree_digest(root), before)

    def test_read_only_modes_never_write_even_when_run_as_commands(self):
        for flags in (["--plan"], ["--status"], ["--verify"], ["--verify-freeze"], ["--print-approval-draft"], []):
            with self.subTest(flags=flags):
                root = clone("s2")
                before = fx.tree_digest(root)
                code, output = fx.run_cli(fx.POINTER_MODULE, root, flags, mode="pipe")
                self.assertIn(code, (0, 1), output)
                self.assertNotIn("REFUSED", output)
                self.assertEqual(fx.tree_digest(root), before)

    def test_builder_source_contains_no_delete_or_replace_primitive(self):
        # Source inspection only; deliberately not counted as mutation evidence.
        tree = ast.parse((fx.REPO / builder.BUILDER_PATH).read_text())
        called = {node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
                  for node in ast.walk(tree) if isinstance(node, ast.Call)}
        self.assertFalse(called & {"remove", "unlink", "rename", "replace", "rmtree", "rmdir", "removedirs", "truncate"}, called)


class StatusAndVerifyTests(unittest.TestCase):
    def test_state_machine(self):
        self.assertEqual(builder.identity_status(clone("s0"))["state"], "S0_NOT_ACTIVATED")
        self.assertEqual(builder.identity_status(clone("s1"))["state"], "S1_POINTER_ONLY")
        self.assertEqual(builder.identity_status(clone("s2"))["state"], "S2_FREEZE_PERSISTED")

    def test_anomalies_are_reported_not_repaired(self):
        cases = {}
        root = clone("s1"); (root / builder.IDENTITY_CONFIG_PATH).write_text("tampered"); cases["ANOMALY_POINTER_NOT_CANONICAL"] = root
        root = clone("s2"); (root / builder.IDENTITY_CONFIG_PATH).unlink(); cases["ANOMALY_FREEZE_WITHOUT_POINTER"] = root
        root = clone("s1"); (root / builder.IDENTITY_CONFIG_PATH).unlink(); cases["ANOMALY_RECORD_WITHOUT_POINTER"] = root
        root = clone("s1"); (root / builder.POINTER_CREATION_RECORD_PATH).unlink(); cases["ANOMALY_POINTER_WITHOUT_CREATION_RECORD"] = root
        root = clone("s2"); data = (root / builder.EXPECTED_FREEZE_PATH).read_bytes(); (root / builder.EXPECTED_FREEZE_PATH).write_bytes(data.replace(b"9.63c-r11", b"9.63c-r12", 1)); cases["ANOMALY_FREEZE_NOT_REPRODUCIBLE"] = root
        for expected, root in cases.items():
            with self.subTest(expected=expected):
                before = fx.tree_digest(root)
                self.assertEqual(builder.identity_status(root)["state"], expected)
                self.assertEqual(fx.tree_digest(root), before)

    def test_verify_accepts_a_correct_pointer_with_and_without_a_freeze(self):
        for name in ("s1", "s2"):
            with self.subTest(root=name):
                result = builder.verify_identity_pointer(clone(name))
                self.assertTrue(result["ok"], result["checks"])

    def test_verify_rejects_altered_pointer_record_or_missing_pointer(self):
        root = clone("s1"); (root / builder.IDENTITY_CONFIG_PATH).write_bytes(builder.canonical_pointer_bytes() + b" ")
        self.assertFalse(builder.verify_identity_pointer(root)["ok"])
        root = clone("s1"); record = root / builder.POINTER_CREATION_RECORD_PATH
        data = json.loads(record.read_text()); data["approval_record_sha256"] = "0" * 64; record.write_text(json.dumps(data))
        self.assertFalse(builder.verify_identity_pointer(root)["ok"])
        self.assertFalse(builder.verify_identity_pointer(clone("ready"))["ok"])

    def test_verify_notices_a_freeze_that_resolves_badly(self):
        root = clone("s2")
        (root / "scripts/v3_namespace_allocator.py").write_bytes((root / "scripts/v3_namespace_allocator.py").read_bytes() + b"\n#")
        self.assertFalse(builder.verify_identity_pointer(root)["ok"])


class PersistedFreezeTests(unittest.TestCase):
    """The read-only 'verify persisted freeze' entry (condition I4)."""

    def test_an_untouched_freeze_reassembles_byte_for_byte(self):
        result = builder.verify_persisted_candidate(clone("s2"))
        self.assertTrue(result["ok"], result)

    def test_actual_freeze_equals_the_prediction_in_the_approval(self):
        root = clone("s2")
        approval = json.loads((root / builder.APPROVAL_PATH).read_text())
        self.assertEqual(fx.sha256(root / builder.EXPECTED_FREEZE_PATH), approval["freeze"]["predicted_sha256"])

    def test_a_hand_edited_freeze_is_detected(self):
        root = clone("s2")
        path = root / builder.EXPECTED_FREEZE_PATH
        document = json.loads(path.read_text())
        document["execution_permission"] = True
        path.write_text(json.dumps(document, sort_keys=True, indent=2) + "\n")
        self.assertFalse(builder.verify_persisted_candidate(root)["ok"])

    def test_a_member_changed_after_the_freeze_is_detected(self):
        root = clone("s2")
        target = root / "scripts/append_only_ledger.py"
        target.write_bytes(target.read_bytes() + b"\n#")
        self.assertFalse(builder.verify_persisted_candidate(root)["ok"])

    def test_missing_or_symlinked_freeze_is_not_ok(self):
        self.assertFalse(builder.verify_persisted_candidate(clone("s1"))["ok"])
        root = clone("s2")
        (root / builder.EXPECTED_FREEZE_PATH).rename(root / "moved.json")
        os.symlink(root / "moved.json", root / builder.EXPECTED_FREEZE_PATH)
        self.assertFalse(builder.verify_persisted_candidate(root)["ok"])

    def test_assemble_still_refuses_an_existing_target_by_default(self):
        with self.assertRaisesRegex(RuntimeError, "already exists"):
            builder.assemble_candidate(clone("s2"), created_at_utc=fx.CREATED_AT)

    def test_persist_never_overwrites_an_existing_freeze(self):
        root = clone("s2")
        before = (root / builder.EXPECTED_FREEZE_PATH).read_bytes()
        with self.assertRaises(RuntimeError):
            builder.persist_candidate(builder.assemble_candidate(clone("s1"), created_at_utc=fx.CREATED_AT), root)
        self.assertEqual((root / builder.EXPECTED_FREEZE_PATH).read_bytes(), before)

    def test_allow_existing_target_is_only_used_by_the_verification_path(self):
        source = (fx.REPO / builder.BUILDER_PATH).read_text()
        self.assertEqual(source.count("allow_existing_target=True"), 1)


class InventoryAndIssuerPinTests(unittest.TestCase):
    def test_member_seven_is_the_r11_issuer_and_the_count_stays_20(self):
        self.assertEqual(len(builder.MEMBER_PATHS), 20)
        self.assertEqual(len(set(builder.MEMBER_PATHS)), 20)
        self.assertEqual(builder.MEMBER_PATHS[6], builder.ISSUER_PATH)
        self.assertNotIn("scripts/issue_step9_63a_r3_authorization.py", builder.MEMBER_PATHS)
        self.assertEqual(builder.REPLACED["scripts/issue_step9_63a_r3_authorization.py"], builder.ISSUER_PATH)

    def test_the_old_r7_issuer_file_is_untouched(self):
        r10 = {m["path"]: m["sha256"] for m in json.loads((fx.REPO / builder.PARENT_PATH).read_text())["members"]}
        self.assertEqual(fx.sha256(fx.REPO / "scripts/issue_step9_63a_r3_authorization.py"), r10["scripts/issue_step9_63a_r3_authorization.py"])

    def test_issuer_sha_is_pinned_to_the_actual_bytes_and_recorded_in_the_freeze(self):
        self.assertEqual(builder.ISSUER_SHA256, fx.sha256(fx.REPO / builder.ISSUER_PATH))
        freeze = json.loads((clone("s2") / builder.EXPECTED_FREEZE_PATH).read_text())
        self.assertEqual((freeze["authorization_issuer_path"], freeze["authorization_issuer_sha256"]), (builder.ISSUER_PATH, builder.ISSUER_SHA256))
        self.assertEqual(freeze["member_count"], 20)

    def test_a_different_issuer_is_rejected_by_the_builder(self):
        root = clone("ready")
        (root / builder.ISSUER_PATH).write_bytes((root / builder.ISSUER_PATH).read_bytes() + b"\n#")
        (root / builder.IDENTITY_CONFIG_PATH).write_bytes(builder.canonical_pointer_bytes())
        with self.assertRaisesRegex(RuntimeError, "approved r11 issuer SHA mismatch"):
            builder.assemble_candidate(root, created_at_utc=fx.CREATED_AT)

    def test_changed_member_pins_are_exact(self):
        self.assertEqual(builder.CHANGED_SHA256["scripts/v3_runner_identity.py"], "a0f5670d3834d5f91391b41a33fbac669d6162587bc620e9bd3acf202aa3c6a5")
        for path, pin in builder.CHANGED_SHA256.items():
            self.assertEqual(fx.sha256(fx.REPO / path), pin, path)


class ApprovalRecordTests(unittest.TestCase):
    def setUp(self):
        self.root = clone("s0")
        self.draft = builder.build_approval(self.root, created_at_utc=fx.CREATED_AT)

    def test_the_draft_pins_everything_required(self):
        draft = self.draft
        self.assertEqual((draft["status"], draft["approver"], draft["signed_at_utc"]), (builder.APPROVAL_DRAFT, None, None))
        self.assertEqual(draft["pointer"], {"path": builder.IDENTITY_CONFIG_PATH, "canonical_sha256": builder.POINTER_SHA256, "canonical_size": 389})
        self.assertEqual(set(draft["members"]), set(builder.MEMBER_PATHS))
        self.assertEqual(set(draft["named_pins"]), {"resolver", "consumer", "scanner", "builder", "producer", "issuer"})
        self.assertEqual(len(draft["unchanged_members"]), 13)  # 20 members: 13 byte-identical to r10, 7 changed/new
        self.assertEqual(draft["historical"]["lifecycle_ledger_prefix"]["length"], 1161)
        self.assertEqual(draft["historical"]["r10_freeze_manifest"]["sha256"], builder.PARENT_SHA256)
        self.assertRegex(draft["repository_aggregate"]["sha256"], "^[0-9a-f]{64}$")
        self.assertRegex(draft["freeze"]["predicted_sha256"], "^[0-9a-f]{64}$")
        self.assertTrue(draft["issuance"]["authorization_id"].startswith(builder.R11_AUTHORIZATION_ID_PREFIX))
        self.assertTrue(draft["ar14"]["must_be_retired_before_pointer_creation"])

    def test_an_unsigned_draft_never_verifies_as_signed(self):
        problems = builder.verify_approval(self.root, self.draft)
        self.assertTrue(any("not signed" in p for p in problems), problems)

    def test_only_a_fully_signed_record_verifies(self):
        # each signature attribute is checked on its own, so every other one is kept valid here
        base = copy.deepcopy(self.draft)
        base.update(status=builder.APPROVAL_SIGNED, approver="x", signed_at_utc="2026-01-01T00:00:00+00:00")
        self.assertEqual(builder.verify_approval(self.root, base), [])
        for label, change in (("status", {"status": builder.APPROVAL_DRAFT}), ("approver", {"approver": ""}),
                              ("signing time", {"signed_at_utc": "yesterday"})):
            with self.subTest(missing=label):
                self.assertTrue(builder.verify_approval(self.root, {**base, **change}), label)

    def test_issuer_pin_and_regression_result_pin_are_enforced_by_the_approval(self):
        base = copy.deepcopy(self.draft)
        base.update(status=builder.APPROVAL_SIGNED, approver="x", signed_at_utc="2026-01-01T00:00:00+00:00")
        with patch.object(builder, "ISSUER_SHA256", "0" * 64):
            self.assertTrue(any("issuer" in p for p in builder.verify_approval(self.root, base)))
        result = self.root / "evaluation/v1_2_3/regression_result.json"
        result.write_text("{}")
        with_result = builder.build_approval(self.root, created_at_utc=fx.CREATED_AT, regression_result="evaluation/v1_2_3/regression_result.json")
        with_result.update(status=builder.APPROVAL_SIGNED, approver="x", signed_at_utc="2026-01-01T00:00:00+00:00")
        self.assertEqual(builder.verify_approval(self.root, with_result), [])
        result.write_text("{ }")
        self.assertTrue(any("regression" in p for p in builder.verify_approval(self.root, with_result)))

    def test_member_pins_are_enforced_independently_of_the_aggregate(self):
        # The issuer verifies the approval with check_aggregate=False, so the member pins must hold on their own.
        signed = copy.deepcopy(self.draft)
        signed.update(status=builder.APPROVAL_SIGNED, approver="x", signed_at_utc="2026-01-01T00:00:00+00:00")
        self.assertEqual(builder.verify_approval(self.root, signed, check_aggregate=False), [])
        extra = copy.deepcopy(signed)
        extra["members"]["scripts/not_a_member.py"] = "0" * 64
        missing = copy.deepcopy(signed)
        missing["members"].pop("scripts/append_only_ledger.py")
        wrong = copy.deepcopy(signed)
        wrong["members"]["scripts/append_only_ledger.py"] = "0" * 64
        for label, record in (("extra member", extra), ("missing member", missing), ("wrong member pin", wrong)):
            with self.subTest(case=label):
                self.assertTrue(builder.verify_approval(self.root, record, check_aggregate=False))
        with_member_edit = self.root / "scripts/append_only_ledger.py"
        with_member_edit.write_bytes(with_member_edit.read_bytes() + b"\n#")
        self.assertTrue(any("member differs" in p for p in builder.verify_approval(self.root, signed, check_aggregate=False)))

    def test_signing_makes_a_consistent_record_verify(self):
        signed = copy.deepcopy(self.draft)
        signed.update(status=builder.APPROVAL_SIGNED, approver="x", signed_at_utc="2026-01-01T00:00:00+00:00")
        self.assertEqual(builder.verify_approval(self.root, signed), [])

    def test_aggregate_is_stable_changes_with_content_and_ignores_noise(self):
        first = builder.repository_aggregate(self.root)
        self.assertEqual(first, builder.repository_aggregate(self.root))
        for noise in ("__pycache__/x.pyc", "._AppleDouble", ".git/config", ".venv/lib/x", "models/m.bin"):
            path = self.root / noise
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("noise")
        self.assertEqual(first, builder.repository_aggregate(self.root))
        (self.root / "scripts/append_only_ledger.py").write_bytes((self.root / "scripts/append_only_ledger.py").read_bytes() + b" ")
        self.assertNotEqual(first["sha256"], builder.repository_aggregate(self.root)["sha256"])

    def test_aggregate_notices_symlinks_and_new_files(self):
        first = builder.repository_aggregate(self.root)
        os.symlink("scripts", self.root / "alias")
        self.assertNotEqual(first["sha256"], builder.repository_aggregate(self.root)["sha256"])

    def test_predicted_freeze_does_not_depend_on_unrelated_repository_content(self):
        one = builder.predict_freeze(self.root, fx.CREATED_AT)
        (self.root / "evaluation/v1_2_3/unrelated.txt").write_text("x")
        self.assertEqual(one, builder.predict_freeze(self.root, fx.CREATED_AT))
        self.assertNotEqual(one["predicted_sha256"], builder.predict_freeze(self.root, "2026-02-02T00:00:00+00:00")["predicted_sha256"])


if __name__ == "__main__":
    unittest.main()
