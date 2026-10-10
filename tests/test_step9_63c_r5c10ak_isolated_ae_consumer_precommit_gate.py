"""Step 9.63c-r5c10ak: test_step9_63c_r5c10ae_consumer_precommit_gate runs UNCHANGED on a temporary mirror of the repository.

The original module (archived as tests/retired/test_step9_63c_r5c10ae_consumer_precommit_gate.py.r5c10ak.retired) exercised production code whose default paths point
at the real activation state (ledger, run root, authorization manifests, namespace lock). Here it runs
inside a private copy (tests/legacy_isolation.py); the methods listed in RETIRED are not run, and their
properties are covered where the mapping says (evaluation/v1_2_3/step9_63c_r5c10ak_coverage_mapping.json).
"""
import legacy_isolation

RETIRED = {
    "ConsumerPrecommitGateTests.test_real_r10_authorization_blocks_r11_until_retired": "tests/test_step9_63c_r5c10ak_isolated_ae_consumer_precommit_gate.py::test_ConsumerPrecommitGateTests__test_executable_superseded_authorization_rejected (an executable superseded authorization blocks the gate); tests/test_step9_63c_r5c10ah_retire_entry.py::PlanTests.test_rt4_an_already_retired_authorization_blocks",
    "ConsumerPrecommitGateTests.test_unavailable_identity_adapter_fails_closed": "tests/test_step9_63c_r5c10ak_isolated_ae_consumer_precommit_gate.py::test_ConsumerPrecommitGateTests__test_missing_key_or_unexecuted_check_fails (a check that cannot run counts as a failure)"
}

legacy_isolation.make_module(globals(), 'test_step9_63c_r5c10ae_consumer_precommit_gate', retired=RETIRED)
