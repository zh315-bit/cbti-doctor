"""Mutation verification of tests/session_safety.py (Step 9.63c-r5c10ak). Writes nothing in the repository.

Each mutant is a copy of session_safety.py with one edit, written to a temporary directory; the
guard tests in tests/test_000_session_guard.py run their CHILD processes against that copy
(CBTI_SESSION_GUARD_SRC_DIR) on temporary fake repositories, so a broken mutant cannot reach the
real activation state. The parent process keeps the real guard installed.
usage: python session_guard_mutation.py OUT.json   (from the repository root)
"""
import json, os, sys, tempfile, unittest
from pathlib import Path

sys.path[:0] = ["tests"]
SRC = Path("tests/session_safety.py").read_text(encoding="utf-8")
MUTANTS = [
 ("M1_os_open_flags_ignored", "    return isinstance(flags, int) and bool(flags & _WRITE_FLAGS)", "    return False"),
 ("M2_append_mode_not_a_write", 'any(c in mode for c in "wax+")', 'any(c in mode for c in "wx+")'),
 ("M3_plus_mode_not_a_write", 'any(c in mode for c in "wax+")', 'any(c in mode for c in "wax")'),
 ("M4_symlinks_not_resolved", "    return os.path.realpath(p)", "    return os.path.abspath(p)"),
 ("M5_protected_dirs_ignored", "        if path == d or path.startswith(d + os.sep):\n            return True", "        if False:\n            return True"),
 ("M6_protected_files_ignored", "    if path in _PROTECTED_FILES:\n        return True", "    if False:\n        return True"),
 ("M7_ancestors_not_protected", "    if destructive:", "    if False:"),
 ("M8_violation_does_not_stop_the_session", "        os._exit(EXIT_CODE)", "        pass"),
 ("M9_replace_target_unchecked", '"os.replace": (0, 1)', '"os.replace": (0,)'),
 ("M10_copy_target_unchecked", '"shutil.copyfile": (1,)', '"shutil.copyfile": (0,)'),
 ("M11_hook_never_installed", "    sys.addaudithook(_hook)", "    pass"),
 ("M12_utime_unchecked", '"os.utime": (0,), ', ""),
 ("M13_open_event_ignored", '        if event == "open":', '        if event == "open-disabled":'),
 ("M14_r11_manifest_not_protected", '"step9_63c_r11_v3_authorization_manifest.json",\n', "\n"),
 ("M15_ledger_not_protected", '"authorization_lifecycle_events.jsonl", ', ""),
 ("M16_everything_blocked", "def protected(path: str | None, *, destructive: bool = False) -> bool:\n    if path is None:\n        return False",
  "def protected(path: str | None, *, destructive: bool = False) -> bool:\n    if path is not None:\n        return True"),
 ("M17_rename_source_unchecked", '"os.rename": (0, 1)', '"os.rename": (1,)'),
 ("M18_rmdir_unchecked", '"os.rmdir": (0,),', ""),
 ("M19_shutil_move_unchecked", '"shutil.move": (0, 1), ', ""),
 ("M21_entry_events_follow_symlinks", "        return os.path.join(os.path.realpath(os.path.dirname(p)), os.path.basename(p))", "        return os.path.realpath(p)"),
 ("M22_entry_parent_not_resolved", "        return os.path.join(os.path.realpath(os.path.dirname(p)), os.path.basename(p))", "        return p"),
 ("M23_dir_fd_ignored", "                        base = _fd_directory(dir_fd)\n", "                        base = None\n"),
 ("M24_dir_fd_relative_paths_not_checked", "                        if base is None:  # cannot tell where it points: do not guess against the cwd\n                            continue\n", "                        continue\n"),
 ("M20_mkdir_unchecked", '_PATH_EVENTS = {"os.mkdir": (0,), ', "_PATH_EVENTS = {"),
]
EQUIVALENT = {
 "M2_append_mode_not_a_write": "EQUIVALENT: builtin open() reports the computed os flags in its audit event, and O_APPEND is caught by the flags check",
 "M3_plus_mode_not_a_write": "EQUIVALENT: same reason (O_RDWR in the flags)",
 "M9_replace_target_unchecked": "EQUIVALENT: CPython's os.replace raises the audit event os.rename, whose two paths are both checked",
 "M10_copy_target_unchecked": "EQUIVALENT: shutil.copyfile opens the destination for writing, which the open check stops",
 "M19_shutil_move_unchecked": "EQUIVALENT: shutil.move raises os.rename (or opens the destination for writing), both checked",
}
import test_000_session_guard as guard_tests  # installs the REAL guard in this process
results = []
for label, old, new in MUTANTS:
    assert SRC.count(old) == 1, (label, SRC.count(old))
    with tempfile.TemporaryDirectory() as d:
        Path(d, "session_safety.py").write_text(SRC.replace(old, new), encoding="utf-8")
        os.environ["CBTI_SESSION_GUARD_SRC_DIR"] = d
        suite = unittest.defaultTestLoader.loadTestsFromNames(
            ["test_000_session_guard.BlockedWrites", "test_000_session_guard.AllowedAccess"])
        r = unittest.TextTestRunner(stream=open(os.devnull, "w"), failfast=True).run(suite)
        bad = r.failures + r.errors
        results.append({"mutant": label, "result": "KILLED" if bad else "SURVIVED", "killed_by": bad[0][0].id() if bad else None,
                        "note": EQUIVALENT.get(label, "")})
        print(results[-1]["result"], label, results[-1]["killed_by"] or "", flush=True)
    os.environ.pop("CBTI_SESSION_GUARD_SRC_DIR", None)
out = {"artifact_type": "R5C10AK_SESSION_GUARD_MUTATION_RESULTS", "total": len(results), "killed": sum(x["result"] == "KILLED" for x in results),
       "survived": [x["mutant"] for x in results if x["result"] == "SURVIVED"], "results": results}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1) + "\n")
print("KILLED", out["killed"], "of", out["total"])
