#!/usr/bin/env python3
"""Copy the five r11 formal-execution artifacts into a read-only evidence archive.

Sources under evaluation/v4_runs/ are only opened for reading. Each source must match its
pinned SHA-256 before copying; each copy is created with O_EXCL (never overwrites), read back
and compared, then made read-only (0444). Writes MANIFEST.json, SHA256SUMS and README.md.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE = ROOT / "evaluation/v1_2_3/step9_63c_r11_run_archive"
NS = "heldout-v4-treatment-v3-run-9ec9c305cc4de01e6538"
EV = NS + "/heldout-v4-step9_55a-treatment-v3-20260930-01"
ATT = "attempt-step9_63c_r11-2312daefa1364bfd83ff3948d101c765"
# relative to evaluation/v4_runs -> pinned SHA-256 (from step9_63c_r11_post_run_review.md section 4.1)
PINNED = {
    ".execution_transactions/auth-step9_63c_r11-1a399434ec0e4494b0045734846b2042.jsonl":
        "63dd783f4f24beedf2bc68a47e282d04a8efb8968a0c7d959703411792b52108",
    NS + "/.namespace_allocation.json":
        "21fad903a54e323c97721ca4a9f3956026bd1431498d3696aa8cb1615f5980e3",
    EV + "/attempts.jsonl":
        "4326a64094b626db45cb13f31b1ec8a716f683153639a7a4e93fd50fc9bfda36",
    EV + f"/{ATT}_raw_traces.jsonl":
        "abd307e0e64730448856c595f134d437a2130bf8ef160a680126cd0067b2a2f5",
    EV + f"/{ATT}_case_results.jsonl":
        "6672f3ef21a20a68776925267896ed4362832aaabc5a16c06546a6b778ef0ba8",
}


def read_source(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as stream:
        return stream.read()


def write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o644)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def main() -> int:
    if ARCHIVE.exists():
        print("ARCHIVE_ALREADY_EXISTS")
        return 1
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()
    copied_at = datetime.now(timezone.utc).isoformat()
    entries = []
    for rel, expected in PINNED.items():
        source = ROOT / "evaluation/v4_runs" / rel
        data = read_source(source)
        if hashlib.sha256(data).hexdigest() != expected:
            print(f"SOURCE_SHA_MISMATCH {rel}")
            return 1
        target = ARCHIVE / "run_root" / rel
        write_new(target, data)
        if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
            print(f"READBACK_SHA_MISMATCH {rel}")
            return 1
        os.chmod(target, 0o444)
        entries.append({
            "source_path": f"evaluation/v4_runs/{rel}",
            "archive_path": target.relative_to(ROOT).as_posix(),
            "bytes": len(data), "sha256": expected,
            "source_mtime_utc": datetime.fromtimestamp(source.stat().st_mtime, timezone.utc).isoformat(),
        })
    manifest = {
        "artifact_type": "R11_FORMAL_EXECUTION_EVIDENCE_ARCHIVE",
        "status": "READ_ONLY_EVIDENCE_COPY",
        "authorization_id": "auth-step9_63c_r11-1a399434ec0e4494b0045734846b2042",
        "attempt_id": ATT,
        "transaction_id": "txn-v3-e96bdfed431149098ea815dec817d6ab",
        "evaluation_id": "heldout-v4-step9_55a-treatment-v3-20260930-01",
        "runner_freeze_sha256": "bafcec8d2ae0bad6c3cb43e89bd49171b85374957ec6ce173071fef5248357b3",
        "copied_at_utc": copied_at, "repository_head_at_copy": head,
        "originals_remain_at": "evaluation/v4_runs/ (git-ignored, unchanged)",
        "files": entries,
    }
    write_new(ARCHIVE / "MANIFEST.json", (json.dumps(manifest, indent=1, sort_keys=True) + "\n").encode())
    sums = "".join(f"{e['sha256']}  {Path(e['archive_path']).relative_to(ARCHIVE.relative_to(ROOT)).as_posix()}\n"
                   for e in entries)
    write_new(ARCHIVE / "SHA256SUMS", sums.encode())
    readme = (
        "# r11 正式执行证据归档（只读副本）\n\n"
        "本目录是 r11 正式执行（事务 `txn-v3-e96bdfed431149098ea815dec817d6ab`）五个运行产物的逐字节副本。"
        "原件仍在被 git 忽略的 `evaluation/v4_runs/` 下，未被修改。\n\n"
        "- `run_root/` 保持原件相对 `evaluation/v4_runs/` 的路径；目录名故意不叫 `v4_runs`，"
        "所有扫描 attempt 与命名空间的代码都只以 `evaluation/v4_runs` 为根，不会把这些副本当成新的 attempt。\n"
        "- `MANIFEST.json`：源路径、归档路径、字节数、SHA-256、源文件修改时间、复制时间与当时的 HEAD。\n"
        "- `SHA256SUMS`：在本目录下运行 `shasum -a 256 -c SHA256SUMS` 校验。\n\n"
        "**不得修改本目录下的任何文件。** 生命周期状态的已知缺陷见 `../step9_63c_r11_known_limitations.md`（KL-1）。\n")
    write_new(ARCHIVE / "README.md", readme.encode())
    print(json.dumps({"archived": len(entries), "archive": ARCHIVE.relative_to(ROOT).as_posix(),
                      "head": head}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
