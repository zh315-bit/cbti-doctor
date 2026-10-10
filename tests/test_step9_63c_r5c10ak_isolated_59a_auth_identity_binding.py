"""Step 9.63c-r5c10ak: test_step9_59a_auth_identity_binding runs UNCHANGED on a temporary mirror of the repository.

The original module (archived as tests/retired/test_step9_59a_auth_identity_binding.py.retired) exercised production code whose default paths point
at the real activation state (ledger, run root, authorization manifests, namespace lock). Here it runs
inside a private copy (tests/legacy_isolation.py); the methods listed in RETIRED are not run, and their
properties are covered where the mapping says (evaluation/v1_2_3/step9_63c_r5c10ak_coverage_mapping.json).
"""
import legacy_isolation

RETIRED = {
    "AuthorizationIdentityBindingTests.test_parent_validator_accepts_authoritative_r7_pins": "tests/test_step9_63c_r5c10ak_isolated_ae_consumer_precommit_gate.py::test_ConsumerPrecommitGateTests__test_00_consistent_fixture_passes_every_r11_precommit_check; tests/test_step9_63c_r5c10ai_final_form_and_tokens.py::FinalFormSequence (the CURRENT runner's authoritative pins are accepted; r7 is superseded)",
    "AuthorizationIdentityBindingTests.test_preflight_runner_binding_mismatch_fails_closed": "tests/test_step9_63c_r5c10ak_isolated_ae_consumer_precommit_gate.py::test_ConsumerPrecommitGateTests__test_formal_entry_or_freeze_binding_mismatch_rejected",
    "AuthorizationIdentityBindingTests.test_preflight_rejects_freeze_hash_not_equal_to_current_runner": "tests/test_step9_63c_r5c10ak_isolated_ae_consumer_precommit_gate.py::test_ConsumerPrecommitGateTests__test_formal_entry_or_freeze_binding_mismatch_rejected",
    "AuthorizationIdentityBindingTests.test_actual_preflight_fails_closed_on_stale_validator_runner_pin": "tests/test_step9_63c_r5c10ak_isolated_ae_consumer_precommit_gate.py::test_ConsumerPrecommitGateTests__test_frozen_identity_mismatch_rejected",
    "AuthorizationIdentityBindingTests.test_parent_validator_rejects_retired_authorization": "tests/test_step9_63c_r5c10ak_isolated_63a_r2_retirement_eligibility.py::test_SupersededRetirementTests__test_retired_auth_cannot_create_parent_attempt; tests/test_step9_63c_r5c10ak_isolated_ae_consumer_precommit_gate.py::test_ConsumerPrecommitGateTests__test_retired_bound_authorization_rejected"
}

legacy_isolation.make_module(globals(), 'test_step9_59a_auth_identity_binding', retired=RETIRED)
