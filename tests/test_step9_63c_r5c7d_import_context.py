"""Import-context tests for the r10-era Mac-local preflight producer.

Step 9.63c-r5c10ad AR-5: the original tests asserted that the r10 snapshot was live
and executable (``ISSUED_EXECUTABLE``). Under the r11-only resolver that can never
hold again, by design. The import-context properties are kept (direct-script
bootstrap reaches the repository root; direct and module contexts reach the same
identity outcome), while "live r10 executable" is replaced by "r10 archival content
hashes equal their recorded values" and "the live r10 snapshot fails closed".
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
# Recorded values: r10 freeze manifest and r10 authorization manifest (record.md,
# Steps 9.63c-r5c5b / r5c6), r10 pointer (identity_config_sha256 inside the r10 manifest).
R10_ARCHIVE = {
    "evaluation/v1_2_3/step9_63c_r5c5b_runner_freeze_r10.json":
        "d24244235e51e7bf6c8567880c654fe3fd73b87fa1bfe1ab0f10dfdc94db2693",
    "evaluation/v1_2_3/step9_63c_r5c6_r10_v3_authorization_manifest.json":
        "beac52d1ed3bc11efa02b1a924a8abc7b210171bf5cc1b7910011a6ef9741241",
    "evaluation/v1_2_3/step9_63c_r5c4_current_runner_identity.json":
        "0f908fb566ad69f52246bf3c762d46d476c1bad40b0be300c152a576a64df412",
}
# The only acceptable outcomes of a live r10 snapshot: formal r11 identity absent, or
# present and therefore not r10.
FAIL_CLOSED = ("current runner identity pointer is missing or unsafe", "R10_FREEZE_MISMATCH")


def archive_hashes() -> dict[str, str]:
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in R10_ARCHIVE}


def run(code: str) -> dict:
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT,
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


class Step963cR5c7dImportContextTests(unittest.TestCase):
    def test_direct_script_import_context_bootstraps_root_and_r10_is_archival_only(self):
        self.assertEqual(archive_hashes(), R10_ARCHIVE)
        outcome = run(r'''
import importlib, json, runpy, sys
from pathlib import Path
root = Path.cwd().resolve()
script = root / "scripts/preflight_step9_63c_r5c7_mac_local.py"
script_dir = script.parent
sys.path = [str(script_dir)] + [p for p in sys.path if p and Path(p).resolve() != root]
assert Path(sys.path[0]).resolve() == script_dir
try:
    importlib.import_module("scripts.authorization_lifecycle")
except ModuleNotFoundError as exc:
    assert exc.name == "scripts"
else:
    raise AssertionError("test did not reproduce missing repository root")
namespace = runpy.run_path(str(script), run_name="r5c7d_direct_import_test")
importlib.import_module("scripts.authorization_lifecycle")  # root bootstrapped by the script
stages = []
tracker = namespace["StageTracker"]()
try:
    namespace["_snapshot"](lambda value: (stages.append(value), tracker.set(value)))
except RuntimeError as exc:
    error = str(exc)
else:
    error = None
print(json.dumps({"root_bootstrapped": True, "first_stage": stages[0] if stages else None,
                  "snapshot_error": error}))
''')
        self.assertTrue(outcome["root_bootstrapped"])
        self.assertEqual(outcome["first_stage"], "R10_FREEZE_VALIDATION")
        self.assertIn(outcome["snapshot_error"], FAIL_CLOSED)
        self.assertEqual(archive_hashes(), R10_ARCHIVE)

    def test_module_context_and_direct_bootstrap_reach_same_identity_outcome(self):
        outcome = run(r'''
import json, runpy, sys
from pathlib import Path
root = Path.cwd().resolve()
script = root / "scripts/preflight_step9_63c_r5c7_mac_local.py"
sys.path = [str(script.parent)] + [p for p in sys.path if p and Path(p).resolve() != root]
def attempt(namespace):
    try:
        namespace["_snapshot"]()
    except RuntimeError as exc:
        return [type(exc).__name__, str(exc)]
    return ["NO_ERROR", ""]
direct = attempt(runpy.run_path(str(script), run_name="direct_context"))
sys.path.insert(0, str(root))
module = attempt(runpy.run_module("scripts.preflight_step9_63c_r5c7_mac_local", run_name="module_context"))
print(json.dumps({"direct": direct, "module": module}))
''')
        self.assertEqual(outcome["direct"], outcome["module"])
        self.assertEqual(outcome["direct"][0], "RuntimeError")
        self.assertIn(outcome["direct"][1], FAIL_CLOSED)
        self.assertEqual(archive_hashes(), R10_ARCHIVE)


if __name__ == "__main__":
    unittest.main()
