"""AR-2 style retirement (standing rule, Step 9.63c-r5c10ah): archive the original bytes under
tests/retired/, remove the listed superseded methods from the live file, update RETIRED_INDEX.json.

usage: python retire_methods.py   (run from the repository root; refuses to run twice)
"""
import ast, hashlib, json, shutil, sys
from pathlib import Path

ROOT = Path.cwd()
RETIRED = ROOT / "tests/retired"
INDEX = RETIRED / "RETIRED_INDEX.json"
SUPERSEDED_BY_MANIFEST = "tests/test_step9_63c_r5c10ah_test_boundary_manifest.py"
PLAN = [
 {"file": "tests/test_step9_63c_r5c10ad_test_boundary_manifest.py", "step_of_origin": "9.63c-r5c10ad",
  "methods": {"test_current_manifest_covers_inventory_and_passes_audit": SUPERSEDED_BY_MANIFEST + "::Step963cR5c10ahManifestTests.test_manifest_covers_current_inventory_and_passes_audit (+ test_missing_or_extra_module_is_rejected)",
              "test_manifest_is_reproducible_from_sources": SUPERSEDED_BY_MANIFEST + "::Step963cR5c10ahManifestTests.test_manifest_is_reproducible_from_sources"}},
 {"file": "tests/test_step9_63c_r5c10ae_test_boundary_manifest.py", "step_of_origin": "9.63c-r5c10ae",
  "methods": {"test_manifest_covers_current_inventory_and_passes_audit": SUPERSEDED_BY_MANIFEST + "::Step963cR5c10ahManifestTests.test_manifest_covers_current_inventory_and_passes_audit (+ test_missing_or_extra_module_is_rejected)",
              "test_manifest_is_reproducible_from_sources": SUPERSEDED_BY_MANIFEST + "::Step963cR5c10ahManifestTests.test_manifest_is_reproducible_from_sources"}},
 {"file": "tests/test_step9_63c_r5c10ag_test_boundary_manifest.py", "step_of_origin": "9.63c-r5c10ag",
  "methods": {"test_manifest_covers_current_inventory_and_passes_audit": SUPERSEDED_BY_MANIFEST + "::Step963cR5c10ahManifestTests.test_manifest_covers_current_inventory_and_passes_audit (+ test_missing_or_extra_module_is_rejected)",
              "test_manifest_is_reproducible_from_sources": SUPERSEDED_BY_MANIFEST + "::Step963cR5c10ahManifestTests.test_manifest_is_reproducible_from_sources"}},
 {"file": "tests/test_step9_63c_r5c10ae_builder_pins.py", "step_of_origin": "9.63c-r5c10ae",
  "methods": {"test_pins_equal_reviewed_constants_and_current_bytes": "tests/test_step9_63c_r5c10ah_superseding_tests.py::BuilderPinTests.test_pins_equal_reviewed_constants_and_current_bytes"}},
 {"file": "tests/test_step9_63c_r5c10ae_consumer_precommit_gate.py", "step_of_origin": "9.63c-r5c10ae",
  "methods": {"test_prepare_formal_gates_reports_real_precommit_failures": "tests/test_step9_63c_r5c10ah_superseding_tests.py::ConsumerGateTests (positive control, tampered historical pin, execute_formal stops, missing issuance event)"}},
 {"file": "tests/test_step9_63c_r5c10ag_authorization_issuer.py", "step_of_origin": "9.63c-r5c10ag",
  "methods": {"test_a_manifest_that_reads_back_differently_stops_before_any_event": "tests/test_step9_63c_r5c10ah_issuance_plan_proof.py::ProofTests.test_a_manifest_that_reads_back_differently_stops_before_any_event (+ the pre-write proof tests)"}},
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def remove_methods(path, names):
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    spans, found = [], set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name in names:
                    start = min([item.lineno] + [d.lineno for d in item.decorator_list]) - 1
                    spans.append((start, item.end_lineno)); found.add(item.name)
    assert found == set(names), (path, set(names) - found)
    for start, end in sorted(spans, reverse=True):
        # drop one blank separator line that preceded the method
        while start > 0 and lines[start - 1].strip() == "":
            start -= 1
            break
        del lines[start:end]
    path.write_text("".join(lines), encoding="utf-8")
    ast.parse(path.read_text(encoding="utf-8"))


def main():
    index = json.loads(INDEX.read_text(encoding="utf-8"))
    if any(e.get("step", "").startswith("9.63c-r5c10ah") for e in index["entries"]):
        sys.exit("already retired")
    entries = []
    for item in PLAN:
        live = ROOT / item["file"]
        archive = RETIRED / (live.name + ".retired")
        if archive.exists():
            # an earlier archive of the same original (AR-2) keeps its bytes; ours gets a step-suffixed name
            archive = RETIRED / (live.name + ".r5c10ah.retired")
        original_sha = sha(live)
        shutil.copyfile(live, archive)
        assert sha(archive) == original_sha
        remove_methods(live, list(item["methods"]))
        entries.append({
            "step": "9.63c-r5c10ah standing rule (superseded pin/manifest/gate tests)",
            "archive": archive.relative_to(ROOT).as_posix(), "original_path": item["file"], "origin_step": item["step_of_origin"],
            "archive_sha256": sha(archive), "original_sha256_at_archive": original_sha, "live_sha256_after_removal": sha(live),
            "disposition": "PARTIAL: the listed methods were removed from the active file; the archive holds the original bytes verbatim",
            "retired_methods": list(item["methods"]), "superseded_by": item["methods"],
            "coverage_mapping": "evaluation/v1_2_3/step9_63c_r5c10ah_coverage_mapping.json"})
    index["entries"].extend(entries)
    INDEX.write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps([{k: e[k] for k in ("original_path", "archive", "archive_sha256", "retired_methods")} for e in entries], indent=1))


if __name__ == "__main__":
    main()
