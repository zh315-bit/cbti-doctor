"""In-memory behavioural mutation of the r11 builder, issuer and consumer. Writes nothing in the repository.

Each mutant replaces one function's source in memory (parent process and, for command-line
entries, the child process too). Source-inspection tests are excluded from kill attribution.
usage: python ag_mutation.py <group> <out.json>   (group: builder | issuer | consumer | all)
"""
import importlib, inspect, json, os, sys, textwrap, unittest, time
sys.path[:0] = [".", "tests"]
import r11_activation_fixtures as fx

BUILDER, ISSUER, FORMAL = ("scripts.build_step9_63c_r11_runner_freeze", "scripts.issue_step9_63c_r11_authorization",
                           "scripts.run_step9_63_v3_formal_execution")
P = "test_step9_63c_r5c10ag_identity_pointer_creation"
I = "test_step9_63c_r5c10ag_authorization_issuer"
C = "test_step9_63c_r5c10ag_consumer_issuance_crosscheck"
E = "test_step9_63c_r5c10ag_end_to_end_rehearsal"
EXCLUDED = {  # source-inspection tests: not counted as mutation evidence
    P + ".PointerWriteGateTests.test_builder_source_contains_no_delete_or_replace_primitive",
    P + ".PersistedFreezeTests.test_allow_existing_target_is_only_used_by_the_verification_path",
}
BOOT = ("import sys,json,importlib,inspect,textwrap\n"
        "spec=json.loads(sys.argv[1]);cli=importlib.import_module(sys.argv[2])\n"
        "m=importlib.import_module(spec['module']);src=textwrap.dedent(inspect.getsource(getattr(m,spec['func'])))\n"
        "for o,n in spec['edits']:\n    assert src.count(o)==1,o\n    src=src.replace(o,n)\n"
        "exec(compile(src,m.__file__,'exec'),m.__dict__)\n"
        "sys.argv=[sys.argv[2]]+sys.argv[3:]\nraise SystemExit(cli.main())\n")

def M(label, module, func, edits, tests, note=""):
    if isinstance(edits, tuple): edits = [edits]
    return dict(label=label, module=module, func=func, edits=edits, tests=tests, note=note)

