"""Step 9.63c-r5c10ak: mutation proof for the coverage mapping (standing rule) and for the rewritten tests.

For every retired method, the property it checked is broken in memory (one function of production code
replaced), and the superseding test(s) named in the mapping must fail. Archived modules that host a
superseding test are loaded from tests/retired/ under their original module name and run IN-PROCESS: they
only READ the real repository, and the session guard (installed first) stops the run on any write.
Writes nothing in the repository.  usage: python coverage_mutation.py OUT.json
"""
import importlib.machinery, importlib.util, inspect, json, os, re, sys, textwrap, unittest
from pathlib import Path

sys.path[:0] = [str(Path("tests").resolve()), str(Path(".").resolve())]
import session_safety
session_safety.install()
os.environ.setdefault("CBTI_ALLOW_SYNTHETIC_ROOT", "1")
RET = Path("tests/retired")


def load_archive(stem):
    path = RET / f"{stem}.py.r5c10ak.retired" if (RET / f"{stem}.py.r5c10ak.retired").exists() else RET / f"{stem}.py.retired"
    loader = importlib.machinery.SourceFileLoader(stem, str(path))
    spec = importlib.util.spec_from_loader(stem, loader)
    module = importlib.util.module_from_spec(spec); sys.modules[stem] = module; loader.exec_module(module)
    return module


for stem in ("test_step9_63c_r5c10ae_consumer_precommit_gate", "test_step9_63a_r2_retirement_eligibility", "test_step9_63c_r5c5b_lifecycle_reducer"):
    load_archive(stem)
FORMAL, LC, ADAPTER, PRODUCER = ("scripts.run_step9_63_v3_formal_execution", "scripts.authorization_lifecycle",
                                 "scripts.run_step9_53_v3_identity_adapter", "scripts.preflight_step9_63c_r11_mac_local")
AE = "test_step9_63c_r5c10ae_consumer_precommit_gate.ConsumerPrecommitGateTests."
R2 = "test_step9_63a_r2_retirement_eligibility.SupersededRetirementTests."
R5B = "test_step9_63c_r5c5b_lifecycle_reducer.LifecycleReducerTests."
AI = "test_step9_63c_r5c10ai_final_form_and_tokens.FinalFormSequence"
PE = "test_step9_63c_r5c10ad_r5_producer_equivalence.R11ProducerArtifactLifecycle."
RW = "test_step9_63c_r5c10ak_legacy_rewrites."


def neutralize(name):
    return ("collect_r11_precommit_state", f'check("{name}", lambda:', f'check("{name}", lambda: True or ')


