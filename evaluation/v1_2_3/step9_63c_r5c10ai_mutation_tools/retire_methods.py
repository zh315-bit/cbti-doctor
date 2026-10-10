"""AR-2 style retirement (standing rule, Step 9.63c-r5c10ai): archive the original bytes under
tests/retired/, remove the listed superseded methods from the live file, update RETIRED_INDEX.json.

usage: python retire_methods.py   (run from the repository root; refuses to run twice)
"""
import ast, hashlib, json, shutil, sys
from pathlib import Path

ROOT = Path.cwd()
RETIRED = ROOT / "tests/retired"
INDEX = RETIRED / "RETIRED_INDEX.json"
SUPERSEDED_BY_MANIFEST = "tests/test_step9_63c_r5c10ai_test_boundary_manifest.py"
PLAN = [
 {"file": "tests/test_step9_63c_r5c10ad_v2_archival_replay.py", "step_of_origin": "9.63c-r5c10ad", "full": True,
  "methods": {"test_head_blobs_equal_v2_pins_and_differ_from_working_tree": "tests/test_step9_63c_r5c10ai_v2_archival_replay.py::V2ArchivalReplayTests.test_archival_blobs_equal_v2_pins_and_differ_from_working_tree",
              "test_01a_frozen_v2_identity_preflight_passes_on_archived_bytes": "tests/test_step9_63c_r5c10ai_v2_archival_replay.py::V2ArchivalReplayTests.test_01a_frozen_v2_identity_preflight_passes_on_archived_bytes (+ ancestry tests)"}},
 {"file": "tests/test_step9_63c_r5c10ah_retire_entry.py", "step_of_origin": "9.63c-r5c10ah",
  "methods": {"test_clean_s0_with_a_signed_approval_is_ready_and_writes_nothing": "tests/test_step9_63c_r5c10ai_final_form_and_tokens.py::TokenTests (the retirement token is now RETIRE-R10-<uuid part of the r10 id, 12 hex>-<approval content hash, 12 hex>)"}},
 {"file": "tests/test_step9_63c_r5c10ah_test_boundary_manifest.py", "step_of_origin": "9.63c-r5c10ah",
  "methods": {"test_manifest_covers_current_inventory_and_passes_audit": SUPERSEDED_BY_MANIFEST + "::Step963cR5c10aiManifestTests.test_manifest_covers_current_inventory_and_passes_audit (+ test_missing_or_extra_module_is_rejected)",
              "test_manifest_is_reproducible_from_sources": SUPERSEDED_BY_MANIFEST + "::Step963cR5c10aiManifestTests.test_manifest_is_reproducible_from_sources"}},
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
    if any(e.get("step", "").startswith("9.63c-r5c10ai") for e in index["entries"]):
        sys.exit("already retired")
    entries = []
    for item in PLAN:
        live = ROOT / item["file"]
        archive = RETIRED / (live.name + ".retired")
        if archive.exists():
            # an earlier archive of the same original (AR-2) keeps its bytes; ours gets a step-suffixed name
            archive = RETIRED / (live.name + ".r5c10ai.retired")
        original_sha = sha(live)
        shutil.copyfile(live, archive)
        assert sha(archive) == original_sha
        if item.get("full"):
            live.unlink()  # FULL: the module leaves the active set; the archive keeps its bytes
        else:
            remove_methods(live, list(item["methods"]))
        entries.append({
            "step": "9.63c-r5c10ai standing rule (superseded pin/manifest/gate tests)",
            "archive": archive.relative_to(ROOT).as_posix(), "original_path": item["file"], "origin_step": item["step_of_origin"],
            "archive_sha256": sha(archive), "original_sha256_at_archive": original_sha, "live_sha256_after_removal": sha(live) if live.exists() else None,
            "disposition": ("FULL: module moved out of the active test set" if item.get("full") else "PARTIAL: the listed methods were removed from the active file") + "; the archive holds the original bytes verbatim",
            "retired_methods": list(item["methods"]), "superseded_by": item["methods"],
            "coverage_mapping": "evaluation/v1_2_3/step9_63c_r5c10ai_coverage_mapping.json"})
    index["entries"].extend(entries)
    INDEX.write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps([{k: e[k] for k in ("original_path", "archive", "archive_sha256", "retired_methods")} for e in entries], indent=1))


if __name__ == "__main__":
    main()
