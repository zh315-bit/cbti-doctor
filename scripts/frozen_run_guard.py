"""Append-only authorization state for a frozen benchmark invocation.

This module deliberately knows nothing about Agent behavior or Benchmark cases.
It records only whether an authorized evaluation attempt has reached a case.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


STATUSES = {
    "PREPARED",
    "STARTED",
    "FAILED_BEFORE_FIRST_CASE",
    "FAILED_AFTER_PARTIAL_EXECUTION",
    "COMPLETED",
    "BLOCKED_BY_MANIFEST_GUARD",
}
STARTLESS_TERMINAL = {"FAILED_BEFORE_FIRST_CASE", "BLOCKED_BY_MANIFEST_GUARD"}
BLOCKING_STATUSES = {"STARTED", "FAILED_AFTER_PARTIAL_EXECUTION", "COMPLETED"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FrozenRunGuard:
    """Read and append execution state without altering frozen inputs."""

    def __init__(self, *, ledger_path: Path, manifest_path: Path, benchmark_path: Path, rubric_path: Path):
        self.ledger_path = ledger_path
        self.manifest_path = manifest_path
        self.benchmark_path = benchmark_path
        self.rubric_path = rubric_path

    def _manifest(self) -> dict:
        if not self.manifest_path.exists():
            raise RuntimeError("frozen manifest is missing")
        try:
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise RuntimeError("frozen manifest is invalid") from error

    def _attempts(self) -> list[dict]:
        if not self.ledger_path.exists():
            return []
        attempts: list[dict] = []
        for line_number, line in enumerate(self.ledger_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as error:
                raise RuntimeError(f"ambiguous ledger: invalid JSON on line {line_number}") from error
            if not isinstance(entry, dict) or entry.get("status") not in STATUSES:
                raise RuntimeError(f"ambiguous ledger: invalid entry on line {line_number}")
            attempts.append(entry)
        return attempts

    def _hashes(self) -> tuple[dict, bool, str | None]:
        manifest = self._manifest()
        expected_benchmark = manifest.get("benchmark", {}).get("sha256")
        expected_rubric = manifest.get("evaluation_configuration", {}).get("rubric_sha256")
        if not isinstance(expected_benchmark, str) or not isinstance(expected_rubric, str):
            return manifest, False, "manifest_missing_frozen_hash"
        if sha256(self.benchmark_path) != expected_benchmark:
            return manifest, False, "benchmark_hash_mismatch"
        if sha256(self.rubric_path) != expected_rubric:
            return manifest, False, "scoring_hash_mismatch"
        return manifest, True, None

    @staticmethod
    def _counts_are_zero(entry: dict) -> bool:
        return entry.get("cases_started") == 0 and entry.get("cases_completed") == 0

    def preflight(self) -> dict:
        """Read-only eligibility decision. It never creates an attempt."""
        try:
            manifest, hashes_match, hash_error = self._hashes()
            attempts = self._attempts()
        except RuntimeError as error:
            return {
                "frozen_inputs": "UNKNOWN", "run_state": "AMBIGUOUS",
                "previous_valid_results": "UNKNOWN", "execution_eligible": False,
                "reason": str(error),
            }

        if not hashes_match:
            return {
                "frozen_inputs": "MISMATCH", "run_state": "ABORT_BEFORE_FIRST_CASE",
                "previous_valid_results": "NONE", "execution_eligible": False,
                "reason": hash_error, "benchmark_hash": manifest["benchmark"]["sha256"],
                "scoring_hash": manifest["evaluation_configuration"]["rubric_sha256"],
            }

        for entry in attempts:
            status = entry["status"]
            if status in BLOCKING_STATUSES:
                return self._blocked(manifest, status, entry)
            if status == "PREPARED" and not self._counts_are_zero(entry):
                return self._ambiguous(manifest, "prepared_attempt_has_case_counts")
            if status in STARTLESS_TERMINAL and not self._counts_are_zero(entry):
                return self._ambiguous(manifest, "startless_terminal_has_case_counts")
            if status not in STARTLESS_TERMINAL | {"PREPARED"}:
                return self._ambiguous(manifest, "unhandled_ledger_status")

        return {
            "frozen_inputs": "MATCH", "run_state": "PREPARED", "previous_valid_results": "NONE",
            "execution_eligible": True, "authorization_required": True,
            "benchmark_hash": manifest["benchmark"]["sha256"],
            "scoring_hash": manifest["evaluation_configuration"]["rubric_sha256"],
            "prior_attempt_count": len(attempts),
        }

    @staticmethod
    def _blocked(manifest: dict, status: str, entry: dict) -> dict:
        return {
            "frozen_inputs": "MATCH", "run_state": status, "previous_valid_results": "PRESENT"
            if status == "COMPLETED" else "PARTIAL_OR_STARTED",
            "execution_eligible": False, "reason": "prior_execution_state_blocks_rerun",
            "blocking_attempt_id": entry.get("attempt_id", "unknown"),
            "benchmark_hash": manifest["benchmark"]["sha256"],
            "scoring_hash": manifest["evaluation_configuration"]["rubric_sha256"],
        }

    @staticmethod
    def _ambiguous(manifest: dict, reason: str) -> dict:
        return {
            "frozen_inputs": "MATCH", "run_state": "AMBIGUOUS", "previous_valid_results": "UNKNOWN",
            "execution_eligible": False, "reason": reason,
            "benchmark_hash": manifest["benchmark"]["sha256"],
            "scoring_hash": manifest["evaluation_configuration"]["rubric_sha256"],
        }

    def _append(self, entry: dict) -> dict:
        if entry.get("status") not in STATUSES:
            raise ValueError("invalid frozen-run status")
        serialized = json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger_path.open("a", encoding="utf-8") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        return entry

    def prepare_attempt(self, authorization_id: str) -> dict:
        report = self.preflight()
        if not report["execution_eligible"]:
            raise RuntimeError(f"frozen execution is not eligible: {report['run_state']}")
        if not authorization_id or any(marker in authorization_id.lower() for marker in ("api_key", "token", "sk-")):
            raise ValueError("authorization_id is required and must not contain a secret")
        return self._append({
            "attempt_id": f"attempt_{uuid4().hex}", "timestamp": utc_now(),
            "authorization_reference": authorization_id, "benchmark_hash": report["benchmark_hash"],
            "scoring_hash": report["scoring_hash"], "status": "PREPARED",
            "cases_started": 0, "cases_completed": 0, "model_calls_started": "unknown",
            "first_case_id": "unknown", "last_completed_case_id": "unknown",
            "failure_stage": None, "failure_type": None, "valid_results": False,
        })

    def mark_started(self, attempt: dict, case_id: str) -> dict:
        # Re-check frozen inputs at the PREPARED → STARTED boundary, immediately
        # before the runner enters the first real case.
        _manifest, hashes_match, hash_error = self._hashes()
        if not hashes_match:
            raise RuntimeError(f"abort before first case: {hash_error}")
        return self._append({**attempt, "timestamp": utc_now(), "status": "STARTED", "cases_started": 1,
                             "first_case_id": case_id, "failure_stage": None, "failure_type": None})

    def mark_case_completed(self, attempt: dict, case_id: str, completed_count: int) -> dict:
        return self._append({**attempt, "timestamp": utc_now(), "status": "STARTED",
                             "cases_started": max(1, completed_count), "cases_completed": completed_count,
                             "last_completed_case_id": case_id, "failure_stage": None, "failure_type": None})

    def mark_failure_before_first_case(self, attempt: dict, error: BaseException) -> dict:
        return self._append({**attempt, "timestamp": utc_now(), "status": "FAILED_BEFORE_FIRST_CASE",
                             "failure_stage": "before_first_case", "failure_type": type(error).__name__})

    def mark_failure_after_partial_execution(self, attempt: dict, completed_count: int, error: BaseException) -> dict:
        return self._append({**attempt, "timestamp": utc_now(), "status": "FAILED_AFTER_PARTIAL_EXECUTION",
                             "cases_started": max(1, completed_count), "cases_completed": completed_count,
                             "failure_stage": "during_or_after_case_execution", "failure_type": type(error).__name__})

    def mark_completed(self, attempt: dict, completed_count: int, last_case_id: str) -> dict:
        return self._append({**attempt, "timestamp": utc_now(), "status": "COMPLETED",
                             "cases_started": completed_count, "cases_completed": completed_count,
                             "last_completed_case_id": last_case_id, "failure_stage": None,
                             "failure_type": None, "valid_results": True})
