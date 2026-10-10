import importlib.util, json, shutil, sys, tempfile
from pathlib import Path
H = Path("evaluation/v1_2_3/step9_63c_r5c10af_test_harness")
spec = importlib.util.spec_from_file_location("gns", H / "guard_negative_scenarios.py")
gns = importlib.util.module_from_spec(spec); sys.modules["gns"] = gns; spec.loader.exec_module(gns)
src = (H / "guard/sitecustomize.py").read_text()
M = [
 ("hardlink_rule_removed", "            elif mutating and not entry and _hardlinked_into_root(real):", "            elif False:", {"a3", "a4", "a5", "a6", "a7", "a8"}),
 ("hardlink_creation_from_repo_allowed", '"os.symlink": [(1, 2)], "os.link": [(0, 2), (1, 3)],', '"os.symlink": [(1, 2)], "os.link": [(1, 3)],', {"a1"}),
 ("hardlink_creation_into_repo_allowed", '"os.symlink": [(1, 2)], "os.link": [(0, 2), (1, 3)],', '"os.symlink": [(1, 2)], "os.link": [(0, 2)],', {"a2"}),
 ("rename_source_unchecked", '"os.rename": [(0, 2), (1, 3)],', '"os.rename": [(1, 3)],', {"b1", "b3", "b5", "b9", "b10"}),
 ("rename_target_unchecked", '"os.rename": [(0, 2), (1, 3)],', '"os.rename": [(0, 2)],', {"b2", "b4", "b6", "b11", "b12"}),
 ("shutil_move_source_unchecked", "                _check(event, [args[0]], args[0], entry=True, ancestors=True)\n            if len(args) > 1:", "                pass\n            if len(args) > 1:", {"b7"}),
 ("shutil_move_target_unchecked", "            if len(args) > 1:\n                _check(event, [args[1]], args[1])\n        elif event in _FIRST_ARG_EVENTS", "            if len(args) > 1:\n                pass\n        elif event in _FIRST_ARG_EVENTS", {"b8"}),
 ("abspath_in_final_resolution", "    return os.path.realpath(p)\n\n\ndef _under_root", "    return os.path.realpath(os.path.abspath(p))\n\n\ndef _under_root", {"c11"}),
 ("abspath_in_entry_parent", 'return os.path.join(os.path.realpath(os.path.dirname(p) or "."), base)', 'return os.path.join(os.path.realpath(os.path.abspath(os.path.dirname(p) or ".")), base)', {"c12"}),
 ("symlink_resolution_dropped", "    return os.path.realpath(p)\n\n\ndef _under_root", "    return os.path.abspath(p)\n\n\ndef _under_root", {"c4", "c5", "c6", "c7", "c8", "c9", "c16", "c20"}),
 ("entry_parent_symlink_not_resolved", 'return os.path.join(os.path.realpath(os.path.dirname(p) or "."), base)', 'return os.path.join(os.path.abspath(os.path.dirname(p) or "."), base)', {"b12", "c10"}),
 ("fd_operands_ignored", "    if isinstance(path, int):\n        try:\n            return _fd_dir(path)\n        except OSError:\n            return None  # pipe/socket/etc.: cannot name a repository file", "    if isinstance(path, int):\n        return None", {"d31", "d32", "d34"}),
 ("dir_fd_open_wrapper_removed", "    os.open = guarded_open\n", "", {"d45", "d46"}),
 ("mkfifo_wrapper_removed", '    for name in ("mkfifo", "mknod"):', '    for name in ():', {"d42", "d43", "d49"}),
 ("sqlite_unchecked", '        elif event == "sqlite3.connect":', '        elif event == "sqlite3.connect_DISABLED":', {"d44"}),
 ("case_alias_inode_walk_removed", "    candidate = real\n    while True:\n        try:\n            st = os.lstat(candidate)", "    return False\n    candidate = real\n    while True:\n        try:\n            st = os.lstat(candidate)", {"d52"}),
 ("ancestor_rule_removed", "            elif ancestors and _is_ancestor_of_root(real):", "            elif False:", {"d58", "d60"}),
 ("ancestor_case_alias_inode_walk_removed", "    try:\n        wanted = os.lstat(real)\n    except OSError:\n        return False\n    candidate = os.path.dirname(_ROOT)", "    return False\n    candidate = os.path.dirname(_ROOT)", {"d61"}),
 ("python_flag_check_removed", 'if char in "ISE":', 'if False:', {"e2", "e3", "e4", "e5", "e9", "e10"}),
 ("child_env_checks_both_removed", '    if merged.get("CBTI_GUARD_ROOT") != _ROOT:\n        return "child environment drops CBTI_GUARD_ROOT"\n    if _GUARD_DIR not in merged.get("PYTHONPATH", "").split(os.pathsep):\n        return "child environment drops the guard directory from PYTHONPATH"\n', '', {"e6", "e7", "e8"}),
 ("nonpython_subprocess_allowed", 'reason = None if _python_executable(executable) else "non-Python subprocess"', 'reason = None', {"e11", "e12"}),
 ("false_positive_symlink_entry_followed", "    if entry and base not in", "    if False and base not in", {"c1", "c2", "c3", "b14"}),
 ("write_open_unchecked", "            if writing:\n                _check(event, [path, mode, flags], path, mutating=True)", "            pass", {"d1", "d2", "d3", "d4", "d5", "d6", "d7", "d8", "d9", "d10", "d11", "d12"}),
]
results = []
for name, old, new, expected in M:
    assert src.count(old) == 1, (name, src.count(old))
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "sitecustomize.py").write_text(src.replace(old, new))
        rows = gns.run_catalogue(d, include_unguarded=False)
    failed = {r["id"]: r["verdict"] for r in rows if r["verdict"] not in ("PASS", "SKIPPED", "LIMIT_BYPASSED", "LIMIT_NOT_REPRODUCED")}
    prefixes = {i.split("_")[0] for i in failed}
    ok = bool(failed) and expected <= prefixes
    results.append({"mutant": name, "result": "KILLED" if failed else "SURVIVED", "expected_scenarios_flagged": sorted(expected),
                    "all_expected_flagged": expected <= prefixes, "flagged": sorted(failed.items())[:14], "flagged_count": len(failed)})
    print(f"{'KILLED  ' if ok else 'CHECK   '}{name:<40} flagged={len(failed):<3} missing={sorted(expected - prefixes)}")
print("KILLED", sum(r["result"] == "KILLED" for r in results), "of", len(results), "| all expected flagged:", all(r["all_expected_flagged"] for r in results))
Path(sys.argv[1]).write_text(json.dumps(results, indent=1))
