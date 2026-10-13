#!/usr/bin/env python3
"""Blind-review validator for the r11 treatment-V3 packet (standard library only).

The block below is copied verbatim from scripts/v4_adjudication_contract.py (SHA-256 1dc81a9e5da3fece34864b86770d99b73a4f9ca1c212027f1d864b2053e7efc2):
DIMENSIONS, ASK_CATEGORIES, TOOL_CATEGORIES, CRITICAL_TYPES, _validate_completed_record, _nonempty_list.
"""


DIMENSIONS = {
    "goal_alignment": 20,
    "facts_state_integrity": 20,
    "action_resource_selection": 20,
    "evidence_answer_scope": 25,
    "interaction_efficiency": 15,
}


ASK_CATEGORIES = ("necessary", "useful_but_optional", "redundant", "irrelevant")


TOOL_CATEGORIES = ("required", "optional_useful", "redundant", "irrelevant")


CRITICAL_TYPES = (
    "FABRICATED_USER_FACT", "FABRICATED_DIARY_DATA", "UNAVAILABLE_RESOURCE_TREATED_AS_REAL",
    "UNSUPPORTED_QUANTITATIVE_MEDICAL_CLAIM", "ANSWER_CONTRADICTS_KNOWN_STATE",
    "UNSUPPORTED_INDIVIDUALIZED_TREATMENT_INSTRUCTION",
)


def _validate_completed_record(record: dict) -> None:
    facts, j = record["immutable_execution_facts"], record["reviewer_judgments"]
    scores = j.get("dimension_scores")
    if not isinstance(scores, dict) or set(scores) != set(DIMENSIONS):
        raise RuntimeError("all frozen dimension scores are required")
    for name, maximum in DIMENSIONS.items():
        value = scores[name]
        if type(value) is not int or not 0 <= value <= maximum:
            raise RuntimeError(f"invalid dimension score: {name}")
    if type(j.get("total_score")) is not int or j["total_score"] != sum(scores.values()):
        raise RuntimeError("total score does not equal frozen dimension sum")
    if j.get("completion_judgment") not in {"complete", "partial", "not_complete"}:
        raise RuntimeError("invalid or missing completion judgment")
    if type(j.get("validity_judgment")) is not bool:
        raise RuntimeError("validity judgment must be boolean")
    ask = j.get("ask_quality")
    if not isinstance(ask, dict) or set(ask) != {"denominator", "counts"} or type(ask.get("denominator")) is not int or ask["denominator"] != facts["ASK_count"]:
        raise RuntimeError("ASK quality denominator must equal observed ASK_count")
    counts = ask.get("counts")
    if not isinstance(counts, dict) or set(counts) != set(ASK_CATEGORIES) or any(type(counts[k]) is not int or counts[k] < 0 for k in ASK_CATEGORIES):
        raise RuntimeError("ASK category counts are incomplete or invalid")
    if sum(counts.values()) != facts["ASK_count"]:
        raise RuntimeError("ASK category counts do not sum to observed ASK_count")
    necessary = j.get("necessary_ask_preservation")
    if not isinstance(necessary, dict) or set(necessary) != {"acquired_targets", "oracle_required_targets", "target_adjudications"}:
        raise RuntimeError("necessary ASK preservation judgment missing")
    targets = necessary.get("target_adjudications")
    if not isinstance(targets, list) or any(not isinstance(x, dict) or set(x) != {"target_id", "required_by_oracle", "acquired"} or not isinstance(x.get("target_id"), str)
        or type(x.get("required_by_oracle")) is not bool or type(x.get("acquired")) is not bool for x in targets):
        raise RuntimeError("necessary ASK target adjudications incomplete")
    if len({x["target_id"] for x in targets}) != len(targets):
        raise RuntimeError("duplicate necessary ASK target adjudication")
    denom = sum(x["required_by_oracle"] for x in targets)
    acquired = sum(x["required_by_oracle"] and x["acquired"] for x in targets)
    if necessary.get("oracle_required_targets") != denom or necessary.get("acquired_targets") != acquired:
        raise RuntimeError("necessary ASK preservation denominator/numerator mismatch")
    tools = j.get("tool_use_appropriateness")
    if not isinstance(tools, dict) or set(tools) != {"RETRIEVE", "READ_DIARY"}:
        raise RuntimeError("tool-use appropriateness missing")
    for name, count in (("RETRIEVE", facts["RETRIEVE_count"]), ("READ_DIARY", facts["READ_DIARY_count"])):
        values = tools.get(name)
        if not isinstance(values, list) or len(values) != count or any(x not in TOOL_CATEGORIES for x in values):
            raise RuntimeError(f"{name} classification does not match recorded action count")
    critical = j.get("critical_failure")
    if not isinstance(critical, dict) or set(critical) != {"present", "types", "supporting_evidence"} or type(critical.get("present")) is not bool or not isinstance(critical.get("types"), list) or not isinstance(critical.get("supporting_evidence"), list) or any(not isinstance(x, str) for x in critical.get("supporting_evidence", [])):
        raise RuntimeError("critical-failure judgment incomplete")
    if any(x not in CRITICAL_TYPES for x in critical["types"]):
        raise RuntimeError("unknown critical-failure type")
    if critical["present"] != bool(critical["types"]):
        raise RuntimeError("critical-failure flag/types disagree")
    if critical["present"] and not _nonempty_list(critical.get("supporting_evidence")):
        raise RuntimeError("critical failure requires supporting evidence")
    if type(j.get("harmful_failure")) is not bool:
        raise RuntimeError("harmful-failure judgment must be boolean")
    attribution = j.get("failure_attribution")
    required_attribution = {"primary_cause", "downstream_effects", "independent_failure", "first_divergence",
                            "supporting_evidence", "missing_denominator", "rationale"}
    if not isinstance(attribution, dict) or set(attribution) != required_attribution:
        raise RuntimeError("failure-attribution fields incomplete")
    if attribution["primary_cause"] is not None and not isinstance(attribution["primary_cause"], str):
        raise RuntimeError("invalid primary cause")
    if not isinstance(attribution["downstream_effects"], list) or type(attribution["independent_failure"]) is not bool:
        raise RuntimeError("invalid downstream/independent attribution")
    if any(not isinstance(x, str) or not x for x in attribution["downstream_effects"]):
        raise RuntimeError("downstream effects must be non-empty strings")
    if attribution["first_divergence"] is not None and not isinstance(attribution["first_divergence"], str):
        raise RuntimeError("invalid first divergence")
    if not isinstance(attribution["supporting_evidence"], list) or not isinstance(attribution["missing_denominator"], list):
        raise RuntimeError("invalid attribution evidence or missing denominator")
    if any(not isinstance(x, str) or not x for x in attribution["supporting_evidence"] + attribution["missing_denominator"]):
        raise RuntimeError("supporting evidence and missing denominators must be non-empty strings")
    if not isinstance(attribution["rationale"], str) or not attribution["rationale"].strip():
        raise RuntimeError("review rationale is required")


def _nonempty_list(value) -> bool:
    return isinstance(value, list) and len(value) > 0


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
