#!/usr/bin/env python3
"""Contamination scan for the reviewer-sensitivity B packet (read-only; prints JSON).

Checks every packet file for: run identity strings; banned version words (strict outside run/);
any prior review text (baseline 9.30b, V1 9.37, V2 9.46, V3 main review) as 30-char shingles;
V3 run content (final-answer shingles, V3-only trace fields).
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKET = ROOT / "evaluation/v1_2_3/step9_63c_r11_baseline_blind_packet"
REVIEWS = ["evaluation/v1_2_3/step9_30b_v4_human_adjudication.jsonl", "evaluation/v1_2_3/step9_37_treatment_adjudication.jsonl",
           "evaluation/v1_2_3/step9_46_v2_adjudication.jsonl", "evaluation/v1_2_3/step9_63c_r11_blind_review_output/v3_adjudication.jsonl"]
V3_TRACES = "evaluation/v1_2_3/step9_63c_r11_blind_review_packet/v3_run/raw_traces.jsonl"
IDENT = ["heldout-v4-step9_28-20260925-01", "5370d36a64d84a3da4f2585e9b57055a", "7c9d4ba6c7b649e69a64f9b9e68175db",
         "4e2bffea0d7eaa9299074a960df84a1806b3ae9d4930662929abc58ca5b2ae79", "e5e4841b51ecc6bced0f342a261a356756d07b39764670d774b910b86b8625a7",
         "b9e891e7cd077dd5b3c6fa72b71faad978a24226c2b5e89e0b06aabde93b51d6", "085d338ed95bbef7370c41cf97ca0d6653ffdfd2f1c924eef4b7123dfdea4607",
         "heldout-v4-step9_55a-treatment-v3", "attempt-step9_63c_r11", "auth-step9_63c_r11", "heldout-v4-step9_34a", "heldout-v4-step9_43"]
WORDS = {"baseline": r"(?i)baseline", "基线": r"基线", "9.28": r"9\.28|9_28|step9_28", "29b": r"step9_29b",
         "codex": r"(?i)codex", "v3": r"(?i)\bv3\b|v3_", "treatment": r"(?i)(?<!INDIVIDUALIZED_)treatment", "r11": r"(?i)\br11\b"}
V3_ONLY_FIELDS = ["answer_authorization", "answer_generation_audit", "trace_schema_version"]


def review_shingles():
    texts = set()
    for path in REVIEWS:
        for line in (ROOT / path).read_text(encoding="utf-8").splitlines():
            def walk(o):
                if isinstance(o, dict):
                    for k, v in o.items():
                        if k not in ("immutable_execution_facts", "execution_provenance", "review_provenance"):
                            walk(v)
                elif isinstance(o, list):
                    for v in o:
                        walk(v)
                elif isinstance(o, str) and len(o) >= 30:
                    texts.add(o)
            walk(json.loads(line))
    return texts, {t[i:i + 30] for t in texts for i in range(0, max(1, len(t) - 30), 15)}


def v3_answer_shingles():
    out = set()
    for line in (ROOT / V3_TRACES).read_text(encoding="utf-8").splitlines():
        answer = json.loads(line).get("final_answer") or ""
        out.update(answer[i:i + 30] for i in range(0, max(1, len(answer) - 30), 15) if len(answer) >= 30)
    return out


def main():
    texts, shingles = review_shingles()
    v3_sh = v3_answer_shingles()
    report = {"prior_review_strings": len(texts), "prior_review_shingles": len(shingles), "v3_answer_shingles": len(v3_sh), "files": {}}
    for path in sorted(p for p in PACKET.rglob("*") if p.is_file() and not p.name.startswith("._")):
        name = path.relative_to(PACKET).as_posix()
        text = path.read_text(encoding="utf-8")
        words = {}
        for key, pattern in WORDS.items():
            matches = list(re.finditer(pattern, text))
            if matches:
                words[key] = {"count": len(matches),
                              "samples": sorted({text[max(0, m.start() - 50):m.end() + 40].replace("\n", " ") for m in matches})[:4]}
        report["files"][name] = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "identity_hits": {i: text.count(i) for i in IDENT if text.count(i)},
            "version_word_hits": words,
            "prior_review_shingle_hits": sorted(s for s in shingles if s in text)[:10],
            "v3_answer_shingle_hits": len([s for s in v3_sh if s in text]),
            "v3_only_field_hits": {f: text.count(f) for f in V3_ONLY_FIELDS if text.count(f)},
        }
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
