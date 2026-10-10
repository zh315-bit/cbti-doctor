"""Run an archived legacy test module on a TEMPORARY ROOT instead of the real repository (Step 9.63c-r5c10ak).

Some legacy test modules exercise production code whose default paths (lifecycle ledger, run root,
transaction journals, authorization manifests, namespace lock) are module constants rooted at the real
repository. After the r11 activation those defaults point at real activation state. Instead of
editing the legacy tests, their original bytes are archived under tests/retired/ (standing rule) and
this helper runs them, unchanged, inside a private mirror of the repository:

  * scripts/, tests/ and the Python files directly under evaluation/ are COPIED, so every module that
    computes its root from __file__ resolves it inside the mirror;
  * evaluation/v4_runs/ is COPIED, and every activation-state file in evaluation/v1_2_3/ (the ledger,
    every *authorization_manifest.json, the r11 Freeze, pointer, records, approval) is COPIED;
  * everything else is SYMLINKED read-only (writes through a symlink are stopped by the guard and the
    session guard, which both protect the real repository).

The child process installs tests/session_safety.py for the REAL repository, so any attempt to write
the real activation state from inside the mirror still stops the run.
"""
from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RETIRED = REPO / "tests" / "retired"
COPY_TOP = {"scripts", "tests"}
SKIP_TOP = {".git", ".venv", "__pycache__"}
COPY_V123 = ("authorization_lifecycle_events.jsonl",)


def _copy_tree(source: Path, target: Path) -> None:
    shutil.copytree(source, target, symlinks=True, ignore=shutil.ignore_patterns("__pycache__", "._*"))


def build_mirror(base: Path) -> Path:
    root = Path(base).resolve() / "mirror"
    root.mkdir(parents=True)
    for entry in REPO.iterdir():
        if entry.name in SKIP_TOP or entry.name.startswith("._"):
            continue
        if entry.name in COPY_TOP:
            _copy_tree(entry, root / entry.name)
        elif entry.name == "evaluation":
            _build_evaluation(entry, root / "evaluation")
        else:
            (root / entry.name).symlink_to(entry)
    return root


def _build_evaluation(source: Path, target: Path) -> None:
    target.mkdir()
    for entry in source.iterdir():
        if entry.name.startswith("._") or entry.name == "__pycache__":
            continue
        if entry.name == "v4_runs":
            _copy_tree(entry, target / entry.name)
        elif entry.name == "v1_2_3":
            (target / entry.name).mkdir()
            pinned = _pinned_v123_files()
            for item in entry.iterdir():
                if item.name.startswith("._"):
                    continue
                activation = (item.name in COPY_V123 or item.name.endswith("authorization_manifest.json")
                              or item.name.startswith("step9_63c_r11_") or item.name in pinned)
                if activation and item.is_file():
                    shutil.copyfile(item, target / entry.name / item.name)
                else:
                    (target / entry.name / item.name).symlink_to(item)
        elif entry.is_file() and entry.suffix == ".py":
            shutil.copyfile(entry, target / entry.name)
        else:
            (target / entry.name).symlink_to(entry)


def _pinned_v123_files() -> set[str]:
    """Files the identity resolver and the historical-pin checks require to be REGULAR files (not symlinks):
    the members of the current runner freeze and every historical pin."""
    names = set()
    freeze = json.loads((REPO / "evaluation/v1_2_3/step9_63c_r11_runner_freeze.json").read_text(encoding="utf-8"))
    for member in freeze.get("members", []):
        names.add(member["path"])
    inventory = json.loads((REPO / "evaluation/v1_2_3/step9_60a_v3_historical_integrity_audit.json").read_text(encoding="utf-8"))
    names |= {pin["path"] for pin in inventory["historical_pins"].values()}
    sys.path.insert(0, str(REPO))
    from scripts.preflight_step9_62b_mac_local import SUPPLEMENTAL_HISTORICAL_PINS
    names |= set(SUPPLEMENTAL_HISTORICAL_PINS)
    return {Path(n).name for n in names if n.startswith("evaluation/v1_2_3/")}


