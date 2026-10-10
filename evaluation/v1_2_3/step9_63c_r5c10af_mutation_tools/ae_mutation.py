"""In-memory mutation of scripts/run_step9_63_v3_formal_execution.py; writes nothing."""
import importlib, inspect, json, re, sys, textwrap, unittest
sys.path[:0] = [".", "tests"]
formal = importlib.import_module("scripts.run_step9_63_v3_formal_execution")
T = "test_step9_63c_r5c10ae_consumer_precommit_gate.ConsumerPrecommitGateTests."
E = "test_step9_63c_r5c10ae_consumer_precommit_gate.ExecuteFormalOrderingTests."
def neutralize(name):  # make check(name, ...) always True
    return ("collect_r11_precommit_state", re.compile(r'check\("' + re.escape(name) + r'", lambda:'), f'check("{name}", lambda: True or ')
MUTANTS = [
 ("historical_pins_check", neutralize("historical_integrity_match"), [T + "test_historical_pin_mismatch_rejected"]),
 ("ledger_prefix_check", ("verify_historical_pins", "if not prefix_matches(", "if False and not prefix_matches("), [T + "test_ledger_prefix_tamper_rejected"]),
 ("exactly_one_active", neutralize("exactly_one_active_authorization"), [T + "test_second_active_authorization_rejected"]),
 ("active_is_bound_id", neutralize("active_authorization_is_bound_id"), [T + "test_second_active_authorization_rejected"]),
 ("old_authorization_retired", neutralize("old_authorization_retired"), [T + "test_executable_superseded_authorization_rejected"]),
 ("old_authorization_non_executable", neutralize("old_authorization_non_executable"), [T + "test_executable_superseded_authorization_rejected"]),
 ("lifecycle_executable", neutralize("authorization_lifecycle_executable"), [T + "test_retired_bound_authorization_rejected"]),
 ("agent_match", neutralize("agent_match"), [T + "test_agent_mismatch_rejected"]),
 ("frozen_identities", neutralize("frozen_identities_match"), [T + "test_frozen_identity_mismatch_rejected"]),
 ("status_unconsumed", neutralize("authorization_status_issued_unconsumed"), [T + "test_consumed_or_counted_authorization_rejected"]),
 ("attempt_absent", neutralize("attempt_absent"), [T + "test_existing_attempt_rejected"]),
 ("namespace_absent", neutralize("namespace_absent"), [T + "test_existing_namespace_rejected"]),
 ("namespace_id_match", neutralize("namespace_id_match"), [T + "test_namespace_binding_mismatch_rejected"]),
 ("case_order_match", neutralize("case_order_match"), [T + "test_case_and_evaluation_identity_mismatch_rejected"]),
 ("evaluation_identity", neutralize("evaluation_identity_match"), [T + "test_case_and_evaluation_identity_mismatch_rejected"]),
 ("runner_freeze_match", neutralize("runner_freeze_match"), [T + "test_formal_entry_or_freeze_binding_mismatch_rejected"]),
 ("lifecycle_contract_match", neutralize("lifecycle_contract_match"), [T + "test_lifecycle_contract_tamper_rejected"]),
 ("atomic_commit_protocol", neutralize("atomic_commit_protocol_match"), [T + "test_atomic_commit_contract_tamper_rejected"]),
 ("fresh_connectivity", neutralize("fresh_connectivity_pass"), [T + "test_unvalidated_preflight_rejected"]),
 ("project_root", neutralize("project_root_match"), [T + "test_wrong_project_root_or_runtime_rejected"]),
 ("unexecuted_check_counts_as_failure", ("validate_precommit", 'for name in state.get("checks_not_executed", ())', 'for name in ()'), [T + "test_unavailable_identity_adapter_fails_closed", T + "test_missing_key_or_unexecuted_check_fails"]),
 ("execute_formal_ignores_gate", ("execute_formal", 'if gates["precommit_failures"]:', 'if False:'), [E + "test_precommit_failure_raises_before_adapter", E + "test_prepare_formal_gates_reports_real_precommit_failures"]),
 ("gate_not_wired", ("prepare_formal_gates", '"precommit_failures": validate_precommit(state, R11_PRECOMMIT_KEYS)', '"precommit_failures": []'), [E + "test_prepare_formal_gates_reports_real_precommit_failures"]),
 ("main_hardcodes_failures", ("main", 'failures = ["precommit_not_evaluated:authorization_and_preflight_required"]', 'failures = []'), [E + "test_main_audit_reports_real_precommit_result"]),
]
original = {name: getattr(formal, name) for name in ("collect_r11_precommit_state", "verify_historical_pins", "validate_precommit", "execute_formal", "prepare_formal_gates", "main")}
results = []
for label, (func, old, new), tests in MUTANTS:
    src = textwrap.dedent(inspect.getsource(original[func]))
    mutated = old.sub(new, src) if hasattr(old, "sub") else src.replace(old, new)
    assert mutated != src, label
    ns = formal.__dict__
    exec(compile(mutated, formal.__file__, "exec"), ns)
    r = unittest.TextTestRunner(stream=open("/dev/null", "w")).run(unittest.defaultTestLoader.loadTestsFromNames(tests))
    killed = bool(r.failures or r.errors)
    how = "TEST_FAILED" if killed else "SURVIVED"
    results.append({"mutant": label, "function": func, "tests": tests, "result": "KILLED" if killed else "SURVIVED", "evidence": how})
    for name, fn in original.items(): ns[name] = fn
print(json.dumps(results, indent=1))
print("KILLED", sum(r["result"] == "KILLED" for r in results), "of", len(results))
