"""(r5c10ak copy: installs tests/session_safety.py first.) Run one test module (or explicit test ids) and emit per-test outcomes as JSON.

Usage: run_module.py OUT.json NAME [NAME ...]   (names are unittest dotted names)
Each test's id is exported as CBTI_GUARD_CURRENT_TEST so guard events are attributable.
"""
import importlib
import json
import os
import sys
import time
import traceback
import unittest
from pathlib import Path

root = Path.cwd()
# Step 9.63c-r5c10ak: the session-level hard guard is installed before any test module is imported,
# in addition to the guard (v3) loaded through PYTHONPATH. It is independent of the guard.
sys.path.insert(0, str(root / "tests"))
import session_safety  # noqa: E402
session_safety.install(str(root))
sys.path.insert(0, str(root / "tests"))
sys.path.insert(0, str(root))
out, names = sys.argv[1], sys.argv[2:]


class Recorder(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.rows = {}

    def startTest(self, test):
        os.environ["CBTI_GUARD_CURRENT_TEST"] = test.id()
        self.rows[test.id()] = {"outcome": "pass"}
        super().startTest(test)

    def _mark(self, test, outcome, err=None):
        row = self.rows.setdefault(test.id(), {})
        row["outcome"] = outcome
        if err is not None:
            row["detail"] = "".join(traceback.format_exception(*err))[-3000:]

    def addFailure(self, test, err):
        super().addFailure(test, err); self._mark(test, "fail", err)

    def addError(self, test, err):
        super().addError(test, err); self._mark(test, "error", err)

    def addSkip(self, test, reason):
        super().addSkip(test, reason); self.rows[test.id()] = {"outcome": "skip", "detail": reason}

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err); self._mark(test, "xfail", err)

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test); self._mark(test, "unexpected_success")


result = {"names": names, "import_errors": {}, "tests": {}}
loader = unittest.TestLoader()
suite = unittest.TestSuite()
for name in names:
    try:
        if "." in name:
            suite.addTests(loader.loadTestsFromName(name))
        else:
            suite.addTests(loader.loadTestsFromModule(importlib.import_module(name)))
    except BaseException as exc:
        result["import_errors"][name] = f"{type(exc).__name__}: {exc}"
started = time.time()
runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=1, resultclass=Recorder)
outcome = runner.run(suite)
os.environ.pop("CBTI_GUARD_CURRENT_TEST", None)
# Errors raised in setUpClass/setUpModule appear as _ErrorHolder entries.
for holder, err in outcome.errors:
    if holder.id() not in outcome.rows:
        result["tests"][holder.id()] = {"outcome": "error", "detail": err[-3000:]}
result["tests"].update(outcome.rows)
result["seconds"] = round(time.time() - started, 2)
json.dump(result, open(out, "w"), indent=1)