PA, PG = [P], [P, I]
MUTANTS = {
"builder": [
 M("B1_terminal_check_removed", BUILDER, "require_write_environment", ("    if not interactive_terminal():", "    if False:"), PG),
 M("B2_synthetic_switch_check_removed", BUILDER, "require_write_environment", ('    elif os.environ.get(SYNTHETIC_ROOT_ENV) != "1":', "    elif False:"), PG),
 M("B3_token_check_removed", BUILDER, "confirm_with_token", ("    if typed.strip() != expected:", "    if False:"), PG),
 M("B4_token_case_insensitive", BUILDER, "confirm_with_token", ("typed.strip() != expected", "typed.strip().lower() != expected.lower()"), PA),
 M("B5_exclusive_create_becomes_truncate", BUILDER, "_write_exclusive", ("os.O_CREAT | os.O_EXCL | os.O_WRONLY", "os.O_CREAT | os.O_TRUNC | os.O_WRONLY"), PA),
 M("B6_pointer_readback_removed", BUILDER, "create_identity_pointer", ("if target.read_bytes() != data or sha256_file(target) != POINTER_SHA256:", "if False:"), PA),
 M("B7a_prelock_plan_check_removed", BUILDER, "create_identity_pointer", ('    if not plan["ready"]:', "    if False:"), PA, "redundant with the in-lock re-check"),
 M("B7b_inlock_recheck_removed", BUILDER, "create_identity_pointer", ('        if not again["ready"]:', "        if False:"), PA, "redundant with the pre-lock check and O_EXCL"),
 M("B7c_both_plan_checks_removed", BUILDER, "create_identity_pointer", [('    if not plan["ready"]:', "    if False:"), ('        if not again["ready"]:', "        if False:")], PA),
 M("B8_write_gate_removed_from_create", BUILDER, "create_identity_pointer", ('    require_write_environment(root, "create the r11 identity pointer")  # first: no side effect before the gate', "    pass"), PG),
 M("B9_confirmation_removed_from_create", BUILDER, "create_identity_pointer", ('    confirm_with_token(POINTER_TOKEN, "complete the r11 pointer creation record" if resume else "create the r11 identity pointer")', "    pass"), PA),
 M("PP1_existing_artifacts_ignored", BUILDER, "pointer_preconditions", ("not any(_artifact_present(root / p) for p in (IDENTITY_CONFIG_PATH, EXPECTED_FREEZE_PATH,", "not any(False for p in (IDENTITY_CONFIG_PATH, EXPECTED_FREEZE_PATH,"), PA),
 M("PP2a_signature_not_required", BUILDER, "pointer_preconditions", ("verify_approval(root, approval, check_aggregate=not resume)", "verify_approval(root, approval, require_signed=False, check_aggregate=not resume)"), PA),
 M("PP2b_aggregate_not_checked", BUILDER, "pointer_preconditions", ("verify_approval(root, approval, check_aggregate=not resume)", "verify_approval(root, approval, check_aggregate=False)"), PA),
 M("PP4a_missing_retirement_event_ignored", BUILDER, "pointer_preconditions", ("        if event is None:", "        if False:"), PA),
 M("PP4b_reducer_executable_ignored", BUILDER, "pointer_preconditions", ("""return result["executable"] is False, f"reducer state {result['derived_state']}\"""", 'return True, ""'), PA),
 M("PP4ab_PP5_all_executability_checks_removed", BUILDER, "pointer_preconditions", [("        if event is None:", "        if False:"), ("""return result["executable"] is False, f"reducer state {result['derived_state']}\"""", 'return True, ""'), ('all(r["executable"] is False for r in rows)', "True")], PA),
 M("PP5_executable_superseded_ignored", BUILDER, "pointer_preconditions", ('all(r["executable"] is False for r in rows)', "True"), PA),
 M("PP6_historical_pins_ignored", BUILDER, "pointer_preconditions", ("formal.verify_historical_pins(root) == formal.HISTORICAL_PIN_COUNT", "True"), PA),
 M("PP7_transaction_journal_ignored", BUILDER, "pointer_preconditions", ("if (root / TRANSACTION_RELATIVE).exists() else True", "if False else True"), PA),
 M("PP9_environment_ignored", BUILDER, "pointer_preconditions", ('return os.environ.get(SYNTHETIC_ROOT_ENV) == "1", f"synthetic', 'return True, f"synthetic'), PA),
 M("AP1_status_not_checked", BUILDER, "verify_approval", ('        if approval.get("status") != APPROVAL_SIGNED:', "        if False:"), PA),
 M("AP2_approver_not_checked", BUILDER, "verify_approval", ('if not isinstance(approval.get("approver"), str) or not approval.get("approver"):', "if False:"), PA),
 M("AP3_signing_time_not_checked", BUILDER, "verify_approval", ("            datetime.fromisoformat(approval.get(\"signed_at_utc\"))", "            pass"), PA),
 M("AP4_pointer_pin_not_checked", BUILDER, "verify_approval", ('if (pointer.get("canonical_sha256") != POINTER_SHA256 or pointer.get("canonical_size") != POINTER_SIZE', 'if (False and pointer.get("canonical_sha256") != POINTER_SHA256 or False and pointer.get("canonical_size") != POINTER_SIZE'), PA),
 M("AP5_member_list_not_checked", BUILDER, "verify_approval", ("    if set(pinned) != set(MEMBER_PATHS):", "    if False:"), PA),
 M("AP6_member_pin_not_checked", BUILDER, "verify_approval", ("        if pinned.get(path) != sha:", "        if False:"), PA),
 M("AP7_named_pin_not_checked", BUILDER, "verify_approval", ('        if current.get(entry.get("path")) != entry.get("sha256"):', "        if False:"), PA),
 M("AP8_issuer_pin_not_checked", BUILDER, "verify_approval", ("    if current.get(ISSUER_PATH) != ISSUER_SHA256:", "    if False:"), PA),
 M("AP9_r10_manifest_pin_not_checked", BUILDER, "verify_approval", ('    if sha256_file(root / PARENT_PATH) != history.get("r10_freeze_manifest", {}).get("sha256") or PARENT_SHA256 != history.get("r10_freeze_manifest", {}).get("sha256"):', "    if False:"), PA),
 M("AP10_regression_result_not_checked", BUILDER, "verify_approval", ('if not result.is_file() or sha256_file(result) != regression.get("result_sha256"):', "if False:"), PA),
 M("AP11_aggregate_not_checked", BUILDER, "verify_approval", ('        if repository_aggregate(root)["sha256"] != aggregate.get("sha256"):', "        if False:"), PA),
 M("FZ1_persisted_freeze_always_ok", BUILDER, "verify_persisted_candidate", ('return {"ok": expected == data,', 'return {"ok": True,'), PA + [I]),
 M("FZ2_assemble_ignores_issuer_pin", BUILDER, "assemble_candidate", ("if relpath == ISSUER_PATH and digest != ISSUER_SHA256:", "if False:"), PA),
],
"issuer": [
 M("I0_approval_not_verified", ISSUER, "issuance_conditions", ("builder.verify_approval(root, approval, check_aggregate=False)", "[]"), [I]),
 M("I1a_pointer_sha_vs_approval_ignored", ISSUER, "issuance_conditions", ('and sha256_file(pointer) == (approval or {}).get("pointer", {}).get("canonical_sha256")', "and True"), [I], "pointer bytes are also compared with the canonical bytes"),
 M("I1b_record_approval_binding_ignored", ISSUER, "issuance_conditions", ('and rec.get("approval_record_sha256") == sha256_file(approval_file))', "and True)"), [I]),
 M("I1c_record_pointer_binding_ignored", ISSUER, "issuance_conditions", ('rec.get("pointer_sha256") == builder.POINTER_SHA256', "True"), [I], "redundant: pointer bytes are compared with the canonical bytes directly"),
 M("I3_freeze_vs_prediction_ignored", ISSUER, "issuance_conditions", ('resolution_ok and sha256_file(context["freeze_path"]) == approval["freeze"]["predicted_sha256"]', "resolution_ok"), [I]),
 M("I4_persisted_freeze_not_reassembled", ISSUER, "issuance_conditions", ('lambda r: (r["ok"], r["reason"])', 'lambda r: (True, r["reason"])'), [I]),
 M("I5a_changed_member_pins_ignored", ISSUER, "issuance_conditions", ("            if sha256_file(root / path) != sha:", "            if False:"), [I], "redundant: the freeze resolution (I2) and the approval (I0) pin the same bytes"),
 M("I5b_issuer_pin_ignored", ISSUER, "issuance_conditions", ("        if sha256_file(root / ISSUER_PATH) != builder.ISSUER_SHA256 or sha256_file(Path(__file__)) != builder.ISSUER_SHA256:", "        if False:"), [I], "redundant: the freeze resolution (I2) and the approval (I0) pin the same bytes"),
 M("I6_executable_superseded_ignored", ISSUER, "issuance_conditions", ('all(r["executable"] is False for r in rows)', "True"), [I]),
 M("I7_active_set_ignored", ISSUER, "issuance_conditions", ('return active == [], f"active={active} (must be empty before issuance)"', 'return True, ""'), [I]),
 M("I8_historical_pins_ignored", ISSUER, "issuance_conditions", ("lambda: formal.verify_historical_pins(root) == formal.HISTORICAL_PIN_COUNT", "lambda: True"), [I]),
 M("I9a_identity_bytes_scan_removed", ISSUER, "issuance_conditions", ("            if any(token in data for token in tokens):", "            if False:"), [I]),
 M("I9b_namespace_collision_ignored", ISSUER, "issuance_conditions", ("        if namespace.exists() or namespace.is_symlink():", "        if False:"), [I]),
 M("I9c_frozen_freshness_helper_removed", ISSUER, "issuance_conditions", ("            lifecycle.assert_fresh_authorization_identity(", "            (lambda **kw: None)("), [I], "the helper's ledger and attempt checks are partly covered by I9a's byte scan"),
 M("I9ab_scan_and_namespace_removed", ISSUER, "issuance_conditions", [("            if any(token in data for token in tokens):", "            if False:"), ("        if namespace.exists() or namespace.is_symlink():", "        if False:")], [I], "I9c (frozen helper) still covers the namespace; see I9abc"),
 M("I9abc_all_uniqueness_checks_removed", ISSUER, "issuance_conditions", [("            if any(token in data for token in tokens):", "            if False:"), ("        if namespace.exists() or namespace.is_symlink():", "        if False:"), ("            lifecycle.assert_fresh_authorization_identity(", "            (lambda **kw: None)(")], [I]),
 M("I10_existing_manifest_ignored", ISSUER, "issuance_conditions", ("lambda: not (target.exists() or target.is_symlink())", "lambda: True"), [I]),
 M("I12a_clock_not_compared", ISSUER, "issuance_conditions", ("ok = issued > created and (last is None or issued > last)", "ok = True"), [I]),
 M("I12b_freeze_time_not_compared", ISSUER, "issuance_conditions", ("ok = issued > created and (last is None or issued > last)", "ok = (last is None or issued > last)"), [I]),
 M("I12c_last_event_not_compared", ISSUER, "issuance_conditions", ("ok = issued > created and (last is None or issued > last)", "ok = issued > created"), [I]),
 M("I13a_prior_event_ignored", ISSUER, "issuance_conditions", ("not issued_events(root) and not (root / builder.REGISTRY_PATH).exists()", "not (root / builder.REGISTRY_PATH).exists()"), [I]),
 M("I13b_registry_ignored", ISSUER, "issuance_conditions", ("not issued_events(root) and not (root / builder.REGISTRY_PATH).exists()", "not issued_events(root)"), [I]),
 M("IX1_environment_ignored", ISSUER, "issuance_conditions", ('(lambda ok: (ok, "production root" if builder.is_production_root(root) else "synthetic root"))(', '(lambda ok: (True, "x"))('), [I]),
 M("G1_write_gate_removed", ISSUER, "issue_authorization", ('    builder.require_write_environment(root, "issue the r11 authorization")  # gate before any work', "    pass"), [I]),
 M("G2_confirmation_removed", ISSUER, "issue_authorization", ('    builder.confirm_with_token(plan["confirmation_token"],', '    (lambda *a, **k: None)(plan["confirmation_token"],'), [I]),
 M("G3_inlock_conditions_removed", ISSUER, "issue_authorization", ('        if not all(c["ok"] for c in conditions):', "        if False:"), [I], "redundant with the pre-lock plan and O_EXCL; only a race can show it"),
 M("G4_manifest_readback_removed", ISSUER, "issue_authorization", ("        if target.read_bytes() != data:", "        if False:"), [I]),
 M("G5_postcondition_removed", ISSUER, "issue_authorization", ('        if active_after != [manifest["authorization_id"]]:', "        if False:"), [I]),
 M("G6_prelock_plan_check_removed", ISSUER, "issue_authorization", ('    if not plan["ready"]:', "    if False:"), [I], "redundant with the in-lock conditions"),
 M("G7_both_plan_checks_removed", ISSUER, "issue_authorization", [('    if not plan["ready"]:', "    if False:"), ('        if not all(c["ok"] for c in conditions):', "        if False:")], [I]),
 M("T1_token_constant", ISSUER, "issue_token", ('return f"ISSUE-R11-AUTH-{digest[:12]}"', 'return "ISSUE-R11-AUTH-000000000000"'), [I]),
 M("T2_token_ignores_authorization_id", ISSUER, "issue_token", ('f"{authorization_id}|{freeze_sha256}|{approval_sha256}"', 'f"{freeze_sha256}|{approval_sha256}"'), [I], "the freeze and approval hashes already change with the identities"),
 M("S1_duplicate_events_not_detected", ISSUER, "issuance_status", ("    if len(events) > 1:", "    if False:"), [I, E]),
 M("S2_non_regular_manifest_not_detected", ISSUER, "issuance_status", ("    if manifest.is_symlink() or not manifest.is_file():", "    if False:"), [I]),
 M("S3_event_mismatch_not_detected", ISSUER, "issuance_status", ('"ISSUED_RECORDED" if recorded else "ANOMALY_EVENT_MISMATCH"', '"ISSUED_RECORDED"'), [I]),
 M("R1_complete_record_state_check_removed", ISSUER, "complete_issuance_record", ('    if issuance_status(root)["state"] != "ISSUED_UNRECORDED":\n        raise RuntimeError("nothing to complete', '    if False:\n        raise RuntimeError("nothing to complete'), [I]),
 M("R2_complete_record_identity_check_removed", ISSUER, "complete_issuance_record", ('if (manifest["authorization_id"], manifest["attempt_id"]) != (approval["issuance"]["authorization_id"], approval["issuance"]["attempt_id"]):', "if False:"), [I]),
 M("R3_complete_record_gate_removed", ISSUER, "complete_issuance_record", ('    builder.require_write_environment(root, "complete the r11 issuance record")', "    pass"), [I]),
 M("R4_complete_record_confirmation_removed", ISSUER, "complete_issuance_record", ('    builder.confirm_with_token(complete_token(manifest_sha), "complete the r11 issuance record")', "    pass"), [I]),
 M("A1_approval_path_override_allowed", ISSUER, "_canonical_approval_only", ("    if approval_path is not None:", "    if False:"), [I]),
 M("V1_verify_state_ignored", ISSUER, "verify_issuance", ('lambda: (status["state"] == "ISSUED_RECORDED", status["state"])', 'lambda: (True, "")'), [I, E]),
],
"consumer": [
 M("F1_duplicate_events_allowed", FORMAL, "verify_issuance_event", ("    if len(mine) != 1:", "    if False:"), [C]),
 M("F2_attempt_reuse_allowed", FORMAL, "verify_issuance_event", ("if any(other is not event and", "if False and any(other is not event and"), [C]),
 M("F3_field_differences_ignored", FORMAL, "verify_issuance_event", ("    if differing:", "    if False:"), [C]),
 M("F4_missing_event_not_detected", FORMAL, "verify_issuance_event", ("    if not mine:", "    if False:"), [C], "an IndexError follows, which the gate also treats as a failure"),
] + [
 M(f"F5_{key}_not_compared", FORMAL, "verify_issuance_event", (f'        "{key}": {old},', f'        "{key}": event.get("{key}"),'), [C])
 for key, old in (("authorization_id", "authorization_id"), ("attempt_id", 'authorization.get("attempt_id")'),
                  ("evaluation_id", 'authorization.get("evaluation_id")'), ("authorization_manifest_path", "manifest_path"),
                  ("authorization_manifest_sha256", "sha256(authorization_file)"),
                  ("runner_freeze_revision", 'authorization.get("runner_freeze_revision")'),
                  ("runner_freeze_sha256", 'authorization.get("runner_freeze_sha256")'),
                  ("authorization_consumed", "False"), ("authorization_consumption_count", "0"))
] + [
 M("F6_cross_check_always_passes", FORMAL, "validate_issuance_cross_check", ("return [] if state.get(ISSUANCE_KEY) is True else [ISSUANCE_KEY]", "return []"), [C]),
 M("F7_cross_check_not_wired_into_gate", FORMAL, "prepare_formal_gates", ("    failures += [name for name in validate_issuance_cross_check(state) if name not in failures]", "    pass"), [C, E]),
 M("F8_state_check_forced_true", FORMAL, "collect_r11_precommit_state", ("    check(ISSUANCE_KEY, issuance_recorded)", "    check(ISSUANCE_KEY, lambda: True)"), [C, E]),
 M("F9_truthy_instead_of_true", FORMAL, "validate_issuance_cross_check", ("is True else", "else") , [C], "state value type strictness"),
 M("F10_gate_does_not_stop_execution", FORMAL, "execute_formal", ('    if gates["precommit_failures"]:', "    if False:"), [C]),
],
}

