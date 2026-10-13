#!/usr/bin/env python3
"""Read-only post-execution (or post-interruption) report for the r11 formal execution.

Never writes, never repairs, never reconciles: it only reads the attempt ledger, the
transaction journal, the namespace marker and the lifecycle reducer, and prints JSON.
Safe to run at any time, including after an interruption.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
AUTH_FILE = ROOT / "evaluation/v1_2_3/step9_63c_r11_v3_authorization_manifest.json"
LEDGER = ROOT / "evaluation/v1_2_3/authorization_lifecycle_events.jsonl"
RUN_ROOT = ROOT / "evaluation/v4_runs"


def _lines(path: Path) -> list[dict] | str:
    if not path.exists():
        return "ABSENT"
    raw = path.read_bytes()
    rows = []
    for number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"_torn_or_corrupt_line": number})
    return rows


def main() -> int:
    from scripts import authorization_lifecycle as lifecycle
    from scripts import v3_execution_transaction as transaction

    auth = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    aid, attempt = auth["authorization_id"], auth["attempt_id"]
    namespace = RUN_ROOT / auth["execution_namespace"]["namespace_id"]
    out_dir = namespace / auth["evaluation_id"]
    report: dict = {"authorization_id": aid}

    journal = _lines(RUN_ROOT / ".execution_transactions" / f"{aid}.jsonl")
    if isinstance(journal, list):
        kinds = [row.get("event_type", "CORRUPT") for row in journal]
        report["transaction_journal"] = {
            "lines": len(journal), "head": kinds[:4],
            "case_started": kinds.count("CASE_STARTED"),
            # Pure classification function; reconcile_journal (which writes) is never called.
            "classification": (transaction.reconcile(journal)
                               if "CORRUPT" not in kinds else "CORRUPT_LINE_PRESENT")}
    else:
        report["transaction_journal"] = journal

    marker = namespace / ".namespace_allocation.json"
    report["namespace_dir_exists"] = namespace.exists()
    report["namespace_marker"] = (json.loads(marker.read_text(encoding="utf-8"))
                                  if marker.exists() else "ABSENT")

    attempts = _lines(out_dir / "attempts.jsonl")
    if isinstance(attempts, list):
        statuses = [row.get("status", "CORRUPT") for row in attempts]
        last = attempts[-1] if attempts else {}
        report["attempt_ledger"] = {
            "lines": len(attempts), "first": statuses[:5], "last_status": statuses[-1:],
            "cases_started": last.get("cases_started"), "cases_completed": last.get("cases_completed"),
            "failure": {k: last.get(k) for k in ("failure_stage", "failure_type") if k in last}}
    else:
        report["attempt_ledger"] = attempts
    for suffix in ("raw_traces", "case_results"):
        rows = _lines(out_dir / f"{attempt}_{suffix}.jsonl")
        report[suffix] = (rows if isinstance(rows, str) else
                          {"lines": len(rows), "case_ids_first_last": [rows[0].get("case_id"), rows[-1].get("case_id")]
                           if rows else []})

    try:
        state = lifecycle.reduce_authorization_lifecycle(
            authorization_id=aid, manifest=auth, manifest_path=AUTH_FILE, run_root=RUN_ROOT)
        report["lifecycle"] = {"derived_state": state.get("derived_state"),
                               "executable": state.get("executable")}
    except Exception as error:  # reported, never repaired
        report["lifecycle"] = {"error": f"{type(error).__name__}: {error}"}
    try:
        report["active_authorizations"] = lifecycle.active_authorizations(ROOT)
    except Exception as error:
        report["active_authorizations"] = f"{type(error).__name__}: {error}"

    raw = LEDGER.read_bytes()
    report["lifecycle_ledger"] = {"bytes": len(raw), "lines": raw.count(b"\n"),
                                  "sha256": hashlib.sha256(raw).hexdigest()}
    report["authorization_manifest_sha256"] = hashlib.sha256(AUTH_FILE.read_bytes()).hexdigest()
    print(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
