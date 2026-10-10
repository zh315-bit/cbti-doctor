#!/usr/bin/env python3
"""Negative-scenario catalogue for the test side-effect guard (Step 9.63c-r5c10af).

Every scenario runs in its own subprocess against a FRESH temporary tree that plays the
protected repository ("Repo") next to an unprotected "out" directory. The real
repository is never a target. For each scenario the same action is first run with no
guard at all to prove it really changes something (an ineffective scenario would make
"blocked" meaningless), then with the guard under test.

expect = BLOCK  guard must raise its PermissionError and nothing may change in Repo or out
         ALLOW  action must complete, the guard must stay silent, Repo must be unchanged
         SAFE   Repo must be unchanged (guard block or OS refusal are both acceptable)
         LIMIT  documented non-blockable path; reported, never asserted

CLI: guard_negative_scenarios.py --guard-dir DIR [--name LABEL] [--out FILE.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

MARKER = "@@RESULT@@"


@dataclass(frozen=True)
class Scenario:
    id: str
    group: str
    expect: str
    code: str
    note: str = ""
    needs_case_insensitive: bool = False


PRELUDE = r'''
import json, os, sys, shutil, io, subprocess, pathlib, sqlite3
from pathlib import Path
ROOT = {root!r}
OUT = {out!r}
ALT = {alt!r}
VICTIM = ROOT + "/victim.txt"
'''

TAIL = r'''
result = {{"outcome": "ALLOWED"}}
try:
    exec(compile(ACTION, "<scenario>", "exec"), globals())
except BaseException as error:  # noqa: BLE001 - classify everything
    text = repr(error)
    result = {{"outcome": "BLOCKED" if "CBTI guard" in text else "OS_ERROR", "error": text[:300]}}
print({marker!r} + json.dumps(result))
'''


def S(id, group, expect, code, note="", ci=False):
    return Scenario(id, group, expect, code.strip("\n"), note, ci)


SCENARIOS = [
    # ---- a: hard links -----------------------------------------------------------------
    S("a1_link_from_repo_file", "a", "BLOCK", "os.link(VICTIM, OUT + '/new_hl')", "never create a link whose source is a repository file"),
    S("a2_link_into_repo", "a", "BLOCK", "os.link(OUT + '/plain.txt', ROOT + '/new_hl')"),
    S("a3_write_via_existing_hardlink", "a", "BLOCK", "open(OUT + '/hl', 'w').write('PWNED')", "hard link created before the guard existed"),
    S("a4_append_via_existing_hardlink", "a", "BLOCK", "fd = os.open(OUT + '/hl', os.O_WRONLY | os.O_APPEND); os.write(fd, b'PWNED')"),
    S("a5_truncate_via_existing_hardlink", "a", "BLOCK", "os.truncate(OUT + '/hl', 0)"),
    S("a6_chmod_via_existing_hardlink", "a", "BLOCK", "os.chmod(OUT + '/hl', 0o000)", "metadata of a shared inode"),
    S("a7_utime_via_existing_hardlink", "a", "BLOCK", "os.utime(OUT + '/hl', (1, 1))"),
    S("a8_pathlib_write_via_existing_hardlink", "a", "BLOCK", "Path(OUT + '/hl').write_text('PWNED')"),
    S("a9_unlink_the_hardlink_name_itself", "a", "ALLOW", "os.remove(OUT + '/hl')", "removing an outside name leaves the repository file intact"),
    S("a10_write_unrelated_multilink_file", "a", "ALLOW", "open(OUT + '/plain.txt', 'w').write('fine')", "plain.txt has a second name, but both names are outside"),
    # ---- b: rename / replace with either end in the repository -------------------------
    S("b1_rename_source_in_repo", "b", "BLOCK", "os.rename(VICTIM, OUT + '/moved')"),
    S("b2_rename_target_in_repo", "b", "BLOCK", "os.rename(OUT + '/plain.txt', VICTIM)"),
    S("b3_replace_source_in_repo", "b", "BLOCK", "os.replace(VICTIM, OUT + '/moved')"),
    S("b4_replace_target_in_repo", "b", "BLOCK", "os.replace(OUT + '/plain.txt', VICTIM)"),
    S("b5_pathlib_rename_source_in_repo", "b", "BLOCK", "Path(VICTIM).rename(OUT + '/moved')"),
    S("b6_pathlib_replace_target_in_repo", "b", "BLOCK", "Path(OUT + '/plain.txt').replace(VICTIM)"),
    S("b7_shutil_move_source_in_repo", "b", "BLOCK", "shutil.move(VICTIM, OUT + '/moved')"),
    S("b8_shutil_move_target_in_repo", "b", "BLOCK", "shutil.move(OUT + '/plain.txt', ROOT + '/moved_in')"),
    S("b9_rename_directory_in_repo", "b", "BLOCK", "os.rename(ROOT + '/emptydir', OUT + '/moved_dir')"),
    S("b10_rename_source_dir_fd_in_repo", "b", "BLOCK", "fd = os.open(ROOT, os.O_RDONLY); os.rename('victim.txt', OUT + '/moved', src_dir_fd=fd)"),
    S("b11_rename_target_dir_fd_in_repo", "b", "BLOCK", "fd = os.open(ROOT, os.O_RDONLY); os.rename(OUT + '/plain.txt', 'victim.txt', dst_dir_fd=fd)"),
    S("b12_rename_into_repo_via_symlinked_dir", "b", "BLOCK", "os.rename(OUT + '/plain.txt', OUT + '/lnk_dir/moved_in')"),
    S("b13_rename_outside_to_outside", "b", "ALLOW", "os.rename(OUT + '/plain.txt', OUT + '/renamed.txt')"),
    S("b14_rename_the_symlink_itself", "b", "ALLOW", "os.rename(OUT + '/lnk_file', OUT + '/lnk_renamed')", "moves the link, not its target"),
    # ---- c: symlinks -----------------------------------------------------------------------
    S("c1_remove_symlink_itself", "c", "ALLOW", "os.remove(OUT + '/lnk_file')", "deleting the link is allowed"),
    S("c2_unlink_symlink_itself", "c", "ALLOW", "os.unlink(OUT + '/lnk_file')"),
    S("c3_pathlib_unlink_symlink_itself", "c", "ALLOW", "Path(OUT + '/lnk_file').unlink()"),
    S("c4_write_through_symlink", "c", "BLOCK", "open(OUT + '/lnk_file', 'w').write('PWNED')"),
    S("c5_os_open_through_symlink", "c", "BLOCK", "os.close(os.open(OUT + '/lnk_file', os.O_WRONLY | os.O_TRUNC))"),
    S("c6_write_text_through_symlink", "c", "BLOCK", "Path(OUT + '/lnk_file').write_text('PWNED')"),
    S("c7_copy_onto_symlink", "c", "BLOCK", "shutil.copy(OUT + '/plain.txt', OUT + '/lnk_file')"),
    S("c8_new_file_through_symlinked_dir", "c", "BLOCK", "open(OUT + '/lnk_dir/created.txt', 'w').write('PWNED')"),
    S("c9_overwrite_through_symlinked_dir", "c", "BLOCK", "open(OUT + '/lnk_dir/inner.txt', 'w').write('PWNED')"),
    S("c10_delete_through_symlinked_dir", "c", "BLOCK", "os.remove(OUT + '/lnk_dir/inner.txt')"),
    S("c11_dotdot_after_symlink_write", "c", "BLOCK", "open(OUT + '/lnk_dir/../victim.txt', 'w').write('PWNED')", "'..' after a symlink leaves the link's target, not the link's parent"),
    S("c12_dotdot_after_symlink_remove", "c", "BLOCK", "os.remove(OUT + '/lnk_dir/../victim.txt')"),
    S("c13_trailing_slash_rmdir_through_symlink", "c", "BLOCK", "os.rmdir(OUT + '/lnk_empty/')", "a trailing slash makes the OS follow the final symlink"),
    S("c14_trailing_slash_rmtree_through_symlink", "c", "SAFE", "shutil.rmtree(OUT + '/lnk_dir/')"),
    S("c15_rmtree_symlink_without_slash", "c", "SAFE", "shutil.rmtree(OUT + '/lnk_dir')", "the standard library itself refuses a symlink here, so there is nothing to block"),
    S("c16_relative_symlink_write", "c", "BLOCK", "open(OUT + '/lnk_rel', 'w').write('PWNED')", "relative link ../Repo/victim.txt"),
    S("c17_create_symlink_inside_repo", "c", "BLOCK", "os.symlink('/nonexistent', ROOT + '/new_link')"),
    S("c18_create_symlink_pointing_into_repo", "c", "ALLOW", "os.symlink(VICTIM, OUT + '/another_link')", "creating a link is harmless; writing through it is blocked (c4)"),
    S("c19_read_through_symlink", "c", "ALLOW", "assert open(OUT + '/lnk_file').read() == 'ORIGINAL'"),
    S("c20_chmod_through_symlink", "c", "BLOCK", "os.chmod(OUT + '/lnk_file', 0o000)"),
    # ---- d: every write entry point against the repository --------------------------------
    S("d1_open_w", "d", "BLOCK", "open(VICTIM, 'w').write('PWNED')"),
    S("d2_open_a", "d", "BLOCK", "open(VICTIM, 'a').write('PWNED')"),
    S("d3_open_x_new", "d", "BLOCK", "open(ROOT + '/brand_new.txt', 'x').write('PWNED')"),
    S("d4_open_r_plus", "d", "BLOCK", "open(VICTIM, 'r+').write('PWNED')"),
    S("d5_open_wb", "d", "BLOCK", "open(VICTIM, 'wb').write(b'PWNED')"),
    S("d6_io_open_w", "d", "BLOCK", "io.open(VICTIM, 'w').write('PWNED')"),
    S("d7_os_open_wronly", "d", "BLOCK", "fd = os.open(VICTIM, os.O_WRONLY); os.write(fd, b'PWNED'); os.close(fd)"),
    S("d8_os_open_creat", "d", "BLOCK", "os.close(os.open(ROOT + '/created', os.O_CREAT | os.O_WRONLY, 0o644))"),
    S("d9_os_open_rdwr", "d", "BLOCK", "fd = os.open(VICTIM, os.O_RDWR); os.write(fd, b'PWNED'); os.close(fd)"),
    S("d10_os_open_trunc", "d", "BLOCK", "os.close(os.open(VICTIM, os.O_WRONLY | os.O_TRUNC))"),
    S("d11_os_open_append", "d", "BLOCK", "fd = os.open(VICTIM, os.O_WRONLY | os.O_APPEND); os.write(fd, b'PWNED'); os.close(fd)"),
    S("d12_os_open_excl", "d", "BLOCK", "os.close(os.open(ROOT + '/excl', os.O_CREAT | os.O_EXCL | os.O_WRONLY))"),
    S("d13_shutil_copy", "d", "BLOCK", "shutil.copy(OUT + '/plain.txt', VICTIM)"),
    S("d14_shutil_copyfile", "d", "BLOCK", "shutil.copyfile(OUT + '/plain.txt', VICTIM)"),
    S("d15_shutil_copy2", "d", "BLOCK", "shutil.copy2(OUT + '/plain.txt', VICTIM)"),
    S("d16_shutil_copy_into_repo_dir", "d", "BLOCK", "shutil.copy(OUT + '/plain.txt', ROOT)"),
    S("d17_shutil_copyfileobj", "d", "BLOCK", "shutil.copyfileobj(io.BytesIO(b'PWNED'), open(VICTIM, 'wb'))"),
    S("d18_shutil_copytree", "d", "BLOCK", "shutil.copytree(OUT + '/tree', ROOT + '/tree_copy')"),
    S("d19_shutil_copymode", "d", "BLOCK", "shutil.copymode(OUT + '/mode_src', VICTIM)"),
    S("d20_shutil_copystat", "d", "BLOCK", "shutil.copystat(OUT + '/stat_src', VICTIM)"),
    S("d21_pathlib_write_text", "d", "BLOCK", "Path(VICTIM).write_text('PWNED')"),
    S("d22_pathlib_write_bytes", "d", "BLOCK", "Path(VICTIM).write_bytes(b'PWNED')"),
    S("d23_pathlib_open_w", "d", "BLOCK", "Path(VICTIM).open('w').write('PWNED')"),
    S("d24_pathlib_touch_new", "d", "BLOCK", "Path(ROOT + '/touched').touch()"),
    S("d25_pathlib_touch_existing", "d", "BLOCK", "Path(VICTIM).touch()", "updates mtime"),
    S("d26_pathlib_mkdir", "d", "BLOCK", "Path(ROOT + '/newdir').mkdir()"),
    S("d27_os_makedirs", "d", "BLOCK", "os.makedirs(ROOT + '/a/b/c')"),
    S("d28_os_mkdir", "d", "BLOCK", "os.mkdir(ROOT + '/newdir')"),
    S("d29_os_truncate_path", "d", "BLOCK", "os.truncate(VICTIM, 0)"),
    S("d30_os_chmod_path", "d", "BLOCK", "os.chmod(VICTIM, 0o000)"),
    S("d31_os_chmod_fd", "d", "BLOCK", "fd = os.open(VICTIM, os.O_RDONLY); os.chmod(fd, 0o000)", "descriptor opened read-only is still a handle on a repository file"),
    S("d32_os_fchmod_fd", "d", "BLOCK", "fd = os.open(VICTIM, os.O_RDONLY); os.fchmod(fd, 0o000)"),
    S("d33_os_utime_path", "d", "BLOCK", "os.utime(VICTIM, (1, 1))"),
    S("d34_os_utime_fd", "d", "BLOCK", "fd = os.open(VICTIM, os.O_RDONLY); os.utime(fd, (1, 1))"),
    S("d35_os_chown_path", "d", "BLOCK", "gids = [g for g in os.getgroups() if g != os.stat(VICTIM).st_gid]; os.chown(VICTIM, -1, gids[0])"),
    S("d36_os_remove", "d", "BLOCK", "os.remove(VICTIM)"),
    S("d37_os_unlink", "d", "BLOCK", "os.unlink(VICTIM)"),
    S("d38_pathlib_unlink", "d", "BLOCK", "Path(VICTIM).unlink()"),
    S("d39_os_rmdir", "d", "BLOCK", "os.rmdir(ROOT + '/emptydir')"),
    S("d40_shutil_rmtree", "d", "BLOCK", "shutil.rmtree(ROOT + '/sub')"),
    S("d41_os_symlink_dst_in_repo", "d", "BLOCK", "os.symlink(OUT + '/plain.txt', ROOT + '/lnk')"),
    S("d42_os_mkfifo", "d", "BLOCK", "os.mkfifo(ROOT + '/fifo')", "raises no audit event of its own"),
    S("d43_os_mknod_fifo", "d", "BLOCK", "import stat; os.mknod(ROOT + '/node', stat.S_IFIFO | 0o600)", "raises no audit event of its own"),
    S("d44_sqlite3_connect_write", "d", "BLOCK", "c = sqlite3.connect(ROOT + '/new.db'); c.execute('create table t(x)'); c.commit()"),
    S("d45_dir_fd_open_create", "d", "BLOCK", "fd = os.open(ROOT, os.O_RDONLY); os.close(os.open('via_dirfd', os.O_WRONLY | os.O_CREAT, 0o644, dir_fd=fd))", "audit event omits dir_fd"),
    S("d46_dir_fd_open_overwrite", "d", "BLOCK", "fd = os.open(ROOT, os.O_RDONLY); os.close(os.open('victim.txt', os.O_WRONLY | os.O_TRUNC, dir_fd=fd))"),
    S("d47_dir_fd_mkdir", "d", "BLOCK", "fd = os.open(ROOT, os.O_RDONLY); os.mkdir('via_dirfd_dir', dir_fd=fd)"),
    S("d48_dir_fd_unlink", "d", "BLOCK", "fd = os.open(ROOT, os.O_RDONLY); os.unlink('victim.txt', dir_fd=fd)"),
    S("d49_dir_fd_mkfifo", "d", "BLOCK", "fd = os.open(ROOT, os.O_RDONLY); os.mkfifo('via_dirfd_fifo', dir_fd=fd)"),
    S("d50_relative_path_after_chdir", "d", "BLOCK", "os.chdir(ROOT); open('victim.txt', 'w').write('PWNED')"),
    S("d51_dotdot_relative_from_out", "d", "BLOCK", "open('../Repo/victim.txt', 'w').write('PWNED')"),
    S("d52_case_variant_of_root", "d", "BLOCK", "open(ALT + '/victim.txt', 'w').write('PWNED')", "case-insensitive filesystem alias of the root", True),
    S("d53_tempfile_inside_repo", "d", "BLOCK", "import tempfile; tempfile.NamedTemporaryFile(dir=ROOT, delete=False)"),
    S("d54_logging_file_handler", "d", "BLOCK", "import logging; logging.FileHandler(ROOT + '/x.log')"),
    S("d58_rename_ancestor_of_repo", "d", "BLOCK", "os.rename(os.path.dirname(ROOT), os.path.dirname(ROOT) + '_x')", "moves the whole repository in one call"),
    S("d59_rmtree_ancestor_of_repo", "d", "SAFE", "shutil.rmtree(os.path.dirname(ROOT))", "must never delete the repository; unprotected siblings may be removed"),
    S("d60_chmod_ancestor_of_repo", "d", "BLOCK", "os.chmod(os.path.dirname(ROOT), 0o000)", "locks the repository out"),
    S("d61_rmdir_ancestor_alias_case", "d", "BLOCK", "os.rename(os.path.dirname(ROOT).rsplit('/', 1)[0] + '/' + os.path.basename(os.path.dirname(ROOT)).swapcase(), os.path.dirname(ROOT) + '_y')", "case-variant alias of the ancestor", True),
    S("d55_read_repo_file", "d", "ALLOW", "assert open(VICTIM).read() == 'ORIGINAL'; assert os.listdir(ROOT); os.stat(VICTIM)"),
    S("d56_write_outside", "d", "ALLOW", "open(OUT + '/new.txt', 'w').write('ok'); shutil.copy(VICTIM, OUT + '/copy_of_victim'); os.makedirs(OUT + '/x/y')", "copying FROM the repo is a read"),
    S("d57_delete_outside_tree", "d", "ALLOW", "shutil.rmtree(OUT + '/tree'); os.remove(OUT + '/plain.txt')"),
    # ---- e: child processes ------------------------------------------------------------------
    S("e1_child_python_inherits_guard", "e", "BLOCK", "r = subprocess.run([sys.executable, '-c', 'open(' + repr(VICTIM) + ', \"w\").write(\"PWNED\")'], capture_output=True, text=True); assert 'CBTI guard' in r.stderr, r.stderr[-300:]; raise PermissionError('CBTI guard (child blocked)')", "control: child inherits the guard through PYTHONPATH"),
    S("e2_child_isolated_flag", "e", "BLOCK", "subprocess.run([sys.executable, '-I', '-c', 'open(' + repr(VICTIM) + ', \"w\").write(\"PWNED\")'], check=True)", "-I ignores PYTHONPATH, so the child would run unguarded"),
    S("e3_child_no_site_flag", "e", "BLOCK", "subprocess.run([sys.executable, '-S', '-c', 'open(' + repr(VICTIM) + ', \"w\").write(\"PWNED\")'], check=True)", "-S skips sitecustomize"),
    S("e4_child_ignore_env_flag", "e", "BLOCK", "subprocess.run([sys.executable, '-E', '-c', 'open(' + repr(VICTIM) + ', \"w\").write(\"PWNED\")'], check=True)"),
    S("e5_child_clustered_flags", "e", "BLOCK", "subprocess.run([sys.executable, '-Ic', 'open(' + repr(VICTIM) + ', \"w\").write(\"PWNED\")'], check=True)"),
    S("e6_child_scrubbed_environment", "e", "BLOCK", "subprocess.run([sys.executable, '-c', 'open(' + repr(VICTIM) + ', \"w\").write(\"PWNED\")'], env={}, check=True)"),
    S("e7_child_environment_without_guard_path", "e", "BLOCK", "env = dict(os.environ); env.pop('PYTHONPATH', None); subprocess.run([sys.executable, '-c', 'open(' + repr(VICTIM) + ', \"w\").write(\"PWNED\")'], env=env, check=True)"),
    S("e8_parent_environ_mutated_then_inherit", "e", "BLOCK", "os.environ.pop('PYTHONPATH', None); subprocess.run([sys.executable, '-c', 'open(' + repr(VICTIM) + ', \"w\").write(\"PWNED\")'], check=True)"),
    S("e9_exec_isolated_python", "e", "BLOCK", "os.execv(sys.executable, [sys.executable, '-I', '-c', 'open(' + repr(VICTIM) + ', \"w\").write(\"PWNED\")'])"),
    S("e10_posix_spawn_isolated_python", "e", "BLOCK", "pid = os.posix_spawn(sys.executable, [sys.executable, '-I', '-c', 'open(' + repr(VICTIM) + ', \"w\").write(\"PWNED\")'], os.environ); os.waitpid(pid, 0)"),
    S("e11_shell_subprocess", "e", "BLOCK", "subprocess.run('echo PWNED > ' + VICTIM, shell=True, check=True)"),
    S("e12_non_python_binary", "e", "BLOCK", "subprocess.run(['/bin/cp', OUT + '/plain.txt', VICTIM], check=True)"),
    S("e13_child_python_writes_outside", "e", "ALLOW", "env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}; subprocess.run([sys.executable, '-c', 'open(' + repr(OUT + '/from_child') + ', \"w\").write(\"ok\")'], env=env, check=True)", "control: ordinary child with a copied environment is fine"),
    # ---- f: documented limits (reported, never asserted) ---------------------------------------
    S("f1_ctypes_libc_write", "f", "LIMIT", "import ctypes; libc = ctypes.CDLL(None); fd = libc.open(VICTIM.encode(), os.O_WRONLY | os.O_TRUNC); libc.write(fd, b'PWNED', 5); libc.close(fd)", "direct libc syscalls never reach the audit hook"),
]


def build_tree(base: Path) -> tuple[Path, Path]:
    root = base / "Repo"
    out = base / "out"
    for directory in (root / "sub", root / "emptydir", out / "tree" / "deep"):
        directory.mkdir(parents=True)
    (root / "victim.txt").write_text("ORIGINAL")
    (root / "sub" / "inner.txt").write_text("INNER")
    (out / "plain.txt").write_text("PLAIN")
    (out / "tree" / "deep" / "f.txt").write_text("T")
    (out / "mode_src").write_text("M"); os.chmod(out / "mode_src", 0o755)
    (out / "stat_src").write_text("T"); os.utime(out / "stat_src", (1, 1))
    os.link(out / "plain.txt", out / "plain_second_name")        # unrelated multi-link file
    (root / "hl_target.txt").write_text("HLTARGET")
    os.link(root / "hl_target.txt", out / "hl")                    # hard link INTO the repository (victim.txt keeps one link)
    os.symlink(root / "victim.txt", out / "lnk_file")
    os.symlink(root / "sub", out / "lnk_dir")
    os.symlink(root / "emptydir", out / "lnk_empty")
    os.symlink("../Repo/victim.txt", out / "lnk_rel")
    return root, out


def digest_tree(top: Path) -> dict:
    rows = {}
    try:
        entries = sorted(top.rglob("*"))
        rows["."] = ("root", top.lstat().st_mode, top.parent.lstat().st_mode)
    except OSError:
        return {"__unreadable_or_missing__": True}
    for path in entries:
        rel = path.relative_to(top).as_posix()
        info = path.lstat()
        if path.is_symlink():
            rows[rel] = ("link", os.readlink(path))
        elif path.is_dir():
            rows[rel] = ("dir", info.st_mode)
        elif path.is_file():
            try:
                content = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:  # e.g. mode 000 after an (unguarded) chmod: the mode already differs
                content = "UNREADABLE"
            rows[rel] = ("file", info.st_mode, info.st_size, info.st_mtime_ns, info.st_gid, content)
        else:
            rows[rel] = ("other", info.st_mode)
    return rows


def _clean_env(extra: dict | None = None) -> dict:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("CBTI_") and k not in ("PYTHONPATH", "PYTHONHOME")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(extra or {})
    return env


def run_once(scenario: Scenario, guard_dir: str | None, python: str) -> dict:
    base = Path(tempfile.mkdtemp(prefix="guardneg-")).resolve()
    try:
        root, out = build_tree(base)
        alt = base / root.name.swapcase()
        if scenario.needs_case_insensitive and not (alt.exists() and Path(str(base).swapcase()).exists()):
            return {"skipped": "filesystem is case-sensitive"}
        before_repo, before_out = digest_tree(root), digest_tree(out)
        logdir = Path(tempfile.mkdtemp(prefix="guardneg-log-")).resolve()  # outside base: scenarios may move base
        log = logdir / "guard.jsonl"
        script = (PRELUDE.format(root=str(root), out=str(out), alt=str(alt))
                  + f"ACTION = {scenario.code!r}\n" + TAIL.format(marker=MARKER))
        extra = {}
        if guard_dir:
            extra = {"CBTI_GUARD_ROOT": str(root), "CBTI_GUARD_LOG": str(log), "PYTHONPATH": guard_dir}
        process = subprocess.run([python, "-c", script], env=_clean_env(extra), cwd=out,
                                 capture_output=True, text=True, timeout=120)
        line = next((l for l in process.stdout.splitlines() if l.startswith(MARKER)), None)
        result = json.loads(line[len(MARKER):]) if line else {"outcome": "NO_RESULT", "stderr": process.stderr[-300:]}
        blocked_events = 0
        if log.exists():
            blocked_events = sum(1 for l in log.read_text().splitlines() if l and json.loads(l).get("blocked"))
        # Descendant processes (e.g. a child Python) log to the same file.
        result.update(repo_changed=digest_tree(root) != before_repo, out_changed=digest_tree(out) != before_out,
                      guard_blocked_events=blocked_events)
        return result
    finally:
        for leftover in (base, Path(str(base) + "_x"), Path(str(base) + "_y")):
            try:
                os.chmod(leftover, 0o755)
            except OSError:
                pass
            shutil.rmtree(leftover, ignore_errors=True)
        shutil.rmtree(locals().get("logdir", base), ignore_errors=True) if "logdir" in locals() else None


def verdict(scenario: Scenario, guarded: dict, unguarded: dict) -> str:
    if guarded.get("skipped"):
        return "SKIPPED"
    if scenario.expect == "LIMIT":
        return "LIMIT_BYPASSED" if guarded["repo_changed"] else "LIMIT_NOT_REPRODUCED"
    blocked = guarded["outcome"] == "BLOCKED" or guarded["guard_blocked_events"] > 0
    if scenario.expect == "BLOCK":
        if guarded["repo_changed"] or guarded["out_changed"]:
            return "BYPASS"
        return "PASS" if blocked else "NOT_BLOCKED"
    if scenario.expect == "SAFE":
        return "BYPASS" if guarded["repo_changed"] else "PASS"
    # ALLOW
    if guarded["repo_changed"]:
        return "BYPASS"
    return "PASS" if (guarded["outcome"] == "ALLOWED" and not blocked) else "FALSE_POSITIVE"


def effective(scenario: Scenario, unguarded: dict) -> bool:
    """Without any guard the scenario must change the tree (or run to completion for ALLOW)."""
    if unguarded.get("skipped"):
        return True
    if scenario.expect in ("BLOCK", "SAFE", "LIMIT"):
        return bool(unguarded["repo_changed"] or unguarded["out_changed"])
    return unguarded["outcome"] == "ALLOWED"


def run_catalogue(guard_dir: str | None, python: str = sys.executable, include_unguarded: bool = True) -> list[dict]:
    rows = []
    for scenario in SCENARIOS:
        unguarded = run_once(scenario, None, python) if include_unguarded else {}
        guarded = run_once(scenario, guard_dir, python) if guard_dir else {}
        rows.append({"id": scenario.id, "group": scenario.group, "expect": scenario.expect, "note": scenario.note,
                     "scenario_effective_without_guard": effective(scenario, unguarded) if include_unguarded else None,
                     "unguarded": unguarded, "guarded": guarded,
                     "verdict": verdict(scenario, guarded, unguarded) if guard_dir else None})
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guard-dir", required=True)
    parser.add_argument("--name", default="guard")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    rows = run_catalogue(str(Path(args.guard_dir).resolve()))
    counts: dict = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    report = {"guard": args.name, "guard_dir": args.guard_dir, "scenarios": len(rows), "verdicts": counts,
              "guard_sitecustomize_sha256": hashlib.sha256((Path(args.guard_dir) / "sitecustomize.py").read_bytes()).hexdigest(),
              "scenario_catalogue_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "ineffective_scenarios": [r["id"] for r in rows if not r["scenario_effective_without_guard"]],
              "failures": [{"id": r["id"], "verdict": r["verdict"], "guarded": r["guarded"]} for r in rows
                           if r["verdict"] not in ("PASS", "SKIPPED", "LIMIT_BYPASSED", "LIMIT_NOT_REPRODUCED")],
              "rows": rows}
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=1, default=str) + "\n")
    print(json.dumps({k: report[k] for k in ("guard", "scenarios", "verdicts", "ineffective_scenarios")}, indent=1))
    for failure in report["failures"]:
        print(f"  {failure['verdict']:<15} {failure['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
