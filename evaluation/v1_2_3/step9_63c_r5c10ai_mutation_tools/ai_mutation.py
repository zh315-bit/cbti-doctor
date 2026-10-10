"""In-memory behavioural mutation of the r11 builder, issuer and consumer. Writes nothing in the repository.

Each mutant replaces one function's source in memory (parent process and, for command-line
entries, the child process too). Source-inspection tests are excluded from kill attribution.
usage: python ai_mutation.py <group> <out.json>   (group: token | replay | manifest | all)
"""
import importlib, inspect, json, os, sys, textwrap, unittest, time
sys.path[:0] = [".", "tests"]
import r11_activation_fixtures as fx

BUILDER, ISSUER, FORMAL = ("scripts.build_step9_63c_r11_runner_freeze", "scripts.issue_step9_63c_r11_authorization",
                           "scripts.run_step9_63_v3_formal_execution")
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

TOK = "test_step9_63c_r5c10ai_final_form_and_tokens"
REP = "test_step9_63c_r5c10ai_v2_archival_replay"
MAN = "test_step9_63c_r5c10ai_test_boundary_manifest"
EXCLUDED = set()
AI_VALIDATOR = "scripts.validate_step9_63c_r5c10ai_test_boundary"
BASE_VALIDATOR = "scripts.validate_step9_63c_test_boundary"
REPMOD = "test_step9_63c_r5c10ai_v2_archival_replay"
MUTANTS = {
"token": [
 A("T1_token_first_segment_is_the_old_literal", BUILDER, "R10_UUID_PREFIX12", lambda v: "auth-step9_6", [TOK]),
 A("T2_token_first_segment_is_the_whole_uuid", BUILDER, "R10_UUID_PREFIX12", lambda v: v + "4278a14d3fd08bf8a84e", [TOK]),
 M("T3_retire_token_ignores_the_approval_part", BUILDER, "retire_token", ('return f"RETIRE-R10-{R10_UUID_PREFIX12}-{approval_sha256[:12]}"', 'return f"RETIRE-R10-{R10_UUID_PREFIX12}-000000000000"'), [TOK]),
 M("T4_token_part_is_always_the_file_hash", BUILDER, "approval_token_part", ('    if "content_sha256" in approval:', "    if False:"), [TOK]),
 M("T5_content_hash_keeps_the_signature_fields", BUILDER, "approval_content_sha256", ("    neutral.update(SIGNATURE_FIELDS)", "    pass"), [TOK]),
 M("T6_content_hash_keeps_the_token_values", BUILDER, "approval_content_sha256", ('    if isinstance(neutral.get("tokens"), dict):', "    if False:"), [TOK]),
 M("T7_content_hash_includes_itself", BUILDER, "approval_content_sha256", ('neutral = {k: v for k, v in approval.items() if k != "content_sha256"}', "neutral = dict(approval)"), [TOK]),
 M("T8_aggregate_is_part_of_the_content_hash", BUILDER, "approval_content_sha256", ('    neutral.pop("repository_aggregate", None)', "    pass"), [TOK]),
 M("C1_content_check_removed", BUILDER, "verify_approval", ('    if "content_sha256" in approval and approval_content_sha256(approval) != approval["content_sha256"]:', "    if False:"), [TOK]),
 M("C2_commit_pin_not_enforced", BUILDER, "verify_approval", ('    if require_signed and isinstance(approval.get("commit_pin"), dict) and approval["commit_pin"].get("required"):', "    if False:"), [TOK]),
 M("C3_head_comparison_removed", BUILDER, "verify_approval", ("        elif head_commit(root) != pinned:", "        elif False:"), [TOK]),
 M("C4_commit_shape_check_removed", BUILDER, "verify_approval", ('        if not isinstance(pinned, str) or not re.fullmatch(r"[0-9a-f]{40}", pinned):', "        if False:"), [TOK], "redundant: a missing or malformed commit never equals HEAD"),
 M("C34_no_commit_check_at_all", BUILDER, "verify_approval", [('        if not isinstance(pinned, str) or not re.fullmatch(r"[0-9a-f]{40}", pinned):', "        if False:"), ("        elif head_commit(root) != pinned:", "        elif False:")], [TOK]),
 M("H1_detached_head_not_validated", BUILDER, "head_commit", ('return ref if re.fullmatch(r"[0-9a-f]{40}", ref) else None', "return ref"), [TOK]),
 M("H2_ref_value_not_validated", BUILDER, "head_commit", ('return value if re.fullmatch(r"[0-9a-f]{40}", value) else None', "return value"), [TOK]),
 M("H3_loose_ref_ignored", BUILDER, "head_commit", ("        if (git / name).is_file():", "        if False:"), [TOK]),
 M("H4_packed_refs_wrong_field", BUILDER, "head_commit", ('line.split(" ", 1)[0] for line in', 'line.split(" ", 1)[1] for line in'), [TOK]),
 M("E1_exceptions_not_recorded", BUILDER, "build_approval", ('    result["accepted_exceptions"] = json.loads(json.dumps(ACCEPTED_EXCEPTIONS))', '    result["accepted_exceptions"] = []'), [TOK]),
 M("E2_commit_pin_not_in_final_form", BUILDER, "build_approval", ('        result["commit_pin"] = {', '        result["commit_pin_unused"] = {'), [TOK]),
 M("E3_final_form_has_no_content_hash", BUILDER, "build_approval", ('        result["content_sha256"] = approval_content_sha256(result)', '        result["content_sha256"] = "0" * 64'), [TOK]),
 M("E4_tokens_not_concrete", BUILDER, "build_approval", ('        result["tokens"]["retire_r10"]["value"] = retire_token(result["content_sha256"])', '        pass'), [TOK]),
],
"replay": [
 M("P1_archived_bytes_tampered", REPMOD, "head_blob", ("    return body", '    return body[:-1] + b"X"'), [REP]),
 M("P2_git_object_tampered", REPMOD, "git_object", ('        return header.split(b" ")[0].decode(), body', '        return header.split(b" ")[0].decode(), body + b"x"'), [REP], "loose-object path; the packed fallback is not reachable in this checkout"),
 A("P3_archival_commit_does_not_exist", REPMOD, "V2_ARCHIVAL_COMMIT", lambda v: "0" * 40, [REP]),
 A("P4_archival_commit_is_the_current_head", REPMOD, "V2_ARCHIVAL_COMMIT", lambda v: __import__("scripts.build_step9_63c_r11_runner_freeze", fromlist=["x"]).head_commit(__import__("pathlib").Path.cwd()), [REP]),
 M("P5_ancestry_not_walked", REPMOD, "parents_of", (r'    return [line.split(" ", 1)[1] for line in body.split(b"\n\n", 1)[0].decode().splitlines() if line.startswith("parent ")]', "    return []"), [REP]),
 A("P6_archival_commit_is_a_tree_not_a_commit", REPMOD, "V2_ARCHIVAL_COMMIT", lambda v: "2b9fb1ff0ab6ef0d05a5f2a1a1b5b09a3f0b7c11", [REP], "a non-existent object id of another shape"),
],
"manifest": [
 M("S1_inventory_check_removed", BASE_VALIDATOR, "audit_manifest", ("    if set(by_name) != discovered:", "    if False:"), [MAN]),
 M("S2_version_check_removed", AI_VALIDATOR, "audit_manifest", ('    if data.get("version_id") != MANIFEST_VERSION:', "    if False:"), [MAN]),
 M("S3_previous_bytes_pin_removed", AI_VALIDATOR, "audit_manifest", ("    if sha256_file(PREVIOUS_MANIFEST) != PREVIOUS_MANIFEST_SHA256:", "    if False:"), [MAN]),
 M("S4_carried_decisions_check_removed", AI_VALIDATOR, "audit_manifest", ("        if name in new_rows and any(new_rows[name].get(field) != old.get(field) for field in CARRIED_FIELDS):", "        if False:"), [MAN]),
 M("S5_added_since_previous_check_removed", AI_VALIDATOR, "audit_manifest", ('    if data.get("added_since_previous") != added:', "    if False:"), [MAN]),
 M("S6_manifest_build_changed", AI_VALIDATOR, "build_manifest", ('"selection_rule": "constant path and version id; no discovery of other manifests",', '"selection_rule": "changed",'), [MAN]),
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
    mods = {n: importlib.import_module(n) for n in (TOK, REP, MAN)}
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
    json.dump({"artifact_type": "R5C10AI_MUTATION_RESULTS", "total": len(results),
               "killed": sum(r["result"] == "KILLED" for r in results),
               "survived": [r["mutant"] for r in results if r["result"] == "SURVIVED"],
               "source_inspection_tests_excluded": sorted(EXCLUDED), "results": results}, open(out, "w"), indent=1)
    print("KILLED", sum(r["result"] == "KILLED" for r in results), "of", len(results))

if __name__ == "__main__":
    main()
