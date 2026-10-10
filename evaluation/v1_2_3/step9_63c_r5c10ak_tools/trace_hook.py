"""Audit-only tracer (Step 9.63c-r5c10ak): records every access by a test process to the protected
real-root locations (evaluation/v4_runs, the lifecycle ledger, the r11 authorization manifest),
reads included. It blocks nothing; the guard (v3) and the session guard do the blocking."""
import json, os, sys

ROOT = os.path.realpath(os.environ.get("CBTI_TRACE_ROOT", os.getcwd()))
PROTECTED_DIRS = [os.path.join(ROOT, "evaluation", "v4_runs")]
PROTECTED_FILES = [os.path.join(ROOT, "evaluation", "v1_2_3", "authorization_lifecycle_events.jsonl"),
                   os.path.join(ROOT, "evaluation", "v1_2_3", "step9_63c_r11_v3_authorization_manifest.json")]
EVENTS = {"open", "os.listdir", "os.scandir", "os.mkdir", "os.rename", "os.replace", "os.remove", "os.rmdir",
          "os.truncate", "shutil.rmtree", "os.chmod", "os.utime", "glob.glob", "os.link", "os.symlink", "shutil.move", "shutil.copyfile"}
_out = None
_busy = False


def _norm(p):
    try:
        if isinstance(p, int):
            return None
        p = os.fsdecode(p)
        return os.path.realpath(os.path.join(os.getcwd(), p)) if not os.path.isabs(p) else os.path.realpath(p)
    except Exception:
        return None


def _hit(path):
    if path is None:
        return None
    for d in PROTECTED_DIRS:
        if path == d or path.startswith(d + os.sep):
            return "v4_runs"
    if path in PROTECTED_FILES:
        return "ledger" if path.endswith(".jsonl") else "r11_manifest"
    for d in PROTECTED_DIRS:  # an ancestor that is listed/globbed onto the protected tree
        if d.startswith(path + os.sep):
            return None
    return None


def _hook(event, args):
    global _busy
    if _busy or event not in EVENTS:
        return
    _busy = True
    try:
        paths = [a for a in args[:2] if isinstance(a, (str, bytes, os.PathLike))]
        for p in paths:
            n = _norm(p)
            kind = _hit(n)
            if kind:
                mode = args[1] if event == "open" and len(args) > 1 else None
                flags = args[2] if event == "open" and len(args) > 2 else None
                _out.write(json.dumps({"test": os.environ.get("CBTI_GUARD_CURRENT_TEST"), "event": event, "kind": kind,
                                       "path": os.path.relpath(n, ROOT), "mode": str(mode), "flags": flags}) + "\n")
                _out.flush()
    finally:
        _busy = False


def install(out_path):
    global _out
    _out = open(out_path, "a", encoding="utf-8")
    sys.addaudithook(_hook)
