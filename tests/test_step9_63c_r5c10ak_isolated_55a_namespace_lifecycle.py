"""Step 9.63c-r5c10ak: test_step9_55a_namespace_lifecycle runs UNCHANGED on a temporary mirror of the repository.

The original module (archived as tests/retired/test_step9_55a_namespace_lifecycle.py.retired) exercised production code whose default paths point
at the real activation state (ledger, run root, authorization manifests, namespace lock). Here it runs
inside a private copy (tests/legacy_isolation.py); the methods listed in RETIRED are not run, and their
properties are covered where the mapping says (evaluation/v1_2_3/step9_63c_r5c10ak_coverage_mapping.json).
"""
import legacy_isolation

RETIRED = {
    "NamespaceLifecycleTests.test_consumed_step954_authorization_cannot_be_reused": "tests/test_step9_63c_r5c10ak_legacy_rewrites.py::Rewritten55a.test_consumed_step954_authorization_cannot_be_reused (same body, run on a synthetic temporary root with a synthetic manifest and ledger)",
    "NamespaceLifecycleTests.test_failed_step955_attempt_cannot_be_resumed": "tests/test_step9_63c_r5c10ak_legacy_rewrites.py::Rewritten55a.test_failed_step955_attempt_cannot_be_resumed (same body, run on a synthetic temporary root with a synthetic manifest and ledger)",
    "NamespaceLifecycleTests.test_new_future_authorization_and_attempt_pass_preflight": "tests/test_step9_63c_r5c10ak_legacy_rewrites.py::Rewritten55a.test_new_future_authorization_and_attempt_pass_preflight (same body, run on a synthetic temporary root with a synthetic manifest and ledger)",
    "NamespaceLifecycleTests.test_missing_authorization_semantic_state_fails_closed": "tests/test_step9_63c_r5c10ak_legacy_rewrites.py::Rewritten55a.test_missing_authorization_semantic_state_fails_closed (same body, run on a synthetic temporary root with a synthetic manifest and ledger)"
}

legacy_isolation.make_module(globals(), 'test_step9_55a_namespace_lifecycle', retired=RETIRED)
