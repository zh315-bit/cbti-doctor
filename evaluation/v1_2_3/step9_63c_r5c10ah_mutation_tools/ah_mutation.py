"""In-memory behavioural mutation of the r11 builder, issuer and consumer. Writes nothing in the repository.

Each mutant replaces one function's source in memory (parent process and, for command-line
entries, the child process too). Source-inspection tests are excluded from kill attribution.
usage: python ah_mutation.py <group> <out.json>   (group: retire | freeze | proof | superseding | all)
"""
import importlib, inspect, json, os, sys, textwrap, unittest, time
sys.path[:0] = [".", "tests"]
import r11_activation_fixtures as fx

BUILDER, ISSUER, FORMAL = ("scripts.build_step9_63c_r11_runner_freeze", "scripts.issue_step9_63c_r11_authorization",
                           "scripts.run_step9_63_v3_formal_execution")
R = "test_step9_63c_r5c10ah_retire_entry"
F = "test_step9_63c_r5c10ah_freeze_entry"
H = "test_step9_63c_r5c10ah_issuance_plan_proof"
X = "test_step9_63c_r5c10ah_end_to_end_gated_rehearsal"
SUP = "test_step9_63c_r5c10ah_superseding_tests"
MAN = "test_step9_63c_r5c10ah_test_boundary_manifest"
EXCLUDED = set()  # no source-inspection tests in the r5c10ah modules
AH_VALIDATOR = "scripts.validate_step9_63c_r5c10ah_test_boundary"
BASE_VALIDATOR = "scripts.validate_step9_63c_test_boundary"
BOOT = ("import sys,json,importlib,inspect,textwrap\n"
        "spec=json.loads(sys.argv[1]);cli=importlib.import_module(sys.argv[2])\n"
        "m=importlib.import_module(spec['module']);src=textwrap.dedent(inspect.getsource(getattr(m,spec['func'])))\n"
        "for o,n in spec['edits']:\n    assert src.count(o)==1,o\n    src=src.replace(o,n)\n"
        "exec(compile(src,m.__file__,'exec'),m.__dict__)\n"
        "sys.argv=[sys.argv[2]]+sys.argv[3:]\nraise SystemExit(cli.main())\n")

def M(label, module, func, edits, tests, note=""):
    if isinstance(edits, tuple): edits = [edits]
    return dict(label=label, module=module, func=func, edits=edits, tests=tests, note=note)


def A(label, module, attr, edit, tests, note=""):
    """attribute mutant: edit is a function value -> value"""
    return dict(label=label, module=module, func=None, attr=attr, edit=edit, edits=[], tests=tests, note=note)

