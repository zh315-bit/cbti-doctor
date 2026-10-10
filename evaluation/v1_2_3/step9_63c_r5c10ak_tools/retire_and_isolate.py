"""Step 9.63c-r5c10ak: archive (standing rule) and isolate legacy tests that touch the real activation state.

FULL: the module's original bytes are archived under tests/retired/ and the live file is removed; a
wrapper test module (test_step9_63c_r5c10ak_isolated_*.py) runs the archived module UNCHANGED on a
temporary mirror of the repository (tests/legacy_isolation.py), skipping the listed retired methods.
PARTIAL: the listed methods are removed from the live file; the archive keeps the original bytes.
usage: python retire_and_isolate.py   (repository root; refuses to run twice)
"""
import ast, hashlib, json, shutil, sys
from pathlib import Path

ROOT = Path.cwd(); RET = ROOT / "tests/retired"; INDEX = RET / "RETIRED_INDEX.json"
REWRITE = "tests/test_step9_63c_r5c10ak_legacy_rewrites.py"
AE = "tests/test_step9_63c_r5c10ak_isolated_ae_consumer_precommit_gate.py"
FULL = {
 "test_step9_55a_namespace_lifecycle": {f"NamespaceLifecycleTests.{m}": REWRITE + "::Rewritten55a." + m + " (same body, run on a synthetic temporary root with a synthetic manifest and ledger)" for m in (
    "test_consumed_step954_authorization_cannot_be_reused", "test_failed_step955_attempt_cannot_be_resumed",
    "test_new_future_authorization_and_attempt_pass_preflight", "test_missing_authorization_semantic_state_fails_closed")},
 "test_step9_58a_r1_namespace_allocator": {"NamespaceAllocatorTests.test_reserved_fresh_namespace_requires_transaction_for_post_first_case_guard":
    REWRITE + "::Rewritten58a.test_reserved_fresh_namespace_requires_transaction_for_post_first_case_guard (same body, synthetic temporary root)"},
 "test_step9_59a_auth_identity_binding": {
    "AuthorizationIdentityBindingTests.test_parent_validator_accepts_authoritative_r7_pins": AE + "::test_ConsumerPrecommitGateTests__test_00_consistent_fixture_passes_every_r11_precommit_check; tests/test_step9_63c_r5c10ai_final_form_and_tokens.py::FinalFormSequence (the CURRENT runner's authoritative pins are accepted; r7 is superseded)",
    "AuthorizationIdentityBindingTests.test_preflight_runner_binding_mismatch_fails_closed": AE + "::test_ConsumerPrecommitGateTests__test_formal_entry_or_freeze_binding_mismatch_rejected",
    "AuthorizationIdentityBindingTests.test_preflight_rejects_freeze_hash_not_equal_to_current_runner": AE + "::test_ConsumerPrecommitGateTests__test_formal_entry_or_freeze_binding_mismatch_rejected",
    "AuthorizationIdentityBindingTests.test_actual_preflight_fails_closed_on_stale_validator_runner_pin": AE + "::test_ConsumerPrecommitGateTests__test_frozen_identity_mismatch_rejected",
    "AuthorizationIdentityBindingTests.test_parent_validator_rejects_retired_authorization": "tests/test_step9_63c_r5c10ak_isolated_63a_r2_retirement_eligibility.py::test_SupersededRetirementTests__test_retired_auth_cannot_create_parent_attempt; " + AE + "::test_ConsumerPrecommitGateTests__test_retired_bound_authorization_rejected"},
 "test_step9_63a_r1_production_integration": {"ProductionWiringTests.test_old_r6_authorization_rejected_at_r7_namespace_gate":
    "tests/test_step9_63c_r5c10ak_isolated_63a_r2_retirement_eligibility.py::test_SupersededRetirementTests__test_current_r7_identity_rejects_old_r6_authorization; " + AE + "::test_ConsumerPrecommitGateTests__test_executable_superseded_authorization_rejected"},
 "test_step9_63a_r2_retirement_eligibility": {
    "SupersededRetirementTests.test_active_authorization_count_becomes_zero": "tests/test_step9_63c_r5c10ai_final_form_and_tokens.py::FinalFormSequence (after activation the active set is exactly [the r11 authorization]); tests/test_step9_63c_r5c10ah_retire_entry.py::WriteTests.test_success_appends_exactly_one_approved_line_and_nothing_else",
    "SupersededRetirementTests.test_retired_auth_cannot_enter_prepared_committing_or_committed": "tests/test_step9_63c_r5c10ak_isolated_63a_r2_retirement_eligibility.py::test_SupersededRetirementTests__test_retired_auth_cannot_enter_new_transaction; tests/test_step9_63c_r5c10ak_isolated_r5c5b_lifecycle_reducer.py::test_LifecycleReducerTests__test_10_retirement_and_transaction_conflict_fail_closed"},
 "test_step9_63c_r3_parent_namespace_repair": {}, "test_step9_63c_r5c5b_lifecycle_reducer": {}, "test_step9_63_v3_formal_execution": {},
 "test_step9_28_v4_runner": {}, "test_step9_30a_v4_adjudication": {}, "test_step9_30c_v4_aggregation": {},
 "test_step9_63c_r5c10ae_consumer_precommit_gate": {
    "ConsumerPrecommitGateTests.test_real_r10_authorization_blocks_r11_until_retired": AE + "::test_ConsumerPrecommitGateTests__test_executable_superseded_authorization_rejected (an executable superseded authorization blocks the gate); tests/test_step9_63c_r5c10ah_retire_entry.py::PlanTests.test_rt4_an_already_retired_authorization_blocks",
    "ConsumerPrecommitGateTests.test_unavailable_identity_adapter_fails_closed": AE + "::test_ConsumerPrecommitGateTests__test_missing_key_or_unexecuted_check_fails (a check that cannot run counts as a failure)"},
}
SHORT = {"test_step9_55a_namespace_lifecycle": "55a_namespace_lifecycle", "test_step9_58a_r1_namespace_allocator": "58a_namespace_allocator",
         "test_step9_59a_auth_identity_binding": "59a_auth_identity_binding", "test_step9_63a_r1_production_integration": "63a_r1_production_integration",
         "test_step9_63a_r2_retirement_eligibility": "63a_r2_retirement_eligibility", "test_step9_63c_r3_parent_namespace_repair": "63c_r3_parent_namespace_repair",
         "test_step9_63c_r5c5b_lifecycle_reducer": "r5c5b_lifecycle_reducer", "test_step9_63_v3_formal_execution": "63_v3_formal_execution",
         "test_step9_28_v4_runner": "28_v4_runner", "test_step9_30a_v4_adjudication": "30a_v4_adjudication", "test_step9_30c_v4_aggregation": "30c_v4_aggregation",
         "test_step9_63c_r5c10ae_consumer_precommit_gate": "ae_consumer_precommit_gate"}
