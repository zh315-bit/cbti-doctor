"""Step 9.63c-r5c10ak: the session-level hard guard.

Importing this module installs tests/session_safety.py for the whole test process (it sorts first,
so unittest discovery and the CI loader import it before any other test module). The tests below
exercise the guard in CHILD processes against a temporary fake repository, so a failing guard can
never touch the real activation state.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import session_safety

session_safety.install()

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent
LEDGER = "evaluation/v1_2_3/authorization_lifecycle_events.jsonl"
MANIFEST = "evaluation/v1_2_3/step9_63c_r11_v3_authorization_manifest.json"
FREEZE = "evaluation/v1_2_3/step9_63c_r11_runner_freeze.json"
LOCK = "evaluation/v4_runs/.namespace-allocation.lock"
JOURNALS = "evaluation/v4_runs/.execution_transactions"


def fake_repo() -> Path:
    root = Path(tempfile.mkdtemp(prefix="session-guard-")).resolve()
    (root / "evaluation/v4_runs/empty_ns").mkdir(parents=True)
    for rel, data in ((LEDGER, b'{"e":1}\n'), (MANIFEST, b"{}"), (FREEZE, b"{}"), (LOCK, b""), (JOURNALS + "/a.jsonl", b"{}\n"),
                      ("evaluation/v1_2_3/unprotected.json", b"{}"), ("scripts/x.py", b"")):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)
    return root


def digest(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "dir"
            for p in sorted(root.rglob("*"))}


def run_child(root: Path, body: str, *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run `body` in a child that installs the guard with `root` as the protected repository."""
    source_dir = os.environ.get("CBTI_SESSION_GUARD_SRC_DIR", str(TESTS))  # the mutation tool points this at a mutant
    code = "import os, shutil, sys\nsys.path.insert(0, %r)\nimport session_safety\nsession_safety.install(%r)\n" % (source_dir, str(root))
    code += textwrap.dedent(body) + "\nprint('SURVIVED')\n"
    # The environment is kept (the guard v3 refuses children with a scrubbed environment or -I); the
    # source directory is put first on sys.path explicitly, so the copy under test is the one imported.
    env = {k: v for k, v in os.environ.items() if k != "CBTI_SESSION_GUARD_INSTALLED"}
    return subprocess.run([sys.executable, "-c", code], cwd=cwd or root, env=env, capture_output=True, text=True, timeout=60)


class InstalledForThisSession(unittest.TestCase):
    def test_the_guard_is_installed_in_this_process_for_the_real_repository(self):
        self.assertEqual(os.environ.get("CBTI_SESSION_GUARD_INSTALLED"), str(os.getpid()))
        self.assertEqual(session_safety._ROOT, os.path.realpath(REPO))
        self.assertTrue(session_safety.protected(os.path.realpath(REPO / LEDGER)))
        self.assertTrue(session_safety.protected(os.path.realpath(REPO / LOCK)))
        self.assertTrue(session_safety.protected(os.path.realpath(REPO / MANIFEST)))
        self.assertFalse(session_safety.protected(os.path.realpath(REPO / "evaluation/v1_2_3/step9_51_v3_development_freeze_r1.json")))