def load_tests(names):
    loader, suite = unittest.defaultTestLoader, unittest.TestSuite()
    def flatten(s):
        for t in s:
            yield from flatten(t) if isinstance(t, unittest.TestSuite) else [t]
    for name in names:
        for t in flatten(loader.loadTestsFromName(name)):
            if t.id() not in EXCLUDED: suite.addTest(t)
    return suite

def main():
    group, out = sys.argv[1], sys.argv[2]
    import io
    sys.stdin = io.StringIO("")   # a mutant that removes a gate must hit EOF, never wait on a person
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    groups = ["builder", "issuer", "consumer"] if group == "all" else [group]
    mods = {n: importlib.import_module(n) for n in (P, I, C, E)}
    for m in mods.values():                    # build the templates once, with unmutated code
        m.setUpModule(); tear = m.tearDownModule; m.setUpModule = lambda: None; m.tearDownModule = lambda: None; m._tear = tear
    results, originals = [], {}
    for g in groups:
        for mutant in MUTANTS[g]:
            mod = importlib.import_module(mutant["module"])
            original = getattr(mod, mutant["func"])
            src = textwrap.dedent(inspect.getsource(original))
            for old, new in mutant["edits"]:
                assert src.count(old) == 1, (mutant["label"], old, src.count(old))
                src = src.replace(old, new)
            exec(compile(src, mod.__file__, "exec"), mod.__dict__)
            spec = json.dumps({"module": mutant["module"], "func": mutant["func"], "edits": mutant["edits"]})
            fx.build_command = lambda module, root, args, spec=spec: [sys.executable, "-c", BOOT, spec, module, "--root", str(root), *args]
            t0 = time.time()
            result = unittest.TextTestRunner(stream=open(os.devnull, "w"), failfast=True).run(load_tests(mutant["tests"]))
            bad = (result.failures + result.errors)
            results.append({"group": g, "mutant": mutant["label"], "function": f"{mutant['module'].split('.')[-1]}.{mutant['func']}",
                            "result": "KILLED" if bad else "SURVIVED", "killed_by": bad[0][0].id() if bad else None,
                            "note": mutant["note"], "seconds": round(time.time() - t0, 1)})
            setattr(mod, mutant["func"], original)
            print(results[-1]["result"], mutant["label"], results[-1]["killed_by"] or "", flush=True)
    for m in mods.values(): m._tear()
    json.dump({"artifact_type": "R5C10AG_MUTATION_RESULTS", "total": len(results),
               "killed": sum(r["result"] == "KILLED" for r in results),
               "survived": [r["mutant"] for r in results if r["result"] == "SURVIVED"],
               "source_inspection_tests_excluded": sorted(EXCLUDED), "results": results}, open(out, "w"), indent=1)
    print("KILLED", sum(r["result"] == "KILLED" for r in results), "of", len(results))

if __name__ == "__main__":
    main()