INNER = r'''
import json, os, sys, traceback, unittest
root, repo, module, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
ids = sys.argv[5:]
sys.path[:0] = [os.path.join(root, "tests"), root]
import session_safety
session_safety.install(repo)          # protect the REAL repository from inside the mirror
os.chdir(root)
class R(unittest.TextTestResult):
    rows = {}
    def startTest(self, t):
        os.environ["CBTI_GUARD_CURRENT_TEST"] = t.id(); R.rows[t.id()] = {"outcome": "pass"}; super().startTest(t)
    def _m(self, t, o, e=None):
        R.rows.setdefault(t.id(), {})["outcome"] = o
        if e: R.rows[t.id()]["detail"] = "".join(traceback.format_exception(*e))[-2500:]
    def addFailure(self, t, e): super().addFailure(t, e); self._m(t, "fail", e)
    def addError(self, t, e): super().addError(t, e); self._m(t, "error", e)
    def addSkip(self, t, r): super().addSkip(t, r); R.rows[t.id()] = {"outcome": "skip", "detail": r}
suite = unittest.defaultTestLoader.loadTestsFromNames([module + "." + i for i in ids])
unittest.TextTestRunner(stream=open(os.devnull, "w"), resultclass=R).run(suite)
json.dump(R.rows, open(out, "w"), indent=1)
'''


def archive_path(original: str) -> Path:
    """The r5c10ak archive of `original` (a ".r5c10ak.retired" name when an older archive already uses the plain name)."""
    special = RETIRED / f"{original}.py.r5c10ak.retired"
    return special if special.exists() else RETIRED / f"{original}.py.retired"


def archived_tests(original: str) -> list[str]:
    """Class.method names of every test in the archived original module."""
    tree = ast.parse(archive_path(original).read_text(encoding="utf-8"))
    names = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name.startswith("test"):
                    names.append(f"{node.name}.{item.name}")
    return names


def run_isolated(original: str, ids: list[str], base: Path) -> dict:
    root = build_mirror(base)
    (root / "tests" / f"{original}.py").write_bytes(archive_path(original).read_bytes())
    out = Path(base) / "result.json"
    env = {k: v for k, v in os.environ.items() if k != "CBTI_SESSION_GUARD_INSTALLED"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    done = subprocess.run([sys.executable, "-c", INNER, str(root), str(REPO), original, str(out), *ids],
                          cwd=root, env=env, capture_output=True, text=True, timeout=1800)
    if done.returncode != 0 or not out.exists():
        raise RuntimeError(f"isolated run of {original} failed (exit {done.returncode}): {done.stderr[-3000:]}")
    return json.loads(out.read_text())


def make_module(namespace: dict, original: str, *, retired: dict[str, str]) -> None:
    """Populate a wrapper test module: one test per kept test of `original`, run on a temporary root.
    `retired` maps Class.method -> where its property is covered now (standing rule)."""
    kept = [name for name in archived_tests(original) if name not in retired]
    unknown = set(retired) - set(archived_tests(original))
    if unknown:
        raise RuntimeError(f"retired names not in {original}: {sorted(unknown)}")
    state: dict = {}

    def setUpModule():
        state["tmp"] = tempfile.TemporaryDirectory(prefix=f"isolated-{original}-")
        state["rows"] = run_isolated(original, kept, Path(state["tmp"].name))

    def tearDownModule():
        state["tmp"].cleanup()

    def make(name):
        def test(self):
            row = state["rows"].get(f"{original}.{name}")
            self.assertIsNotNone(row, f"{name} did not run in the isolated root")
            if row["outcome"] == "skip":
                self.skipTest(row.get("detail", ""))
            self.assertEqual(row["outcome"], "pass", row.get("detail", ""))
        test.__name__ = "test_" + name.replace(".", "__")
        return test

    attrs = {"__doc__": f"{original}, run unchanged on a temporary mirror of the repository.",
             "__module__": namespace["__name__"]}  # so unittest runs THIS module's setUpModule
    for name in kept:
        method = make(name)
        attrs[method.__name__] = method
    namespace["IsolatedLegacyTests"] = type("IsolatedLegacyTests", (unittest.TestCase,), attrs)
    namespace["setUpModule"] = setUpModule
    namespace["tearDownModule"] = tearDownModule
    namespace["ORIGINAL"] = original
    namespace["KEPT"] = kept
    namespace["RETIRED_HERE"] = retired
