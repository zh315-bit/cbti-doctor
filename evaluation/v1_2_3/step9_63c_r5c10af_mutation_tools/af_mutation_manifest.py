import importlib, inspect, json, sys, textwrap, unittest
sys.path[:0] = [".", "tests"]
b = importlib.import_module("scripts.validate_step9_63c_r5c10ae_test_boundary")
P = "test_step9_63c_r5c10ae_test_boundary_manifest.Step963cR5c10aeManifestTests."
MUTANTS = [
 ("version_check_removed", "audit_manifest", 'if data.get("version_id") != MANIFEST_VERSION:', 'if False:', [P + "test_wrong_version_or_previous_reference_is_rejected"]),
 ("previous_manifest_hash_check_removed", "audit_manifest", 'if sha256_file(PREVIOUS_MANIFEST) != PREVIOUS_MANIFEST_SHA256:', 'if False:', None),
 ("previous_reference_check_removed", "audit_manifest", 'if previous.get("sha256") != PREVIOUS_MANIFEST_SHA256 or previous.get("version_id") != PREVIOUS_MANIFEST_VERSION:', 'if False:', [P + "test_wrong_version_or_previous_reference_is_rejected"]),
 ("carried_decision_check_removed", "audit_manifest", 'if name in new_rows and any(new_rows[name].get(field) != old.get(field) for field in CARRIED_FIELDS):', 'if False:', [P + "test_decision_of_a_row_carried_from_r5c10ad_cannot_change"]),
 ("added_since_previous_check_removed", "audit_manifest", 'if data.get("added_since_previous") != added:', 'if False:', None),
]
original = b.audit_manifest; results = []
for label, func, old, new, tests in MUTANTS:
    src = textwrap.dedent(inspect.getsource(original)); assert src.count(old) == 1, label
    exec(compile(src.replace(old, new), b.__file__, "exec"), b.__dict__)
    if tests is None:   # these two checks are exercised by a dedicated tamper probe below
        import copy
        data = json.loads(b.MANIFEST.read_text())
        probe = copy.deepcopy(data)
        if "hash" in label: 
            real = b.PREVIOUS_MANIFEST_SHA256; b.PREVIOUS_MANIFEST_SHA256 = "0" * 64
            errors = b.audit_manifest(probe); b.PREVIOUS_MANIFEST_SHA256 = real
            killed = not any("previous (r5c10ad) manifest bytes changed" in e for e in errors) and True
            # with the check removed, a wrong pinned hash is NOT reported -> mutant detectable only if the unmutated code reports it
            b.__dict__["audit_manifest"] = original
            real_pin = "0" * 64; b.PREVIOUS_MANIFEST_SHA256 = real_pin
            reported = any("bytes changed" in e for e in b.audit_manifest(probe)); b.PREVIOUS_MANIFEST_SHA256 = real
            killed = reported
        else:
            probe["added_since_previous"] = ["bogus"]
            exec(compile(src.replace(old, new), b.__file__, "exec"), b.__dict__); mutant_errors = b.audit_manifest(probe)
            b.__dict__["audit_manifest"] = original; real_errors = b.audit_manifest(probe)
            killed = any("added_since_previous" in e for e in real_errors) and not any("added_since_previous" in e for e in mutant_errors)
        results.append({"mutant": label, "result": "KILLED" if killed else "SURVIVED", "evidence": "unmutated audit reports the tamper that the mutant misses"})
    else:
        r = unittest.TextTestRunner(stream=open("/dev/null", "w")).run(unittest.defaultTestLoader.loadTestsFromNames(tests))
        results.append({"mutant": label, "result": "KILLED" if (r.failures or r.errors) else "SURVIVED", "evidence": "TEST_FAILED", "tests": [t.split(".")[-1] for t in tests]})
    b.__dict__["audit_manifest"] = original
print(json.dumps(results, indent=1)); print("KILLED", sum(x["result"] == "KILLED" for x in results), "of", len(results))
