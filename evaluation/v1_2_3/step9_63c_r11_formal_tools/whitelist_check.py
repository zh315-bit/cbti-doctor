#!/usr/bin/env python3
"""Read-only whole-repository snapshot and write-whitelist check for the r11 formal execution.

snapshot OUT.json   record every regular file / directory / symlink under the repository
                    (except .git and .venv) with its SHA-256; writes only OUT.json (keep it
                    outside the repository, e.g. under /tmp).
compare  BASE.json  compare the current tree with BASE.json and classify every difference:
                    exit 0 when every changed/added path is on the whitelist and nothing was
                    removed; exit 1 otherwise. Never writes anything.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SKIP_DIRS = {".git", ".venv"}
AUTH = "auth-step9_63c_r11-1a399434ec0e4494b0045734846b2042"
ATTEMPT = "attempt-step9_63c_r11-2312daefa1364bfd83ff3948d101c765"
NAMESPACE = "evaluation/v4_runs/heldout-v4-treatment-v3-run-9ec9c305cc4de01e6538"
EVALUATION = NAMESPACE + "/heldout-v4-step9_55a-treatment-v3-20260930-01"
# Paths the formal execution may create; "._" AppleDouble companions of these are also allowed.
NEW_ALLOWED = {
    f"evaluation/v4_runs/.execution_transactions/{AUTH}.jsonl",
    NAMESPACE,
    NAMESPACE + "/.namespace_allocation.json",
    EVALUATION,
    EVALUATION + "/attempts.jsonl",
    EVALUATION + f"/{ATTEMPT}_raw_traces.jsonl",
    EVALUATION + f"/{ATTEMPT}_case_results.jsonl",
}
# Existing paths whose content may legitimately change (directories change listing only).
CHANGE_ALLOWED = {
    "evaluation/v4_runs/.namespace-allocation.lock",
}


def _entry(path: Path) -> dict:
    if path.is_symlink():
        return {"type": "symlink", "target": os.readlink(path)}
    if path.is_dir():
        return {"type": "dir"}
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return {"type": "file", "size": path.stat().st_size, "sha256": digest.hexdigest()}


def take() -> dict[str, dict]:
    tree: dict[str, dict] = {}
    for current, dirs, files in os.walk(ROOT):
        rel_dir = Path(current).relative_to(ROOT)
        dirs[:] = sorted(d for d in dirs if not (rel_dir == Path(".") and d in SKIP_DIRS))
        for name in dirs + sorted(files):
            path = Path(current) / name
            tree[(rel_dir / name).as_posix()] = _entry(path)
    return tree


def _allowed_new(rel: str) -> bool:
    head, _, name = rel.rpartition("/")
    if name.startswith("._"):
        rel = f"{head}/{name[2:]}" if head else name[2:]
    return rel in NEW_ALLOWED


def compare(base: dict[str, dict]) -> dict:
    now = take()
    added = sorted(set(now) - set(base))
    removed = sorted(set(base) - set(now))
    changed = sorted(p for p in set(now) & set(base) if now[p] != base[p])
    return {
        "added": added, "removed": removed, "changed": changed,
        "added_not_whitelisted": [p for p in added if not _allowed_new(p)],
        "changed_not_whitelisted": [p for p in changed if p not in CHANGE_ALLOWED],
        "whitelisted_paths_present": sorted(p for p in NEW_ALLOWED if p in now),
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3 or argv[1] not in {"snapshot", "compare"}:
        print(__doc__)
        return 2
    if argv[1] == "snapshot":
        out = Path(argv[2]).resolve()
        if ROOT in out.parents:
            print("refusing to write the snapshot inside the repository")
            return 2
        tree = take()
        out.write_text(json.dumps(tree, sort_keys=True), encoding="utf-8")
        print(json.dumps({"entries": len(tree), "snapshot": str(out)}))
        return 0
    result = compare(json.loads(Path(argv[2]).read_text(encoding="utf-8")))
    result["ok"] = not (result["removed"] or result["added_not_whitelisted"]
                        or result["changed_not_whitelisted"])
    print(json.dumps(result, indent=1))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
