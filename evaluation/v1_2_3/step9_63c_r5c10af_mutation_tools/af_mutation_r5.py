import importlib, inspect, json, re, sys, textwrap, unittest
sys.path[:0] = [".", "tests"]
formal = importlib.import_module("scripts.run_step9_63_v3_formal_execution")
T = "test_step9_63c_r5c10ae_consumer_precommit_gate.ConsumerPrecommitGateTests."
def neutralize(name):
    return ("collect_r11_precommit_state", re.compile(r'check\("' + re.escape(name) + r'", lambda:'), f'check("{name}", lambda: True or ')
MULTI = [T + "test_second_active_authorization_rejected"]
PINS = [T + "test_historical_pin_mismatch_rejected", T + "test_inventory_pin_mismatch_rejected",
        T + "test_ledger_prefix_tamper_rejected", T + "test_historical_pin_count_54_rejected"]
MUTANTS = [
 # property: more than one active authorization is refused (retired r5 test_multiple_active_authorizations)
 ("multi_active:exactly_one_check_removed", neutralize("exactly_one_active_authorization"), MULTI),
 ("multi_active:bound_id_check_removed", neutralize("active_authorization_is_bound_id"), MULTI),
 ("multi_active:independent_recount_replaced_by_producer_view", ("collect_r11_precommit_state",
   'active = check("active_authorizations", lambda: lifecycle.active_authorizations(root))',
   'active = check("active_authorizations", lambda: [authorization_id])'), MULTI),
 # property: all 55 historical pins are enforced (retired r5 test_historical_pin_mismatch)
 ("pins:gate_check_removed", neutralize("historical_integrity_match"), PINS),
 ("pins:inventory_hash_check_removed", ("verify_historical_pins", 'if pin.get("match") is not True or sha256(root / pin["path"]) != pin["sha256"]:', 'if False:'), [PINS[1]]),
 ("pins:supplemental_hash_check_removed", ("verify_historical_pins", 'if sha256(root / relpath) != expected:', 'if False:'), [PINS[0]]),
 ("pins:ledger_prefix_check_removed", ("verify_historical_pins", 'if not prefix_matches(', 'if False and not prefix_matches('), [PINS[2]]),
 ("pins:count_check_removed", ("verify_historical_pins", 'if len(pins) != HISTORICAL_PIN_COUNT:', 'if False:'), [PINS[3]]),
 ("pins:gate_result_ignored_by_execute_formal", ("execute_formal", 'if gates["precommit_failures"]:', 'if False:'),
   ["test_step9_63c_r5c10ae_consumer_precommit_gate.ExecuteFormalOrderingTests.test_prepare_formal_gates_reports_real_precommit_failures"]),
]
orig = {n: getattr(formal, n) for n in ("collect_r11_precommit_state", "verify_historical_pins", "execute_formal")}
results = []
for label, (func, old, new), tests in [(m[0], m[1], m[2]) for m in MUTANTS]:
    src = textwrap.dedent(inspect.getsource(orig[func]))
    mutated = old.sub(new, src) if hasattr(old, "sub") else src.replace(old, new)
    assert mutated != src, label
    exec(compile(mutated, formal.__file__, "exec"), formal.__dict__)
    r = unittest.TextTestRunner(stream=open("/dev/null", "w")).run(unittest.defaultTestLoader.loadTestsFromNames(tests))
    killed = bool(r.failures or r.errors)
    results.append({"mutant": label, "function": func, "tests": [t.split(".")[-1] for t in tests], "result": "KILLED" if killed else "SURVIVED"})
    for n, f in orig.items(): formal.__dict__[n] = f
print(json.dumps(results, indent=1)); print("KILLED", sum(r["result"] == "KILLED" for r in results), "of", len(results))