RT, FZ = [R], [F]
BOTH = [R, F, X]
MUTANTS = {
"retire": [
 M("RT1_approval_not_verified", BUILDER, "plan_retirement", ("verify_approval(root, approval)", "[]"), RT),
 M("RT2_existing_r11_artifacts_ignored", BUILDER, "plan_retirement", ("not any(_artifact_present(root / p) for p in (IDENTITY_CONFIG_PATH, EXPECTED_FREEZE_PATH, REGISTRY_PATH,", "not any(False for p in (IDENTITY_CONFIG_PATH, EXPECTED_FREEZE_PATH, REGISTRY_PATH,"), RT),
 M("RT3_ledger_pin_ignored", BUILDER, "plan_retirement", ("""return len(raw) == pin["size"] and sha256_bytes(raw) == pin["sha256"], f"ledger is {len(raw)} bytes, pinned {pin['size']}\"""", 'return True, ""'), RT),
 M("RT3b_ledger_size_only", BUILDER, "plan_retirement", ("""return len(raw) == pin["size"] and sha256_bytes(raw) == pin["sha256"], f"ledger""", """return len(raw) == pin["size"], f"ledger"""), RT),
 M("RT3c_ledger_sha_only", BUILDER, "plan_retirement", ("""return len(raw) == pin["size"] and sha256_bytes(raw) == pin["sha256"], f"ledger""", """return sha256_bytes(raw) == pin["sha256"], f"ledger"""), RT, "redundant: any appended byte changes the SHA"),
 M("RT4a_existing_retirement_event_ignored", BUILDER, "plan_retirement", ("        if lifecycle.authorization_retirement_event(R10_AUTHORIZATION_ID, ledger_path=root / LEDGER_PATH) is not None:", "        if False:"), RT, "redundant with RT3 and RT4b"),
 M("RT4b_executable_state_ignored", BUILDER, "plan_retirement", ("""return result["derived_state"] == lifecycle.ISSUED_EXECUTABLE and result["executable"] is True, f"reducer state {result['derived_state']}\"""", 'return True, ""'), RT),
 M("RT4ab_RT3_all_retirement_state_checks_removed", BUILDER, "plan_retirement", [("        if lifecycle.authorization_retirement_event(R10_AUTHORIZATION_ID, ledger_path=root / LEDGER_PATH) is not None:", "        if False:"), ("""return result["derived_state"] == lifecycle.ISSUED_EXECUTABLE and result["executable"] is True, f"reducer state {result['derived_state']}\"""", 'return True, ""'), ("""return len(raw) == pin["size"] and sha256_bytes(raw) == pin["sha256"], f"ledger is {len(raw)} bytes, pinned {pin['size']}\"""", 'return True, ""')], RT),
 M("RT5a_determination_bytes_not_compared", BUILDER, "plan_retirement", ('ok = (data == canonical_determination_bytes(approval["approval_id"]) and sha256_bytes(data) == pin["sha256"]', 'ok = (sha256_bytes(data) == pin["sha256"]'), RT, "redundant: the pinned SHA and the approval id still bind the file"),
 M("RT5b_determination_sha_not_compared", BUILDER, "plan_retirement", ('and sha256_bytes(data) == pin["sha256"]\n              and approval["approval_id"].encode() in data)', 'and approval["approval_id"].encode() in data)'), RT, "redundant: canonical bytes equality implies the SHA"),
 M("RT5c_approval_reference_not_checked", BUILDER, "plan_retirement", ('\n              and approval["approval_id"].encode() in data)', ')'), RT, "redundant: canonical bytes derive from the approval id"),
 M("RT5abc_determination_not_bound_to_the_approval", BUILDER, "plan_retirement", [('ok = (data == canonical_determination_bytes(approval["approval_id"]) and sha256_bytes(data) == pin["sha256"]', 'ok = (True'), ('\n              and approval["approval_id"].encode() in data)', ')')], RT),
 M("RT6_historical_pins_ignored", BUILDER, "plan_retirement", ("lambda: formal.verify_historical_pins(root) == formal.HISTORICAL_PIN_COUNT", "lambda: True"), RT),
 M("RT7_environment_ignored", BUILDER, "plan_retirement", ("lambda: _environment_condition(root)", 'lambda: (True, "")'), RT),
 M("W1_write_gate_removed", BUILDER, "retire_r10", ('    require_write_environment(root, "retire the r10 authorization")', "    pass"), RT + [X]),
 M("W2_plan_check_removed", BUILDER, "retire_r10", ('    if not plan["ready"]:', "    if False:"), RT, "redundant: the frozen function re-validates its own predicate; the ledger pin is rechecked next"),
 M("W3_confirmation_removed", BUILDER, "retire_r10", ('    confirm_with_token(plan["confirmation_token"],', '    (lambda *a, **k: None)(plan["confirmation_token"],'), RT + [X]),
 M("W4_ledger_recheck_after_confirmation_removed", BUILDER, "retire_r10", ('    if len(before) != pin["size"] or sha256_bytes(before) != pin["sha256"]:', "    if False:"), RT, "redundant with the plan's RT3; only a change between confirmation and write can show it"),
 M("W4b_plan_and_recheck_both_removed", BUILDER, "retire_r10", [('    if not plan["ready"]:', "    if False:"), ('    if len(before) != pin["size"] or sha256_bytes(before) != pin["sha256"]:', "    if False:")], RT),
 M("W5_refusal_of_frozen_function_not_distinguished", BUILDER, "retire_r10", ("        if ledger.read_bytes() != before:", "        if False:"), RT),
 M("W6_postcondition_checks_removed", BUILDER, "retire_r10", ("""    if not verification["ok"] or not (appended.endswith(b"\\n") and appended.count(b"\\n") == 1) or not ledger.read_bytes().startswith(before):""", "    if False:"), RT),
 M("W6b_verification_not_required", BUILDER, "retire_r10", ('    if not verification["ok"] or not (appended', '    if not (appended'), RT, "the one-line and prefix checks still catch most; the template and reducer checks are unique to verify"),
 M("W6c_one_line_check_removed", BUILDER, "retire_r10", ("""or not (appended.endswith(b"\\n") and appended.count(b"\\n") == 1)""", ""), RT),
 M("W6d_prefix_check_removed", BUILDER, "retire_r10", ("or not ledger.read_bytes().startswith(before):", ":"), RT, "verify_retirement also checks the pinned prefix"),
 M("VR1_prefix_pin_ignored", BUILDER, "verify_retirement", ('prefix_ok = len(raw) >= pin["size"] and sha256_bytes(raw[:pin["size"]]) == pin["sha256"]', "prefix_ok = True"), RT),
 M("VR2a_terminal_newline_not_required", BUILDER, "verify_retirement", ('ends_cleanly = lines[-1] == "" and retirement_line != ""', "ends_cleanly = True"), RT, "no test appends an unterminated line"),
 M("VR2b_later_lines_unrestricted", BUILDER, "verify_retirement", ("later_ok = len(rest) <= 1 and all(json.loads(line).get(\"event_type\") == ISSUED_EVENT_TYPE_NAME for line in rest)", "later_ok = True"), RT),
 M("VR3a_template_fields_ignored", BUILDER, "verify_retirement", ("            if differing:", "            if False:"), RT),
 M("VR3b_event_id_shape_ignored", BUILDER, "verify_retirement", ("""            if not re.fullmatch(r"retire-[0-9a-f]{32}", str(event.get("lifecycle_event_id"))):""", "            if False:"), RT),
 M("VR3c_timestamp_order_ignored", BUILDER, "verify_retirement", ('return all(stamp > e for e in earlier), "event equals the approved template; timestamp is later than every earlier event"', 'return True, ""'), RT),
 M("VR3d_path_fields_ignored", BUILDER, "verify_retirement", ("            differing += [k for k in path_fields if not _path_matches(event.get(k), template[k])]", "            pass"), RT),
 M("VR4_reducer_state_ignored", BUILDER, "verify_retirement", ("""return result["derived_state"] == lifecycle.RETIRED_STATE and result["executable"] is False, f"reducer state {result['derived_state']}\"""", 'return True, ""'), RT, "template and one-line checks catch the same anomalies in practice"),
 M("VR5_single_retirement_event_ignored", BUILDER, "verify_retirement", ("lifecycle.authorization_retirement_event(R10_AUTHORIZATION_ID, ledger_path=root / LEDGER_PATH) is not None, \"\"", "True, \"\""), RT, "implied by V3"),
 M("PM_path_match_always_true", BUILDER, "_path_matches", ("    return isinstance(value, str) and (value == relative or (value.startswith(\"/\") and value.endswith(\"/\" + relative)))", "    return True"), RT),
 M("TK_retire_token_ignores_the_approval", BUILDER, "retire_token", ('return f"RETIRE-R10-{R10_AUTHORIZATION_ID[:12]}-{approval_sha256[:12]}"', 'return f"RETIRE-R10-{R10_AUTHORIZATION_ID[:12]}-000000000000"'), RT),
 M("AG_aggregate_not_stable", BUILDER, "stable_aggregate", ("return repository_aggregate(Path(root), extra_excludes=ACTIVATION_OUTPUTS)", "return repository_aggregate(Path(root))"), [X]),
],
"freeze": [
 M("FZ1_approval_not_verified", BUILDER, "plan_freeze", ("verify_approval(root, approval)", "[]"), FZ),
 M("FZ2a_missing_retirement_event_ignored", BUILDER, "plan_freeze", ("        if event is None:", "        if False:"), FZ, "redundant with FZ2b and FZ3"),
 M("FZ2b_reducer_state_ignored", BUILDER, "plan_freeze", ("""return result["derived_state"] == lifecycle.RETIRED_STATE and result["executable"] is False, f"reducer state {result['derived_state']}\"""", 'return True, ""'), FZ),
 M("FZ2ab_ar14_not_required", BUILDER, "plan_freeze", [("        if event is None:", "        if False:"), ("""return result["derived_state"] == lifecycle.RETIRED_STATE and result["executable"] is False, f"reducer state {result['derived_state']}\"""", 'return True, ""')], FZ),
 M("FZ3a_pointer_bytes_ignored", BUILDER, "plan_freeze", ("        if path.is_symlink() or not path.is_file() or path.read_bytes() != canonical_pointer_bytes() or sha256_file(path) != POINTER_SHA256:", "        if False:"), FZ),
 M("FZ3b_record_binding_ignored", BUILDER, "plan_freeze", ("""return data.get("pointer_sha256") == POINTER_SHA256 and data.get("approval_record_sha256") == sha256_file(root / APPROVAL_PATH), \\""", "return True, \\"), FZ),
 M("FZ4_existing_freeze_ignored", BUILDER, "plan_freeze", ("not any(_artifact_present(root / p) for p in (EXPECTED_FREEZE_PATH, REGISTRY_PATH, AUTHORIZATION_MANIFEST_PATH))", "not any(False for p in (EXPECTED_FREEZE_PATH, REGISTRY_PATH, AUTHORIZATION_MANIFEST_PATH))"), FZ),
 M("FZ5a_prediction_sha_ignored", BUILDER, "plan_freeze", ("""return sha256_bytes(data) == pinned["predicted_sha256"] and len(data) == pinned["predicted_size"], \\""", """return len(data) == pinned["predicted_size"], \\"""), FZ),
 M("FZ5b_prediction_size_ignored", BUILDER, "plan_freeze", ("""return sha256_bytes(data) == pinned["predicted_sha256"] and len(data) == pinned["predicted_size"], \\""", """return sha256_bytes(data) == pinned["predicted_sha256"], \\"""), FZ, "redundant: the SHA fixes the size"),
 M("FZ6_historical_pins_ignored", BUILDER, "plan_freeze", ("lambda: formal.verify_historical_pins(root) == formal.HISTORICAL_PIN_COUNT", "lambda: True"), FZ),
 M("FZ7_environment_ignored", BUILDER, "plan_freeze", ("lambda: _environment_condition(root)", 'lambda: (True, "")'), FZ),
 M("CF1_write_gate_removed", BUILDER, "create_freeze", ('    require_write_environment(root, "create the r11 Freeze")', "    pass"), FZ + [X]),
 M("CF2_plan_check_removed", BUILDER, "create_freeze", ('    if not plan["ready"]:', "    if False:"), FZ, "redundant with the in-lock re-check"),
 M("CF3_confirmation_removed", BUILDER, "create_freeze", ('    confirm_with_token(plan["confirmation_token"], f"create the r11 Freeze ({len(data)} bytes, SHA-256 {predicted})")', "    pass"), FZ + [X]),
 M("CF4_inlock_recheck_removed", BUILDER, "create_freeze", ('        if not again["ready"] or again["_data"] != data:', "        if False:"), FZ),
 M("CF4b_both_ready_checks_removed", BUILDER, "create_freeze", [('    if not plan["ready"]:', "    if False:"), ('        if not again["ready"] or again["_data"] != data:', "        if False:")], FZ),
 M("CF5_disk_sha_vs_prediction_ignored", BUILDER, "create_freeze", ("        if written != data or sha256_bytes(written) != predicted:", "        if False:"), FZ),
 M("CF6_reproducibility_check_ignored", BUILDER, "create_freeze", ('    if not verification["ok"]:', "    if False:"), FZ, "unreachable in tests: the SHA check fires first for any byte difference; reproducibility can only fail if the members change during the write"),
 M("CF7_library_write_used_instead", BUILDER, "create_freeze", ("        _write_exclusive(target, data)", "        target.write_bytes(data)"), FZ),
 M("TK_freeze_token_ignores_the_approval", BUILDER, "freeze_token", ('return f"CREATE-R11-FREEZE-{predicted_sha256[:12]}-{approval_sha256[:12]}"', 'return f"CREATE-R11-FREEZE-{predicted_sha256[:12]}-000000000000"'), FZ),
],
"proof": [
 M("H1_hook_not_called", BUILDER, "_write_exclusive", ("    _verify_manifest_matches_plan(path, data)", "    pass"), [H]),
 M("H2_every_path_checked", BUILDER, "_verify_manifest_matches_plan", ("    if not target.as_posix().endswith(AUTHORIZATION_MANIFEST_PATH):", "    if False:"), [H]),
 M("H3_shape_guard_removed", BUILDER, "_verify_manifest_matches_plan", ('    if not isinstance(preview, dict) or not isinstance(written, dict) or not isinstance(written.get("issued_at_utc"), str):', "    if False:"), [H]),
 M("H4_key_comparison_removed", BUILDER, "_verify_manifest_matches_plan", ("    if differing:", "    if False:"), [H], "redundant with the byte comparison"),
 M("H5_byte_comparison_removed", BUILDER, "_verify_manifest_matches_plan", ("""    if issuer.manifest_bytes({**preview, "issued_at_utc": written["issued_at_utc"]}) != data:""", "    if False:"), [H]),
 M("H45_both_comparisons_removed", BUILDER, "_verify_manifest_matches_plan", [("    if differing:", "    if False:"), ("""    if issuer.manifest_bytes({**preview, "issued_at_utc": written["issued_at_utc"]}) != data:""", "    if False:")], [H]),
 M("H6_issue_time_compared_too", BUILDER, "_verify_manifest_matches_plan", ('if k != "issued_at_utc" and preview.get(k) != written.get(k)', "if preview.get(k) != written.get(k)"), [H]),
 M("H7_readback_removed_in_issuer", ISSUER, "issue_authorization", ("        if target.read_bytes() != data:", "        if False:"), [H]),
],
"superseding": [
 A("S1_consumer_pin_altered", BUILDER, "CHANGED_SHA256", lambda v: {**v, "scripts/run_step9_63_v3_formal_execution.py": "0" * 64}, [SUP]),
 A("S2_scanner_pin_altered", BUILDER, "CHANGED_SHA256", lambda v: {**v, "scripts/v3_execution_transaction.py": "0" * 64}, [SUP]),
 A("S3_issuer_pin_altered", BUILDER, "ISSUER_SHA256", lambda v: "0" * 64, [SUP]),
 M("S4_historical_pin_check_neutralized", FORMAL, "collect_r11_precommit_state", ('check("historical_integrity_match", lambda: verify_historical_pins(root) == HISTORICAL_PIN_COUNT)', 'check("historical_integrity_match", lambda: True or verify_historical_pins(root) == HISTORICAL_PIN_COUNT)'), [SUP]),
 M("S5_execute_formal_ignores_the_gate", FORMAL, "execute_formal", ('    if gates["precommit_failures"]:', "    if False:"), [SUP]),
 M("S6_issuance_cross_check_not_wired", FORMAL, "prepare_formal_gates", ("    failures += [name for name in validate_issuance_cross_check(state) if name not in failures]", "    pass"), [SUP]),
 M("S7_manifest_inventory_check_removed", BASE_VALIDATOR, "audit_manifest", ("    if set(by_name) != discovered:", "    if False:"), [MAN]),
 M("S8_manifest_version_check_removed", AH_VALIDATOR, "audit_manifest", ('    if data.get("version_id") != MANIFEST_VERSION:', "    if False:"), [MAN]),
 M("S9_previous_bytes_pin_removed", AH_VALIDATOR, "audit_manifest", ("    if sha256_file(PREVIOUS_MANIFEST) != PREVIOUS_MANIFEST_SHA256:", "    if False:"), [MAN]),
 M("S10_previous_reference_check_removed", AH_VALIDATOR, "audit_manifest", ('    if previous.get("sha256") != PREVIOUS_MANIFEST_SHA256 or previous.get("version_id") != PREVIOUS_MANIFEST_VERSION:', "    if False:"), [MAN]),
 M("S11_carried_decisions_check_removed", AH_VALIDATOR, "audit_manifest", ("        if name in new_rows and any(new_rows[name].get(field) != old.get(field) for field in CARRIED_FIELDS):", "        if False:"), [MAN]),
 M("S12_added_since_previous_check_removed", AH_VALIDATOR, "audit_manifest", ('    if data.get("added_since_previous") != added:', "    if False:"), [MAN]),
 M("S13_manifest_build_changed", AH_VALIDATOR, "build_manifest", ('"selection_rule": "constant path and version id; no discovery of other manifests",', '"selection_rule": "changed",'), [MAN]),
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
    groups = list(MUTANTS) if group == "all" else [group]
    mods = {n: importlib.import_module(n) for n in (R, F, H, X, SUP, MAN)}
    for m in mods.values():                    # build the templates once, with unmutated code
        up, tear = getattr(m, "setUpModule", None), getattr(m, "tearDownModule", None)
        if up: up()
        m.setUpModule = lambda: None; m.tearDownModule = lambda: None; m._tear = tear or (lambda: None)
    results, originals = [], {}
    for g in groups:
        for mutant in MUTANTS[g]:
            mod = importlib.import_module(mutant["module"])
            if mutant.get("func") is None:
                original = getattr(mod, mutant["attr"])
                setattr(mod, mutant["attr"], mutant["edit"](original))
                fx.build_command = lambda module, root, args: [sys.executable, "-m", module, "--root", str(root), *args]
            else:
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
            results.append({"group": g, "mutant": mutant["label"], "function": f"{mutant['module'].split('.')[-1]}.{mutant['func'] or mutant['attr']}",
                            "result": "KILLED" if bad else "SURVIVED", "killed_by": bad[0][0].id() if bad else None,
                            "note": mutant["note"], "seconds": round(time.time() - t0, 1)})
            setattr(mod, mutant["func"] or mutant["attr"], original)
            print(results[-1]["result"], mutant["label"], results[-1]["killed_by"] or "", flush=True)
    for m in mods.values(): m._tear()
    json.dump({"artifact_type": "R5C10AH_MUTATION_RESULTS", "total": len(results),
               "killed": sum(r["result"] == "KILLED" for r in results),
               "survived": [r["mutant"] for r in results if r["result"] == "SURVIVED"],
               "source_inspection_tests_excluded": sorted(EXCLUDED), "results": results}, open(out, "w"), indent=1)
    print("KILLED", sum(r["result"] == "KILLED" for r in results), "of", len(results))

if __name__ == "__main__":
    main()