class BlockedWrites(unittest.TestCase):
    CASES = {
        "append to the ledger": f"open({LEDGER!r}, 'a').write('x')",
        "rewrite the ledger": f"open({LEDGER!r}, 'w')",
        "read-write the ledger": f"open({LEDGER!r}, 'r+')",
        "os.open the lock with O_RDWR|O_CREAT": f"os.open({LOCK!r}, os.O_RDWR | os.O_CREAT)",
        "os.open the lock with O_WRONLY": f"os.open({LOCK!r}, os.O_WRONLY)",
        "create a namespace directory": "os.makedirs('evaluation/v4_runs/heldout-ns/eval', exist_ok=True)",
        "create a transaction journal": f"open({JOURNALS + '/auth-x.jsonl'!r}, 'x')",
        "append to a transaction journal": f"open({JOURNALS + '/a.jsonl'!r}, 'ab')",
        "overwrite the r11 manifest": f"open({MANIFEST!r}, 'wb')",
        "overwrite the Freeze": f"open({FREEZE!r}, 'w')",
        "remove the r11 manifest": f"os.remove({MANIFEST!r})",
        "rename the ledger away": f"os.rename({LEDGER!r}, 'evaluation/v1_2_3/moved.jsonl')",
        "replace the ledger with another file": f"os.replace('evaluation/v1_2_3/unprotected.json', {LEDGER!r})",
        "truncate the ledger": f"os.truncate({LEDGER!r}, 0)",
        "remove the whole evaluation tree (ancestor)": "shutil.rmtree('evaluation')",
        "rename an ancestor": "os.rename('evaluation/v1_2_3', 'evaluation/old')",
        "write through an absolute path": f"open(os.path.abspath({LEDGER!r}), 'a')",
        "write through a symlink alias": f"os.symlink(os.path.abspath('evaluation/v4_runs'), '/tmp/alias-' + str(os.getpid())); open('/tmp/alias-' + str(os.getpid()) + '/new', 'w')",
        "touch the lock (utime)": f"os.utime({LOCK!r})",
        "chmod the manifest": f"os.chmod({MANIFEST!r}, 0o600)",
        "copy onto the Freeze": f"shutil.copyfile('evaluation/v1_2_3/unprotected.json', {FREEZE!r})",
        "move into v4_runs": "shutil.move('evaluation/v1_2_3/unprotected.json', 'evaluation/v4_runs/moved.json')",
        "remove an empty namespace directory": "os.rmdir('evaluation/v4_runs/empty_ns')",
        "remove the ledger relative to a directory file descriptor": f"fd = os.open('evaluation/v1_2_3', os.O_RDONLY); os.remove('authorization_lifecycle_events.jsonl', dir_fd=fd)",
        "unlink the real ledger even when reached through a symlinked directory": "os.symlink(os.path.abspath('evaluation/v1_2_3'), '/tmp/v123-' + str(os.getpid())); os.remove('/tmp/v123-' + str(os.getpid()) + '/authorization_lifecycle_events.jsonl')",
    }

    def test_every_write_capable_access_stops_the_session_and_changes_nothing(self):
        for label, body in self.CASES.items():
            with self.subTest(case=label):
                root = fake_repo()
                before = digest(root)
                result = run_child(root, body)
                self.assertEqual(result.returncode, session_safety.EXIT_CODE, (label, result.stdout, result.stderr[-400:]))
                self.assertNotIn("SURVIVED", result.stdout)
                self.assertIn("SESSION GUARD", result.stderr)
                self.assertEqual(digest(root), before, label)

    def test_a_relative_path_from_another_working_directory_is_resolved(self):
        root = fake_repo()
        before = digest(root)
        result = run_child(root, "open('../evaluation/v1_2_3/authorization_lifecycle_events.jsonl', 'a')", cwd=root / "scripts")
        self.assertEqual(result.returncode, session_safety.EXIT_CODE)
        self.assertEqual(digest(root), before)


class AllowedAccess(unittest.TestCase):
    def test_reads_and_unprotected_writes_are_allowed(self):
        root = fake_repo()
        body = f"""
        open({LEDGER!r}).read(); open({MANIFEST!r}, 'rb').read(); os.listdir('evaluation/v4_runs')
        fd = os.open({LOCK!r}, os.O_RDONLY); os.close(fd)
        open('evaluation/v1_2_3/unprotected.json', 'w').write('[]')
        os.makedirs('evaluation/other_runs/x', exist_ok=True)
        open('/tmp/session-guard-ok-' + str(os.getpid()), 'w').write('ok')
        """
        result = run_child(root, body)
        self.assertEqual(result.returncode, 0, result.stderr[-500:])
        self.assertIn("SURVIVED", result.stdout)

    def test_removing_a_temporary_symlink_that_points_at_a_protected_file_is_allowed(self):
        # e.g. a temporary mirror whose entries are symlinks to the real files is cleaned up afterwards
        root = fake_repo()
        body = f"""
        import tempfile
        d = tempfile.mkdtemp()
        os.symlink(os.path.abspath({LEDGER!r}), d + '/ledger'); os.remove(d + '/ledger')
        os.symlink(os.path.abspath('evaluation/v4_runs'), d + '/runs'); os.remove(d + '/runs')
        os.symlink(os.path.abspath({MANIFEST!r}), d + '/m'); shutil.rmtree(d)
        """
        before = digest(root)
        result = run_child(root, body)
        self.assertEqual(result.returncode, 0, result.stderr[-500:])
        self.assertEqual(digest(root), before)

    def test_removing_a_temporary_tree_with_the_same_relative_names_is_allowed(self):
        # shutil.rmtree removes entries relative to a directory file descriptor; with the working directory
        # at the repository root, "evaluation" must not be mistaken for the real evaluation directory.
        root = fake_repo()
        body = """
        import tempfile
        d = tempfile.mkdtemp()
        os.makedirs(d + '/evaluation/v1_2_3'); os.makedirs(d + '/evaluation/v4_runs/x')
        open(d + '/evaluation/v1_2_3/authorization_lifecycle_events.jsonl', 'w').write('{}')
        shutil.rmtree(d)
        """
        before = digest(root)
        result = run_child(root, body)
        self.assertEqual(result.returncode, 0, result.stderr[-500:])
        self.assertEqual(digest(root), before)

    def test_a_temporary_root_with_the_same_layout_is_not_protected(self):
        root, other = fake_repo(), fake_repo()
        result = run_child(root, f"open({str(other / LEDGER)!r}, 'a').write('x')")
        self.assertEqual(result.returncode, 0, result.stderr[-400:])

    def test_install_is_idempotent_within_one_process(self):
        root = fake_repo()
        result = run_child(root, "session_safety.install(); session_safety.install(); print(len([1]))")
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