PARTIAL = {
 "tests/test_step9_63c_r5c10ag_end_to_end_rehearsal.py": {"FullRehearsal.test_the_rehearsal_never_touches_the_real_repository":
    "tests/test_000_session_guard.py (the session guard now stops ANY write to the real activation state from every test) + evaluation/v1_2_3/step9_63c_r5c10ak_tools/real_state_check.py before/after every run"},
 "tests/test_step9_63c_r5c10ah_end_to_end_gated_rehearsal.py": {"FullSequence.test_the_real_repository_is_not_touched":
    "tests/test_000_session_guard.py + real_state_check.py (same as above)"},
 "tests/test_step9_63c_r5_mac_local_preflight.py": {
    "R8MacLocalPreflightTests.test_existing_artifact_blocks_network": "tests/test_step9_63c_r5c10ad_r5_producer_equivalence.py::R11ProducerArtifactLifecycle.test_T11_duplicate_preflight_id_exclusive_create_fails (the r11 producer's exclusive create)",
    "R8MacLocalPreflightTests.test_pre_post_state_change_fails_closed": "tests/test_step9_63c_r5c10ak_r11_producer_recheck.py (NEW: the r11 producer's PREFLIGHT_BINDING_CHANGED_DURING_PROBE re-check had no test)",
    "R8MacLocalPreflightTests.test_success_fixture_exclusively_writes_only_evidence": "tests/test_step9_63c_r5c10ad_r5_producer_equivalence.py::R11ProducerArtifactLifecycle.test_T3_offline_fixture_only_writes_temp"},
 "tests/test_step9_63c_r5c10ai_test_boundary_manifest.py": {
    "Step963cR5c10aiManifestTests.test_manifest_covers_current_inventory_and_passes_audit": "tests/test_step9_63c_r5c10ak_test_boundary_manifest.py::Step963cR5c10akManifestTests.test_manifest_covers_current_inventory_and_passes_audit (+ test_missing_or_extra_module_is_rejected)",
    "Step963cR5c10aiManifestTests.test_manifest_is_reproducible_from_sources": "tests/test_step9_63c_r5c10ak_test_boundary_manifest.py::Step963cR5c10akManifestTests.test_manifest_is_reproducible_from_sources"},
}
WRAPPER = '''"""Step 9.63c-r5c10ak: {orig} runs UNCHANGED on a temporary mirror of the repository.

The original module (archived as {archive}) exercised production code whose default paths point
at the real activation state (ledger, run root, authorization manifests, namespace lock). Here it runs
inside a private copy (tests/legacy_isolation.py); the methods listed in RETIRED are not run, and their
properties are covered where the mapping says (evaluation/v1_2_3/step9_63c_r5c10ak_coverage_mapping.json).
"""
import legacy_isolation

RETIRED = {retired}

legacy_isolation.make_module(globals(), {orig!r}, retired=RETIRED)
'''


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def remove_methods(path, names):
    src = path.read_text(encoding="utf-8"); tree = ast.parse(src); lines = src.splitlines(keepends=True); spans = []; found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and f"{node.name}.{item.name}" in names:
                    start = min([item.lineno] + [d.lineno for d in item.decorator_list]) - 1
                    spans.append((start, item.end_lineno)); found.add(f"{node.name}.{item.name}")
    assert found == set(names), (path, set(names) - found)
    for start, end in sorted(spans, reverse=True):
        if start > 0 and lines[start - 1].strip() == "":
            start -= 1
        del lines[start:end]
    path.write_text("".join(lines), encoding="utf-8"); ast.parse(path.read_text(encoding="utf-8"))


