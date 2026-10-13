

# ---------------------------------------------------------------------------
# Packet-specific checks (r11 FINAL pre-registration). Standard library only.
# ---------------------------------------------------------------------------
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

PACKET = Path(__file__).resolve().parent
TEMPLATE = PACKET / "review_template.jsonl"
RAW = PACKET / "v3_run/raw_traces.jsonl"
RESULTS = PACKET / "v3_run/case_results.jsonl"
ORACLE_TARGETS = {"V4-CA-01": "recent_sleep_pattern", "V4-PD-01": "shift_transition_pattern",
                  "V4-PD-03": "bedtime", "V4-PD-09": "nap_duration"}
TOP = {"immutable_execution_facts", "reviewer_judgments", "review_provenance", "execution_provenance"}
PROVENANCE = {"rubric_path", "rubric_sha256", "metric_registry_path", "metric_registry_sha256",
              "reviewer", "review_method", "reviewed_at"}
JUDGMENT_KEYS = {"dimension_scores", "total_score", "completion_judgment", "validity_judgment", "ask_quality",
                 "necessary_ask_preservation", "tool_use_appropriateness", "critical_failure",
                 "harmful_failure", "failure_attribution"}


def _lines(path):
    return [line for line in path.read_bytes().split(b"\n") if line.strip()]


def verify_packet():
    bad = []
    for line in (PACKET / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        target = PACKET / name
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            bad.append(name)
    if bad:
        raise SystemExit("PACKET_MODIFIED_OR_INCOMPLETE: " + ", ".join(bad))


def templates():
    return [json.loads(line) for line in _lines(TEMPLATE)]


def check_record(record, template):
    """Raise RuntimeError with a reason if one completed review record is invalid."""
    case_id = template["immutable_execution_facts"]["case_id"]
    if not isinstance(record, dict) or set(record) != TOP:
        raise RuntimeError("top-level fields must be exactly " + ", ".join(sorted(TOP)))
    if record["immutable_execution_facts"] != template["immutable_execution_facts"]:
        raise RuntimeError("immutable_execution_facts must be copied unchanged from the template")
    if record["execution_provenance"] != template["execution_provenance"]:
        raise RuntimeError("execution_provenance must be copied unchanged from the template")
    provenance = record["review_provenance"]
    if not isinstance(provenance, dict) or set(provenance) != PROVENANCE:
        raise RuntimeError("review_provenance fields must be exactly " + ", ".join(sorted(PROVENANCE)))
    for field in ("rubric_path", "rubric_sha256", "metric_registry_path", "metric_registry_sha256", "review_method"):
        if provenance[field] != template["review_provenance"][field]:
            raise RuntimeError(f"review_provenance.{field} must be copied unchanged from the template")
    if not isinstance(provenance["reviewer"], str) or not provenance["reviewer"].strip():
        raise RuntimeError("review_provenance.reviewer must name the reviewer and model/version")
    try:
        datetime.fromisoformat(str(provenance["reviewed_at"]).replace("Z", "+00:00"))
    except ValueError as error:
        raise RuntimeError("review_provenance.reviewed_at must be an ISO-8601 timestamp") from error
    if not isinstance(record["reviewer_judgments"], dict) or set(record["reviewer_judgments"]) != JUDGMENT_KEYS:
        raise RuntimeError("reviewer_judgments fields must be exactly " + ", ".join(sorted(JUDGMENT_KEYS)))
    _validate_completed_record(record)  # verbatim copy of the frozen contract check (above)
    targets = record["reviewer_judgments"]["necessary_ask_preservation"]["target_adjudications"]
    if case_id in ORACLE_TARGETS:
        if len(targets) != 1 or targets[0]["target_id"] != ORACLE_TARGETS[case_id] or targets[0]["required_by_oracle"] is not True:
            raise RuntimeError(f"{case_id}: target_adjudications must be exactly one entry "
                               f"{{target_id: {ORACLE_TARGETS[case_id]}, required_by_oracle: true, acquired: <bool>}}")
    elif targets != []:
        raise RuntimeError(f"{case_id}: not an oracle necessary-ASK case; target_adjudications must be []")


def check_file(path):
    tpl = templates()
    rows = [json.loads(line) for line in _lines(path)] if path.exists() else []
    if len(rows) > len(tpl):
        raise RuntimeError("more records than cases")
    for index, record in enumerate(rows):
        try:
            check_record(record, tpl[index])
        except Exception as error:
            raise RuntimeError(f"line {index + 1} ({tpl[index]['immutable_execution_facts']['case_id']}): {error}")
    return len(rows), len(tpl)


def main(argv):
    verify_packet()
    if len(argv) == 3 and argv[1] == "check-next":
        out = Path(argv[2])
        written, total = check_file(out)
        if written >= total:
            raise SystemExit("ALL_40_WRITTEN: stop reviewing")
        record = json.loads(sys.stdin.read())
        check_record(record, templates()[written])
        print(f"OK next record valid for line {written + 1} "
              f"({templates()[written]['immutable_execution_facts']['case_id']}); append it as one line")
        return 0
    if len(argv) == 3 and argv[1] == "check-file":
        written, total = check_file(Path(argv[2]))
        print(f"OK {written}/{total} records valid")
        return 0
    print("usage: python3 validate_review.py check-next OUTPUT.jsonl < record.json | check-file OUTPUT.jsonl")
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except RuntimeError as error:
        print("INVALID:", error)
        raise SystemExit(1)
