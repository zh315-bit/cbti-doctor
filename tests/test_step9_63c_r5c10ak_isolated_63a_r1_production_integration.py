"""Step 9.63c-r5c10ak: test_step9_63a_r1_production_integration runs UNCHANGED on a temporary mirror of the repository.

The original module (archived as tests/retired/test_step9_63a_r1_production_integration.py.retired) exercised production code whose default paths point
at the real activation state (ledger, run root, authorization manifests, namespace lock). Here it runs
inside a private copy (tests/legacy_isolation.py); the methods listed in RETIRED are not run, and their
properties are covered where the mapping says (evaluation/v1_2_3/step9_63c_r5c10ak_coverage_mapping.json).
"""
import legacy_isolation

RETIRED = {
    "ProductionWiringTests.test_old_r6_authorization_rejected_at_r7_namespace_gate": "tests/test_step9_63c_r5c10ak_isolated_63a_r2_retirement_eligibility.py::test_SupersededRetirementTests__test_current_r7_identity_rejects_old_r6_authorization; tests/test_step9_63c_r5c10ak_isolated_ae_consumer_precommit_gate.py::test_ConsumerPrecommitGateTests__test_executable_superseded_authorization_rejected"
}

legacy_isolation.make_module(globals(), 'test_step9_63a_r1_production_integration', retired=RETIRED)