def archive_name(stem):
    plain = RET / f"{stem}.py.retired"
    return plain if not plain.exists() else RET / f"{stem}.py.r5c10ak.retired"


index = json.loads(INDEX.read_text(encoding="utf-8"))
if any(e["step"].startswith("9.63c-r5c10ak") for e in index["entries"]):
    sys.exit("already done")
entries = []
for stem, retired in FULL.items():
    live = ROOT / "tests" / f"{stem}.py"; arch = archive_name(stem)
    original = sha(live); shutil.copyfile(live, arch); assert sha(arch) == original
    live.unlink()
    wrapper = ROOT / "tests" / f"test_step9_63c_r5c10ak_isolated_{SHORT[stem]}.py"
    wrapper.write_text(WRAPPER.format(orig=stem, archive=arch.relative_to(ROOT).as_posix(),
                                      retired=json.dumps(retired, indent=4, ensure_ascii=False)), encoding="utf-8")
    entries.append({"step": "9.63c-r5c10ak standing rule (isolation of tests that touch the real activation state)",
                    "archive": arch.relative_to(ROOT).as_posix(), "original_path": f"tests/{stem}.py", "archive_sha256": sha(arch),
                    "original_sha256_at_archive": original, "disposition": "FULL: module moved out of the active set; it runs UNCHANGED on a temporary mirror through " + wrapper.relative_to(ROOT).as_posix(),
                    "retired_methods": list(retired), "superseded_by": retired, "coverage_mapping": "evaluation/v1_2_3/step9_63c_r5c10ak_coverage_mapping.json"})
for rel, retired in PARTIAL.items():
    live = ROOT / rel; arch = archive_name(live.stem)
    original = sha(live); shutil.copyfile(live, arch); assert sha(arch) == original
    remove_methods(live, list(retired))
    entries.append({"step": "9.63c-r5c10ak standing rule (superseded tests)", "archive": arch.relative_to(ROOT).as_posix(), "original_path": rel,
                    "archive_sha256": sha(arch), "original_sha256_at_archive": original, "live_sha256_after_removal": sha(live),
                    "disposition": "PARTIAL: the listed methods were removed from the active file; the archive holds the original bytes verbatim",
                    "retired_methods": list(retired), "superseded_by": retired, "coverage_mapping": "evaluation/v1_2_3/step9_63c_r5c10ak_coverage_mapping.json"})
index["entries"].extend(entries)
INDEX.write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps([{k: e[k] for k in ("original_path", "archive", "disposition")} for e in entries], indent=1)[:4000])
