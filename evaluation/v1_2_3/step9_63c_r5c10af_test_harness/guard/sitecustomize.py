"""Step 9.63c-r5c10af test side-effect guard, v3 CANDIDATE (not approved; evidence copy).

Activated only through PYTHONPATH. v1 (r5c10ab) and v2 (r5c10ad) stay untouched as
historical evidence. Blocks and logs, for the protected root CBTI_GUARD_ROOT:
  * writes, creations, renames, deletions and metadata changes (path, descriptor and
    dir_fd forms),
  * writes through symlinks, through '..' after a symlink, and through hard links,
  * non-loopback network use, non-Python subprocesses, and Python children started
    without this guard (isolated/no-site/ignore-environment flags, scrubbed environment).
Known limits (not blockable from Python): ctypes/C-extension syscalls, and anything
that bypasses the audit hook machinery.
"""
import json
import os
import stat
import sys
import threading

_ROOT = os.environ.get("CBTI_GUARD_ROOT")
_LOG = os.environ.get("CBTI_GUARD_LOG")
_GUARD_DIR = os.path.dirname(os.path.abspath(__file__))
_LOCAL = threading.local()
_LOOPBACK = {"localhost", "127.0.0.1", "::1", "", None}
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
_ROOT_ID = None
_WALK_LIMIT = 300000

# Events whose path operand names a directory ENTRY (the link itself, not its target).
_ENTRY_EVENTS = {"os.remove", "os.rmdir", "os.rename", "os.symlink", "os.link", "shutil.rmtree"}
# (path index, dir_fd index) pairs per audit event.
_DIR_FD_ARGS = {
    "os.remove": [(0, 1)], "os.rmdir": [(0, 1)], "os.mkdir": [(0, 2)],
    "os.chmod": [(0, 2)], "os.chown": [(0, 3)], "os.utime": [(0, 3)],
    "os.symlink": [(1, 2)], "os.link": [(0, 2), (1, 3)], "os.rename": [(0, 2), (1, 3)],
}
# Events that modify the inode behind the path (shared by every hard link to it).
_INODE_MUTATING = {"os.truncate", "os.chmod", "os.chown", "os.utime", "os.setxattr",
                   "os.removexattr", "os.chflags", "os.lchflags"}
_FIRST_ARG_EVENTS = {"os.truncate", "os.setxattr", "os.removexattr", "os.chflags", "os.lchflags"}
# Events that, applied to an ANCESTOR of the root, move/delete/lock the whole repository.
_ANCESTOR_EVENTS = {"os.remove", "os.rmdir", "os.rename", "shutil.rmtree", "shutil.move",
                    "os.chmod", "os.chown", "os.chflags", "os.lchflags"}
_COPY_DST_EVENTS = {"shutil.copyfile", "shutil.copymode", "shutil.copystat", "shutil.copytree"}
_EXEC_EVENTS = {"subprocess.Popen": (0, 1, 3), "os.exec": (0, 1, 2), "os.posix_spawn": (0, 1, 2)}


class _Unresolvable(Exception):
    pass


def _record(event, detail, blocked):
    if not _LOG:
        return
    row = {"pid": os.getpid(), "event": event, "detail": detail, "blocked": blocked,
           "test": os.environ.get("CBTI_GUARD_CURRENT_TEST")}
    with open(_LOG, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, default=repr) + "\n")


def _fd_dir(fd):
    import fcntl
    return os.fsdecode(fcntl.fcntl(fd, fcntl.F_GETPATH, bytes(1024)).rstrip(b"\0"))


def _resolve(path, dir_fd, entry):
    """Real path of the operand; None when it is not a filesystem path at all."""
    if isinstance(path, int):
        try:
            return _fd_dir(path)
        except OSError:
            return None  # pipe/socket/etc.: cannot name a repository file
    try:
        p = os.fsdecode(os.fspath(path))
    except TypeError:
        return None
    if isinstance(dir_fd, int) and dir_fd >= 0 and not os.path.isabs(p):
        try:
            p = os.path.join(_fd_dir(dir_fd), p)
        except OSError as error:
            raise _Unresolvable() from error
    base = os.path.basename(p)
    if entry and base not in ("", ".", ".."):
        # Directory-entry operations act on the entry itself: resolve only its parent.
        # (No abspath: textual '..' collapsing would skip symlinks.)
        return os.path.join(os.path.realpath(os.path.dirname(p) or "."), base)
    # Trailing slash or dot components make the OS follow the final symlink.
    return os.path.realpath(p)


