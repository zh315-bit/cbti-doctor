"""Step 9.63c-r5c10ak: the r11 preflight producer refuses to write evidence when the binding changed
during the connectivity probe (PREFLIGHT_BINDING_CHANGED_DURING_PROBE).

Supersedes the obsolete r5 test test_pre_post_state_change_fails_closed (its module is no longer an r11
member). Everything around the re-check is stood in on a temporary directory: no registry, artifact,
network or real repository path is touched.
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts import preflight_step9_63c_r11_mac_local as producer

PRODUCTION_ROOT = Path("/Volumes/Elements/cbti-doctor-main")


class _FakeRoot:
    """Stands in for the producer's ROOT so the Mac-local runtime check passes on any machine."""

    def __init__(self, scratch: Path):
        self.scratch = scratch

    def resolve(self):
        return PRODUCTION_ROOT

    def __fspath__(self):  # paths the producer derives from ROOT (e.g. the artifact path it prints) stay in the scratch dir
        return str(self.scratch)

    __str__ = __fspath__

    def __truediv__(self, other):
        if other == ".venv/bin/python":
            return Path(sys.executable)
        return self.scratch / other


class ProducerRecheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="r11-producer-recheck-")
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.auth_file = self.dir / "authorization.json"
        self.auth_file.write_text(json.dumps({"authorization_id": "a"}))
        self.freeze_file = self.dir / "freeze.json"
        self.freeze_file.write_text("{}")
        self.producer_sha = producer.sha256_file(Path(producer.__file__))
        self.authorization = {"authorization_id": "auth-step9_63c_r11-" + "0" * 32, "attempt_id": "attempt-x"}

    def freeze(self, producer_sha=None):
        return {"preflight_producer_path": producer.PRODUCER_PATH, "preflight_producer_sha256": producer_sha or self.producer_sha}

    def run_main(self, *, refreshed=None, refreshed_freeze=None, refreshed_file=None, change_file=False):
        identity = {"runner_freeze_path": "evaluation/v1_2_3/step9_63c_r11_runner_freeze.json"}
        resolve = MagicMock(side_effect=[(self.freeze(), self.freeze_file, identity),
                                         (refreshed_freeze or self.freeze(), refreshed_file or self.freeze_file, identity)])
        validate = MagicMock(side_effect=[(self.authorization, {}, self.auth_file), (refreshed or self.authorization, {}, self.auth_file)])
        writer, terminal = MagicMock(return_value="f" * 64), MagicMock()

        def payload(**kwargs):
            if change_file:  # the manifest bytes change while the probe runs
                self.auth_file.write_text(json.dumps({"authorization_id": "changed"}))
            return {"authorization_manifest_sha256": kwargs["authorization_sha256"]}
        out = io.StringIO()
        with patch("scripts.v3_runner_identity.resolve_current_freeze", resolve), \
             patch("scripts.preflight_step9_63c_current_mac_local.validate_authorization_state", validate), \
             patch.object(producer, "ensure_registry_initialized"), \
             patch.object(producer, "claim_invocation", return_value=("preflight-x", self.dir / "artifact.json", 0, "0" * 64)), \
             patch.object(producer, "write_artifact", writer), patch.object(producer, "append_terminal_event", terminal), \
             patch.object(producer, "build_preflight_payload", side_effect=payload), \
             patch.object(producer, "REGISTRY_PATH", self.dir / "registry.jsonl"), \
             patch.object(producer, "ROOT", _FakeRoot(self.dir)), \
             patch.object(sys, "platform", "darwin"), \
             patch.object(Path, "cwd", classmethod(lambda cls: PRODUCTION_ROOT)), \
             patch("dotenv.load_dotenv"), patch.dict(os.environ, {"DEEPSEEK_API_KEY": "synthetic"}), \
             patch("scripts.preflight_step9_63b_mac_local.connectivity", return_value={"dns_ready": True}), \
             redirect_stdout(out):
            code = producer.main(["--authorization-file", str(self.auth_file)])
        return code, out.getvalue(), writer, terminal

    def assert_refused(self, result):
        code, output, writer, terminal = result
        self.assertEqual(code, 1)
        self.assertIn("FAIL_CLOSED_R11_PREFLIGHT", output)
        writer.assert_not_called()  # no evidence is written
        terminal.assert_called_once()
        self.assertEqual(terminal.call_args.kwargs["failure_stage"], "PREFLIGHT_FAILED")  # the claim is burned, not reusable

    def test_positive_control_unchanged_binding_writes_the_evidence(self):
        code, output, writer, terminal = self.run_main()
        self.assertEqual(code, 0, output)
        writer.assert_called_once()
        self.assertNotIn("failure_stage", terminal.call_args.kwargs)

    def test_a_changed_authorization_state_is_refused(self):
        self.assert_refused(self.run_main(refreshed={**self.authorization, "authorization_status": "RETIRED"}))

    def test_a_changed_freeze_file_is_refused(self):
        other = self.dir / "other_freeze.json"
        other.write_text('{"x": 1}')
        self.assert_refused(self.run_main(refreshed_file=other))

    def test_a_changed_producer_pin_in_the_freeze_is_refused(self):
        self.assert_refused(self.run_main(refreshed_freeze=self.freeze(producer_sha="0" * 64)))

    def test_changed_authorization_manifest_bytes_are_refused(self):
        self.assert_refused(self.run_main(change_file=True))


if __name__ == "__main__":
    unittest.main()
