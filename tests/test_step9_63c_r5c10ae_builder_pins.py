"""Step 9.63c-r5c10ae AR-10 / AR-11: r11 builder SHA pins and inlined frozen-input check.

All builder runs use temporary roots holding byte copies of the r11 member inventory
and a synthetic r11 pointer; no repository pointer or freeze is created.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from scripts import build_step9_63c_r11_runner_freeze as builder

REPO = Path(__file__).resolve().parents[1]
CONSUMER = "scripts/run_step9_63_v3_formal_execution.py"
RESOLVER = "scripts/v3_runner_identity.py"
SCANNER = "scripts/v3_execution_transaction.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@contextmanager
def synthetic_root():
    with tempfile.TemporaryDirectory(prefix="r11-pins-") as directory:
        root = Path(directory)
        for relpath in (set(builder.MEMBER_PATHS) - {builder.IDENTITY_CONFIG_PATH}) | {builder.PARENT_PATH}:
            (root / relpath).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / relpath, root / relpath)
        (root / builder.IDENTITY_CONFIG_PATH).write_text(json.dumps({
            "artifact_type": "V3_CURRENT_RUNNER_IDENTITY_POINTER",
            "status": "FROZEN_IDENTITY_POINTER_NOT_AUTHORIZATION",
            "runner_freeze_revision": "r11", "runner_freeze_path": builder.EXPECTED_FREEZE_PATH,
            "execution_permission": False}, sort_keys=True) + "\n", encoding="utf-8")
        yield root


@contextmanager
def scoped_adapter_stub(stub):
    """Equivalent of monkeypatch.setitem(sys.modules, ...) for unittest (pytest is not
    installed): install the stand-in, always restore the exact prior state, and assert
    it. The prior state is the real adapter module once r11 exists, or 'absent' while
    the formal r11 identity is missing and the real adapter cannot be imported."""
    import sys
    import scripts
    name, attribute = "scripts.run_step9_53_v3_identity_adapter", "run_step9_53_v3_identity_adapter"
    missing = object()
    modules_before = sys.modules.get(name, missing)
    attribute_before = scripts.__dict__.get(attribute, missing)
    sys.modules[name] = stub
    setattr(scripts, attribute, stub)
    try:
        yield stub
    finally:
        if modules_before is missing:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = modules_before
        if attribute_before is missing:
            scripts.__dict__.pop(attribute, None)
        else:
            setattr(scripts, attribute, attribute_before)
        assert sys.modules.get(name, missing) is modules_before, "adapter sys.modules entry not restored"
        assert scripts.__dict__.get(attribute, missing) is attribute_before, "adapter attribute not restored"


class BuilderPinTests(unittest.TestCase):

    def test_exact_inventory_assembles(self):
        with synthetic_root() as root:
            candidate = builder.assemble_candidate(root, created_at_utc="2026-10-09T00:00:00+00:00")
        members = {m["path"]: m["sha256"] for m in candidate["members"]}
        self.assertEqual(len(members), 20)
        for relpath, pin in builder.CHANGED_SHA256.items():
            self.assertEqual(members[relpath], pin)
        self.assertEqual(candidate["formal_entry_runner_sha256"], builder.CONSUMER_SHA256)

    def test_unreviewed_change_to_any_changed_member_is_rejected(self):
        for relpath in (CONSUMER, RESOLVER, SCANNER):
            with self.subTest(relpath=relpath), synthetic_root() as root:
                path = root / relpath
                path.write_bytes(path.read_bytes() + b"\n# unreviewed edit\n")
                parent = json.loads((root / builder.PARENT_PATH).read_text(encoding="utf-8"))
                r10 = {m["path"]: m["sha256"] for m in parent["members"]}
                self.assertNotEqual(digest(path), r10[relpath])  # differs from r10, yet must fail
                with self.assertRaisesRegex(RuntimeError, f"approved r11 member SHA mismatch: {relpath}"):
                    builder.assemble_candidate(root)

    def test_pin_table_must_cover_every_changed_member(self):
        with synthetic_root() as root, \
             patch.dict(builder.CHANGED_SHA256, clear=False) as pins:
            pins.pop(CONSUMER)
            with self.assertRaisesRegex(RuntimeError, "exactly one reviewed SHA pin"):
                builder.assemble_candidate(root)


class InlinedFrozenInputEquivalenceTests(unittest.TestCase):
    """AR-11: the inlined verify_frozen_inputs behaves exactly like the r5c4 original.

    Both functions import the frozen identity adapter internally. For this
    differential test only, a scoped stand-in (restored and asserted by
    scoped_adapter_stub) answers the
    agent-identity question identically for both; nothing is written and no
    repository identity artifact exists or is created.
    """

    @classmethod
    def setUpClass(cls):
        from scripts import build_step9_63c_r5c4_runner_freeze as legacy
        cls.legacy = legacy
        r10 = json.loads((REPO / builder.PARENT_PATH).read_text(encoding="utf-8"))
        cls.identities = r10["bound_identities"]

    def test_inlined_functions_are_verbatim_and_import_free(self):
        import ast
        import inspect
        for name in ("sha256_bytes", "nonsecret_model_configuration_matches", "verify_frozen_inputs"):
            with self.subTest(name=name):
                self.assertEqual(inspect.getsource(getattr(builder, name)),
                                 inspect.getsource(getattr(self.legacy, name)))
        tree = ast.parse(Path(builder.__file__).read_text(encoding="utf-8"))
        imported = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        self.assertNotIn("scripts.build_step9_63c_r5c4_runner_freeze", imported)
        self.assertNotIn("build_step9_63c_r5c4_runner_freeze", inspect.getsource(builder.build_candidate))
        self.assertEqual(len(builder.MEMBER_PATHS), 20)
        self.assertNotIn("scripts/build_step9_63c_r5c4_runner_freeze.py", builder.MEMBER_PATHS)

    def outcome(self, function, identities, agent=None, agent_ok=True, env=None):
        import os
        import types
        stub = types.SimpleNamespace(current_v3_agent_identity=lambda: (
            agent or identities["treatment_agent_sha256"], agent_ok))
        with scoped_adapter_stub(stub), patch.dict(os.environ, env or {}):
            try:
                function(REPO, identities)
            except Exception as error:  # compare type and message exactly
                return type(error).__name__, str(error)
            return None

    def test_adapter_stub_is_fully_restored_after_use(self):
        import sys
        import scripts
        name, attribute = "scripts.run_step9_53_v3_identity_adapter", "run_step9_53_v3_identity_adapter"
        missing = object()
        modules_before = sys.modules.get(name, missing)
        attribute_before = scripts.__dict__.get(attribute, missing)
        self.outcome(builder.verify_frozen_inputs, self.identities)
        self.assertIs(sys.modules.get(name, missing), modules_before)
        self.assertIs(scripts.__dict__.get(attribute, missing), attribute_before)
        if modules_before is not missing:  # r11 exists: the entry is the real module again
            self.assertTrue(hasattr(modules_before, "run"))
        # Restoration also happens when the body raises.
        with self.assertRaises(RuntimeError):
            with scoped_adapter_stub(object()):
                raise RuntimeError("body failure")
        self.assertIs(sys.modules.get(name, missing), modules_before)
        self.assertIs(scripts.__dict__.get(attribute, missing), attribute_before)

    def test_differential_behaviour_matches_original(self):
        base = dict(self.identities)
        scenarios = {
            "unchanged": ({}, {}),
            "agent_mismatch": ({}, {"agent": "f" * 64}),
            "agent_inventory_not_ok": ({}, {"agent_ok": False}),
            "benchmark_sha": ({"benchmark_sha256": "0" * 64}, {}),
            "benchmark_manifest_sha": ({"benchmark_manifest_sha256": "0" * 64}, {}),
            "case_count": ({"case_count": 39}, {}),
            "task_distribution": ({"task_distribution": {"KNOWLEDGE_QA": 40}}, {}),
            "case_order_fingerprint": ({"case_order_fingerprint_sha256": "abc"}, {}),
            "scoring_rubric": ({"scoring_rubric_sha256": "0" * 64}, {}),
            "dependency_lock": ({"dependency_lock_sha256": "0" * 64}, {}),
            "harness": ({"harness_sha256": "0" * 64}, {}),
            "scoring": ({"scoring_sha256": "0" * 64}, {}),
            "rag_configuration": ({"rag_configuration_fingerprint_sha256": "0" * 64}, {}),
            "model_configuration": ({}, {"env": {"DEEPSEEK_MODEL": "other-model"}}),
        }
        results = {}
        for label, (changes, options) in scenarios.items():
            with self.subTest(scenario=label):
                identities = {**base, **changes}
                original = self.outcome(self.legacy.verify_frozen_inputs, identities, **options)
                inlined = self.outcome(builder.verify_frozen_inputs, identities, **options)
                self.assertEqual(inlined, original)
                results[label] = inlined
        self.assertIsNone(results["unchanged"])
        self.assertTrue(all(results[label] is not None for label in scenarios if label != "unchanged"))


if __name__ == "__main__":
    unittest.main()
