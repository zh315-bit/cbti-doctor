"""Step 9.63c test side-effect guard (scratchpad only, never part of the repository).

Installed through PYTHONPATH so every child interpreter inherits it. It blocks
and logs (a) any write/create/rename/delete/metadata change under the protected
repository root, (b) non-loopback network resolution/connection, and (c)
subprocesses that are not this Python interpreter. Blocking raises
PermissionError so the offending test fails visibly instead of mutating state.
"""
import json
import os
import sys
import threading

_ROOT = os.environ.get("CBTI_GUARD_ROOT")
_LOG = os.environ.get("CBTI_GUARD_LOG")
_LOCAL = threading.local()
_LOOPBACK = {"localhost", "127.0.0.1", "::1", "", None}
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
_PATH_EVENTS = {
    "os.remove", "os.rmdir", "os.mkdir", "os.symlink", "os.link", "os.truncate",
    "os.chmod", "os.chown", "os.utime", "os.chflags", "os.lchflags", "os.setxattr",
    "os.removexattr", "shutil.rmtree", "shutil.copyfile", "shutil.copymode",
    "shutil.copystat", "shutil.copytree", "shutil.move", "shutil.chown",
    "os.rename", "os.replace",
}


# (path index, dir_fd index) pairs per audit event; dir_fd-relative names must be
# resolved against the descriptor's directory, not the current working directory.
_DIR_FD_ARGS = {
    "os.remove": [(0, 1)], "os.rmdir": [(0, 1)], "os.mkdir": [(0, 2)],
    "os.chmod": [(0, 2)], "os.chown": [(0, 3)], "os.utime": [(0, 3)],
    "os.symlink": [(1, 2)], "os.link": [(0, 2), (1, 3)], "os.rename": [(0, 2), (1, 3)],
    "os.replace": [(0, 2), (1, 3)],
}


def _fd_dir(fd):
    import fcntl
    return os.fsdecode(fcntl.fcntl(fd, fcntl.F_GETPATH, bytes(1024)).rstrip(b"\0"))


def _protected(path, dir_fd=None):
    if isinstance(path, int) or path is None:
        return False
    try:
        path = os.fsdecode(os.fspath(path))
    except TypeError:
        return False
    if isinstance(dir_fd, int) and dir_fd >= 0 and not os.path.isabs(path):
        try:
            path = os.path.join(_fd_dir(dir_fd), path)
        except OSError:
            return True  # unresolvable descriptor: fail closed
    real = os.path.realpath(os.path.abspath(path))
    return real == _ROOT or real.startswith(_ROOT + os.sep)


def _record(event, detail, blocked):
    if not _LOG:
        return
    row = {"pid": os.getpid(), "event": event, "detail": detail, "blocked": blocked,
           "test": os.environ.get("CBTI_GUARD_CURRENT_TEST")}
    with open(_LOG, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, default=repr) + "\n")


def _python_executable(executable):
    try:
        name = os.path.basename(os.fsdecode(executable))
    except TypeError:
        return False
    return name.startswith("python")


def _hook(event, args):
    if getattr(_LOCAL, "busy", False):
        return
    _LOCAL.busy = True
    try:
        if event == "open":
            path, mode, flags = (list(args) + [None, None, None])[:3]
            writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
                isinstance(flags, int) and flags & _WRITE_FLAGS)
            if writing and _protected(path):
                _record(event, [path, mode, flags], True)
                raise PermissionError(f"CBTI guard blocked repository write: {path}")
        elif event in _PATH_EVENTS:
            if event in {"shutil.copyfile", "shutil.copymode", "shutil.copystat", "shutil.copytree"}:
                # (src, dst, ...): reading the repository source is allowed; only dst is written.
                pairs = [(args[1], None)] if len(args) > 1 else []
            elif event in _DIR_FD_ARGS:
                pairs = [(args[p], args[d] if d < len(args) else None)
                         for p, d in _DIR_FD_ARGS[event] if p < len(args)]
            else:
                pairs = [(a, None) for a in args if isinstance(a, (str, bytes, os.PathLike))]
            paths = [p for p, _ in pairs]
            if any(_protected(p, d) for p, d in pairs):
                _record(event, paths, True)
                raise PermissionError(f"CBTI guard blocked repository mutation: {event} {paths}")
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
        elif event in {"subprocess.Popen", "os.posix_spawn", "os.exec", "os.spawn"}:
            executable = args[0] if args else None
            allowed = _python_executable(executable)
            _record(event, [executable, args[1] if len(args) > 1 else None], not allowed)
            if not allowed:
                raise PermissionError(f"CBTI guard blocked subprocess: {executable}")
        elif event in {"os.system", "os.fork", "os.forkpty"}:
            _record(event, list(args), True)
            raise PermissionError(f"CBTI guard blocked {event}")
    finally:
        _LOCAL.busy = False


if _ROOT:
    _ROOT = os.path.realpath(_ROOT)
    sys.addaudithook(_hook)
