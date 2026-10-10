"""Session-level hard stop for test runs (Step 9.63c-r5c10ak). Independent of the guard (v3).

Once installed, any write-capable access by the test process to the REAL activation state ends the
whole test session immediately (os._exit), so nothing is half-written and the run fails loudly:

  * evaluation/v4_runs/ and everything below it (namespaces, attempts, the transaction journals in
    .execution_transactions, the namespace-allocation lock)
  * the lifecycle ledger evaluation/v1_2_3/authorization_lifecycle_events.jsonl
  * the r11 authorization manifest, Freeze, identity pointer, pointer creation record and approval record

Write-capable means: open/os.open with a write, append, create or truncate mode or flag; mkdir,
rename/replace (either end), remove/unlink, rmdir, truncate, rmtree, link/symlink, chmod, utime,
shutil.move/copyfile onto it; and destructive operations on an ANCESTOR of a protected path.
Reading is allowed. Paths are resolved with realpath, so relative paths and symlink aliases count.

Installed by tests/test_000_session_guard.py (first module in sorted order), by the CI loader and by
the r5c10ak harness. Like any in-process audit hook it does not see child processes, C extensions or
ctypes; it is a rail against accidents, not a security boundary.
"""
from __future__ import annotations

import os
import sys

EXIT_CODE = 86
_DEFAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROOT = None
_PROTECTED_DIRS: list[str] = []
_PROTECTED_FILES: list[str] = []
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
_PATH_EVENTS = {"os.mkdir": (0,), "os.rename": (0, 1), "os.replace": (0, 1), "os.remove": (0,), "os.rmdir": (0,),
                "os.truncate": (0,), "shutil.rmtree": (0,), "os.link": (0, 1), "os.symlink": (1,), "os.chmod": (0,),
                "os.utime": (0,), "os.chown": (0,), "shutil.move": (0, 1), "shutil.copyfile": (1,), "shutil.copytree": (1,)}
_DESTRUCTIVE = {"os.rename", "os.replace", "os.remove", "os.rmdir", "shutil.rmtree", "shutil.move", "os.chmod"}
# Events that act on the directory entry itself rather than on what a final symlink points to.
_ENTRY_EVENTS = {"os.rename", "os.replace", "os.remove", "os.rmdir", "shutil.rmtree", "shutil.move", "os.symlink", "os.link", "os.mkdir"}
_busy = False


def _configure(root: str) -> None:
    global _ROOT, _PROTECTED_DIRS, _PROTECTED_FILES
    _ROOT = os.path.realpath(root)
    e = os.path.join(_ROOT, "evaluation", "v1_2_3")
    _PROTECTED_DIRS = [os.path.join(_ROOT, "evaluation", "v4_runs")]
    _PROTECTED_FILES = [os.path.join(e, name) for name in (
        "authorization_lifecycle_events.jsonl", "step9_63c_r11_v3_authorization_manifest.json",
        "step9_63c_r11_runner_freeze.json", "step9_63c_r11_current_runner_identity.json",
        "step9_63c_r11_identity_pointer_creation_record.json", "step9_63c_r11_activation_approval.json")]


# Position of the dir_fd argument in each audit event (relative paths are relative to that directory).
_DIR_FD_INDEX = {"os.remove": 1, "os.rmdir": 1, "os.mkdir": 2, "os.symlink": 2, "os.chmod": 2, "os.utime": 3,
                 "shutil.rmtree": 1, "os.chown": 3}
_RENAME_DIR_FD = {"os.rename": (2, 3), "os.replace": (2, 3), "os.link": (2, 3)}


def _fd_directory(fd) -> str | None:
    """The directory a directory file descriptor refers to (Linux /proc, macOS F_GETPATH)."""
    if not isinstance(fd, int) or fd < 0:
        return None
    try:
        return os.readlink(f"/proc/self/fd/{fd}")
    except OSError:
        pass
    try:
        import fcntl
        if hasattr(fcntl, "F_GETPATH"):
            return os.fsdecode(fcntl.fcntl(fd, fcntl.F_GETPATH, bytes(1024)).rstrip(b"\0"))
    except OSError:
        return None
    return None


def _resolve(path, *, entry: bool = False, base: str | None = None) -> str | None:
    """realpath of `path`; with entry=True the LAST component is not followed (removing, renaming or
    creating a directory entry acts on the entry itself, e.g. a temporary symlink pointing at a real file)."""
    if isinstance(path, int) or path is None:
        return None
    try:
        p = os.fsdecode(path)
    except TypeError:
        return None
    if not os.path.isabs(p):
        p = os.path.join(base if base is not None else os.getcwd(), p)
    if entry:
        p = os.path.normpath(p)
        return os.path.join(os.path.realpath(os.path.dirname(p)), os.path.basename(p))
    return os.path.realpath(p)


def protected(path: str | None, *, destructive: bool = False) -> bool:
    if path is None:
        return False
    for d in _PROTECTED_DIRS:
        if path == d or path.startswith(d + os.sep):
            return True
    if path in _PROTECTED_FILES:
        return True
    if destructive:  # removing or moving an ancestor would take the protected state with it
        return any(t.startswith(path + os.sep) for t in _PROTECTED_DIRS + _PROTECTED_FILES)
    return False


def _write_open(args) -> bool:
    mode = args[1] if len(args) > 1 else None
    flags = args[2] if len(args) > 2 else 0
    if isinstance(mode, str) and any(c in mode for c in "wax+"):
        return True
    return isinstance(flags, int) and bool(flags & _WRITE_FLAGS)


def _stop(event: str, path: str) -> None:
    test = os.environ.get("CBTI_GUARD_CURRENT_TEST") or "unknown test"
    try:
        sys.stderr.write(f"\nSESSION GUARD: {event} on the real activation state {path} (from {test}); the test session is stopped.\n")
        sys.stderr.flush()
    finally:
        os._exit(EXIT_CODE)


def _hook(event: str, args) -> None:
    global _busy
    if _busy:
        return
    _busy = True
    try:
        if event == "open":
            if _write_open(args):
                target = _resolve(args[0])
                if protected(target):
                    _stop(event, target)
        elif event in _PATH_EVENTS:
            for position, index in enumerate(_PATH_EVENTS[event]):
                if index < len(args):
                    fd_index = _RENAME_DIR_FD[event][position] if event in _RENAME_DIR_FD else _DIR_FD_INDEX.get(event)
                    dir_fd = args[fd_index] if fd_index is not None and fd_index < len(args) else None
                    base = None
                    if isinstance(dir_fd, int) and dir_fd >= 0:
                        base = _fd_directory(dir_fd)
                        if base is None:  # cannot tell where it points: do not guess against the cwd
                            continue
                    target = _resolve(args[index], entry=event in _ENTRY_EVENTS, base=base)
                    if protected(target, destructive=event in _DESTRUCTIVE):
                        _stop(event, target)
    finally:
        _busy = False


def install(root: str | None = None) -> None:
    """Idempotent. The root defaults to this repository; CBTI_SESSION_GUARD_ROOT overrides it (tests only)."""
    if os.environ.get("CBTI_SESSION_GUARD_INSTALLED") == str(os.getpid()):
        return
    _configure(root or os.environ.get("CBTI_SESSION_GUARD_ROOT") or _DEFAULT_ROOT)
    sys.addaudithook(_hook)
    os.environ["CBTI_SESSION_GUARD_INSTALLED"] = str(os.getpid())