def _under_root(real):
    if real == _ROOT or real.startswith(_ROOT + os.sep):
        return True
    # Case-insensitive/normalising filesystems: compare identities along the ancestry.
    candidate = real
    while True:
        try:
            st = os.lstat(candidate)
            if _ROOT_ID is not None and (st.st_dev, st.st_ino) == _ROOT_ID:
                return True
        except OSError:
            pass
        parent = os.path.dirname(candidate)
        if parent == candidate:
            return False
        candidate = parent


def _inode_in_root(dev, ino):
    seen = 0
    for directory, _, files in os.walk(_ROOT, followlinks=False):
        for name in files:
            seen += 1
            if seen > _WALK_LIMIT:
                return True  # cannot prove otherwise: fail closed
            try:
                st = os.lstat(os.path.join(directory, name))
            except OSError:
                continue
            if st.st_ino == ino and st.st_dev == dev:
                return True
    return False


def _is_ancestor_of_root(real):
    if real != _ROOT and (_ROOT + os.sep).startswith(real.rstrip(os.sep) + os.sep):
        return True
    try:
        wanted = os.lstat(real)
    except OSError:
        return False
    candidate = os.path.dirname(_ROOT)
    while True:
        try:
            info = os.lstat(candidate)
            if (info.st_dev, info.st_ino) == (wanted.st_dev, wanted.st_ino):
                return True
        except OSError:
            pass
        parent = os.path.dirname(candidate)
        if parent == candidate:
            return False
        candidate = parent


def _hardlinked_into_root(real):
    try:
        st = os.stat(real)
    except OSError:
        return False
    if (not stat.S_ISREG(st.st_mode) or st.st_nlink <= 1 or _ROOT_ID is None
            or st.st_dev != _ROOT_ID[0]):
        return False
    return _inode_in_root(st.st_dev, st.st_ino)


def _check(event, detail, path, dir_fd=None, entry=False, mutating=False, ancestors=False):
    try:
        real = _resolve(path, dir_fd, entry)
    except _Unresolvable:
        real = ""
        reason = "unresolvable descriptor"
    else:
        reason = None
        if real is not None:
            if _under_root(real):
                reason = "protected path"
            elif ancestors and _is_ancestor_of_root(real):
                reason = "ancestor of the protected root"
            elif mutating and not entry and _hardlinked_into_root(real):
                reason = "hard link to a protected file"
    if reason:
        _record(event, detail, True)
        raise PermissionError(f"CBTI guard blocked repository mutation ({reason}): {event} {detail}")


def _python_executable(executable):
    try:
        return os.path.basename(os.fsdecode(executable)).startswith("python")
    except TypeError:
        return False


def _unguarded_python_reason(argv, env):
    """Why a child Python would run without this guard, or None."""
    for arg in list(argv or [])[1:]:
        arg = os.fsdecode(arg)
        if not arg.startswith("-") or arg in ("-c", "-m"):
            break
        if arg.startswith("--"):
            if arg == "--isolated":
                return "isolated mode ignores PYTHONPATH"
            continue
        for char in arg[1:]:
            if char in "ISE":
                return f"python flag -{char} disables the guard"
            if char in "cmWXQ":
                break
    effective = os.environ if env is None else env
    try:
        items = effective.items() if hasattr(effective, "items") else [
            os.fsdecode(entry).split("=", 1) for entry in effective]
        merged = {os.fsdecode(k): os.fsdecode(v) for k, v in items}
    except (TypeError, ValueError):
        return "environment not inspectable"
    if merged.get("CBTI_GUARD_ROOT") != _ROOT:
        return "child environment drops CBTI_GUARD_ROOT"
    if _GUARD_DIR not in merged.get("PYTHONPATH", "").split(os.pathsep):
        return "child environment drops the guard directory from PYTHONPATH"
    return None


