import importlib, inspect, json, sys, textwrap, unittest
sys.path[:0] = [".", "tests"]
b = importlib.import_module("scripts.build_step9_63c_r11_runner_freeze")
P = "test_step9_63c_r5c10ae_builder_pins."
MUTANTS = [
 ("ar10_accept_any_change_differing_from_r10", "assemble_candidate",
  'if relpath in CHANGED and digest != CHANGED_SHA256[relpath]:',
  'if relpath in CHANGED and digest == old.get(relpath):', [P + "BuilderPinTests.test_unreviewed_change_to_any_changed_member_is_rejected"]),
 ("ar10_pin_table_completeness_removed", "assemble_candidate",
  'if set(CHANGED_SHA256) != CHANGED:', 'if False:', [P + "BuilderPinTests.test_pin_table_must_cover_every_changed_member"]),
 ("ar11_agent_check_removed", "verify_frozen_inputs",
  'if not agent_match or agent_sha != identities["treatment_agent_sha256"]:', 'if False:', [P + "InlinedFrozenInputEquivalenceTests.test_differential_behaviour_matches_original"]),
 ("ar11_rag_check_removed", "verify_frozen_inputs",
  'if sha256_bytes(rag_payload.encode()) != identities["rag_configuration_fingerprint_sha256"]:', 'if False:', [P + "InlinedFrozenInputEquivalenceTests.test_differential_behaviour_matches_original"]),
 ("ar11_model_config_check_removed", "verify_frozen_inputs",
  'if not nonsecret_model_configuration_matches(root):', 'if False:', [P + "InlinedFrozenInputEquivalenceTests.test_differential_behaviour_matches_original"]),
]
original = {n: getattr(b, n) for n in ("assemble_candidate", "verify_frozen_inputs")}
results = []
for label, func, old, new, tests in MUTANTS:
    src = textwrap.dedent(inspect.getsource(original[func])); assert src.count(old) == 1, label
    exec(compile(src.replace(old, new), b.__file__, "exec"), b.__dict__)
    r = unittest.TextTestRunner(stream=open("/dev/null", "w")).run(unittest.defaultTestLoader.loadTestsFromNames(tests))
    results.append({"mutant": label, "function": func, "tests": tests,
                    "result": "KILLED" if (r.failures or r.errors) else "SURVIVED", "evidence": "TEST_FAILED" if (r.failures or r.errors) else "SURVIVED"})
    for n, f in original.items(): b.__dict__[n] = f
print(json.dumps(results, indent=1)); print("KILLED", sum(x["result"] == "KILLED" for x in results), "of", len(results))
