"""Self-check of the activation checklist: re-runs every command in it and compares the output with the
recorded "expected output" character for character. Fails on any Traceback / error text in an expectation.

usage: python selfcheck_checklist.py   (from the repository root; read-only)
"""
import os, re, subprocess, sys
from pathlib import Path

CHECKLIST = Path("evaluation/v1_2_3/step9_63c_r5c10ai_activation_approval_checklist.md")
env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
lines = CHECKLIST.read_text(encoding="utf-8").splitlines()
pairs = []
i = 0
while i < len(lines):
    m = re.match(r"^  - 命令：`(.*)`$", lines[i])
    if m and i + 1 < len(lines) and lines[i + 1].startswith("  - 期望输出："):
        cmd = m.group(1)
        j = i + 3  # skip the "期望输出：" line and the opening fence
        out = []
        while not lines[j].strip() == "```":
            out.append(lines[j][4:] if lines[j].startswith("    ") else lines[j])
            j += 1
        pairs.append((cmd, "\n".join(out).strip()))
        i = j
    i += 1
bad = []
for n, (cmd, expected) in enumerate(pairs, 1):
    actual = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env, executable="/bin/zsh").stdout.strip()
    stderr_free = "Traceback" not in expected and "Error" not in expected
    ok = actual == expected and stderr_free
    print(f"{'OK ' if ok else 'BAD'} {n:2d} {cmd[:100]}")
    if not ok:
        bad.append(n)
print(f"{len(pairs) - len(bad)}/{len(pairs)} identical")
sys.exit(0 if not bad and len(pairs) == 44 else 1)