def _hook(event, args):
    if getattr(_LOCAL, "busy", False):
        return
    _LOCAL.busy = True
    try:
        if event == "open":
            path, mode, flags = (list(args) + [None, None, None])[:3]
            writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
                isinstance(flags, int) and flags & _WRITE_FLAGS)
            if writing:
                _check(event, [path, mode, flags], path, mutating=True)
        elif event in _DIR_FD_ARGS:
            for index, fd_index in _DIR_FD_ARGS[event]:
                if index < len(args):
                    _check(event, [args[index]], args[index],
                           args[fd_index] if fd_index < len(args) else None,
                           entry=event in _ENTRY_EVENTS, mutating=event in _INODE_MUTATING,
                           ancestors=event in _ANCESTOR_EVENTS)
        elif event in _COPY_DST_EVENTS:
            if len(args) > 1:
                _check(event, [args[1]], args[1])
        elif event == "shutil.move":
            if args:
                _check(event, [args[0]], args[0], entry=True, ancestors=True)
            if len(args) > 1:
                _check(event, [args[1]], args[1])
        elif event in _FIRST_ARG_EVENTS:
            if args:
                _check(event, [args[0]], args[0], mutating=True, ancestors=event in _ANCESTOR_EVENTS)
        elif event == "shutil.rmtree":
            if args:
                _check(event, [args[0]], args[0], entry=True, ancestors=True)
        elif event == "sqlite3.connect":
            database = args[0] if args else None
            if isinstance(database, (str, bytes, os.PathLike)):
                name = os.fsdecode(database)
                read_only = name.startswith("file:") and "mode=ro" in name
                if name.startswith("file:"):
                    name = name[len("file:"):].split("?", 1)[0]
                if name and name != ":memory:" and not read_only:
                    _check(event, [database], name, mutating=True)
        elif event in {"socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyname_ex"}:
            host = args[0] if args else None
            if isinstance(host, bytes):
                host = host.decode(errors="replace")
            if host not in _LOOPBACK:
                _record(event, [host], True)
                raise PermissionError(f"CBTI guard blocked network resolution: {host}")
        elif event in {"socket.connect", "socket.sendto"}:
            address = args[1] if len(args) > 1 else None
            host = address[0] if isinstance(address, tuple) else address
            if isinstance(address, tuple) and host not in _LOOPBACK:
                _record(event, [repr(address)], True)
                raise PermissionError(f"CBTI guard blocked network connection: {address}")
        elif event in _EXEC_EVENTS:
            exe_i, argv_i, env_i = _EXEC_EVENTS[event]
            executable = args[exe_i] if len(args) > exe_i else None
            argv = args[argv_i] if len(args) > argv_i else None
            env = args[env_i] if len(args) > env_i else None
            reason = None if _python_executable(executable) else "non-Python subprocess"
            if reason is None:
                reason = _unguarded_python_reason(argv, env)
            _record(event, [executable, argv], reason is not None)
            if reason:
                raise PermissionError(f"CBTI guard blocked subprocess ({reason}): {executable}")
        elif event in {"os.system", "os.fork", "os.forkpty", "os.spawn"}:
            _record(event, list(args), True)
            raise PermissionError(f"CBTI guard blocked {event}")
    finally:
        _LOCAL.busy = False


def _install_wrappers():
    """Operations that raise no audit event, or hide operands from it."""
    real_open = os.open

    def guarded_open(path, flags, mode=0o777, *, dir_fd=None):
        # The audit event omits dir_fd, so a relative name would be resolved against
        # the working directory instead of the directory descriptor.
        if dir_fd is not None and flags & _WRITE_FLAGS and not getattr(_LOCAL, "busy", False):
            _LOCAL.busy = True
            try:
                _check("os.open(dir_fd)", [path, flags], path, dir_fd, mutating=True)
            finally:
                _LOCAL.busy = False
        return real_open(path, flags, mode, dir_fd=dir_fd)

    os.open = guarded_open
    for name in ("mkfifo", "mknod"):  # create filesystem nodes without any audit event
        real = getattr(os, name, None)
        if real is None:
            continue

        def guarded(path, *rest, __real=real, __name=name, dir_fd=None, **kwargs):
            if not getattr(_LOCAL, "busy", False):
                _LOCAL.busy = True
                try:
                    _check(f"os.{__name}", [path], path, dir_fd, entry=True)
                finally:
                    _LOCAL.busy = False
            return __real(path, *rest, dir_fd=dir_fd, **kwargs)

        setattr(os, name, guarded)


if _ROOT:
    _ROOT = os.path.realpath(_ROOT)
    try:
        _info = os.lstat(_ROOT)
        _ROOT_ID = (_info.st_dev, _info.st_ino)
    except OSError:
        _ROOT_ID = None
    sys.addaudithook(_hook)
    _install_wrappers()
