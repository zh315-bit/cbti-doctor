"""Read-only proof that the real activation state is unchanged.

usage: python real_state_check.py snapshot OUT.json      record the current state
       python real_state_check.py compare BASE.json      exit 1 if anything differs
Checked: the ledger (bytes, SHA, line count, equality with the blob in commit ef37534), the r11
authorization manifest, the Freeze, the pointer, and a hash over the whole evaluation/v4_runs tree
(every path, its type, and every regular file's bytes).
"""
import hashlib, json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
E = ROOT / "evaluation/v1_2_3"
FILES = {"ledger": E / "authorization_lifecycle_events.jsonl", "r11_manifest": E / "step9_63c_r11_v3_authorization_manifest.json",
         "freeze": E / "step9_63c_r11_runner_freeze.json", "pointer": E / "step9_63c_r11_current_runner_identity.json"}
ACTIVATION_COMMIT = "ef3753435c4ab095f1753122ab720eb0ce041dfa"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tree_hash(top: Path) -> dict:
    rows = []
    for directory, dirs, files in os.walk(top, followlinks=False):
        dirs.sort()
        base = Path(directory)
        rows.append(f"D {base.relative_to(ROOT).as_posix()}")
        for name in sorted(files):
            p = base / name
            rel = p.relative_to(ROOT).as_posix()
            if p.is_symlink():
                rows.append(f"L {rel} {os.readlink(p)}")
            else:
                rows.append(f"F {rel} {sha(p.read_bytes())}")
        for name in dirs:
            if (base / name).is_symlink():
                rows.append(f"L {(base / name).relative_to(ROOT).as_posix()} {os.readlink(base / name)}")
    return {"sha256": sha("\n".join(rows).encode()), "entries": len(rows)}


def state() -> dict:
    out = {}
    for name, path in FILES.items():
        data = path.read_bytes()
        out[name] = {"sha256": sha(data), "size": len(data)}
    raw = FILES["ledger"].read_bytes()
    out["ledger"]["lines"] = len(raw.decode().splitlines())
    blob = subprocess.run(["git", "show", f"{ACTIVATION_COMMIT}:evaluation/v1_2_3/authorization_lifecycle_events.jsonl"], cwd=ROOT,
                          capture_output=True, check=True).stdout
    out["ledger"]["equals_activation_commit_blob"] = blob == raw
    out["v4_runs_tree"] = tree_hash(ROOT / "evaluation/v4_runs")
    return out


if __name__ == "__main__":
    mode, path = sys.argv[1], Path(sys.argv[2])
    now = state()
    if mode == "snapshot":
        path.write_text(json.dumps(now, indent=1, sort_keys=True) + "\n")
        print(json.dumps(now, indent=1, sort_keys=True))
    else:
        base = json.loads(path.read_text())
        same = base == now
        print(json.dumps({"identical": same, "now": now}, indent=1, sort_keys=True))
        sys.exit(0 if same else 1)