MUTANTS = [
 # (retired test it stands for, label, module, (function, old, new) | ("ATTR", name, value), superseding tests)
 ("59a.test_parent_validator_accepts_authoritative_r7_pins", "current_runner_pins_rejected", FORMAL, ("collect_r11_precommit_state", 'check("agent_match", lambda:', 'check("agent_match", lambda: False and '), [AE + "test_00_consistent_fixture_passes_every_r11_precommit_check"]),
 ("59a.test_preflight_runner_binding_mismatch_fails_closed / test_preflight_rejects_freeze_hash_not_equal_to_current_runner", "runner_freeze_binding_unchecked", FORMAL, neutralize("runner_freeze_match"), [AE + "test_formal_entry_or_freeze_binding_mismatch_rejected"]),
 ("59a.test_actual_preflight_fails_closed_on_stale_validator_runner_pin", "frozen_identities_unchecked", FORMAL, neutralize("frozen_identities_match"), [AE + "test_frozen_identity_mismatch_rejected"]),
 ("59a.test_parent_validator_rejects_retired_authorization", "retired_bound_authorization_accepted", FORMAL, neutralize("authorization_lifecycle_executable"), [AE + "test_retired_bound_authorization_rejected"]),
 ("59a.test_parent_validator_rejects_retired_authorization (parent path)", "retirement_ignored_by_reducer", LC, ("reduce_authorization_lifecycle", "        if retire:\n            return {**evidence, \"derived_state\": RETIRED_STATE,", "        if False:\n            return {**evidence, \"derived_state\": RETIRED_STATE,"), [R2 + "test_retired_auth_cannot_create_parent_attempt", R2 + "test_retired_auth_cannot_enter_new_transaction"]),
 ("63a_r1.test_old_r6_authorization_rejected_at_r7_namespace_gate / ae.test_real_r10_authorization_blocks_r11_until_retired", "executable_superseded_authorization_ignored", FORMAL, neutralize("old_authorization_non_executable"), [AE + "test_executable_superseded_authorization_rejected"]),
 ("63a_r2.test_retired_auth_cannot_enter_prepared_committing_or_committed", "retirement_transaction_conflict_ignored", LC, ("reduce_authorization_lifecycle", "        if retire and (events or attempted or markers):", "        if False:"), [R5B + "test_10_retirement_and_transaction_conflict_fail_closed"]),
 ("63a_r2.test_active_authorization_count_becomes_zero", "active_set_not_computed", LC, ("ATTR", "active_authorizations", "EMPTY"), [AI]),
 ("ae.test_unavailable_identity_adapter_fails_closed", "unexecuted_check_not_a_failure", FORMAL, ("validate_precommit", 'for name in state.get("checks_not_executed", ())', "for name in ()"), [AE + "test_missing_key_or_unexecuted_check_fails"]),
 ("63c_r5.test_existing_artifact_blocks_network", "existing_target_overwritten", PRODUCER, ("write_artifact", "    if path.exists() or path.is_symlink():\n        raise RuntimeError(\"PREFLIGHT_TARGET_EXISTS\")\n", ""), [PE + "test_T11_duplicate_preflight_id_exclusive_create_fails"]),
 ("63c_r5.test_success_fixture_exclusively_writes_only_evidence", "digest_not_of_the_written_bytes", PRODUCER, ("write_artifact", "    return hashlib.sha256(data).hexdigest()", "    return hashlib.sha256(data + b\" \").hexdigest()"), [PE + "test_T12_different_ids_do_not_collide"]),
 ("63c_r5.test_pre_post_state_change_fails_closed", "binding_recheck_removed", PRODUCER, ("main", "        if (refreshed != authorization or sha256_file(refreshed_file) != freeze_sha", "        if False and (refreshed != authorization or sha256_file(refreshed_file) != freeze_sha"), ["test_step9_63c_r5c10ak_r11_producer_recheck"]),
 ("55a.test_consumed_step954_authorization_cannot_be_reused / test_failed_step955_attempt_cannot_be_resumed (REWRITTEN)", "reuse_guard_removed", ADAPTER, ("_validate_namespace_lifecycle", "            if authorization_id == CONSUMED_STEP9_54_AUTHORIZATION_ID or attempt_id == FAILED_STEP9_55_ATTEMPT_ID:\n                raise RuntimeError(\"consumed Step 9.54 authorization or failed Step 9.55 attempt cannot be reused\")", "            pass"), [RW + "Rewritten55a.test_consumed_step954_authorization_cannot_be_reused", RW + "Rewritten55a.test_failed_step955_attempt_cannot_be_resumed"]),
 ("55a.test_missing_authorization_semantic_state_fails_closed (REWRITTEN)", "manifest_requirement_removed", ADAPTER, ("_validate_namespace_lifecycle", "            if authorization_file is None or not authorization_file.is_file():\n                raise RuntimeError(\"new authorization manifest is required for identity preflight\")", "            if False:\n                raise RuntimeError(\"new authorization manifest is required for identity preflight\")"), [RW + "Rewritten55a.test_missing_authorization_semantic_state_fails_closed"]),
 ("55a.test_new_future_authorization_and_attempt_pass_preflight (REWRITTEN, positive control)", "lifecycle_always_rejects", LC, ("assert_executable_authorization", "    if result[\"derived_state\"] != ISSUED_EXECUTABLE or result[\"executable\"] is not True:", "    if True:"), [RW + "Rewritten55a.test_new_future_authorization_and_attempt_pass_preflight"]),
 ("58a.test_reserved_fresh_namespace_requires_transaction_for_post_first_case_guard (REWRITTEN)", "post_first_case_transaction_requirement_removed", ADAPTER, ("_validate_namespace_lifecycle", "requires transaction identity", "XX_REMOVED_XX"), [RW + "Rewritten58a.test_reserved_fresh_namespace_requires_transaction_for_post_first_case_guard"]),
]
results = []
for retired, label, modname, edit, tests in MUTANTS:
    mod = importlib.import_module(modname)
    if edit[0] == "ATTR":
        original = getattr(mod, edit[1]); setattr(mod, edit[1], lambda *a, **k: []); restore = (edit[1], original)
    else:
        func, old, new = edit
        original = getattr(mod, func); src = textwrap.dedent(inspect.getsource(original))
        assert src.count(old) >= 1, (label, old)
        exec(compile(src.replace(old, new, 1), mod.__file__, "exec"), mod.__dict__); restore = (func, original)
    suite = unittest.defaultTestLoader.loadTestsFromNames(tests)
    r = unittest.TextTestRunner(stream=open(os.devnull, "w")).run(suite)
    bad = r.failures + r.errors
    setattr(mod, *restore)
    results.append({"retired_test": retired, "mutant": label, "module": modname, "superseding_tests": tests,
                    "result": "KILLED" if bad else "SURVIVED", "killed_by": bad[0][0].id() if bad else None, "tests_run": r.testsRun})
    print(results[-1]["result"], label, results[-1]["killed_by"] or "", flush=True)
out = {"artifact_type": "R5C10AK_COVERAGE_MUTATION_RESULTS", "total": len(results), "killed": sum(x["result"] == "KILLED" for x in results),
       "survived": [x["mutant"] for x in results if x["result"] == "SURVIVED"], "results": results}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1) + "\n"); print("KILLED", out["killed"], "of", out["total"])
